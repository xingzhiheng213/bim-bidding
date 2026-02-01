"""Celery task: generate document framework from analyze + params + knowledge base.

Step statuses: pending / running / waiting_user / completed / failed.
Framework step is set to waiting_user on success (user must accept/regenerate/add points)."""
import json
import logging

from celery_app import app
from sqlalchemy.orm import Session

from app import config
from app.database import SessionLocal
from app.knowledge_base import search as kb_search
from app.llm import call_llm
from app.models import Task, TaskStep
from app.prompts import build_framework_messages, parse_framework_text

logger = logging.getLogger(__name__)

FRAMEWORK_TEMPERATURE = 0.4
# 有用户要点时用更低温度，减少对「未要求部分」的随意改写
FRAMEWORK_TEMPERATURE_WITH_USER_POINTS = 0.1
ERROR_MESSAGE_MAX_LEN = 2000
# Truncate analyze text for KB query to avoid huge requests
KB_QUERY_MAX_LEN = 500


def _get_or_create_framework_step(db: Session, task_id: int) -> TaskStep:
    step = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.step_key == "framework")
        .first()
    )
    if not step:
        step = TaskStep(task_id=task_id, step_key="framework", status="pending")
        db.add(step)
        db.flush()
    return step


def _set_framework_failed(db: Session, task_id: int, error_message: str) -> None:
    step = _get_or_create_framework_step(db, task_id)
    step.status = "failed"
    step.error_message = (error_message[:ERROR_MESSAGE_MAX_LEN] if error_message else None)
    step.output_snapshot = None
    db.commit()


@app.task
def run_framework(task_id: int) -> None:
    """Generate framework from analyze + params + KB; write chapters to framework step.

    Reads analyze step text, params step (bim_requirements etc.), calls KB search,
    then LLM with framework prompt, parses "第X章 标题" into chapters, writes
    framework step output_snapshot = {"chapters": [...]}. On failure sets
    framework step status=failed and error_message.
    """
    db: Session = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.warning("run_framework: task_id=%s not found", task_id)
            return

        params_step = (
            db.query(TaskStep)
            .filter(TaskStep.task_id == task_id, TaskStep.step_key == "params")
            .first()
        )
        if not params_step or params_step.status != "completed" or not params_step.output_snapshot:
            _set_framework_failed(db, task_id, "请先完成参数提取")
            return

        analyze_step = (
            db.query(TaskStep)
            .filter(TaskStep.task_id == task_id, TaskStep.step_key == "analyze")
            .first()
        )
        if not analyze_step or analyze_step.status != "completed" or not analyze_step.output_snapshot:
            _set_framework_failed(db, task_id, "请先完成分析")
            return

        try:
            params_output = json.loads(params_step.output_snapshot)
        except (json.JSONDecodeError, TypeError):
            _set_framework_failed(db, task_id, "参数步骤输出格式异常")
            return

        bim_requirements = params_output.get("bim_requirements")
        if not isinstance(bim_requirements, list):
            bim_requirements = []
        bim_requirements = [str(x) for x in bim_requirements]

        try:
            analyze_output = json.loads(analyze_step.output_snapshot)
        except (json.JSONDecodeError, TypeError):
            _set_framework_failed(db, task_id, "分析步骤输出格式异常")
            return

        analyze_text = analyze_output.get("text")
        if analyze_text is None:
            _set_framework_failed(db, task_id, "分析步骤缺少 text")
            return
        analyze_text = str(analyze_text)

        # KB search: query = truncated analyze or fixed string (Dify used llm.text)
        query = analyze_text[:KB_QUERY_MAX_LEN].strip() if analyze_text else "BIM技术标框架"
        chunks = kb_search(query=query, top_k=10)
        context_text = "\n\n".join(chunks) if chunks else ""

        # Read existing framework step output for extra_points and current chapters (for "user has ideas" mode)
        extra_points: list[str] = []
        current_chapters: list[dict] = []
        framework_step_for_input = _get_or_create_framework_step(db, task_id)
        if framework_step_for_input.output_snapshot:
            try:
                out = json.loads(framework_step_for_input.output_snapshot)
                if isinstance(out, dict):
                    if isinstance(out.get("extra_points"), list):
                        extra_points = [str(p) for p in out["extra_points"] if p]
                    if isinstance(out.get("chapters"), list):
                        current_chapters = out["chapters"]
            except (json.JSONDecodeError, TypeError):
                pass

        # 有用户要点时只传「当前框架 + 要点」；无要点时传完整 analyze + params + context
        messages = build_framework_messages(
            analyze_text=analyze_text,
            bim_requirements=bim_requirements,
            context_text=context_text,
            extra_points=extra_points if extra_points else None,
            current_chapters=current_chapters if extra_points else None,
        )
        from app.llm_resolver import get_llm_for_step
        provider, model = get_llm_for_step("framework")

        temperature = (
            FRAMEWORK_TEMPERATURE_WITH_USER_POINTS if extra_points else FRAMEWORK_TEMPERATURE
        )
        content = call_llm(
            provider=provider,
            model=model,
            messages=messages,
            temperature=temperature,
        )

        chapters = parse_framework_text(content)
        if not chapters:
            logger.warning("run_framework: task_id=%s parse_framework_text returned no chapters", task_id)

        framework_step = _get_or_create_framework_step(db, task_id)
        # Snapshot current output before overwrite (for 6.1 diff: 要点变更前 vs 变更后)
        if framework_step.output_snapshot:
            framework_step.output_snapshot_before_regenerate = framework_step.output_snapshot
        # Preserve extra_points in output so they are kept for next regenerate or display
        output_payload: dict = {"chapters": chapters}
        if extra_points:
            output_payload["extra_points"] = extra_points
        framework_step.output_snapshot = json.dumps(output_payload, ensure_ascii=False)
        framework_step.status = "waiting_user"
        framework_step.error_message = None
        db.commit()
        logger.info(
            "run_framework: task_id=%s framework completed, chapters=%s",
            task_id,
            len(chapters),
        )
    except Exception as e:
        logger.exception("run_framework: task_id=%s failed", task_id)
        try:
            db.rollback()
            err_msg = str(e)[:ERROR_MESSAGE_MAX_LEN]
            _set_framework_failed(db, task_id, err_msg)
        except Exception:
            db.rollback()
            raise
    finally:
        db.close()
