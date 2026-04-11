"""Chapters step endpoints: run, save-points, regenerate, regenerate-all-from-review, diff."""
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from tasks.chapters import regenerate_all_chapters_from_review, regenerate_chapter, run_chapters

from app.database import get_db
from app.diff_compare import compute_diff
from app.models import TaskStep
from app.schemas.compare import DiffResponse
from app.schemas.task import RegenerateChapterRequest, RunChaptersRequest, SaveChapterPointsRequest
from app.services.step_service import (
    dispatch_celery_step,
    get_or_create_step,
    require_step_completed,
    require_task,
)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post("/{task_id}/steps/chapters/run", status_code=202)
def run_chapters_step(
    task_id: int,
    body: RunChaptersRequest | None = None,
    db: Session = Depends(get_db),
):
    """Enqueue chapter generation. Requires framework step completed with a non-empty chapters list."""
    require_task(task_id, db)

    framework_step = require_step_completed(task_id, "framework", db, "请先完成并接受框架")
    try:
        fw_out = json.loads(framework_step.output_snapshot)  # type: ignore[arg-type]
        chapters_list = fw_out.get("chapters")
        if not isinstance(chapters_list, list) or not chapters_list:
            raise HTTPException(status_code=400, detail="框架无章节列表")
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=400, detail="框架步骤输出格式异常")

    step = get_or_create_step(task_id, "chapters", db)
    if step.status == "running":
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

    step.output_snapshot = json.dumps(
        {"total": total, "current": 0, "chapters": {}},
        ensure_ascii=False,
    )
    dispatch_celery_step(step, run_chapters, db, task_id, chapter_numbers=chapter_numbers)
    return {"message": "按章生成已入队", "step_key": "chapters"}


@router.post("/{task_id}/steps/chapters/save-points", status_code=200)
def save_chapter_points(
    task_id: int,
    body: SaveChapterPointsRequest,
    db: Session = Depends(get_db),
):
    """Save user points/suggestions for a chapter (step status remains completed)."""
    require_task(task_id, db)

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
    """Re-generate a single chapter. Requires chapters step completed and the chapter to exist."""
    require_task(task_id, db)

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

    output["current"] = body.chapter_number
    chapters_step.output_snapshot = json.dumps(output, ensure_ascii=False)
    dispatch_celery_step(chapters_step, regenerate_chapter, db, task_id, body.chapter_number)
    return {"message": "该章已重新入队", "step_key": "chapters"}


@router.post("/{task_id}/steps/review/regenerate-all", status_code=202)
def regenerate_all_from_review_step(task_id: int, db: Session = Depends(get_db)):
    """One-click: regenerate all chapters sequentially using review output as chapter_points.

    Enqueues a single Celery task that runs chapters in order to respect API rate limits.
    """
    require_task(task_id, db)

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

    dispatch_celery_step(chapters_step, regenerate_all_chapters_from_review, db, task_id)
    return {"message": "已入队，将按章顺序重生成全部章节", "step_key": "chapters"}


@router.get("/{task_id}/steps/chapters/diff", response_model=DiffResponse)
def get_chapters_diff(
    task_id: int,
    chapter_number: int = Query(..., description="章节号"),
    db: Session = Depends(get_db),
):
    """Return last regenerate for the given chapter: original vs modified text and structured diff."""
    require_task(task_id, db)
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
