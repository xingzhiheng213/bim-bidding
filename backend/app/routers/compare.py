"""Compare API: POST /api/compare for text diff."""
from fastapi import APIRouter

from app.diff_compare import compute_diff
from app.schemas.compare import CompareRequest, CompareResponse

router = APIRouter(tags=["compare"])


@router.post("/compare", response_model=CompareResponse)
def post_compare(body: CompareRequest):
    """Compare two texts and return structured diff (add/del segments)."""
    diff = compute_diff(body.original, body.modified)
    return CompareResponse(diff=diff)
