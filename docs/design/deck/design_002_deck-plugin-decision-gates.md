# Deck Plugin 后续 Stage 五项决策 Gate 增量设计附录

> **Design ID**: `DECK-DESIGN-002`
>
> **对应 Issue**: [SUO-249](/SUO/issues/SUO-249)
>
> **上游主设计**: `docs/design/deck-plugin-voice-ink-dream-integration.md`
>
> **当前 canonical 路径**: `docs/design/deck/design_002_deck-plugin-decision-gates.md`
>
> **修订日期**: 2026-08-01
>
> **修订状态**: `conditional_frozen`
>
> **适用流水线**: `design → issue → task → stage`

## 1. 背景与目标

主设计 §22、Issue 决策单 `DECK-016`～`DECK-020` 与 Stage 计划 §6 将五项架构/UX 问题保留为默认假设。默认假设可以支持早期拆解，但不能作为 API、生产部署、安全策略或 UI 文案的冻结依据。

本附录给出五项可引用的**条件性冻结结论**，使下游能明确判断对应 Gate 是通过、限域通过还是阻断，并避免继续把默认假设写成已批准方案。

### 1.1 真相源与优先级

1. 本附录不重写稳定主设计；主设计除 §22 五项未决说明外继续有效。
2. 对 `DECK-016`～`DECK-020`，本附录的结论、合同和 Gate 条件优先于主设计 §22、Issue 清单和既有 Task/Stage 中的默认假设。
3. 下游若尚未获得本附录列出的审批，只能按 `conditional_frozen` 的限域条件推进，不得把状态写为 `approved` 或 `fully_frozen`。
4. 审批方提出实质变更时，增量修订本文件并保留原决策记录；不得另建平行主文档。

## 2. 范围界定

### 2.1 范围内

- Deck Plugin catalog 与 ClaudeAgent Runtime Admin 的物理承载和写所有权；
- 生产 marketplace 制品签名、摘要校验、引用留存与恢复合同；
- 单节点、多节点及临时 runtime 的制品分发、readiness 和运行节点绑定；
- 普通禁用、安全撤销、紧急撤销对新运行和非终态运行的行为；
- Voice 持久 chat 发起 Workflow Run 后，来源关系、独立 run-scoped session 与用户可见界面；
- 对应 Stage Gate、受影响 Task、兼容与回滚要求、待审批角色。

### 2.2 范围外

- 不拆分或改写 `docs/issue/`、`docs/task/`、`docs/stage/`；
- 不指定具体仓库目录、数据库供应商、消息队列或云厂商；
- 不实现 marketplace、runtime、撤销服务或前端组件；
- 不改变 Deck 是唯一业务模块、story-workspace 是运行/结果 owner、ClaudeAgent 是执行/session owner 的既有边界；
- 不把 Paperclip Plugin worker 模型引入 Deck Plugin 或 Claude Code Plugin 运行链路；
- 不替代安全、运行平台、产品 owner 对生产启用的正式审批。

## 3. 方案摘要与冻结状态

`conditional_frozen` 表示：设计方案和最小合同已经确定，下游可以按限域条件实现；但在列出的 owner 审批前，不得跨过对应生产或发布 Gate。它不是“沿用默认假设”，也不是“已获最终批准”。

| 决策单 | 决策 ID | 条件性结论 | Gate 结论 | 仍需审批 |
|---|---|---|---|---|
| `DECK-016` | `DECK-GATE-DEC-016` | 不新增第三个业务服务；Deck control plane 与 ClaudeAgent runtime control 分别持有状态，由无状态 gateway 聚合 | Stage 2 API/schema Gate 在 owner 确认前为**阻断**；逻辑接口实现可限域推进 | `CEOOrchestrator`、Deck/Voice Decks owner、ClaudeAgent runtime owner |
| `DECK-017` | `DECK-GATE-DEC-017` | 生产制品必须以 SHA-256 精确摘要、受信签名包和引用感知留存共同构成完整性合同 | 非生产可限域推进；Stage 4 生产 Gate 在验证/恢复能力落地前为**阻断** | 安全 owner、marketplace/制品平台 owner、runtime owner |
| `DECK-018` | `DECK-GATE-DEC-018` | 采用共享 CAS 源 + 节点按摘要拉取 + 本地派生缓存；run-ready 只在选定节点加载回执后成立 | 单节点为**限域通过**；多节点/临时 runtime 在 CAS、调度绑定和节点回执落地前为**阻断** | ClaudeAgent runtime owner、运行平台/SRE owner |
| `DECK-019` | `DECK-GATE-DEC-019` | `DISABLE` 不终止既有 run；`REVOKE` 终止所有受影响非终态 run；`EMERGENCY` 立即硬终止 | Stage 4 安全 Gate 在等级、时限、权限和演练获批前为**阻断** | 安全 owner、Workflow Run owner、runtime owner |
| `DECK-020` | `DECK-GATE-DEC-020` | Voice chat 保留原线程；创建独立 Workflow Run/Agent session，以双向来源卡片和运行详情显式连接，禁止伪装成同一 chat | Stage 3 UI/文案 Gate 在产品确认前为**阻断**；数据合同和组件骨架可推进 | 产品 owner、Voice/Chat owner、story-workspace owner |

