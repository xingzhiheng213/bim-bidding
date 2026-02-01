"""Task CRUD and list API."""
import io
import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app import config
from app.assembler import assemble_full_markdown
from app.database import get_db
from app.diff_compare import compute_diff
from app.export_docx import markdown_to_docx
from app.models import Task, TaskStep
from app.settings_store import get_export_format_config
from app.schemas.compare import DiffResponse
from app.schemas.task import (
    AcceptFrameworkRequest,
    CreateTaskRequest,
    CreateTaskResponse,
    DEFAULT_INITIAL_STEPS,
    RegenerateChapterRequest,
    RunChaptersRequest,
    SaveChapterPointsRequest,
    TaskDetailResponse,
    TaskStepSchema,
    TaskSummary,
)
from tasks.analyze import run_analyze
from tasks.chapters import regenerate_chapter, run_chapters
from tasks.extract import run_extract
from tasks.framework import run_framework
from tasks.params import run_params

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

ALLOWED_EXTENSIONS = (".pdf", ".doc", ".docx")


@router.post("", response_model=CreateTaskResponse, status_code=201)
def create_task(
    body: CreateTaskRequest | None = Body(None),
    db: Session = Depends(get_db),
):
    """Create a task and optionally initial steps (all pending)."""
    steps_to_create = (
        body.initial_steps if body and body.initial_steps
        else DEFAULT_INITIAL_STEPS
    )
    task = Task(status="pending")
    db.add(task)
    db.flush()  # get task.id
    for step_key in steps_to_create:
        step = TaskStep(task_id=task.id, step_key=step_key, status="pending")
        db.add(step)
    db.commit()
    db.refresh(task)
    return CreateTaskResponse(id=task.id, status=task.status, created_at=task.created_at)


@router.get("/{task_id}", response_model=TaskDetailResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    """Get task by id with steps (ordered by step id)."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    steps = db.query(TaskStep).filter(TaskStep.task_id == task_id).order_by(TaskStep.id).all()
    return TaskDetailResponse(
        id=task.id,
        user_id=task.user_id,
        status=task.status,
        created_at=task.created_at,
        updated_at=task.updated_at,
        steps=[TaskStepSchema.model_validate(s) for s in steps],
    )


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """Delete a task and its steps. Returns 204 No Content."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.query(TaskStep).filter(TaskStep.task_id == task_id).delete()
    db.delete(task)
    db.commit()
    return None


@router.post("/{task_id}/upload", status_code=201)
def upload_file(
    task_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a file for the task; validate type (pdf/doc/docx) and size; store and update upload step."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

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

    size = 0
    chunk_size = 1024 * 1024
    try:
        with open(dest_path, "wb") as f:
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

    upload_step = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.step_key == "upload")
        .first()
    )
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

    return {
        "step_key": "upload",
        "status": "completed",
        "message": "ok",
        "stored_path": relative_stored_path,
    }


@router.post("/{task_id}/steps/extract/run", status_code=202)
def run_extract_step(task_id: int, db: Session = Depends(get_db)):
    """Enqueue document extraction (parse) for the task. Requires upload step completed."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    upload_step = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.step_key == "upload")
        .first()
    )
    if not upload_step or upload_step.status != "completed" or not upload_step.output_snapshot:
        raise HTTPException(status_code=400, detail="请先完成文件上传")
    try:
        output = json.loads(upload_step.output_snapshot)
        if not output.get("stored_path"):
            raise HTTPException(status_code=400, detail="请先完成文件上传")
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=400, detail="请先完成文件上传")

    extract_step = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.step_key == "extract")
        .first()
    )
    if not extract_step:
        extract_step = TaskStep(task_id=task_id, step_key="extract", status="pending")
        db.add(extract_step)
        db.flush()
    if extract_step.status == "running":
        return {"message": "解析已在进行中", "step_key": "extract"}

    extract_step.status = "running"
    extract_step.error_message = None
    db.commit()

    run_extract.delay(task_id)
    return {"message": "解析已入队", "step_key": "extract"}


@router.post("/{task_id}/steps/analyze/run", status_code=202)
def run_analyze_step(task_id: int, db: Session = Depends(get_db)):
    """Enqueue LLM analysis for the task. Requires extract step completed."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    extract_step = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.step_key == "extract")
        .first()
    )
    if not extract_step or extract_step.status != "completed" or not extract_step.output_snapshot:
        raise HTTPException(status_code=400, detail="请先完成文档解析")
    try:
        output = json.loads(extract_step.output_snapshot)
        if not output.get("text"):
            raise HTTPException(status_code=400, detail="请先完成文档解析")
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=400, detail="请先完成文档解析")

    analyze_step = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.step_key == "analyze")
        .first()
    )
    if not analyze_step:
        analyze_step = TaskStep(task_id=task_id, step_key="analyze", status="pending")
        db.add(analyze_step)
        db.flush()
    if analyze_step.status == "running":
        return {"message": "分析已在进行中", "step_key": "analyze"}

    analyze_step.status = "running"
    analyze_step.error_message = None
    db.commit()

    run_analyze.delay(task_id)
    return {"message": "分析已入队", "step_key": "analyze"}


