# Deck Plugin 后续 Stage 五项决策 Gate 增量设计附录

> **Design ID**: `DECK-DESIGN-002`
>
> **对应 Issue**: [SUO-249](/SUO/issues/SUO-249)
>
> **本次修订 Issue**: [SUO-259](/SUO/issues/SUO-259)（依据 [SUO-256](/SUO/issues/SUO-256) `request_changes`）
>
> **本次状态回写 Issue**: [SUO-269](/SUO/issues/SUO-269)（消费 [SUO-267](/SUO/issues/SUO-267#comment-6ac1ba89-f6dd-4b69-ac2c-5dfd79fe440c) `approve`；批准输入 SHA-256 `085796ffc67a54d5f9ec2a45df9d454f742fc14503570ced2ccafee7aca51d23`）
>
> **上游主设计**: `docs/design/deck-plugin-voice-ink-dream-integration.md`
>
> **当前 canonical 路径**: `docs/design/deck/design_002_deck-plugin-decision-gates.md`
>
> **修订日期**: 2026-08-01
>
> **修订状态**: `partially_frozen`（`DECK-GATE-DEC-016`、`DECK-GATE-DEC-018`、`DECK-GATE-DEC-019`、`DECK-GATE-DEC-020` 已冻结；`DECK-GATE-DEC-017` 仍为 `conditional_frozen`）
>
> **状态增量**: `DECK-GATE-DEC-016 = frozen`、`DECK-GATE-DEC-018 = frozen`（依据 [SUO-253](/SUO/issues/SUO-253) 的 CEO `approve` 裁决）；`DECK-GATE-DEC-019 = frozen`（依据 [SUO-267](/SUO/issues/SUO-267) 的 `approve` 裁决）；`DECK-GATE-DEC-020 = frozen`（依据 [SUO-254](/SUO/issues/SUO-254) 的 CEO `approve` 裁决）
>
> **适用流水线**: `design → issue → task → stage`

## 1. 背景与目标

主设计 §22、Issue 决策单 `DECK-016`～`DECK-020` 与 Stage 计划 §6 将五项架构/UX 问题保留为默认假设。默认假设可以支持早期拆解，但不能作为 API、生产部署、安全策略或 UI 文案的冻结依据。

本附录给出五项可引用的 Gate 结论，使下游能明确判断对应设计是已冻结、条件性冻结、限域通过还是阻断，并避免继续把默认假设写成已批准方案。其中 `DECK-GATE-DEC-016`、`DECK-GATE-DEC-018` 已由 [SUO-253](/SUO/issues/SUO-253) 的 CEO Stage 2 裁决冻结，`DECK-GATE-DEC-019` 已由 [SUO-267](/SUO/issues/SUO-267) 的安全撤销矩阵复审裁决冻结，`DECK-GATE-DEC-020` 已由 [SUO-254](/SUO/issues/SUO-254) 的 CEO Stage 3 裁决冻结；`DECK-GATE-DEC-017` 仍为条件性冻结。设计冻结不自动表示多节点/临时 runtime 或生产运行 rollout 已放行。

### 1.1 真相源与优先级

1. 本附录不重写稳定主设计；主设计除 §22 五项未决说明外继续有效。
2. 对 `DECK-016`～`DECK-020`，本附录的结论、合同和 Gate 条件优先于主设计 §22、Issue 清单和既有 Task/Stage 中的默认假设。
3. 下游对 `DECK-GATE-DEC-016`、`DECK-GATE-DEC-018`、`DECK-GATE-DEC-019`、`DECK-GATE-DEC-020` 应按本文已冻结设计消费；`DECK-GATE-DEC-017` 在获得本附录列出的审批前只能按 `conditional_frozen` 的限域条件推进，不得把状态写为 `approved` 或 `fully_frozen`。
4. 审批方提出实质变更时，增量修订本文件并保留原决策记录；不得另建平行主文档。

## 2. 范围界定

### 2.1 范围内

- Deck Plugin catalog 与 ClaudeAgent Runtime Admin 的物理承载和写所有权；
- 生产 marketplace 制品签名、摘要校验、引用留存与恢复合同；
- 单节点、多节点及临时 runtime 的制品分发、readiness 和运行节点绑定；
- 普通禁用、安全撤销、紧急撤销对新运行和非终态运行的行为；
- Voice 持久 chat 发起 Workflow Run 后，来源关系、独立 run-scoped session 与用户可见界面；
- 对应 Stage Gate、受影响 Task、兼容与回滚要求、审批角色与已记录裁决。

### 2.2 范围外

- 不拆分或改写 `docs/issue/`、`docs/task/`、`docs/stage/`；
- 不指定具体仓库目录、数据库供应商、消息队列或云厂商；
- 不实现 marketplace、runtime、撤销服务或前端组件；
- 不改变 Deck 是唯一业务模块、story-workspace 是运行/结果 owner、ClaudeAgent 是执行/session owner 的既有边界；
- 不把 Paperclip Plugin worker 模型引入 Deck Plugin 或 Claude Code Plugin 运行链路；
- 不替代安全、运行平台、产品 owner 对生产启用的正式审批。

## 3. 方案摘要与冻结状态

`frozen` 表示设计方案、服务边界和最小合同已经完成裁决，下游不得改成另一架构；`conditional_frozen` 表示方案已确定但仍等待对应 owner 审批。两者都不自动表示 production-ready 或运行 rollout 已放行，运行 Gate 仍以各行限制和 §5.2 证据为准。CEO 分别在 [SUO-253](/SUO/issues/SUO-253) 与 [SUO-254](/SUO/issues/SUO-254) 以组织最高决策权限临时覆盖相应缺位 owner，[SUO-267](/SUO/issues/SUO-267) 对安全撤销矩阵作出具名 `approve`；上述覆盖或批准均不覆盖代码正确性、其他决策或实际生产发布。

| 决策单 | 决策 ID | 条件性结论 | Gate 结论 | 仍需审批 |
|---|---|---|---|---|
| `DECK-016` | `DECK-GATE-DEC-016` | **`frozen`**：不新增第三个业务服务；Deck control plane、ClaudeAgent runtime control、story-workspace 三域单写，由无状态 gateway 聚合 | **Stage 2 设计 Gate 已通过**；物理拆分只能替换 transport/deployment adapter，不得改变领域合同或写所有权 | 无；CEO 已在 [SUO-253](/SUO/issues/SUO-253) 以 Stage 2 限域代理权限 `approve` |
| `DECK-017` | `DECK-GATE-DEC-017` | 生产制品必须以 SHA-256 精确摘要、受信签名包和引用感知留存共同构成完整性合同 | 非生产可限域推进；Stage 4 生产 Gate 在验证/恢复能力落地前为**阻断** | 安全 owner、marketplace/制品平台 owner、runtime owner |
| `DECK-018` | `DECK-GATE-DEC-018` | **`frozen`**：采用共享 CAS 源 + pool/node/session 分层；run-ready 只在选定节点产生 `session_loaded` 回执后成立；session 前可重调度，session 后必须新 attempt | 仅 `runtime_pool_id == runtime_environment_id` 且 `distribution_mode=local_persistent` 的单节点形态**限域通过**；多节点/临时 runtime 仍为 rollout **阻断** | 设计无待审批；多节点/临时 runtime 仍需 §5.2 解锁证据与具名 runtime/SRE 签署 |
| `DECK-019` | `DECK-GATE-DEC-019` | **`frozen`**：`DISABLE` 不终止既有 run；`REVOKE` 默认 60 秒、最大 300 秒 grace 后硬停；`EMERGENCY` 零 grace 立即硬停 | 设计审批已通过；真实 11 项 evidence pack、独立 reviewer 签署及 rollout 审批完成前，Stage 4 production Gate 仍为**阻断** | 设计无待审批；production Gate 仍需独立 reviewer 与 rollout approver |
| `DECK-020` | `DECK-GATE-DEC-020` | Voice chat 保留原线程；创建独立 Workflow Run/Agent session，以双向来源卡片和运行详情显式连接，禁止伪装成同一 chat | `frozen`；Stage 3 UI/文案 Gate **已通过**，下游 E2E/发布验收仍须留下批准裁决要求的证据 | 无；CEO 已以组织最高决策权限临时覆盖产品、Voice/Chat 与 story-workspace owner 完成裁决 |

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

- **Gate**：Stage 2 服务边界设计 Gate 已通过并冻结；跨域 API/schema 必须遵守三域单写与无状态 gateway 合同。物理拆分不是本 Gate 的必要条件，发生拆分时只能替换 transport/deployment adapter。
- **直接影响 Task**：`task_deck_001_backend_manifest-model.md`、`task_deck_003_backend_installation-lifecycle.md`、`task_deck_004_backend_compatibility-capability.md`、`task_210_shared_deck_plugin_binding.md`、`task_deck_006_backend_workflow-preflight.md`、`task_deck_008_backend_reconcile-load-receipt.md`、`task_deck_009_backend_run-scoped-session.md`、`task_deck_014_backend_api-error-codes.md`。
- **审批记录**：CEO `a77605f2-8bbf-4eb9-9cda-7c036f5c5f75` 在 [SUO-253](/SUO/issues/SUO-253) 以组织最高决策权限临时覆盖缺位的 Deck/Voice Decks、ClaudeAgent runtime、运行平台/SRE owner，对本项作出 `approve`；覆盖范围仅限 Stage 2 架构与放行边界，不扩张为后续生产运维授权。

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

- 单节点 persistent runtime 仅在 `runtime_pool_id == runtime_environment_id` **且** `distribution_mode=local_persistent` 时作为一节点特例推进；仍必须保留 digest 校验、scoped readiness、`runtime_node_id`、`session_loaded` 与 node/session receipt 语义。
- 分发功能可以通过 `distribution_mode=local_persistent` 回滚，但 readiness scope 和 receipt 语义不可回滚。
- 多节点 rollout 失败时只关闭多节点调度，回到单节点池；不得伪造全局 ready 或跳过 digest 校验。

#### 4.3.5 Gate、Task 与审批

- **Gate**：Stage 2 分发设计已冻结，但运行放行仅覆盖满足 §4.3.4 双条件的单节点形态。任何多节点/临时 runtime 环境在 §5.2 全部解锁证据和具名签署完成前仍为 rollout 阻断，不得标记为 production-ready。
- **直接影响 Task**：`task_deck_006_backend_workflow-preflight.md`、`task_deck_008_backend_reconcile-load-receipt.md`、`task_deck_009_backend_run-scoped-session.md`、`task_deck_013_backend_events-audit.md`、`task_deck_014_backend_api-error-codes.md`、`task_211_frontend_plugin_admin_ui.md`、`task_213_frontend_story_workspace_status.md`。
- **审批记录**：CEO `a77605f2-8bbf-4eb9-9cda-7c036f5c5f75` 在 [SUO-253](/SUO/issues/SUO-253) 对共享 CAS、pool/node/session 分层、`session_loaded` run-ready、session 前重调度与 session 后新 attempt 作出 `approve`。该批准冻结设计，不替代多节点/临时 runtime 所需的运行证据和具名 runtime/SRE rollout 签署。

### 4.4 `DECK-GATE-DEC-019`：安全撤销策略

#### 4.4.1 采用方案

三个等级及其服务端行为已由 [SUO-267](/SUO/issues/SUO-267) 的具名 `approve` 裁决冻结；该设计审批不替代真实证据、独立 reviewer 签署或 rollout 审批：

| 等级 | 新 installation / binding / preflight / run | `effective_at` 时的受影响非终态 run | session 动作 | 恢复 |
|---|---|---|---|---|
| `DISABLE` | 对命中目标的新操作立即阻止 | 继续使用既有不可变 lock/snapshot 直到原终态；**不得**写入 `cancelling` | 不撤权、不终止 | 具备同 scope 权限的 Deck Operator 可重新 enable；不改历史 run/lock |
| `REVOKE` | 撤销屏障提交后立即阻止 | 原子转入 `cancelling`；在有限 grace 内只允许到安全停止点，届时未终止者强制 hard-stop | 立即撤销新增工具/网络授权；grace 结束前关闭 session，超时强制终止 | 原 run 永不恢复；只允许 superseding release/policy 通过新 preflight 创建 new run |
| `EMERGENCY` | 撤销屏障提交后立即阻止 | 零 grace，立即发出 hard-stop；不得等待 checkpoint、进度保存或通知 | 立即撤权、隔离并硬终止 | 不允许原地解除或复活；只允许 superseding release/policy + new run 恢复 |

所有等级都先生成不可变 `SecurityRevocationRecord`。`REVOKE` / `EMERGENCY` 的撤销屏障、影响清单和取消 outbox 必须在同一提交边界内落盘；提交成功的服务端时间为 `effective_at`。任何被 `REVOKE` / `EMERGENCY` 置入安全取消路径的 run 在该屏障之后不得转成 `completed`；`DISABLE` 不把既有 run 放入安全取消路径，因此其真实完成不属于安全终态映射。

#### 4.4.2 权限、双人控制与 break-glass

逻辑角色是生产权限合同，不代表当前组织已经完成具名任命。一个主体可以拥有多个普通角色，但在同一 `REVOKE` / `EMERGENCY` 上仍受下表的职责分离约束。

| 等级 | 发起 | 批准 | runtime 执行 | 审计复核 | 控制规则与最小 scope |
|---|---|---|---|---|---|
| `DISABLE` | `DeckOperator`，需 `deck.disable` | 无独立批准；发起即生效 | Deck control plane 的 `RevocationCoordinator` 仅安装阻止屏障；runtime 不得收到终止命令 | `DeckAuditReviewer` 在 24 小时内复核 | 允许单人控制；仅限其管理的 `environment_id + tenant_id/project_id + installation_id|binding_id|release_id`，禁止全局签名身份或全局策略 scope |
| `REVOKE` | `SecurityResponder`，需 `security.revocation.propose` | **不同主体**的 `SecurityApprover`，需 `security.revocation.approve` | `RevocationCoordinator`、Workflow Run canceller、runtime terminator 三个机器主体只执行已批准的 `impact_manifest_id`，无扩 scope 权限 | 与发起/批准均不同的 `SecurityAuditReviewer` 在 24 小时内复核 | 生效前强制双人控制；scope 必须同时包含 environment、tenant/project 边界和一个版本化 target；跨 tenant/global scope 需 `security.revocation.approve_global` |
| `EMERGENCY` | 当班 `SecurityResponder`，需短时 JIT `security.revocation.break_glass` | 不等待事前批准；不同主体的 `SecurityApprover` 须在 `effective_at + 30 分钟` 前追认 | 与 `REVOKE` 相同，但只接受 `termination_mode=hard`，不能降低为 graceful | 独立 `SecurityAuditReviewer` 在 24 小时内完成 break-glass 复核 | break-glass 凭证最长 15 分钟、单次 `revocation_id`、绑定 incident ID 和允许的最大 scope；追认失败不撤销已执行动作，而是立即升级 incident 并冻结该主体后续 break-glass 权限 |

共同最小权限规则：

1. 人类主体只能提出或批准规范化 scope，不可直接调用 runtime kill 接口；机器执行主体只能消费签名的 `impact_manifest_id + manifest_sha256`。
2. 每个请求必须携带 `environment_ids`、`tenant_or_project_ids`、唯一 `target_type + target_key`、`reason_code`、`incident_id`（`REVOKE` / `EMERGENCY` 必填）和 `requested_by`。
3. `target_type=signing_identity|capability_policy` 若解析到授权边界外对象，服务必须返回 `REVOCATION_SCOPE_APPROVAL_REQUIRED`，列出脱敏计数和所需更高 scope，不得静默截断或扩大。
4. runtime executor 不拥有 release、policy 或权限配置写权；审计 reviewer 只有 append-only 证据读取/签署复核权。

#### 4.4.3 撤销目标与确定性影响解析

唯一允许的目标类型及规范化 key 为：

| `target_type` | `target_key` | 必须解析的对象 |
|---|---|---|
| `deck_plugin_release` | `deck_plugin_release_id` | 引用该 release 的 installation、当前/历史 binding revision、runtime lock/snapshot、`effective_at` 时仍非终态的 run |
| `runtime_plugin_digest` | `sha256:<64-lowercase-hex>` | lock/snapshot 中含该 digest 的 installation/binding/run，以及已物化该 digest 的 runtime node/session |
| `signing_identity` | `trust_domain + issuer + subject + key_fingerprint` | 由该身份签名且仍在留存范围内的 release/digest，再传递解析其 installation/binding/非终态 run |
| `capability_policy` | `policy_id + policy_revision` | 绑定该精确 revision 的 installation/binding/lock/snapshot/非终态 run；不得用未版本化 policy 名称替代 |

影响解析遵循以下确定性语义：

1. 在与撤销屏障相同的一致性快照上，按 ID 字典序生成不可变 `RevocationImpactManifest`，至少包含 `impact_manifest_id`、四类对象 ID 列表、`resolved_at`、`resolver_revision`、`manifest_sha256` 和计数。
2. `DISABLE` 只阻止目标 installation/binding/release 的未来解析，不递归终止运行；`REVOKE` / `EMERGENCY` 对解析出的全部非终态 run 建立安全取消屏障。已在 `effective_at` 之前真正终态的 run 只保留历史引用，不接收取消命令。
3. 影响清单提交后不可原地扩 scope。扩大 target、environment 或 tenant/project 范围必须新建 `revocation_id`，写 `extends_revocation_id`，重新执行适用于新增 delta 的批准规则；旧记录和旧 manifest 均保留。
4. 相同 `idempotency_key` 的重复请求必须返回原 `revocation_id + impact_manifest_id`。不同 key 但规范化 scope 被一个已生效的同级或更强撤销完全覆盖时，返回 `already_covered_by_revocation_id`，不重复发取消命令。
5. 并发重叠请求按每个受影响对象的 `revocation_sequence` 串行化；安全强度固定为 `EMERGENCY > REVOKE > DISABLE`。同强度取最小 sequence 为 primary；更强请求可以把尚未终止的 run 从 graceful 升级为 hard，较弱/较晚请求不得降级、延长 deadline 或改变既有终态。
6. 一个 run 可记录多个 `related_revocation_ids`，但终态只绑定实际触发终止的 `primary_revocation_id`；并发 loser 必须写 `workflow.run.security_cancellation_suppressed` 证据，不得再次 kill 或产生另一终态。

#### 4.4.4 grace、hard-stop 与时间语义

生产参数绑定 `revocation_policy_revision=security-revocation/v1`，不得由客户端任意覆盖：

| 等级 | `effective_grace_seconds` | `grace_deadline_at` | 到期动作 |
|---|---:|---|---|
| `DISABLE` | `null` | `null` | 无取消、无终止 |
| `REVOKE` | 未显式请求时默认 **60 秒**；允许 `0..300` 秒 | `effective_at + effective_grace_seconds` | deadline 到达后 1 秒内为仍非终态 run 发出 hard-stop；runtime 须在命令发出后 10 秒内确认终止或确认隔离 |
| `EMERGENCY` | 固定 **0 秒** | 等于 `effective_at` | 撤销提交后 1 秒内发 hard-stop；runtime 须在命令发出后 10 秒内确认终止或确认隔离，不等待 checkpoint |

`REVOKE` 的计时从全局 `effective_at` 开始，而不是从各消费者收到消息时开始。请求大于 300 秒必须以 `REVOCATION_GRACE_OUT_OF_RANGE` 拒绝；记录生效后不得延长 deadline。缩短等待只能新建更强的 `EMERGENCY`，或同 scope 新建 `REVOKE` 且 deadline 更早；合并时取最早 deadline。

在 grace 内，runtime 只允许完成安全 checkpoint 和非敏感诊断持久化，不允许提交业务成功结果、开启新外部副作用或获取新授权。到期时消息延迟、通知失败、checkpoint 卡住都不是延迟 hard-stop 的理由。若 10 秒内既无终止确认也无隔离确认，run 保持 `cancelling`，升级 `SECURITY_TERMINATION_UNCONFIRMED` incident；不得先写伪终态。

#### 4.4.5 无歧义终态映射

撤销屏障必须以 compare-and-set 把命中的非终态 run 转为 `cancelling`，从而阻止后续成功提交。终态映射只允许下表结果：

| 观测结果 | run 终态 | `termination_mode` | 必填原因/证据 |
|---|---|---|---|
| `REVOKE` 在 deadline 前到达安全停止点并收到 cancellation ack | `cancelled` | `graceful` | `terminal_reason_code=SECURITY_REVOCATION`、`revocation_id`、`termination_receipt_id` |
| `REVOKE` 到期后 hard-stop 获 runtime 确认 | `cancelled` | `hard` | 同上，并记录 `hard_stop_command_id`、deadline 与 ack 时间 |
| `EMERGENCY` hard-stop 获 runtime 确认 | `cancelled` | `hard` | 同上；`grace_deadline_at == effective_at`，且无 checkpoint 等待 |
| runtime 在 cancellation ack 前崩溃/失联/异常退出，且执行凭据和 node/session 隔离已确认 | `failed` | 实际最后请求的 `graceful` 或 `hard` | `terminal_reason_code=SECURITY_REVOCATION`、`failure_detail_code`、`isolation_receipt_id`、`revocation_id` |
| 终止/隔离尚未确认 | 保持 `cancelling`，不是终态 | 实际最后请求的模式 | `SECURITY_TERMINATION_UNCONFIRMED` incident；持续隔离与人工处置 |

所有由本安全路径产生的终态都必须保留 `cancel_reason=security_revocation`、公开错误码 `SECURITY_REVOCATION`、`revocation_id` 和 `termination_mode`。`completed` 不在映射表中；屏障提交后出现 `completed` 必须拒绝该状态写入并生成 `RUN_TERMINAL_CONFLICT` 审计事件。仅在 `effective_at` 之前已提交成功终态的 run 不属于此次“安全撤销路径”，其历史状态保持不变。

#### 4.4.6 取消幂等、投递与事件证据

1. 每个受影响 run 的命令唯一键为 `(revocation_id, workflow_run_id)`，数据库和消费者 inbox 都建立唯一约束；`security_cancel_command_id` 由该键稳定派生或首次创建后永久复用。
2. outbox 至少一次投递。消费者首次处理执行状态转换/终止；重放只返回同一个 `termination_receipt_id` 和当前终态，不重复 checkpoint、kill、终态事件或用户通知。
3. 状态写入使用 `run_state_version` compare-and-set。已存在同一安全终态时 replay ack；已存在不同终态时拒绝并追加 `RUN_TERMINAL_CONFLICT`，不得覆盖。
4. 事件最少包含：`security.revocation.effective`、`workflow.run.security_cancellation_requested`、可选 `workflow.run.security_hard_stop_requested`、最终 `workflow.run.security_cancelled|security_failed`、重复/并发抑制事件。每条包含唯一 `event_id`、`revocation_id`、`workflow_run_id`、`command_id`、`delivery_attempt`、`termination_mode`、前后状态和发生时间。
5. `SecurityRevocationRecord`、impact manifest、outbox/inbox receipt、runtime termination/isolation receipt 和通知 receipt 均写 append-only 审计域。纠错只追加 superseding 记录；禁止 update/delete 原事件。

#### 4.4.7 通知合同

撤销提交时须在持久化 outbox 创建通知，不依赖进程内队列。通知正文只含公开安全摘要、受影响对象、run 链接、当前状态和支持/恢复入口，不回显 secret、prompt、原始制品或未脱敏 incident 细节。

| 等级 | 运行 owner / 发起用户 | 安全值班 | 时序 |
|---|---|---|---|
| `DISABLE` | 对 `effective_at` 时的既有 run 发送“本 run 不终止、后续重跑会被阻止”；无既有 run 时通知 installation/binding owner | 收到审计摘要但不触发 paging | 三方首次投递均不晚于 `effective_at + 5 分钟` |
| `REVOKE` | 每个受影响 run 的 owner 与 `started_by_user_id` 收到 cancelling 通知；终态后收到结果/恢复说明 | 收到 impact、deadline 和终止进度 | 安全值班首次投递不晚于 30 秒；用户首次投递不晚于 60 秒；终态更新不晚于终态后 60 秒 |
| `EMERGENCY` | 每个受影响 run 的 owner 与发起用户收到硬停和恢复说明 | 立即收到 incident、impact 与隔离状态 | 先提交屏障并发 hard-stop，通知绝不在其关键路径；安全值班首次投递不晚于 30 秒，用户不晚于 60 秒 |

每个通知以 `notification_id` 和 `(revocation_id, workflow_run_id|null, recipient_id, notification_phase)` 去重。投递计划固定为首次立即尝试，失败后在 `+30 秒、+2 分钟、+10 分钟、+30 分钟、+2 小时` 重试，共最多 6 次；接收端重复 receipt 视为成功。全部失败时写 `security.notification.delivery_failed`、保留 provider receipt/error code，并通过独立值班告警通道创建 incident；不得回滚撤销、延长 grace 或延迟 `EMERGENCY`。通知 outbox 至少保留到 Stage 4 定义的安全审计留存期结束。

#### 4.4.8 隔离与恢复

- revoked release/digest、相关签名身份和 policy revision 标记为 quarantined，禁止被新 installation、binding、preflight 或 runtime load 解析；原始字节、签名包、lock、receipt 和审计事件按取证留存，不物理覆盖。
- `DISABLE` 允许同一对象由授权 Deck Operator enable；`REVOKE` / `EMERGENCY` 不允许“unrevoke”原记录。
- 恢复必须创建新的 superseding release 或 policy revision，重新完成签名、capability/preflight、runtime load receipt，并创建新的 `workflow_run_id + agent_session_id`。旧 run 保持 `cancelled|failed`，旧 session 永不复活。
- 禁止自动降级到“最近可用”版本、缩小能力集合后静默重试，或修改历史 runtime lock 来伪造恢复。

#### 4.4.9 Stage 4 审计演练证据包

production Gate 只接受单一 `Stage4RevocationEvidencePack`。包头必须包含 `evidence_pack_id`、`design_decision_id=DECK-GATE-DEC-019`、`revocation_policy_revision`、被测 release/commit、测试环境、`test_run_id`、生成时间、独立 reviewer、证据对象清单和 `evidence_manifest_sha256`。每个 case 必须保存原始时间戳；只写文字结论不算证据。

| 演练项 | 必须留存的测试/事件/审计标识 | 唯一通过条件 |
|---|---|---|
| 三等级权限与行为矩阵 | `test_case_id`；actor/approver/executor/reviewer principal ID；授权判定日志；三类 `revocation_id`；对应 `impact_manifest_id` | `DISABLE` 单人最小 scope 可生效且无取消命令；`REVOKE` 同人批准被拒、双人批准成功；`EMERGENCY` 可 break-glass 先执行且 30 分钟内有独立追认，越权 scope 均失败 |
| 四目标影响解析 | 四类 target 各自的 `test_case_id`、`impact_manifest_id`、`manifest_sha256`、installation/binding/lock/run ID 列表 | 四类 target 解析结果与 fixture 完全相等；排序/hash 可重放；授权边界外 scope 不截断、不静默扩大 |
| scope 扩大、重复与并发 | 原/扩展 `revocation_id`、`extends_revocation_id`、idempotency response、`revocation_sequence`、suppressed event ID | 扩大产生新记录和 delta 审批；同 key 返回原记录；重叠请求遵守强度/sequence，run 只有一个 primary 终态且不降级 deadline/mode |
| `DISABLE` 不中止 | active `workflow_run_id`、disable `revocation_id`、preflight 拒绝事件、运行终态事件 | 新操作被阻止；已有 run 不进入 `cancelling`、无终止命令并按原逻辑到终态 |
| `REVOKE` grace→hard-stop | `effective_at`、`grace_deadline_at`、取消/硬停 command/event ID、runtime receipt、最终 run event ID | 默认 60 秒与显式 300 秒边界均可复现；deadline 后 1 秒内发 hard-stop、10 秒内确认终止/隔离；终态字段与 §4.4.5 一致且从不 `completed` |
| `EMERGENCY` 立即硬停 | revocation/event ID、hard-stop command、runtime/isolation receipt、checkpoint trace | grace 为 0；1 秒内发 hard-stop、10 秒内确认；`effective_at` 后无 checkpoint/成功提交；通知故障注入不改变时间线 |
| 重复取消与至少一次投递 | 同一 command 的 `delivery_attempt >= 2`、inbox/outbox receipt、termination receipt、终态 event ID | 重放复用同一 receipt；只有一次真实终止和一个一致终态，无重复/矛盾通知 |
| 终态映射与冲突防护 | graceful、hard、异常隔离、未确认四类 `test_case_id`，CAS 冲突事件 ID | `cancelled`/`failed`/保持 `cancelling` 与 §4.4.5 逐项一致；安全路径写 `completed` 必被拒并留下 `RUN_TERMINAL_CONFLICT` |
| append-only 审计 | revocation record、manifest、outbox/inbox、termination/isolation、notification receipt ID；hash-chain/WORM 验证报告；update/delete 拒绝日志 | 所有引用可从 `revocation_id` 双向追溯；hash 校验通过；修改/删除尝试均失败且自身也被审计 |
| 通知时序与失败 | 各角色 `notification_id`、delivery attempt/receipt、故障注入 ID、delivery_failed/incident ID | 满足 30 秒/60 秒/5 分钟时限；重试序列和去重符合合同；穷尽失败可追踪且不延迟 grace/hard-stop |
| 隔离与 superseding 恢复 | quarantine receipt、旧对象拒绝日志、superseding release/policy ID、新 preflight/load receipt/new run/session ID | 旧对象不可新加载；旧 run/session 不复活；只有完成重新签名、preflight、load receipt 的新 run 恢复成功 |

证据包缺任一行、任一必填标识、原始 receipt 或 reviewer 签署，都视为 production Gate 失败。本文只定义证据合同，不把尚未执行的演练伪装成证据；本修订合同已由 [SUO-267](/SUO/issues/SUO-267) 明确 `approve`，因此决策状态为 `frozen`。设计冻结后仍必须真实生成完整 evidence pack、取得独立 reviewer 签署并获得 production rollout 审批，才能打开 production Gate。

#### 4.4.10 替代方案

| 替代方案 | 结论 | 原因 |
|---|---|---|
| 所有禁用/撤销都让活动 run 继续 | 拒绝 | 已知恶意/泄漏能力会继续执行 |
| 所有普通禁用都立即杀 run | 拒绝 | 将日常运维误作安全事故，造成不必要数据损失 |
| 撤销后自动回退最近可用版本 | 禁止 | 可能绕过批准能力、schema 和摘要锁 |
| 原地删除/修改历史 runtime lock | 禁止 | 破坏审计和复现 |

#### 4.4.11 影响合同

- `SecurityRevocationRecord` 至少包含 `revocation_id`、`idempotency_key`、`level`、规范化 scope、`actor_id`、`approver_id`、`reason_code`、`incident_id`、`effective_at`、`effective_grace_seconds`、`grace_deadline_at`、`revocation_policy_revision`、`impact_manifest_id`、`extends_revocation_id`。
- `RevocationImpactManifest` 至少包含受影响 installation/binding/release/digest/policy/lock/snapshot/run/session/node ID、`resolved_at`、`resolver_revision`、计数与 `manifest_sha256`。
- Workflow Run 增加 `cancel_reason=security_revocation`、`terminal_reason_code=SECURITY_REVOCATION`、`revocation_id`、`related_revocation_ids`、`termination_mode=graceful|hard`、`termination_receipt_id`、可选 `isolation_receipt_id`。
- preflight/运行错误码统一使用 `SECURITY_REVOCATION`，响应只给安全摘要和恢复去向。
- 管理 UI 显示撤销等级、影响范围、运行处理进度和审计入口；普通用户不能触发 `REVOKE`/`EMERGENCY`。

#### 4.4.12 兼容与回滚

- 旧的 `disabled` 映射为 `DISABLE`，不会意外终止既有 run。
- revocation record 不可删除或原地改为“未撤销”；误报通过新的 superseding policy/release 记录修复。
- 代码 rollout 可关闭自动硬终止并回到人工处置，但此回滚只允许在非生产演练；production Gate 一旦批准，关闭 hard-stop 能力本身视为安全降级，必须由安全 owner 走独立紧急变更流程并关闭新 run。

#### 4.4.13 Gate、Task 与审批

- **Gate**：`DECK-GATE-DEC-019` 已由 [SUO-267](/SUO/issues/SUO-267#comment-6ac1ba89-f6dd-4b69-ac2c-5dfd79fe440c) 的具名 `approve` 裁决更新为 `frozen`；获批输入 SHA-256 为 `085796ffc67a54d5f9ec2a45df9d454f742fc14503570ced2ccafee7aca51d23`。Stage 4 production Gate 另行保持**阻断**，直到 §4.4.9 的真实 11 项证据包齐全、独立 reviewer 签署且 rollout 审批明确通过。设计 `frozen` 不等于 production-ready。
- **直接影响 Task**：`task_deck_001_backend_manifest-model.md`、`task_deck_003_backend_installation-lifecycle.md`、`task_deck_004_backend_compatibility-capability.md`、`task_deck_007_backend_workflow-run.md`、`task_deck_009_backend_run-scoped-session.md`、`task_deck_013_backend_events-audit.md`、`task_deck_015_backend_revocation-rollback.md`、`task_211_frontend_plugin_admin_ui.md`、`task_213_frontend_story_workspace_status.md`。
- **审批动作**：设计审批已由 [SUO-267](/SUO/issues/SUO-267) 完成，批准范围为撤销角色、scope、60/300 秒 grace、break-glass、通知合同、取消幂等、终态映射、1/10 秒 hard-stop SLO 与证据合同。实际 rollout 前仍须真实生成完整 evidence manifest，由独立 reviewer 签署并取得 rollout 审批；这些动作尚未完成。

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

- **Gate**：Stage 3 UI/文案 Gate 已由 [SUO-254](/SUO/issues/SUO-254) 的 CEO `approve` 裁决通过，本项状态为 `frozen`；下游 E2E/发布验收仍须按该裁决留证，且不得将本通过结论外推到代码正确性、runtime/安全 Gate 或实际生产发布。
- **直接影响 Task**：`task_deck_007_backend_workflow-run.md`、`task_deck_009_backend_run-scoped-session.md`、`task_212_frontend_deck_editor_plugin_binding.md`、`task_213_frontend_story_workspace_status.md`、`task_deck_013_backend_events-audit.md`。
- **审批动作**：已完成。CEO 以组织最高决策权限临时覆盖产品、Voice/Chat 与 story-workspace owner，对既有显式启动、原 chat 留卡、独立 run/session、双向来源、权限降级与发布文案作出 `approve` 裁决；批准内容保持 §4.5.1～§4.5.4 不变。

## 5. 验收标准

### 5.1 设计验收

- [x] 五项决策分别有唯一决策 ID 和明确采用方案；`DECK-GATE-DEC-016`、`DECK-GATE-DEC-018`、`DECK-GATE-DEC-019`、`DECK-GATE-DEC-020` 为 `frozen`，`DECK-GATE-DEC-017` 为 `conditional_frozen`。
- [x] 每项均列出替代方案及采用/拒绝理由。
- [x] 每项均列出跨域合同变化、兼容策略和回滚边界。
- [x] 每项均标注 Stage Gate、直接受影响 Task，以及仍需审批角色或已记录裁决。
- [x] 默认假设、设计冻结与运行 rollout 放行已区分；未获得的生产/运行审批未写成已完成。
- [x] 本附录不改写稳定主设计，也不修改 issue/task/stage/exec 或实现代码。
- [x] `DECK-GATE-DEC-019` 已补齐逐等级角色与职责分离、四类 target 影响解析、scope 扩大/重复/并发语义、确定 grace/hard-stop 参数、终态映射、通知重试和取消幂等。
- [x] `DECK-GATE-DEC-019` 已定义可追溯到测试、事件、命令、receipt 和审计 ID 的 Stage 4 evidence pack；尚未执行的演练和审批未标记为通过。

### 5.2 下游 Gate 验收

| Gate | 必须验证 | 通过标准 |
|---|---|---|
| Stage 2 / `DECK-016` | 单写者/API facade 一致性验证 | Deck control plane、ClaudeAgent runtime control、story-workspace 三域无重复 writer，gateway 无业务状态；物理拆分只替换 transport/deployment adapter |
| Stage 2 / `DECK-018`（单节点） | 部署范围声明、digest、scoped readiness 与 node/session receipt 测试 | `runtime_pool_id == runtime_environment_id` 且 `distribution_mode=local_persistent`；选定节点产生与 lock 一致的完整 `session_loaded` 回执后才 run-ready |
| Multi-node / ephemeral rollout / `DECK-018` | CAS 可用与同 digest 恢复；pool eligibility 与不可变 node/session 绑定；完整 load receipt；节点失联前后恢复；临时节点空 cache 启动；容量预算/配额；高低水位或等价压力阈值；LRU 或等价淘汰；运行中制品保护；冷启动与淘汰测试；告警与回退单节点演练 | 全部证据可审计通过，且 ClaudeAgent runtime owner 与运行平台/SRE owner 具名签署；缺任一项均保持阻断且不得标记 production-ready |
| Stage 3 / `DECK-020` | Voice → run E2E、权限和文案评审 | 设计 Gate 已 `frozen`；下游须证明原 chat 留卡、run 页面有反向来源、session 不进入 Chat 历史，并满足 [SUO-254](/SUO/issues/SUO-254) 裁决列出的权限降级、单次创建和重试链证据 |
| Stage 4 / `DECK-017` | 签名/digest 篡改测试、冷恢复演练、引用清理测试 | 篡改必拒绝；冷恢复得到同 digest；有引用时无法 purge |
| Stage 4 / `DECK-019` | §4.4.9 `Stage4RevocationEvidencePack` 全部 11 项演练、独立 reviewer 签署及 rollout 审批 | 设计审批已由 [SUO-267](/SUO/issues/SUO-267) 通过；真实 evidence 必须使权限/scope/grace/终态/通知/幂等/append-only/隔离恢复逐项满足唯一通过条件，且 evidence manifest hash 可验证，随后取得 rollout 审批 |

## 6. 风险与依赖

| 风险/依赖 | 影响 | 缓解或阻断条件 |
|---|---|---|
| 下游实现偏离已冻结服务边界 | 出现第三业务服务、重复 writer 或 gateway 持有业务状态 | 按 `DECK-GATE-DEC-016` 阻断偏离方案；只允许替换 transport/deployment adapter |
| marketplace 暂不支持签名包或冷恢复 | 供应链和历史复现不成立 | 仅允许 non-production/legacy_unverified，不得降级 production Gate |
| 多节点/临时 runtime 解锁证据或具名签署不完整 | 临时节点无法证明 ready，缓存压力或节点失联会破坏恢复合同 | 明确回到符合双条件的单节点池；不得宣称多节点 ready 或 production-ready |
| 真实 11 项 evidence pack、独立 reviewer 签署或 rollout 审批尚未完成 | 已冻结的 60/300 秒 grace、1/10 秒 hard-stop SLO 与角色边界仍不能视为生产授权 | `DECK-019` 保持设计 `frozen`，Stage 4 production Gate 继续阻断；完成真实证据、签署和 rollout 审批后才可放行 |
| runtime 无法在 10 秒内确认终止或隔离 | 安全 run 可能长期处于未知执行状态 | run 保持 `cancelling`，触发 `SECURITY_TERMINATION_UNCONFIRMED` incident；不得写伪终态或开放新 run |
| 通知 provider 不可用 | owner/发起用户/安全值班可能延迟获知 | 持久化 outbox 按固定 6 次计划重试并升级独立 incident；不得延迟 hard-stop |
| Chat 与 story-workspace 权限模型不同 | 来源链接可能泄露对话存在性 | 每个方向独立鉴权，无权时只给脱敏摘要 |
| 既有 Task 使用默认假设或遗留字段 | 下游实现与本附录冲突 | 下游只读消费本附录并做增量修订；不得反向改写本设计 |

关键依赖：Deck/Voice Decks 服务 owner、ClaudeAgent runtime/运行平台、受信 marketplace 与 CAS、签名信任根、Workflow Run 取消机制、Voice Chat 插卡能力、story-workspace 运行详情和权限检查。

## 7. 关键决策记录

| 决策 ID | 日期 | 状态 | 结论 | 替代/影响摘要 |
|---|---|---|---|---|
| `DECK-GATE-DEC-016` | 2026-08-01 | `frozen` | Deck control plane、ClaudeAgent runtime control、story-workspace 三域单写；无状态 gateway 聚合；不新增第三业务服务 | [SUO-253](/SUO/issues/SUO-253) CEO `approve`；物理拆分仅替换 transport/deployment adapter |
| `DECK-GATE-DEC-017` | 2026-08-01 | `conditional_frozen` | SHA-256 精确字节摘要 + 受信 DSSE/Sigstore 签名包 + 引用感知留存/恢复 | 无签名仅限非生产；阻断 Stage 4 production Gate |
| `DECK-GATE-DEC-018` | 2026-08-01 | `frozen` | 共享 CAS、pool/node/session 分层、选定节点 `session_loaded` 才 run-ready；session 前可重调度，session 后新 attempt | [SUO-253](/SUO/issues/SUO-253) CEO `approve` 设计；严格单节点限域通过，多节点/临时 runtime rollout 仍阻断 |
| `DECK-GATE-DEC-019` | 2026-08-01 | `frozen` | DISABLE 不中止；REVOKE 默认 60 秒/最大 300 秒后硬停；EMERGENCY 零 grace 立即硬停；取消与通知均具备可审计幂等合同 | [SUO-267](/SUO/issues/SUO-267) `approve`，获批输入 SHA-256 `085796ffc67a54d5f9ec2a45df9d454f742fc14503570ced2ccafee7aca51d23`；真实 11 项 evidence pack、独立 reviewer 签署及 rollout 审批仍未完成，Stage 4 production Gate 继续阻断 |
| `DECK-GATE-DEC-020` | 2026-08-01 | `frozen` | 原 Voice chat 留可更新卡片，独立 run/session 在 story-workspace 展示，并提供双向来源 | 禁止复用 thread 或把 run 当普通 chat；[SUO-254](/SUO/issues/SUO-254) 已批准 Stage 3 UI/文案 Gate，其他 Gate 与生产发布不在裁决范围内 |

## 8. 增量变更说明

- **新增 / SUO-249（2026-08-01）**：创建唯一决策 Gate 附录，替代主设计 §22 与下游文档中 `DECK-016`～`DECK-020` 的纯默认假设。
- **修订 / SUO-259（2026-08-01）**：依据 SUO-256 `request_changes` 增量重写 §4.4；新增逐等级 RBAC/双人控制/break-glass、四类 target 的影响 manifest、scope 扩大/重复/并发优先级、`REVOKE` 60 秒默认/300 秒上限与 1/10 秒 hard-stop SLO、确定性终态表、通知 outbox/6 次重试、取消幂等和 11 项 Stage 4 审计演练证据合同。`DECK-GATE-DEC-019` 状态未提升，继续为 `conditional_frozen`。
- **状态回写 / [SUO-257](/SUO/issues/SUO-257)（2026-08-01）**：消费 [SUO-254](/SUO/issues/SUO-254) 的 CEO `approve` 裁决，仅将 `DECK-GATE-DEC-020` 从 `conditional_frozen` 更新为 `frozen`；§4.5.1～§4.5.4 的既有 UX、权限与发布文案合同未改写。
- **状态回写 / [SUO-260](/SUO/issues/SUO-260)（2026-08-01）**：消费 [SUO-253](/SUO/issues/SUO-253) 的 CEO Stage 2 `approve` 裁决，将 `DECK-GATE-DEC-016`、`DECK-GATE-DEC-018` 从 `conditional_frozen` 更新为 `frozen`；冻结三域单写/无状态 gateway、共享 CAS/pool-node-session/readiness/attempt 合同，并保留严格单节点限域与多节点/临时 runtime rollout 阻断。未改变其余决策状态。
- **状态回写 / [SUO-269](/SUO/issues/SUO-269)（2026-08-01）**：消费 [SUO-267](/SUO/issues/SUO-267) 对 SHA-256 `085796ffc67a54d5f9ec2a45df9d454f742fc14503570ced2ccafee7aca51d23` 修订物的具名 `approve`，仅将 `DECK-GATE-DEC-019` 从 `conditional_frozen` 更新为 `frozen`；§4.4 安全撤销矩阵正文保持不变，真实 11 项 evidence pack、独立 reviewer 签署及 rollout 审批仍未完成，Stage 4 production Gate 继续关闭。
- 未修改 `docs/design/deck-plugin-voice-ink-dream-integration.md` 的稳定正文；本附录通过优先级声明提供增量覆盖。
- 未修改 `docs/issue/ISSUES_deck-plugin-voice-ink-dream-integration.md`、`docs/task/` 或 `docs/stage/stage_deck-plugin-voice-ink-dream-integration.md`；下游由各阶段 owner 只读消费并增量传播。

## 9. 阻塞或澄清说明

本附录本身无输入 blocker。`DECK-GATE-DEC-016`、`DECK-GATE-DEC-018` 已获得 [SUO-253](/SUO/issues/SUO-253) 的 CEO Stage 2 `approve` 裁决，`DECK-GATE-DEC-019` 已获得 [SUO-267](/SUO/issues/SUO-267) 的具名 `approve` 裁决，`DECK-GATE-DEC-020` 已获得 [SUO-254](/SUO/issues/SUO-254) 的 CEO Stage 3 `approve` 裁决；`DECK-GATE-DEC-017` 仍等待所列 owner 审批。因此：

- `[CLARIFICATION_NEEDED]` 仅继续适用于 `DECK-GATE-DEC-017`，表示“等待具名 owner 对本附录方案作 approve / request changes”。
- 多节点/临时 runtime 不属于设计歧义：其设计已经冻结，但运行 rollout 明确阻断；解锁责任人为 ClaudeAgent runtime owner 与运行平台/SRE owner，动作是补齐 §5.2 全部证据并具名签署。
- 各 Stage 必须分别读取“设计状态”和“运行 Gate”，不得以已冻结设计、默认假设、占位实现或 feature flag 代替 production-ready 证据。
- 对 `DECK-GATE-DEC-019`，[SUO-267](/SUO/issues/SUO-267) 已批准 [SUO-259](/SUO/issues/SUO-259) 修订物并将设计状态更新为 `frozen`；该裁决不执行证据、不构成 rollout 审批。Stage 4 production Gate 仍须等待 §4.4.9 真实 11 项 evidence pack、独立 reviewer 签署与 rollout 审批；[SUO-256](/SUO/issues/SUO-256) 的历史 `request_changes` 与后续修订链继续保留。
