"""Pytest 配置。

`app.settings_store` 在 import 时要求有效的 Fernet `SETTINGS_SECRET_KEY`；
在加载任何会间接 import 该模块的测试前，为未配置的环境生成一次性测试密钥。
"""
from __future__ import annotations

import os


def _ensure_fernet_key() -> None:
    if (os.environ.get("SETTINGS_SECRET_KEY") or "").strip():
        return
    from cryptography.fernet import Fernet

    os.environ["SETTINGS_SECRET_KEY"] = Fernet.generate_key().decode()


_ensure_fernet_key()
