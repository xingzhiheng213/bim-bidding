"""Params snapshot: key_requirements (canonical) vs legacy bim_requirements."""

REQUIREMENTS_JSON_KEY = "key_requirements"
LEGACY_REQUIREMENTS_JSON_KEY = "bim_requirements"


def coalesce_requirements_from_llm_raw(raw: dict) -> list[str]:
    """Build list to persist as key_requirements.

    If key_requirements is present in LLM output (even []), it wins over bim_requirements.
    If absent, fall back to bim_requirements for backward compatibility with old prompts.
    """
    if REQUIREMENTS_JSON_KEY in raw:
        lst = raw[REQUIREMENTS_JSON_KEY]
        return [str(x) for x in lst] if isinstance(lst, list) else []
    lst = raw.get(LEGACY_REQUIREMENTS_JSON_KEY)
    return [str(x) for x in lst] if isinstance(lst, list) else []


def extract_requirements_list(params_out: dict) -> list[str]:
    """Read requirements from a params step output dict (new or legacy snapshot)."""
    lst = params_out.get(REQUIREMENTS_JSON_KEY)
    if isinstance(lst, list):
        return [str(x) for x in lst]
    legacy = params_out.get(LEGACY_REQUIREMENTS_JSON_KEY)
    if isinstance(legacy, list):
        return [str(x) for x in legacy]
    return []


def params_snapshot_has_requirements_list(params_out: dict) -> bool:
    """True if snapshot has a list-typed requirements field (allows empty list)."""
    return isinstance(params_out.get(REQUIREMENTS_JSON_KEY), list) or isinstance(
        params_out.get(LEGACY_REQUIREMENTS_JSON_KEY), list
    )
