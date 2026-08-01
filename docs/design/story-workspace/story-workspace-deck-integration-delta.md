# Story Workspace × Deck × Claude Agent 集成设计 Delta

> **Design ID**: `design_001_story-workspace-prd.delta.deck-integration`
> **关联 Issue**: `SUO-215`、`SUO-236`
> **父级裁决**: `SUO-235`
> **基线**: `story-workspace-prd.md`、`story-workspace-layout-design.md`
> **最后更新**: 2026-08-01
> **设计阶段**: `design → issue → task → stage`

---

## 1. 背景与目标

Story Workspace 的稳定基线把核心流程定义为“Claude Agent 产出 → 页面渲染 → 用户审阅确认”，并已引入可选择、可追溯的 Deck 工作流。父级裁决进一步统一了领域边界：**Deck 是唯一业务模块和设计元语**；Deck 编辑器、Deck 插件、Agent 运行配置均属于 Deck 内部能力，不再拆成独立产品、服务、API owner、配置域或 Agent profile 域。

本 delta 在不丢失既有安全与追溯合同的前提下，统一以下真相：

1. Deck 保存并发布版本化工作流定义，也拥有 Agent 提示词、模型/工具策略、插件运行配置、secret-ref 和权限策略。
2. Deck 在执行前生成不可变的 `deck_runtime_snapshot_id`，供本次运行审计、重试和回滚复用。
3. Ink-Dream 选择 Deck 插件并发起权威 preflight，只保存 Deck 版本、快照引用、非敏感摘要和运行结果。
4. Claude Agent 以服务身份解析已授权的 Deck 运行快照并执行，不成为配置或业务结果的真相源。
5. 执行结果进入 `story-workspace`，继续沿用数据表渲染和审阅确认流程。

### 1.1 Delta 优先级

- 本文覆盖此前将运行配置错误拆为独立领域的口径；被覆盖内容不得继续作为当前设计真相。
- 两份基线中的桌面三栏、审阅、视觉、数据表展示及范围排除继续有效。
- “Chat 直接触发 Agent”收敛为：Chat 可以表达创作意图，但执行前必须存在有效的 Deck 插件选择、Deck 运行配置和通过的 preflight。
- Deck 编辑器仍是工作流与运行配置的创作/发布界面；本次不实现完整第三方插件运行时。

### 1.2 裁决与冲突处理

- `SUO-235` 的 Deck-only 裁决优先于本文早期的双域默认假设。
- 早期设计中的配置版本、不可变快照、secret-ref、权限、preflight、审计和回滚合同全部保留，但归属 Deck，并采用本文件定义的类型、字段与错误码。
- `DEC-009`～`DEC-011` 按当前语义修订；`DEC-019` 记录本次统一裁决。
- 下游只能消费本文件及两份已同步基线，不得拼接被覆盖的旧所有权模型。

## 2. 范围界定

### 2.1 范围内

- 定义 Deck、Deck 编辑器、Deck 插件、Deck 运行配置、Ink-Dream story-workspace、Claude Agent 的职责与所有权。
- 定义提示词/插件配置、插件选择、工作流绑定、preflight、Agent 执行和结果审阅的端到端合同。
- 定义最小数据引用、状态、错误、权限、不可变快照与版本固定原则。
- 识别对既有 issue/task/stage/exec 与实现的增量影响。

### 2.2 范围外

- 不修改 `docs/issue/`、`docs/task/`、`docs/stage/`、`docs/exec/` 或实现代码。
- 不实现 Deck 编辑器、Claude Agent 或 story-workspace 代码。
- 不设计完整插件市场、插件安装器、依赖解析器或第三方插件沙箱。
- 不增加复杂故事板/时间线画布、平台视频能力或移动端适配。
- 不改变“用户审阅 Agent 产出，而非手动从零创建故事/角色/场景”的既有边界。

## 3. 方案摘要

采用“Deck 定义与配置 → Ink-Dream 选择与 preflight → Agent 执行 → story-workspace 审阅”的四层协作：

