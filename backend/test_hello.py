"""Test Celery demo task: run from backend/ with venv activated."""
import os
import time

os.chdir(r"d:\标书工作流\backend")

from celery_app import app
from tasks.demo import hello

# 调试：确认与 Worker 使用同一 Redis（Worker 启动时应显示相同 transport/results）
print("Broker:", app.conf.broker_url)
print("Result backend:", app.conf.result_backend)
print()

r = hello.delay("BIM")
print("Task sent, task_id:", r.id)
print("等待结果 (轮询 Redis，最多 10s)...")
# Windows 上 result.get() 的“订阅”方式有时收不到结果，改为轮询 Redis 取结果
for _ in range(34):  # 34 * 0.3s ≈ 10s
    if r.ready():
        out = r.get()
        print("Result:", out)
        print("OK")
        break
    time.sleep(0.3)
else:
    print("Timeout: 10s 内未收到结果，请确认 Worker 在运行且终端出现 received/succeeded")
