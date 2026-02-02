# BIM 标书生成 — Docker 一键运行

本目录包含用 Docker 一键启动全部服务（Redis、PostgreSQL、后端、Celery、前端）的配置，**不修改**项目内 `backend/`、`frontend/` 等开发代码。

---

## 前置要求

- 已安装 [Docker](https://docs.docker.com/get-docker/) 与 [Docker Compose](https://docs.docker.com/compose/install/)（或 Docker Desktop 自带 Compose）
- 本机 6379、5432、8001、8080 端口未被占用（可在 `.env` 中改 `FRONTEND_PORT`）

---

## 一键运行

**方式一：在 Docker 目录下执行（推荐）**

```bash
cd Docker
cp .env.example .env
# 按需编辑 .env（生产环境请修改 POSTGRES_PASSWORD；大模型 API Key 可在应用内「设置」页配置）
docker compose up -d --build
```

**方式二：在项目根目录执行**

```bash
cp Docker/.env.example .env
# 按需编辑项目根目录下的 .env（Compose 从当前目录读取 .env）
docker compose -f Docker/docker-compose.yml up -d --build
```

（方式二时，`env_file` 相对于当前目录，故需将 `Docker/.env.example` 复制为**项目根目录**下的 `.env`；或使用方式一在 `Docker/` 下操作，只需一份 `.env`。）

启动完成后：

- **前端页面**：浏览器打开 **http://localhost:8080**（端口以 `Docker/.env` 中 `FRONTEND_PORT` 为准）
- **后端健康检查**：http://localhost:8001/health 应返回 `{"status":"ok"}`
- **API 文档**：http://localhost:8001/docs

---

## 服务说明

| 服务     | 端口  | 说明 |
|----------|-------|------|
| redis    | 6379  | Celery broker/backend |
| postgres | 5432  | 业务数据库 |
| backend  | 8001  | FastAPI 接口 |
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

- **环境变量**：在 `.env` 中修改（方式一为 `Docker/.env`，方式二为项目根 `.env`）；`POSTGRES_*`、`FRONTEND_PORT`、`VITE_API_BASE` 见 `Docker/.env.example` 注释。**生产环境请修改 `POSTGRES_PASSWORD`**；`.env` 勿提交到仓库（已由 `.gitignore` 排除）。
- **大模型 API Key**：建议在应用内「设置」页配置，不写进 `.env` 更安全；若写在 `.env` 中，构建时**不会**打进镜像（`backend/.env`、`Docker/.env` 已用 `.dockerignore` 排除）。
- **知识库（可选）**：默认不使用知识库。若需 RAGFlow，请**自行部署** RAGFlow，启动本应用后在「设置」页选择知识库类型 RAGFlow，填写 Base URL、API Key、Dataset IDs。后端在 Docker 内时，Base URL 填 `http://host.docker.internal:9380`（Windows/Mac）或 RAGFlow 所在主机/服务地址；也可使用 ThinkDoc 等云知识库并在设置页配置。
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
