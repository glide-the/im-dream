# Voice Decks × Ink Dream Deck Plugin 与 ClaudeAgent 集成 Issue 清单

> Issue: SUO-237 (修订版)
> 来源设计稿: SUO-218 / SUO-236 (deck-plugin-voice-ink-dream-integration.md)
> 上游: SUO-235 / SUO-217 / SUO-216 / SUO-198
> 生成 Agent: IssueDispatcher
> 生成日期: 2026-08-01
> 修订日期: 2026-08-01
> 所属流水线阶段: issue
> 上游阶段: design
> 下游阶段: task
> 下游 Agent: TaskDesignAgent

---

## 0. 文档元信息

- Issue 清单文件: `docs/issue/ISSUES_deck-plugin-voice-ink-dream-integration.md`
- 来源设计稿:
  - 主设计稿: `docs/design/deck-plugin-voice-ink-dream-integration.md` (SUO-218)
  - 补充设计稿: `docs/design/plugin-remote-interaction.md`
  - 背景设计稿: `docs/design/story-workspace/story-workspace-prd.md`
  - 背景设计稿: `docs/design/story-workspace/story-workspace-layout-design.md`
  - 背景设计稿: `docs/design/deck/deck-integration-delta.md`
  - 参考设计稿: `docs/design/deck-claude-agent.md`
- 生成 Agent: `IssueDispatcher`
- 所属流水线阶段: `issue`
- 上游阶段: `design`
- 下游阶段: `task`
- 下游 Agent:
  - `TaskDesignAgent`
- 共享设计稿来源: `docs/design/`
- 是否作为当前实现合同: 是
- 备注:
  - 本文档由 SUO-218 设计稿拆解生成，经 SUO-236 按 SUO-235 Deck-only 裁决修订。
  - 所有 Desk 引用已统一为 Deck；运行配置、不可变快照、secret-ref、权限、preflight、审计和回滚合同归属 Deck。
  - 分发去向统一为 `@TaskDesignAgent`，由 `type`、标签和范围字段表达 domain。
  - 若与设计稿冲突，以 `docs/design/` 中稳定设计稿为准。
  - 若与当前 API / 代码实现冲突，必须记录为阻塞或澄清项，不得静默覆盖。

---

## 1. 关联设计稿信息

- 主设计稿: `docs/design/deck-plugin-voice-ink-dream-integration.md` (SUO-218)
- 重点补充设计稿: `docs/design/plugin-remote-interaction.md`
- 关联设计稿: `docs/design/story-workspace/story-workspace-prd.md`
- 关联设计稿: `docs/design/story-workspace/story-workspace-layout-design.md`
- 关联设计稿: `docs/design/deck/deck-integration-delta.md`
- 参考设计稿: `docs/design/deck-claude-agent.md`

- 本清单覆盖范围:
  1. Deck Plugin 的 manifest、发布版本、安装记录、启停、升级、回滚、兼容性和权限声明
  2. Deck Plugin 发布版本到 Claude Code Plugin 精确依赖锁的映射
  3. Voice Decks 创建/编辑时的插件选择、版本可用性、校验和下一次运行生效语义
  4. Ink Dream/story-workspace、Deck 运行配置快照、ClaudeAgent 的职责与数据所有权
  5. ClaudeAgent 的声明意图、物化、会话启动、加载回执、热刷新限制和 CLI 备选路径
  6. 工作流 preflight、运行状态、幂等、重试、审计和不可变历史来源
  7. 安装、兼容、加载、运行、禁用、升级、回滚和降级路径
  8. 管理端、Deck Editor、story-workspace 的前端状态及逻辑 API/事件合同
  9. 验收条件、最小验证建议、风险、依赖和未决决策

- 明确排除范围:
  1. 任何实现代码、数据库 migration、Issue/Task/Stage/Exec 产物
  2. Claude Code 二进制、SDK control 协议或 `/plugin` TUI 的修改
  3. 公共插件 marketplace、计费、商业授权/license 服务
  4. 通用多租户插件分发平台或多节点制品复制方案
  5. Deck 工作流编辑器的画布交互细节
  6. story-workspace 已稳定的三栏布局、故事/角色/场景审阅 UI 重设计
  7. 复用 `voice.thread_id` 的普通内联聊天细节（由 `deck-claude-agent.md` 管理）
  8. Paperclip Plugin worker 模型和状态枚举的直接复用

- 关键约束:
  1. 所有业务工作流字段必须使用 `deck_plugin_*` 前缀
  2. 所有 Claude Code 运行时依赖字段必须使用 `claude_code_plugin_*` 或 `runtime_plugin_*` 前缀
  3. 禁止在跨域 API 中使用无前缀的 `plugin_id`、`plugin_version`
  4. UI 必须显示"Deck 工作流插件"和"ClaudeAgent 运行时插件"两类标签
  5. 已发布 release 不可原地修改；依赖升级产生新 release
  6. 选择/升级仅影响下一次运行；当前和历史 run 不改绑
  7. 活动 Workflow Run 禁止插件热刷新
  8. 有效能力按 manifest、审批、Deck 运行快照策略、用户/workspace、runtime 支持取交集

- 补充说明:
  - 本批 Issue 拆解基于 SUO-218 完整 design 合同，经 SUO-236 按 SUO-235 统一为 Deck-only 修订。
  - 运行配置、不可变快照、secret-ref、权限、preflight、审计和回滚合同全部归属 Deck，字段统一为 `deck_runtime_*`。
  - 5 个设计澄清项被显式路由为决策工作单或带默认假设的实施依赖，不得静默消解。
  - story-workspace 既有布局、审阅、数据表设计继续有效，本清单只增量拆解 Deck Plugin 相关能力。

---

## 2. Issue 总览表

