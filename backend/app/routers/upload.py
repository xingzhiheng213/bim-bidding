"""File upload endpoint for tasks."""
import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app import config
from app.database import get_db
from app.models import TaskStep
from app.services.step_service import require_task
from app.upload_sniff import bytes_match_upload_extension

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

# SEC-04: mirrors parser.py — .doc is intentionally excluded
ALLOWED_EXTENSIONS = (".pdf", ".docx")


@router.post("/{task_id}/upload", status_code=201)
def upload_file(
    task_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a file for the task.

    Validates extension whitelist, magic bytes (SEC-04), and file size.
    On success, stores the file and marks the upload step as completed.
    Re-uploading replaces the previous file after a successful DB commit.
    """
    require_task(task_id, db)

    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type; allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    task_dir = config.UPLOAD_DIR / f"task_{task_id}"
    task_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{suffix}"
    dest_path = task_dir / stored_name
    relative_stored_path = f"task_{task_id}/{stored_name}"

    # Fetch existing upload step now so we can recover the old file path before overwriting
    upload_step = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.step_key == "upload")
        .first()
    )
    old_file_path: Path | None = None
    if upload_step and upload_step.output_snapshot:
        try:
            old_output = json.loads(upload_step.output_snapshot)
            old_rel = old_output.get("stored_path")
            if old_rel:
                old_file_path = config.UPLOAD_DIR / old_rel
        except (json.JSONDecodeError, TypeError):
            pass

    head_max = 8192
    head = file.file.read(head_max)
    if len(head) < 4:
        raise HTTPException(status_code=400, detail="文件过小或为空")
    if not bytes_match_upload_extension(suffix, head):
        raise HTTPException(
            status_code=400,
            detail="文件内容与扩展名不符（请上传真实 PDF 或 DOCX）",
        )

    size = 0
    chunk_size = 1024 * 1024
    try:
        with open(dest_path, "wb") as f:
            f.write(head)
            size += len(head)
            while True:
                chunk = file.file.read(chunk_size)
                if not chunk:
                    break
                size += len(chunk)
                if size > config.MAX_UPLOAD_SIZE_BYTES:
                    dest_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=400,
                        detail=f"File too large; max {config.MAX_UPLOAD_SIZE_MB} MB",
                    )
                f.write(chunk)
    except HTTPException:
        raise
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}") from e

    if not upload_step:
        upload_step = TaskStep(task_id=task_id, step_key="upload", status="pending")
        db.add(upload_step)
        db.flush()

    output = {
        "stored_path": relative_stored_path,
        "original_filename": filename,
    }
    upload_step.output_snapshot = json.dumps(output, ensure_ascii=False)
    upload_step.status = "completed"
    upload_step.error_message = None
    db.commit()

    # Remove the previous upload only after a successful DB commit
    if old_file_path and old_file_path != dest_path:
        old_file_path.unlink(missing_ok=True)

    return {
        "step_key": "upload",
        "status": "completed",
        "message": "ok",
        "stored_path": relative_stored_path,
    }
