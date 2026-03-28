"""Task CRUD and list API."""
import io
import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app import config
from app.assembler import assemble_full_markdown
from app.database import get_db
from app.diff_compare import compute_diff
from app.export_docx import markdown_to_docx
from app.models import Task, TaskStep
from app.settings_store import get_export_format_config
from app.schemas.compare import CompareMetaResponse, DiffResponse, FrameworkCompareMeta, ChapterCompareMetaItem
from app.schemas.task import (
    AcceptFrameworkRequest,
    AcceptReviewRequest,
    CreateTaskRequest,
    CreateTaskResponse,
    DEFAULT_INITIAL_STEPS,
    RegenerateChapterRequest,
    RunChaptersRequest,
    SaveChapterPointsRequest,
    TaskCompareSummary,
    TaskDetailResponse,
    TaskStepSchema,
    TaskSummary,
)
from celery_app import app as celery_app
from tasks.analyze import run_analyze
from tasks.chapters import regenerate_all_chapters_from_review, regenerate_chapter, run_chapters
from tasks.extract import run_extract
from tasks.framework import run_framework
from tasks.params import run_params
from tasks.review import run_review, run_review_chapter

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

ALLOWED_EXTENSIONS = (".pdf", ".doc", ".docx")


def _compute_compare_meta_from_steps(
    framework_step: TaskStep | None,
    chapters_step: TaskStep | None,
) -> dict:
    """Pure helper: compute compare meta from already-fetched step objects (no DB I/O).

    Returns dict with:
    - has_any: bool
    - framework_has_diff: bool
    - chapter_numbers: list[int]  # chapters that have before/after snapshots
    """
    framework_has_diff = bool(
        framework_step and framework_step.output_snapshot_before_regenerate
    )

    before_keys: set[int] = set()
    after_keys: set[int] = set()
    if chapters_step:
        if chapters_step.output_snapshot_before_regenerate:
            try:
                before = json.loads(chapters_step.output_snapshot_before_regenerate)
                if isinstance(before, dict):
                    for k in before.keys():
                        try:
                            before_keys.add(int(k))
                        except (TypeError, ValueError):
                            continue
            except (json.JSONDecodeError, TypeError):
                pass
        if chapters_step.output_snapshot:
            try:
                out = json.loads(chapters_step.output_snapshot)
                chapters_map = out.get("chapters") or {}
                if isinstance(chapters_map, dict):
                    for k in chapters_map.keys():
                        try:
                            after_keys.add(int(k))
                        except (TypeError, ValueError):
                            continue
            except (json.JSONDecodeError, TypeError):
                pass

    chapter_numbers = sorted(before_keys & after_keys) if (before_keys and after_keys) else []
    has_any = framework_has_diff or len(chapter_numbers) > 0
    return {
        "has_any": has_any,
        "framework_has_diff": framework_has_diff,
        "chapter_numbers": chapter_numbers,
    }


def _compute_compare_meta_for_task(db: Session, task_id: int) -> dict:
    """DB helper: fetch framework/chapters steps for one task then delegate to pure helper."""
    framework_step = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.step_key == "framework")
        .first()
    )
    chapters_step = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.step_key == "chapters")
        .first()
    )
    return _compute_compare_meta_from_steps(framework_step, chapters_step)

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
    if body and body.name and body.name.strip():
        task.name = body.name.strip()[:255]
    else:
        # Default name for better list readability
        task.name = f"未命名任务-{task.id}-{datetime.now().strftime('%m%d%H%M')}"
    for step_key in steps_to_create:
        step = TaskStep(task_id=task.id, step_key=step_key, status="pending")
        db.add(step)
    db.commit()
    db.refresh(task)
    return CreateTaskResponse(id=task.id, name=task.name, status=task.status, created_at=task.created_at)


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
        name=task.name,
        status=task.status,
        created_at=task.created_at,
        updated_at=task.updated_at,
        steps=[TaskStepSchema.model_validate(s) for s in steps],
    )


@router.get("/{task_id}/compare-meta", response_model=CompareMetaResponse)
def get_task_compare_meta(task_id: int, db: Session = Depends(get_db)):
    """Return compare metadata for a task: which items have before/after versions."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    meta = _compute_compare_meta_for_task(db, task_id)
    framework = FrameworkCompareMeta(has_diff=meta["framework_has_diff"])
    chapters_items: list[ChapterCompareMetaItem] = []
    for num in meta["chapter_numbers"]:
        chapters_items.append(
            ChapterCompareMetaItem(number=num, has_diff=True, label=f"第 {num} 章")
        )
    return CompareMetaResponse(
        has_any=meta["has_any"],
        framework=framework,
        chapters=chapters_items,
    )


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """Delete a task and its steps. Returns 204 No Content.

    DB records are removed first; uploaded files are cleaned up after a
    successful commit so that a failed commit never leaves orphaned DB rows.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.query(TaskStep).filter(TaskStep.task_id == task_id).delete()
    db.delete(task)
    db.commit()
    # Clean up uploaded files after successful DB commit
    task_dir = config.UPLOAD_DIR / f"task_{task_id}"
    shutil.rmtree(task_dir, ignore_errors=True)
    return None


