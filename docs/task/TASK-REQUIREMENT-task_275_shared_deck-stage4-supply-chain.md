# TASK-REQUIREMENT — task_275_shared_deck-stage4-supply-chain

Status: Filled Prompt for Task Document Generation
Updated: 2026-08-01
Domain: `shared`（覆盖治理、backend 与 full-stack/shared 对齐合同）

> 本文件依据 TaskDesignAgent 私有 `TASK-REQUIREMENT-FORMAT.md` 填充，是 [SUO-275](/SUO/issues/SUO-275) 的 task-stage 模型输入，不是最终任务文档、Stage 排期或 execute prompt。项目内 `docs/task/TASK-REQUIREMENT-FORMAT.md` 是通用 execute 模板，本 Issue 明确禁止 TaskDesignAgent 预填或改写它。

## Optimized Prompt

你是 `TaskDesignAgent`，负责项目管理流水线 `design → issue → task → stage` 中唯一的 task 阶段规划工作。请基于以下已冻结输入，为 `DECK-GATE-DEC-017` Stage 4 supply-chain follow-up 生成九份可独立执行、可验收、可排期的 Markdown 任务合同。不要实现代码，不要编排 Stage，不要生成 execute prompt，不要修改 `docs/task/` 之外的任何路径，也不得把设计完整性或 task 文档完整性写成 production Gate 已通过。

### 1. Issue 上下文

| 字段 | 填充值 |
|---|---|
| 当前 Paperclip Issue | [SUO-275](/SUO/issues/SUO-275) — `[task][deck-plugin][stage-4][supply-chain] 设计生产 Gate 可执行任务合同` |
| 来源编排 | [SUO-258](/SUO/issues/SUO-258) |
| Design 裁决 | [SUO-261](/SUO/issues/SUO-261) — `no_design_delta` |
| Issue-stage 产物 | [SUO-266](/SUO/issues/SUO-266) |
| 审批来源 | [SUO-255](/SUO/issues/SUO-255) — `request_changes` 已转为 follow-up，不构成当前 Gate approve |
| 当前状态 / Work mode | `in_progress` / `standard` |
| 优先级 | `medium`；来源条目分别为 `P0` / `P1` |
| Assignee | `TaskDesignAgent` (`87a68471-07aa-40e1-8783-4c0f6dd7fd02`) |
| Domain | `shared`（九份任务各自标注 `backend` 或 `shared`） |
| 当前 blocker | Task 文档生成本身无 blocker；生产放行仍被具名 owner、运营承诺、真实演练证据、独立 reviewer 与独立复审 approve 阻断 |
| 标签 | `deck-plugin`, `stage-4`, `supply-chain`, `signature`, `digest`, `retention`, `evidence`, `legacy` |

### 2. 权威输入与优先级

按以下顺序消费，发现冲突时采用更上游且更稳定的口径，并停止受影响的 task 细化、记录 clarification owner/action；不得反向改写上游：

1. `docs/design/deck/design_002_deck-plugin-decision-gates.md` §4.2、§5.2、§6～§9；
2. `docs/issue/ISSUES_deck-plugin-stage4-supply-chain.md` 中 `DECK-SC-001..009`；
3. `docs/design/deck-plugin-voice-ink-dream-integration.md`；
4. `docs/issue/ISSUES_deck-plugin-voice-ink-dream-integration.md` 中 `DECK-002`、`DECK-003`、`DECK-008`、`DECK-017`；
5. 已有 Deck task 合同，尤其是 `task_deck_002_backend_runtime-lock.md`、`task_deck_003_backend_installation-lifecycle.md`、`task_deck_008_backend_reconcile-load-receipt.md`、`task_deck_013_backend_events-audit.md`、`task_deck_014_backend_api-error-codes.md` 与 `task_211_frontend_plugin_admin_ui.md`。

`DECK-GATE-DEC-017` 保持 `conditional_frozen`；[SUO-261](/SUO/issues/SUO-261) 的 `no_design_delta` 表示不得改写 canonical design，不表示 production rollout 已批准。