1. **Deck**通过 Deck 编辑器编辑并发布 Deck 插件，同时版本化管理 Agent 提示词、模型/工具策略、插件运行配置、secret-ref 与权限策略。
2. **Ink-Dream story-workspace**展示可用 Deck 插件、通过 Deck API 更新权威 binding，执行 WorkflowPreflight 并记录不可变运行来源。
3. **Claude Agent**按锁定的 Deck 插件、Deck 运行快照和能力交集执行。
4. **story-workspace 审阅层**把规范化结果渲染为故事/角色/场景数据表，供用户确认、编辑或驳回。

Ink-Dream 不复制 Deck 中的提示词正文、secret 或高敏配置，只持有可审计的版本化引用和脱敏摘要；Claude Agent 只在执行期按授权读取快照。

## 4. 术语、职责与所有权

### 4.1 术语表

| 概念 | 职责 | 权威拥有内容 | 消费内容 | 明确不负责 |
|---|---|---|---|---|
| `Deck` | 唯一业务模块与配置控制面 | Deck、插件发布版本、`DeckPluginBinding`、工作流定义、Agent profile、提示词、模型/工具策略、插件运行配置、secret-ref、权限、不可变运行快照、审计元数据 | 平台能力目录、用户/workspace 授权 | story-workspace 业务结果、Claude Agent 运行日志 |
| `Deck 编辑器` | Deck 内部的创作、校验、版本化、发布和运行配置界面 | Deck 草稿与发布操作 | Deck 数据与能力目录 | 独立业务模块或独立配置 owner |
| `Deck 插件` | 可选择、版本化的剧本工作流定义产物；不是执行主体 | `deck_plugin_id`、版本、工作流、输入/输出 schema、能力声明、运行配置合同 | Deck 运行配置与用户输入 | 自行保存剧本、绕过权限调用 Agent |
| `Deck 运行配置` | Deck 内部的 Agent 执行合同 | 提示词模板、模型/工具策略、插件配置、secret-ref、权限策略、启停状态、配置版本 | Deck 插件要求、用户/workspace 授权 | 独立服务、独立 API owner 或独立 Agent profile 域 |
| `Ink-Dream story-workspace` | 工作流使用入口和结果审阅工作区 | 用户选择交互、preflight/run、非敏感输入、结果及审阅状态 | Deck 目录、`deck_plugin_binding_id`/revision、release/lock、运行快照引用、Agent 事件与结果 | 保存提示词/secret、权威保存 Deck binding、编辑 Deck、执行 Agent |
| `Claude Agent` | 按工作流合同生成规范化结果 | 单次执行上下文、短期状态、执行日志/事件 | Deck 工作流、运行快照、用户输入、workspace 上下文 | 成为配置权威源、替用户选择工作流、决定审阅结果 |

### 4.2 所有权边界

- Deck 拥有“工作流是什么、有哪些能力、输入输出长什么样，以及 Agent 用什么提示词和运行策略执行”。
- Deck 权威保存“当前 Deck 为下一次运行选择哪个发布版本”的 `DeckPluginBinding`；Ink-Dream 提供选择交互，并在 preflight/run 中保存精确 binding/revision 引用。
- Ink-Dream 拥有“发起哪次运行、非敏感输入、结果如何持久化和审阅”。
- Claude Agent 拥有“这次运行如何执行及产生哪些运行事件”，但不成为 Deck 配置或剧本结果的真相源。
- Deck 运行配置是 Deck 内部子对象，不形成新的产品、服务、API namespace 或独立权限域。

### 4.3 规范命名

| 语义 | 规范名称 |
|---|---|
| Deck 内部 Agent 配置模板 | `DeckAgentProfile` |
| Deck 插件运行配置 | `DeckPluginRuntimeConfig` |
| 运行配置 profile 标识 | `deck_runtime_profile_id` |
| 单次不可变配置快照 | `deck_runtime_snapshot_id` |
| 快照合同版本 | `deck_runtime_snapshot_contract` |
| 快照能力策略 | `deck_runtime_snapshot_policy` |

