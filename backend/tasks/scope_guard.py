"""Worker-side task ownership guard for tenant/user scoped Celery messages."""

from __future__ import annotations

import logging
from collections.abc import Callable

from app.models import Task
from sqlalchemy.orm import Session


def validate_task_scope(
    db: Session,
    task_id: int,
    tenant_id: str | None,
    user_id: str | None,
    *,
    logger: logging.Logger,
    task_name: str,
    on_failed: Callable[[str], None],
) -> Task | None:
    """Validate Celery message scope against DB owner before worker execution."""
    if not tenant_id or not user_id:
        logger.warning(
            "%s: task_id=%s missing tenant/user in celery message",
            task_name,
            task_id,
        )
        on_failed("任务归属校验失败")
        return None

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        logger.warning("%s: task_id=%s not found", task_name, task_id)
        return None

    if task.tenant_id != tenant_id or task.user_id != user_id:
        logger.warning(
            "%s: task_id=%s owner mismatch message=(%s,%s) db=(%s,%s)",
            task_name,
            task_id,
            tenant_id,
            user_id,
            task.tenant_id,
            task.user_id,
        )
        on_failed("任务归属校验失败")
        return None

    return task
