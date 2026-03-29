# BIM 标书生成 — 待修复问题清单

> 生成时间：2026-03-28  
> 来源：全项目代码审查  
> 状态标记：⬜ 待修复 / ✅ 已修复 / ❌ 已排除（误报）

---

## P0 — 严重（功能失效 / 安全漏洞）

### ~~P0-1 ❌ 模型配置 UI 完全失效（已排除——功能已有意废弃）~~

**验证结论**：  
经代码审查确认，`PlatformLlmConfig` 模型、`get_model_config()` / `set_model_config()` 函数均为**早期支持多模型选择功能时遗留的死代码**。  
后续团队决策收敛为**仅使用 DeepSeek**（通过环境变量配置），对应 API 端点始终未实现，前端亦无相关 UI。  
`get_llm_for_step()` 只读取环境变量是**正确行为**，并非 bug。

**处置**：已清理全部死代码——删除 `platform_llm_config.py`，移除 `settings_store.py` 中的 `get_model_config()` / `set_model_config()` 及相关导入，更新 `models/__init__.py`。

---

### P0-2 ~~❌ `doc.add_comment()` 方法不存在（已排除）~~

**验证结果**：`python-docx >= 1.2.0` 已内置 `add_comment()`，`hasattr(doc, 'add_comment')` 返回 `True`，此问题不成立。

---

### P0-3 ✅ `SETTINGS_SECRET_KEY` 未设置时使用已知硬编码密钥

**文件**：`backend/app/settings_store.py`

**问题描述**：  
```python
_DEV_PLACEHOLDER_KEY = base64.urlsafe_b64encode(b"dev-placeholder-key-32bytes!!!!!")
```
若 `SETTINGS_SECRET_KEY` 未配置，所有加密的 API Key 都以**公开已知的固定密钥**加密存储。
任何人拿到数据库 dump 后，用此已知密钥立刻可解密出所有 DeepSeek / RAGFlow API Key，
造成直接经济损失。