@router.post("/{task_id}/steps/params/run", status_code=202)
def run_params_step(task_id: int, db: Session = Depends(get_db)):
    """Enqueue params extraction for the task. Requires analyze step completed."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    analyze_step = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.step_key == "analyze")
        .first()
    )
    if not analyze_step or analyze_step.status != "completed" or not analyze_step.output_snapshot:
        raise HTTPException(status_code=400, detail="请先完成分析")
    try:
        output = json.loads(analyze_step.output_snapshot)
        if not output.get("text"):
            raise HTTPException(status_code=400, detail="请先完成分析")
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=400, detail="请先完成分析")

    params_step = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.step_key == "params")
        .first()
    )
    if not params_step:
        params_step = TaskStep(task_id=task_id, step_key="params", status="pending")
        db.add(params_step)
        db.flush()
    if params_step.status == "running":
        return {"message": "参数提取已在进行中", "step_key": "params"}

    params_step.status = "running"
    params_step.error_message = None
    db.commit()

    run_params.delay(task_id)
    return {"message": "参数提取已入队", "step_key": "params"}


@router.post("/{task_id}/steps/framework/run", status_code=202)
def run_framework_step(task_id: int, db: Session = Depends(get_db)):
    """Enqueue framework generation for the task. Requires params step completed."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    params_step = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.step_key == "params")
        .first()
    )
    if not params_step or params_step.status != "completed" or not params_step.output_snapshot:
        raise HTTPException(status_code=400, detail="请先完成参数提取")
    try:
        output = json.loads(params_step.output_snapshot)
        if not isinstance(output.get("bim_requirements"), list):
            raise HTTPException(status_code=400, detail="请先完成参数提取")
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=400, detail="请先完成参数提取")

    framework_step = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.step_key == "framework")
        .first()
    )
    if not framework_step:
        framework_step = TaskStep(task_id=task_id, step_key="framework", status="pending")
        db.add(framework_step)
        db.flush()
    if framework_step.status == "running":
        return {"message": "框架生成已在进行中", "step_key": "framework"}

    framework_step.status = "running"
    framework_step.error_message = None
    db.commit()

    run_framework.delay(task_id)
    return {"message": "框架已入队", "step_key": "framework"}


@router.post("/{task_id}/steps/framework/regenerate", status_code=202)
def regenerate_framework_step(task_id: int, db: Session = Depends(get_db)):
    """Re-enqueue framework generation when step is waiting_user. Resets step to running and enqueues run_framework."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    framework_step = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.step_key == "framework")
        .first()
    )
    if not framework_step:
        raise HTTPException(status_code=400, detail="未找到框架步骤")
    if framework_step.status == "running":
        return {"message": "框架生成已在进行中", "step_key": "framework"}
    if framework_step.status != "waiting_user":
        raise HTTPException(status_code=400, detail="仅当框架等待审核时可重新生成")

    framework_step.status = "running"
    framework_step.error_message = None
    db.commit()

    run_framework.delay(task_id)
    return {"message": "框架已重新入队", "step_key": "framework"}


@router.post("/{task_id}/steps/framework/save-points", status_code=200)
def save_framework_points(
    task_id: int,
    body: AcceptFrameworkRequest,
    db: Session = Depends(get_db),
):
    """Save user points/suggestions for the framework. Only updates extra_points, status stays waiting_user.
    User can then click 'regenerate' to regenerate the framework incorporating these points."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    framework_step = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.step_key == "framework")
        .first()
    )
    if not framework_step:
        raise HTTPException(status_code=400, detail="未找到框架步骤")
    if framework_step.status != "waiting_user":
        raise HTTPException(status_code=400, detail="仅当框架等待审核时可保存要点")

    output = {}
    if framework_step.output_snapshot:
        try:
            output = json.loads(framework_step.output_snapshot)
            if not isinstance(output, dict):
                output = {}
        except (json.JSONDecodeError, TypeError):
            output = {}
    output["extra_points"] = body.added_points
    framework_step.output_snapshot = json.dumps(output, ensure_ascii=False)
    db.commit()
    return {"message": "已保存要点", "step_key": "framework"}


