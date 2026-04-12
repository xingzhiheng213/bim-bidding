"""Validate semantic_overrides on PromptProfile create/update (Phase B)."""

from __future__ import annotations

import json

from app.semantic_slots import SEMANTIC_SLOT_KEYS

# Per-slot cap (~64 KiB); total JSON string cap to bound storage
MAX_SEMANTIC_VALUE_CHARS = 65536
MAX_SEMANTIC_JSON_CHARS = 512 * 1024


def validate_semantic_overrides_for_save(raw: object | None) -> dict[str, str] | None:
    """Normalize overrides for persistence. ``None`` / missing means store ``None``.

    Raises ``ValueError`` with a user-facing message on invalid keys or sizes.
    """
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("semantic_overrides 必须是对象")
    out: dict[str, str] = {}
    for k, v in raw.items():
        if k not in SEMANTIC_SLOT_KEYS:
            raise ValueError(f"不允许的语义槽位键: {k!r}")
        if v is None:
            continue
        if not isinstance(v, str):
            raise ValueError(f"槽位 {k!r} 的值必须是字符串")
        if len(v) > MAX_SEMANTIC_VALUE_CHARS:
            raise ValueError(f"槽位 {k!r} 超过单槽长度上限 ({MAX_SEMANTIC_VALUE_CHARS} 字符)")
        out[k] = v
    payload = json.dumps(out, ensure_ascii=False)
    if len(payload) > MAX_SEMANTIC_JSON_CHARS:
        raise ValueError(f"semantic_overrides 序列化后超过总长度上限 ({MAX_SEMANTIC_JSON_CHARS} 字符)")
    return out if out else None