**修复方案**：
1. 在 `backend/.env.example` 和 `Docker/.env.example` 中将 `SETTINGS_SECRET_KEY` 标注为**必填项**，并提供生成命令示例：`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
2. 若 `SETTINGS_SECRET_KEY` 未设置，**启动时打印明显的 WARNING 或拒绝启动**，而不是静默使用 placeholder。
3. `Docker/.env.example` 中补充此项的生成说明。

**处置**：已按方案修复——`backend/.env.example` 和 `Docker/.env.example` 均已将 `SETTINGS_SECRET_KEY` 改为必填项（含生成命令说明）；`main.py` 启动时若未设置则打印醒目的多行 WARNING 框。

---

## P1 — 高危（性能劣化 / 稳定性风险）

### P1-1 ✅ 任务列表接口存在严重 N+1 查询

**文件**：`backend/app/routers/tasks.py`，`list_tasks()` 函数（末尾）

**问题描述**：  
`list_tasks()` 对每个任务调用 `_compute_compare_meta_for_task(db, t.id)`，
该函数内部执行 2 次子查询（framework step + chapters step）。
100 个任务 = 201 次 SQL 查询；随任务数线性增长，首页加载最终超时。

**修复方案**：  
用一次批量查询加载所有任务的相关步骤数据，再在 Python 中按 `task_id` 聚合，
替代逐任务循环查询。

**处置**：已修复——提取纯函数 `_compute_compare_meta_from_steps(framework_step, chapters_step)`（无 DB I/O），原 `_compute_compare_meta_for_task` 委托给它（单任务端点行为不变）。`list_tasks()` 改为先批量 IN 查询 framework steps 和 chapters steps（各 1 次），再 Python dict 按 task_id 聚合，总查询数从 **1+2N 降为恒定 3 次**。

---

### P1-2 ✅ 高频查询路径无数据库索引

**文件**：`backend/app/models/task.py`，`TaskStep` 模型

**问题描述**：  
全项目最高频的查询是 `WHERE task_id=X AND step_key=Y`，
但 `TaskStep` 模型上没有对 `(task_id, step_key)` 建复合索引。
随步骤数据增多，每次查询都是全表扫描。

**修复方案**：  
在 `TaskStep` 模型上添加复合索引：
```python
from sqlalchemy import Index
__table_args__ = (
    Index("ix_task_steps_task_id_step_key", "task_id", "step_key"),
)
```
同时在 `main.py` 的启动迁移中补充 `CREATE INDEX IF NOT EXISTS` 语句（过渡方案），
长期应迁移到 Alembic。

**处置**：已修复——`TaskStep` 模型添加 `__table_args__` 声明复合索引（新环境 `create_all` 直接建好）；`main.py` 启动迁移块末尾追加 `CREATE INDEX IF NOT EXISTS ix_task_steps_task_id_step_key ON task_steps (task_id, step_key)`（已有数据库重启即补上，与现有迁移代码风格一致）。

---

### P1-3 ✅ 删除任务不清理磁盘文件，导致存储泄漏

**文件**：`backend/app/routers/tasks.py`，`delete_task()` 函数

**问题描述**：  
删除任务时只删除数据库记录，`data/uploads/task_{id}/` 目录及其所有文件**永不被清理**。
每个任务上传的文件（最大 50MB）会一直堆积，生产环境存储卷早晚被撑满。

**修复方案**：  
在 `db.commit()` 之后（或成功提交后），删除 `config.UPLOAD_DIR / f"task_{task_id}"` 目录，
使用 `shutil.rmtree(task_dir, ignore_errors=True)` 防止因文件不存在而报错。

**处置**：已修复——`import shutil` 加入，`db.commit()` 成功后追加 `shutil.rmtree(config.UPLOAD_DIR / f"task_{task_id}", ignore_errors=True)`。文件清理放在 commit 之后，确保 DB 提交失败时不会留下孤立行、也不会误删文件。

---

### P1-4 ✅ 重复上传文件不清理旧文件

**文件**：`backend/app/routers/tasks.py`，`upload_file()` 函数

**问题描述**：  
同一 `task_id` 每次上传都生成新 UUID 文件名并写入新文件，旧文件不被删除。
用户反复上传时，`task_{id}/` 目录堆积多个孤儿文件，只有最后一次有效。

**修复方案**：  
上传新文件成功后，读取旧 `upload_step.output_snapshot` 中的 `stored_path`，
删除旧文件（`old_path.unlink(missing_ok=True)`），再更新步骤记录。

**处置**：已修复——在写新文件**之前**先查 upload_step 并解析旧 `stored_path` 存入 `old_file_path`；`db.commit()` 成功后，若 `old_file_path` 存在且与新文件不同，则 `old_file_path.unlink(missing_ok=True)` 清理旧文件。旧文件删除严格在 commit 之后，确保 DB 提交失败时磁盘状态不被破坏。

---

### P1-5 ⬜ 取消任务后数据库状态可能与实际不一致

**文件**：`backend/app/routers/tasks.py`，`cancel_task()` 函数

**问题描述**：  
- `revoke(terminate=True)` 发送 SIGTERM，不保证立即生效。
- Celery worker 可能已执行到一半（例如已写入若干章节），
  此时 step 被强制置回 `pending`，但 `output_snapshot` 已被修改，语义不一致。
- 若 worker 在收到 revoke 前刚好写完 DB 并设置 `status=completed`，
  cancel 接口将其重置为 `pending`，用户无法看到已完成结果。

**修复方案**：  
- 将状态回退为 `cancelled`（而非 `pending`），语义更明确。
- 前端对 `cancelled` 状态提供"重新运行"按钮，而非继续等待。
- 或在 revoke 前先检查步骤的最新状态，若已是 `completed` 则不做重置。

---

## P2 — 中等（功能隐患 / 部署风险）

### P2-1 ⬜ 启动时用原始 ALTER TABLE 做迁移，无版本控制

**文件**：`backend/app/main.py`，`startup()` 函数

**问题描述**：  
每次启动都执行多条 `ALTER TABLE`，通过异常信息字符串匹配判断列是否已存在。
多实例部署有竞态风险；随版本迭代此段代码无限膨胀；无法回滚。

**修复方案**（长期）：引入 Alembic 做版本化迁移管理。  
**修复方案**（短期）：将所有 `ALTER TABLE` 改写为：
```sql
ALTER TABLE task_steps ADD COLUMN IF NOT EXISTS celery_task_id VARCHAR(255);
```
PostgreSQL 支持 `IF NOT EXISTS`，无需 try/except 捕获异常。

---

### P2-2 ⬜ `celery_task_id` 写入存在竞态窗口

**文件**：`backend/app/routers/tasks.py`，各步骤 `run_*_step()` 函数

**问题描述**：  
步骤状态先设置为 `running` 并 `commit()`，然后才投递 Celery 任务，
再第二次 `commit()` 写入 `celery_task_id`。
若进程在两次 commit 之间崩溃，或任务极快完成，`celery_task_id` 永远是 `None`，
导致 cancel 功能对该步骤失效。

**修复方案**：  
先投递 Celery 任务（`result = task.delay(...)`），
拿到 `result.id` 后，在**同一次** `db.commit()` 中同时写入 `status=running` 和 `celery_task_id`。

---

### P2-3 ⬜ 整个 API 无任何认证机制

**文件**：`backend/app/main.py`，`backend/app/routers/`

**问题描述**：  
所有 API 端点对任何能访问 8001 端口的请求完全开放，无 Token / Session / API Key。
攻击者可读取所有任务内容、无限触发 LLM 调用（消耗 API Key 费用）、删除所有数据。

**修复方案**（最小成本）：  
添加一个静态 `X-API-Token` Header 验证中间件，Token 通过环境变量 `API_TOKEN` 配置，
所有非 `/health` 路由强制校验。

---

### P2-4 ⬜ 任务列表无分页，全量加载

**文件**：`backend/app/routers/tasks.py`，`list_tasks()` 函数

**问题描述**：  
`db.query(Task).order_by(...).all()` 无 `limit`/`offset`。
长期使用后，该接口将全部历史任务加载到内存，结合 P1-1 的 N+1 问题，会导致请求超时。

**修复方案**：  
添加 `page` / `page_size` 查询参数（默认 `page=1, page_size=20`），
返回数据同时包含 `total` 字段供前端分页。

---

### P2-5 ⬜ Docker 中 PostgreSQL 5432 端口直接对外映射

**文件**：`Docker/docker-compose.yml`

**问题描述**：  
Redis 的注释专门说明不对外映射以防资产扫描，但 Postgres 5432 却直接映射到宿主机。
配合默认弱密码 `postgres`，一旦服务器在公网上，数据库将直接暴露。

**修复方案**：  
生产环境将 Postgres `ports` 改为仅监听本地回环：
```yaml
ports:
  - "127.0.0.1:5432:5432"