| Issue ID | 标题 | 类型 | 优先级 | 标签 | 前置依赖 | 分发去向 |
|---|---|---|---|---|---|---|
| `DECK-001` | Deck Plugin Manifest 与发布版本模型 | backend | P0 | `deck-plugin`,`manifest`,`schema` | 无 | `@TaskDesignAgent` |
| `DECK-002` | Deck Runtime Plugin Lock 生成与不可变合同 | backend | P0 | `deck-plugin`,`runtime-lock`,`release` | `DECK-001` | `@TaskDesignAgent` |
| `DECK-003` | Deck Plugin Installation 生命周期管理 | backend | P0 | `deck-plugin`,`installation`,`lifecycle` | `DECK-001`, `DECK-002` | `@TaskDesignAgent` |
| `DECK-004` | 兼容性判定与能力交集权限 | backend | P0 | `deck-plugin`,`compatibility`,`capability`,`security` | `DECK-001`, `DECK-003` | `@TaskDesignAgent` |
| `DECK-005` | Deck 创建/编辑的插件选择与版本绑定 | shared | P0 | `deck-plugin`,`binding`,`selection`,`frontend`,`backend` | `DECK-001`, `DECK-003`, `DECK-004` | `@TaskDesignAgent` |
| `DECK-006` | Story Workspace Workflow Preflight | backend | P0 | `story-workspace`,`preflight`,`execution` | `DECK-002`, `DECK-004` | `@TaskDesignAgent` |
| `DECK-007` | Workflow Run 创建、状态与幂等重试 | backend | P0 | `story-workspace`,`workflow-run`,`idempotency` | `DECK-006` | `@TaskDesignAgent` |
| `DECK-008` | ClaudeAgent 声明式 Reconcile 与 Load Receipt | backend | P0 | `claude-agent`,`reconcile`,`materialization` | `DECK-002`, `DECK-006` | `@TaskDesignAgent` |
| `DECK-009` | ClaudeAgent Run-Scoped Session 与远程交互限制 | backend | P0 | `claude-agent`,`session`,`remote-interaction` | `DECK-008` | `@TaskDesignAgent` |
| `DECK-010` | 前端管理端插件目录与安装状态 UI | frontend | P1 | `frontend`,`plugin-admin`,`ui` | `DECK-003`, `DECK-004` | `@TaskDesignAgent` |
| `DECK-011` | Deck Editor 插件选择与版本绑定 UI | frontend | P1 | `frontend`,`deck-editor`,`binding` | `DECK-005` | `@TaskDesignAgent` |
| `DECK-012` | Story Workspace 工作流状态与错误恢复体验 | frontend | P1 | `frontend`,`story-workspace`,`status`,`error-recovery` | `DECK-006`, `DECK-007` | `@TaskDesignAgent` |
| `DECK-013` | 统一事件合同与审计 | backend | P1 | `events`,`audit`,`observability` | `DECK-007`, `DECK-009` | `@TaskDesignAgent` |
| `DECK-014` | API 路由与错误码规范 | backend | P1 | `api`,`error-codes`,`contract` | `DECK-004`, `DECK-006`, `DECK-007` | `@TaskDesignAgent` |
| `DECK-015` | 安全撤销、回滚与降级路径 | backend | P1 | `security`,`rollback`,`degradation` | `DECK-003`, `DECK-007` | `@TaskDesignAgent` |
| `DECK-016` | [决策单] Deck Plugin catalog 与 Runtime Admin 物理服务边界 | docs | P1 | `clarification`,`decision`,`architecture` | 无 | `@CEOOrchestrator` |
| `DECK-017` | [决策单] 生产 marketplace 签名、digest 与留存能力 | docs | P1 | `clarification`,`decision`,`security` | 无 | `@CEOOrchestrator` |
| `DECK-018` | [决策单] 多节点/临时 ClaudeAgent runtime 分发策略 | docs | P1 | `clarification`,`decision`,`deployment` | 无 | `@CEOOrchestrator` |
| `DECK-019` | [决策单] 安全撤销是否强制终止活动 run | docs | P1 | `clarification`,`decision`,`security` | 无 | `@CEOOrchestrator` |
| `DECK-020` | [决策单] Voice chat 到 run session 的可见 UX | docs | P1 | `clarification`,`decision`,`ux` | 无 | `@CEOOrchestrator` |

---

## 3. Issue 明细

### DECK-001

- 标题: Deck Plugin Manifest 与发布版本模型
- 类型: backend
- 优先级: P0
- 标签: `deck-plugin`,`manifest`,`schema`
- 描述:
  实现 Deck Plugin 的 manifest 模型和发布版本管理。包括 `DeckPluginManifestV1` schema 定义、字段校验（`deck_plugin_id`、`deck_plugin_version`、工作流定义引用、输入/输出 schema、能力声明、兼容性矩阵、Deck 运行配置合同、运行时依赖）、发布版本状态机（`draft` → `validating` → `published` → `deprecated` → `revoked`）。确保 manifest 不包含密钥明文和完整 Deck 运行配置 prompt，仅声明 config key 或 secret-ref 类型。

- 验收条件:
  - [ ] `DeckPluginManifestV1` schema 定义完整，包含所有设计稿 §5.1 字段
  - [ ] `deck_plugin_id` 全局稳定，`deck_plugin_version` 遵循 SemVer
  - [ ] 发布版本状态机完整，已发布版本禁止回到 `draft`
  - [ ] manifest 校验覆盖：标识唯一性、schema 结构、能力子集、来源 allowlist、完整性（禁止可变 `latest` 引用）
  - [ ] manifest 禁止包含密钥明文和完整 Deck 运行配置 prompt
  - [ ] 单元测试覆盖合法/非法 manifest、SemVer 校验、重复标识检测

- 前置依赖: 无

- 关联路径:
  - `docs/design/deck-plugin-voice-ink-dream-integration.md` §5.1, §5.2, §5.4
  - 后端: manifest schema/model/validator 模块

- 分发去向: `@TaskDesignAgent`

- 主责 Agent: `TaskDesignAgent`

- 协作 Agent: 无

- 设计决策引用:
  - `DECK-DEC-001`: Deck Plugin 是业务工作流 release
  - `DECK-DEC-002`: 发布时解析精确版本和摘要并冻结 runtime lock

- 备注:
  - 这是所有后续 Deck Plugin 相关 Issue 的基础；manifest 模型必须稳定后才能推进发布和安装。

---

### DECK-002

- 标题: Deck Runtime Plugin Lock 生成与不可变合同
- 类型: backend
- 优先级: P0
- 标签: `deck-plugin`,`runtime-lock`,`release`
- 描述:
  实现 Deck Plugin 发布时生成 `DeckRuntimePluginLock` 的能力。将 manifest 中声明的 Claude Code Plugin 版本约束解析为精确版本和制品摘要，生成不可变的 runtime lock。确保同一 `deck_plugin_id + deck_plugin_version` 的工作流定义、运行时锁、能力请求、输入/输出 schema 和 Deck 运行配置合同发布后不可变。

- 验收条件:
  - [ ] 发布时解析 `claude_code_plugins` 版本约束为精确 `resolved_version` 和 `artifact_digest`
  - [ ] 生成 `runtime_plugin_lock_id` 并与发布版本原子关联
  - [ ] 相同 `deck_plugin_id + deck_plugin_version` 不允许变更 manifest hash 或 runtime lock
  - [ ] 无不可变 digest 的来源不得标为 production-ready
  - [ ] 历史引用存在时必须保留对应制品或可验证的恢复源
  - [ ] 单元测试覆盖发布锁生成、不可变性校验、digest 缺失拒绝

- 前置依赖: `DECK-001`

- 关联路径:
  - `docs/design/deck-plugin-voice-ink-dream-integration.md` §5.3, §3.3
  - 后端: release service / lock generator

- 分发去向: `@TaskDesignAgent`

- 主责 Agent: `TaskDesignAgent`

- 协作 Agent: 无

- 设计决策引用:
  - `DECK-DEC-002`: 发布时冻结 runtime lock
  - `DECK-DEC-005`: 选择/升级仅影响下一次运行

- 备注:
  - 依赖 `DECK-001` 的 manifest 模型；需要与 marketplace/制品存储交互以解析精确版本。

---

### DECK-003

