# TASK-REQUIREMENT — task_238_shared_deck-task-contract-normalization

Status: Filled Prompt for Model Execution  
Updated: 2026-08-01  
Domain: `shared`（cross-cutting task 合同纠偏）

> 本文件由 `docs/task/TASK-REQUIREMENT-FORMAT.md` 填充而来，是 [SUO-238](/SUO/issues/SUO-238) 的执行提示词，不是最终 task 文档或 Stage 排期。

## Optimized Prompt

你是 `TaskDesignAgent`，负责项目管理流水线 `design → issue → task → stage` 中唯一的 task 阶段规划工作。请基于以下已冻结输入，立即修订 `docs/task/` 中所有受 Deck-only 裁决影响的任务合同，并完成最小充分验证。不要输出实现代码，不要修改 task 目录之外的任何文件，也不要把本 prompt 当作最终任务文档。

### 1. Issue 上下文

| 字段 | 填充值 |
|---|---|
| 执行 Issue | `[SUO-238](/SUO/issues/SUO-238)` |
| 标题 | `[task] 统一 Deck 任务合同、依赖与验收口径` |
| 背景 | [SUO-235](/SUO/issues/SUO-235) 裁决 Deck 为唯一业务模块；早期 task 仍保留独立旧配置域的 owner、字段、类型、服务、API 与旧 canonical 引用，需要在 task 层传播已冻结的 design/issue 真相。 |
| Domain | `shared`（覆盖 backend、frontend 与 shared task） |
| 优先级 | `medium` |
| 状态 / Work mode | `in_progress` / `standard` |
| Assignee | `TaskDesignAgent` (`87a68471-07aa-40e1-8783-4c0f6dd7fd02`) |
| Parent / Ancestor | [SUO-235](/SUO/issues/SUO-235) → [SUO-216](/SUO/issues/SUO-216) |
| 已解除依赖 | [SUO-250](/SUO/issues/SUO-250)（design canonical 迁移，done）、[SUO-251](/SUO/issues/SUO-251)（issue 口径清理，done） |

### 2. 权威输入

按如下优先级消费：

1. `docs/design/deck/deck-integration-delta.md` — Deck integration 唯一当前 canonical；
2. `docs/design/deck-plugin-voice-ink-dream-integration.md`；
3. `docs/issue/ISSUES_deck-plugin-voice-ink-dream-integration.md`；
4. `docs/issue/ISSUES_story-workspace.md` 及 Episodes 增量清单；
5. `docs/task/` 中所有受影响 task 与 completion report。

如果 design 与 issue 存在影响本修订的矛盾，停止受影响写入，将当前 Issue 标记 `blocked`，并点名 `DesignArchitect` 或 `IssueDispatcher` 的具体解锁动作；不得反向改写上游。

### 3. 必须传播的 canonical 合同

- Deck 是唯一业务模块与配置 owner；Deck 编辑器、Deck 插件、Agent profile、插件运行配置、secret-ref、权限和不可变运行快照均属于 Deck 内部能力。
- 不得保留独立旧配置模块、service、API namespace、owner、profile/config 域或权限域。
- 规范类型：`DeckAgentProfile`、`DeckPluginRuntimeConfig`、`DeckRuntimeSnapshot`。
- 规范字段：`deck_runtime_profile_id`、`deck_runtime_snapshot_id`、`deck_runtime_snapshot_contract`、`deck_runtime_snapshot_policy`。
- Ink-Dream 只保存 Deck 版本、binding/revision、运行快照引用与脱敏摘要；不得保存提示词正文、secret 或完整高敏配置。
- 单次 run 固定 `deck_plugin_id + deck_plugin_version + deck_runtime_snapshot_id + runtime_plugin_lock_id`；默认重试沿用原来源并创建新 run/session，改选、升级或刷新快照创建新运行。
- 规范错误码至少包含 `DECK_RUNTIME_CONFIG_INVALID`、`DECK_RUNTIME_CONFIG_INCOMPATIBLE`、`DECK_RUNTIME_CONFIG_UNAVAILABLE`、`OUTPUT_CONTRACT_INVALID`；移除旧配置域错误码。
- `pending_review` 是唯一 API 审阅态；`awaiting review` 只能作为 UI 文案。
- Deck integration 引用只能指向 `docs/design/deck/deck-integration-delta.md`，不得引用已迁移的旧 delta 路径。
- 当前业务语义中的旧独立配置域名称、字段前缀与组合名必须消除；历史审计若保留，必须显式标注“已废弃口径”。

### 4. 修订范围与方式

1. 扫描 `docs/task/` 全目录，覆盖后续新增的 frontend、backend、shared task 与 completion report。
2. 对每一处旧口径按上下文重写：保留配置版本、不可变快照、secret-ref、权限、preflight、审计和回滚语义，并统一归属 Deck；禁止只删词造成合同缺失。
3. 修正 task 之间的依赖引用：不存在的 task 引用必须改为已有 task，或显式写成 canonical design/Issue gate。
4. 保留工作区已有的 task 写入边界与 execute prompt 修订；采用最小增量合并，不覆盖、重置或清理其他 Agent 的改动。
5. 受影响 task 维持 10 个标准章节；输入/输出、路径、依赖、验收、测试和风险必须可独立执行。
6. shared/full-stack 合同显式区分 frontend、backend、联调与验收边界，不拆给旧 Agent 身份。

### 5. 允许与禁止范围

允许修改：

- 本已填充 prompt；
- `docs/task/task_*.md` 中与 Deck-only 传播直接相关的最小区段；
- `docs/task/*completion-report.md` 中与当前合同直接相关的最小区段；
- `docs/task/SUO-238-completion-report.md`。

禁止修改：

- `docs/design/`、`docs/issue/`、`docs/stage/`、`docs/exec/`；
- 实现代码、测试代码、依赖锁文件、生成物；
- `docs/task/TASK-REQUIREMENT-FORMAT.md` 中由其他工作单元维护的可复用 execute 模板。

### 6. 验收与验证

1. 对旧独立配置域名称与字段前缀执行不区分大小写的 `rg` 全目录扫描：当前业务命中为 0；历史命中逐项说明废弃依据。
2. `rg -n "story-workspace-deck.*integration-delta\\.md" docs/task`：0 命中。
3. 交叉核验 `deck_runtime_profile_id`、`deck_runtime_snapshot_id`、三项 `DECK_RUNTIME_CONFIG_*` 错误码、`pending_review`、`OUTPUT_CONTRACT_INVALID` 与 design/issue 一致。
4. task 文件引用必须真实存在；否则改为明确的 canonical design/Issue gate。
5. `git diff --check -- docs/task` 通过。
6. 差异仅包含本 Issue 允许范围与预先存在、已保留的 task 改动；不得修改上游或 Stage。

### 7. 输出与完成报告

最终交付包含本 prompt、修订后的 task 文档与 `SUO-238-completion-report.md`。完成报告和 Issue 评论记录变更文件、canonical 映射、验证结果、最终剩余命中、blocker、rollback 与 review 建议。全部完成且无后续工作时将当前 Issue 标记 `done`；若存在上游矛盾，则标记 `blocked` 并点名 owner/action。

立即执行上述 task 合同修订与验证。不要只给计划或分析。
