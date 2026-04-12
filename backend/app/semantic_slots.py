"""Single source of truth for user-overridable semantic prompt slots (Phase A).

Contract-layer strings stay in code and must not be stored in profile overrides;
see CONTRACT_PROMPT_ATTRS and docs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import app.prompts as prompts


@dataclass(frozen=True)
class SemanticSlotDef:
    """One editable semantic fragment aligned with prompt_catalog semantic_items."""

    slot_key: str
    step: str
    title: str
    source_attr: str


# Order matches get_prompt_catalog().semantic_items.
SEMANTIC_SLOTS: tuple[SemanticSlotDef, ...] = (
    SemanticSlotDef("analyze_system", "analyze", "分析 · system", "ANALYZE_SYSTEM"),
    SemanticSlotDef("analyze_user", "analyze", "分析 · user 模板", "ANALYZE_USER_TEMPLATE"),
    SemanticSlotDef("params_system", "params", "参数提取 · system", "PARAMS_SYSTEM"),
    SemanticSlotDef("params_user", "params", "参数提取 · user 模板", "PARAMS_USER_TEMPLATE"),
    SemanticSlotDef("framework_system", "framework", "框架生成 · system（完整生成）", "FRAMEWORK_SYSTEM"),
    SemanticSlotDef(
        "framework_system_points",
        "framework",
        "框架生成 · system（仅用户要点）",
        "FRAMEWORK_SYSTEM_WITH_USER_POINTS",
    ),
    SemanticSlotDef("chapter_outline_system", "chapter_outline", "章节小节大纲 · system", "CHAPTER_OUTLINE_SYSTEM"),
    SemanticSlotDef("chapter_content_system", "chapter_content", "章节正文 · system", "CHAPTER_CONTENT_SYSTEM"),
    SemanticSlotDef(
        "chapter_regenerate_system",
        "chapter_regenerate",
        "章节重生成 · system",
        "CHAPTER_REGENERATE_SYSTEM",
    ),
    SemanticSlotDef(
        "review_system",
        "review",
        "校审 · system（人设示例；维度与输出格式见契约层）",
        "REVIEW_SYSTEM_SEMANTIC",
    ),
)

SEMANTIC_SLOT_KEYS: tuple[str, ...] = tuple(s.slot_key for s in SEMANTIC_SLOTS)

# Module-level prompt constants that are contract/frozen (not semantic slots). For Phase B validation.
CONTRACT_PROMPT_ATTRS: Final[frozenset[str]] = frozenset(
    {
        "PARAMS_CONTEXT_PLACEHOLDER",
        "FRAMEWORK_USER_TEMPLATE",
        "FRAMEWORK_USER_EXTRA_POINTS_TEMPLATE",
        "FRAMEWORK_ANALYZE_PLACEHOLDER",
        "FRAMEWORK_REQUIREMENTS_PLACEHOLDER",
        "FRAMEWORK_SCORING_PLACEHOLDER",
        "FRAMEWORK_CONTEXT_PLACEHOLDER",
        "CHAPTER_OUTLINE_USER_TEMPLATE",
        "CHAPTER_CONTENT_USER_TEMPLATE",
        "CHAPTER_REGENERATE_USER_TEMPLATE",
        "REVIEW_USER_TEMPLATE",
        "REVIEW_OUTPUT_FORMAT_SPEC",
        "REVIEW_TYPE_VALUES",
        "REVIEW_CHAPTER_FULL_NAME",
        "REVIEW_CHAPTER_CONTENT",
        "REVIEW_ANALYZE_EXCERPT",
        "REVIEW_PARAMS_CONTEXT_PLACEHOLDER",
        "REVIEW_KB_CONTEXT",
        "REVIEW_SYSTEM",  # concatenation; use REVIEW_OUTPUT_FORMAT_SPEC + REVIEW_SYSTEM_SEMANTIC separately
        "ANALYZE_CONTEXT_PLACEHOLDER",
    }
)


def catalog_id_for_slot(slot_key: str) -> str:
    """prompt_catalog semantic item id: semantic.{slot_key}."""
    return f"semantic.{slot_key}"


def get_default_semantic_overrides() -> dict[str, str]:
    """Current built-in semantic texts from app.prompts (BIM 技术标 default)."""
    out: dict[str, str] = {}
    for slot in SEMANTIC_SLOTS:
        raw = getattr(prompts, slot.source_attr)
        if not isinstance(raw, str):
            raise TypeError(f"prompts.{slot.source_attr} must be str, got {type(raw)}")
        out[slot.slot_key] = raw
    return out


def pick_semantic_slot_text(slot_key: str, semantic_overrides: dict[str, str] | None) -> str:
    """Resolve one slot: non-empty override wins; else built-in from prompts."""
    for slot in SEMANTIC_SLOTS:
        if slot.slot_key != slot_key:
            continue
        default = getattr(prompts, slot.source_attr)
        if semantic_overrides is None:
            return default
        v = semantic_overrides.get(slot_key)
        if isinstance(v, str) and v.strip():
            return v
        return default
    raise KeyError(f"unknown semantic slot_key: {slot_key!r}")


def assert_semantic_catalog_matches_slots() -> None:
    """Runtime check: prompt_catalog semantic_items align with SEMANTIC_SLOTS."""
    from app.prompt_catalog import get_prompt_catalog

    cat = get_prompt_catalog()
    items = cat.semantic_items
    if len(items) != len(SEMANTIC_SLOTS):
        raise AssertionError(
            f"semantic_items count {len(items)} != SEMANTIC_SLOTS {len(SEMANTIC_SLOTS)}"
        )
    for slot, item in zip(SEMANTIC_SLOTS, items, strict=True):
        expected_id = catalog_id_for_slot(slot.slot_key)
        if item.id != expected_id:
            raise AssertionError(f"catalog id {item.id!r} != expected {expected_id!r}")
        if item.step != slot.step:
            raise AssertionError(f"catalog step {item.step!r} != slot {slot.step!r}")
        if item.title != slot.title:
            raise AssertionError(f"catalog title mismatch for {slot.slot_key}")