- 标题: Deck Plugin Installation 生命周期管理
- 类型: backend
- 优先级: P0
- 标签: `deck-plugin`,`installation`,`lifecycle`
- 描述:
  实现 Deck Plugin Installation 的完整生命周期管理。包括安装记录模型（`deck_plugin_installation_id`、scope、版本列表、默认版本、状态、审批能力、来源策略）、状态机（`installing` → `ready` ↔ `disabled` / `error` / `upgrade_pending` / `uninstalled`）、升级双版本切换、回滚路径。确保安装先校验 manifest、兼容性、来源、摘要和能力，再提交可见状态。

- 验收条件:
  - [ ] Installation 模型完整，包含设计稿 §6.1 所有字段
  - [ ] 状态机完整，覆盖所有合法流转和错误恢复
  - [ ] 升级采用双版本切换：目标版本 runtime lock 全部物化并完成 load smoke 后才成为 `default_version`
  - [ ] 回滚只影响默认版本或 Deck 下一次运行 binding，不改历史 run
  - [ ] 卸载默认软删除并保留历史引用；强制 purge 前证明不存在历史审计或留存义务
  - [ ] 安装响应包含 `operation_id`、`capability_diff`、`runtime_readiness`
  - [ ] 单元测试覆盖状态流转、升级回滚、并发安装、错误恢复

- 前置依赖: `DECK-001`, `DECK-002`

- 关联路径:
  - `docs/design/deck-plugin-voice-ink-dream-integration.md` §6.1, §6.2
  - 后端: installation service / state machine

- 分发去向: `@TaskDesignAgent`

- 主责 Agent: `TaskDesignAgent`

- 协作 Agent: 无

- 设计决策引用:
  - `DECK-DEC-004`: declared、materialized、loadable/loaded 分开记录
  - `DECK-DEC-008`: 重试创建新 run，回滚也不改历史

- 备注:
  - 下游禁止直接复用 Paperclip `PluginStatus` 类型；本文状态是 Deck 业务域的规范枚举。

---

### DECK-004

- 标题: 兼容性判定与能力交集权限
- 类型: backend
- 优先级: P0
- 标签: `deck-plugin`,`compatibility`,`capability`,`security`
- 描述:
  实现 Deck Plugin 的兼容性判定链和能力交集计算。兼容性判定按固定顺序执行（release 可用性 → Deck host API → ClaudeAgent contract → story schema → Deck 运行配置 snapshot contract → runtime lock 可解析 → 权限交集 → runtime plugin 已物化）。有效能力按 manifest_requested ∩ installation_approved ∩ deck_runtime_snapshot_policy ∩ user_and_workspace_grants ∩ claude_agent_runtime_supported 取交集。

- 验收条件:
  - [ ] 兼容性判定顺序固定，失败即停止并返回结构化 reason code
  - [ ] 8 步判定覆盖设计稿 §6.3 所有检查项
  - [ ] 有效能力交集计算正确，未知能力默认拒绝
  - [ ] 能力扩张升级进入 `upgrade_pending`，必须由管理员显式审批
  - [ ] 禁止用客户端版本字符串比较替代服务端兼容性判定
  - [ ] 目录响应返回结构化 reason code 与可恢复动作
  - [ ] 单元测试覆盖各维度边界与结构化 reason code

- 前置依赖: `DECK-001`, `DECK-003`

- 关联路径:
  - `docs/design/deck-plugin-voice-ink-dream-integration.md` §6.3, §6.4
  - 后端: compatibility service / capability evaluator

- 分发去向: `@TaskDesignAgent`

- 主责 Agent: `TaskDesignAgent`

- 协作 Agent: 无

- 设计决策引用:
  - `DECK-DEC-007`: 有效能力取交集

- 备注:
  - 这是 selection validation 和 execution preflight 的共同基础；需要与身份/权限服务集成。

---

### DECK-005

- 标题: Deck 创建/编辑的插件选择与版本绑定
- 类型: shared
- 优先级: P0
- 标签: `deck-plugin`,`binding`,`selection`,`frontend`,`backend`
- 描述:
  实现 Deck 创建/编辑时的插件选择、版本绑定和保存语义。Deck Editor 展示可选 release、版本差异、下一次运行生效提示。服务端只接受精确版本，禁止保存 `latest` 或范围。使用 `expected_binding_revision` 防止并发覆盖，不匹配返回 `409 BINDING_REVISION_CONFLICT`。保存产生新的 `binding_revision`，只影响下一次运行。

- 验收条件:
  - [ ] Deck Editor 插件区展示已选 release 的 `display_name`、`deck_plugin_version`、发布状态、capability 摘要
  - [ ] 版本列表展示 `ready/materializing/configuration_required/deprecated/disabled/revoked/incompatible/permission_denied/upgrade_pending` 状态
  - [ ] 选择变更提示"仅影响下一次运行；历史和当前运行不变"
  - [ ] 服务端保存只接受精确版本，返回新 `binding_revision` 和 selection validation 摘要
  - [ ] `expected_binding_revision` 不匹配返回 `409 BINDING_REVISION_CONFLICT`
  - [ ] 运行中可以预选下一版本；当前 run 继续显示自己的锁定来源
  - [ ] 前端单元测试覆盖版本列表渲染、选择交互、并发冲突处理
  - [ ] 后端单元测试覆盖 binding 保存、revision 冲突、selection validation

- 前置依赖: `DECK-001`, `DECK-003`, `DECK-004`

- 关联路径:
  - `docs/design/deck-plugin-voice-ink-dream-integration.md` §9.1, §9.2, §9.3
  - 前端: Deck Editor 插件选择组件
  - 后端: binding service / selection validation

- 分发去向: `@TaskDesignAgent`

- 主责 Agent: `TaskDesignAgent`

- 协作 Agent: `TaskDesignAgent`

- 设计决策引用:
  - `DECK-DEC-005`: 选择/升级仅影响下一次运行

- 备注:
  - 前端职责：版本列表 UI、状态展示、选择交互、revision 冲突处理、生效提示
  - 后端职责：binding 模型、保存校验、revision 并发控制、selection validation 逻辑

---

### DECK-006

- 标题: Story Workspace Workflow Preflight
- 类型: backend
- 优先级: P0
  - 标签: `story-workspace`,`preflight`,`execution`
- 描述:
  实现 Story Workspace 的权威 Workflow Preflight。按固定顺序执行 preflight 检查（身份权限 → binding revision 可用性 → manifest/hash/schema → 兼容性 → 能力交集 → Deck 运行配置 snapshot → runtime lock 物化 → preflight token 签发）。Preflight 对象包含 `workflow_preflight_id`、`status`、`error_code`、`expires_at` 等。只有未过期且与当前 `binding_revision`、输入 hash 一致的 preflight 才可创建 Workflow Run。

- 验收条件:
  - [ ] Preflight 顺序固定，失败即停止后续阶段
  - [ ] 8 步 preflight 覆盖设计稿 §10.2 所有检查项
  - [ ] 创建或复用不可变 `deck_runtime_snapshot_id`
  - [ ] 验证 runtime lock 的 declared/materialized/digest/load smoke
  - [ ] 签发一次性/有限次 `preflight_token`，绑定 binding revision、input hash、Deck 运行配置 snapshot 和 runtime lock
  - [ ] preflight 失败不启动 ClaudeAgent；不创建伪运行记录
  - [ ] 单元测试覆盖各 preflight 阶段失败、token 过期、并发 preflight

