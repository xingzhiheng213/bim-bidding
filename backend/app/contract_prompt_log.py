"""Optional runtime logging of contract-layer prompt text (LOG_CONTRACT_PROMPTS=1).

Semantic slots (Profile overrides) are not logged as contract; user templates and
fixed output specs from prompts.py / prompt_catalog are.

When LOG_CONTRACT_PROMPTS_FILE is set (default: data/logs/contract_prompts.log under
backend/), the same records are also appended to that file.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

from app import config
from app.prompts import (
    ANALYZE_CONTEXT_PLACEHOLDER,
    PARAMS_CONTEXT_PLACEHOLDER,
    REVIEW_OUTPUT_FORMAT_SPEC,
)

_BACKEND_ROOT = Path(__file__).resolve().parent.parent

logger = logging.getLogger("bim.contract_prompt")

_file_handler_lock = threading.Lock()
_file_handler_installed = False


def _ensure_contract_file_handler() -> None:
    """Attach a FileHandler once per process when file path is configured."""
    global _file_handler_installed
    if not config.LOG_CONTRACT_PROMPTS:
        return
    raw = (config.LOG_CONTRACT_PROMPTS_FILE or "").strip()
    if not raw:
        return
    with _file_handler_lock:
        if _file_handler_installed:
            return
        path = Path(raw)
        if not path.is_absolute():
            path = _BACKEND_ROOT / path
        path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(path, encoding="utf-8")
        fh.setLevel(logging.INFO)
        fh.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        )
        logger.addHandler(fh)
        logger.setLevel(logging.INFO)
        _file_handler_installed = True


def _truncate(s: str, max_chars: int) -> str:
    if max_chars <= 0 or len(s) <= max_chars:
        return s
    return s[:max_chars] + f"\n… [truncated, total_len={len(s)}]"


def _content_for_role(messages: list[dict[str, Any]], role: str) -> str:
    for m in messages:
        if m.get("role") == role:
            c = m.get("content")
            return c if isinstance(c, str) else ""
    return ""


def _params_snapshot_contract_excerpt() -> str:
    """Short contract doc from prompt catalog (params JSON keys)."""
    try:
        from app.prompt_catalog import get_prompt_catalog

        cat = get_prompt_catalog()
        for item in cat.contract_items:
            if item.id == "contract.params_snapshot":
                return item.content
    except Exception:
        pass
    return ""


def log_contract_prompts(
    *,
    prompt_step: str | None,
    messages: list[dict[str, Any]],
    task_id: int | None,
) -> None:
    """Log contract-layer text for inspection. Never raises."""
    if not config.LOG_CONTRACT_PROMPTS:
        return
    if not prompt_step:
        return

    try:
        _ensure_contract_file_handler()
    except Exception:
        logging.getLogger(__name__).debug("contract file handler setup failed", exc_info=True)

    max_c = config.LOG_CONTRACT_MAX_CHARS
    prefix = f"[task_id={task_id}] [prompt_step={prompt_step}]"

    try:
        if prompt_step in ("framework", "framework_points", "chapter_outline", "chapter_content", "chapter_regenerate"):
            user_txt = _content_for_role(messages, "user")
            logger.info(
                "%s contract user message (fixed user template + injected data):\n%s",
                prefix,
                _truncate(user_txt, max_c),
            )
            return

        if prompt_step == "review":
            user_txt = _content_for_role(messages, "user")
            logger.info(
                "%s contract: REVIEW_OUTPUT_FORMAT_SPEC (fixed JSON array spec):\n%s",
                prefix,
                _truncate(REVIEW_OUTPUT_FORMAT_SPEC.strip(), max_c),
            )
            logger.info(
                "%s contract user message (REVIEW_USER_TEMPLATE + injected fields):\n%s",
                prefix,
                _truncate(user_txt, max_c),
            )
            return

        if prompt_step == "analyze":
            logger.info(
                "%s contract: literal placeholder ANALYZE_CONTEXT_PLACEHOLDER=%r "
                "(runtime system/user bodies are semantic slots, not contract text).",
                prefix,
                ANALYZE_CONTEXT_PLACEHOLDER,
            )
            return

        if prompt_step == "params":
            doc = _params_snapshot_contract_excerpt()
            logger.info(
                "%s contract: PARAMS_CONTEXT_PLACEHOLDER=%r; persisted JSON key rules (catalog):\n%s",
                prefix,
                PARAMS_CONTEXT_PLACEHOLDER,
                _truncate(doc, max_c),
            )
            logger.info(
                "%s note: params system/user prompts are semantic slots; not logged as contract.",
                prefix,
            )
            return

        if prompt_step == "prompt_profile_gen":
            logger.info(
                "%s contract: pipeline contract layer N/A (meta prompt for Profile slot generation).",
                prefix,
            )
            return

        logger.info(
            "%s unknown prompt_step; no contract split defined.",
            prefix,
        )
    except Exception as e:  # noqa: BLE001 — must never break LLM calls
        logger.debug("contract prompt log failed: %s", e, exc_info=True)
