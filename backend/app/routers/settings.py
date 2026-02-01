"""Settings API: LLM API keys, base URLs, and model config (stage 5.1)."""
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.model_registry import list_supported_models
from app.settings_store import (
    get_all_providers_status,
    get_export_format_config,
    get_model_config,
    set_api_key_in_db,
    set_export_format_config,
    set_model_config,
    update_base_url_in_db,
    SUPPORTED_PROVIDERS,
)

router = APIRouter(tags=["settings"])


class PostLlmBody(BaseModel):
    provider: Literal["deepseek", "zhipu"] = Field(..., description="LLM provider")
    api_key: str | None = Field(None, description="API key (plain); omit or empty to keep current")
    base_url: str | None = Field(None, description="Base URL; omit to keep current, empty string to clear")


@router.get("/llm")
def get_settings_llm():
    """Return each provider's configured status, masked key, and base_url (no plain key)."""
    try:
        return {"providers": get_all_providers_status()}
    except Exception as e:
        # e.g. llm_settings table missing base_url column (old DB): return safe fallback
        from sqlalchemy.exc import OperationalError, ProgrammingError
        if isinstance(e, (OperationalError, ProgrammingError)):
            return {
                "providers": [
                    {"provider": p, "configured": False, "masked_key": None, "base_url": None}
                    for p in SUPPORTED_PROVIDERS
                ],
            }
        raise


@router.post("/llm")
def post_settings_llm(body: PostLlmBody):
    """Save API key and/or base_url for provider. Returns configured + masked_key + base_url."""
    if body.provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {body.provider}")
    api_key = body.api_key.strip() if body.api_key else ""
    try:
        if api_key:
            set_api_key_in_db(body.provider, api_key, base_url=body.base_url if body.base_url is not None else None)
        elif body.base_url is not None:
            try:
                update_base_url_in_db(body.provider, body.base_url)
            except ValueError as e:
                if "No existing config" in str(e):
                    raise HTTPException(status_code=400, detail="请先保存该 provider 的 API Key 后再设置 Base URL") from e
                raise HTTPException(status_code=400, detail=str(e)) from e
        else:
            raise HTTPException(status_code=400, detail="请提供 api_key 和/或 base_url")
    except HTTPException:
        raise
    except Exception as e:
        from sqlalchemy.exc import OperationalError, ProgrammingError
        if isinstance(e, (OperationalError, ProgrammingError)):
            raise HTTPException(
                status_code=500,
                detail="数据库结构可能过旧，请执行: ALTER TABLE llm_settings ADD COLUMN base_url VARCHAR(512); 或重新创建表后重试。",
            ) from e
        raise HTTPException(status_code=500, detail=f"保存失败: {e!s}") from e
    status_list = get_all_providers_status()
    for s in status_list:
        if s["provider"] == body.provider:
            return {
                "provider": body.provider,
                "configured": s["configured"],
                "masked_key": s["masked_key"],
                "base_url": s.get("base_url"),
            }
    return {"provider": body.provider, "configured": False, "masked_key": None, "base_url": None}


# --- Model config (default + per-step) ---


class PostModelsBody(BaseModel):
    default_model: str | None = Field(None, description="Default model for all steps")
    analyze_model: str | None = Field(None, description="Model for analyze step; empty = use default")
    params_model: str | None = Field(None, description="Model for params step; empty = use default")
    framework_model: str | None = Field(None, description="Model for framework step; empty = use default")
    chapters_model: str | None = Field(None, description="Model for chapters step; empty = use default")


@router.get("/models")
def get_settings_models():
    """Return default model, per-step overrides, and list of supported models for UI."""
    try:
        cfg = get_model_config()
    except Exception:
        cfg = {
            "default_model": "deepseek-chat",
            "analyze_model": None,
            "params_model": None,
            "framework_model": None,
            "chapters_model": None,
        }
    return {
        "default_model": cfg["default_model"],
        "steps": {
            "analyze": cfg.get("analyze_model"),
            "params": cfg.get("params_model"),
            "framework": cfg.get("framework_model"),
            "chapters": cfg.get("chapters_model"),
        },
        "supported_models": list_supported_models(),
    }


@router.post("/models")
def post_settings_models(body: PostModelsBody):
    """Save default model and/or per-step model overrides."""
    set_model_config(
        default_model=body.default_model,
        analyze_model=body.analyze_model,
        params_model=body.params_model,
        framework_model=body.framework_model,
        chapters_model=body.chapters_model,
    )
    cfg = get_model_config()
    return {
        "default_model": cfg["default_model"],
        "steps": {
            "analyze": cfg.get("analyze_model"),
            "params": cfg.get("params_model"),
            "framework": cfg.get("framework_model"),
            "chapters": cfg.get("chapters_model"),
        },
    }


# --- Export format (stage 7.1) ---


class PostExportFormatBody(BaseModel):
    """All optional; omit or null = keep current / use default."""

    heading_1_font: str | None = Field(None, description="一级标题字体")
    heading_1_size_pt: int | None = Field(None, description="一级标题字号（磅）", ge=8, le=72)
    heading_2_font: str | None = Field(None, description="二级标题字体")
    heading_2_size_pt: int | None = Field(None, description="二级标题字号", ge=8, le=72)
    heading_3_font: str | None = Field(None, description="三级标题字体")
    heading_3_size_pt: int | None = Field(None, description="三级标题字号", ge=8, le=72)
    body_font: str | None = Field(None, description="正文字体")
    body_size_pt: int | None = Field(None, description="正文字号", ge=8, le=72)
    table_font: str | None = Field(None, description="表格内字体")
    table_size_pt: int | None = Field(None, description="表格内字号", ge=8, le=72)
    first_line_indent_pt: int | None = Field(None, description="首行缩进（磅），0 或不传表示不缩进", ge=0, le=100)
    line_spacing: float | None = Field(None, description="行距倍数，如 1.0 / 1.5", ge=0.5, le=3.0)


@router.get("/export-format")
def get_settings_export_format():
    """Return current export format config (defaults when not configured)."""
    try:
        return get_export_format_config()
    except Exception:
        from app.settings_store import DEFAULT_EXPORT_FORMAT
        return dict(DEFAULT_EXPORT_FORMAT)


@router.post("/export-format")
def post_settings_export_format(body: PostExportFormatBody):
    """Save export format config; returns full current config."""
    try:
        set_export_format_config(
            heading_1_font=body.heading_1_font,
            heading_1_size_pt=body.heading_1_size_pt,
            heading_2_font=body.heading_2_font,
            heading_2_size_pt=body.heading_2_size_pt,
            heading_3_font=body.heading_3_font,
            heading_3_size_pt=body.heading_3_size_pt,
            body_font=body.body_font,
            body_size_pt=body.body_size_pt,
            table_font=body.table_font,
            table_size_pt=body.table_size_pt,
            first_line_indent_pt=body.first_line_indent_pt,
            line_spacing=body.line_spacing,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return get_export_format_config()