- 前置依赖: `DECK-002`, `DECK-004`

- 关联路径:
  - `docs/design/deck-plugin-voice-ink-dream-integration.md` §10.1, §10.2
  - `docs/design/deck/deck-integration-delta.md` §5.1, §7.2
  - 后端: preflight service / token issuer

- 分发去向: `@TaskDesignAgent`

- 主责 Agent: `TaskDesignAgent`

- 协作 Agent: 无

- 设计决策引用:
  - `DECK-DEC-006`: Workflow Run 使用 run-scoped ClaudeAgent session
  - `DECK-DEC-011`: Deck 运行配置预检未通过时禁止启动 Claude Agent

- 备注:
  - 与 SUO-198 的状态语义对齐；`preflight` 状态保留但 UI 的普通校验失败不伪造已启动 Agent 的运行记录。

---

### DECK-007

- 标题: Workflow Run 创建、状态与幂等重试
- 类型: backend
- 优先级: P0
- 标签: `story-workspace`,`workflow-run`,`idempotency`
- 描述:
  实现 Workflow Run 的创建、状态管理和幂等重试。包括 run 模型（保留 SUO-198 字段并新增 `deck_plugin_manifest_hash`、`runtime_plugin_lock_id`、`runtime_load_receipt_id`、`workflow_preflight_id`、`agent_session_id`、`source_voice_thread_id` 等）、状态机（`preflight` → `queued` → `running` → `output_validating` → `pending_review` → `continuing` → `completed` / `failed` / `cancelled`）、幂等启动（`idempotency_key`）、重试（创建新 run 并设置 `retry_of_run_id`，默认沿用原 release/Deck 运行配置 snapshot/runtime lock）。

- 验收条件:
  - [ ] Run 模型完整，保留 SUO-198 全部字段并新增设计稿 §11.1 字段
  - [ ] 状态机只允许规范流转；终态不可复活
  - [ ] 启动请求携带 `idempotency_key`；同 key、同 binding、同 input 返回原 run
  - [ ] 同 key 不同语义返回 `409 IDEMPOTENCY_CONFLICT`
  - [ ] 重试创建新 run，设置 `retry_of_run_id`，继承原 release/Deck 运行配置 snapshot/runtime lock
  - [ ] 改选插件/升级/Deck 运行配置变更属于新运行，不得伪装成重试
  - [ ] 运行来源、runtime lock/load receipt、Deck 运行配置 snapshot 创建后不可变
  - [ ] 单元测试覆盖状态流转、幂等启动、重试、并发创建

- 前置依赖: `DECK-006`

- 关联路径:
  - `docs/design/deck-plugin-voice-ink-dream-integration.md` §11.1, §11.2, §11.3, §11.4
  - `docs/design/story-workspace/story-workspace-layout-design.md` §5.6
  - 后端: workflow run service / state machine

- 分发去向: `@TaskDesignAgent`

- 主责 Agent: `TaskDesignAgent`

- 协作 Agent: 无

- 设计决策引用:
  - `DECK-DEC-005`: 选择/升级仅影响下一次运行
  - `DECK-DEC-006`: run-scoped session
  - `DECK-DEC-008`: 重试创建新 run

- 备注:
  - 这是 story-workspace 执行核心；需要与 Deck 运行配置 snapshot、ClaudeAgent session 紧密集成。

---

### DECK-008

- 标题: ClaudeAgent 声明式 Reconcile 与 Load Receipt
- 类型: backend
- 优先级: P0
- 标签: `claude-agent`,`reconcile`,`materialization`
- 描述:
  实现 ClaudeAgent 的声明式 reconcile 和 load receipt 生成。生产主路径为 settings 意图 + headless reconcile（`CLAUDE_CODE_SYNC_PLUGIN_INSTALL=true`），CLI 为受控备选。实现 runtime plugin 的三维状态（`declaration_status`: undeclared/declared/disabled、`materialization_status`: missing/materializing/materialized/failed、`activation_status`: inactive/loadable/loaded/load_failed）。物化幂等合同（`materialization_key`、原子发布、旧制品留存）。

- 验收条件:
  - [ ] settings 意图写入 `enabledPlugins`/`extraKnownMarketplaces`
  - [ ] headless reconcile 在第一条 query 前同步完成
  - [ ] CLI 备选路径（`claude plugin install`）受控执行，校验来源、超时、输出和审计
  - [ ] 三维状态独立记录，UI 显示"已声明但未物化"而非笼统"已安装"
  - [ ] 物化幂等：`materialization_key` 唯一、原子发布、旧制品留存
  - [ ] 加载回执 `runtime_load_receipt_id` 逐项记录插件加载状态
  - [ ] required 插件全部 `loaded` 后才能进入 `running`
  - [ ] 单元测试覆盖 reconcile 成功/失败、幂等物化、load receipt 生成

- 前置依赖: `DECK-002`, `DECK-006`

- 关联路径:
  - `docs/design/deck-plugin-voice-ink-dream-integration.md` §7.1, §7.2, §7.3, §7.4
  - `docs/design/plugin-remote-interaction.md` §4.2, §4.3, §4.4
  - 后端: reconcile service / materialization manager / load receipt generator

- 分发去向: `@TaskDesignAgent`

- 主责 Agent: `TaskDesignAgent`

- 协作 Agent: 无

- 设计决策引用:
  - `DECK-DEC-003`: 声明意图 + headless reconcile 是主路径
  - `DECK-DEC-004`: declared、materialized、loadable/loaded 分开记录

- 备注:
  - 需要与 Claude Code runtime 环境集成；多节点场景在无分发能力时 readiness 必须为 node-scoped。

---

### DECK-009

- 标题: ClaudeAgent Run-Scoped Session 与远程交互限制
- 类型: backend
- 优先级: P0
- 标签: `claude-agent`,`session`,`remote-interaction`
- 描述:
  实现 ClaudeAgent 的 run-scoped session 管理和远程交互限制。为 Workflow Run 生成隔离的 run settings，仅包含锁定插件、批准能力和 marketplace 引用。会话启动时同步 reconcile 并校验加载结果。会话内插件集合固定到运行结束。禁止活动 run 调用 `apply_flag_settings`/`reload_plugins` 改变能力集合。普通 Voice chat 的 `voice.thread_id` 只作为 `source_voice_thread_id` 记录，不直接复用为 `agent_session_id`。

- 验收条件:
  - [ ] Run-scoped session 创建时仅包含锁定插件和批准能力
  - [ ] 第一条 query 前完成同步 reconcile 与 load receipt 校验
  - [ ] 会话内插件集合固定，配置/版本变更只为下一次运行创建新会话
  - [ ] 活跃 Workflow Run 禁止 `apply_flag_settings`/`reload_plugins`
  - [ ] 已物化插件的空闲管理会话可热刷新以做 smoke，结果不自动授权生产运行
  - [ ] `voice.thread_id` 记录为 `source_voice_thread_id`，不直接复用
  - [ ] 单元测试覆盖 session 隔离、热刷新限制、Voice thread 来源记录