## 4. 详细设计

### 4.1 `DECK-GATE-DEC-016`：物理服务边界

#### 4.1.1 采用方案

物理承载冻结为两个既有责任单元，不新增独立的“Deck Runtime”业务服务：

| 责任单元 | 权威写入 | 可以读取 | 禁止写入 |
|---|---|---|---|
| **Deck control plane** | Deck Plugin draft/release/catalog、installation、binding/revision、runtime lock、Deck runtime snapshot、来源策略引用 | runtime readiness 和 load receipt 摘要 | runtime 节点 cache、settings 物化事实、Agent session |
| **ClaudeAgent runtime control** | runtime environment/pool/node、settings 意图、marketplace allowlist 执行结果、materialization operation、节点 cache 状态、Agent session、load receipt | runtime lock、Deck runtime snapshot、有效能力 | Deck release、installation、binding、story 结果 |
| **story-workspace**（既有边界） | Workflow Preflight、Workflow Run、输入 hash、结果、审阅与重试链 | binding/release/lock/snapshot、runtime receipt | Deck 定义、运行时制品和 session 内部状态 |
| **API gateway/BFF** | 无权威业务状态 | 聚合上述公开/内部合同 | 不得双写、复制 owner 表或自行推进状态机 |

物理部署可以先同进程/同集群部署，但模块必须保持独立写所有权。未来拆为独立服务时，只替换 gateway 和内部 transport，不改变公开资源语义。

跨边界调用只传不可变 ID、版本、摘要和脱敏状态。最小内部合同为：

```text
Deck control plane
  ├─ ResolveRuntimeLock(runtime_plugin_lock_id)
  ├─ GetDeckRuntimeSnapshot(deck_runtime_snapshot_id)
  └─ GetEffectiveRuntimePolicy(policy_ref)

ClaudeAgent runtime control
  ├─ CheckPoolEligibility(runtime_pool_id, artifact_set_hash)
  ├─ EnsureMaterialized(runtime_node_id, runtime_plugin_lock_id)
  ├─ CreateRunSession(workflow_run_id, snapshot_id, lock_id)
  └─ GetRuntimeLoadReceipt(runtime_load_receipt_id)
```

强制规则：

1. gateway 只聚合和路由，不拥有 release、installation、materialization 或 session 状态。
2. 每个状态只有一个 writer；跨服务更新以命令回执或事件表达，禁止共享表双写。
3. 浏览器继续消费逻辑 API；Runtime Admin 内部 API 不直接暴露任意 settings、路径、CLI 或 marketplace 输入。
4. 服务拆分不得改变 `deck_plugin_*`、`runtime_plugin_*`、`deck_runtime_*` 和 `workflow_run_*` 的领域前缀。

#### 4.1.2 替代方案

| 替代方案 | 结论 | 原因 |
|---|---|---|
| catalog 与 Runtime Admin 全部归入 ClaudeAgent runtime | 拒绝 | 会让运行平台拥有 Deck 业务发布、binding 和 installation 语义 |
| catalog 与 runtime 物化全部归入 Deck | 拒绝 | Deck 无法成为 runtime 节点、cache、session 和 load receipt 的可信 owner |
| 新建第三个 Deck Runtime 业务服务 | 本期拒绝 | 增加双 owner/循环依赖，违背 Deck 唯一业务模块决策 |
| gateway 持有聚合状态并双写两侧 | 禁止 | 无法确定审计真相源，失败时产生不可恢复分叉 |

#### 4.1.3 影响合同

