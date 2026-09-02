<!-- [输入] 当前 Dream/Admin/Gateway 拓扑、仓库合同以及已发布的 Claude SDK/Runtime 配对。 -->
<!-- [输出] 说明 Ink & Memory 是什么、如何安装运行、如何配对版本，以及必须遵守的运维边界。 -->
<!-- [定位] README.md 英文真相源的中文镜像；事实、结构和命令必须与 README.md 保持一致。 -->
<!-- [同步] 2026-08-28：以当前 develop 流程、精确 SDK/Runtime 配对、本机 Runtime 安装、故障排查和注意事项替换旧说明。 -->
<!-- [同步] 2026-08-28：记录固定 ntn 安装、agentdata 内按用户隔离的凭证与当前快照、后台策略同步及 per-Thread 投影合同。 -->
<!-- [同步] 2026-08-29：记录当前选择范围过滤、thread 最小元数据、空范围撤销和重新授权 LKG 行为。 -->
<!-- [同步] 2026-08-29：记录 Settings Notion 能力/Skill 审阅界面和 Hosted MCP 读写的真实边界。 -->
<!-- [同步] 2026-08-30：记录按 actor/thread 绑定的 Notion CLI 环境注入与认证前 ntn 安装检查。 -->
<!-- [同步] 2026-08-30：记录由部署所有的 Claude Bash sandbox 开关和 AutoDL 显式关闭配置。 -->
<!-- [同步] 2026-08-30：在安装、验证、registry 验收和故障排查中统一采用已公开的 clean-room Runtime 0.1.4。 -->
<!-- [同步] 2026-08-31：要求 AutoDL 发布验证后端生成的 crawler 文件并拒绝 Vite SPA HTML fallback。 -->
<!-- [同步] 2026-09-01：记录生产 skill-creator 打包、AutoDL discovery 验证与未知 Skill 可见失败。 -->
<!-- [同步] 2026-09-01：记录经规范 Chat/SSE/Turn 路径持久化并单次执行的 Dream 工作区自动修正。 -->
<!-- [同步] 2026-09-01：允许歧义 Dream 工作区进入修正 Turn，并安全截断递归 Skill 链接。 -->
<!-- [同步] 2026-09-02：Dream 启动前要求 Admin 0042 发布精确 Chat 历史 keyset pagination capability。 -->
<!-- [同步] 2026-09-01：要求投影写入前校验重复项目根/stage，采用 move-not-copy 清理，并在唯一一次修正停止时显示安全原因。 -->
<!-- [同步] 2026-09-02：记录索引优先的 Episode 同步、稳定的逐 Episode 导航以及禁止跨 Episode 产物回退。 -->

# Ink & Memory

<p align="center">
  <img src="assets/banner.png" alt="Ink & Memory" width="700" />
</p>

<p align="center">
  <a href="README.md">English</a> · 中文
</p>

Ink & Memory 是一个面向写作、Chat、Dream 创作流程和版本化 Deck 的创作工作台。它由 React/Vite 前端、FastAPI 后端、Admin 管理的 PostgreSQL Schema、提供模型访问和计费的 Admin Gateway，以及独立发布的 Claude Agent SDK 和 Claude Runtime 组成。

本仓库只包含 Dream 应用，不拥有共享数据库 Schema、模型 Provider 凭据、计费系统或 Claude SDK/Runtime 的内部实现。

## 可以做什么

