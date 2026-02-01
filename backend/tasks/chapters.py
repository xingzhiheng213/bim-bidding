"""Celery task: generate chapter content for each framework chapter (stage 4.1).

Per chapter: outline LLM -> KB search -> content LLM; write result to chapters step output_snapshot.
Output format: {"total": N, "current": k, "chapters": {"1": "markdown...", "2": "..."}}.
"""
import json
import logging

from celery_app import app
from sqlalchemy.orm import Session

from app import config
from app.database import SessionLocal
from app.knowledge_base import search as kb_search
from app.llm import call_llm
from app.models import Task, TaskStep
from app.prompts import (
    build_chapter_content_messages,
    build_chapter_outline_messages,
    build_chapter_regenerate_messages,
)

logger = logging.getLogger(__name__)

CHAPTER_OUTLINE_TEMPERATURE = 0.2
CHAPTER_CONTENT_TEMPERATURE = 0.3
CHAPTER_REGENERATE_TEMPERATURE = 0.2
ERROR_MESSAGE_MAX_LEN = 2000
KB_TOP_K = 8


def _get_or_create_chapters_step(db: Session, task_id: int) -> TaskStep:
    step = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.step_key == "chapters")
        .first()
    )
    if not step:
        step = TaskStep(task_id=task_id, step_key="chapters", status="pending")
        db.add(step)
        db.flush()
    return step


def _set_chapters_failed(db: Session, task_id: int, error_message: str) -> None:
    step = _get_or_create_chapters_step(db, task_id)
    step.status = "failed"
    step.error_message = (error_message[:ERROR_MESSAGE_MAX_LEN] if error_message else None)
    db.commit()


