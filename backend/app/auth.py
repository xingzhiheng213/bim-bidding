"""HTTP API Key authentication (SEC-01)."""
import secrets

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader

from app import config

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _is_exempt_path(path: str) -> bool:
    """Health and OpenAPI/Swagger UI — no key required."""
    if path == "/health" or path == "/openapi.json" or path == "/redoc":
        return True
    if path.startswith("/docs"):
        return True
    return False


async def verify_api_key(
    request: Request,
    x_api_key: str | None = Depends(api_key_header),
) -> None:
    """Require X-API-Key when ADMIN_API_KEY is set; otherwise no-op (dev)."""
    expected = (config.ADMIN_API_KEY or "").strip()
    if not expected:
        return
    if _is_exempt_path(request.url.path):
        return
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )
    if not secrets.compare_digest(x_api_key.encode("utf-8"), expected.encode("utf-8")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