- 前置依赖: `DECK-008`

- 关联路径:
  - `docs/design/deck-plugin-voice-ink-dream-integration.md` §7.4, §7.5, §8.2
  - `docs/design/deck-claude-agent.md`
  - 后端: agent session manager / remote interaction guard

- 分发去向: `@TaskDesignAgent`

- 主责 Agent: `TaskDesignAgent`

- 协作 Agent: 无

- 设计决策引用:
  - `DECK-DEC-006`: run-scoped session
  - `DECK-DEC-009`: 活动 run 禁止热刷新

- 备注:
  - 与 `deck-claude-agent.md` 的 Voice chat/thread/Memory 能力复用边界需要协调。

---

### DECK-010

- 标题: 前端管理端插件目录与安装状态 UI
- 类型: frontend
- 优先级: P1
- 标签: `frontend`,`plugin-admin`,`ui`
- 描述:
  实现管理端的 Deck Plugin 目录和安装状态 UI。复用 Paperclip Settings → Plugins 的管理体验，但区分 Deck Plugin（业务工作流）和 Claude Code Plugin（运行时能力包）两类标签。展示安装项、精确版本、状态（declared/materialized/loadable）、能力、兼容、健康和错误摘要。支持安装、启停、升级、卸载动作，能力扩张升级进入显式审批。

- 验收条件:
  - [ ] 管理端列表展示名称、来源、精确版本、状态、错误摘要和安装/启停/卸载动作
  - [ ] 详情页分 Configuration / Status，展示 manifest、categories、capabilities、健康、日志和最近运行
  - [ ] UI 区分"Deck 工作流插件"和"ClaudeAgent 运行时插件"两类标签
  - [ ] 展示 declared/materialized/loadable/loaded 三维状态
  - [ ] 能力扩张升级进入显式审批流程
  - [ ] 健康状态和 `last_error` 可观察
  - [ ] 管理动作要求实例/插件管理员权限
  - [ ] 单元测试/E2E 测试覆盖列表渲染、状态展示、安装/启停交互

- 前置依赖: `DECK-003`, `DECK-004`

- 关联路径:
  - `docs/design/deck-plugin-voice-ink-dream-integration.md` §16.1, §16.2
  - 前端: plugin admin pages / components

- 分发去向: `@TaskDesignAgent`

- 主责 Agent: `TaskDesignAgent`

- 协作 Agent: 无

- 设计决策引用:
  - `DECK-DEC-010`: 复用 Paperclip UX 与控制面原则，不直接复用 worker 模型

- 备注:
  - 不直接复用 Paperclip `PluginRecord.status` 类型；Deck 域维护独立规范枚举。

---

### DECK-011

- 标题: Deck Editor 插件选择与版本绑定 UI
- 类型: frontend
- 优先级: P1
- 标签: `frontend`,`deck-editor`,`binding`
- 描述:
  实现 Deck Editor 的插件选择区和版本绑定 UI。展示已选择的 `display_name`、`deck_plugin_version`、发布状态和 capability 摘要。提供"推荐兼容版本"与"查看其他版本"，每个版本展示 `published/deprecated/revoked`、installation、runtime readiness、Deck 运行配置 contract、权限状态。选择变更提示"仅影响下一次运行"。通过 `binding_revision`/ETag 处理并发。

- 验收条件:
  - [ ] 插件区展示已选 release 的完整信息
  - [ ] 版本列表展示所有规范状态（ready/materializing/configuration_required/deprecated/disabled/revoked/incompatible/permission_denied/upgrade_pending）
  - [ ] "推荐兼容版本"与"查看其他版本"功能
  - [ ] 选择变更生效提示："仅影响下一次运行；历史和当前运行不变"
  - [ ] 配置/安装问题的 owner 与恢复入口
  - [ ] 保存时通过 `expected_binding_revision` 处理并发冲突
  - [ ] 单元测试/E2E 测试覆盖版本列表、选择交互、并发冲突

- 前置依赖: `DECK-005`

- 关联路径:
  - `docs/design/deck-plugin-voice-ink-dream-integration.md` §9.1, §9.2
  - 前端: Deck Editor plugin selection components

- 分发去向: `@TaskDesignAgent`

- 主责 Agent: `TaskDesignAgent`

- 协作 Agent: 无

- 设计决策引用:
  - `DECK-DEC-005`: 选择仅影响下一次运行

- 备注:
  - 需要与后端 binding API 紧密协作；版本列表数据来自后端目录服务。

---

### DECK-012

- 标题: Story Workspace 工作流状态与错误恢复体验
- 类型: frontend
- 优先级: P1
- 标签: `frontend`,`story-workspace`,`status`,`error-recovery`
- 描述:
  实现 story-workspace 中工作流执行状态展示和错误恢复体验。包括 Dashboard 工作流上下文条（展示 Deck 插件名称/版本、Deck 运行配置就绪状态、运行进度）、preflight 进度展示、run 状态与不可变来源展示、结构化错误码映射为用户可理解的恢复入口。覆盖状态：workflow_unselected、workflow_unavailable、deck_runtime_config_not_ready、preflight_checking、running、pending_review、failed、completed。

- 验收条件:
  - [ ] Dashboard 工作流上下文条展示 Deck 插件名称/版本、工作流摘要、Deck 运行配置就绪标记
  - [ ] 各状态（未选择/不可用/Deck 运行配置未就绪/预检中/运行中/待审阅/失败/完成）均有明确 UI 表现
  - [ ] Preflight 进度可观察（选择器只读 + Loading）
  - [ ] 运行中展示步骤进度与 `workflow_run_id`
  - [ ] 失败状态展示失败步骤/错误摘要和恢复动作
  - [ ] 历史剧本可追溯到 `workflow_run_id`、`deck_plugin_version` 与 `deck_runtime_snapshot_id`
  - [ ] 结构化错误码映射为用户可理解的恢复入口
  - [ ] 单元测试/E2E 测试覆盖各状态渲染、错误恢复交互

- 前置依赖: `DECK-006`, `DECK-007`

- 关联路径:
  - `docs/design/deck-plugin-voice-ink-dream-integration.md` §13.1
  - `docs/design/story-workspace/story-workspace-layout-design.md` §2.3, §4.5
  - 前端: story-workspace status components / error recovery UI

- 分发去向: `@TaskDesignAgent`

- 主责 Agent: `TaskDesignAgent`

- 协作 Agent: 无

- 设计决策引用:
  - `DECK-DEC-005`: 选择仅影响下一次运行
  - `DECK-DEC-011`: 预检失败禁止启动 Agent

- 备注:
  - 与 story-workspace 既有布局、审阅 UI 增量集成；不推翻既有设计。

---

### DECK-013

- 标题: 统一事件合同与审计
- 类型: backend
- 优先级: P1
- 标签: `events`,`audit`,`observability`
- 描述:
  实现统一的事件 envelope 和规范事件类型。包括事件 envelope 结构（`event_id`、`event_type`、`event_version`、`occurred_at`、`workspace_id`、`aggregate_id`、`aggregate_version`、`correlation_id`、`causation_id`）、规范事件（release published、installation status changed、materialization status changed、binding changed、preflight status changed、run created/status changed/step progressed、result persisted、security cancelled）。事件至少一次投递，消费者按 `event_id` 去重，按 `aggregate_version` 处理顺序。事件禁止携带 prompt、secret 或完整 settings。

