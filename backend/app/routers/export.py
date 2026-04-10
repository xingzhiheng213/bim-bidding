"""Export endpoint: generate and download the assembled DOCX."""
import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.assembler import assemble_full_markdown
from app.database import get_db
from app.export_docx import markdown_to_docx
from app.services.step_service import require_task
from app.settings_store import get_export_format_config

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("/{task_id}/download")
def download_docx(task_id: int, db: Session = Depends(get_db)):
    """Generate DOCX from the assembled Markdown (chapters + appendix) and stream it."""
    require_task(task_id, db)

    try:
        md = assemble_full_markdown(task_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    format_options = get_export_format_config()
    doc = markdown_to_docx(md, format_options)
    buffer = io.BytesIO()
    doc.save(buffer)
    body = buffer.getvalue()

    return Response(
        content=body,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": (
                f'attachment; filename="BIM_bidding_task_{task_id}.docx"; '
                f"filename*=UTF-8''BIM%E6%A0%87%E4%B9%A6_%E4%BB%BB%E5%8A%A1{task_id}.docx"
            ),
        },
    )