### 3. 必须生成的唯一映射

| 来源 Issue 条目 | Task ID / 文件 | Domain | 优先级 | 直接依赖 |
|---|---|---|---|---|
| `DECK-SC-001` | `task_275a_shared_supply-chain-owner-signoff.md` | `shared` | P0 | 无 |
| `DECK-SC-002` | `task_275b_backend_trust-policy-bundle.md` | `backend` | P0 | `task_275a` |
| `DECK-SC-003` | `task_275c_backend_publish-digest-signature-verification.md` | `backend` | P0 | `task_275b` |
| `DECK-SC-004` | `task_275d_backend_runtime-digest-load-receipt.md` | `backend` | P0 | `task_275c`, `task_deck_002`, `task_deck_008` |
| `DECK-SC-005` | `task_275e_backend_artifact-retention-lifecycle.md` | `backend` | P0 | `task_275c`, `task_deck_003` |
| `DECK-SC-006` | `task_275f_backend_cold-recovery-operations.md` | `backend` | P1 | `task_275e`, marketplace/制品平台 owner 方案与签署 |
| `DECK-SC-007` | `task_275g_backend_tamper-evidence-pack.md` | `backend` | P1 | `task_275c`, `task_275d` |
| `DECK-SC-008` | `task_275h_backend_recovery-purge-evidence-pack.md` | `backend` | P1 | `task_275e`, `task_275f` |
| `DECK-SC-009` | `task_275i_shared_legacy-unverified-alignment.md` | `shared` | P1 | `task_275c` |

每个来源条目只映射到一份 task 文档；每份 task 文档只承接一个来源条目。StagePlanner 后续必须能以 Task ID 直接构建 DAG，禁止再次合并或产生孤儿条目。

Canonical 集仅为本节列出的 `task_275a..275i` 与本填充 prompt。`TASK-REQUIREMENT-task_275_shared_deck-supply-chain-gate-contracts.md` 及 `task_deck_sc_001..009_*` 属于 superseded / non-canonical 并发产物，只为审计保留；StagePlanner 与 ExecTaskAgent 必须忽略，不得删除、重命名、覆盖或据此建立第二套映射。

### 4. 全局不可放宽合同

1. 生产制品同时满足摘要、签名和可恢复留存，缺一即不得进入 `production_ready`。
2. `artifact_digest = sha256:<64-lowercase-hex>` 对实际分发字节计算；不得信任 marketplace 标签、分支、`latest` 或 cache 元数据。
3. `deck_plugin_manifest_hash` 对 RFC 8785 规范化 JSON 字节计算 SHA-256；必须使用经验证的标准库，不得手写近似 canonicalizer。
4. DSSE 兼容签名包必须绑定 `artifact_digest + deck_plugin_manifest_hash + publisher_identity`；首选 `sigstore-bundle/v1`，trust-policy revision、信任根、identity、算法、时间证明、轮换、撤销、过期和离线缓存生命周期均可审计。
5. 未知算法、未知 identity/根、撤销状态未知、缺时间证明、离线缓存过期、verifier 失联或策略降级全部 fail closed，不得 warn-only。
6. 发布端先验证实际字节、manifest、签名包与 identity；runtime 物化后重新计算实际字节摘要并绑定 load receipt，禁止重新信任 marketplace 标签或 cache 元数据。
7. published/deprecated/revoked release、runtime lock、Workflow Run 或 legal hold 任一权威引用存在即禁止 purge；全部引用归零且无 legal hold 后进入不少于 90 天的可恢复隔离期，期满后 purge 前再次原子检查引用。
8. revoked 制品隔离且禁止新执行，但保留用于历史复现与取证的字节/签名/来源/审计。
9. `legacy_unverified` 仅允许显式开发、测试或历史只读；任何 production-ready/preflight/run 请求均拒绝并返回 `ARTIFACT_VERIFICATION_REQUIRED`。
10. 真实篡改测试、冷恢复演练、引用清理测试、可点击报告、run/commit 标识、日志摘要、owner/独立 reviewer 签署和后续独立复审缺一时，Stage 4 production Gate 继续阻断。