- 验收条件:
  - [ ] 统一事件 envelope 结构完整
  - [ ] 10 类规范事件覆盖设计稿 §15.2 所有事件类型
  - [ ] 事件至少一次投递，消费者可按 `event_id` 去重
  - [ ] 同 aggregate 的 `event_version` 单调递增
  - [ ] 事件禁止携带 prompt、secret 或完整 settings
  - [ ] 前端 SSE/WebSocket 可消费脱敏投影
  - [ ] 数据库审计事件是权威来源
  - [ ] 单元测试覆盖事件生成、投递、去重、顺序

- 前置依赖: `DECK-007`, `DECK-009`

- 关联路径:
  - `docs/design/deck-plugin-voice-ink-dream-integration.md` §15.1, §15.2
  - 后端: event emitter / audit log service

- 分发去向: `@TaskDesignAgent`

- 主责 Agent: `TaskDesignAgent`

- 协作 Agent: 无

- 设计决策引用:
  - `DECK-DEC-008`: 重试创建新 run，保留审计一致

- 备注:
  - 事件系统是运行追溯和审计的基础；需要与现有事件基础设施集成。

---

### DECK-014

- 标题: API 路由与错误码规范
- 类型: backend
- 优先级: P1
- 标签: `api`,`error-codes`,`contract`
- 描述:
  实现设计稿中定义的逻辑 API 路由和错误码规范。包括管理端 API（installations、install、versions、enable/disable/upgrade/rollback、runtime-readiness、reconcile）、Deck 创建/编辑 API（plugin-options、plugin-binding、validate）、Story workspace 执行 API（workflow-preflights、workflow-runs、retry、cancel）。以及 25+ 规范错误码，每个错误码包含含义和恢复动作。客户端只展示安全文案、失败阶段、operation/run ID 和恢复动作。

- 验收条件:
  - [ ] 管理端 API 路由完整，覆盖设计稿 §14.1
  - [ ] Deck 创建/编辑 API 路由完整，覆盖设计稿 §14.2
  - [ ] Story workspace 执行 API 路由完整，覆盖设计稿 §14.3
  - [ ] 25+ 规范错误码定义完整，覆盖设计稿 §12.1
  - [ ] 每个错误码包含含义和恢复动作
  - [ ] 客户端只展示安全文案，堆栈/路径/prompt/secret 只进入受限日志
  - [ ] 安装响应包含 `operation_id`、`capability_diff`、`runtime_readiness`
  - [ ] 创建运行响应中来源字段由服务端复制，客户端不得直接提交覆盖
  - [ ] 单元测试覆盖所有 API 路由和错误码响应

- 前置依赖: `DECK-004`, `DECK-006`, `DECK-007`

- 关联路径:
  - `docs/design/deck-plugin-voice-ink-dream-integration.md` §12.1, §14.1, §14.2, §14.3
  - 后端: API gateway / route handlers / error registry

- 分发去向: `@TaskDesignAgent`

- 主责 Agent: `TaskDesignAgent`

- 协作 Agent: 无

- 设计决策引用:
  - `DECK-DEC-003`: 远程管理边界

- 备注:
  - 物理服务拆分未确认前，以下为规范逻辑路由；可以由 gateway 映射，但请求/响应语义和错误码不得丢失。

---

### DECK-015

- 标题: 安全撤销、回滚与降级路径
- 类型: backend
- 优先级: P1
- 标签: `security`,`rollback`,`degradation`
- 描述:
  实现安全撤销、回滚和降级路径。包括禁用/撤销/升级中的行为矩阵（普通禁用 vs 安全撤销对新 preflight、已 queued、已 running、历史的影响）、降级规则（仅在 manifest 明确声明 `degraded_modes` 时允许，optional 插件缺失可省略但输出 schema 不变，required 插件缺失禁止自动降级）。安全撤销可强制取消活动 run，必须记录撤销人、策略、`error_code` 和终止事件。

- 验收条件:
  - [ ] 禁用/撤销/升级行为矩阵完整，覆盖设计稿 §12.2
  - [ ] 普通禁用阻止新 binding 和新 run，不删除历史
  - [ ] 安全撤销可强制取消活动 run，记录 `SECURITY_REVOCATION` 审计
  - [ ] 降级仅在 manifest 声明 `degraded_modes` 时允许
  - [ ] 降级后输出仍符合相同 story-workspace output schema
  - [ ] required 插件缺失、能力授权不足、安全撤销均禁止自动降级
  - [ ] 升级失败保留旧版本 `ready`
  - [ ] 单元测试覆盖撤销场景、降级路径、升级失败恢复

- 前置依赖: `DECK-003`, `DECK-007`

- 关联路径:
  - `docs/design/deck-plugin-voice-ink-dream-integration.md` §6.2, §12.2, §12.3
  - 后端: revocation service / rollback manager / degradation handler

- 分发去向: `@TaskDesignAgent`

- 主责 Agent: `TaskDesignAgent`

- 协作 Agent: 无

- 设计决策引用:
  - `DECK-DEC-008`: 回滚不改历史
  - `DECK-DEC-009`: 活动 run 禁止热刷新

- 备注:
  - 安全撤销的强制终止策略需要与 `DECK-019` 决策单确认。

---

### DECK-016

- 标题: '[决策单] Deck Plugin catalog 与 Runtime Admin 物理服务边界'
- 类型: docs
- 优先级: P1
- 标签: `clarification`,`decision`,`architecture`
- 描述:
  设计稿 §22 未决项 #1：Deck Plugin catalog 与 Runtime Admin 的物理服务/API owner 未定。默认假设是保持逻辑双边界，由 gateway 聚合。风险是重复状态或循环依赖。需要 CEOOrchestrator 路由 Voice Decks/平台 owner 冻结物理边界。

- 验收条件:
  - [ ] 明确 Deck Plugin catalog 的物理服务 owner
  - [ ] 明确 Runtime Admin（runtime environment、settings 意图、marketplace allowlist、materialization）的物理服务 owner
  - [ ] 确认 gateway 聚合策略或单一服务承载方案
  - [ ] 输出决策文档，下游 Issue 引用

- 前置依赖: 无

- 关联路径:
  - `docs/design/deck-plugin-voice-ink-dream-integration.md` §22, §8.1

- 分发去向: `@CEOOrchestrator`

- 主责 Agent: `CEOOrchestrator`

- 协作 Agent: 无

- 设计决策引用:
  - `DECK-DEC-001`: 三类插件边界

- 备注:
  - 默认假设下可推进实现，但 API schema 冻结前必须解决。
  - 不是阻塞当前 issue 阶段，但阻塞 task 阶段的 API 合同冻结。

---

### DECK-017