跨域 API、事件、数据模型和 UI 状态必须使用上述名称。旧字段不得与新字段并存形成双写；迁移映射由下游 Task 定义，历史记录通过只读兼容读取，不改变其原始审计内容。

## 5. 端到端交互设计

### 5.1 主序列

```mermaid
sequenceDiagram
    actor Creator as 创作者
    participant Deck as Deck / Deck 编辑器
    participant Ink as Ink-Dream story-workspace
    participant Agent as Claude Agent

    Creator->>Deck: 配置 Agent profile、提示词、插件运行配置与权限
    Deck->>Deck: 校验 schema、secret-ref、权限并激活配置版本
    Creator->>Deck: 自定义并发布 Deck 插件工作流
    Deck->>Deck: 绑定/校验 deck_runtime_profile_id 与配置合同
    Deck-->>Ink: 暴露有权使用的插件版本与脱敏 readiness
    Creator->>Ink: 选择 Deck 插件并填写非敏感创作输入
    Ink->>Deck: 保存/校验 DeckPluginBinding（精确 release + expected revision）
    Deck-->>Ink: 返回 deck_plugin_binding_id + binding_revision
    Ink->>Ink: 创建 WorkflowPreflight（binding revision + input hash）
    Ink->>Deck: 校验 release、配置、权限并请求不可变运行快照
    Deck->>Deck: 生成 deck_runtime_snapshot_id，返回 runtime_plugin_lock_id/readiness
    Deck-->>Ink: 返回 snapshot + runtime_plugin_lock_id + Deck readiness receipt
    Ink->>Ink: 完成 runtime 校验、签发 preflight token 并原子创建 workflow run
    Ink->>Agent: 提交 plugin/version、运行快照、runtime lock 与输入
    Agent->>Deck: 以服务身份解析已授权运行快照
    Deck-->>Agent: 返回执行期配置（不下发浏览器）
    Agent-->>Ink: 返回运行事件与规范化故事/角色/场景结果
    Ink->>Ink: 原子保存结果，review_status=pending
    Ink-->>Creator: 以数据表和 Review Panel 渲染结果
    Creator->>Ink: 确认 / 编辑后确认 / 驳回
```

### 5.2 详细规则

1. **配置与发布**
   - 有权限的用户在 Deck 编辑器中保存 Agent profile、提示词、模型/工具策略和插件运行配置。
   - Deck 校验必填项、schema、secret-ref 和权限；通过后激活不可变配置版本。
   - 浏览器不获得 secret 明文；提示词正文可见性由 Deck 权限控制。

2. **Deck 插件发布**
   - 创作者定义工作流名称、用途、输入、输出和能力声明。
   - 插件引用 Deck 内有效的 runtime profile/version 或兼容范围，不复制提示词正文和 secret。
   - 发布时必须校验输出可映射为 story-workspace 的故事、角色和场景数据。

3. **选择与 preflight**
   - Ink-Dream 只展示当前 workspace、当前用户有权使用且可执行的 Deck 插件版本。
   - Chat 可承载用户输入，但必须解析到同一 `deck_plugin_binding_id` 与 `binding_revision`，不能绕过 Deck 选择。
   - story-workspace 拥有 `WorkflowPreflight`；它调用 Deck 校验 release、配置、权限和 schema、生成 `deck_runtime_snapshot_id`，再校验 `runtime_plugin_lock_id` 对应的物化状态并签发短期 preflight token。

4. **执行、重试与审阅**
   - 单次 `workflow_run` 固定 `deck_plugin_id + deck_plugin_version + deck_runtime_snapshot_id + runtime_plugin_lock_id`。
   - 前端不得提交提示词正文、secret 或高敏配置；Claude Agent 使用服务身份解析快照。
   - 默认重试沿用原 release、运行快照和 runtime lock，但创建新的 run 与 Agent session。
   - 用户修改输入、改选插件、升级配置或要求刷新快照时创建新运行，不覆盖原来源。
   - 结果经合同校验后原子写入并进入 `pending_review`；不允许部分结果伪装为完整业务产出。