- 逻辑公开 API 路径保持兼容；物理路由由 gateway 映射。
- 所有 runtime 结果必须携带 `runtime_environment_id`，多节点启用后追加 `runtime_pool_id`、`runtime_node_id`。
- Deck 侧仅保存 `runtime_materialization_id`、`runtime_load_receipt_id` 等引用和脱敏摘要。
- 事件生产者按 owner 划分：release/installation/binding 事件来自 Deck；materialization/session/load 事件来自 ClaudeAgent runtime；run/result 事件来自 story-workspace。

#### 4.1.4 兼容与回滚

- 当前同进程实现可以通过模块 facade 适配，无需立即网络拆分。
- 若未来物理拆分失败，回滚到同进程部署，但不能回滚单写者和领域边界。
- 禁止以数据库共享访问作为回滚路径；只能回滚 transport/deployment adapter。

#### 4.1.5 Gate、Task 与审批

- **Gate**：Stage 2 Gate；Deck/Runtime owner 未确认前，不得冻结跨服务 API schema 或物理路由。
- **直接影响 Task**：`task_deck_001_backend_manifest-model.md`、`task_deck_003_backend_installation-lifecycle.md`、`task_deck_004_backend_compatibility-capability.md`、`task_210_shared_deck_plugin_binding.md`、`task_deck_006_backend_workflow-preflight.md`、`task_deck_008_backend_reconcile-load-receipt.md`、`task_deck_009_backend_run-scoped-session.md`、`task_deck_014_backend_api-error-codes.md`。
- **审批动作**：`CEOOrchestrator` 召集 Deck/Voice Decks owner 与 ClaudeAgent runtime owner，确认部署单元、内部 transport 和单写者表；三方确认后可把本项改为 `frozen`。

### 4.2 `DECK-GATE-DEC-017`：marketplace 签名、digest 与留存

#### 4.2.1 采用方案

生产制品必须同时满足摘要、签名和可恢复留存，缺一即不得进入 `production_ready`：

1. marketplace 提供不可变的打包制品；`artifact_digest = sha256:<hex>` 对**实际分发字节**计算，不对可变目录、分支或 `latest` 引用计算。
2. `deck_plugin_manifest_hash` 对 RFC 8785 规范化 JSON 计算 SHA-256。
3. 发布者使用 DSSE 兼容签名包绑定 `artifact_digest + deck_plugin_manifest_hash + publisher_identity`；首选实现为可离线验证的 `sigstore-bundle/v1`，信任身份/密钥必须在管理员 allowlist 中。
4. 发布时验证签名、身份、摘要和来源策略；运行时物化后再次验证摘要。运行阶段只消费已冻结的验证结果和摘要，不重新信任 marketplace 标签。
5. 留存以引用为准：只要 published/deprecated/revoked release、runtime lock 或 Workflow Run 仍引用制品，制品必须保留或可从冷存储恢复为相同摘要。
6. 全部权威引用归零且无 legal hold 后，进入 90 天可恢复隔离期；期满才允许 purge。digest、签名证明、来源、引用清理审计至少与最长运行审计记录同寿命。
7. revoked 制品进入隔离存储并禁止新执行；撤销不是删除，不能破坏历史取证。

最小合同：

```jsonc
{
  "artifact_digest": "sha256:...",
  "artifact_size_bytes": 123456,
  "deck_plugin_manifest_hash": "sha256:...",
  "signature_scheme": "sigstore-bundle/v1",
  "signature_bundle_ref": "artifact://signatures/...",
  "publisher_identity": "...",
  "verification_status": "verified",
  "verified_at": "...",
  "retention_state": "pinned|recoverable|purge_eligible|quarantined",
  "restore_source_ref": "artifact://cas/sha256/..."
}
```

`production_ready` 的服务端判定至少要求：`verification_status=verified`、digest 算法受支持、签名身份受信、恢复源可读、所有 required 依赖满足相同条件。

#### 4.2.2 替代方案

| 替代方案 | 结论 | 原因 |
|---|---|---|
| 只有版本号或 marketplace 名称 | 禁止 | 可变标签不能证明实际执行字节 |
| 只有 SHA-256、无签名 | 仅开发环境允许 | 可检测传输损坏，不能证明发布者身份 |
| 签名只覆盖 manifest、不覆盖 artifact digest | 禁止 | manifest 与实际制品仍可被替换 |
| 卸载或 revoked 后立即删除制品 | 禁止 | 破坏历史复现、回滚和安全取证 |
| 所有制品永久热存储 | 不采用 | 成本不可控；引用固定 + 冷恢复足以维持合同 |

