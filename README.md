## BIM 标书生成应用

一个基于大模型的 BIM 技术标书生成工具：上传招标文件，自动完成分析、生成章节框架与正文，并导出为 Word 文档。

---

## 功能

- 上传 PDF / Word 招标文件，自动解析与分析招标要求。
- 一键生成 BIM 技术标书章节框架和按章正文。
- 支持按章校审、采纳意见后重生成。
- 将全部章节聚合并导出为可编辑的 DOCX。

---

## 安装（推荐：Docker）

1. 安装 Docker / Docker Compose。
2. 在项目根目录执行：

   ```bash
   cd Docker
   cp .env.example .env
   # 可按需修改 .env 中的数据库密码、FRONTEND_PORT、VITE_API_BASE 等
   docker compose up -d --build
   ```

3. 打开浏览器访问：
   - 前端界面：`http://localhost:8080`（如在 `.env` 中修改了 `FRONTEND_PORT`，以你的配置为准）
   - 后端健康检查：`http://localhost:8001/health`

4. 首次进入应用后：
   - 打开「设置」页面，配置 DeepSeek 大模型 API Key。
   - 回到首页，创建任务并上传招标文件，按界面提示依次完成分析、框架、按章生成与导出。

如需查看更详细的 Docker 使用说明，请阅读 `Docker/README.md`。
