"""Export format settings for DOCX (stage 7.1): single row for heading/body/table font, indent, line spacing."""
from sqlalchemy import Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.task import Base


class ExportFormatSetting(Base):
    __tablename__ = "export_format_settings"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", name="uq_export_format_tenant_user"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    heading_1_font: Mapped[str | None] = mapped_column(String(64), nullable=True)
    heading_1_size_pt: Mapped[int | None] = mapped_column(Integer, nullable=True)
    heading_2_font: Mapped[str | None] = mapped_column(String(64), nullable=True)
    heading_2_size_pt: Mapped[int | None] = mapped_column(Integer, nullable=True)
    heading_3_font: Mapped[str | None] = mapped_column(String(64), nullable=True)
    heading_3_size_pt: Mapped[int | None] = mapped_column(Integer, nullable=True)
    body_font: Mapped[str | None] = mapped_column(String(64), nullable=True)
    body_size_pt: Mapped[int | None] = mapped_column(Integer, nullable=True)
    table_font: Mapped[str | None] = mapped_column(String(64), nullable=True)
    table_size_pt: Mapped[int | None] = mapped_column(Integer, nullable=True)
    first_line_indent_pt: Mapped[int | None] = mapped_column(Integer, nullable=True)
    line_spacing: Mapped[float | None] = mapped_column(Float, nullable=True)