#### 4.2.3 影响合同

- `DeckRuntimePluginLock` 增加签名验证与恢复引用字段；现有 `artifact_digest` 保持兼容。
- 发布、安装、物化和 preflight 分别返回结构化失败：`ARTIFACT_SIGNATURE_INVALID`、`ARTIFACT_DIGEST_MISMATCH`、`ARTIFACT_RESTORE_UNAVAILABLE`。
- 管理 UI 展示“已验证 / 未验证 / 已隔离 / 可恢复”，不得仅以“已下载”表示可信。
- 事件与日志只记录 signer 摘要和证明引用，不内联完整签名包或制品。

#### 4.2.4 兼容与回滚

- 既有无签名制品迁移为 `legacy_unverified`，只允许开发/测试或历史只读，不得静默升级为 production-ready。
- 签名 verifier 可替换，但新的 verifier 必须产生相同的规范验证结果；不改变 lock 中的原摘要。
- 策略配置回滚只能把新发布暂停为 non-production-ready，不能跳过已冻结 release 的校验或删除历史证明。

#### 4.2.5 Gate、Task 与审批

- **Gate**：Stage 4 生产 Gate；在非生产环境可以显式 `legacy_unverified` 推进，但不得标 production-ready。
- **直接影响 Task**：`task_deck_001_backend_manifest-model.md`、`task_deck_002_backend_runtime-lock.md`、`task_deck_003_backend_installation-lifecycle.md`、`task_deck_008_backend_reconcile-load-receipt.md`、`task_deck_013_backend_events-audit.md`、`task_deck_014_backend_api-error-codes.md`、`task_211_frontend_plugin_admin_ui.md`。
- **审批动作**：安全 owner 批准信任根、签名算法与失败策略；marketplace/制品平台 owner 承诺签名包和冷恢复能力；runtime owner 批准双重摘要校验路径。

### 4.3 `DECK-GATE-DEC-018`：多节点或临时 runtime 分发

#### 4.3.1 采用方案

采用“共享内容寻址源（CAS）+ 调度后节点按摘要拉取 + 节点本地派生缓存”，不采用向所有节点预推制品：

```text
Marketplace / 发布服务
        │ 签名验证、按 digest 写入
        ▼
Shared CAS（权威分发源）
        │ scheduler 选定 runtime_pool_id / runtime_node_id
        ▼
Node-local cache（可淘汰、非权威）
        │ reconcile + digest verify + load smoke
        ▼
RuntimeLoadReceipt → run queued → running
```

readiness 必须分层：

| 层级 | 事实 | 可否表示 run-ready |
|---|---|---|
| `artifact_available` | required digest 在共享 CAS 中可读取且签名已验证 | 否，只表示可分发 |
| `pool_eligible` | 运行池满足平台/能力/网络策略，且所有 digest 可拉取 | 否，只表示可调度 |
| `node_materialized` | 选定节点已下载并校验全部 required digest | 否，尚未证明当前 session 加载 |
| `session_loaded` | 选定节点为本次 run 生成逐项一致的 load receipt | **是**，允许 `queued → running` |

强制规则：

1. preflight token 绑定 `runtime_pool_id + artifact_set_hash + policy_revision`；节点可在 token 有效期内由 scheduler 选择。
2. Workflow Run 创建后记录 `runtime_pool_id`；节点选定后追加不可变 `runtime_node_id` 和 `runtime_load_receipt_id`。
3. 任一节点 materialized 不能让整个 pool 显示 global ready；管理 UI 使用“可按需准备 / 部分节点已缓存 / 当前运行已加载”等精确状态。
4. 临时节点启动后必须从 CAS 拉取并校验，不能依赖镜像外的持久本地 settings/cache。
5. 节点 cache 可按 LRU/容量策略淘汰；权威留存只在 CAS/冷存储，cache 不能计入 `DECK-GATE-DEC-017` 的留存证明。
6. 节点在加载前失联时可重新调度；一旦 `agent_session_id` 创建，不得把同一 session 迁移到另一节点。恢复必须创建新 session attempt，并保留原回执/失败记录。

#### 4.3.2 替代方案

| 替代方案 | 结论 | 原因 |
|---|---|---|
| 发布时向全部节点主动 fan-out | 不采用 | 临时节点集合不稳定，失败重试和一致性成本高 |
| 共享可写插件目录由多节点直接加载 | 禁止 | 部分写入和并发更新会破坏摘要与原子性 |
| 任何节点 ready 即标记 pool ready | 禁止 | scheduler 可能选择未物化节点 |
| 把插件永久烘焙进 runtime 镜像 | 仅基础内置能力允许 | 无法支持发布锁和按版本回滚 |

