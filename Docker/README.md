## Docker 一键运行

用 Docker 一次性启动本项目所需的 Redis、PostgreSQL、后端 API、Celery 与前端界面。

---

## 前置条件

- 已安装 Docker 与 Docker Compose（或 Docker Desktop 自带 Compose）。

---

## 快速开始

在项目根目录执行：

```bash
cd Docker
cp .env.example .env
# 如有需要，可编辑 .env（例如修改数据库密码或前端端口）
docker compose up -d --build
```

启动完成后，打开浏览器访问：

- 前端界面：`http://localhost:8080`（如在 `.env` 中修改了 `FRONTEND_PORT`，以你的配置为准）
- 后端健康检查：`http://localhost:8001/health`
