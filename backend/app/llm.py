"""LLM call layer: OpenAI-compatible chat completions for DeepSeek / Zhipu."""
import httpx

from app import config


def _default_base_url(provider: str) -> str:
    """Return base URL for provider (DB first, then env)."""
    return config.get_llm_base_url(provider)


def call_llm(
    provider: str,
    model: str,
    messages: list[dict],
    temperature: float = 0.7,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
) -> str:
    """Call LLM via OpenAI-compatible chat completions; return content or raise.

    Args:
        provider: "deepseek" or "zhipu" (used for default base_url and key lookup).
        model: Model name (e.g. deepseek-chat, glm-4-flash).
        messages: OpenAI format, e.g. [{"role": "user", "content": "..."}].
        temperature: 0..1.
        api_key: If None, taken from config.get_llm_api_key(provider).
        base_url: If None, taken from config by provider (no trailing slash).

    Returns:
        choices[0].message.content as str.

    Raises:
        ValueError: Missing API key or unknown provider.
        httpx.HTTPStatusError: Non-2xx response.
        KeyError/IndexError: Unexpected response shape (re-raised or wrapped).
    """
    key = api_key or config.get_llm_api_key(provider)
    if not key:
        raise ValueError(f"请在设置中配置 {provider} API Key")
    url_base = (base_url or _default_base_url(provider)).rstrip("/")
    url = f"{url_base}/chat/completions"

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    timeout = httpx.Timeout(
        connect=config.LLM_TIMEOUT_CONNECT,
        read=config.LLM_TIMEOUT_READ,
        write=config.LLM_TIMEOUT_READ,
        pool=config.LLM_TIMEOUT_CONNECT,
    )
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise ValueError(f"Unexpected LLM response shape: {data}") from e