#### 4.3.3 影响合同

- 新增 `runtime_pool_id`、`runtime_node_id`、`artifact_set_hash`、`distribution_attempt_id`。
- `RuntimeReadiness` 响应必须返回 `scope=artifact|pool|node|session`，禁止无 scope 的 `ready=true`。
- `RuntimeLoadReceipt` 增加 node、session、artifact set 和 policy revision；每个 required 条目仍记录精确 digest。
- 错误码至少区分 `ARTIFACT_DISTRIBUTION_FAILED`、`RUNTIME_NODE_UNAVAILABLE`、`RUNTIME_POOL_NOT_ELIGIBLE`、`RUNTIME_PLUGIN_LOAD_FAILED`。

#### 4.3.4 兼容与回滚

- 单节点 persistent runtime 作为 `runtime_pool_id == runtime_environment_id` 的一节点特例，沿用同一合同。
- 分发功能可以通过 `distribution_mode=local_persistent` 回滚，但 readiness scope 和 receipt 语义不可回滚。
- 多节点 rollout 失败时只关闭多节点调度，回到单节点池；不得伪造全局 ready 或跳过 digest 校验。

#### 4.3.5 Gate、Task 与审批

- **Gate**：Stage 2 对单节点限域通过；任何多节点/临时 runtime 环境在 CAS、调度绑定和 node/session receipt 验证前不得进入 Stage 2 Gate。
- **直接影响 Task**：`task_deck_006_backend_workflow-preflight.md`、`task_deck_008_backend_reconcile-load-receipt.md`、`task_deck_009_backend_run-scoped-session.md`、`task_deck_013_backend_events-audit.md`、`task_deck_014_backend_api-error-codes.md`、`task_211_frontend_plugin_admin_ui.md`、`task_213_frontend_story_workspace_status.md`。
- **审批动作**：ClaudeAgent runtime owner 确认 pool/node/session 数据模型；运行平台/SRE owner 确认 CAS 可用性、调度失败恢复、容量和缓存淘汰策略。

### 4.4 `DECK-GATE-DEC-019`：安全撤销策略

#### 4.4.1 采用方案

冻结三个等级及其服务端行为：

| 等级 | 新 binding/preflight/run | 撤销前已存在的非终态 run | session 动作 | 恢复 |
|---|---|---|---|---|
| `DISABLE` | 阻止 | 继续使用已锁来源直到终态 | 不终止 | 管理员可重新 enable；不改历史 |
| `REVOKE` | 立即阻止 | 全部进入 `cancelling`，在策略规定的有限 grace period 内到安全停止点，超时硬终止 | 撤销工具/网络授权并终止 | 不恢复原 run；修复后以新 release/new run 执行 |
| `EMERGENCY` | 立即阻止 | 立即进入 `cancelled` 或 `failed` 的安全终态 | 立即硬终止，不等待业务 checkpoint | 不原地解除；只能由 superseding release 和新 run 恢复 |

撤销目标可以是 `deck_plugin_release`、`runtime_plugin_digest`、签名身份或能力策略。服务必须解析所有受影响的 installation、binding 和非终态 run，且同一 `revocation_id` 幂等。

`REVOKE`/`EMERGENCY` 强制要求：

1. 写入 append-only `SecurityRevocationRecord`，包含 actor、level、reason code、scope、effective time、policy revision 和可公开安全摘要。
2. 先使新 preflight 失败，再广播受影响 run 的取消命令；取消命令至少一次投递，消费者按 `revocation_id + workflow_run_id` 去重。
3. 运行状态记录 `SECURITY_REVOCATION`，事件使用 `workflow.run.security_cancelled`；不得归类为用户取消或普通执行失败。
4. 尽可能在终止前持久化非敏感进度；不得提交不完整业务结果为成功，也不得为了保存结果延迟 `EMERGENCY`。
5. 通知运行 owner、发起用户和安全值班；紧急撤销允许先终止后通知。
6. revoked 制品隔离但保留取证和历史引用，不允许自动降级到未明确授权的版本或能力集合。

#### 4.4.2 替代方案

