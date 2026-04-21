"""LLM API key settings stored in DB (stage 5.1).
If the table already existed before base_url was added, run:
  ALTER TABLE llm_settings ADD COLUMN base_url VARCHAR(512);
"""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.task import Base


class LlmSetting(Base):
    __tablename__ = "llm_settings"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", "provider", name="uq_llm_settings_tenant_user_provider"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    encrypted_api_key: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
