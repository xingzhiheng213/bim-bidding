"""Knowledge base settings: kb_type (none/ragflow) and RAGFlow config (single row)."""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.task import Base


class KbSetting(Base):
    __tablename__ = "kb_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kb_type: Mapped[str] = mapped_column(String(32), nullable=False, default="none")
    ragflow_api_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ragflow_encrypted_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    ragflow_dataset_ids: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
