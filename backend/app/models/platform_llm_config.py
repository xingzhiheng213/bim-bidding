"""Platform-wide LLM model config: default model + per-step override (single row)."""
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.task import Base


class PlatformLlmConfig(Base):
    __tablename__ = "platform_llm_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    default_model: Mapped[str] = mapped_column(String(64), nullable=False, default="deepseek-chat")
    analyze_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    params_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    framework_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    chapters_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