- **Writing** —— 写作并保存 Session，通过时间线查看历史和 Reflections。
- **Chat** —— 使用 Deck Agent 在持久 Thread 中进行流式对话、工具调用、resume、计划和 TODO。
- **Dream** —— 启动 Dream Run，审阅剧本、分镜、提示词和生成产物。
- **Episode 同步** —— 同步视图先打开 Run 范围的 Episode 索引，通过稳定的不透明标识分别进入 EP01/EP02，并返回同一 Run 的索引。每个产物请求、ETag 和最近有效快照都按 Episode 隔离，因此 EP02 缺少产物时绝不展示 EP01 内容。
- **Dream 工作区恢复** —— Dream 在写入后置投影前，对 allowlist 内的 workspace slug、重复 canonical 项目根和 stage identity/schema 错误进行分类；随后持久化一条可见的自动修正 user 消息，明确要求移动/合并并清理旧项目根而不是只复制目录，再通过正常 Chat/SSE/Turn 路径续接同一 Claude 会话。多个安全项目根会生成不绑定任一 slug 的修正上下文，不再在 Agent 启动前终止；递归文件树也不会跟随 Thread 外的只读内置 Skill 链接。可信 actor、Thread、Run、Deck 或 plugin authority 异常仍会 fail closed；同一个 originating Turn 最多只发起一次修正，第二次失败只显示 allowlist 内的安全原因且不会启动第三轮。
- **Decks** —— 创建并版本化 Deck、Agent、Prompt、资源和 Claude Plugin 引用。
- **Workspace 与工具** —— 使用 Thread 自有文件、沙箱工具、MCP Server、Skill 和插件。
- **Skill 创作** —— 在既有 Thread workspace 中使用后端所有的 `skill-creator` 创建、评估和改进 Skill；生产发布会按 canonical 小写 ID 刷新其 discovery。
- **Notion 资源** —— 在 Settings 中连接并选择精确允许范围，审阅已安装的 `notion-session` 与 `notion-cli`，并在 Chat 外刷新轻量索引。Dream 在认证前检查固定版本 `ntn` 是否已安装，并把当前 actor/thread 投影作为 `NOTION_HOME`、`NOTION_API_TOKEN`、`NOTION_KEYRING` 与 `NOTION_WORKERS_CONFIG_FILE` 注入 Agent Runtime Bash。Hosted Notion MCP 与这条 CLI 路径相互独立。
- **平台集成** —— 从 Admin/Gateway 获取已认证的模型 alias、订阅资格、用量和计费能力。

Deck 市场分发当前明确延期，参见 [docs/design/deck-register/README.md](docs/design/deck-register/README.md)。

## 系统边界

```mermaid
flowchart LR
    Browser["浏览器 / Vite"] -->|"REST + SSE"| Dream["Dream / FastAPI"]
    Dream -->|"Python 公共 API"| SDK["ink-claude-dream-agent-sdk"]
    SDK -->|"stdio JSONL"| Runtime["ink-claude-code-dream"]
    Runtime -->|"Anthropic Messages"| Gateway["Admin Gateway"]
    Gateway --> Provider["模型 Provider"]
    Dream --> PostgreSQL["Admin 管理的 PostgreSQL"]
    Admin["Admin / Drizzle / Billing"] --> PostgreSQL
    Admin --> Gateway
```

| 仓库/服务 | 负责 | 禁止负责 |
| --- | --- | --- |
| `ink-dream-memory` | Dream 前后端、Thread/Run/Workspace 集成、SDK/Runtime 选择 | 共享 Schema migration、Provider Key、第二套 Agent/Runtime 协议 |
| `ink-admin-memory` | Drizzle Schema、PostgreSQL、Admin、Gateway、模型目录、订阅、计费 | Dream Thread/Run 业务逻辑 |
| `ink-claude-dream-agent-sdk-python` | Python SDK distribution 和公共 `claude_agent_sdk` API | Dream 业务 DTO 或数据库访问 |
| `ink-claude-code-dream` | Clean-room CLI/Runtime、协议、工具、MCP、多平台 npm 包 | Dream/Admin 业务状态机或用户数据 |

## 支持的版本合同

Python SDK 和 npm Runtime 虽然通过不同包生态发布，但 Dream 必须把它们作为一个兼容配对管理。

| 组件 | 要求版本 |
| --- | --- |
| Dream 分支 | `develop` |
| Python | `>=3.12` |
| Node.js | Runtime selector 要求 `>=22 <25` |
| Python SDK | `ink-claude-dream-agent-sdk==0.2.144` |
| npm Runtime | `@glide-the/ink-claude-code-dream@0.1.4` |
| Runtime CLI 兼容输出 | `2.1.241 (Claude Code)` |
| Notion CLI | `ntn@0.15.1` |

重要：`uv sync` 只管理 Python 环境。它会安装 Python SDK，但不会安装或升级 npm Runtime。源码要求 Runtime `0.1.4` 时，即使其他 capability 全部合法，也会拒绝 `0.1.3` 可执行文件。

## 环境要求

