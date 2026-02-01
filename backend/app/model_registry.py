"""Model name -> provider mapping; used to infer provider from model name (e.g. glm-4.7 -> zhipu)."""

# model_id -> provider (used for API key / base_url lookup)
MODEL_TO_PROVIDER: dict[str, str] = {
    # DeepSeek
    "deepseek-chat": "deepseek",
    "deepseek-reasoner": "deepseek",
    "deepseek-v3": "deepseek",
    # 智谱 GLM (https://docs.bigmodel.cn)
    "glm-4.7": "zhipu",
    "glm-4.6": "zhipu",
    "glm-4-plus": "zhipu",
    "glm-4-flash": "zhipu",
    "glm-4-long": "zhipu",
    "glm-4-air": "zhipu",
    "glm-4-airx": "zhipu",
}

# Display order and label for settings UI (id, label, provider)
SUPPORTED_MODELS: list[tuple[str, str, str]] = [
    ("deepseek-chat", "DeepSeek Chat", "deepseek"),
    ("deepseek-reasoner", "DeepSeek Reasoner", "deepseek"),
    ("deepseek-v3", "DeepSeek V3", "deepseek"),
    ("glm-4.7", "GLM-4.7", "zhipu"),
    ("glm-4.6", "GLM-4.6", "zhipu"),
    ("glm-4-plus", "GLM-4 Plus", "zhipu"),
    ("glm-4-flash", "GLM-4 Flash", "zhipu"),
    ("glm-4-long", "GLM-4 Long", "zhipu"),
    ("glm-4-air", "GLM-4 Air", "zhipu"),
    ("glm-4-airx", "GLM-4 AirX", "zhipu"),
]


def get_provider_for_model(model_id: str) -> str | None:
    """Return provider for model id (e.g. glm-4.7 -> zhipu); None if unknown."""
    return MODEL_TO_PROVIDER.get(model_id.strip().lower() if model_id else "")


def list_supported_models() -> list[dict]:
    """Return list of {id, name, provider} for settings UI."""
    return [
        {"id": mid, "name": name, "provider": prov}
        for mid, name, prov in SUPPORTED_MODELS
    ]