```
或直接删除 `ports` 映射（仅容器内通过服务名访问）。

---

### P2-6 ⬜ Docker 生产环境使用弱默认密码

**文件**：`Docker/.env`，`Docker/.env.example`

**问题描述**：  
`POSTGRES_PASSWORD=postgres` 是极常见的弱密码，与 `.env.example` 的默认值相同，
团队成员可能直接复用此配置上生产。

**修复方案**：  
在 `Docker/.env.example` 中将 `POSTGRES_PASSWORD` 替换为明确的占位符如 `CHANGE_ME_STRONG_PASSWORD`，
并在注释中说明生产必须修改。

---

### P2-7 ⬜ 前端 `.env.development` 硬编码局域网 IP

**文件**：`frontend/.env.development`

**问题描述**：  
`VITE_API_BASE=http://192.168.2.14:8001` 指向某台特定机器的局域网地址。
其他开发者拉取代码后直接 `npm run dev`，API 请求全部打到这个（可能不可达的）IP，
造成"前端一片空白"的困惑。

**修复方案**：  
将 `.env.development` 改为 `VITE_API_BASE=http://localhost:8001`，
如需指向其他地址，各开发者自行创建 `.env.development.local`（已在 `.gitignore` 中）。

---

## P3 — 低风险（代码质量 / 可维护性）

