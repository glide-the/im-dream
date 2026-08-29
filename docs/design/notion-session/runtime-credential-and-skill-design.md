<!-- [Input] Current Notion connector, MCP credential pattern, Runtime PreToolUse hook, workspace initialization, and upstream notion-session Skill. -->
<!-- [Output] Product/architecture contract for actor credentials, lightweight indexes, thread projection, lazy Read, failures, migration, and acceptance. -->
<!-- [Pos] Current Notion credential/index/Runtime/Skill source of truth in docs/design/notion-session. -->
<!-- [Sync] 2026-08-28: replace full-content snapshots and Agent-visible MCP calls with actor index snapshots plus `.notion/pages/<id>.json` lazy Read. -->
<!-- [Sync] 2026-08-29: minimize connector projections, filter LKG by current selection, paginate discovery, clear empty scope, and preserve effective credentials on failed reauthorization. -->
<!-- [Sync] 2026-08-29: make the installed notion-session Skill discoverable from both `.notion/README.md` and the per-turn workspace context. -->

# Notion 用户凭证、轻量索引与 Runtime Read Hook 设计

Status: Implemented and verified  
Updated: 2026-08-29
Scope: Notion 连接、用户凭证、策略同步、thread 投影、Skill 与按需正文读取

## 1. 背景与问题

Notion 授权已经成功，但此前实现把两件不同的事情合成了“snapshot 同步”：

1. 后台同步已选资源的 ID/元数据索引；
2. 逐页读取 Markdown、metadata 和 blocks，并把正文长期写入 snapshot。

第二项不属于后台索引职责。真实账户证据显示：单个已选 data source 的旧实现顺序读取 49 页正文，第一次 `current.json` 从 `fetched_at` 到原子发布约 225 秒，文件达到 3,069,491 bytes；改选 5 个来源后 600 秒内仍未发布新版本，最终旧进程耗时约 18 分钟才发布 255 个嵌入 page body、15,125,505 bytes 的文件。原子发布本身正确，但由于 builder 做了不必要的正文 I/O，用户在构建期间看到 `snapshots/` 为空或只能看到旧版本。

同时存在两个状态/消费错误：

- `connector_resources` 在刚保存 selection 时就写成 `synced`，即使对应 ID 尚未进入成功索引；
- 当前内置 Skill 把上游 CLI 适配成显式 `mcp__notion__*`，但目标文件体验应为 Agent 读取 `.notion/pages/<id>.json` 时由 Runtime hook 按需获取正文。

已确认的代码链路：

| 链路 | 证据 | 结论 |
|---|---|---|
| 旧 snapshot builder | `backend/notion/sync.py` 对每个数据库 row 调用 `operations.get_page()`，后者连续请求 page、markdown、blocks | 根因：后台同步被正文数量线性放大。 |
| 原子 current | `backend/notion/snapshot_store.py` 仅在完整 payload 构建后替换 `current.json` | 保留；不能用半成品缓解慢同步。 |
| 资源状态 | `backend/notion/store.py::insert_resource` 旧值为 `synced` | 根因：UI 将“已选择”误报为“已进入成功索引”。 |
| 上游 Skill | `develop@e3523db9` 先读取 `.notion/index.json` / database 清单定位 ID，再按需读取页面 | 保留文件导航模型；不恢复 Agent Bash/CLI 凭证访问。 |
| Runtime hook | `agent_runner.py` 已有 `.editor` PreToolUse Read redirect 模式 | 复用同一 hook/临时文件机制，不新增 Agent 工具协议。 |
| 凭证边界 | actor agentdata source + `{thread}/.notion-home` 0700/0600 投影 | 保留；与 MCP 的 actor snapshot 原则一致。 |

## 2. 目标与边界

### 2.1 目标