@app.task
def run_chapters(task_id: int, chapter_numbers: list[int] | None = None) -> None:
    """Generate chapter content for selected framework chapters.

    Reads framework step (completed) for chapters list; optionally filters by chapter_numbers.
    For each chapter: outline LLM -> KB search -> content LLM; appends to chapters step output.
    On success sets chapters step status=completed; on failure sets status=failed and error_message.
    """
    db: Session = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.warning("run_chapters: task_id=%s not found", task_id)
            return

        framework_step = (
            db.query(TaskStep)
            .filter(TaskStep.task_id == task_id, TaskStep.step_key == "framework")
            .first()
        )
        if not framework_step or framework_step.status != "completed" or not framework_step.output_snapshot:
            _set_chapters_failed(db, task_id, "请先完成框架并接受框架")
            return

        try:
            fw_out = json.loads(framework_step.output_snapshot)
        except (json.JSONDecodeError, TypeError):
            _set_chapters_failed(db, task_id, "框架步骤输出格式异常")
            return

        chapters_list = fw_out.get("chapters")
        if not isinstance(chapters_list, list) or not chapters_list:
            _set_chapters_failed(db, task_id, "框架无章节列表")
            return

        if chapter_numbers is not None and len(chapter_numbers) > 0:
            num_set = set(chapter_numbers)
            selected = [ch for ch in chapters_list if ch.get("number") in num_set]
            selected.sort(key=lambda ch: ch.get("number", 0))
        else:
            selected = list(chapters_list)

        if not selected:
            _set_chapters_failed(db, task_id, "筛选后无章节")
            return

        analyze_step = (
            db.query(TaskStep)
            .filter(TaskStep.task_id == task_id, TaskStep.step_key == "analyze")
            .first()
        )
        if not analyze_step or analyze_step.status != "completed" or not analyze_step.output_snapshot:
            _set_chapters_failed(db, task_id, "请先完成分析")
            return

        params_step = (
            db.query(TaskStep)
            .filter(TaskStep.task_id == task_id, TaskStep.step_key == "params")
            .first()
        )
        if not params_step or params_step.status != "completed" or not params_step.output_snapshot:
            _set_chapters_failed(db, task_id, "请先完成参数提取")
            return

        try:
            analyze_out = json.loads(analyze_step.output_snapshot)
            analyze_text = str(analyze_out.get("text", ""))
        except (json.JSONDecodeError, TypeError):
            _set_chapters_failed(db, task_id, "分析步骤输出格式异常")
            return

        try:
            params_out = json.loads(params_step.output_snapshot)
            bim_requirements = params_out.get("bim_requirements")
            if not isinstance(bim_requirements, list):
                bim_requirements = []
            bim_requirements = [str(x) for x in bim_requirements]
            project_info = params_out.get("project_info")
            if not isinstance(project_info, dict):
                project_info = {}
        except (json.JSONDecodeError, TypeError):
            _set_chapters_failed(db, task_id, "参数步骤输出格式异常")
            return

        chapters_step = _get_or_create_chapters_step(db, task_id)
        chapters_step.status = "running"
        chapters_step.error_message = None
        total = len(selected)
        output_payload = {"total": total, "current": 0, "chapters": {}}
        chapters_step.output_snapshot = json.dumps(output_payload, ensure_ascii=False)
        db.commit()

        from app.llm_resolver import get_llm_for_step
        provider, model = get_llm_for_step("chapters")

        for idx, ch in enumerate(selected):
            num = ch.get("number")
            full_name = ch.get("full_name") or f"第{num}章 {ch.get('title', '')}"

            # 在开始生成本章前写入 current=本章序号，便于前端显示「正在生成第 X 章」
            chapters_step = _get_or_create_chapters_step(db, task_id)
            try:
                out = json.loads(chapters_step.output_snapshot or "{}")
            except (json.JSONDecodeError, TypeError):
                out = {"total": total, "current": 0, "chapters": {}}
            out["current"] = num
            out["total"] = total
            if not isinstance(out.get("chapters"), dict):
                out["chapters"] = {}
            chapters_step.output_snapshot = json.dumps(out, ensure_ascii=False)
            db.commit()

            try:
                outline_messages = build_chapter_outline_messages(
                    full_name, analyze_text, bim_requirements
                )
                outline_content = call_llm(
                    provider=provider,
                    model=model,
                    messages=outline_messages,
                    temperature=CHAPTER_OUTLINE_TEMPERATURE,
                )
            except Exception as e:
                logger.exception("run_chapters: task_id=%s chapter %s outline failed", task_id, num)
                _set_chapters_failed(db, task_id, f"第{num}章小节大纲生成失败: {str(e)[:500]}")
                return

            context_chunks = kb_search(query=full_name, top_k=KB_TOP_K)
            context_text = "\n\n".join(context_chunks) if context_chunks else ""

            try:
                content_messages = build_chapter_content_messages(
                    chapter_full_name=full_name,
                    outline_text=outline_content,
                    context_text=context_text,
                    analyze_text=analyze_text,
                    bim_requirements=bim_requirements,
                    project_info=project_info,
                )
                chapter_content = call_llm(
                    provider=provider,
                    model=model,
                    messages=content_messages,
                    temperature=CHAPTER_CONTENT_TEMPERATURE,
                )
            except Exception as e:
                logger.exception("run_chapters: task_id=%s chapter %s content failed", task_id, num)
                _set_chapters_failed(db, task_id, f"第{num}章正文生成失败: {str(e)[:500]}")
                return

            chapters_step = _get_or_create_chapters_step(db, task_id)
            try:
                out = json.loads(chapters_step.output_snapshot or "{}")
            except (json.JSONDecodeError, TypeError):
                out = {"total": total, "current": 0, "chapters": {}}
            if not isinstance(out.get("chapters"), dict):
                out["chapters"] = {}
            out["chapters"][str(num)] = chapter_content
            out["current"] = num
            out["total"] = total
            chapters_step.output_snapshot = json.dumps(out, ensure_ascii=False)
            db.commit()
            logger.info("run_chapters: task_id=%s chapter %s done", task_id, num)

        chapters_step = _get_or_create_chapters_step(db, task_id)
        try:
            out = json.loads(chapters_step.output_snapshot or "{}")
        except (json.JSONDecodeError, TypeError):
            out = {}
        out.pop("current", None)
        chapters_step.output_snapshot = json.dumps(out, ensure_ascii=False)
        chapters_step.status = "completed"
        chapters_step.error_message = None
        db.commit()
        logger.info("run_chapters: task_id=%s all %s chapters completed", task_id, total)
    except Exception as e:
        logger.exception("run_chapters: task_id=%s failed", task_id)
        try:
            db.rollback()
            _set_chapters_failed(db, task_id, str(e)[:ERROR_MESSAGE_MAX_LEN])
        except Exception:
            db.rollback()
            raise
    finally:
        db.close()


