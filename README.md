<!-- [Input] Current develop/story-workspace/Deck delivery state, Admin Gateway contract, and local runtime requirements. -->
<!-- [Output] Reader-oriented setup, usage, branch status, scope boundaries, and feature TODOs. -->
<!-- [Pos] Repository entry guide for Ink & Memory contributors and local users. -->
<!-- [Sync] 2026-08-17: replace the historical progress diary with a concise usage-first project guide. -->

# Ink & Memory

<p align="center">
  <img src="assets/banner.png" alt="Ink & Memory" width="700" />
</p>

Ink & Memory 是一个围绕写作、Chat、Dream 和 Deck 构建的创作工作台。用户可以在同一套
Story Workspace 中记录内容、与 Agent 对话、启动 Dream 创作流程，并通过 Deck 管理可用的
Agent、插件引用和内容版本。

## 可以做什么

- **Writing**：记录内容、保存写作 Session，并通过时间线和 Reflections 查看历史与分析结果。
- **Chat**：使用 Deck 中的 Agent 对话；同一 Thread 保持固定 Deck，并可在 Deck 内切换 Agent。
- **Dream**：从 DreamAgent Deck 发起独立 Dream Run，在工作台中审阅剧本、分镜、提示词和相关产物。
- **Deck**：创建和维护 Deck、Agent、Prompt 与 Claude Plugin 引用；表单变更进入草稿，显式提交形成不可变内容版本。
- **Settings / Work**：集中管理 Deck、资源链接和插件。系统 Deck 默认可用，用户 Deck 可在这里启停和维护。
- **Agent 工作状态**：在侧边栏查看 SubAgent、计划和 TODO 的执行进度。
- **认证与模型**：支持账号登录、Google OAuth 和 OAuth Device Flow；模型列表、订阅资格、用量与推理由 Admin Gateway 统一提供。

Deck 市场分发、注册、安装和分发治理本期不实现，也不提供占位入口。延期范围统一记录在
[`docs/design/deck-register/`](docs/design/deck-register/README.md)。

## 分支与集成状态

