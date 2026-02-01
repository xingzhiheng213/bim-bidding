# BIM 标书生成 — Docker 一键运行

本目录包含用 Docker 一键启动全部服务（Redis、PostgreSQL、后端、Celery、前端）的配置，**不修改**项目内 `backend/`、`frontend/` 等开发代码。

---

## 前置要求

- 已安装 [Docker](https://docs.docker.com/get-docker/) 与 [Docker Compose](https://docs.docker.com/compose/install/)（或 Docker Desktop 自带 Compose）
- 本机 6379、5432、8000、8080 端口未被占用（可在 `.env` 中改 `FRONTEND_PORT`）

---

## 一键运行

**方式一：在 Docker 目录下执行（推荐）**

```bash
cd Docker
cp .env.example .env
# 按需编辑 .env（如 POSTGRES_PASSWORD、VITE_API_BASE）
docker compose up -d --build
```

**方式二：在项目根目录执行**

```bash
cp Docker/.env.example Docker/.env
# 按需编辑 Docker/.env
docker compose -f Docker/docker-compose.yml up -d --build
```

（方式二时，Compose 用于变量替换的 `.env` 默认取自当前目录；若需用 `Docker/.env` 做替换，请先 `cd Docker` 再执行 compose，即方式一。）

启动完成后：

- **前端页面**：浏览器打开 **http://localhost:8080**（端口以 `Docker/.env` 中 `FRONTEND_PORT` 为准）
- **后端健康检查**：http://localhost:8000/health 应返回 `{"status":"ok"}`
- **API 文档**：http://localhost:8000/docs

---

## 服务说明

| 服务     | 端口  | 说明 |
|----------|-------|------|
| redis    | 6379  | Celery broker/backend |
| postgres | 5432  | 业务数据库 |
| backend  | 8000  | FastAPI 接口 |
| celery   | —     | 异步任务（解析、LLM、按章生成等） |
| frontend | 8080  | 前端静态（Nginx） |

上传文件、导出 DOCX 等数据会持久化在 Docker 卷中（`backend_uploads`、`backend_exports`、`postgres_data`），重启或 `down` 后再次 `up` 不会丢失。**首次启动**时后端会自动创建数据库表（含任务、步骤、设置、导出格式等），无需手动迁移。

---

## 常用命令

（以下在 `Docker/` 目录下执行时，可省略 `-f docker-compose.yml`。）

```bash
# 停止并删除容器（卷保留）
docker compose -f Docker/docker-compose.yml down

# 停止并删除容器及卷（清空数据库与上传文件）
docker compose -f Docker/docker-compose.yml down -v

# 查看日志
docker compose -f Docker/docker-compose.yml logs -f

# 仅查看后端或前端日志
docker compose -f Docker/docker-compose.yml logs -f backend
docker compose -f Docker/docker-compose.yml logs -f frontend
```

---

## 配置说明

- **环境变量**：在 `Docker/.env` 中修改；`POSTGRES_*`、`FRONTEND_PORT`、`VITE_API_BASE` 见 `Docker/.env.example` 注释。
- **大模型 API Key**：可在 `Docker/.env` 中写 `DEEPSEEK_API_KEY`、`ZHIPU_API_KEY`，或在应用内「设置」页配置。构建时**不会**把 `backend/.env` 打进镜像（已用项目根 `.dockerignore` 排除），请勿依赖本机 backend/.env。
- **CORS**：后端已根据 `FRONTEND_PORT` 允许 `http://localhost:8080`（或你设置的端口）；若前端通过其他地址访问，需在 backend 环境变量中设置 `CORS_ORIGINS`。

---

## 文件说明

| 文件 | 说明 |
|------|------|
| `docker-compose.yml` | 编排 redis、postgres、backend、celery、frontend |
| `Dockerfile.backend` | 后端镜像（Python + uvicorn） |
| `Dockerfile.frontend` | 前端镜像（Node 构建 + Nginx 提供静态） |
| `nginx.conf` | 前端 Nginx 配置（SPA 路由） |
| `.env.example` | 环境变量示例，复制为 `.env` 使用 |
| `README.md` | 本说明 |

所有路径均以「项目根目录」为基准，构建上下文为项目根，**不修改** `backend/`、`frontend/` 内任何文件。
