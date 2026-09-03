<!-- [Input] Dream actor/thread Notion projections, Claude Agent SDK 0.2.144, Runtime 0.1.3 baseline and published 0.1.4, restored Claude Code 2.1.88 source reference, and real Chat evidence from 2026-08-30. -->
<!-- [Output] Root-cause matrix, user interaction contract, minimal remediation decisions, business impact scope, and acceptance gates for Notion CLI environment delivery and PreToolUse routing to Agent Bash. -->
<!-- [Pos] Focused remediation design for the Dream-to-Runtime Notion CLI boundary; the broader credential/index product model remains in runtime-credential-and-skill-design.md. -->
<!-- [Sync] 2026-08-30: record the digest-bound Runtime 0.1.4 real Chat acceptance and completed same-SHA public release. -->
<!-- [Sync] 2026-09-04: separate the Dream PreToolUse .dream-guard collision from the earlier Runtime env defect and record the narrow actor-bound read-command remediation. -->

# Notion CLI Agent Bash 环境修复设计

Status: Runtime environment fix released and real-business verified; Dream PreToolUse remediation implemented and provider-free verified
Updated: 2026-09-04
Scope: 当前 actor/thread 的 Notion CLI 凭证从 Dream 投影到 Agent Bash 与只读 `ntn` 验收

## 1. 背景与问题

普通交互式 shell 中没有 Notion CLI 变量并不能说明 Dream 注入失败。服务器不应把某个 actor 的凭证写入用户 shell profile，也不应让 Dream 父进程的所有子进程继承该凭证。验收对象只能是通过正常 Chat 入口、由 Dream 为当前 actor/thread 启动的 Agent Bash。

2026-08-30 的真实 Chat 基线同时证明了两个不同事实：

- 当前 actor 已连接，actor credential source 与 thread `.notion-home` 都存在；Dream 对实际 thread 解析出的 Runtime 环境为 home、API token、文件认证模式存在，workers 配置不存在。
- 同一 thread 的首轮和继续轮 Agent Bash 都把三个目标变量报告为 `unset`。已安装 Runtime 0.1.3 的生产 sandbox 在最终 Bash spawn 前只保留通用 shell allowlist，因此删除了 Dream 已放入 Runtime 进程的 Notion 绑定。

当前 actor source 没有 `workers.json`，所以 `NOTION_WORKERS_CONFIG_FILE` 未设置是符合 `ntn 0.15.1` 合同的可选状态；它不能与另外两个被错误过滤的变量合并为同一个根因。

## 2. 目标与非目标

### 2.1 目标

- 精确追踪 credential source → thread projection → `sdk_env` → SDK `options.env` → native Runtime → Agent Bash → `ntn`。
- 只让当前 actor/thread 的 server-owned Notion 绑定进入生产 Agent Bash。
- 新 turn 与 resume 都在本次 Runtime 启动时读取最新 thread projection，不复用旧 session 环境。
- 缺少 CLI、连接、workspace、token 或 workers 配置时 fail closed，并让普通 Chat、其他 Skill、Hook、MCP、turn、resume、cancel、EventBus 与 SSE 保持原语义。
- 自动化和真实验收只输出存在状态、来源类型、Runtime 身份和命令成功状态，不输出凭证值、完整环境或 Notion 正文。

### 2.2 非目标

- 不修改 `.zshrc`、`.bashrc`、launchd 或用户全局环境。
- 不把 actor 凭证放入 Dream 父进程、MCP、Hook 或其他无关子进程。
- 不新增第二个 Notion wrapper、credential store、数据库表、API、队列、服务、restart/kill/shell 控制通道或测试专用生产分支。
- 不扩展到 Hosted Notion MCP、Notion 写入、多账号、其他 connector 或部署环境分支。
- 不在 `claude-code-sourcemap/restored-src` 实现修复；该目录只提供明确版本的上游行为参考。

## 3. 概念、边界与规则