| 分支 | 用途 | 状态 |
|---|---|---|
| [`develop`](https://github.com/glide-the/im/tree/develop) | 开发主分支；PR #2 合并后的功能以它为基线 | 当前主开发基线，尚未包含 PR #2 |
| [`platform`](https://github.com/glide-the/im/tree/platform) | Admin 服务接入和平台能力 | 已完成主要接入 |
| [`story-workspace`](https://github.com/glide-the/im/tree/story-workspace) | Story Workspace、Dream、Chat、订阅与工作台集成 | PR #2 已创建，当前为 Draft，等待合入 `develop` |
| [`decks-version-man`](https://github.com/glide-the/im/tree/decks-version-man) | Deck Work、内容版本与 DreamAgent Demo 分流 | PR #1 已合入 `story-workspace` |
| [`notion-session`](docs/design/notion-session/)（规划名） | Notion Device / 资源连接器设计 | 暂停；当前未保留同名远端分支，设计资料仍在仓库内 |

相关 Pull Request：

- [PR #1：Deck management, versioning, and typed Dream launch](https://github.com/glide-the/im/pull/1)（已合并）
- [PR #2：Merge Story Workspace into develop](https://github.com/glide-the/im/pull/2)（Draft，等待完整 CI 和评审）

## 本地运行

### 0. 选择代码基线

PR #2 合并前，Deck Work 和完整 Story Workspace 以 `story-workspace` 为可运行基线：

```bash
git clone https://github.com/glide-the/im.git ink-dream-memory
cd ink-dream-memory
git switch story-workspace
```

PR #2 合并后，新功能统一从最新 `develop` 创建分支：

```bash
git switch develop
git pull --ff-only origin develop
```

下文 Dream 命令均从 `ink-dream-memory` 根目录执行；Admin 推荐克隆为它的同级目录
`../ink-admin-memory`。

### 1. 准备依赖

- Python 3.10+
- [uv](https://github.com/astral-sh/uv)
- Node.js 20+
- pnpm 9+ 与 npm
- Docker Desktop 或兼容 Docker Engine
- [Ink Admin Memory](https://github.com/glide-the/ink-admin-memory)：负责 PostgreSQL Drizzle Schema、Admin、Gateway、模型目录、订阅和计费能力

Dream 不会在启动时建表，也没有 SQLite 运行时回退。共享 PostgreSQL Schema 只能由 Admin
仓库中的 Drizzle migration 管理。

首次运行时，在 Dream 根目录执行以下命令获取 Admin、生成本机私有配置，并由 Admin
package 初始化内嵌 PostgreSQL 与发布 Schema。MinIO 当前关闭：

```bash
test -d ../ink-admin-memory || (cd .. && git clone https://github.com/glide-the/ink-admin-memory.git)
test -f backend/.env || cp backend/.env.example backend/.env
(cd ../ink-admin-memory && pnpm install)
(cd ../ink-admin-memory && pnpm env:setup)
(cd ../ink-admin-memory && pnpm env:check)
(cd ../ink-admin-memory && pnpm db:migrate)
(cd ../ink-admin-memory && pnpm db:migrate:check)
```

在终端 A 启动 Admin / Gateway；同一个 `@ink-memory/db` supervisor 会管理持久化的
PostgreSQL 进程，应用启动本身不会执行 migration：

```bash
(cd ../ink-admin-memory && pnpm dev)
```

然后在终端 B 发布默认订阅数据并把 Product API 的共享身份写入 Admin 和 Dream 的
gitignored、权限为 `0600` 的环境文件：

```bash
(cd ../ink-admin-memory && pnpm db:data:subscriptions -- --apply)
(cd ../ink-admin-memory && pnpm product:provision-local-dream)
```

打开 `http://localhost:3000/admin`。首次启动按 Admin 页面提示，使用
`../ink-admin-memory/.env.local` 中的 `ADMIN_BOOTSTRAP_TOKEN` 创建首位管理员；随后在模型中心配置
Provider、可调用模型 alias 和定价。Admin 不会生成上游 Provider Key。

需要本机 Dream 调用真实 Gateway 时，先确认至少有一个启用、已定价且已配置 Provider 凭据的模型，
然后在 Dream 根目录执行：

```bash
(cd ../ink-admin-memory && pnpm gateway:provision-local-dream)
```

该命令只接受 localhost 上名为 `ink-memory` 的数据库，并把 Gateway 服务身份和可调用模型 alias
写入两边的私有环境文件；不要对共享或生产数据库执行。完成后重启终端 A 中的
`pnpm dev`，让 Admin 加载新的 Gateway 身份。Admin Gateway 默认由
`http://127.0.0.1:3000` 提供。Admin migration 至少需要发布以下 Dream 运行 capability：

- `dream.schema.unified.v1`
- `dream.workflow.thread-lookup.v1`
- `dream.story-artifact-contract.v2`
- `dream.workflow.no-continuing.v1`

Deck 内容版本还依赖 `dream.deck-content-versions.v1`；缺少时版本能力关闭，不得由 Dream 临时建表补齐。

### 2. 启动 Dream 后端

```bash
(cd backend && uv venv)
(cd backend && uv pip install --python .venv/bin/python -r requirements.txt)
test -f backend/.env || cp backend/.env.example backend/.env
```

至少配置 PostgreSQL 和 Admin Gateway：

```dotenv
DATABASE_URL=postgresql://<user>:<password>@127.0.0.1:<port>/<database>

INK_GATEWAY_ENABLED=1
INK_GATEWAY_BASE_URL=http://127.0.0.1:3000
INK_GATEWAY_SERVICE_KEY=replace-with-local-service-key
INK_GATEWAY_TEXT_MODEL_ALIAS=dream-balanced
INK_GATEWAY_IMAGE_DESCRIPTION_MODEL_ALIAS=dream-image-description
INK_GATEWAY_IMAGE_GENERATION_MODEL_ALIAS=dream-image-generation
```

本机 Admin 默认 PostgreSQL 地址是 `localhost:5433/ink-memory`；实际用户名、密码和连接串以
`../ink-admin-memory/.env.local` 为准。若已运行上一步 Gateway provision，它会写入服务 Key、
Subject JWT 和可调用模型 alias，请保留其结果，不要再用示例值覆盖。

不要提交真实数据库密码、Gateway Service Key、Provider Key 或 OAuth Secret。Dream 只接收
Admin 发布的平台模型 alias；浏览器不能直接传 Provider ID、上游模型名或密钥。

启动后端：

```bash
(cd backend && .venv/bin/python server.py)
```

后端默认监听 `http://127.0.0.1:8765`。

### 3. 启动前端

```bash
(cd frontend && npm install)
(cd frontend && npm run dev)
```

浏览器打开 `http://127.0.0.1:5173`。

### 4. 可选认证配置

密码登录可直接使用。需要 Google OAuth 时，在 `backend/.env` 配置：

```dotenv
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_OAUTH_SCOPE=openid email profile
ENABLE_OAUTH_SIGNUP=true
```

OAuth Device Flow 使用服务端允许的客户端 ID，具体协议与验证页面参见
[`docs/architecture/auth-device.md`](docs/architecture/auth-device.md) 和 `backend/routers/device_oauth.py`。

## 主要入口

登录后默认进入 Story Workspace：

| 页面 | 路径 | 用途 |
|---|---|---|
| Chat | `/story-workspace/chat` | 新对话、历史 Thread、Deck/Agent 选择 |
| Dream | `/story-workspace/dream` | Dream 列表、Run 重入和独立创作工作台 |
| Decks | `/story-workspace/decks` | 查看已启用且已发布的用户 Deck 和系统 Deck |
| Work | `/story-workspace/settings/work` | 管理 Deck、资源链接与插件 |
| Settings | `/story-workspace/settings` | 通用设置、订阅、模型与关于信息 |

首次使用时，可在登录页选择“注册”创建账号；注册流程会应用 Admin 发布的默认产品、订阅和系统
Deck。若 Admin/Gateway、数据库 capability、默认产品或可调用模型 alias 未准备好，注册或 Agent
调用会 fail closed，不会使用本地伪数据兜底。

使用 Deck 时：

1. 在 Decks 页面打开 Deck 预览。
2. Chat Agent 示例会进入 Chat 并预填内容，不会自动发送。
3. DreamAgent 示例会创建 Dream Run，并进入独立 Dream 工作台。
4. Deck 的完整维护、启停、版本记录和相关对话清理统一在 Settings / Work 中完成。

首次创建用户 Deck 的最短路径：

1. 打开 `/story-workspace/settings/work`，进入 Deck 页签并点击“创建”。
2. 在弹窗中填写 Deck 信息，至少增加并启用一个 Agent。
3. 保存草稿后显式提交为内容 `v1`。
4. 在 Work 中启用 Deck；已启用、已发布且无未提交草稿的 Deck 才会出现在 Decks 主页面。

## 常用验证命令

默认技术验证不写真实业务数据：前端 lint/build 不需要服务；下方 Deck Playwright 用例通过公开页面
和拦截的 API 合同验证 UI，只要求 `npm run dev` 正在 `5173` 端口运行；后端测试会在缺少专用测试
数据库或 Provider 凭据时跳过相应集成用例，不得通过业务代码 fallback 强行放行。

```bash
# 前端检查
(cd frontend && npm run lint)
(cd frontend && npm run build)

# 首次使用 Playwright 时安装浏览器；运行 E2E 前保持 Vite 在 5173 端口运行
(cd frontend && npx playwright install chromium)
(cd frontend && npx playwright test e2e/chat-first-deck-defaults.spec.ts --reporter=line --workers=1)

# 后端测试
(cd backend && .venv/bin/python -m pytest -q)
```

真实业务测试必须使用正常运行的 Dream、Admin、Gateway、真实 PostgreSQL 和指定现有账号；
所有步骤走页面或公开生产 API，保留正常 Admin 可查询的 Run、Thread、Gateway 和 Token 回执。
隔离测试结果不能冒充真实业务验收，也不要用测试命令修改或清理无关真实数据。

## 相关文档

- [Deck 设计与需求追踪](docs/design/deck/README.md)
- [延期的 Deck 市场分发需求](docs/design/deck-register/README.md)
- [Story Workspace 设计](docs/design/story-workspace/)
- [订阅业务设计](docs/design/subscription/06-subscription-business-design.md)
- [模型服务接入设计](docs/design/model-service/07-model-service-integration-design.md)
- [部署说明](docs/deploy/overview.md)
- [Notion Developers](https://www.notion.so/developers)

## 功能 TODO

- [ ] **P0**：完成支付系统设计、支付回调、订单状态与订阅结算闭环。
- [ ] **P0**：完成 PR #2 的完整 CI、评审与合并；合并后统一以 `develop` 创建功能分支。
- [ ] **P1**：基于新的 `develop` 功能分支恢复 `notion-session` 设计，完成 Notion Device 授权、资源选择、同步与异常恢复。
- [ ] **P1**：继续完善工作区文件展示、存储服务和跨端同步能力。
- [ ] **P1**：增加用户 Profile 定制，用于 Reflections 的回响、特质和模式深度分析。
- [ ] **P2**：扩展 ASR 与语音输入/输出能力。
- [ ] **P2**：补充阿里云部署、可观测性、备份和故障恢复文档。
- [ ] **延期**：单独评审 Deck 市场注册、发布、安装和分发治理；本期不提前实现。
