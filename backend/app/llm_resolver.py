"""Resolve (provider, model) for a step: use env config (DeepSeek as primary model)."""
from app import config

_STEP_ENV_MAP = {
    "analyze": (config.ANALYZE_LLM_PROVIDER, config.ANALYZE_LLM_MODEL),
    "params": (config.PARAMS_LLM_PROVIDER, config.PARAMS_LLM_MODEL),
    "framework": (config.FRAMEWORK_LLM_PROVIDER, config.FRAMEWORK_LLM_MODEL),
    "chapters": (config.CHAPTER_LLM_PROVIDER, config.CHAPTER_LLM_MODEL),
    "review": (config.CHAPTER_LLM_PROVIDER, config.CHAPTER_LLM_MODEL),
    "prompt_profile_generate": (
        config.PROMPT_PROFILE_GEN_LLM_PROVIDER,
        config.PROMPT_PROFILE_GEN_LLM_MODEL,
    ),
}


def get_llm_for_step(step_key: str) -> tuple[str, str]:
    """Return (provider, model) for the given step. Uses env config only (e.g. DeepSeek)."""
    return _STEP_ENV_MAP.get(step_key, (config.CHAPTER_LLM_PROVIDER, config.CHAPTER_LLM_MODEL))