- 标题: '[决策单] 生产 marketplace 签名、digest 与留存能力'
- 类型: docs
- 优先级: P1
- 标签: `clarification`,`decision`,`security`
- 描述:
  设计稿 §22 未决项 #2：生产 marketplace 的签名、digest 与留存能力未定。默认假设是无不可变 digest 不得 production-ready。风险是供应链和历史复现风险。需要安全/运行平台 owner 给出来源与制品合同。

- 验收条件:
  - [ ] 确认 marketplace 来源的签名/校验机制
  - [ ] 确认 artifact digest 的生成和校验算法
  - [ ] 确认制品留存策略（留存窗口、冷存储、引用计数）
  - [ ] 确认历史 release 被引用时的制品恢复能力
  - [ ] 输出安全合同文档，下游 Issue 引用

- 前置依赖: 无

- 关联路径:
  - `docs/design/deck-plugin-voice-ink-dream-integration.md` §22, §5.2, §5.3, §7.3

- 分发去向: `@CEOOrchestrator`

- 主责 Agent: `CEOOrchestrator`

- 协作 Agent: 无

- 设计决策引用:
  - `DECK-DEC-002`: 发布时冻结 digest

- 备注:
  - 默认假设下可推进实现（无 digest 禁止 production-ready），但生产部署前必须解决。

---

### DECK-018

- 标题: '[决策单] 多节点/临时 ClaudeAgent runtime 分发策略'
- 类型: docs
- 优先级: P1
- 标签: `clarification`,`decision`,`deployment`
- 描述:
  设计稿 §22 未决项 #3：多节点/临时 ClaudeAgent runtime 的分发策略未定。默认假设是当前 readiness 按具体持久 runtime environment 判定。风险是目录误报全局 ready。需要运行平台 owner 定义 artifact distribution/coordination。

- 验收条件:
  - [ ] 确认 runtime environment 的拓扑模型（单节点/多节点/临时）
  - [ ] 确认制品分发策略（共享存储/复制/拉取）
  - [ ] 确认节点一致性校验机制
  - [ ] 确认 readiness 聚合策略（node-scoped vs global）
  - [ ] 输出部署合同文档，下游 Issue 引用

- 前置依赖: 无

- 关联路径:
  - `docs/design/deck-plugin-voice-ink-dream-integration.md` §22, §7.1, §7.3
  - `docs/design/plugin-remote-interaction.md` §4.5

- 分发去向: `@CEOOrchestrator`

- 主责 Agent: `CEOOrchestrator`

- 协作 Agent: 无

- 设计决策引用:
  - `DECK-DEC-004`: settings-first 失败可观测

- 备注:
  - 默认假设下可推进实现（单节点 persistent runtime），但多节点部署前必须解决。

---

### DECK-019

- 标题: '[决策单] 安全撤销是否强制终止活动 run'
- 类型: docs
- 优先级: P1
- 标签: `clarification`,`decision`,`security`
- 描述:
  设计稿 §22 未决项 #4：安全撤销是否强制终止活动 run 未定。默认假设是普通禁用不终止；安全撤销允许强制终止并审计。风险是可用性与安全策略冲突。需要安全 owner 定义撤销等级和强制动作。

- 验收条件:
  - [ ] 定义撤销等级（普通禁用 / 安全撤销 / 紧急撤销）
  - [ ] 明确各等级对已 running run 的处理策略
  - [ ] 确认强制终止的审计要求（撤销人、策略、error_code、终止事件）
  - [ ] 确认通知/告警机制
  - [ ] 输出安全策略文档，下游 Issue 引用

- 前置依赖: 无

- 关联路径:
  - `docs/design/deck-plugin-voice-ink-dream-integration.md` §22, §12.2

- 分发去向: `@CEOOrchestrator`

- 主责 Agent: `CEOOrchestrator`

- 协作 Agent: 无

- 设计决策引用:
  - `DECK-DEC-007`: 有效能力取交集

- 备注:
  - 默认假设下可推进实现（普通禁用不终止），但安全策略冻结前必须解决。

---

### DECK-020

- 标题: '[决策单] Voice chat 到 run session 的可见 UX'
- 类型: docs
- 优先级: P1
- 标签: `clarification`,`decision`,`ux`
- 描述:
  设计稿 §22 未决项 #5：Voice chat 到 run session 的可见 UX 未定。默认假设是后台创建 run-scoped session 并展示来源链接。风险是用户可能误以为在同一线程继续。需要产品 owner 确认 fork/跳转/历史展示文案。

- 验收条件:
  - [ ] 确认 Voice chat 发起 workflow run 的 UX 流程
  - [ ] 确认 run-scoped session 的展示方式（独立面板/标签/页面）
  - [ ] 确认来源链接的展示文案和位置
  - [ ] 确认历史记录中 Voice thread 与 run session 的关系展示
  - [ ] 输出 UX 决策文档，下游 Issue 引用

- 前置依赖: 无

- 关联路径:
  - `docs/design/deck-plugin-voice-ink-dream-integration.md` §22, §8.2
  - `docs/design/deck-claude-agent.md`

- 分发去向: `@CEOOrchestrator`

- 主责 Agent: `CEOOrchestrator`

- 协作 Agent: 无

- 设计决策引用:
  - `DECK-DEC-006`: run-scoped session，Voice thread 只作可选来源引用

- 备注:
  - 默认假设下可推进实现，但 UI 文案冻结前必须解决。

---

## 4. 共享任务与依赖说明

- `DECK-001` 是后续所有后端 Issue 的前置基础；manifest 模型必须稳定后才能推进发布、安装和选择。
- `DECK-002` 依赖 `DECK-001` 的 manifest 模型；runtime lock 是发布阶段的核心产物。
- `DECK-003` 依赖 `DECK-001` 和 `DECK-002`；installation 需要 release 和 lock 才能管理生命周期。
- `DECK-004` 依赖 `DECK-001` 和 `DECK-003`；兼容性判定需要 manifest 和 installation 状态。
- `DECK-005` 是 shared 类型 Issue，由 `TaskDesignAgent` 统一规划，并在 task 文档中显式拆分各 domain 的执行边界。前端负责版本列表 UI、选择交互、并发冲突处理；后端负责 binding 模型、保存校验、revision 并发控制。
- `DECK-006` 依赖 `DECK-002` 和 `DECK-004`；preflight 需要 runtime lock 和兼容性判定。
- `DECK-007` 依赖 `DECK-006`；Workflow Run 创建依赖 preflight 通过。
- `DECK-008` 依赖 `DECK-002` 和 `DECK-006`；reconcile 需要 runtime lock 和 preflight 上下文。
- `DECK-009` 依赖 `DECK-008`；run-scoped session 需要 reconcile 完成。
- `DECK-010` 依赖 `DECK-003` 和 `DECK-004`；管理端 UI 需要 installation 和兼容性数据。
- `DECK-011` 依赖 `DECK-005`；Deck Editor 插件选择 UI 依赖 binding API。
- `DECK-012` 依赖 `DECK-006` 和 `DECK-007`；story-workspace 状态展示依赖 preflight 和 run 状态。
- `DECK-013` 依赖 `DECK-007` 和 `DECK-009`；事件系统需要 run 和 session 状态变化。
- `DECK-014` 依赖 `DECK-004`、`DECK-006` 和 `DECK-007`；API 路由需要兼容性、preflight 和 run 能力。
- `DECK-015` 依赖 `DECK-003` 和 `DECK-007`；撤销/回滚需要 installation 和 run 状态。
- 若后续发现某个 Issue 的实现范围超出当前设计稿，必须回到 Issue 评论区记录澄清，不得直接下沉到 task 阶段。
- 若某个 Issue 需要新增设计决策，必须标记 `[CLARIFICATION_NEEDED]`，由 `CEOOrchestrator` 判断是否回退到 `DesignArchitect`。