## 6. 最小数据与配置边界

### 6.1 最小对象

| 对象 | 权威存储 | 最小字段 | Ink-Dream 处理方式 |
|---|---|---|---|
| `DeckPluginManifestV1` | Deck | `deck_plugin_id`, `deck_plugin_version`, `display_name`, `workflow_definition_ref`, input/output schema、capabilities、status | 读取公开字段；保存版本化引用 |
| `DeckAgentProfile` | Deck | `deck_runtime_profile_id`, `prompt_version`, `prompt_template`, `model_policy`, `tool_policy`, `permission_policy`, `status`, `owner_id` | 仅保存 ID、版本、状态/摘要；不复制正文 |
| `DeckPluginRuntimeConfig` | Deck | `deck_runtime_profile_id`, `deck_plugin_id`, `config_version`, `config`, `secret_refs`, `schema_version`, `status` | 仅引用；只提交非敏感可覆盖参数 |
| `DeckRuntimeSnapshot` | Deck | `deck_runtime_snapshot_id`, profile/config versions、policy hash、secret refs、created_at | 保存受控 ID 与脱敏摘要；不复制敏感值 |
| `DeckPluginBinding` | Deck | `deck_plugin_binding_id`, `deck_id`, `workspace_id`, plugin id/version、`binding_revision`, `updated_by`, `updated_at` | 通过 Deck API 选择/读取；run 中只保存精确 ID/revision |
| `DeckRuntimePluginLock` | Deck | `runtime_plugin_lock_id`, plugin id/version、manifest hash、精确 runtime plugin versions/digests、capability bindings | preflight/run 只保存锁引用与脱敏摘要 |
| `StoryWorkflowRun` | Ink-Dream | `workflow_run_id`, `deck_plugin_binding_id`, `binding_revision`, `deck_runtime_snapshot_id`, `runtime_plugin_lock_id`, `idempotency_key`, `input_hash`, `status`, `agent_session_id`, `error_code`, timestamps | 权威保存运行来源、状态与结果关联 |
| 故事/角色/场景结果 | Ink-Dream | 既有 story-workspace 字段 + `workflow_run_id` | 沿用既有表格渲染与审阅模型 |

### 6.2 存储与消费矩阵

| 信息 | Deck | Ink-Dream | Claude Agent |
|---|---|---|---|
| Agent 提示词正文/模板 | 权威存储、版本化 | 仅引用；默认不可读正文 | 执行时按授权读取 |
| 插件运行配置 | 权威存储、校验、版本化 | 读取脱敏摘要；保存快照引用 | 执行时按授权读取 |
| secret/令牌 | 保存 secret-ref 或安全存储句柄 | 不保存、不下发浏览器 | 执行期注入，不回传结果 |
| Deck 插件 manifest | 权威存储与发布 | 读取目录并保存版本引用 | 读取执行所需声明 |
| 用户非敏感输入 | 不作为业务真相源 | 权威保存于 workflow run | 单次执行消费 |
| 插件/配置选择 | 权威保存 `DeckPluginBinding` 并提供可选版本/readiness | 提供选择交互；run 保存 binding ID/revision | 按 run 消费 |
| 生成结果与审阅状态 | 不保存 | 权威保存 | 生成后返回，不替代业务存储 |

### 6.3 版本与一致性

- 已发布的插件版本、prompt version、config version 和运行快照不得原地改写。
- 每次 run 固定版本组合并记录配置摘要 hash，保证可复现和可审计。
- Deck profile/config 停用后禁止新 run；已开始 run 默认使用已锁快照完成，安全撤销策略可以强制终止并审计。
- preflight、快照生成和 run 创建必须支持 `idempotency_key`，防止重复点击或网络重试产生重复剧本。

## 7. 状态设计

### 7.1 Deck 配置与插件状态