### 5. 每份 task 文档的强制结构

每份最终文档至少包含以下章节，字段不可省略：

1. 任务标题；
2. 关联 Issue（来源条目、[SUO-275](/SUO/issues/SUO-275)、[SUO-258](/SUO/issues/SUO-258)、design/issue 路径、domain、优先级、标签）；
3. 任务目标与明确排除范围；
4. 实现步骤，具体到模型/服务/API/状态、原子边界、失败路径、审计和回滚；
5. 涉及文件路径，以允许修改闭集表列出准确文件/模式、动作和最小变更；
6. 输入 / 输出说明，包含结构化合同与证据字段；
7. 依赖项、可并行性、Stage 准入条件与冻结点；
8. 测试策略，列出最小命令/方法、场景、通过标准与证据；
9. 完成标志，逐条映射来源 Issue 验收条件；
10. 风险提示、回滚要求与 clarification owner/action；
11. 允许/禁止修改范围；
12. StagePlanner / execute readiness 字段（前序、并行、freeze point、真实证据、未满足 Gate）。

所有文件必须声明：task 完成只表示该单项实现/证据合同满足，不自动代表 `DECK-GATE-DEC-017`、Stage 4 或 production Gate 获批。

### 6. shared / 非代码交付边界

#### `task_275a` 治理边界

- Frontend：N/A，不产生 UI 实现。
- Backend：N/A，不产生服务实现。
- 治理交付：具名 security、marketplace/制品平台、runtime owner；每个 owner 的主体 ID、任命类型（临时/正式）、有效期、允许/禁止 scope、否决权、签署时间、签署对象 hash 与审批记录链接。
- 验收：三类 owner 均签署对应最小权限范围；临时覆盖必须写明到期和替代 owner 行动；缺任一项保持生产 Gate 阻断。

#### `task_275i` shared 边界

- Frontend：管理 UI 的 `legacy_unverified` 警告、生产选择禁用、恢复/迁移指引；不自行判定权威 verification。
- Backend：权威状态、production-ready/preflight/run 拒绝、`ARTIFACT_VERIFICATION_REQUIRED`、审计；不实现 UI 文案。
- 联调：API 状态/reason code 与 UI 标签/禁用动作一致；开发/测试/历史只读路径显式且不可扩张。
- 验收：扫描台账分类为 `legacy_unverified|updated|deprecated`，当前开放文档与代码为强制范围；历史关闭产物只记录引用，不反写上游。

其他 backend task 的前端范围均为 N/A；若需要管理 UI 展示，只输出只读消费合同并依赖 `task_211_frontend_plugin_admin_ui.md`，不得在 backend task 中吞并前端实现。

### 7. 文件闭集设计原则

- 优先复用当前仓库的 `backend/models/deck_plugin.py`、`backend/services/deck_plugin/`、`backend/database.py`、`backend/tests/` 与 `.github/workflows/ci-backend.yml`；新增模块必须在 task 中逐文件授权。
- runtime 二次摘要与 load receipt 使用 `backend/models/runtime_plugin.py`、`backend/services/runtime_plugin/`、`backend/tests/test_runtime_plugin_*` 闭集，并与既有 `task_deck_008` 合同做增量对齐。
- shared legacy UI 只授权 `frontend/src/components/deck-plugin/`、`frontend/src/api/deckPluginApi.ts`、对应测试和后端权威检查路径；若真实代码尚未建立这些路径，Stage 必须先验证 owner/路径，不得扩大到整个 `frontend/` 或 `backend/`。
- 证据产物使用受控的 `artifacts/deck-plugin-stage4/` 或 CI artifact 外部 URL；不得把占位链接写成可点击证据已经存在。
- 禁止修改 `docs/design/`、`docs/issue/`、`docs/stage/`、`docs/exec/`、无关 task、依赖锁文件、部署配置和实现闭集之外的源码。

