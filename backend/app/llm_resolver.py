"""Resolve (provider, model) for a step: from DB model config + model->provider mapping, fallback to env."""
from app import config
from app.model_registry import get_provider_for_model
from app.settings_store import get_model_config, STEP_KEYS

_STEP_ENV_MAP = {
    "analyze": (config.ANALYZE_LLM_PROVIDER, config.ANALYZE_LLM_MODEL),
    "params": (config.PARAMS_LLM_PROVIDER, config.PARAMS_LLM_MODEL),
    "framework": (config.FRAMEWORK_LLM_PROVIDER, config.FRAMEWORK_LLM_MODEL),
    "chapters": (config.CHAPTER_LLM_PROVIDER, config.CHAPTER_LLM_MODEL),
}


def get_llm_for_step(step_key: str) -> tuple[str, str]:
    """Return (provider, model) for the given step.

    Uses DB model config: step-specific model if set, else default_model.
    Resolves provider from model name via model registry.
    Falls back to env (ANALYZE_LLM_PROVIDER/MODEL etc.) if DB empty or model unknown.
    """
    if step_key not in STEP_KEYS:
        raise ValueError(f"Unknown step_key: {step_key}")

    cfg = get_model_config()
    step_field = f"{step_key}_model"
    step_model = cfg.get(step_field)
    if not step_model:
        step_model = cfg.get("default_model") or "deepseek-chat"

    provider = get_provider_for_model(step_model)
    if provider:
        return (provider, step_model)

    # Fallback to env
    env_provider, env_model = _STEP_ENV_MAP.get(step_key, ("deepseek", "deepseek-chat"))
    return (env_provider, env_model)