| 对象 | 状态 | 允许流转/含义 |
|---|---|---|
| Deck runtime profile/config | `draft` | 可编辑，不可执行 |
| Deck runtime profile/config | `active` | 已校验，可供授权插件执行 |
| Deck runtime profile/config | `disabled` | 禁止新执行，历史引用保留 |
| Deck plugin version | `draft` | 可编辑，不进入 Ink-Dream 目录 |
| Deck plugin version | `published` | 只读版本，可被授权用户选择 |
| Deck plugin version | `deprecated` | 不推荐新选择；历史 run 可追溯 |
| Deck plugin version | `disabled` | 禁止新 run |

### 7.2 Preflight readiness 与工作流运行状态

```text
WorkflowPreflight: configuring → ready / failed / expired

StoryWorkflowRun:
preflight → queued → running → output_validating → pending_review → confirmed
                │              │                 │              ├→ continuing → completed
                │              │                 │              └→ completed
                │              │                 └→ rejected（重试创建新 run）
                ├──────────────┴────────────────────────────────→ failed
                └───────────────────────────────────────────────→ cancelled
```

- `configuring` / `ready` 是 `WorkflowPreflight` readiness，不写入 `StoryWorkflowRun.status`。
- `pending_review` 是唯一 API 审阅态；`awaiting review` 仅可作为 UI 文案，不得形成第二枚举。
- `rejected`、`failed`、`cancelled` 是当前 run 的终态；重试创建新 run 并保留原记录。

## 8. 错误、恢复与可观测性

| 错误码 | 场景 | 用户可见处理 | 恢复规则 |
|---|---|---|---|
| `WORKFLOW_SELECTION_REQUIRED` | 未选择 Deck 插件 | 阻止执行并引导选择工作流 | 选择有效插件后重试 |
| `DECK_PLUGIN_UNAVAILABLE` | 插件未发布、停用、无权限或版本不存在 | 显示不可用原因，不静默升级 | 用户确认新版本后创建新 binding/run |
| `DECK_RUNTIME_CONFIG_INVALID` | Deck 运行配置缺失、未激活或过期 | 展示非敏感类别及配置入口 | Deck owner 修复并重新 preflight |
| `DECK_RUNTIME_CONFIG_INCOMPATIBLE` | 运行快照合同或 schema 不兼容 | 阻止执行并显示兼容建议 | 选择兼容 profile/release |
| `DECK_RUNTIME_CONFIG_UNAVAILABLE` | Deck 配置解析暂时不可用 | 保留输入，显示可重试错误 | 以同一 idempotency key 重试 |
| `WORKFLOW_PERMISSION_DENIED` | 用户或服务身份权限不足 | 不泄露配置细节 | 申请授权或选择其他插件 |
| `AGENT_EXECUTION_FAILED` | Claude Agent 超时、工具失败或停止 | 展示失败步骤与安全摘要 | 按同来源创建新 attempt |
| `OUTPUT_CONTRACT_INVALID` | 输出不符合 schema/contract，无法映射为业务数据 | 不写入部分业务结果 | 修复插件/配置后新 run |
| `CONFIG_VERSION_DRIFT` | 选择后执行前引用变化 | 阻止隐式切换 | 使用已固定版本或显式升级 |

最小可观测字段：`workflow_run_id`、`deck_plugin_binding_id`、`binding_revision`、plugin id/version、`deck_runtime_profile_id`、`deck_runtime_snapshot_id`、`runtime_plugin_lock_id`、`agent_session_id`、`status`、`error_code`、时间戳和配置摘要 hash。日志和 UI 不得记录提示词、secret、令牌或敏感配置值。

## 9. 权限与安全

| 动作 | 默认角色/身份 | 服务端最小校验 |
|---|---|---|
| 编辑/发布 Deck 插件 | workspace creator/editor 或 plugin owner | workspace 隔离、owner、发布权限、schema 校验 |
| 编辑/激活 Deck 运行配置 | workspace admin 或 Deck config owner | 高敏字段写权限、版本审计、secret 不回显 |
| 查看可用插件目录 | workspace member | 只返回被授权且可用的版本 |
| 选择并执行插件 | creator/editor | 对 Deck、release、runtime profile、workspace 的授权交集 |
| 读取完整运行快照 | Claude Agent 服务身份 | 短期授权、最小权限、服务端访问 |
| 审阅结果 | creator/editor/reviewer | story/workspace 审阅权限 |

