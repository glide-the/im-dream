# TASK-REQUIREMENT — task_275_shared_deck-supply-chain-gate-contracts

Status: Filled Prompt for Task Design  
Updated: 2026-08-01  
Domain: `shared`（覆盖 governance、backend 与 full-stack/shared 边界）

> 本文件由 `docs/task/TASK-REQUIREMENT-FORMAT.md` 的输入、边界、验收、验证与回填约束填充而来，是 [SUO-275](/SUO/issues/SUO-275) 的 **task-stage 规划提示词**。它不是最终 task 文档、Stage 排期或 ExecTaskAgent execute prompt；本阶段不得实现代码、创建 Stage/Exec 产物或宣称 production Gate 已通过。

## Optimized Prompt

你是 `TaskDesignAgent`，负责固定流水线 `design → issue → task → stage` 中唯一的 task 阶段规划。请基于以下权威输入，为 `DECK-SC-001` 至 `DECK-SC-009` 生成一对一、可独立执行、可验收、可排期的 task 合同。必须保持每个来源 Issue 条目、Task ID 与后续 Stage 映射唯一；不得合并或遗漏来源条目。

### 1. 当前 Issue

| 字段 | 填充值 |
|---|---|
| Paperclip Issue | [SUO-275](/SUO/issues/SUO-275) |
| 标题 | `[task][deck-plugin][stage-4][supply-chain] 设计生产 Gate 可执行任务合同` |
| 状态 / Work mode | `in_progress` / `standard` |
| 优先级 | `medium` |
| Assignee | `TaskDesignAgent` (`87a68471-07aa-40e1-8783-4c0f6dd7fd02`) |
| Parent | [SUO-258](/SUO/issues/SUO-258) |
| Design 裁决 | [SUO-261](/SUO/issues/SUO-261)：`no_design_delta` |
| Issue 拆解 | [SUO-266](/SUO/issues/SUO-266) |
| 标签语义 | `task`, `deck-plugin`, `stage-4`, `supply-chain` |

### 2. 权威输入与优先级

1. `docs/design/deck/design_002_deck-plugin-decision-gates.md` §4.2、§5.2、§9 中的 `DECK-GATE-DEC-017`；
2. `docs/issue/ISSUES_deck-plugin-stage4-supply-chain.md` 中 `DECK-SC-001..009`；
3. `docs/task/task_deck_001_backend_manifest-model.md`、`task_deck_002_backend_runtime-lock.md`、`task_deck_003_backend_installation-lifecycle.md`、`task_deck_008_backend_reconcile-load-receipt.md`、`task_deck_013_backend_events-audit.md`、`task_deck_014_backend_api-error-codes.md`、`task_211_frontend_plugin_admin_ui.md` 的稳定 task 约定；
4. 当前仓库真实路径与测试入口：`backend/models/`、`backend/services/deck_plugin/`、`backend/tests/`、`frontend/src/`、`backend/pyproject.toml`、`frontend/package.json`。

若 task 输入与 canonical design 冲突，停止受影响 task，记录冲突与 `DesignArchitect`/`IssueDispatcher` 的 owner/action，不得反向修改 `docs/design/` 或 `docs/issue/`。当前已知输入无阻塞性冲突。

### 3. 必须生成的唯一映射

| 来源 Issue | Task ID | Domain | 输出文件 |
|---|---|---|---|
| `DECK-SC-001` | `TASK-DECK-SC-001` | `shared` | `docs/task/task_deck_sc_001_shared_named-owner-signoff.md` |
| `DECK-SC-002` | `TASK-DECK-SC-002` | `backend` | `docs/task/task_deck_sc_002_backend_trust-policy.md` |
| `DECK-SC-003` | `TASK-DECK-SC-003` | `backend` | `docs/task/task_deck_sc_003_backend_release-integrity-verification.md` |
| `DECK-SC-004` | `TASK-DECK-SC-004` | `backend` | `docs/task/task_deck_sc_004_backend_runtime-digest-receipt.md` |
| `DECK-SC-005` | `TASK-DECK-SC-005` | `backend` | `docs/task/task_deck_sc_005_backend_artifact-retention-lifecycle.md` |
| `DECK-SC-006` | `TASK-DECK-SC-006` | `backend` | `docs/task/task_deck_sc_006_backend_cold-restore-commitment.md` |
| `DECK-SC-007` | `TASK-DECK-SC-007` | `backend` | `docs/task/task_deck_sc_007_backend_tamper-evidence.md` |
| `DECK-SC-008` | `TASK-DECK-SC-008` | `backend` | `docs/task/task_deck_sc_008_backend_restore-cleanup-drill.md` |
| `DECK-SC-009` | `TASK-DECK-SC-009` | `shared` | `docs/task/task_deck_sc_009_shared_legacy-unverified-alignment.md` |