@router.post("/{task_id}/cancel", status_code=200)
def cancel_task(task_id: int, db: Session = Depends(get_db)):
    """Revoke the currently running Celery step for this task (e.g. one-click cancel)."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    running = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.status == "running")
        .first()
    )
    if not running:
        return {"message": "当前无正在执行的步骤", "revoked": False}
    celery_task_id = running.celery_task_id
    if celery_task_id:
        try:
            celery_app.control.revoke(celery_task_id, terminate=True)
        except Exception:
            pass
    running.status = "pending"
    running.celery_task_id = None
    db.commit()
    return {"message": "已取消当前步骤", "revoked": True, "step_key": running.step_key}


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

    result = run_extract.delay(task_id)
    extract_step.celery_task_id = result.id
    db.commit()
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

    result = run_analyze.delay(task_id)
    analyze_step.celery_task_id = result.id
    db.commit()
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

    result = run_params.delay(task_id)
    params_step.celery_task_id = result.id
    db.commit()
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

    result = run_framework.delay(task_id)
    framework_step.celery_task_id = result.id
    db.commit()
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

    result = run_framework.delay(task_id)
    framework_step.celery_task_id = result.id
    db.commit()
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
    """Format framework output_snapshot JSON as comparable text (chapters + sections + subsections)."""
    if not snapshot_json:
        return ""
    try:
        data = json.loads(snapshot_json)
        chapters = data.get("chapters") or []
        lines = []
        for c in chapters:
            full_name = c.get("full_name") or f"第{c.get('number', '')}章 {c.get('title', '')}"
            lines.append(full_name.strip())
            for sec in c.get("sections") or []:
                lines.append(f"  {sec.get('number', '')} {sec.get('title', '')}")
                for sub in sec.get("subsections") or []:
                    lines.append(f"    {sub.get('number', '')} {sub.get('title', '')}")
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

    result = run_chapters.delay(task_id, chapter_numbers=chapter_numbers)
    chapters_step.celery_task_id = result.id
    db.commit()
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

    result = regenerate_chapter.delay(task_id, body.chapter_number)
    chapters_step.celery_task_id = result.id
    db.commit()
    return {"message": "该章已重新入队", "step_key": "chapters"}


@router.post("/{task_id}/steps/review/run", status_code=202)
def run_review_step(
    task_id: int,
    chapter_number: int | None = Query(None, description="If set, run review for this chapter only"),
    db: Session = Depends(get_db),
):
    """Enqueue review for all chapters or a single chapter. Requires chapters step completed."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    chapters_step = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.step_key == "chapters")
        .first()
    )
    if not chapters_step or chapters_step.status != "completed" or not chapters_step.output_snapshot:
        raise HTTPException(status_code=400, detail="请先完成按章生成")

    review_step = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.step_key == "review")
        .first()
    )
    if not review_step:
        review_step = TaskStep(task_id=task_id, step_key="review", status="pending")
        db.add(review_step)
        db.flush()

    if chapter_number is not None:
        if review_step.status == "running":
            raise HTTPException(
                status_code=400,
                detail="全章审查进行中，请稍后再试单章审查",
            )
        try:
            ch_out = json.loads(chapters_step.output_snapshot)
        except (json.JSONDecodeError, TypeError):
            raise HTTPException(status_code=400, detail="按章生成步骤输出格式异常")
        chapters_dict = ch_out.get("chapters")
        if not isinstance(chapters_dict, dict) or str(chapter_number) not in chapters_dict:
            raise HTTPException(status_code=400, detail="该章节不存在或按章生成无该章内容")
        framework_step = (
            db.query(TaskStep)
            .filter(TaskStep.task_id == task_id, TaskStep.step_key == "framework")
            .first()
        )
        if not framework_step or not framework_step.output_snapshot:
            raise HTTPException(status_code=400, detail="请先完成框架")
        try:
            fw_out = json.loads(framework_step.output_snapshot)
        except (json.JSONDecodeError, TypeError):
            raise HTTPException(status_code=400, detail="框架步骤输出格式异常")
        chapters_list = fw_out.get("chapters")
        if not isinstance(chapters_list, list) or not any(
            c.get("number") == chapter_number for c in chapters_list
        ):
            raise HTTPException(status_code=400, detail="框架中无该章节")
        review_step.status = "running"
        review_step.error_message = None
        db.commit()
        result = run_review_chapter.delay(task_id, chapter_number)
        review_step.celery_task_id = result.id
        db.commit()
        return {"message": "单章审查已入队", "step_key": "review"}

    if review_step.status == "running":
        return {"message": "审查已在进行中", "step_key": "review"}

    review_step.status = "running"
    review_step.error_message = None
    db.commit()

    result = run_review.delay(task_id)
    review_step.celery_task_id = result.id
    db.commit()
    return {"message": "审查已入队", "step_key": "review"}


