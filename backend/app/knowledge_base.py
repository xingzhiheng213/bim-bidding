"""Pluggable knowledge base search for framework and chapter generation.

Abstract interface: search(query, top_k) -> list[str].
Adapters: thinkdoc (ThinkDoc/doc.bluedigit.ai); none = return [].
"""
import logging
from typing import Callable

import httpx

from app import config

logger = logging.getLogger(__name__)

# Type for search implementation: (query, top_k) -> list[str]
SearchFn = Callable[[str, int], list[str]]


def _search_none(_query: str, _top_k: int) -> list[str]:
    """No retrieval; return empty list."""
    return []


def _search_thinkdoc(query: str, top_k: int = 10) -> list[str]:
    """ThinkDoc adapter: POST /api/retrieve, parse response to list of text chunks."""
    if not config.THINKDOC_API_KEY or not config.get_thinkdoc_kb_ids():
        logger.info("ThinkDoc not configured: missing THINKDOC_API_KEY or THINKDOC_KB_IDS")
        return []
    url = f"{config.THINKDOC_API_URL}/api/retrieve"
    payload = {
        "query": query,
        "kb_ids": config.get_thinkdoc_kb_ids(),
        "retrieval_setting": {"top_k": top_k, "score_threshold": 0.5},
    }
    headers = {"Authorization": f"Bearer {config.THINKDOC_API_KEY}", "Content-Type": "application/json"}
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        logger.warning("ThinkDoc retrieve HTTP error: %s %s", e.response.status_code, e.response.text[:200])
        return []
    except Exception as e:
        logger.warning("ThinkDoc retrieve failed: %s", e)
        return []

    # Parse response: ThinkDoc returns { "records": [ { "text": "...", "md_text": "..." } ] }
    # https://doc.bluedigit.ai/docs/developer-guide/http-api
    chunks: list[str] = []
    if isinstance(data, dict):
        raw_list = (
            data.get("records")  # ThinkDoc 官方格式
            or data.get("data")
            or data.get("chunks")
            or data.get("results")
        )
        if isinstance(raw_list, list):
            for item in raw_list:
                if isinstance(item, str):
                    chunks.append(item)
                elif isinstance(item, dict):
                    text = (
                        item.get("text")
                        or item.get("md_text")  # ThinkDoc 可选 Markdown 内容
                        or item.get("content")
                        or item.get("body")
                    )
                    if isinstance(text, str) and text.strip():
                        chunks.append(text.strip())
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, str):
                chunks.append(item)
            elif isinstance(item, dict):
                text = (
                    item.get("text")
                    or item.get("md_text")
                    or item.get("content")
                    or item.get("body")
                )
                if isinstance(text, str) and text.strip():
                    chunks.append(text.strip())
    return chunks


def get_search_fn() -> SearchFn:
    """Return the search implementation based on KNOWLEDGE_BASE_TYPE."""
    if config.KNOWLEDGE_BASE_TYPE == "thinkdoc":
        return _search_thinkdoc
    return _search_none


def search(query: str, top_k: int = 10) -> list[str]:
    """Search knowledge base; returns list of text chunks. Never raises; returns [] on misconfig or error."""
    return get_search_fn()(query, top_k)