| 替代方案 | 结论 | 原因 |
|---|---|---|
| 所有禁用/撤销都让活动 run 继续 | 拒绝 | 已知恶意/泄漏能力会继续执行 |
| 所有普通禁用都立即杀 run | 拒绝 | 将日常运维误作安全事故，造成不必要数据损失 |
| 撤销后自动回退最近可用版本 | 禁止 | 可能绕过批准能力、schema 和摘要锁 |
| 原地删除/修改历史 runtime lock | 禁止 | 破坏审计和复现 |

#### 4.4.3 影响合同

- `SecurityRevocationRecord` 至少包含 `revocation_id`、`level`、`scope_type/id`、`actor_id`、`reason_code`、`effective_at`、`grace_deadline_at`、`policy_revision`。
- Workflow Run 增加 `cancel_reason=security_revocation`、`revocation_id`、`termination_mode=graceful|hard`。
- preflight/运行错误码统一使用 `SECURITY_REVOCATION`，响应只给安全摘要和恢复去向。
- 管理 UI 显示撤销等级、影响范围、运行处理进度和审计入口；普通用户不能触发 `REVOKE`/`EMERGENCY`。

#### 4.4.4 兼容与回滚

- 旧的 `disabled` 映射为 `DISABLE`，不会意外终止既有 run。
- revocation record 不可删除或原地改为“未撤销”；误报通过新的 superseding policy/release 记录修复。
- 代码 rollout 可关闭自动硬终止并回到人工处置，但此回滚只允许在非生产演练；生产启用后必须由安全 owner 走紧急变更流程。

#### 4.4.5 Gate、Task 与审批

- **Gate**：Stage 4 安全 Gate；等级权限、grace deadline、事件投递、硬终止和恢复演练未通过前不得 production-ready。
- **直接影响 Task**：`task_deck_001_backend_manifest-model.md`、`task_deck_003_backend_installation-lifecycle.md`、`task_deck_004_backend_compatibility-capability.md`、`task_deck_007_backend_workflow-run.md`、`task_deck_009_backend_run-scoped-session.md`、`task_deck_013_backend_events-audit.md`、`task_deck_015_backend_revocation-rollback.md`、`task_211_frontend_plugin_admin_ui.md`、`task_213_frontend_story_workspace_status.md`。
- **审批动作**：安全 owner 批准撤销角色、scope、grace/hard-stop policy 和通知要求；Workflow Run/runtime owner 共同确认取消幂等、终态映射和演练证据。

### 4.5 `DECK-GATE-DEC-020`：Voice chat 到 run-scoped session 的可见 UX

#### 4.5.1 采用方案

Voice chat 与 Workflow Run 保持两种不同的用户对象：Voice chat 是持久对话和来源，Workflow Run 是锁定 workflow/runtime 的可审计执行。两者通过可见双向链接关联，不创建一个可被误解为“同一对话继续”的第二聊天线程。

标准交互：

1. 用户在 Voice chat 中通过显式动作「创建工作流运行」发起，不因普通聊天消息自动启动 run。
2. 服务端执行 preflight，创建独立 `workflow_run_id`；随后创建 run-scoped `agent_session_id`。`source_voice_thread_id` 只作来源引用，绝不赋给 `agent_session_id`。
3. 原 Voice chat 保持当前位置，并插入/更新 `WorkflowRunLinkCard`，不自动跳走。
4. 卡片主标题固定为「已创建独立工作流运行」；辅助说明为「本次运行使用锁定的 Deck 工作流与 ClaudeAgent 运行时；当前 Voice 对话仅作为来源。」
5. 卡片展示 Deck 工作流名称/版本、运行状态、创建时间和主操作「查看运行」。点击后进入 `/story-workspace/runs/{workflow_run_id}`。
6. 运行详情顶部展示 `来源：Voice {voice_display_name} · {source_message_time}` 和「返回来源对话」。用户无来源线程权限时只展示脱敏来源摘要，不提供链接。
7. run-scoped session 不进入普通 Chat 历史列表，不提供继续对话输入框；用户看到的是步骤、状态、结果、错误、审阅和来源时间线。
8. 重试创建新的 run/session，并在原卡片中形成重试链；不得把失败 run 的 session 复活为聊天线程。

来源合同：

```jsonc
{
  "source_context": {
    "source_type": "voice_chat",
    "source_voice_id": "...",
    "source_voice_thread_id": "...",
    "source_message_id": "...",
    "source_message_time": "...",
    "started_by_user_id": "..."
  },
  "workflow_run_id": "...",
  "agent_session_id": "server-only",
  "run_detail_url": "/story-workspace/runs/...",
  "source_url": "/chat/..."
}
```