安全规则：

- 所有对象必须带 `workspace_id` 或可验证的租户归属。
- 前端只获得脱敏摘要与公开 manifest；secret 与提示词运行态注入只发生在服务端。
- 有效能力为 manifest 请求、安装审批、Deck 运行快照策略、用户/workspace grant 和 runtime 支持的交集。
- 插件能力声明、manifest 或 prompt 均不能自我授权；未知能力默认拒绝。

## 10. 对下游的增量影响

> 本节只声明影响。本 Issue 不修改任何下游产物。

| 层级/产物 | 影响 | 传播要求 |
|---|---|---|
| `docs/issue/ISSUES_story-workspace.md` | 统一为 Deck 目录、运行配置、binding/run、preflight 与权限 | 下游按本设计增量修订，不保留双 owner |
| Story Workspace schema/API tasks | 增加运行快照、runtime lock、来源、错误码和幂等字段 | 采用 additive migration/兼容读取，不破坏既有故事与审阅模型 |
| Agent integration/shared types tasks | Agent 输入改为锁定的 Deck release + runtime snapshot + runtime lock | 类型源先行；前后端镜像一致 |
| Frontend/E2E tasks | 覆盖 Deck 配置 → 发布/选择 → preflight → Agent → 渲染/审阅 | 只增加组件与状态，不推翻三栏和 Review Panel |
| Stage/Exec | 需验证 Deck-only 一致性和迁移顺序 | 当前不修改；由下游负责 gate 与实现回滚 |

## 11. 验收标准

- [ ] Deck 是唯一业务模块和设计元语；不存在独立配置模块、服务、API owner 或 Agent profile 域。
- [ ] Deck 编辑器、Deck 插件、Deck 运行配置、story-workspace 与 Claude Agent 的职责无重叠歧义。
- [ ] 配置/提示词/secret-ref/权限 → 发布/选择 → preflight → Agent → 渲染/审阅的端到端流程完整。
- [ ] Ink-Dream 不存储提示词、secret 或完整高敏配置，只保存 Deck 版本、运行快照引用和脱敏摘要。
- [ ] 每次运行固定 release、Deck 运行快照和 runtime lock，支持幂等、审计、失败重试和回滚追溯。
- [ ] 类型名、字段名、错误码、participant、文件引用和决策项在相关设计稿中一致。
- [ ] 下游影响仅通过设计稿传播；本 Issue 不修改 issue/task/stage/exec 或代码。

## 12. 风险与依赖

| 风险/依赖 | 影响 | 缓解/准入条件 |
|---|---|---|
| Deck catalog、运行配置与 secret provider 的物理实现边界未冻结 | API 可能重复或循环依赖 | 对外保持单一 Deck owner/API namespace；内部拆分不外泄为新业务元语 |
| Deck Plugin manifest/schema 未稳定 | 插件无法可靠映射到结果 | 类型合同先行，发布时校验输入/输出及 runtime snapshot contract |
| 既有实现按 Chat 直触发推进 | 可能绕过工作流选择与 preflight | 使用兼容适配与 additive migration；完成迁移前保留显式 gate |
| 配置版本漂移 | 同一输入不可复现 | run 固定不可变快照与 hash；禁止静默升级 |
| secret 或提示词复制到 story-workspace | 安全与所有权越界 | 仅保存引用/脱敏状态，执行期服务端解析 |
| 紧急安全撤销策略未冻结 | 已运行任务可能继续使用旧快照 | 安全 owner 定义强制终止等级、审计与恢复动作 |

关键依赖：Deck 插件目录/发布合同、Deck 运行配置与 secret provider、Claude Agent 服务身份与 runtime load receipt、story-workspace 运行/结果 API、身份与 capability grant。

## 13. 关键决策记录

