"""Encrypt/decrypt and DB read/write for LLM API keys (stage 5.1)."""
import base64
import logging
import os
from datetime import datetime

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import LlmSetting, PlatformLlmConfig

logger = logging.getLogger(__name__)

SUPPORTED_PROVIDERS = ("deepseek", "zhipu")

# Fixed dev placeholder key so FastAPI and Celery workers decrypt the same stored API keys when SETTINGS_SECRET_KEY is unset. Must decode to 32 bytes.
_DEV_PLACEHOLDER_KEY = base64.urlsafe_b64encode(b"dev-placeholder-key-32bytes!!!!!")

# Fernet key: 32 bytes base64. If not set, use fixed dev placeholder so all processes (FastAPI + Celery) share the same key.
_SETTINGS_SECRET_KEY = os.getenv("SETTINGS_SECRET_KEY", "").strip()
if _SETTINGS_SECRET_KEY:
    try:
        _fernet = Fernet(_SETTINGS_SECRET_KEY.encode() if isinstance(_SETTINGS_SECRET_KEY, str) else _SETTINGS_SECRET_KEY)
    except Exception as e:
        logger.warning("SETTINGS_SECRET_KEY invalid, using placeholder: %s", e)
        _fernet = Fernet(_DEV_PLACEHOLDER_KEY)
else:
    logger.warning("SETTINGS_SECRET_KEY not set; using dev-only placeholder key (same in all processes)")
    _fernet = Fernet(_DEV_PLACEHOLDER_KEY)


def _get_fernet() -> Fernet:
    return _fernet


def encrypt_api_key(plain: str) -> str:
    """Encrypt plain API key to base64 string for storage."""
    return _get_fernet().encrypt(plain.encode("utf-8")).decode("ascii")


def decrypt_api_key(cipher: str) -> str | None:
    """Decrypt stored cipher to plain key; None on failure."""
    try:
        return _get_fernet().decrypt(cipher.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        return None


def mask_api_key(plain: str) -> str:
    """Return masked key e.g. sk-***xyz (first 2 + *** + last 3)."""
    if len(plain) <= 5:
        return "***"
    return plain[:2] + "***" + plain[-3:]


def get_api_key_from_db(provider: str) -> str | None:
    """Return decrypted API key for provider from DB, or None."""
    if provider not in SUPPORTED_PROVIDERS:
        return None
    db: Session = SessionLocal()
    try:
        row = db.query(LlmSetting).filter(LlmSetting.provider == provider).first()
        if not row or not row.encrypted_api_key:
            return None
        return decrypt_api_key(row.encrypted_api_key)
    finally:
        db.close()


def get_base_url_from_db(provider: str) -> str | None:
    """Return base_url for provider from DB, or None (use env default)."""
    if provider not in SUPPORTED_PROVIDERS:
        return None
    db: Session = SessionLocal()
    try:
        row = db.query(LlmSetting).filter(LlmSetting.provider == provider).first()
        if not row or not row.base_url:
            return None
        return row.base_url.rstrip("/") or None
    finally:
        db.close()


def set_api_key_in_db(provider: str, api_key: str, base_url: str | None = None) -> None:
    """Encrypt and upsert API key for provider; optionally set base_url (empty string = clear)."""
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f"Unsupported provider: {provider}")
    encrypted = encrypt_api_key(api_key)
    db: Session = SessionLocal()
    try:
        row = db.query(LlmSetting).filter(LlmSetting.provider == provider).first()
        if row:
            row.encrypted_api_key = encrypted
            row.updated_at = datetime.utcnow()
            if base_url is not None:
                row.base_url = base_url.strip() or None
        else:
            db.add(LlmSetting(
                provider=provider,
                encrypted_api_key=encrypted,
                base_url=base_url.strip() or None if base_url is not None else None,
            ))
        db.commit()
    finally:
        db.close()


def update_base_url_in_db(provider: str, base_url: str | None) -> None:
    """Update only base_url for provider (row must exist). Empty string = clear."""
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f"Unsupported provider: {provider}")
    db: Session = SessionLocal()
    try:
        row = db.query(LlmSetting).filter(LlmSetting.provider == provider).first()
        if not row:
            raise ValueError(f"No existing config for provider: {provider}")
        row.base_url = base_url.strip() or None if base_url else None
        row.updated_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()


def get_all_providers_status() -> list[dict]:
    """Return list of {provider, configured, masked_key, base_url} for all supported providers."""
    db: Session = SessionLocal()
    result: list[dict] = []
    try:
        for provider in SUPPORTED_PROVIDERS:
            row = db.query(LlmSetting).filter(LlmSetting.provider == provider).first()
            if row and row.encrypted_api_key:
                plain = decrypt_api_key(row.encrypted_api_key)
                result.append({
                    "provider": provider,
                    "configured": True,
                    "masked_key": mask_api_key(plain) if plain else None,
                    "base_url": row.base_url if row.base_url else None,
                })
            else:
                result.append({"provider": provider, "configured": False, "masked_key": None, "base_url": None})
        return result
    finally:
        db.close()


# --- Platform model config (default + per-step) ---

STEP_KEYS = ("analyze", "params", "framework", "chapters")


def get_model_config() -> dict:
    """Return { default_model, analyze_model, params_model, framework_model, chapters_model } from DB."""
    db: Session = SessionLocal()
    try:
        row = db.query(PlatformLlmConfig).first()
        if not row:
            return {
                "default_model": "deepseek-chat",
                "analyze_model": None,
                "params_model": None,
                "framework_model": None,
                "chapters_model": None,
            }
        return {
            "default_model": row.default_model or "deepseek-chat",
            "analyze_model": row.analyze_model,
            "params_model": row.params_model,
            "framework_model": row.framework_model,
            "chapters_model": row.chapters_model,
        }
    finally:
        db.close()


def set_model_config(
    default_model: str | None = None,
    analyze_model: str | None = None,
    params_model: str | None = None,
    framework_model: str | None = None,
    chapters_model: str | None = None,
) -> None:
    """Update platform model config (single row; create if not exist)."""
    db: Session = SessionLocal()
    try:
        row = db.query(PlatformLlmConfig).first()
        if not row:
            row = PlatformLlmConfig(
                default_model=default_model or "deepseek-chat",
                analyze_model=analyze_model,
                params_model=params_model,
                framework_model=framework_model,
                chapters_model=chapters_model,
            )
            db.add(row)
        else:
            if default_model is not None:
                row.default_model = default_model.strip() or "deepseek-chat"
            # Step fields: None or empty = clear (use default)
            row.analyze_model = (analyze_model and analyze_model.strip()) or None
            row.params_model = (params_model and params_model.strip()) or None
            row.framework_model = (framework_model and framework_model.strip()) or None
            row.chapters_model = (chapters_model and chapters_model.strip()) or None
        db.commit()
    finally:
        db.close()