权限规则：创建 run、查看 run、查看来源 chat 分别校验；拥有 run 权限不自动获得 Voice thread 权限。事件和来源卡片不得回显原消息正文、Voice system prompt、secret 或 session settings。

#### 4.5.2 替代方案

| 替代方案 | 结论 | 原因 |
|---|---|---|
| 直接复用 Voice `thread_id` 作为 `agent_session_id` | 禁止 | 无法证明插件/settings 与 runtime lock 一致 |
| 自动跳转到新页面且不在原 chat 留痕 | 拒绝 | 用户难以返回来源，也会误以为原消息丢失 |
| 把 run session 展示为普通 Chat 历史线程 | 拒绝 | 混淆工作流执行、审计状态和自由对话 |
| 只存 `source_voice_thread_id`、不存消息级来源 | 不采用 | 无法解释由哪条用户意图触发运行 |
| 后台静默启动 run | 禁止 | 用户无法预期成本、权限和不可变来源 |

#### 4.5.3 影响合同

- Workflow Run 增加可选不可变 `source_context`；非 Voice 发起的 run 保持 `null`。
- start API 返回 `workflow_run_id`、`run_detail_url` 和可公开来源摘要；`agent_session_id` 不作为前端导航 ID。
- `workflow.run.status_changed` 驱动 chat 卡片和 story-workspace 运行详情，消费者按 `event_id` 去重。
- `task_213` 的上下文条/来源追溯必须区分“来源 Voice 对话”和“独立运行”；`task_212` 中“仅影响下一次运行”文案不再引用本决策作为未冻结占位。

#### 4.5.4 兼容与回滚

- 既有 Voice chat、`Chat →` 和 Memory 初始化行为不变；只有显式运行动作走新路径。
- 历史无 `source_context` 的 run 隐藏来源区，不生成伪来源。
- UI 可通过 feature flag 隐藏运行入口和卡片，但已经写入的 `source_context`、run 与审计记录不得删除。
- 若新详情路由回滚，`run_detail_url` 可映射到既有 Story Workspace 状态面板；ID 和双向来源语义不变。

#### 4.5.5 Gate、Task 与审批

- **Gate**：Stage 3 UI/文案 Gate；数据模型、权限校验和组件骨架可先实现，未获产品确认不得把占位文案当发布文案。
- **直接影响 Task**：`task_deck_007_backend_workflow-run.md`、`task_deck_009_backend_run-scoped-session.md`、`task_212_frontend_deck_editor_plugin_binding.md`、`task_213_frontend_story_workspace_status.md`、`task_deck_013_backend_events-audit.md`。
- **审批动作**：产品 owner 确认显式启动、留在原 chat、卡片与运行详情文案；Voice/Chat owner 确认插卡和返回来源能力；story-workspace owner 确认运行详情与权限降级展示。

## 5. 验收标准

### 5.1 设计验收

- [x] 五项决策分别有唯一决策 ID、明确采用方案和 `conditional_frozen` 状态。
- [x] 每项均列出替代方案及采用/拒绝理由。
- [x] 每项均列出跨域合同变化、兼容策略和回滚边界。
- [x] 每项均标注 Stage Gate、直接受影响 Task 和仍需审批角色。
- [x] 默认假设与冻结结论已区分；未获得的审批未写成已完成。
- [x] 本附录不改写稳定主设计，也不修改 issue/task/stage/exec 或实现代码。

### 5.2 下游 Gate 验收

| Gate | 必须验证 | 通过标准 |
|---|---|---|
| Stage 2 / `DECK-016` | owner/单写者/API facade 评审 | 三个权威域无重复 writer，gateway 无业务状态，物理 owner 已确认 |
| Stage 2 / `DECK-018` | 单节点或多节点范围声明、readiness/receipt 测试 | 单节点明确限域；多节点时选定节点必须产生与 lock 一致的 load receipt |
| Stage 3 / `DECK-020` | Voice → run E2E、权限和文案评审 | 原 chat 留卡、run 页面有反向来源、session 不进入 Chat 历史、产品 owner 确认文案 |
| Stage 4 / `DECK-017` | 签名/digest 篡改测试、冷恢复演练、引用清理测试 | 篡改必拒绝；冷恢复得到同 digest；有引用时无法 purge |
| Stage 4 / `DECK-019` | 三等级矩阵、取消幂等、硬终止和审计演练 | 行为符合矩阵；安全取消不误报用户取消；历史 lock/证据不被改写 |

