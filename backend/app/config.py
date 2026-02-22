"""Load REDIS_URL, DATABASE_URL, UPLOAD_DIR from environment."""
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from backend directory when running from backend/
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@localhost:5432/bim_bidding",
)

# Upload: dir for stored files (relative to backend/ or absolute)
_upload_dir_raw: str = os.getenv("UPLOAD_DIR", "data/uploads")
UPLOAD_DIR: Path = (
    Path(_upload_dir_raw).resolve()
    if Path(_upload_dir_raw).is_absolute()
    else Path(__file__).resolve().parent.parent / _upload_dir_raw
)
MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
MAX_UPLOAD_SIZE_BYTES: int = MAX_UPLOAD_SIZE_MB * 1024 * 1024

# Export: dir for generated DOCX (stage 4.3; optional, for caching)
_export_dir_raw: str = os.getenv("EXPORT_DIR", "data/exports")
EXPORT_DIR: Path = (
    Path(_export_dir_raw).resolve()
    if Path(_export_dir_raw).is_absolute()
    else Path(__file__).resolve().parent.parent / _export_dir_raw
)

# LLM: API keys and base URLs (env only in 2.1; settings table in stage 5)
DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL: str = os.getenv(
    "DEEPSEEK_BASE_URL", "https://api.deepseek.com"
).rstrip("/")

# LLM HTTP timeout (seconds): read timeout for long analysis/framework responses
LLM_TIMEOUT_CONNECT: float = float(os.getenv("LLM_TIMEOUT_CONNECT", "10"))
LLM_TIMEOUT_READ: float = float(os.getenv("LLM_TIMEOUT_READ", "180"))
# LLM max completion tokens (output length). Default 8K; can be overridden via env.
LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "8192"))

# Analyze step (stage 2.2): default deepseek / deepseek-chat
ANALYZE_LLM_PROVIDER: str = os.getenv("ANALYZE_LLM_PROVIDER", "deepseek")
ANALYZE_LLM_MODEL: str = os.getenv("ANALYZE_LLM_MODEL", "deepseek-chat")

# Params step (stage 2.3): default deepseek / deepseek-chat, temperature 0.1
PARAMS_LLM_PROVIDER: str = os.getenv("PARAMS_LLM_PROVIDER", "deepseek")
PARAMS_LLM_MODEL: str = os.getenv("PARAMS_LLM_MODEL", "deepseek-chat")

# Framework step (stage 2.4): default deepseek / deepseek-chat, temperature 0.4
FRAMEWORK_LLM_PROVIDER: str = os.getenv("FRAMEWORK_LLM_PROVIDER", "deepseek")
FRAMEWORK_LLM_MODEL: str = os.getenv("FRAMEWORK_LLM_MODEL", "deepseek-chat")

# Chapter generation (stage 4.1): default same as framework; long read timeout
CHAPTER_LLM_PROVIDER: str = os.getenv("CHAPTER_LLM_PROVIDER", "deepseek")
CHAPTER_LLM_MODEL: str = os.getenv("CHAPTER_LLM_MODEL", "deepseek-chat")

# Chapter outline/content: max chars of "招标要求参考" (stage 2.1 truncation)
CHAPTER_OUTLINE_ANALYZE_MAX_LEN: int = int(os.getenv("CHAPTER_OUTLINE_ANALYZE_MAX_LEN", "8000"))
CHAPTER_CONTENT_ANALYZE_MAX_LEN: int = int(os.getenv("CHAPTER_CONTENT_ANALYZE_MAX_LEN", "6000"))

# Knowledge base (stage 2.4): thinkdoc | none; none or unset = return empty list
# If THINKDOC_API_KEY and THINKDOC_KB_IDS are set but KNOWLEDGE_BASE_TYPE is not, default to thinkdoc
THINKDOC_API_URL: str = os.getenv("THINKDOC_API_URL", "https://doc.bluedigit.ai").rstrip("/")
THINKDOC_API_KEY: str = os.getenv("THINKDOC_API_KEY", "")
# Single ID or comma-separated IDs, e.g. 69725828f7f898efad71e93c
THINKDOC_KB_IDS_RAW: str = os.getenv("THINKDOC_KB_IDS", "")
# RAGFlow: local or remote, e.g. http://localhost:9380
RAGFLOW_API_URL: str = os.getenv("RAGFLOW_API_URL", "").strip().rstrip("/")
RAGFLOW_API_KEY: str = os.getenv("RAGFLOW_API_KEY", "")
RAGFLOW_DATASET_IDS_RAW: str = os.getenv("RAGFLOW_DATASET_IDS", "")
_kb_type: str = os.getenv("KNOWLEDGE_BASE_TYPE", "").strip().lower()
if _kb_type:
    KNOWLEDGE_BASE_TYPE: str = _kb_type
elif THINKDOC_API_KEY and THINKDOC_KB_IDS_RAW.strip():
    KNOWLEDGE_BASE_TYPE = "thinkdoc"
elif RAGFLOW_API_KEY and RAGFLOW_DATASET_IDS_RAW.strip():
    KNOWLEDGE_BASE_TYPE = "ragflow"
else:
    KNOWLEDGE_BASE_TYPE = "none"


def get_thinkdoc_kb_ids() -> list[str]:
    """Return list of knowledge base IDs from THINKDOC_KB_IDS (comma-separated)."""
    if not THINKDOC_KB_IDS_RAW.strip():
        return []
    return [x.strip() for x in THINKDOC_KB_IDS_RAW.split(",") if x.strip()]


def get_ragflow_dataset_ids() -> list[str]:
    """Return list of dataset IDs from RAGFLOW_DATASET_IDS (comma-separated)."""
    if not RAGFLOW_DATASET_IDS_RAW.strip():
        return []
    return [x.strip() for x in RAGFLOW_DATASET_IDS_RAW.split(",") if x.strip()]


def get_llm_api_key(provider: str) -> str | None:
    """Return API key for provider (deepseek); from DB first, then env; None if not set."""
    from app.settings_store import get_api_key_from_db
    key = get_api_key_from_db(provider)
    if key:
        return key
    if provider == "deepseek":
        return DEEPSEEK_API_KEY or None
    return None


def get_llm_base_url(provider: str) -> str:
    """Return base URL for provider (no trailing slash); from DB first, then env."""
    from app.settings_store import get_base_url_from_db
    url = get_base_url_from_db(provider)
    if url:
        return url.rstrip("/")
    if provider == "deepseek":
        return DEEPSEEK_BASE_URL.rstrip("/")
    raise ValueError(f"Unknown provider: {provider}")
