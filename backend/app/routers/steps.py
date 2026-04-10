"""Step run-triggers for the simple linear pipeline: extract → analyze → params.

Each endpoint validates the prerequisite step and enqueues the Celery task.
The common mechanics (get-or-create step, set running, store celery_task_id)
are handled by :func:`app.services.step_service.dispatch_celery_step`.
"""
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.step_service import (
    dispatch_celery_step,
    get_or_create_step,
    require_step_completed,
    require_task,
)
from tasks.analyze import run_analyze
from tasks.extract import run_extract
from tasks.params import run_params

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post("/{task_id}/steps/extract/run", status_code=202)
def run_extract_step(task_id: int, db: Session = Depends(get_db)):
    """Enqueue document extraction (parse). Requires upload step completed."""
    require_task(task_id, db)

    upload_step = require_step_completed(task_id, "upload", db, "请先完成文件上传")
    try:
        output = json.loads(upload_step.output_snapshot)  # type: ignore[arg-type]
        if not output.get("stored_path"):
            raise HTTPException(status_code=400, detail="请先完成文件上传")
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=400, detail="请先完成文件上传")

    step = get_or_create_step(task_id, "extract", db)
    if step.status == "running":
        return {"message": "解析已在进行中", "step_key": "extract"}
    dispatch_celery_step(step, run_extract, db, task_id)
    return {"message": "解析已入队", "step_key": "extract"}


@router.post("/{task_id}/steps/analyze/run", status_code=202)
def run_analyze_step(task_id: int, db: Session = Depends(get_db)):
    """Enqueue LLM analysis. Requires extract step completed."""
    require_task(task_id, db)

    extract_step = require_step_completed(task_id, "extract", db, "请先完成文档解析")
    try:
        output = json.loads(extract_step.output_snapshot)  # type: ignore[arg-type]
        if not output.get("text"):
            raise HTTPException(status_code=400, detail="请先完成文档解析")
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=400, detail="请先完成文档解析")

    step = get_or_create_step(task_id, "analyze", db)
    if step.status == "running":
        return {"message": "分析已在进行中", "step_key": "analyze"}
    dispatch_celery_step(step, run_analyze, db, task_id)
    return {"message": "分析已入队", "step_key": "analyze"}


@router.post("/{task_id}/steps/params/run", status_code=202)
def run_params_step(task_id: int, db: Session = Depends(get_db)):
    """Enqueue params extraction. Requires analyze step completed."""
    require_task(task_id, db)

    analyze_step = require_step_completed(task_id, "analyze", db, "请先完成分析")
    try:
        output = json.loads(analyze_step.output_snapshot)  # type: ignore[arg-type]
        if not output.get("text"):
            raise HTTPException(status_code=400, detail="请先完成分析")
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=400, detail="请先完成分析")

    step = get_or_create_step(task_id, "params", db)
    if step.status == "running":
        return {"message": "参数提取已在进行中", "step_key": "params"}
    dispatch_celery_step(step, run_params, db, task_id)
    return {"message": "参数提取已入队", "step_key": "params"}