@app.task
def regenerate_chapter(task_id: int, chapter_number: int) -> None:
    """Re-generate a single chapter. Reads current content + chapter_points; only updates that chapter.

    If chapter_points exist: use 'current content + user points' prompt (stage 4.1.1).
    If no points: use full outline + content flow (fallback).
    On success: write back to chapters[str(chapter_number)], status=completed; on failure: status=failed.
    """
    db: Session = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.warning("regenerate_chapter: task_id=%s not found", task_id)
            return

        chapters_step = _get_or_create_chapters_step(db, task_id)
        if not chapters_step.output_snapshot:
            _set_chapters_failed(db, task_id, "按章生成步骤无输出")
            return
        try:
            out = json.loads(chapters_step.output_snapshot)
        except (json.JSONDecodeError, TypeError):
            _set_chapters_failed(db, task_id, "按章生成步骤输出格式异常")
            return
        chapters_dict = out.get("chapters")
        if not isinstance(chapters_dict, dict) or str(chapter_number) not in chapters_dict:
            _set_chapters_failed(db, task_id, f"第{chapter_number}章不存在")
            return
        current_content = chapters_dict.get(str(chapter_number)) or ""

        framework_step = (
            db.query(TaskStep)
            .filter(TaskStep.task_id == task_id, TaskStep.step_key == "framework")
            .first()
        )
        if not framework_step or framework_step.status != "completed" or not framework_step.output_snapshot:
            _set_chapters_failed(db, task_id, "请先完成框架")
            return
        try:
            fw_out = json.loads(framework_step.output_snapshot)
        except (json.JSONDecodeError, TypeError):
            _set_chapters_failed(db, task_id, "框架步骤输出格式异常")
            return
        chapters_list = fw_out.get("chapters")
        if not isinstance(chapters_list, list):
            _set_chapters_failed(db, task_id, "框架无章节列表")
            return
        ch_info = next((c for c in chapters_list if c.get("number") == chapter_number), None)
        full_name = (
            ch_info.get("full_name") if ch_info else f"第{chapter_number}章"
        ) or f"第{chapter_number}章"

        chapter_points: list[str] = []
        cp = out.get("chapter_points")
        if isinstance(cp, dict) and str(chapter_number) in cp:
            pts = cp[str(chapter_number)]
            if isinstance(pts, list):
                chapter_points = [str(p) for p in pts if p]

        from app.llm_resolver import get_llm_for_step
        provider, model = get_llm_for_step("chapters")

        if chapter_points:
            messages = build_chapter_regenerate_messages(
                chapter_full_name=full_name,
                current_content=current_content,
                added_points=chapter_points,
            )
            chapter_content = call_llm(
                provider=provider,
                model=model,
                messages=messages,
                temperature=CHAPTER_REGENERATE_TEMPERATURE,
            )
        else:
            analyze_step = (
                db.query(TaskStep)
                .filter(TaskStep.task_id == task_id, TaskStep.step_key == "analyze")
                .first()
            )
            params_step = (
                db.query(TaskStep)
                .filter(TaskStep.task_id == task_id, TaskStep.step_key == "params")
                .first()
            )
            if not analyze_step or not params_step or analyze_step.status != "completed" or params_step.status != "completed":
                _set_chapters_failed(db, task_id, "请先完成分析和参数提取")
                return
            try:
                analyze_out = json.loads(analyze_step.output_snapshot)
                analyze_text = str(analyze_out.get("text", ""))
            except (json.JSONDecodeError, TypeError):
                _set_chapters_failed(db, task_id, "分析步骤输出格式异常")
                return
            try:
                params_out = json.loads(params_step.output_snapshot)
                bim_requirements = params_out.get("bim_requirements")
                if not isinstance(bim_requirements, list):
                    bim_requirements = []
                bim_requirements = [str(x) for x in bim_requirements]
                project_info = params_out.get("project_info")
                if not isinstance(project_info, dict):
                    project_info = {}
            except (json.JSONDecodeError, TypeError):
                _set_chapters_failed(db, task_id, "参数步骤输出格式异常")
                return

            outline_messages = build_chapter_outline_messages(
                full_name, analyze_text, bim_requirements
            )
            outline_content = call_llm(
                provider=provider,
                model=model,
                messages=outline_messages,
                temperature=CHAPTER_OUTLINE_TEMPERATURE,
            )
            context_chunks = kb_search(query=full_name, top_k=KB_TOP_K)
            context_text = "\n\n".join(context_chunks) if context_chunks else ""
            content_messages = build_chapter_content_messages(
                chapter_full_name=full_name,
                outline_text=outline_content,
                context_text=context_text,
                analyze_text=analyze_text,
                bim_requirements=bim_requirements,
                project_info=project_info,
            )
            chapter_content = call_llm(
                provider=provider,
                model=model,
                messages=content_messages,
                temperature=CHAPTER_CONTENT_TEMPERATURE,
            )

        chapters_step = _get_or_create_chapters_step(db, task_id)
        # Snapshot this chapter's content before overwrite (for 6.1 diff: 要点变更前 vs 变更后)
        before_regenerate = {}
        if chapters_step.output_snapshot_before_regenerate:
            try:
                before_regenerate = json.loads(chapters_step.output_snapshot_before_regenerate)
                if not isinstance(before_regenerate, dict):
                    before_regenerate = {}
            except (json.JSONDecodeError, TypeError):
                before_regenerate = {}
        before_regenerate[str(chapter_number)] = current_content
        chapters_step.output_snapshot_before_regenerate = json.dumps(
            before_regenerate, ensure_ascii=False
        )
        try:
            out = json.loads(chapters_step.output_snapshot or "{}")
        except (json.JSONDecodeError, TypeError):
            out = {}
        if not isinstance(out.get("chapters"), dict):
            out["chapters"] = {}
        out["chapters"][str(chapter_number)] = chapter_content
        out.pop("current", None)
        chapters_step.output_snapshot = json.dumps(out, ensure_ascii=False)
        chapters_step.status = "completed"
        chapters_step.error_message = None
        db.commit()
        logger.info("regenerate_chapter: task_id=%s chapter %s done", task_id, chapter_number)
    except Exception as e:
        logger.exception("regenerate_chapter: task_id=%s chapter %s failed", task_id, chapter_number)
        try:
            db.rollback()
            _set_chapters_failed(db, task_id, str(e)[:ERROR_MESSAGE_MAX_LEN])
        except Exception:
            db.rollback()
            raise
    finally:
        db.close()