### 8. 测试与证据要求

- backend 最小基线：从仓库根执行 `python -m unittest` 指向本 task 新增的精确测试模块；不得默认运行全仓库测试替代范围验证。
- 文档校验：`git diff --check -- docs/task`；确认九个 Task ID、九个来源条目与九个文件名均唯一命中。
- 篡改 evidence pack 至少覆盖：制品字节、manifest、签名包、publisher identity、未知/降级算法、旧签名重放、lock digest、runtime cache/物化字节；每项均须拒绝并产生结构化错误与审计事件。
- 冷恢复 evidence pack 必须清除热副本和节点 cache，从冷存储恢复相同 `sha256`，重新验证签名包、manifest hash 与 runtime 二次摘要。
- purge evidence pack 必须证明任一 release/lock/run/legal hold 引用存在时拒绝；仅在引用归零、hold 解除、90 天隔离届满并完成二次检查后允许 purge，且审计仍可查询。
- 报告条目至少包含 `evidence_pack_id`、`test_case_id`、`test_run_id`、`commit_sha`、输入/预期/实际结果、结构化错误、审计 ID、日志摘要 URL、artifact/report URL、`manifest_sha256`、owner/reviewer ID、签署时间与范围。
- 失败证据也是有效交付，但 task/Stage 必须保持相应 Gate 未通过，不得把失败或占位证据表述为 approve。

### 9. Clarification 与阻断传播

- `task_275a`：Owner 为 `CEOOrchestrator`；动作是任命三类 owner 或记录有期限、有限 scope 的临时覆盖并取得对应签署。
- `task_275f`：Owner 为 marketplace/制品平台 owner，由 `CEOOrchestrator` 路由；动作是选择冷存储方案并签署 RTO/RPO、备份频率、演练周期、可用性指标与第三方违约/升级责任。默认允许 owner 自选实现，只要满足冻结合同。
- `task_275i`：Owner 为 `CEOOrchestrator`；当前默认扫描开放文档与代码，关闭历史产物只登记引用。若要求全历史改写，必须新建增量 Issue，不得在本 task 擅自扩大。
- 任何未具名 owner、未定 RTO/RPO、缺失真实环境或 reviewer 均不阻塞 task 文档生成，但必须成为后续 Stage/execute readiness 的显式 blocker/freeze point。

### 10. 输出与完成报告

生成上表九份最终 task 文档，并做以下最小验证：

1. 每个 `DECK-SC-001..009` 在对应 task 的关联 Issue 中唯一出现；
2. 文件名符合 `task_<序号>_<domain>_<slug>.md`，domain 仅为 `backend` 或 `shared`；
3. 每份文档包含所有强制章节、允许/禁止闭集、验证命令、证据格式、回滚和 clarification owner/action；
4. 依赖图无反向阶段依赖，`task_275f`、`task_275g`、`task_275i` 可在各自前置满足后并行，`task_275h` 等待 `task_275e + task_275f`；
5. 所有文档都保留 production Gate 阻断语义；
6. `git diff --check -- docs/task` 通过，且没有修改 `docs/design/`、`docs/issue/` 或 `docs/stage/`。

立即生成任务文档，不要只输出计划或分析。若输入矛盾只影响某一 task，完成其余 task，并在受影响文档中点名 blocker owner/action；只有上游合同不可判定时才停止对应文档。

## Optional Enhancers

- StagePlanner 可在消费时把 P0 核心链 `275a → 275b → 275c → {275d,275e}` 设为冻结主线，并在 `275d/275e` 满足后并行推进 `275f/275g/275i`。
- ExecTaskAgent 可在 Stage 完成后按单个 task 复制 `docs/task/TASK-REQUIREMENT-FORMAT.md`；该动作不属于 [SUO-275](/SUO/issues/SUO-275) 的输出。
