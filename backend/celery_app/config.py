"""Celery configuration: broker, backend, serialization."""
import os
from pathlib import Path

from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

broker_url = REDIS_URL
result_backend = REDIS_URL
task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]
timezone = "Asia/Shanghai"
enable_utc = True
# 确保结果写入 Redis，便于客户端 result.get() 读取
result_extended = True