## 6. 风险与依赖

| 风险/依赖 | 影响 | 缓解或阻断条件 |
|---|---|---|
| 物理 owner 未确认 | API schema 和部署边界反复 | `DECK-016` 保持 Stage 2 阻断；只实现逻辑 facade |
| marketplace 暂不支持签名包或冷恢复 | 供应链和历史复现不成立 | 仅允许 non-production/legacy_unverified，不得降级 production Gate |
| CAS 或 scheduler 无多节点能力 | 临时节点无法证明 ready | 明确回到单节点池，不得宣称多节点 ready |
| 安全 owner 未给 grace/hard-stop policy | 强制终止可能过慢或误伤 | `REVOKE/EMERGENCY` production rollout 阻断 |
| Chat 与 story-workspace 权限模型不同 | 来源链接可能泄露对话存在性 | 每个方向独立鉴权，无权时只给脱敏摘要 |
| 既有 Task 使用默认假设或遗留字段 | 下游实现与本附录冲突 | 下游只读消费本附录并做增量修订；不得反向改写本设计 |

关键依赖：Deck/Voice Decks 服务 owner、ClaudeAgent runtime/运行平台、受信 marketplace 与 CAS、签名信任根、Workflow Run 取消机制、Voice Chat 插卡能力、story-workspace 运行详情和权限检查。

## 7. 关键决策记录

| 决策 ID | 日期 | 状态 | 结论 | 替代/影响摘要 |
|---|---|---|---|---|
| `DECK-GATE-DEC-016` | 2026-08-01 | `conditional_frozen` | Deck control plane 与 ClaudeAgent runtime control 分别单写；无状态 gateway 聚合；不新增第三业务服务 | 拒绝 gateway 双写和第三业务 owner；阻断 Stage 2 schema 冻结直至 owner 确认 |
| `DECK-GATE-DEC-017` | 2026-08-01 | `conditional_frozen` | SHA-256 精确字节摘要 + 受信 DSSE/Sigstore 签名包 + 引用感知留存/恢复 | 无签名仅限非生产；阻断 Stage 4 production Gate |
| `DECK-GATE-DEC-018` | 2026-08-01 | `conditional_frozen` | 共享 CAS、节点按摘要拉取、本地派生缓存、选定节点 load receipt 才是 run-ready | 单节点限域通过；多节点/临时部署需平台能力审批 |
| `DECK-GATE-DEC-019` | 2026-08-01 | `conditional_frozen` | DISABLE 不中止；REVOKE 有限优雅后硬停；EMERGENCY 立即硬停 | 禁止自动降级/改写历史；阻断 Stage 4 安全 Gate |
| `DECK-GATE-DEC-020` | 2026-08-01 | `conditional_frozen` | 原 Voice chat 留可更新卡片，独立 run/session 在 story-workspace 展示，并提供双向来源 | 禁止复用 thread 或把 run 当普通 chat；阻断 Stage 3 UI 文案 Gate |

## 8. 增量变更说明

- **新增 / SUO-249（2026-08-01）**：创建唯一决策 Gate 附录，替代主设计 §22 与下游文档中 `DECK-016`～`DECK-020` 的纯默认假设。
- 未修改 `docs/design/deck-plugin-voice-ink-dream-integration.md` 的稳定正文；本附录通过优先级声明提供增量覆盖。
- 未修改 `docs/issue/ISSUES_deck-plugin-voice-ink-dream-integration.md`、`docs/task/` 或 `docs/stage/stage_deck-plugin-voice-ink-dream-integration.md`；下游由各阶段 owner 只读消费并增量传播。

## 9. 阻塞或澄清说明

本附录本身无输入 blocker，五项均已形成可实施的条件性结论；但它们尚未获得所列 owner 的生产审批。因此：

- `[CLARIFICATION_NEEDED]` 不再表示“没有方案”，而表示“等待具名 owner 对本附录方案作 approve / request changes”。
- `CEOOrchestrator` 应把审批结论记录在对应 Issue 线程；批准后由 DesignArchitect 把相应状态从 `conditional_frozen` 增量修订为 `frozen`。
- 在状态转为 `frozen` 前，各 Stage 只能按本文 Gate 结论限域推进；不得以默认假设、占位实现或 feature flag 代替生产 Gate。
