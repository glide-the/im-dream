<!-- [Sync] 2026-10-12: record fresh local image cancel/retry, history and normal Admin visible verification; unknown usage retains pending settlement. -->
<!-- [Sync] 2026-10-12: image model division, sketch input and Stop cancellation delivery; full real acceptance remains open. -->
<!-- [Sync] 2026-10-11: pin publicly qualified Runtime0.1.12; normal local adoption and scoped consumer receipt are separate from remote deployment. -->
<!-- [Sync] 2026-10-10: 根工作合同统一为 AGENTS.md，移除 Agent.md 引用。 -->
<!-- [Sync] 2026-10-09: 中文产品名称统一为思维模式，并索引现行业务 PRD。 -->
<!-- [Input] Notion 项目定位、现行业务设计与 PRD、前端功能、包清单与环境模板。 -->
<!-- [Output] 按功能模块说明用途与范围的带图产品介绍，以及运维安装与启用条件。 -->
<!-- [Pos] 仓库中文入口；与 README.md 保持结构、命令及事实一致。 -->
<!-- [Sync] 2026-10-09: 依据具体功能重写产品定位与模块描述，移除泛化创作流程；同步思维模式配图。 -->

# Ink & Memory Dream

<p align="center">
  <a href="README.md">English</a> · 中文
</p>

**Ink & Memory 用于整理个人思维模式，并将这些模式用于具体问题的分析、任务执行和创作。** 思维模式保存处理某类需求的思考方向、解决路径与 Agent 配置；Chat 提供对话和任务入口；Dream 将创作对话与项目产物放在同一工作台。写作、回顾、日历与资源连接帮助用户积累材料、安排工作和重新进入已有任务。