@router.post("/{task_id}/steps/review/accept", status_code=200)
def accept_review_step(
    task_id: int,
    body: AcceptReviewRequest,
    db: Session = Depends(get_db),
):
    """Accept review items for a chapter: write to chapter_points and enqueue regenerate."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    chapters_step = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.step_key == "chapters")
        .first()
    )
    if not chapters_step or not chapters_step.output_snapshot:
        raise HTTPException(status_code=400, detail="按章生成未完成或该任务无按章生成步骤")
    try:
        ch_out = json.loads(chapters_step.output_snapshot)
        chapters = ch_out.get("chapters")
        if not isinstance(chapters, dict) or str(body.chapter_number) not in chapters:
            raise HTTPException(status_code=400, detail="该章节不存在或按章生成未完成")
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=400, detail="按章生成步骤输出格式异常")

    review_step = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.step_key == "review")
        .first()
    )
    if not review_step or not review_step.output_snapshot:
        raise HTTPException(status_code=400, detail="请先完成审查或审查无结果")

    if "chapter_points" not in ch_out or not isinstance(ch_out["chapter_points"], dict):
        ch_out["chapter_points"] = {}
    ch_out["chapter_points"][str(body.chapter_number)] = body.accepted_items
    chapters_step.output_snapshot = json.dumps(ch_out, ensure_ascii=False)
    chapters_step.status = "running"
    chapters_step.error_message = None
    db.commit()

    result = regenerate_chapter.delay(task_id, body.chapter_number)
    chapters_step.celery_task_id = result.id
    db.commit()
    return {"message": "已接受校审意见，该章已加入重生成队列", "step_key": "chapters"}


@router.post("/{task_id}/steps/review/regenerate-all", status_code=202)
def regenerate_all_from_review_step(task_id: int, db: Session = Depends(get_db)):
    """One-click: regenerate all chapters sequentially using review output as chapter_points.
    Enqueues a single task that runs chapters in order to respect API limits.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    chapters_step = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.step_key == "chapters")
        .first()
    )
    if not chapters_step or not chapters_step.output_snapshot:
        raise HTTPException(status_code=400, detail="请先完成按章生成")
    if chapters_step.status == "running":
        raise HTTPException(status_code=400, detail="章节正在重生成中，请稍后再试")
    if chapters_step.status != "completed":
        raise HTTPException(status_code=400, detail="请先完成按章生成")

    review_step = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.step_key == "review")
        .first()
    )
    if not review_step or review_step.status != "completed" or not review_step.output_snapshot:
        raise HTTPException(status_code=400, detail="请先完成校审")

    chapters_step.status = "running"
    chapters_step.error_message = None
    db.commit()
    result = regenerate_all_chapters_from_review.delay(task_id)
    chapters_step.celery_task_id = result.id
    db.commit()
    return {"message": "已入队，将按章顺序重生成全部章节", "step_key": "chapters"}


@router.get("/{task_id}/download")
def download_docx(task_id: int, db: Session = Depends(get_db)):
    """Generate DOCX from assembled Markdown (chapters + 附录)."""
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
    body = buffer.getvalue()

    return Response(
        content=body,
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
    """List tasks (newest first).

    Uses 3 queries total regardless of task count (vs. the previous 1+2N pattern):
      1. SELECT all tasks
      2. SELECT framework steps WHERE task_id IN (...)
      3. SELECT chapters steps WHERE task_id IN (...)
    """
    tasks = db.query(Task).order_by(Task.created_at.desc()).all()
    if not tasks:
        return []

    task_ids = [t.id for t in tasks]

    framework_steps = (
        db.query(TaskStep)
        .filter(TaskStep.task_id.in_(task_ids), TaskStep.step_key == "framework")
        .all()
    )
    chapters_steps = (
        db.query(TaskStep)
        .filter(TaskStep.task_id.in_(task_ids), TaskStep.step_key == "chapters")
        .all()
    )

    framework_by_task: dict[int, TaskStep] = {s.task_id: s for s in framework_steps}
    chapters_by_task: dict[int, TaskStep] = {s.task_id: s for s in chapters_steps}

    summaries: list[TaskSummary] = []
    for t in tasks:
        meta = _compute_compare_meta_from_steps(
            framework_by_task.get(t.id),
            chapters_by_task.get(t.id),
        )
        compare_summary: TaskCompareSummary | None = None
        if meta["has_any"]:
            compare_summary = TaskCompareSummary(
                has_framework=meta["framework_has_diff"],
                chapter_count=len(meta["chapter_numbers"]),
            )
        summaries.append(
            TaskSummary(
                id=t.id,
                name=t.name,
                status=t.status,
                created_at=t.created_at,
                compare_summary=compare_summary,
            )
        )
    return summaries