@router.post("/{task_id}/steps/framework/accept", status_code=200)
def accept_framework_step(
    task_id: int,
    body: AcceptFrameworkRequest,
    db: Session = Depends(get_db),
):
    """Accept framework and set step to completed. Optionally merge added_points into output for stage 4. Only when status is waiting_user."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    framework_step = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.step_key == "framework")
        .first()
    )
    if not framework_step:
        raise HTTPException(status_code=400, detail="未找到框架步骤")
    if framework_step.status != "waiting_user":
        raise HTTPException(status_code=400, detail="仅当框架等待审核时可接受")

    output = {}
    if framework_step.output_snapshot:
        try:
            output = json.loads(framework_step.output_snapshot)
            if not isinstance(output, dict):
                output = {}
        except (json.JSONDecodeError, TypeError):
            output = {}
    if body.added_points:
        output["extra_points"] = body.added_points
    framework_step.output_snapshot = json.dumps(output, ensure_ascii=False)
    framework_step.status = "completed"
    framework_step.error_message = None
    db.commit()
    return {"message": "已接受并继续", "step_key": "framework"}


def _framework_snapshot_to_text(snapshot_json: str | None) -> str:
    """Format framework output_snapshot JSON as comparable text (one line per chapter)."""
    if not snapshot_json:
        return ""
    try:
        data = json.loads(snapshot_json)
        chapters = data.get("chapters") or []
        lines = []
        for c in chapters:
            full_name = c.get("full_name") or f"第{c.get('number', '')}章 {c.get('title', '')}"
            lines.append(full_name.strip())
        return "\n".join(lines)
    except (json.JSONDecodeError, TypeError):
        return ""


@router.get("/{task_id}/steps/framework/diff", response_model=DiffResponse)
def get_framework_diff(task_id: int, db: Session = Depends(get_db)):
    """Return last framework regenerate: original vs modified and structured diff."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    framework_step = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.step_key == "framework")
        .first()
    )
    if not framework_step:
        raise HTTPException(status_code=404, detail="未找到框架步骤")
    original_text = _framework_snapshot_to_text(framework_step.output_snapshot_before_regenerate)
    modified_text = _framework_snapshot_to_text(framework_step.output_snapshot)
    if not original_text and not modified_text:
        raise HTTPException(
            status_code=404,
            detail="无框架重生成前后数据，请先执行一次「重新生成框架」后再查看对比",
        )
    diff = compute_diff(original_text, modified_text)
    return DiffResponse(original=original_text, modified=modified_text, diff=diff)


@router.get("/{task_id}/steps/chapters/diff", response_model=DiffResponse)
def get_chapters_diff(
    task_id: int,
    chapter_number: int = Query(..., description="章节号"),
    db: Session = Depends(get_db),
):
    """Return last regenerate for the given chapter: original vs modified and structured diff."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    chapters_step = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.step_key == "chapters")
        .first()
    )
    if not chapters_step:
        raise HTTPException(status_code=404, detail="未找到按章生成步骤")
    original_text = ""
    if chapters_step.output_snapshot_before_regenerate:
        try:
            before = json.loads(chapters_step.output_snapshot_before_regenerate)
            if isinstance(before, dict) and str(chapter_number) in before:
                original_text = before[str(chapter_number)] or ""
        except (json.JSONDecodeError, TypeError):
            pass
    modified_text = ""
    if chapters_step.output_snapshot:
        try:
            out = json.loads(chapters_step.output_snapshot)
            ch = (out.get("chapters") or {}).get(str(chapter_number))
            if ch is not None:
                modified_text = ch or ""
        except (json.JSONDecodeError, TypeError):
            pass
    if not original_text and not modified_text:
        raise HTTPException(
            status_code=404,
            detail=f"无第{chapter_number}章重生成前后数据，请先对该章执行「重新生成本章」后再查看对比",
        )
    diff = compute_diff(original_text, modified_text)
    return DiffResponse(original=original_text, modified=modified_text, diff=diff)


@router.post("/{task_id}/steps/chapters/run", status_code=202)
def run_chapters_step(
    task_id: int,
    body: RunChaptersRequest | None = None,
    db: Session = Depends(get_db),
):
    """Enqueue chapter generation. Requires framework step completed with non-empty chapters."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    framework_step = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.step_key == "framework")
        .first()
    )
    if not framework_step or framework_step.status != "completed" or not framework_step.output_snapshot:
        raise HTTPException(status_code=400, detail="请先完成并接受框架")
    try:
        fw_out = json.loads(framework_step.output_snapshot)
        chapters_list = fw_out.get("chapters")
        if not isinstance(chapters_list, list) or not chapters_list:
            raise HTTPException(status_code=400, detail="框架无章节列表")
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=400, detail="框架步骤输出格式异常")

    chapters_step = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.step_key == "chapters")
        .first()
    )
    if not chapters_step:
        chapters_step = TaskStep(task_id=task_id, step_key="chapters", status="pending")
        db.add(chapters_step)
        db.flush()
    if chapters_step.status == "running":
        return {"message": "按章生成已在进行中", "step_key": "chapters"}

    chapter_numbers = body.chapter_numbers if body and body.chapter_numbers else None
    if chapter_numbers is not None and len(chapter_numbers) > 0:
        num_set = set(chapter_numbers)
        selected = [ch for ch in chapters_list if ch.get("number") in num_set]
        if not selected:
            raise HTTPException(status_code=400, detail="指定章节号在框架中不存在")
        total = len(selected)
    else:
        total = len(chapters_list)

    chapters_step.status = "running"
    chapters_step.error_message = None
    chapters_step.output_snapshot = json.dumps(
        {"total": total, "current": 0, "chapters": {}},
        ensure_ascii=False,
    )
    db.commit()

    run_chapters.delay(task_id, chapter_numbers=chapter_numbers)
    return {"message": "按章生成已入队", "step_key": "chapters"}


