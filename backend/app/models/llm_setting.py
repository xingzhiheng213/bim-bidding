"""LLM API key settings stored in DB (stage 5.1).
If the table already existed before base_url was added, run:
  ALTER TABLE llm_settings ADD COLUMN base_url VARCHAR(512);
"""
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.task import Base


class LlmSetting(Base):
    __tablename__ = "llm_settings"

    provider: Mapped[str] = mapped_column(String(32), primary_key=True)
    encrypted_api_key: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