---

## 5. 分发去向说明

- `TaskDesignAgent`:
  - 统一领取 frontend / backend / full-stack / shared 类型 Issue。
  - 根据 `type`、标签、关联路径与验收条件分别规划 UI、交互、状态、接口、数据、Schema、脚本、服务端逻辑和跨端联调。
  - domain 必须写入 Issue/task 字段；不得再通过拆分 Agent 身份表达前后端边界。

- `Shared Issue` 处理规则：
  - shared 类型 Issue 必须明确主责 Agent。
  - 另一个 Agent 作为协作方。
  - 不允许 shared Issue 无主责。
  - 若主责不清，必须标记 `[CLARIFICATION_NEEDED]`。

---

## 6. 推荐推进顺序

### 第一阶段：基础模型（P0 后端基础）

```text
DECK-001 (Manifest 模型)
  ↓
DECK-002 (Runtime Lock)
  ↓
DECK-003 (Installation 生命周期)
  ↓
DECK-004 (兼容性判定)
```

### 第二阶段：选择与执行（P0 核心链路）

```text
DECK-005 (Deck 选择绑定) [shared, 需前后端协作]
  ↓
DECK-006 (Preflight)
  ↓
DECK-007 (Workflow Run)
  ↓
DECK-008 (Reconcile)
  ↓
DECK-009 (Run-Scoped Session)
```

### 第三阶段：前端体验（P1 前端）

```text
DECK-010 (管理端 UI) ──→ DECK-011 (Deck Editor UI) ──→ DECK-012 (Story Workspace 状态)
```

### 第四阶段：完善与审计（P1 后端）

```text
DECK-013 (事件审计)
DECK-014 (API 路由)
DECK-015 (撤销回滚)
```

### 第五阶段：决策单（并行）

```text
DECK-016 ~ DECK-020 (决策单，由 CEOOrchestrator 并行处理)
```

### 推进原则

1. 先完成所有无前置依赖的 P0 Issue。
2. 再推进依赖 P0 基础能力的 frontend / backend Issue。
3. shared Issue 必须在双方依赖项稳定后推进。
4. P1 Issue 不得阻塞 P0 主链路。
5. 决策单 `DECK-016` ~ `DECK-020` 可与技术 Issue 并行推进，但必须在 API/schema 冻结前解决。
6. 若发现合同字段、路径、设计范围不一致，优先暂停并记录 Issue 评论。

---

## 7. 阻塞与澄清记录

### [CLARIFICATION_NEEDED] DECK-016

- 歧义点：Deck Plugin catalog 与 Runtime Admin 的物理服务/API owner 未定
- 默认假设：保持逻辑双边界，由 gateway 聚合
- 风险：重复状态或循环依赖
- 需要确认方：`@CEOOrchestrator` 路由 Voice Decks/平台 owner
- 是否阻塞 task 阶段：否（默认假设可推进），阻塞 API schema 冻结
- 下游影响：DECK-001 ~ DECK-015 的实现合同

### [CLARIFICATION_NEEDED] DECK-017

- 歧义点：生产 marketplace 的签名、digest 与留存能力未定
- 默认假设：无不可变 digest 不得 production-ready
- 风险：供应链和历史复现风险
- 需要确认方：安全/运行平台 owner
- 是否阻塞 task 阶段：否（默认假设可推进），阻塞生产部署
- 下游影响：DECK-002, DECK-008

### [CLARIFICATION_NEEDED] DECK-018

- 歧义点：多节点/临时 ClaudeAgent runtime 的分发策略未定
- 默认假设：当前 readiness 按具体持久 runtime environment 判定
- 风险：目录误报全局 ready
- 需要确认方：运行平台 owner
- 是否阻塞 task 阶段：否（默认假设可推进），阻塞多节点部署
- 下游影响：DECK-008, DECK-009

### [CLARIFICATION_NEEDED] DECK-019

- 歧义点：安全撤销是否强制终止活动 run 未定
- 默认假设：普通禁用不终止；安全撤销允许强制终止并审计
- 风险：可用性与安全策略冲突
- 需要确认方：安全 owner
- 是否阻塞 task 阶段：否（默认假设可推进），阻塞安全策略冻结
- 下游影响：DECK-015

### [CLARIFICATION_NEEDED] DECK-020

- 歧义点：Voice chat 到 run session 的可见 UX 未定
- 默认假设：后台创建 run-scoped session 并展示来源链接
- 风险：用户可能误以为在同一线程继续
- 需要确认方：产品 owner
- 是否阻塞 task 阶段：否（默认假设可推进），阻塞 UI 文案冻结
- 下游影响：DECK-009, DECK-012

---

## 8. Issue-First 协作说明

- Issue 是最小调度单元。
- 同一 Issue 任一时刻只允许一个主责 Agent。
- shared Issue 必须有主责 Agent 与协作 Agent。
- 必须通过 Issue 评论区补充上下文、阻塞、回退和评审意见。
- 必须通过 `@mention` 唤醒目标 Agent。
- 不假设 Agent 之间存在隐式共享内存。
- 不允许绕过 Issue 直接下发 task。
- IssueDispatcher 只负责生成 Issue 清单，不直接生成 task。
- StagePlanner 只能消费 task 阶段后的任务文档。
- ExecTaskAgent 只能在 stage 阶段完成后，由 CEOOrchestrator 指派执行。

---

## 9. 校验清单

生成 Issue 清单后，已检查：

- [x] 已读取 `ISSUE-LIST-FORMAT.md`
- [x] 包含文档元信息
- [x] 包含关联设计稿信息
- [x] 声明覆盖范围
- [x] 声明排除范围
- [x] 包含关键约束
- [x] 包含 Issue 总览表
- [x] 每条 Issue 都有明细
- [x] 每条 Issue 都有 Issue ID
- [x] 每条 Issue 都有标题
- [x] 每条 Issue 都有类型
- [x] 每条 Issue 都有优先级
- [x] 每条 Issue 都有标签
- [x] 每条 Issue 都有描述
- [x] 每条 Issue 都有验收条件
- [x] 每条 Issue 都有前置依赖
- [x] 每条 Issue 都有关联路径
- [x] 每条 Issue 都有分发去向
- [x] 每条 Issue 都有主责 Agent
- [x] shared Issue 有协作 Agent
- [x] shared Issue 有唯一主责 Agent
- [x] 依赖关系可供 StagePlanner 建立 DAG
- [x] 存在 `[CLARIFICATION_NEEDED]`（DECK-016 ~ DECK-020）
- [x] 不存在 `[BLOCKED]`（默认假设下可推进）
