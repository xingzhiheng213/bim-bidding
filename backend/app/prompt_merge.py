"""Runtime merge of PromptProfile semantic overrides with built-in defaults (Phase B)."""

from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import PromptProfile, Task
from app.semantic_slots import SEMANTIC_SLOT_KEYS, get_default_semantic_overrides


def merge_semantic_overrides(stored: dict | None) -> dict[str, str]:
    """Merge profile JSON overrides onto defaults; drop keys not in SEMANTIC_SLOT_KEYS.

    Non-empty string values in ``stored`` override the corresponding slot; whitespace-only
    strings are ignored (slot falls back to default in pick/build paths).
    """
    base = get_default_semantic_overrides()
    if not stored:
        return base
    out = dict(base)
    for k, v in stored.items():
        if k not in SEMANTIC_SLOT_KEYS:
            continue
        if isinstance(v, str) and v.strip():
            out[k] = v
    return out


def load_merged_semantic_for_task(db: Session, task_id: int) -> dict[str, str]:
    """Load Task.profile_id; if set and profile exists, merge overrides; else defaults only."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task or not task.profile_id:
        return merge_semantic_overrides(None)
    profile = (
        db.query(PromptProfile)
        .filter(
            PromptProfile.id == task.profile_id,
            or_(
                PromptProfile.is_builtin.is_(True),
                (
                    (PromptProfile.tenant_id == task.tenant_id)
                    & (PromptProfile.user_id == task.user_id)
                ),
            ),
        )
        .first()
    )
    if not profile:
        return merge_semantic_overrides(None)
    return merge_semantic_overrides(profile.semantic_overrides)