@router.post("/{task_id}/steps/chapters/save-points", status_code=200)
def save_chapter_points(
    task_id: int,
    body: SaveChapterPointsRequest,
    db: Session = Depends(get_db),
):
    """Save user points/suggestions for a chapter. Only updates chapter_points, status stays completed."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    chapters_step = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.step_key == "chapters")
        .first()
    )
    if not chapters_step:
        raise HTTPException(status_code=400, detail="未找到按章生成步骤")
    if chapters_step.status != "completed":
        raise HTTPException(status_code=400, detail="仅当按章生成已完成时可保存要点")

    try:
        output = json.loads(chapters_step.output_snapshot or "{}")
        if not isinstance(output, dict):
            output = {}
    except (json.JSONDecodeError, TypeError):
        output = {}
    chapters = output.get("chapters")
    if not isinstance(chapters, dict) or str(body.chapter_number) not in chapters:
        raise HTTPException(status_code=400, detail="该章节不存在或未生成")

    if "chapter_points" not in output or not isinstance(output["chapter_points"], dict):
        output["chapter_points"] = {}
    output["chapter_points"][str(body.chapter_number)] = body.added_points
    chapters_step.output_snapshot = json.dumps(output, ensure_ascii=False)
    db.commit()
    return {"message": "已保存要点", "step_key": "chapters"}


@router.post("/{task_id}/steps/chapters/regenerate", status_code=202)
def regenerate_chapter_step(
    task_id: int,
    body: RegenerateChapterRequest,
    db: Session = Depends(get_db),
):
    """Re-generate a single chapter. Requires chapters step completed and chapter exists."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    chapters_step = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.step_key == "chapters")
        .first()
    )
    if not chapters_step:
        raise HTTPException(status_code=400, detail="未找到按章生成步骤")
    if chapters_step.status == "running":
        return {"message": "按章生成已在进行中", "step_key": "chapters"}
    if chapters_step.status != "completed":
        raise HTTPException(status_code=400, detail="仅当按章生成已完成时可重新生成本章")

    try:
        output = json.loads(chapters_step.output_snapshot or "{}")
        if not isinstance(output, dict):
            output = {}
    except (json.JSONDecodeError, TypeError):
        output = {}
    chapters = output.get("chapters")
    if not isinstance(chapters, dict) or str(body.chapter_number) not in chapters:
        raise HTTPException(status_code=400, detail="该章节不存在或未生成")

    if body.added_points:
        if "chapter_points" not in output or not isinstance(output["chapter_points"], dict):
            output["chapter_points"] = {}
        output["chapter_points"][str(body.chapter_number)] = body.added_points
        chapters_step.output_snapshot = json.dumps(output, ensure_ascii=False)

    chapters_step.status = "running"
    chapters_step.error_message = None
    output = json.loads(chapters_step.output_snapshot or "{}")
    if not isinstance(output, dict):
        output = {}
    output["current"] = body.chapter_number
    chapters_step.output_snapshot = json.dumps(output, ensure_ascii=False)
    db.commit()

    regenerate_chapter.delay(task_id, body.chapter_number)
    return {"message": "该章已重新入队", "step_key": "chapters"}


@router.get("/{task_id}/download")
def download_docx(task_id: int, db: Session = Depends(get_db)):
    """Generate DOCX from assembled Markdown and return as file stream."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        md = assemble_full_markdown(task_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    format_options = get_export_format_config()
    doc = markdown_to_docx(md, format_options)
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": (
                f'attachment; filename="BIM_bidding_task_{task_id}.docx"; '
                f"filename*=UTF-8''BIM%E6%A0%87%E4%B9%A6_%E4%BB%BB%E5%8A%A1{task_id}.docx"
            ),
        },
    )


@router.get("", response_model=list[TaskSummary])
def list_tasks(db: Session = Depends(get_db)):
    """List tasks (newest first)."""
    tasks = db.query(Task).order_by(Task.created_at.desc()).all()
    return [TaskSummary(id=t.id, status=t.status, created_at=t.created_at) for t in tasks]