| 层 | 所有者 | 正确边界 |
|---|---|---|
| 普通交互式 shell | 本机用户 | 默认不含 actor/thread 凭证；`unset` 是预期。 |
| Dream 服务父进程 | Dream composition root | 不持有 turn 专属 Notion 绑定；只在构造本次 options 时解析。 |
| Claude Agent SDK `options.env` | Dream runner | ambient 同名值先清空，再由当前 thread projection 覆盖。 |
| native Runtime 进程 | SDK transport | SDK 显式值覆盖继承值；不重选 actor、home 或 token。 |
| Agent Bash 子进程 | Runtime production sandbox | 只继承经过 thread path 校验的四项 Notion CLI binding 和既有通用 shell allowlist。 |
| `ntn` 子进程 | Bash | 使用同一 Bash 环境；不得回退到进程用户的默认 home/keychain。 |
| resume | Dream service + SDK | session/transcript 可继续，但每轮重新投影并启动带最新环境的 Runtime。 |

规则：

1. `NOTION_HOME` 在 Workspace Mode 开启、当前 connector 已连接且精确 `.notion-home` 投影成功时存在。
2. `NOTION_API_TOKEN` 只在当前投影的 `auth.json` 能唯一、安全地解析当前 workspace token 时存在；不得从 ambient 环境补齐。
3. `NOTION_KEYRING` 在有效 thread projection 中固定为文件认证模式 `0`；用户值不能覆盖。
4. `NOTION_WORKERS_CONFIG_FILE` 仅在同一 `.notion-home/workers.json` 是真实普通文件时存在；当前真实 actor 没有该文件，因此 `unset` 正确。
5. Workspace Mode 关闭、foreign/symlink/越界 projection、缺少有效认证或 connector 不可用时，四项绑定均不得进入 Runtime/Bash。
6. Runtime 只校验和传递 Dream 已绑定的能力，不解析 actor credential file，也不创建第二套凭证真相。

## 4. 调查证据与根因判断矩阵

版本基线：Dream `837c3f715299a9d0556faf8e23035bc448f7c9f3`；Python SDK `ink-claude-dream-agent-sdk 0.2.144`；正常 Dream backend 通过受控绝对路径运行摘要绑定的 `0.1.4` darwin-arm64 executable；兼容 CLI 为 `2.1.241`。Runtime release HEAD `0ebafe95db22101cf77db2c27e73b561d3af37a6`；上游参考 `restored-src@a8a678cb6244e6770e1e421767ff0987a1d95549`（Claude Code `2.1.88`）。0.1.4 clean-room source-tree SHA-256 为 `266362ac3543ca6d5dc7a400e2a23ac718e231abb761eab8f824726ab595de81`，darwin-arm64 executable SHA-256 为 `969f9193be8750e2573e4c4ea9c3556d48687925d9f57b8ea676669d753980dd`，授权 v2 真实回执 SHA-256 为 `87f3d1c6040e5462d85e6259a5cb16509a5d26838d5299d1ba350a4ba463dbea`。

