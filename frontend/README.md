# BIM 标书生成 — 前端

前端运行目录为 **frontend/**，后端在 **backend/**。

## 环境

- Node.js 18+
- 本地需先启动后端（见 [README-backend.md](../README-backend.md)），否则健康检查请求会失败

## 环境变量

| 变量 | 说明 | 默认（开发） |
|------|------|----------------|
| `VITE_API_BASE` | 后端 API 根地址 | `http://localhost:8001` |

开发环境在 `frontend/.env.development` 中已配置 `VITE_API_BASE=http://localhost:8001`。若后端端口或主机不同，请修改该文件或新建 `.env.local` 覆盖。

## 本地运行

### 1. 安装依赖

在 **frontend/** 目录下执行：

```bash
npm install
```

### 2. 启动开发服务器

在 **frontend/** 下执行：

```bash
npm run dev
```

默认访问：<http://localhost:5173>。请确保后端已启动（`uvicorn app.main:app --reload --host 0.0.0.0 --port 8001`），页面会请求 `GET /health` 并显示「后端状态：ok」。

### 3. 构建

```bash
npm run build
```

产物在 `frontend/dist/`。

### 4. 单元测试（Vitest）

```bash
npm run test
```

监听模式：`npm run test:watch`。详见 `vite.config.ts` 中 `test` 配置与 `src/test/setup.ts`。

## CI（与 `.github/workflows/ci.yml` 一致）

在 **`frontend/`** 下执行（与 Actions 中 `frontend` job 等价；CI 使用 Node **22**）：

```bash
npm ci
npm run lint
npx tsc -b
```

`npm run build` 会额外执行 Vite 打包；流水线为加快反馈仅跑 `tsc -b` 做类型检查。

## 验收（阶段 0.2）

- `npm run dev` 能启动前端，浏览器打开显示「BIM 标书生成」标题。
- 页面展示后端 `/health` 返回结果（如「后端状态：ok」）。
- 后端已启用 CORS，浏览器控制台无跨域错误。
