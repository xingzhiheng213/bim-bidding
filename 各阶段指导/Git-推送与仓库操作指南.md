# Git 推送与仓库操作指南（新手向）

本文档说明如何把本项目的代码**提交到本地 Git**并**推送到 GitHub 私有仓库**，便于备份与恢复。下次忘记时按本文一步步做即可。

---

## 一、你已经完成过的设置（只需做一次）

以下内容在**第一次**时已经做过，一般不需要重复：

| 项目 | 说明 | 如何确认 |
|------|------|----------|
| 根目录 `.gitignore` | 排除 `.env`、`.venv`、`node_modules`、上传文件等，避免误提交 | 项目根目录有 `.gitignore` 文件 |
| `git init` | 把当前文件夹变成 Git 仓库 | 根目录存在 `.git` 文件夹（隐藏） |
| 远程仓库 | 已添加 GitHub 私有仓库 `origin` | 执行 `git remote -v` 能看到 `origin` 指向 `https://github.com/xingzhiheng213/bim-bidding` |
| 作者信息 | Git 知道你的名字和邮箱 | 执行 `git config --global user.name` 和 `git config user.email` 有返回值 |
| 分支跟踪 | 本地 `main` 已关联远程 `origin/main` | 执行 `git push` 能直接推送，不需再写 `origin main` |

若换了一台电脑、或重新克隆了仓库，只需要再配一次「作者信息」和「远程仓库」（见下文「五」）。

---

## 二、日常推送：改完代码后备份到 GitHub

每次你改了一些代码，想**保存到本地并同步到 GitHub** 时，在项目根目录执行下面三步即可。

### 第 1 步：进入项目根目录

```powershell
cd D:\标书工作流
```

（若你的项目不在 `D:\标书工作流`，请改成你的实际路径。）

---

### 第 2 步：添加并提交到本地

```powershell
git add .
git commit -m "简短说明你改了什么"
```

- **`git add .`**：把所有修改过的文件加入「暂存区」（`.gitignore` 里排除的不会加进去）。
- **`git commit -m "..."`**：在本地生成一次提交，`"..."` 里写一句说明，例如：
  - `"feat: 完成阶段 0 设计系统"`
  - `"fix: 修复任务详情页步骤条不刷新的问题"`
  - `"docs: 更新 UI 计划"`

---

### 第 3 步：推送到 GitHub

```powershell
git push
```

- 第一次推送时如果提示登录，在**浏览器**里完成 GitHub 登录或授权即可。
- 推送成功后，打开 `https://github.com/xingzhiheng213/bim-bidding` 就能在网页上看到最新代码。

**小结（日常三步）：**

```powershell
cd D:\标书工作流
git add .
git commit -m "写一句你改了什么"
git push
```

---

## 三、推送前想确认「会提交哪些文件」

避免误提交不该提交的内容，可以先看一眼：

```powershell
cd D:\标书工作流
git status
```

- **红色**：未纳入本次提交的修改（执行 `git add .` 后会变成绿色）。
- **绿色**：已暂存，下次 `git commit` 会把这些变更写进提交。
- 若列表里出现 `backend/.env`、`backend/.venv`、`frontend/node_modules`，说明 `.gitignore` 未生效，**不要**继续 `git add .`，先检查根目录 `.gitignore` 是否包含这些项。

---

## 四、常见报错与处理

### 1. `Author identity unknown` / `Please tell me who you are`

**原因**：Git 不知道你的名字和邮箱（常见于新电脑或第一次用 Git）。

**处理**：在任意目录执行（把名字和邮箱改成你的）：

```powershell
git config --global user.name "你的名字或英文名"
git config --global user.email "你的邮箱@example.com"
```

然后再执行 `git commit -m "..."`。

---

### 2. `src refspec main does not match any`

**原因**：本地还没有叫 `main` 的分支，多数是因为**还没有做过任何提交**。

**处理**：先做一次提交再推送：

```powershell
git add .
git commit -m "feat: 首次提交或备份"
git branch -M main
git push -u origin main
```

之后日常推送只需 `git push`。

---

### 3. `git branch` 什么都不显示

**原因**：还没有任何提交，所以连第一个分支都不存在。

**处理**：同上面第 2 条，先 `git add .` 再 `git commit -m "..."`，然后再执行 `git branch -M main` 和 `git push -u origin main`。

---

### 4. 推送时要求登录（`please complete authentication in your browser`）

**说明**：GitHub 要求你在浏览器里登录或授权，按提示在打开的网页里完成即可，完成后终端里的 `git push` 会继续执行。

---

## 五、换电脑或重新克隆后要做的事

若你在**另一台电脑**上克隆了仓库，或**删掉本地文件夹后重新 clone**，需要：

### 1. 克隆仓库（仅第一次或重装时）

```powershell
cd D:\
git clone https://github.com/xingzhiheng213/bim-bidding.git 标书工作流
cd 标书工作流
```

（若已克隆，可跳过。）

### 2. 配置作者信息（该电脑第一次用 Git 时）

```powershell
git config --global user.name "你的名字"
git config --global user.email "你的邮箱"
```

### 3. 复制 `backend/.env`

克隆下来的仓库里**没有** `backend/.env`（被 `.gitignore` 排除），需要你自己在 `backend` 目录下新建 `.env`，参考 `backend/.env.example` 填写 API Key、数据库连接等。不要提交 `.env`。

---

## 六、小结：下次忘记时看这里

| 场景 | 要做的 |
|------|--------|
| **日常改完代码，备份到 GitHub** | `cd D:\标书工作流` → `git add .` → `git commit -m "说明"` → `git push` |
| **想看会提交哪些文件** | `git status` |
| **提示要填名字/邮箱** | `git config --global user.name "名字"` 和 `user.email "邮箱"` |
| **提示 main 不存在 / branch 为空** | 先 `git add .` 和 `git commit -m "..."`，再 `git branch -M main` 和 `git push -u origin main` |
| **换电脑或重克隆** | 克隆后配好 `user.name` / `user.email`，并手动建好 `backend/.env` |

仓库地址（私有，仅你自己可见）：  
https://github.com/xingzhiheng213/bim-bidding