| 环节 | 预期行为 | 实际行为 | 代码/运行证据 | 是否根因 | 正确处理 |
|---|---|---|---|---|---|
| 普通 shell | 不含 actor/thread binding | 四项目标均 unset；`ntn 0.15.1` 可执行 | 变量名布尔检查；`command -v ntn` / `ntn --version` | 否 | 保持，不写全局 profile。 |
| Dream 父进程 | 不持有 turn 专属 binding | 运行中 backend PID 的四项均 unset/empty | 对 PID 仅做变量存在性检查 | 否 | 保持 composition-time 投影。 |
| actor credential source | 有认证文件；workers 可选 | `auth.json`、`config.json`、`workspaces.json` 存在，`workers.json` 不存在 | agentdata 文件名清单，不读取值 | 否 | workers 变量保持 unset。 |
| thread projection | 每轮复制当前 actor 文件 | 真实 thread `.notion-home` 存在且同样只有三文件 | workspace 文件名与 mtime | 否 | 新 turn/resume 继续原子刷新。 |
| `resolve_notion_cli_runtime_env` | 解析当前 thread，ambient 不得覆盖 | 实际 thread 得到 home/token/keyring `set`、workers `unset` | 对真实 projection 的来源类型/布尔检查；`test_sdk_env.py` | 否 | 保持 Dream 解析规则。 |
| Runner `options.env` | Notion 应作为最终 server authority | `apply_notion_cli_env_to_options` 在 user/gateway overlay 后调用 | `agent_runner.py` 调用顺序；runner focused test | 否 | 保持最终覆盖顺序。 |
| Python SDK transport | `options.env` 覆盖 inherited env | 0.2.144 合并顺序为 inherited → defaults → options → SDK version | `SubprocessCLITransport.connect()` | 否 | SDK 无需修改。 |
| Runtime 主进程 | 接受 SDK 显式环境 | 真实 Bash 下游缺失，但没有证据表明 SDK spawn 丢失 | SDK transport 代码与 Dream options 证据 | 否 | 用 compiled process test 补齐边界证据。 |
| Runtime production sandbox | 保留精确 thread-bound Notion binding | 0.1.3 `cleanEnvironment()` 只保留 `LANG/LC_*/PATH/TERM` | `src/cleanroom/sandbox/production.ts@7c7598f` | **是** | 在现有 sandbox allowlist 上增加精确、校验后的 Notion binding。 |
| Agent Bash | 看到 home/token/keyring；workers 按文件存在性 | 真实新 turn 和继续轮三个目标均 `unset` | 正常 Chat 保留的 thread，两个 Bash `output-available`/exit 0，仅状态输出 | 下游症状 | Runtime 修复后重跑同一验收。 |
| `ntn` | version/doctor/只读身份可用 | 普通 shell version 可用；Agent Bash 因 binding 被删不能认证 | `ntn --help` 明确四项环境合同；真实 Bash 状态 | 下游症状 | 修复后只读验证，不输出响应正文。 |
| resume | 每轮刷新后与新 turn 一致 | 第二轮再次被同一 sandbox allowlist 清除 | 同一真实 Chat thread 的第二个 Bash | 否（非缓存） | 不新增 resume cache；修复单一 spawn 路径。 |

结论：这是 **Runtime fork 的生产 Bash sandbox 环境继承缺陷**，并伴随一个独立但合理的“workers 配置文件不存在”状态。它不是普通 shell 检查位置问题，不是 Dream 投影、SDK 合并顺序或 resume 缓存缺陷。上游 Bash 广泛使用 `subprocessEnv()`，clean-room Runtime 有意采用更窄的 allowlist；真正缺口是 Notion 能力加入 Dream 后，Runtime allowlist/capability/build contract 未同步扩展，不能笼统描述为 Claude Code 源码迁移时漏抄某个函数。

### 4.1 2026-09-04 Dream PreToolUse 拒绝事件

Runtime 0.1.4 已正确交付 Notion 环境后，线上仍可在 Dream workspace 复现另一条独立故障：`notion-cli` Skill 发起

```text
ntn api v1/search --data '{"query":"心学","page_size":10}'
```

立即得到 `Hook PreToolUse:Bash denied this tool`。使用 production runner 的真实
`_apply_dream_surface_write_guard`、包含 `.dream/` 的临时 workspace 和同一命令，
无需 Notion credential 或远程内容即可稳定得到 Story Workspace 的通用 mutation
deny reason。这证明拒绝发生在 Bash 启动前，Runtime、workspace OS sandbox 和
`ntn` 都尚未执行。