| 决策 ID | 日期 | 决策 | 影响 |
|---|---|---|---|
| `DEC-009`（修订） | 2026-08-01 | Deck 是唯一业务模块；Deck Editor、Deck Plugin、Deck 运行配置与 `DeckPluginBinding` 是 Deck 内部职责，story-workspace 消费公开合同并独立保存运行/结果 | 取消双域/双 owner 假设 |
| `DEC-010`（修订） | 2026-08-01 | 单次运行锁定 Deck 插件版本、`deck_runtime_snapshot_id` 与 `runtime_plugin_lock_id` | 切换只影响新运行，历史来源不可改写 |
| `DEC-011`（修订） | 2026-08-01 | Deck release、运行配置、权限或 runtime preflight 任一失败时禁止启动 Claude Agent | 统一失败边界与恢复动作 |
| `DEC-012`（修订） | 2026-08-01 | Deck 是提示词、插件运行配置、secret-ref、权限策略和不可变运行快照的权威源 | Ink-Dream 只保存引用与脱敏摘要 |
| `DEC-013`（修订） | 2026-08-01 | 选择 Deck 插件即更新 Deck 权威 `DeckPluginBinding`；每次执行在 run 中冻结 `deck_plugin_binding_id + binding_revision` | 消除 Deck/Ink-Dream 双 binding owner，并将选择与运行显式关联 |
| `DEC-014` | 2026-08-01 | 重试默认沿用固定来源并新建 run；改选、升级或刷新快照属于新运行 | 保证复现与审计 |
| `DEC-015` | 2026-08-01 | 既有下游产物只接受后续增量传播，不在本 design delta 中改写 | 保护流水线边界 |
| `DEC-016` | 2026-08-01 | 保持数据表、无平台视频、桌面端、无完整第三方插件运行时 | 控制范围 |
| `DEC-019` | 2026-08-01 | 按 `SUO-235` 裁决统一 Deck 术语，并将既有配置/快照/权限/审计合同归入 Deck | 本文件、PRD、layout 与 Deck Plugin 主设计同步修订 |

## 14. 增量变更说明

- **Delta 1 / SUO-215（2026-08-01）**：首次补充工作流选择、Agent 配置、binding/run、权限、错误和下游影响。
- **Delta 2 / SUO-236（2026-08-01）**：执行 `SUO-235` 的 Deck-only 裁决；重写所有权、时序、数据模型、状态、错误码、权限、依赖和决策记录。
- 运行配置、不可变快照、secret-ref、preflight、权限交集、审计、重试和回滚合同均保留，统一改为 Deck ownership 和规范字段。
- 文件与 Design ID 同步改为 `story-workspace-deck-integration-delta.md` / `design_001_story-workspace-prd.delta.deck-integration`；旧文件不再是设计真相源。

## 15. 阻塞或澄清说明

当前设计无阻塞。以下实现级未决项不改变 Deck-only 边界：

| 未决项 | 默认假设 | 风险 | Owner / action |
|---|---|---|---|
| **[CLARIFICATION_NEEDED] Deck catalog、运行配置与 secret provider 的内部部署拆分** | 对外保持单一 Deck API/owner，内部可按安全边界拆组件 | 内部拓扑泄漏为重复业务域 | Deck/平台 owner 冻结内部路由与鉴权，不新增业务元语 |
| **[CLARIFICATION_NEEDED] 插件选择主入口** | story-workspace 提供选择器并写入 Deck 权威 binding；Chat 复用同一 `deck_plugin_binding_id` | 旧路径绕过选择或产生双 binding | 产品 owner 确认主入口；后端强制同一 gate |
| **[CLARIFICATION_NEEDED] 自定义插件发布审核** | 编辑与发布权限分离，能力扩张需审批 | 未审核插件获得高敏能力 | 安全/平台 owner 定义白名单、审批和撤销策略 |
| **[CLARIFICATION_NEEDED] 安全撤销是否强制终止活动 run** | 普通禁用不终止；安全撤销可强制终止并审计 | 可用性与安全策略冲突 | 安全 owner 定义撤销等级和终止动作 |
