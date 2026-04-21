"""Authentication helpers: service API key guard + request principal."""
from __future__ import annotations

import base64
import json
import secrets
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from app import config

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_header = HTTPBearer(auto_error=False)
debug_user_header = APIKeyHeader(name="X-Debug-User-Id", auto_error=False)
debug_tenant_header = APIKeyHeader(name="X-Debug-Tenant-Id", auto_error=False)


@dataclass(frozen=True)
class Principal:
    tenant_id: str
    user_id: str
    auth_mode: str


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


def _from_debug_headers(user_id_raw: str | None, tenant_id_raw: str | None) -> Principal | None:
    user_id = (user_id_raw or "").strip()
    if not user_id:
        return None
    tenant_id = (tenant_id_raw or "").strip() or config.AUTH_DEFAULT_TENANT_ID
    return Principal(tenant_id=tenant_id, user_id=user_id, auth_mode="header")


def _decode_jwt_payload(token: str) -> dict | None:
    parts = token.split(".")
    if len(parts) != 3:
        return None
    payload = parts[1]
    payload += "=" * ((4 - len(payload) % 4) % 4)
    try:
        raw = base64.urlsafe_b64decode(payload.encode("ascii")).decode("utf-8")
        data = json.loads(raw)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _from_bearer(creds: HTTPAuthorizationCredentials | None) -> Principal | None:
    if not creds or creds.scheme.lower() != "bearer":
        return None
    payload = _decode_jwt_payload(creds.credentials)
    if not payload:
        return None
    user_id = str(payload.get("sub") or payload.get("user_id") or "").strip()
    if not user_id:
        return None
    tenant_id = str(payload.get("tenant_id") or payload.get("tid") or "").strip() or config.AUTH_DEFAULT_TENANT_ID
    return Principal(tenant_id=tenant_id, user_id=user_id, auth_mode="jwt")


def _from_mock() -> Principal:
    return Principal(
        tenant_id=config.AUTH_DEFAULT_TENANT_ID,
        user_id=config.AUTH_DEFAULT_USER_ID,
        auth_mode="mock",
    )


async def get_principal(
    bearer: HTTPAuthorizationCredentials | None = Depends(bearer_header),
    x_debug_user_id: str | None = Depends(debug_user_header),
    x_debug_tenant_id: str | None = Depends(debug_tenant_header),
) -> Principal:
    """Resolve request principal for isolation (tenant_id + user_id)."""
    mode = config.AUTH_MODE
    if mode == "jwt":
        p = _from_bearer(bearer)
        if not p:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid Bearer token")
        return p
    if mode == "header":
        p = _from_debug_headers(x_debug_user_id, x_debug_tenant_id)
        if not p:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing X-Debug-User-Id header")
        return p
    if mode == "mock":
        return _from_mock()
    # hybrid: jwt -> header -> mock fallback
    return _from_bearer(bearer) or _from_debug_headers(x_debug_user_id, x_debug_tenant_id) or _from_mock()