| 边界 | 证据 | 判定 |
|---|---|---|
| `allowed_tools` | Runner 同时暴露精确 `Bash` 与 `Skill`；Auto 自定义清单也保留 `Skill`。 | 不是工具未暴露。 |
| permission mode | Dream 不依赖 native TUI permission mode 做产品裁决；PreToolUse 返回显式 allow/deny，`can_use_tool` 处理 Runtime 系统询问。 | 不是 native prompt 配置缺失。 |
| Skill | Skill frontmatter 声明 `tools: ["Bash"]`，且发布的 search/page/database/block 命令均为 read-oriented `ntn api`。 | Skill 声明正确。 |
| PreToolUse | `.dream` surface guard 在 disabled-network、full-access 与 frontend confirmation 之前执行；workspace 含 `.dream/` 时，未识别命令被保守视作 mutation。 | **直接根因。** |
| Skill provenance | SDK `PreToolUseHookInput` 只有 tool name/input/session/cwd 等字段，没有可验证的 originating-Skill identity。 | 不得依赖 prompt 名称伪造来源。 |
| actor/thread binding | 只有 service 成功投影当前 actor/thread credential 后才设置 `notion_credential_home` 并启用 Notion Skill。 | 可作为 server-owned capability gate。 |
| workspace sandbox / Runtime | 两者位于 hook allow 之后；原故障没有到达它们。 | 无需修改 sibling Runtime/SDK。 |

根因判定为 **Dream 代码缺陷**：Story Workspace 的 `.dream` 写保护错误地把跨域、
只读且本应进入普通 Bash 审批策略的 Notion CLI 调用硬拒绝。它不是“所有 Skill
Bash 都应自动执行”的产品规则缺口。

最小修复只在 Dream guard 增加分类出口：当前 turn 必须有 server-owned
`notion_credential_home`，可执行 token 必须是 literal `ntn`，endpoint 必须属于内置
Skill 已发布的 read API 集合，search/query 的 `--data` 必须是单引号包裹的 JSON
object；wrapper、绝对/相对替代路径、写/未知 endpoint、换行、拼接和命令替换均不
匹配。匹配结果仅表示“不是 `.dream` mutation”，不返回 allow：禁网模式随后硬拒绝，
Full Access 保持既有语义，Auto/手动模式仍发出原有 frontend confirmation，拒绝、
取消或确认通道缺失继续 fail closed。`ntn api` 同时加入 disabled-network 识别，避免
Full Access 越过禁网设置。

provider-free production-path 验收使用本地 fake Messages SSE provider 和
workspace-local fake `ntn` executable，经真实 SDK/manifest-qualified Runtime、启用的
sandbox、实际投影的 `notion-cli` Skill 与一次 Bash confirmation 执行固定 fixture
命令；fake 输出回到 provider，turn 正常结束。该验收不连接 Notion、不读取用户内容、
不使用真实凭证或 PostgreSQL，不能冒充真实业务验收。

## 5. 用户交互方案

Settings 只呈现业务状态、自动恢复和下一步，不呈现变量名、内部路径、SDK options、Runtime 版本或 Bash spawn 实现。

| 状态 | 页面表达 | 自动行为 | 用户下一步 |
|---|---|---|---|
| CLI 未安装 | “需要安装 Notion CLI” | 不启动连接 | 按固定安装说明安装后重试。 |
| 未连接 | “Notion CLI 尚未连接” | 普通 Chat 可用 | 连接 Notion。 |
| 投影中 | “正在准备 Notion CLI” | 当前 turn fail closed；下一 turn 重新投影 | 无需操作，完成后重试。 |
| 可用 | “Notion CLI 可用” | 新 turn/resume 自动刷新当前连接 | 无需操作。 |
| 部分可用 | “Notion 已连接，部分 CLI 能力暂不可用” | 保留 credential/index LKG；下一 turn 自动重试 | 可继续普通 Chat；必要时重试或重新连接。 |
| 失败 | “Notion CLI 暂不可用” | 局部失败不传播到 Chat 状态机 | 按页面建议安装、连接或重试。 |

workers 配置缺失本身不降低普通 API/doctor 能力，也不单独显示为错误；只有用户使用 workers 能力且该配置确实必需时，才给出对应的业务提示。

### 5.1 新 turn 与 resume

- 新 turn：先刷新 actor credential/index 到当前 thread，再构造 SDK options 并启动 Runtime。
- resume：复用 session/transcript identity，但重复同一刷新与 options 构造；已运行 turn 不热替换。
- connector 恢复、重新授权成功或 workers 文件后来出现：下一 turn 自动生效。
- connector 断开、workspace 关闭或 projection 校验失败：下一 turn 清空 binding；普通 Chat 继续。