- 用户只在 Settings 完成连接、选择和同步策略，不提供路径、CLI 参数或 token。
- 凭证与 index current 统一位于服务器 agentdata，并按 canonical user 哈希隔离。
- 定时/立即同步只生成轻量索引：资源 ID、页面 ID、标题、URL、编辑时间、数据库归属、snapshot identity；不抓正文。
- Chat 启动只把当前用户的 index LKG 与凭证投影到当前 thread，不远程同步。
- Agent 只通过 `Read(.notion/...)` 使用 Notion：索引文件是本地只读文件；页面虚拟路径由 Runtime hook 校验并实时返回 Markdown。
- 未选择 ID、缺凭证、过期、权限不足、API/CLI 异常只让该次 Read 失败，普通 turn/resume/cancel/SSE 不变。

### 2.2 非目标

- 不同步或缓存所有页面正文、blocks、附件或全文向量索引。
- 不暴露 `ntn`、Bash、token、`NOTION_HOME` 或显式 Notion MCP 工具给 Agent。
- 不实现 Notion 写入、任意远程 filter/sorts、多账号、共享 connector、webhook 或跨副本队列。
- 不新增数据库表、migration、runtime DDL、SQLite fallback、独立服务或控制通道。
- 不改变 Agent 状态机、EventBus、SSE、模型、资源准入或现有公开 connector API。

## 3. 核心概念与业务规则

| 概念 | 定义 |
|---|---|
| actor credential source | `{agentdata}/notion-runtime/users/{user-hash}/home`；服务器与 `ntn` 认证进程可读，0700/0600。 |
| actor index source | `{agentdata}/notion-runtime/users/{user-hash}/snapshots/{connector-id}/current.json`；仅含轻量 index，原子替换并保留 LKG。 |
| thread index projection | `{AGENT_CWD}/{thread_id}/.notion`；每个 turn 从 actor current 原子复制，整个目录对 Agent 禁写。 |
| thread credential projection | `{AGENT_CWD}/{thread_id}/.notion-home`；只供 Runtime hook，Agent denyRead/denyWrite。 |
| page virtual path | `.notion/pages/<page_id>.json`；磁盘不保存正文，PreToolUse hook 在 Read 时解析。 |
| sync policy | connector `config_json.snapshot_sync_policy` 中的 `default / desired / effective / revision / status`。 |

规则：

1. PostgreSQL `user_id` 是 connector 归属真相；credential path/token 不进入 DTO、connector config、日志或 telemetry。
2. selection 保存后资源状态为 `pending`；只有同一批精确 `(resource_type, external_id)` 进入成功 index 并提交后才变为 `synced`。
3. index builder 可分页枚举 data source rows，但不得调用 page/markdown/blocks 内容端点。
4. `current.json` 只接受 `pages={}` 的新 payload；旧 LKG 可读取其 index 以平滑迁移，但 thread projector 无条件丢弃其中的 legacy page body。
5. thread `.notion/index.json` 和 `.notion/databases/<id>.json` 只用于定位 ID；页面正文不在 snapshot 中。
6. Read hook 仅拦截当前 workspace 精确 `.notion/pages/<id>.json`，拒绝 symlink、越界、非法 ID 与不在当前 index 的 ID。
7. hook 只调用 Markdown endpoint；结果写入当前 thread `.claude-tmp` 的 0600 临时文件，turn 结束删除。
8. `.notion` 加入 sandbox denyWrite，防止 Agent 修改 index 扩大可读范围。
9. 缺少 credential/index 时 fail closed；不得回退到进程 `~/.config/notion`、ambient env、浏览器值或其他 actor。
10. 同步取消必须把 policy 从 `syncing` 转为可重试错误，不能永久卡住 scheduler。

## 4. 架构方案选择

| 维度 | 1. 完整迁移独立 CLI | 2. 保留 CLI，Dream 管连接与 hook | 3. Dream 重写 OAuth/API |
|---|---|---|---|
| 用户体验 | 仍要协调 CLI home | 现有 device flow，无新增输入 | 可定制但重建成本高 |
| 用户隔离 | 仍需额外 wrapper | actor agentdata + thread projection | 需新 token store |
| Runtime | Agent 容易接触 CLI | Read hook 使用服务器投影 | 需新 API client |
| 单一消费协议 | CLI 命令与文件并存 | Agent 只使用 `.notion` Read | 可做到但改动大 |
| 测试/回滚 | 中高 | 最小 | 最高 |

