"""Celery configuration: broker, backend, serialization."""
from app.config import settings

broker_url = settings.redis_url
result_backend = settings.redis_url
task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]
timezone = "Asia/Shanghai"
enable_utc = True
# 确保结果写入 Redis，便于客户端 result.get() 读取
result_extended = True
