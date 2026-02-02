# BIM 标书生成

基于大模型的 BIM 技术标书生成应用：上传招标文件 → 解析与 LLM 分析 → 生成章节框架 → 按章生成正文 → 聚合导出 Word。支持框架审核、要点补充、单章重生成、修改前后对比，以及导出格式（标题/正文/表格字体字号、首行缩进、行距）配置。

---

## 功能概览

- **文档上传与解析**：支持 PDF / DOC / DOCX，解析为纯文本供后续分析。
- **招标分析**：调用大模型提取招标要求、BIM 技术要求、评分细则等。
- **参数提取**：从分析结果中结构化提取项目信息、BIM 要求、废标风险点。
- **章节框架生成**：生成「第 X 章 标题」框架，可对接知识库检索；支持审核、重生成、添加要点后继续。
- **按章生成**：按小节大纲逐章生成正文（二级/三级标题、段落、表格），支持单章重生成与要点补充。
- **文档聚合与导出**：将各章 + 项目信息 + 风险点聚合为完整 Markdown，导出为 Word（DOCX）；支持代码块内表格转真实表格、中英文字体（含 eastAsia）配置。
- **设置**：大模型 API Key（DeepSeek、智谱等）、各步骤模型选择、导出格式（标题/正文/表格字体字号、首行缩进、行距）。
- **对比**：从任务加载或粘贴两段文本，进行差异对比（标红标绿）。

---

## 技术栈

| 层级     | 技术 |
|----------|------|
| 后端     | FastAPI、Celery、Redis、PostgreSQL、SQLAlchemy |
| 前端     | React、TypeScript、Vite、Ant Design、TanStack Query |
| 文档解析 | PyMuPDF、python-docx |
| 文档生成 | Markdown → HTML → python-docx（DOCX），支持表格与样式配置 |
| 大模型   | 设置中配置 API Key，对接 DeepSeek、智谱等 |

---

## 环境要求

- **后端**：Python 3.10+，Redis，PostgreSQL
- **前端**：Node.js 18+

---

## 快速开始

### 方式一：Docker 一键运行

```bash
cd Docker
cp .env.example .env
# 按需编辑 .env（POSTGRES_PASSWORD、VITE_API_BASE、API Key 等）
docker compose up -d --build
```

- 前端：<http://localhost:8080>
- 后端健康检查：<http://localhost:8001/health>
- API 文档：<http://localhost:8001/docs>

详见 [Docker/README.md](Docker/README.md)。

### 方式二：本地开发

1. **Redis、PostgreSQL** 已安装并启动（端口 6379、5432）。
2. **后端**（在 `backend/` 下）：
   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   pip install -r requirements.txt
   copy .env.example .env   # 配置 REDIS_URL、DATABASE_URL 等
   uvicorn app.main:app --reload
   ```
3. **Celery**（另开终端，同目录）：
   ```bash
   celery -A celery_app worker -l info -P solo
   ```
4. **前端**（在 `frontend/` 下）：
   ```bash
   npm install
   npm run dev
   ```
   访问 <http://localhost:5173>。

数据库表在**后端首次启动**时自动创建（`Base.metadata.create_all`），无需手动建表。  
本地开发与办公环境迁移说明见：[各阶段指导/开发前-服务启动顺序.md](各阶段指导/开发前-服务启动顺序.md)、[各阶段指导/办公环境-数据库迁移与启动指南.md](各阶段指导/办公环境-数据库迁移与启动指南.md)。

---

## 项目结构

```
├── backend/          # FastAPI + Celery，任务与步骤、解析、LLM、聚合、导出
├── frontend/         # React + TypeScript，首页 / 任务详情 / 设置 / 对比
├── Docker/           # docker-compose、Dockerfile、nginx 配置
├── 各阶段指导/       # 开发与操作指南（服务启动、数据库迁移、Git、UI 阶段等）
├── 开发计划-分阶段.md
├── UI设计计划-分阶段.md
└── README-backend.md # 后端说明
```
