"""Celery demo 任务联调脚本。

在 backend/ 目录下：

  python scripts/run_celery_demo.py

需 Worker 与 Redis；非自动化测试。
"""
import os
import time

_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(_BACKEND_ROOT)

from celery_app import app
from tasks.demo import hello


def main() -> None:
    print("Broker:", app.conf.broker_url)
    print("Result backend:", app.conf.result_backend)
    print()

    r = hello.delay("BIM")
    print("Task sent, task_id:", r.id)
    print("等待结果 (轮询 Redis，最多 10s)...")
    for _ in range(34):
        if r.ready():
            out = r.get()
            print("Result:", out)
            print("OK")
            break
        time.sleep(0.3)
    else:
        print("Timeout: 10s 内未收到结果，请确认 Worker 在运行且终端出现 received/succeeded")


if __name__ == "__main__":
    main()