选择方案 2：`ntn` 仅是 Dream 后端的认证/API driver；Dream 拥有连接、用户隔离、index 同步、thread 投影和 Read hook。删除 Agent-visible CLI/MCP 正式路径。

拒绝方案 1，因为它保留产品状态与 CLI 状态双真相；拒绝方案 3，因为当前没有证据要求重写 OAuth、token 生命周期和 Notion API 版本适配。

## 5. 产品交互

### 5.1 连接、重新连接与断开

- “连接 Notion”启动服务器 device flow；页面只展示验证链接、验证码和认证状态。
- 重新授权在用户独立 pending home 完成，成功后原子替换 credential source；正在运行的 turn 不热替换。
- 重新授权失败或过期时，若旧 credential 仍有效则保留旧 source；前端显示“部分可用”，而不是把连接误报为过期。
- 断开不删除 Notion 侧数据且可重新连接恢复，因此不增加确认弹窗；删除 connector、actor credential/index source 和已有 thread credential/index projection。

### 5.2 选择与索引同步

- 用户保存选中资源后立即触发首次轻索引；无需先发起 Chat。
- 资源发现消费全部 search cursor，只保留 ID、标题、URL、更新时间和选择所需 schema，不保存上游原始响应。
- 空 selection 是显式 fail-closed 配置：保持授权连接，清除 current identity/index 和最近成功时间。
- 页面在构建中显示“正在更新 Notion 索引”，不能显示“内容已同步”。
- 成功后显示“索引已同步”、来源数、最近成功与下次计划；正文在对话实际读取时获取。
- “立即同步”只是主动刷新 index，不下载页面正文。

### 5.3 策略设计

- `default` 是服务器默认；用户操作只推进 `desired`；校验后产生 `effective` 和更高 `revision`。
- `status` 为 `applied / syncing / error / disabled`；旧 LKG 存在时同步失败不删除它。
- 频率选项来自后端 DTO，不把技术常量包装成产品配额。

### 5.4 Agent 使用

1. `.notion/README.md` 和每轮 workspace context 都索引已安装的 `notion-session` Skill、`skills/notion-session/SKILL.md` 指令入口与 `.claude/skills/notion-session` Runtime 发现别名。
2. 请求需要搜索或读取已连接 Notion 时，Agent 使用该 Skill，先读取 `.notion/connector.json` 和 `.notion/index.json` 定位范围/页面 ID。
3. 只看一个数据库时读取 `.notion/databases/<database_id>.json`。
4. 只有需要正文时读取 `.notion/pages/<page_id>.json`。
5. hook 校验当前 index 后实时读取 Markdown；Agent 不感知 CLI、凭证路径或内部参数。

每个新 turn 投影前，provider 必须把 actor LKG 与当前 connector resources 求交。数据库仅保留当前选择的数据源及其页面，独立页面仅保留当前选择 ID；connector projection 只含公开连接摘要，不得包含 `user_id`、config、授权会话或验证码。范围缩小优先于 LKG 保留。

## 6. 失败状态与反馈

| 条件 | 系统行为 | 用户可采取的下一步 |
|---|---|---|
| 未连接/过期 | Read 返回 `NOTION_AUTH_REQUIRED`，不请求 API | 在“资源链接 → Notion”连接或重新连接。 |
| ID 未选择 | Read 返回 `NOTION_RESOURCE_NOT_SELECTED`，不请求 API | 选择页面或所属数据库并同步 index。 |
| 403 | 仅本次 Read 返回 `NOTION_PERMISSION_DENIED` | 在 Notion 授予该页面，或重新连接。 |
| CLI/API 不可用 | 返回 capability/request failed，错误脱敏 | 稍后重试；普通回答继续。 |
| index 同步失败 | 保留旧 current，pending 不误报 synced | 立即重试或等待下一次策略同步。 |
| Skill/hook 初始化失败 | 不改变 Agent turn；Read 安全失败 | 继续非 Notion 对话，服务恢复后重试。 |
| Workspace Mode 关闭 | 不投影 `.notion`/credential | 普通对话继续；启用后新 turn 使用。 |

## 7. 多用户、安全与隐私