### 5.2 多用户与 thread 隔离

- actor ID 只在 Dream credential provider 中解释；Runtime 不接收可重新选择 actor 的参数。
- Runtime 只接受 `NOTION_HOME == {canonical workspace}/.notion-home`，拒绝 foreign thread、symlink 和其他 workers path。
- ambient/user env 无权覆盖 home、token、keyring 或 workers 配置。

## 6. 兼容、迁移、回滚与可观测性

- 不迁移数据库或 credential files；现有 actor/thread projection 可直接被修复后的 Runtime 消费。
- Runtime 新制品必须声明可验证的 Notion Bash 环境 capability，Dream 只有在 exact version/manifest/capability 全部匹配时才使用；缺失时 fail closed。
- 回滚到 Runtime 0.1.3 会恢复已知的 Notion Bash 不可用状态，但不得回滚 Dream 到 ambient credential fallback。
- 日志/测试只记录层、变量是否非空、来源类型、workspace/thread 的非敏感 identity、Runtime version/commit/checksum、命令 exit 状态；禁止记录 token、完整环境、Notion API body 或页面正文。

## 7. 实现前反过度设计评审

### 保留

- Dream actor credential source、每 turn thread projection、`resolve_notion_cli_runtime_env`、SDK 最终 authority 顺序。
- Runtime 现有 production sandbox、默认拒绝网络、精确 workspace/tmpdir 与 process-tree lifecycle。
- 同一 `ntn` 驱动和现有 `notion-cli` Skill；普通 Chat/Hook/MCP/Read hook 不变。

### 修改

- Runtime production Bash 的窄 allowlist：仅加入通过 exact workspace 校验的 Notion binding。
- Runtime sandbox 网络/可执行读取策略：只加入 `ntn` 只读验收实际需要的生产 hosts 和 canonical executable，且必须由真实 OS sandbox 测试证明。
- Runtime capability/build/version 文档与 Dream exact manifest requirement。
- 自动化测试与真实 Chat 验收，覆盖新 turn、resume、ambient/跨 actor/thread 拒绝和 optional workers。

### 删除

- 不删除现有 credential/projector 或安全 allowlist。
- 若调查期间存在把值写入用户 shell、第二套 wrapper/store 或仅手工 `export` 的临时方案，应删除且不得合入。

### 延期

- Hosted Notion MCP、Notion 写入、workers 产品界面、多账号、通用 connector env framework、热更新运行中 Runtime。

结论：不需要修改 Dream `sdk_env` 合并顺序，不需要新增凭证投影；最小改动位于 Runtime 生产 Bash boundary 及其 capability/build contract。

## 8. 真实业务验收影响说明

| 概念/事实 | Source of truth | 写入/同步 owner | 可见消费者 | 预期影响 |
|---|---|---|---|---|
| 当前 actor Notion 连接 | PostgreSQL connector + actor credential source | 现有 Settings auth flow | Settings Resource Links | 必须保持不变。 |
| 当前 thread credential projection | `{thread}/.notion-home` | Dream service 每 turn 投影 | Runtime/Read hook/Agent Bash | 每 turn 刷新；不得跨 thread。 |
| Chat thread/session | PostgreSQL thread + Claude session | ClaudeAgentService | Chat history/status | 新 turn 后 resume 同一 thread。 |
| Notion API identity | Notion 只读 identity endpoint | `ntn` | Agent 的安全结论 | 只读成功；不持久化正文。 |
| Notion 页面/资源/策略 | Notion 与现有 connector selection | 用户/既有 sync worker | Settings/索引 | 不在范围，不得改变。 |
| 普通 Chat | 既有 turn/EventBus/SSE | ClaudeAgentService | Chat UI | Notion 局部失败或成功均不得回归。 |

真实验收保留本轮 thread 与正常 Gateway/Admin 记录；不清理既有 connector、凭证、selection、历史 thread 或账本。

## 9. 验收标准

