## 端口一览表

| 端口  | 用途             |
|-------|------------------|
| 5173  | 本地开发前端 Vite |
| 8001  | 后端 FastAPI/API |
| 8080  | Docker 前端入口  |
| 5432  | PostgreSQL 数据库 |
| 6379  | Redis/Celery（Docker 默认不映射到宿主机，仅容器内访问；见 `Docker/docker-compose.yml` 注释） |