- user hash 使用 domain separator；A 的 provider、connector 和 thread 不能加载 B 的 source。
- auth/index/thread/temp 路径拒绝 symlink、越界、错误类型和过宽权限。
- `.notion-home` denyRead/denyWrite；`.notion` denyWrite；临时正文 0600 且 turn 结束删除。
- `ntn` 子进程使用显式 home 和最小环境，ambient `NOTION_HOME` / `NOTION_API_TOKEN` 无权覆盖。
- 原始 stdout/stderr、token、auth JSON、home path 和正文不进入日志、HTTP 错误或测试快照。

## 8. 兼容、迁移与回滚

- 公开 `/api/connectors*`、PostgreSQL schema 和 snapshot identity 字段保持；`pageCount` 改为 index 条目数而非嵌入正文数。
- 新 producer 强制 `pages={}`；thread projector 即使读取 legacy current 也只投影 index 并清理所有静态 page 文件；下一次成功同步再把 actor 旧正文 current 替换成轻索引。
- `.notion/pages/<id>.json` 路径保留，但从静态 page 文件改为 Runtime Read hook，Agent 文件体验不变。
- 内置 Skill 仍由 backend-owned 目录刷新；其他用户 Skill 不变。
- 回滚 Dream 制品不需要 schema 回滚；禁止恢复共享 process home 或 Agent CLI fallback。

## 9. 验收标准

1. index builder 分页枚举 ID，测试证明不调用 `get_page`/markdown/blocks。
2. 新 current `pages={}`，体积与页面正文大小无关；真实 5 来源在合理的索引查询时间内发布。
3. selection 初始为 pending，只有精确 ID 随成功 index 提交后 synced。
4. Agent 默认工具和 Skill 不包含 `mcp__notion__*`、`ntn`、Bash 或 credential path。
5. `Read(.notion/pages/selected.json)` 实时返回 Markdown；未选 ID 不发远程请求。
6. A 不能使用 B 的 credential/index；ambient env 不能覆盖 thread projection。
7. 正文只进入 thread `.claude-tmp` 0600 临时文件并在 turn 结束清理。
8. auth/permission/API 错误脱敏且只影响该次 Read；普通 turn/resume/cancel/SSE 不变。
9. 定时同步与保存 selection 不依赖 Chat；Chat 初始化不运行 index builder。
10. 后端、Runtime、前端、Skill 和文档自动化测试通过；真实账户链路只有在按本机真实业务测试协议执行后才能作为当次验收证据。

## 10. 反过度设计评审

### 保留

- actor agentdata、credential staging、thread projection、原子 LKG、现有 scheduler/config policy。
- 固定 `ntn` 作为 Dream-owned driver；现有 `.notion` 文件协议和 PreToolUse redirect 模式。
- connector/resource/snapshot PostgreSQL 表和公开 API。

### 删除

- 后台逐页 Markdown/blocks 同步、snapshot page body、静态 `.notion/pages/*.json` 正文。
- Agent-visible Notion MCP、Agent CLI/Bash 与 `NOTION_HOME` 指令。
- selection 即 synced 的假状态、Chat 初始化远程同步和浏览器伪成功 fallback。

### 延期

- 增量 cursor/webhook、跨副本租约、全文搜索、附件、写入、多账号、任意远程 filter/sorts。
- 通用第三方 connector hook 框架；当前没有第二个实现验证抽象。

结论：一个后台“轻索引发布”路径、一个 Runtime“单页按需 Read”路径，职责互补且没有两套正文读取协议；不新增服务、表、队列或控制通道。

## 11. 项目职责

- `ink-dream-memory`：唯一受影响项目，拥有 connector、Runtime hook、Skill、前端、workspace、文档和测试。
- `ink-admin-memory`：本次无 schema/capability 变化，不创建迁移任务。
- 生产部署：不在本次范围；只验证当前本机代码与真实账户链路。

业务时序见 [runtime-credential-and-skill-sequence.md](runtime-credential-and-skill-sequence.md)，上游差异见 [upstream-gap-and-sync-review.md](upstream-gap-and-sync-review.md)。