产品定位依据[Notion 项目说明](https://app.notion.com/p/ink-and-memory-38f30b7547c3804cb8a0d1250a3b8ae2?source=copy_link#e4f30b7547c3837ab5d4815f3f1b0e37)，各模块的当前范围以仓库中的现行设计为准。中文界面称为“思维模式”，英文界面沿用 Deck。

![产品总览：思维模式组织解决问题的方法，Chat 用于对话与任务，Dream 管理创作产物](assets/readme/product-overview.zh.svg)

*依据产品定位和[现行导航设计](docs/design/story-workspace/product-scope-and-navigation.md)绘制的功能示意图。*

## 功能模块

### 思维模式

整理针对某类问题的思考方向、解决路径和执行方式，供后续工作重复使用。用户可以浏览和试用已有思维模式，也可以创建自己的模式，编写名称与说明，配置 Agent 角色和 Claude 插件，维护草稿、内容版本及启停状态。系统提供剧本创作、音乐创作等起点；使用入口位于 Chat 和 Dream。当前功能以用户整理和配置为主。

### Chat 对话

围绕具体问题与 Agent 讨论、分析材料或执行任务。用户可以选择模型和 Agent，添加参考文件，阅读回复与工具结果，搜索历史并回到较早的轮次。任务执行期间仍可补充待处理消息、调整方向，或将消息移到独立聊天。保存的对话可再次打开并继续使用。

添加菜单提供[手绘草图](docs/prd/chat/sketch-input.md)：在本机绘制、擦除和撤销，再将 PNG 添加到当前消息。

### 写作与日记

记录想法、撰写正文，保存并重新打开写作内容。段落下的“深入一下”提供主动获取建议的入口，建议与正文分别展示并随写作记录保留；最新建议支持重新生成或失败重试。普通输入和停顿不会自动生成建议，正文仍由用户编辑。已有日记也可以按日期从日历中打开。

### 回顾分析

基于已有日记整理值得回看的内容，帮助用户观察表达中的共鸣、特征和反复出现的模式。用户可以发起分析，按 Echoes、Traits、Patterns 阅读结果，查看条目的解释与依据，并重新打开历史报告。分析范围是日记内容；创作成果的效果评估与反馈统计尚未实现。

### 任务与进度

集中查看 Agent 工作中产生的任务、子智能体活动、计划和待办，了解当前进度及已有结果。任务详情提供关联聊天和来源入口，便于继续处理。活动侧栏汇集优先级事项与历史记录；这些功能用于跟踪已创建的工作。

### 定时任务与日历

安排一次性或重复执行的任务，选择执行模型，以及继续原聊天或每次创建新聊天。日历提供每小时、每天、工作日、每周和自定义周期的编辑入口，支持修改、暂停、恢复、立即执行和查看执行历史。按日期浏览时，可在定时任务、日记和 Notion 内容之间切换，并打开关联记录。

### 资源连接

让 Agent 使用用户选定的外部资料和工具。Notion 连接支持账号授权、选择页面或数据库、同步资源索引，以及按需读取已授权正文；选定资源也可在 Chat 和日历中查看。受管 MCP 连接用于接入外部工具。连接的完整管理入口位于设置，Chat 提供简要入口。MCP Apps 的交互式界面目前处于技术预览，公开渲染尚未开放。

### 文件工作区

集中阅读和使用当前对话的参考文件与 Agent 产物。用户可以添加附件，打开支持的 Markdown 报告、图片和图示，预览或下载文件，并在后续对话中继续使用这些材料。文件围绕当前对话组织；文件预览本身不提供图片生成或视频制作能力。

设置现在分别选择 **AI 模型**（主对话理解与回复）和 **Image 模型**（明确要求 `image_gen.imagegen` 执行的图片操作）。Image 候选来自 Admin 公开的 Images 能力与当前调用资格。使用工具前须保存 Image 选择；没有环境变量、目录默认或唯一候选回退。工具需要工作区、`images:create` 和匹配的 Admin 合同。上传和草图只添加素材。Responses内置生成/编辑已接通Gateway、CLI raw结果及原文件/历史；只有公开能力、明确Responses配置、精确capability和实际角色权限满足时可调用，失败不回退到Images。查看、下载和历史复用原 Chat 路径。本轮本机生成、编辑、取消重试、下载和历史重开已观察，七次合格图片执行已在正常Admin后台逐项可见核对。缺usage的取消请求保留原待结算状态；故障注入仍属于技术验证。见[专项 PRD](docs/prd/chat/image-model-call-division.md)、[正式设计](docs/design/claude-agent/image-model-call-division.md)和[本轮执行回执](docs/exec/image-model-call-division-20261010.md)。

### Dream 创作工作台

将创作任务的持续对话、共享素材和分集成果放在一起，方便查看、审阅和继续创作。当前重点是剧本组织与分镜：项目层管理可跨集复用的人物和场景，分集层阅读大纲、剧本、分镜、提示词和审阅报告。用户可以重新进入已保存的创作任务，在产物旁继续与 Agent 协作，也可以回到同一段 Chat。

<p align="center">
  <img src="frontend/public/assets/story-workspace-guide-illustrations/01-mimo-xiaohei-workflow-triptych.png" alt="剧本工作台指引：共享人物与场景、逐集剧本与分镜、未来制作方向" width="440" />
</p>

*复用应用[创作指引](docs/design/story-workspace/project-and-episode-workbench.md#创作阶段指引)中的插图。上部展示项目共享素材，中部展示逐集创作与审阅，下部的渲染、配音和后期表示未来方向。当前工作台的范围止于剧本与分镜产物的组织、阅读和协作。*

主导航是 **Chat、Dream、思维模式**；**更多**中提供写作、时间线和回顾入口。设置管理语言、主题、模型与资源连接。界面采用暖纸[色彩系统](docs/prd/color_system/README.md)，支持窄屏布局；语言和主题保留在当前浏览器中，详见[设置设计](docs/design/story-workspace/settings.md)。

## 当前范围与启用条件

自动发现解决路径、自动组合 Skills/MCP/Plugin、完整的多 Agent 协作编排，以及创作成果反馈统计仍是后续方向。Dream 尚未提供画布、知识库或从剧本到成片的自动制作链路。

<details>
<summary>部署与能力启用条件</summary>

设计稿描述功能目标；源码、已部署能力和验收记录决定实例中的实际可用范围。

| 功能 | 当前部署条件 |
| --- | --- |
| Chat 输入队列与独立任务 | 依赖 Admin Drizzle 0064–0066 发布的 `dream.chat-input-queue.v1` / `dream.chat-task-session.v2` capability；运行 owner 控制目前要求同一 Dream 进程。见[任务与进度](docs/prd/chat/task-activity.md)。 |
| 定时任务 | 依赖 Admin Drizzle 0077 的 v3 capability 和精确操作合同。代码支持一次、每天、间隔、每小时及每周规则。[最近记录的真实业务回执](docs/design/scheduled-tasks/codex-repeat-and-run-options-real-e2e.md)仍需在权限修复加载后复验正常服务中的成功模型执行。 |
| Notion 同步增量 | 既有连接器与索引读取已实现；新增归属/接受版本路径已通过隔离技术检查，正常 capability 发布、旧 writer drain 及服务切换仍待完成，见[接入回执](docs/exec/notion-sync-ownership-dream-integration-20261007.md)。 |
| MCP Apps | 仅技术预览；`productionAppsEffective=false`，公开 App 渲染关闭，普通工具结果可使用。见[接入设计](docs/design/claude-mcp/mcp-apps-integration-strategy.md)。 |

</details>

## 打开正在运行的实例

在 AutoDL 控制台打开正在运行的实例，选择 **WebUI-6006**。从 Dream 登录卡进入；Admin 完成密码或 Google 认证后返回 Dream。登录后的默认入口为 Chat。

实例变化时公网主机名会变化，请使用控制台当前的 WebUI 链接。**WebUI-6008**是独立的 Admin 运维后台。

| 入口 | 内部监听 | 用途 |
| --- | --- | --- |
| **WebUI-6006** | Next.js `127.0.0.1:6006` | Dream 页面、同源认证/BFF 与 API 路由 |
| Dream 后端 | FastAPI `127.0.0.1:8765` | 私有 Agent Runtime、SSE、业务编排与文件 |
| **WebUI-6008** | Admin `127.0.0.1:6008` | 运维后台、认证、数据接口与 Gateway |
| 嵌入式 PostgreSQL | `54329` | 私有的 Admin 持久化；Dream 不持有数据库凭据 |

重启后入口不可用时，按[AutoDL 恢复手册](docs/deploy/autodl-recovery.md)处理。[2026-09-18 发布回执](docs/exec/exec_autodl_release_20260918.md)记录当次部署，不表示后续全部功能已经验收。其他平台状态由[部署矩阵](deploy/README.md)维护。

## 认证与数据边界

Admin 是认证中心和唯一生产数据库访问服务。Dream 通过 typed DTO client 调用具名且带版本的 Admin operation；Admin Service 与 typed Drizzle Repository 负责权限、事务、锁与持久化。

Dream 产品用户与 Admin 运维账号属于不同业务身份。登录 Dream 不会获得 Admin 管理权限。Google 是 Admin Better Auth 的外部身份来源；Dream 业务接口不接受 Google token 或任意用户 ID 请求头。

Dream 继续负责产品路由、Agent Runtime、EventBus、SSE、turn/resume/cancel 行为与授权后的共享文件操作。Dream 不持有 PostgreSQL 密码，不存在生产 SQL/ORM 路径、migration、runtime DDL 或数据库 fallback。Admin Drizzle 是唯一 Schema 与 migration 权威。

```mermaid
flowchart LR
  Browser["Dream 浏览器"] -->|"WebUI-6006"| Next["Dream Next.js / BFF"]
  Next -->|"同主机私有路由"| FastAPI["Dream FastAPI"]
  Next -->|"OAuth / Session"| Admin["Admin Better Auth"]
  FastAPI -->|"typed DTO operation"| Admin
  Admin -->|"Drizzle Repository / 事务"| PG[("PostgreSQL")]
  FastAPI -->|"授权文件操作"| FS[("共享文件系统")]
```

## 本机运行

### 环境要求

- Dream `develop` 分支；Admin `main` 分支
- Python `>=3.12` 与 `uv`
- Node.js `>=22 <25`、Corepack 与 `pnpm@10.28.1`
- Admin 与 Dream 位于相邻目录
- 原生 Runtime 主机：macOS 或 Linux，arm64 或 x64；registry 验证器拒绝其他目标

```bash
git clone --branch develop https://github.com/glide-the/im-dream.git ink-dream-memory
git clone --branch main https://github.com/glide-the/dream-im-platform.git ink-admin-memory
```

为新安装准备 Admin、嵌入式 PostgreSQL、Gateway 与服务身份。Migration 与 provisioning 写入已配置数据库，应使用预期安装目标；可重复的 migration 测试必须使用具名、可删除的隔离数据库：

```bash
cd ink-admin-memory
pnpm install
pnpm env:setup
pnpm env:check
pnpm db:migrate
pnpm db:migrate:check
pnpm product:provision-local-dream
pnpm gateway:provision-local-dream
pnpm local:stable
```

安装 Dream 与精确版本 Runtime：

```bash
cd ../ink-dream-memory/backend
uv sync --frozen
npm install --global @glide-the/ink-claude-code-dream@0.1.12
npm install --global ntn@0.15.1
command -v ink-claude-code-dream
ink-claude-code-dream --version
ntn --version

# Verify the SDK and manifest-qualified normal PATH Runtime.
uv run python - <<'PY_RUNTIME'
from libs.claude_agent_kit.server.sdk_env import (
    require_dream_claude_sdk_distribution,
    resolve_claude_cli_path,
)
sdk = require_dream_claude_sdk_distribution()
cli = resolve_claude_cli_path()
if cli is None:
    raise SystemExit('Dream Runtime is missing from PATH')
print(f'SDK: {sdk.version}')
print(f'Qualified Runtime: {cli}')
PY_RUNTIME

cd ../frontend
corepack enable
corepack pnpm install --frozen-lockfile
```

Runtime 必须输出 `2.1.241 (Claude Code)`。`uv` 管理 Python SDK，npm 管理原生 Runtime 与 Notion CLI，pnpm 管理 Web workspace；`uv sync` 不会安装 Runtime。

根据[backend/.env.example](backend/.env.example)和[frontend/.env.example](frontend/.env.example)创建 `backend/.env` 与 `frontend/.env.local`。配置明确的 Admin origin/issuer、Dream resource 以及已注册的 service/BFF identity。Dream env 不得包含 `DATABASE_URL` 或 Provider secret。

公开浏览器 origin、OAuth callback、issuer/resource 统一使用 `localhost`，与前端模板一致；私有 Python 监听可使用 `127.0.0.1`。

<details>
<summary>Notion 元数据、同步与日记响应配置</summary>

选中独立页面同步和快照今天更新项的远程元数据读取要求在 `backend/.env` 配置服务器所有的 `INK_NOTION_TODAY_API_VERSION=2026-03-11`，模板已显式设置。loopback 请求头捕获确认固定的 `ntn@0.15.1` 默认请求和显式 `--notion-version` 均发送该日期，见[503 修复回执](docs/exec/notion-today-503-repair-20261006.md)。已有 env 文件须补此键并重启所拥有的 Dream 后端，因为配置在启动时读取。程序没有兜底日期：缺失或非法配置返回 HTTP 503 和 `detail.error_code=NOTION_API_VERSION_UNCONFIGURED`，此时连接列表和快照读取仍可成功。`INK_NOTION_ALLOWED_URL_HOSTS` 配置精确的 HTTPS 目的地主机，默认值见 `backend/.env.example`。这些配置用于远程元数据校验；真实账户的上游兼容性与[隔离技术回执](docs/exec/calendar-right-panel-tabs-implementation-20261005.md)分开验收。

选择 Notion 数据库后，已同步的数据库页面行进入日历候选索引，无需逐行手动选择。重启 Dream 不会重建持久化索引。旧索引缺上游创建/编辑时间时，进入 Notion 设置 → 管理已挂载来源 → 立即同步，然后刷新日历；该操作沿用现有仅同步元数据的入口。

新的 Notion 手动同步、首次选择同步和策略同步消费端要求精确的 `dream.notion-sync-ownership.v1` capability，以及固定的 request/claim/renew/finish 四操作。Admin 负责执行领取、续租与原子接受快照；Dream 随后缓存接受版本。日历、facade 读取和新 Thread 投影在缓存缺失时通过现有 Admin 读取恢复，并校验完整接受身份及仅含元数据的结构。Chat turn 不通过此索引路径触发 Notion 同步或正文下载。缺执行能力时新同步写入关闭，既有读取仍兼容。2026-10-07 集成回执记录正常 Admin 目录尚缺这些操作和 capability；正常库迁移、旧 writer 排空与 claim 启用仍是发布前置。不使用 runtime DDL 或按时间强制接管。详见[集成回执](docs/exec/notion-sync-ownership-dream-integration-20261007.md)及[正式连接器设计](docs/design/notion-session/connector-interaction.md)。

</details>

分别启动拥有的服务：

```bash
# Dream backend
cd ink-dream-memory/backend
uv run uvicorn server:app --host 127.0.0.1 --port 8765

# Dream frontend
cd ink-dream-memory/frontend
INK_BACKEND_INTERNAL_URL=http://127.0.0.1:8765 NEXT_PUBLIC_WS_BASE_URL=ws://127.0.0.1:8765 corepack pnpm run dev --hostname 127.0.0.1 --port 5173
```

Dream 地址为 [Dream](http://localhost:5173)，Admin 地址为 [Admin](http://localhost:3000/admin)。

## 支持版本与所有权

| 组件 | 当前合同 |
| --- | --- |
| Dream metadata | backend `0.1.4`、frontend `0.0.4`、API schema `2.0.0` |
| Next.js / React | `16.1.6` / `19.1.0` |
| Python SDK | `ink-claude-dream-agent-sdk==0.2.145` |
| 原生 Runtime | `@glide-the/ink-claude-code-dream@0.1.12` |
| Runtime compatibility | `2.1.241 (Claude Code)` |
| Notion CLI | `ntn@0.15.1` |
| 认证、PostgreSQL、Drizzle、Gateway、计费 | Admin 仓库 |
| Dream Web、Runtime、SSE、Thread/Run 与文件 | 本仓库 |

## 构建与验证

```bash
# Backend provider-free suite
PYTHONPATH=backend uv run --native-tls --project backend --frozen \
  --with pytest==9.1.1 --with pytest-asyncio \
  python -m pytest backend/tests -q

# Frontend checks
corepack pnpm --dir frontend exec tsc --noEmit --incremental false
corepack pnpm --dir frontend lint
NODE_ENV=production corepack pnpm --dir frontend build

# Published SDK/Runtime identity
python3 scripts/verify_claude_registry_release.py \
  --sdk-version 0.2.145 \
  --runtime-version 0.1.12 \
  --expected-cli-version '2.1.241 (Claude Code)'
```

Provider-free 检查证明确定性合同。真实 Google、模型与业务验收必须使用正常 Dream/Admin/Gateway/PostgreSQL 服务和已授权真实账号。

## 故障排查与运维边界

- **WebUI 返回 404 或无法打开：** 先确认 AutoDL 实例已运行，再按[恢复手册](docs/deploy/autodl-recovery.md)检查；不要新增隧道或硬编码当前公网主机名。
- **Unable to check your session：** 验证两个 WebUI 映射，先检查 Admin，并确认 issuer、Dream origin/resource 与 callback 都来自当前实例。
- **日记检索返回 `session_projection_unavailable` / `ADMIN_RESPONSE_INVALID`：** 元数据读取成功而正文读取失败时，应先核对服务器响应容量，不能仅凭错误码判断字段不匹配。后端模板显式设置 `INK_ADMIN_DREAM_MAX_RESPONSE_BYTES=16777216`（16 MiB）；未配置这个可选项时，代码仍采用 1 MiB。Admin HTTP 与私有 Session broker 共用这一字节上限。全文读取发生在 fuzzy 排序和 `limit` 之前，因此较小的结果数量限制不会减少输入正文。已有后端配置需要明确设置容量，并由进程所有者重启后端；后续 turn 才会取得新的 broker 上限。严格响应结构及请求编号校验保持生效。见[日记检索修复回执](docs/exec/agent-diary-retrieval-capacity-repair-20261006.md)。
- **`ADMIN_SERVICE_AUTH_UNAVAILABLE` 或 `ADMIN_TIMEOUT`：** 先验证 Admin 与 PostgreSQL，再重启 Dream；Dream 不得回退数据库连接。
- **Runtime 未通过 production qualification：** 核对 `command -v ink-claude-code-dream`、package-root `cli.js`、相邻 manifest、Runtime `0.1.12`、compatibility `2.1.241` 与必需 capability。
- **`uv sync` 删除 pytest：** 使用上面的临时 `uv run --with pytest...` 命令，或单独评审开发依赖。
- **Chat 提示 Token allowance 不足：** Gateway 拒绝模型 reservation 前，用户消息已保存。先在 Admin 修正订阅/模型额度，重新加载 Thread 后再决定是否发送。
- **Chat 提示消息队列不可用：** 检查目标 Admin PostgreSQL 是否存在 `chat_input_queue`、`chat_task_session` 及 `dream.chat-input-queue.v1` / `dream.chat-task-session.v2` schema capability。Admin Drizzle 迁移 0064–0066 提供这些能力；获准将迁移应用到目标数据库前，Dream 会保留草稿并拒绝排队。隔离数据库中的 provider-free 测试通过不代表正常业务数据库可用。
- **Chat 返回 `GATEWAY_API_KEY_INVALID`：** Dream service key 与 Admin 当前 active canonical-subject Gateway key 不匹配。AutoDL 现在会在替换运行环境前阻断 sync 和 qualified。必须通过 Admin 所有的发布操作恢复或轮换 Key，仅重启 Dream 以重新读取私有环境，然后完整重跑真实 `create Thread -> POST /api/claude-agent -> SSE` 验收后才能发布。
- **MCP App 没有显示：**公开 App 渲染仍关闭（`productionAppsEffective=false`）。检查连接和工具可用性；普通工具结果仍可使用。

不得提交 secret、对话正文或用户工作区内容。浏览器输入、用户 env、Deck、Plugin 和工作区设置不能覆盖服务器所有的模型/资源配置。Thread 临时文件使用服务器绑定的 `{AGENT_CWD}/{thread_id}/.claude-tmp`，不得将边界扩大到 `/tmp`。

`CLAUDE_CODE_CLI_PATH` 仅用于明确评审的绝对路径回滚，不能掩盖旧 PATH；Dream 不会静默选择 ambient `claude` 或 SDK 内置 CLI。应用回滚不会反向执行 Admin 数据库 migration。详见[SDK/Runtime 接入与回滚](docs/deploy/claude-sdk-runtime-packaging-and-integration.md)。

发送链路真实业务验收必须通过正常 Dream/Admin/Gateway/PostgreSQL 路径完成**创建 Thread → `POST /api/claude-agent` → 鉴权模型目录 → 接受 SSE**，规则见 [AGENTS.md](AGENTS.md#本机真实业务测试协议)。测试只能清理自己命名的进程、端口和临时资源，浏览器检查复用兼容的已安装 Chrome。除非要求清理，保留正常业务 Run 与日志。

## 文档

| 主题 | 入口 |
| --- | --- |
| 现行产品设计 | [Story Workspace](docs/design/story-workspace/README.md)、[思维模式 PRD](docs/prd/deck/thinking-modes.md)、[思维模式设计](docs/design/deck/README.md)、[Chat PRD](docs/prd/chat/.folder.md) |
| 写作与回顾 | [写作手动建议](docs/design/writing-manual-suggestions.md)、[回顾分析](docs/prd/reflection-blog.md) |
| 对话与创作 | [输入队列](docs/prd/chat/queued-input.md)、[轮次导航](docs/prd/chat/turn-navigation.md)、[Dream 重入](docs/design/story-workspace/dream-workspace-and-reentry.md)、[创作工作台](docs/design/story-workspace/project-and-episode-workbench.md) |
| 日历与重复任务 | [日历 PRD](docs/prd/calendar/calendar-right-panel-tabs-prd.md)、[定时任务设计](docs/design/scheduled-tasks/codex-repeat-and-run-options.md) |
| 资源与工具 | [Notion 连接器](docs/prd/notion-session/resource-connector.md)、[连接器交互](docs/design/notion-session/connector-interaction.md)、[MCP Apps](docs/design/claude-mcp/mcp-apps-integration-strategy.md) |
| 架构与认证 | [项目架构](docs/architecture/项目架构设计说明.md)、[Admin 认证/数据合同](docs/architecture/admin-auth-data-interaction.md)、[后端 API](backend/API.md) |
| 安装与部署 | [平台状态](deploy/README.md)、[AutoDL](deploy/autodl-ssh/README.md)、[AutoDL 恢复](docs/deploy/autodl-recovery.md) |
| 仓库与 Agent 规则 | [根工作合同](AGENTS.md)、[Agent 行为](docs/Agent.md)、[规则索引](docs/rules/README.md) |


### 主对话Responses协议前提

共享Admin Provider表单可明确选择通用OpenAI连接的Chat或Responses接口，旧配置默认Chat。验证、实际请求与JSON/SSE使用选中候选的同一配置；不替换Image模型，也不因此开放内置图片。两条源码路径、本机采用与本轮尚未完成的完整验收见[专项正式稿](docs/design/claude-agent/image-model-call-division.md)和[执行记录](docs/exec/image-model-call-division-20261010.md)。