### 4. 每份 task 的强制字段

每份最终 task 文档至少包含：任务标题、Task/来源 Issue/设计映射、domain、目标与非目标、输入/输出、实现步骤、涉及文件路径、允许修改闭集、禁止修改范围、直接依赖、下游依赖、可并行性、冻结点、execute readiness、验收条件、最小测试/验证命令、证据格式、完成信号、回滚要求、风险、clarification owner/action。

对 `shared` task 必须显式拆出 backend、frontend、治理/联调、验收边界；domain 只作为 task 字段，不通过旧 Agent 身份拆分。对 owner 签署、运营承诺、测试/演练等非代码交付，必须定义机器可读记录、可点击证据、具名签署与独立复审完成信号；“文档已写”不能作为 production-ready 证据。

### 5. Production Gate 不变量

- `DECK-GATE-DEC-017` 保持 `conditional_frozen`；TaskDesign 输出不构成 `approve`。
- 生产制品必须同时满足实际分发字节 SHA-256、RFC 8785 manifest hash、受信 DSSE/Sigstore 签名包与引用感知的可恢复留存。
- 未知/不允许算法、publisher identity 或信任根异常、签名格式错误、签名覆盖不完整、撤销状态未知、离线 trust/revocation 缓存过期、时间证明缺失/无效、恢复源不可读、required 依赖未验证时一律 fail closed。
- `legacy_unverified` 仅允许开发/测试或历史只读，不得进入 `production_ready`。
- 在真实篡改矩阵、冷恢复、引用清理证据齐全且独立 reviewer 明确 `approve` 前，Stage 4 production Gate 保持阻断。

### 6. 依赖与排期约束

基础链：`TASK-DECK-SC-001 → 002 → 003`。`004` 与 `005` 在 `003` 完成后可并行；`006` 依赖 `005`；`007` 依赖 `003 + 004`；`008` 依赖 `005 + 006`；`009` 依赖 `003`，可与 `004/005/006/007` 并行，但其 production 验收要汇总 `001..008` 的状态与证据。

`TASK-DECK-SC-001` 的具名 owner 签署是 production Gate 冻结点，不阻止受控的非生产技术实现。StagePlanner 必须能从每份文档直接读取前序、并行条件、冻结点、外部签署 blocker 与 execute readiness；不得创建从 task 反向依赖 design/issue 重写或 Stage/Exec 产物的边。

### 7. 当前 TaskDesign 写入边界

仅新增本提示词及第 3 节列出的 9 份 task 文档。禁止修改 `docs/design/`、`docs/issue/`、`docs/stage/`、`docs/exec/`、实现/测试源码、依赖锁、生成物与部署配置；禁止改写 `docs/task/TASK-REQUIREMENT-FORMAT.md` 或无关 task 文档。保留工作树既有改动，若目标路径发生并发写入则停止受影响文件并在 [SUO-275](/SUO/issues/SUO-275) 评论记录。

### 8. TaskDesign 验收与验证

1. 9 个来源 Issue、9 个 Task ID、9 个输出文件一一对应，无孤儿或重复映射；
2. 每份文档的允许路径闭集等于其“涉及文件路径”，未列路径默认禁止；
3. 每个原始验收语义均映射到 task 验收与证据，不以宽松口径替代；
4. 依赖图无环、无反向阶段依赖，并明确可并行项、冻结点与外部签署；
5. fail-closed 与 production Gate 阻断语义在所有相关 task 中一致；
6. `rg` 校验 Task/Issue ID、关键字段和占位符，`git diff --check -- docs/task` 通过；
7. 完成评论列出输出路径、Task ID、差异摘要、验证结果与未决 owner/action；完成后将 [SUO-275](/SUO/issues/SUO-275) 标记 `done`，但不得把 `DECK-GATE-DEC-017` 或 production Gate 写成已批准。

立即生成上述 9 份 task-stage 合同并执行最小充分的文档验证。不要实现代码，不要创建或填充 execute prompt，不要创建 Stage 排期。

## Optional Enhancers

- StagePlanner 可在后续 Stage Issue 中把 task 文档的“StagePlanner 输入”字段机械转换为 wave、entry condition 与 freeze point；本文件不代替该排期。
- ExecTaskAgent 可在 Stage 完成后按 `docs/task/TASK-REQUIREMENT-FORMAT.md` 为单一 task 另行生成 execute prompt；本文件不得直接用于代码执行。