### P3-1 ⬜ Celery Worker `-P solo` 模式全局串行，吞吐量极低

**文件**：`Docker/docker-compose.yml`

**问题描述**：  
`-P solo` 是单进程单线程，同一时刻全局只能执行一个 Celery 任务。
多用户并发时，后来的任务必须等前一个完全结束。

**修复方案**：  
将 `-P solo` 改为 `--concurrency=2`（或根据服务器 CPU 核数调整），
同时为 LLM 调用密集的任务配置 task rate limit 来替代完全串行的限流方式。

---

### P3-2 ⬜ `export_docx.py` 顶层与 `div` 内部逻辑大量重复

**文件**：`backend/app/export_docx.py`，`markdown_to_docx()` 函数

**问题描述**：  
`div` 标签内的处理逻辑与顶层 `p`、`ul`、`pre`、`table` 等标签的处理逻辑几乎完全重复（约 100 行）。
修改一处必须同步修改另一处，容易出现行为不一致。

**修复方案**：  
将元素处理逻辑提取为独立函数 `_process_elements(doc, elements, opts, ...)`，
顶层和 `div` 内部均调用该函数，实现逻辑复用。

---

### P3-3 ⬜ `Task.status` 字段从不更新，语义丢失

**文件**：`backend/app/models/task.py` + `backend/app/routers/tasks.py`

**问题描述**：  
`Task.status` 创建时是 `"pending"`，但所有状态变化都发生在 `TaskStep.status`，
`Task.status` 始终保持 `"pending"`，对前端毫无意义。

**修复方案**：  
在各步骤触发和完成时，同步更新 `Task.status`（如 `"running"` / `"completed"` / `"failed"`），
或明确废弃该字段并从模型中移除，避免误导。

---

### P3-4 ⬜ CORS 配置过于宽松

**文件**：`backend/app/main.py`

**问题描述**：  
`allow_methods=["*"]` 和 `allow_headers=["*"]` 在引入认证（如 Cookie）后会引发浏览器 CORS 安全限制问题。

**修复方案**：  
收紧为：
```python
allow_methods=["GET", "POST", "DELETE", "OPTIONS"]
allow_headers=["Content-Type", "Authorization", "X-API-Token"]
```

---

## 修复优先顺序建议

```
P0-1（模型配置失效）→ P0-3（加密密钥）→
P1-2（添加索引）→ P1-3（删除文件清理）→ P1-4（上传覆盖清理）→
P2-1（ALTER TABLE 改 IF NOT EXISTS）→ P2-2（竞态窗口）→
P2-7（前端 IP 硬编码）→ P2-6（弱密码提示）→ P2-5（Postgres 端口）→
P1-1 + P2-4（N+1 + 分页，需前后端联动）→
P1-5（cancel 状态一致性）→
P3-x（低优先级，可逐步处理）
```

---

## 附加清理记录

### ✅ ThinkDoc 残留代码清理（非原列表问题）

**背景**：项目早期支持 ThinkDoc 云知识库，后决策切换为本地部署 RAGFlow，但相关代码未及时清理。

**已清理内容**：
- `backend/app/config.py`：删除 `THINKDOC_API_URL` / `THINKDOC_API_KEY` / `THINKDOC_KB_IDS_RAW` 变量、`get_thinkdoc_kb_ids()` 函数、自动检测 thinkdoc 的分支逻辑
- `backend/app/knowledge_base.py`：删除 `_search_thinkdoc()` 函数（约 60 行）及 `get_search_fn()` 中的 thinkdoc 分支
- `backend/app/settings_store.py`：`VALID_KB_TYPES` 中移除 `"thinkdoc"`
- `backend/app/routers/settings.py`：`PostKnowledgeBaseBody.kb_type` 的 `Literal` 中移除 `"thinkdoc"`
- `backend/app/models/kb_setting.py`：更新注释
- `backend/test_kb.py`：移除 ThinkDoc 相关说明和提示信息
- `Docker/.env.example`：移除 ThinkDoc 配置注释块
