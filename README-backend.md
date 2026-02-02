# BIM 标书生成 — 后端

后端运行目录为 **backend/**，前端在 **frontend/**（见 [frontend/README.md](frontend/README.md)）。后端已启用 CORS，允许前端开发服务器（如 `http://localhost:5173`）跨域请求；可通过环境变量 `CORS_ORIGINS` 配置，多个源用逗号分隔。

## 环境

- Python 3.10+
- Redis（Celery broker/backend）
- PostgreSQL（后续业务表用，本阶段仅连接）

## 本地运行

### 1. 进入后端目录并创建虚拟环境

```bash
cd backend
python -m venv .venv
```

Windows 激活：

```bash
.venv\Scripts\activate
```

Linux/macOS：

```bash
source .venv/bin/activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

复制示例并修改（Redis、PostgreSQL 地址等）：

```bash
copy .env.example .env
```

编辑 `.env`，填写 `REDIS_URL`、`DATABASE_URL`。

### 4. 启动 FastAPI

在 **backend/** 下执行：

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

访问：<http://localhost:8001/health> 应返回 `{"status":"ok"}`。

### 5. 启动 Celery Worker

另开终端，在 **backend/** 下激活同一 venv 后执行：

```bash
celery -A celery_app worker -l info -P solo
```

Windows 建议加 `-P solo` 避免多进程问题。

### 6. 验证演示任务

在 **backend/** 下进入 Python：

```python
from tasks.demo import hello
r = hello.delay("BIM")
print(r.get())   # {"message": "Hello, BIM!"}
```

## 验收（阶段 0.1）

- `GET http://localhost:8001/health` 返回 `{"status":"ok"}`。
- Redis、PostgreSQL 配置正确时，Celery 演示任务 `hello.delay("...")` 能执行并拿到结果。
- 数据库连接正常（启动时日志有 "Database connection OK"，或未配置时仅警告不阻塞启动）。

## 与前端联调（阶段 0.2）

先启动本后端（`uvicorn app.main:app --reload --host 0.0.0.0 --port 8001`），再在 **frontend/** 下执行 `npm install` 与 `npm run dev`；前端会请求 `/health` 并显示结果，需确保后端已启动且 CORS 无报错。
