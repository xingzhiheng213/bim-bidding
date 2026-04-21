"""Review step endpoints: run (all chapters or single chapter), accept."""
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from tasks.chapters import regenerate_chapter
from tasks.review import run_review, run_review_chapter

from app.auth import Principal, get_principal
from app.database import get_db
from app.models import TaskStep
from app.schemas.task import AcceptReviewRequest
from app.services.step_service import (
    dispatch_celery_step,
    get_or_create_step,
    require_step_completed,
    require_task,
)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post("/{task_id}/steps/review/run", status_code=202)
def run_review_step(
    task_id: int,
    chapter_number: int | None = Query(
        None, description="If set, run review for this chapter only"
    ),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_principal),
):
    """Enqueue review for all chapters or a single chapter. Requires chapters step completed."""
    require_task(task_id, db, principal)

    chapters_step = require_step_completed(task_id, "chapters", db, "请先完成按章生成")
    review_step = get_or_create_step(task_id, "review", db)

    if chapter_number is not None:
        if review_step.status == "running":
            raise HTTPException(
                status_code=400,
                detail="全章审查进行中，请稍后再试单章审查",
            )
        try:
            ch_out = json.loads(chapters_step.output_snapshot)  # type: ignore[arg-type]
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

        dispatch_celery_step(
            review_step,
            run_review_chapter,
            db,
            principal,
            task_id,
            chapter_number,
        )
        return {"message": "单章审查已入队", "step_key": "review"}

    if review_step.status == "running":
        return {"message": "审查已在进行中", "step_key": "review"}
    dispatch_celery_step(review_step, run_review, db, principal, task_id)
    return {"message": "审查已入队", "step_key": "review"}


@router.post("/{task_id}/steps/review/accept", status_code=200)
def accept_review_step(
    task_id: int,
    body: AcceptReviewRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_principal),
):
    """Accept review items for a chapter: write to chapter_points and enqueue chapter regenerate."""
    require_task(task_id, db, principal)

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
    # dispatch_celery_step will commit the above snapshot along with status="running"
    dispatch_celery_step(
        chapters_step,
        regenerate_chapter,
        db,
        principal,
        task_id,
        body.chapter_number,
    )
    return {"message": "已接受校审意见，该章已加入重生成队列", "step_key": "chapters"}