- Git
- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Node.js 22–24 和 npm
- pnpm 9+
- 同级目录中的 [Ink Admin Memory](https://github.com/glide-the/ink-admin-memory)
- 仅 Docker/Remote SSH 部署路径需要 Docker

当前 Runtime 支持 Darwin/Linux 的 arm64/x64；Windows 和 musl 目标会 fail closed。

## 本机安装

### 1. 获取当前开发分支

```bash
git clone https://github.com/glide-the/im.git ink-dream-memory
cd ink-dream-memory
git switch develop
git pull --ff-only origin develop
```

除非配置了显式绝对路径，否则 Admin 应位于 `../ink-admin-memory`。

### 2. 准备 Admin、PostgreSQL 和 Gateway

```bash
test -d ../ink-admin-memory || git clone https://github.com/glide-the/ink-admin-memory.git ../ink-admin-memory
cd ../ink-admin-memory
pnpm install
pnpm env:setup
pnpm env:check
pnpm db:migrate
pnpm db:migrate:check
```

所有共享 PostgreSQL migration 只能由 Admin 管理。Dream 禁止临时创建共享表，也没有运行时 SQLite fallback。
当前 Chat 历史分页路径要求 Admin migration `0042_chat_history_keyset_pagination` 和精确 capability `dream.chat-history-keyset-pagination.v1`；启动 Dream 前，`pnpm db:migrate:check` 必须返回 current。

在终端 A 启动 Admin/Gateway：

```bash
cd ../ink-admin-memory
pnpm dev
```

首次本机安装时，从 Admin 仓库发布默认订阅和 Dream 服务身份：

```bash
cd ../ink-admin-memory
pnpm db:data:subscriptions -- --apply
pnpm product:provision-local-dream
pnpm gateway:provision-local-dream
```

这些命令属于本机身份操作。对任何非本机数据库执行前，必须先阅读 Admin 仓库说明。

### 3. 同步 Dream Python 环境

在本仓库执行：

```bash
cd backend
uv sync
```

`uv sync` 创建或更新 `backend/.venv`，并使其精确匹配 `backend/pyproject.toml` 和 `backend/uv.lock`。它可能删除未声明的包，尤其不会保留临时安装的 pytest，也不会管理 npm Runtime。

无需把 pytest 永久加入生产环境即可运行后端测试：

```bash
cd backend
uv run --with pytest==9.1.1 pytest -q
```

### 4. 安装精确 Claude Runtime 与 Notion CLI

Runtime 是 npm/native 制品，必须单独安装公开 selector 包：

```bash
npm install --global @glide-the/ink-claude-code-dream@0.1.4
export PATH="$(npm prefix --global)/bin:$PATH"
command -v ink-claude-code-dream
ink-claude-code-dream --version
```

版本命令必须输出：

```text
2.1.241 (Claude Code)
```

然后通过 Dream 的真实 resolver 校验 Runtime manifest：

```bash
cd backend
.venv/bin/python -c 'from libs.claude_agent_kit.server.sdk_env import resolve_claude_cli_path; print(resolve_claude_cli_path())'
```

该命令必须 exit 0 并输出解析到的 `0.1.4` 可执行路径。如果 `command -v` 仍指向旧的 `~/.local/bin/ink-claude-code-dream`，必须在启动 Dream 前调整 `PATH` 顺序或替换旧安装。运行中的进程会保留启动时继承的 `PATH`；修改后只重启自己拥有的进程。

正常生产资格路径禁止使用 `CLAUDE_CODE_CLI_PATH` 绕过 manifest 校验。该变量只保留给经过评审的显式绝对路径回滚。

安装 Dream 后端连接器路径使用的 Notion CLI：

```bash
npm install --global ntn@0.15.1
ntn --version
ntn login --help
ntn doctor --help
```

`ntn --version` 必须输出 `ntn 0.15.1`。Docker 与 AutoDL 发布会自动安装并验证同一版本。用户应通过 Dream Settings 授权；应用安装时不要在服务账号的默认 home 中运行 `ntn login`。

### 5. 配置 Dream

需要时创建 Dream 私有环境文件：

```bash
test -f backend/.env || cp backend/.env.example backend/.env
```

推荐的本机数据库/Gateway 所有权配置：

```dotenv
DATABASE_URL=
INK_LOAD_DATABASE_URL_FROM_ENV_FILE=1
INK_DATABASE_ENV_FILE=/absolute/path/to/ink-admin-memory/.env.local

INK_GATEWAY_ENABLED=1
INK_GATEWAY_BASE_URL=http://127.0.0.1:3000

AGENT_CWD=/absolute/path/to/agentdata/agent-workspace
INK_AGENT_SANDBOX_ENABLED=true
INK_NOTION_RUNTIME_ROOT=/absolute/path/to/agentdata/notion-runtime
INK_NOTION_MAX_SNAPSHOT_BYTES=134217728
INK_NOTION_SYNC_SCHEDULER_INTERVAL_SECONDS=60
```

Admin provision 命令会把其余本机服务身份和模型 alias 写入 gitignored 环境文件。不要把 Provider Key 复制到 Dream，也不要向浏览器暴露服务凭据。

`INK_NOTION_RUNTIME_ROOT` 必须是与 `AGENT_CWD` 位于同一持久 agentdata 区域的服务端绝对路径。Dream 将每个用户的不透明凭证源保存到 `users/<actor-hash>/home`，并将每个连接器最近一次成功的轻量索引保存到 `users/<actor-hash>/snapshots/<connector-id>/current.json`。保存资源选择时立即执行首次索引同步；之后由连接器的服务端策略在后台刷新到期索引，不要求用户先发起 Chat 或初始化 workspace。索引只含已选 ID 与紧凑元数据，不保存页面 Markdown、blocks 或附件。

启用可信 thread workspace 的 Chat turn 会在 Runtime 初始化时把当前用户有效凭证和最近一次成功索引复制到 `{AGENT_CWD}/{thread_id}/.notion-home` 与 `.notion`；投影前先与用户当前选择范围求交，并最小化连接器元数据。随后 `sdk_env.py` 将该精确 thread 投影通过 `NOTION_HOME`、`NOTION_API_TOKEN`、`NOTION_KEYRING` 与 `NOTION_WORKERS_CONFIG_FILE` 绑定到 Agent Runtime Bash；ambient 值会被清空，不能选择其他用户或 home。投影过程不会调用 Notion 或执行索引同步，因此即使新索引刷新失败，清空或缩小选择范围也会在下一 turn 生效。既有页面 Read hook 与 Agent 直接使用 `ntn` CLI 并存。Workspace Mode 关闭时不提供两种投影和四个 Runtime 环境变量。

### 6. 启动 Dream

终端 B——后端：

```bash
cd backend
.venv/bin/python server.py
```

终端 C——前端：

```bash
cd frontend
npm install
npm run dev
```

访问地址：

- Dream：<http://127.0.0.1:5173>
- Dream API：<http://127.0.0.1:8765>
- Admin：<http://127.0.0.1:3000/admin>

## 主要页面

| 路径 | 用途 |
| --- | --- |
| `/story-workspace/chat` | 新建和历史 Agent Thread |
| `/story-workspace/dream` | Dream Run 和创作工作台 |
| `/story-workspace/decks` | 已启用、已发布的 Deck |
| `/story-workspace/settings/work` | Deck、资源和插件管理 |
| `/story-workspace/settings` | 账号、订阅、模型和应用设置 |

## 验证

```bash
# 后端
cd backend
uv run --with pytest==9.1.1 pytest -q

# 前端
cd frontend
npm run lint
npm run build

# 已发布 SDK/Runtime registry 验收；provider-free，不调用模型
cd ..
python3 scripts/verify_claude_registry_release.py \
  --sdk-version 0.2.144 \
  --runtime-version 0.1.4 \
  --expected-cli-version '2.1.241 (Claude Code)'
```

真实业务测试必须使用正常 Dream/Admin/Gateway/PostgreSQL 链路和指定的现有账号。Provider-free fixture 禁止汇报为真实业务验收。

## 运维与安全注意事项

1. **两个包管理器，一个兼容合同。** `uv` 管理 Python 包，npm 管理 native Runtime；版本变更必须在同一变更中更新两端和验收证据。
2. **Fail closed。** Schema capability 缺失、SDK/Runtime 版本不匹配、manifest 非法、模型 alias 或凭据不可用时必须失败，禁止静默选择 ambient CLI 或伪数据。
3. **Admin 拥有 Schema。** 共享 PostgreSQL Schema 只能通过 Admin Drizzle migration 和 capability 发布修改。
4. **禁止提交 Secret。** 数据库密码、Gateway Service Key、Provider Key、OAuth Secret、npm token、transcript 和用户 Workspace 内容都不得进入 Git。
5. **Thread 自有 Runtime 文件。** Claude 临时文件必须位于经过校验的 Thread workspace `.claude-tmp`，禁止放宽到 `/tmp` 或用户真实 Claude home。
6. **禁止全局清理服务。** 测试只能停止和清理由本轮测试创建的进程与临时资源。
7. **已发布版本不可覆盖。** 错误 Runtime 必须通过前向版本修复或显式评审回滚，正常回滚不得覆盖或 unpublish 已验收版本。
8. **模型输出能力由服务端所有。** Admin 最终选中模型的 `maxOutputTokens` 必须投影到 Runtime；浏览器设置、用户环境、workspace 文件和 Gateway body 改写均不得替代它。
9. **Notion Runtime 绑定归当前 actor/thread 所有。** canonical 持久状态位于服务端 agentdata，策略索引同步与 Chat 解耦，每个 Runtime turn 只接收当前 actor、当前选择范围内的 per-Thread 投影；Dream 在向 Agent Bash 暴露四个受支持变量前替换所有 ambient `NOTION_*` 值。
10. **Editor 写入同时绑定 actor、当前 session 和持久状态。** runner 拒绝面向过期 session 的写入；Editor MCP 子进程只接收服务端所有的 actor 与有效 PostgreSQL capability；每次查询/更新均按 actor 限定；业务失败只刷新唯一内存 EditorState 软缓存，不发布成功事件。Notion 索引和按需页面正文不得进入 EditorState。
11. **Claude Bash sandbox 开关由部署所有。** `INK_AGENT_SANDBOX_ENABLED` 缺省为 `true`，非法值也保持启用。设为 `false` 仍保留 Workspace Mode、cwd、上下文、文件工具、hooks 和工具确认，但已批准的 Bash 会绕过 bubblewrap 文件系统/网络隔离，直接以 Dream 服务账号运行；用户 Settings 与用户 env 均不能覆盖该能力。AutoDL 的外层容器拒绝所需 namespace 创建，因此发布环境固定投影为 `false`；当前 Dream 在 AutoDL 以 `root` 运行，所以已批准 Bash 在该外层容器内拥有 root 权限。
12. **AutoDL crawler 文件属于发布门禁。** Vite Preview 必须把 `/robots.txt`、`/sitemap.xml` 和 `/llms.txt` 代理到 FastAPI。每次 AutoDL start、deploy、verify 与 rollback 都检查公网 MIME、必要正文标记及不存在 SPA HTML；仅 HTTP 200 不算验收通过。
13. **生产 Skill 必须进入 backend build context。** AutoDL start、deploy、verify 与 rollback 会初始化隔离 workspace，并检查 `skill-creator` source、workspace copy、`.claude/skills` discovery，以及 title-case `/Skill-Creator` 到 canonical 小写 ID 的归一化。Runtime 消费未知 Skill 命令时必须返回明确 turn error，不能保存空成功 assistant；修复 package 后可继续复用原 Claude session。

## 故障排查

### `Dream Claude Runtime is not production-qualified`

同时检查可执行文件和 release manifest：

```bash
command -v ink-claude-code-dream
readlink "$(command -v ink-claude-code-dream)"
ink-claude-code-dream --version
```

当前 `develop` 要求 manifest 中的 Runtime 为 `0.1.4`。即使 capability flag 全部为 `true`，实际 Runtime 版本过旧仍会失败。

### `uv sync` 删除了 pytest

`uv sync` 会删除不属于锁定生产环境的包。使用文档中的 `uv run --with pytest==9.1.1 pytest ...`，或者通过单独评审加入开发依赖组；禁止假设临时安装的包能跨 sync 保留。

### PostgreSQL 或 Schema capability 不可用

启动 Admin supervisor，检查 `../ink-admin-memory/.env.local`，并执行 Admin migration check。若 Dream 报告缺少 Chat-history capability，应应用并验证 Admin migration `0042_chat_history_keyset_pagination`；禁止从 Dream 创建该索引或 capability。

### 没有可调用模型

在 Admin 中配置已启用、有定价的模型 alias 和 Provider 凭据，然后执行本机 Gateway provision。Dream 只接受平台 alias，不接受浏览器传入的 Provider ID 或 Key。

### 模型已配置但仍发送 `max_tokens: 32000`

先确认实际运行的 Runtime 版本，并检查 Admin 模型目录中的 `maxOutputTokens`。opaque Gateway alias 无法通过名称安全识别，因此 Dream 必须把认证目录值投影为 `INK_CLAUDE_CODE_MODEL_MAX_OUTPUT_TOKENS`。CLI 使用它作为模型 default/upper limit，`CLAUDE_CODE_MAX_OUTPUT_TOKENS` 只保留为受 capability 裁剪的 standalone override。目录值未设置时，unknown alias 会有意保留上游兼容的 32,000/64,000 fallback；禁止通过硬编码模型 ID 或改写 Gateway 请求体修复。

## 文档与贡献规则

- 仓库维护规则：[Agent.md](Agent.md)
- Agent 产品交互说明：[docs/Agent.md](docs/Agent.md)
- 架构总览：[docs/architecture/项目架构设计说明.md](docs/architecture/项目架构设计说明.md)
- SDK/Runtime 打包与集成：[docs/deploy/claude-sdk-runtime-packaging-and-integration.md](docs/deploy/claude-sdk-runtime-packaging-and-integration.md)
- Registry 验收：[docs/deploy/claude-registry-release-acceptance.md](docs/deploy/claude-registry-release-acceptance.md)
- Story Workspace 设计：[docs/design/story-workspace/](docs/design/story-workspace/)

功能分支必须从最新 `develop` 创建；保留无关工作区改动；同步受影响的文件头和 `.folder.md`；最终报告必须包含精确验证命令和退出码。
