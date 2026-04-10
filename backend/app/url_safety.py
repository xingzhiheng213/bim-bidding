"""URL validation for server-side HTTP to user-supplied base URLs (SEC-05).

企业内网场景：允许 RFC1918、回环与主机名；禁止非 http(s)、云元数据等高危目标。
"""
from __future__ import annotations

import ipaddress
from urllib.parse import urlparse


def validate_ragflow_base_url(base_url: str) -> tuple[bool, str]:
    """Return (ok, error_message). Intranet / private IPs are allowed."""
    raw = (base_url or "").strip()
    if not raw:
        return False, "Base URL 不能为空"
    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https"):
        return False, "仅支持 http 或 https 协议"
    if not parsed.netloc:
        return False, "URL 缺少主机名或端口"
    host = parsed.hostname
    if host is None:
        return False, "无法解析主机名"

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        # 内网 DNS 主机名，不做解析，由业务侧连接
        return True, ""

    # 仍拦截典型云元数据与无效目标（内网网段一律放行）
    if ip.version == 4:
        s = str(ip)
        if s == "169.254.169.254":
            return False, "不允许访问云元数据地址 (169.254.169.254)"
        if s == "0.0.0.0":
            return False, "无效地址"
    if ip.version == 6:
        # AWS Nitro 等元数据（示例）
        try:
            if ip == ipaddress.ip_address("fd00:ec2::254"):
                return False, "不允许访问云元数据类地址"
        except ValueError:
            pass

    return True, ""
