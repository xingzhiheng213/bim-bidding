"""Shared utilities for step management and Celery dispatching.

Extracted from routers/tasks.py to eliminate repeated boilerplate across
all step-trigger endpoints and to centralise pure domain helpers.
"""
from __future__ import annotations

import json
from typing import Any, Callable

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Task, TaskStep


# ---------------------------------------------------------------------------
# Task / Step lookup helpers
# ---------------------------------------------------------------------------

def require_task(task_id: int, db: Session) -> Task:
    """Return the Task or raise HTTP 404."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


def get_or_create_step(task_id: int, step_key: str, db: Session) -> TaskStep:
    """Return an existing TaskStep or insert a pending one.

    Flushes (to populate the PK) but does **not** commit — callers decide
    when to commit.
    """
    step = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.step_key == step_key)
        .first()
    )
    if not step:
        step = TaskStep(task_id=task_id, step_key=step_key, status="pending")
        db.add(step)
        db.flush()
    return step


def require_step_completed(
    task_id: int,
    step_key: str,
    db: Session,
    error_msg: str,
) -> TaskStep:
    """Return TaskStep if completed with non-empty output_snapshot, else raise HTTP 400."""
    step = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.step_key == step_key)
        .first()
    )
    if not step or step.status != "completed" or not step.output_snapshot:
        raise HTTPException(status_code=400, detail=error_msg)
    return step


# ---------------------------------------------------------------------------
# Celery dispatch helper
# ---------------------------------------------------------------------------

def dispatch_celery_step(
    step: TaskStep,
    celery_fn: Any,
    db: Session,
    *celery_args: Any,
    **celery_kwargs: Any,
) -> None:
    """Mark *step* as running, commit, launch Celery task, store task ID, commit.

    Any ``output_snapshot`` mutations applied to *step* **before** this call
    are included in the first ``db.commit()``.
    """
    step.status = "running"
    step.error_message = None
    db.commit()
    result = celery_fn.delay(*celery_args, **celery_kwargs)
    step.celery_task_id = result.id
    db.commit()


# ---------------------------------------------------------------------------
# Compare-meta helpers  (used by task list + compare-meta endpoint)
# ---------------------------------------------------------------------------

def compute_compare_meta_from_steps(
    framework_step: TaskStep | None,
    chapters_step: TaskStep | None,
) -> dict:
    """Compute compare metadata from step objects (no DB I/O).

    Returns a dict with keys:
    - ``has_any``: bool
    - ``framework_has_diff``: bool
    - ``chapter_numbers``: list[int] — chapters that have before/after snapshots
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


def compute_compare_meta_for_task(task_id: int, db: Session) -> dict:
    """Fetch framework/chapters steps for one task then delegate to pure helper."""
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
    return compute_compare_meta_from_steps(framework_step, chapters_step)


# ---------------------------------------------------------------------------
# Framework diff text helper (pure domain logic, no DB I/O)
# ---------------------------------------------------------------------------

def framework_snapshot_to_text(snapshot_json: str | None) -> str:
    """Render a framework ``output_snapshot`` JSON blob as line-oriented text.

    Used by the diff endpoint to produce comparable strings for ``compute_diff``.
    """
    if not snapshot_json:
        return ""
    try:
        data = json.loads(snapshot_json)
        chapters = data.get("chapters") or []
        lines: list[str] = []
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