1. 当前 actor/thread 有效时，compiled Runtime 的真实 production Bash 看到 home/token/keyring；workers 只在文件存在时看到。
2. ambient 同名值、用户值、foreign actor/thread、symlink、越界 home/workers path 均不能进入 Bash。
3. Workspace Mode 关闭或 credential projection 缺失时四项均不可用，普通 Chat 仍完成。
4. source unit、真实 OS sandbox 子进程、provider-free compiled Runtime + fake Messages SSE 三层测试通过；不能只断言 Python `options.env`。
5. `ntn --version`、`ntn doctor` 或等价只读 identity 在真实 Agent Bash 中成功，输出不含 token、完整环境或 API body。
6. 同一真实 thread 的新 turn 与 resume 都重新获得最新 binding；无旧 session env cache。
7. Dream、Runtime 相关测试、构建、manifest/capability、Markdown inventory/path 和 `git diff --check` 全部通过。
8. 只有完成正常 Dream/真实账户/公开 Chat 验收后，才能把状态改为 Implemented and verified。
9. Dream PreToolUse 修复必须证明 Auto/手动/Full Access/禁网、批准/拒绝/取消/确认通道缺失、actor binding、合法 endpoint、wrapper/拼接/替换/未知 endpoint 和非 Notion Bash；真实 Runtime 验收只使用 fake provider 与 fake `ntn`，不得读取真实 Notion 内容。

业务时序见 [runtime-credential-and-skill-sequence.md](./runtime-credential-and-skill-sequence.md)。

## 10. 完成性审计

| 原始要求 | 权威证据 | 当前判定 |
|---|---|---|
| 区分普通 shell、Dream、SDK、Runtime、Bash、`ntn` 与 resume | 本文第 3、4 节；真实旧版 Chat 基线 | 已证明。 |
| 逐变量解释 API token、keyring 与 workers | 本文第 3、4 节；当前 actor/thread 只有 `auth.json`/`config.json`/`workspaces.json` | 已证明；workers 当前 `unset` 正确。 |
| 明确 commit 的 upstream/fork 对比 | `restored-src@a8a678cb6244` 的 `subprocessEnv()`；Runtime `7c7598f` 的 production allowlist | 已证明为 clean-room capability 缺口，不是笼统迁移漏拷。 |
| 交互设计、六类 Mermaid 时序、反过度设计 | 本文第 5、7节；`runtime-credential-and-skill-sequence.md` 第 4–9 节 | 已完成。 |
| Dream projection、ambient 覆盖、A/B actor、foreign thread、Workspace Mode | Dream focused suite | 203 passed、1 skipped、122 subtests；已证明。 |
| Runtime 源级、真实 OS sandbox、compiled fresh/resume、MCP/helper 隔离 | Runtime focused suite 与 `bun run test` | 14/14 focused；125 passed、5 external-fixture skips；已证明。 |
| 稳定 capability 和五包生成证据 | `runtime/cleanroom-artifact-policy.json` → 五份 generated `manifest/capabilities.json` | `sandbox.notion-cli` 已证明；formal four-target/five-package lane 通过。 |
| 正常 Dream 真实账户、公开 Chat 的新 turn/resume/`ntn`/普通 Chat | `frontend/e2e/notion-cli-runtime-real.spec.ts`；保留 thread `4ce9fd1a-1244-4893-ab68-a81de14396bb`；Runtime v2 回执 | **已验证**；Playwright 1/1 passed（1.8m），3 turns，6 个 Bash parts 全为 `output-available`；fresh/resume 两轮均为 token/keyring `set`、workers `unset`、`ntn 0.15.1`、doctor/identity `ok`，普通 Chat 无新增 Bash。 |
| 版本绑定业务资格、四平台资格、npm 发布、registry 安装 | Runtime publication policy 和 Dream exact manifest gate | **已完成**；qualification `33306855166`、publish `33306940462` 成功，五包 registry fresh install 与 Dream 0.1.4 原子版本面通过。 |

因此，本问题的本机实现、真实 Dream 验收、四目标 release qualification、registry 回下载、公网五包发布和 Dream 0.1.4 版本采用均已完成。真实业务回执与 provider-free registry 验收继续保持独立证据语义。
