"""Singleton row: which LLM provider is active for the pipeline (overrides env per-step provider when set)."""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.task import Base


class LlmPreference(Base):
    __tablename__ = "llm_preference"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # None = follow .env (ANALYZE_LLM_PROVIDER etc.); else deepseek | openai_compatible
    active_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
