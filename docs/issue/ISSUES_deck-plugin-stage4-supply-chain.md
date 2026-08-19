# Deck Plugin Stage 4 Supply-Chain 生产 Gate 增量 Issue 清单

> Issue: SUO-266
> 父项: SUO-258
> 设计裁决: SUO-261 (`no_design_delta`)
> 审批来源: SUO-255
> 来源设计稿: `docs/design/deck/design_002_deck-plugin-decision-gates.md` §4.2
> 决策状态: `DECK-GATE-DEC-017` = `conditional_frozen`
> 生成 Agent: IssueDispatcher
> 生成日期: 2026-08-01
> 所属流水线阶段: issue
> 上游阶段: design
> 下游阶段: task
> 下游 Agent: TaskDesignAgent

---

## 0. 文档元信息

- Issue 清单文件: `docs/issue/ISSUES_deck-plugin-stage4-supply-chain.md`
- 来源设计稿:
  - 主设计稿: `docs/design/deck/design_002_deck-plugin-decision-gates.md` (SUO-261)
  - 上游主设计: `docs/design/deck-plugin-voice-ink-dream-integration.md`
  - 关联设计稿: `docs/issue/ISSUES_deck-plugin-voice-ink-dream-integration.md` (SUO-237)
- 生成 Agent: `IssueDispatcher`
- 所属流水线阶段: `issue`
- 上游阶段: `design`
- 下游阶段: `task`
- 下游 Agent:
  - `TaskDesignAgent`
- 共享设计稿来源: `docs/design/`
- 是否作为当前实现合同: 是
- 备注:
  - 本文档由 SUO-266 指派，基于 SUO-261 `no_design_delta` 裁决，对 SUO-258 尚缺的实现、运营承诺与生产 Gate 证据做增量拆解。
  - 不得改写稳定设计（`DECK-GATE-DEC-016`、`DECK-GATE-DEC-018`、`DECK-GATE-DEC-019`、`DECK-GATE-DEC-020` 已冻结）。
  - `DECK-GATE-DEC-017` 仍为 `conditional_frozen`；本文档不将其提升为 `approve` 或 `fully_frozen`。
  - 若与设计稿冲突，以 `docs/design/` 中稳定设计稿为准。
  - 若与当前 API / 代码实现冲突，必须记录为阻塞或澄清项，不得静默覆盖。

---

## 1. 关联设计稿信息

- 主设计稿: `docs/design/deck/design_002_deck-plugin-decision-gates.md` §4.2
- 上游主设计: `docs/design/deck-plugin-voice-ink-dream-integration.md`
- 关联设计稿: `docs/issue/ISSUES_deck-plugin-voice-ink-dream-integration.md`
- 关联设计稿: `docs/design/deck/deck-integration-delta.md`

- 本清单覆盖范围:
  1. `DECK-GATE-DEC-017` 下具名安全、marketplace/制品平台、runtime owner 的权限范围与签署责任
  2. trust-policy 包：信任根/identity、轮换、撤销、过期、时间证明、允许算法矩阵、离线验证与 fail-closed
  3. 发布端与 runtime 端 SHA-256 双路径校验、RFC 8785 manifest 与签名验证
  4. published/deprecated/revoked、runtime lock、Workflow Run、legal hold、零引用后 90 天隔离与 purge 的引用状态机
  5. 签名包、证明留存、冷恢复可用性及可度量恢复目标的运营承诺
  6. 篡改矩阵、冷恢复演练、引用清理测试及可点击报告、run/commit、日志摘要、owner 签署
  7. 下游仍以"sha256 占位 / 决策未冻结"描述的旧假设对齐

- 明确排除范围:
  1. `DECK-GATE-DEC-016`、`DECK-GATE-DEC-018`、`DECK-GATE-DEC-019`、`DECK-GATE-DEC-020` 的已冻结设计（已由 SUO-253、SUO-254、SUO-267 裁决）
  2. 任何实现代码、数据库 migration、Stage/Exec 产物
  3. 通用多租户插件分发平台或多节点制品复制方案（由 `DECK-GATE-DEC-018` 覆盖）
  4. 安全撤销策略细节（由 `DECK-GATE-DEC-019` §4.4 覆盖）
  5. Voice chat 到 run session 的 UX（由 `DECK-GATE-DEC-020` 覆盖）

- 关键约束:
  1. `DECK-GATE-DEC-017` 仍为 `conditional_frozen`；非生产环境可显式 `legacy_unverified` 推进，但不得标 `production_ready`
  2. 生产制品必须同时满足摘要、签名和可恢复留存，缺一即不得进入 `production_ready`
  3. `artifact_digest = sha256:<hex>` 对实际分发字节计算，不对可变目录、分支或 `latest` 引用计算
  4. `deck_plugin_manifest_hash` 对 RFC 8785 规范化 JSON 计算 SHA-256
  5. 首选签名为可离线验证的 `sigstore-bundle/v1`，信任身份/密钥必须在管理员 allowlist 中
  6. 全部权威引用归零且无 legal hold 后，进入 90 天可恢复隔离期；期满才允许 purge
  7. 既有无签名制品迁移为 `legacy_unverified`，只允许开发/测试或历史只读，不得静默升级为 production-ready

- 补充说明:
  - 本批 Issue 拆解是 SUO-237 Issue 清单的增量补充，不替代既有 `DECK-001` ~ `DECK-020`。
  - 既有 `DECK-017` 为 `docs` 类型决策单，描述为"未定"；本清单将其转化为可实施的技术 Issue，因为 SUO-261 已确认设计方案。
  - 设计冻结不自动表示 production-ready 或运行 rollout 已放行；Stage 4 生产 Gate 继续阻断，直到本文档列出的证据全部落地。

---

## 2. Issue 总览表

| Issue ID | 标题 | 类型 | 优先级 | 标签 | 前置依赖 | 分发去向 |
|---|---|---|---|---|---|---|
| `DECK-SC-001` | 具名 Owner 任命与签署责任矩阵 | docs | P0 | `supply-chain`,`ownership`,`governance` | 无 | `@CEOOrchestrator` |
| `DECK-SC-002` | Trust-Policy 包：信任根、Identity 与算法矩阵 | backend | P0 | `supply-chain`,`trust-policy`,`signature`,`security` | `DECK-SC-001` | `@TaskDesignAgent` |
| `DECK-SC-003` | 发布端 SHA-256 与 RFC 8785 Manifest 签名验证 | backend | P0 | `supply-chain`,`digest`,`signature`,`manifest` | `DECK-SC-002` | `@TaskDesignAgent` |
| `DECK-SC-004` | Runtime 端摘要校验与 Load Receipt 绑定 | backend | P0 | `supply-chain`,`digest`,`runtime`,`verification` | `DECK-SC-003`, `DECK-002` | `@TaskDesignAgent` |
| `DECK-SC-005` | 制品引用状态机与生命周期留存策略 | backend | P0 | `supply-chain`,`retention`,`state-machine`,`lifecycle` | `DECK-SC-003` | `@TaskDesignAgent` |
| `DECK-SC-006` | 冷恢复可用性与运营承诺合同 | backend | P1 | `supply-chain`,`disaster-recovery`,`sla`,`operations` | `DECK-SC-005` | `@TaskDesignAgent` |
| `DECK-SC-007` | 篡改矩阵测试与可点击证据报告 | backend | P1 | `supply-chain`,`tamper-test`,`evidence`,`security` | `DECK-SC-003`, `DECK-SC-004` | `@TaskDesignAgent` |
| `DECK-SC-008` | 冷恢复演练与引用清理测试 | backend | P1 | `supply-chain`,`dr-test`,`cleanup`,`evidence` | `DECK-SC-006`, `DECK-SC-005` | `@TaskDesignAgent` |
| `DECK-SC-009` | 下游旧假设对齐与 `legacy_unverified` 路径标记 | shared | P1 | `supply-chain`,`legacy`,`migration`,`alignment` | `DECK-SC-003` | `@TaskDesignAgent` |

---

## 3. Issue 明细

### DECK-SC-001

- 标题: 具名 Owner 任命与签署责任矩阵
- 类型: docs
- 优先级: P0
- 标签: `supply-chain`,`ownership`,`governance`
- 描述:
  明确 `DECK-GATE-DEC-017` 下三个关键角色的具名任命、权限范围与签署责任。根据设计稿 §4.2.5，需要：安全 owner 批准信任根、签名算法与失败策略；marketplace/制品平台 owner 承诺签名包和冷恢复能力；runtime owner 批准双重摘要校验路径。输出具名 owner 名单、各自权限边界、签署流程与审批记录格式。

- 验收条件:
  - [ ] 安全 owner 已具名任命，权限覆盖信任根选择、签名算法 allowlist、失败策略（fail-closed vs fail-open）、密钥轮换周期
  - [ ] Marketplace/制品平台 owner 已具名任命，权限覆盖签名包生成、CAS 可用性、冷恢复能力、留存策略执行
  - [ ] Runtime owner 已具名任命，权限覆盖发布端验证路径、runtime 端校验路径、load receipt 绑定策略
  - [ ] 每个 owner 的签署责任以结构化文档记录，包含签署人 ID、签署时间、签署范围、否决权说明
  - [ ] 缺失任一 owner 时，Stage 4 生产 Gate 保持阻断，不得标记 `production_ready`

- 前置依赖: 无

- 关联路径:
  - `docs/design/deck/design_002_deck-plugin-decision-gates.md` §4.2.5
  - `docs/issue/ISSUES_deck-plugin-voice-ink-dream-integration.md` DECK-017

- 分发去向: `@CEOOrchestrator`

- 主责 Agent: `CEOOrchestrator`

- 协作 Agent: 无

- 设计决策引用:
  - `DECK-GATE-DEC-017`: 生产制品必须以 SHA-256 精确摘要、受信签名包和引用感知留存共同构成完整性合同

- 备注:
  - 这是所有后续 supply-chain Issue 的前置条件；owner 未任命时，技术实现可限域推进，但生产 Gate 保持阻断。
  - `[CLARIFICATION_NEEDED]` 若 CEO 需继续以组织最高决策权限临时覆盖缺位 owner，需显式记录覆盖范围与期限。

---

### DECK-SC-002

- 标题: Trust-Policy 包：信任根、Identity 与算法矩阵
- 类型: backend
- 优先级: P0
- 标签: `supply-chain`,`trust-policy`,`signature`,`security`
- 描述:
  实现 trust-policy 包，覆盖信任根/identity 管理、密钥轮换、撤销、过期、时间证明、允许算法矩阵、离线验证与 fail-closed 策略。基于设计稿 §4.2.1 第 3 点：发布者使用 DSSE 兼容签名包绑定 `artifact_digest + deck_plugin_manifest_hash + publisher_identity`；首选实现为可离线验证的 `sigstore-bundle/v1`，信任身份/密钥必须在管理员 allowlist 中。

- 验收条件:
  - [ ] 信任根配置模型完整，包含 `trust_domain`、`issuer`、`subject`、`key_fingerprint`、`not_before`、`not_after`、`revocation_url`、`algorithm_allowlist`
  - [ ] 允许算法矩阵显式列出：签名算法（如 ECDSA-P256-SHA256、Ed25519）、摘要算法（SHA-256 必选、SHA-384 可选）、密钥格式（x509、PKIX、TUF 元数据）
  - [ ] 密钥轮换策略：新密钥预热期、并行验证窗口、旧密钥退役期（至少 30 天重叠）
  - [ ] 密钥撤销：通过 `revocation_url` 发布 CRL 或 OCSP 响应；离线验证器必须缓存撤销列表并定期更新
  - [ ] 过期处理：密钥过期的签名包拒绝验证；允许配置 `clock_skew_tolerance`（默认 5 分钟）
  - [ ] 时间证明：支持 RFC 3161 时间戳或 Sigstore 的透明日志条目作为签名时间证明
  - [ ] 离线验证：验证器在无网络时必须能使用缓存的信任根和撤销列表完成验证；缓存过期后进入 fail-closed（拒绝验证）
  - [ ] fail-closed 策略：任何验证失败（信任根缺失、算法不在 allowlist、签名格式错误、撤销状态未知、时间证明缺失）均拒绝验证，不得降级为 warn-only
  - [ ] 管理员 allowlist 管理 API：添加/移除/查询信任身份，记录操作审计

- 前置依赖: `DECK-SC-001`

- 关联路径:
  - `docs/design/deck/design_002_deck-plugin-decision-gates.md` §4.2.1
  - 后端: trust-policy service / signature verifier

- 分发去向: `@TaskDesignAgent`

- 主责 Agent: `TaskDesignAgent`

- 协作 Agent: 无

- 设计决策引用:
  - `DECK-GATE-DEC-017`: SHA-256 精确摘要 + 受信 DSSE/Sigstore 签名包 + 引用感知留存

- 备注:
  - 与 `DECK-002`（Runtime Lock）紧密相关；trust-policy 是 lock 中签名验证字段的依赖。
  - 算法矩阵必须显式版本化（`trust_policy_revision`），不得隐式依赖代码版本。

---

### DECK-SC-003

- 标题: 发布端 SHA-256 与 RFC 8785 Manifest 签名验证
- 类型: backend
- 优先级: P0
- 标签: `supply-chain`,`digest`,`signature`,`manifest`
- 描述:
  实现发布端的制品摘要和 manifest 签名验证。基于设计稿 §4.2.1： marketplace 提供不可变打包制品；`artifact_digest = sha256:<hex>` 对实际分发字节计算；`deck_plugin_manifest_hash` 对 RFC 8785 规范化 JSON 计算 SHA-256；发布时验证签名、身份、摘要和来源策略。

- 验收条件:
  - [ ] `artifact_digest` 计算：对实际分发字节（gzip/tar/zip 包的字节流）计算 SHA-256，输出 `sha256:<64-lowercase-hex>`
  - [ ] `deck_plugin_manifest_hash` 计算：对 RFC 8785 规范化后的 manifest JSON 计算 SHA-256；规范化规则包括：键按 Unicode 码点排序、无空白、无尾随零、数字用最短表示
  - [ ] 签名验证流程：提取 signature bundle → 验证签名格式 → 验证信任根 → 验证签名覆盖 `artifact_digest + manifest_hash + publisher_identity` → 验证时间证明 → 验证密钥未过期/未撤销
  - [ ] 发布端验证结果持久化：记录 `verification_status`（`verified`/`failed`/`expired`/`revoked`）、`verified_at`、`verifier_version`、`trust_policy_revision`
  - [ ] 验证失败时返回结构化错误：`ARTIFACT_SIGNATURE_INVALID`、`ARTIFACT_DIGEST_MISMATCH`、`ARTIFACT_TRUST_ROOT_UNKNOWN`、`ARTIFACT_VERIFICATION_EXPIRED`
  - [ ] 验证结果与 release 原子关联；同一 release 的验证结果不可变
  - [ ] 单元测试覆盖：合法签名验证、篡改字节后摘要不匹配、篡改 manifest 后 hash 不匹配、过期密钥、撤销密钥、未知信任根、离线验证

- 前置依赖: `DECK-SC-002`

- 关联路径:
  - `docs/design/deck/design_002_deck-plugin-decision-gates.md` §4.2.1, §4.2.3
  - `docs/issue/ISSUES_deck-plugin-voice-ink-dream-integration.md` DECK-002
  - 后端: release service / signature verifier / manifest normalizer

- 分发去向: `@TaskDesignAgent`

- 主责 Agent: `TaskDesignAgent`

- 协作 Agent: 无

- 设计决策引用:
  - `DECK-GATE-DEC-017`: artifact_digest 对实际分发字节计算；manifest_hash 对 RFC 8785 规范化 JSON 计算

- 备注:
  - RFC 8785 规范化必须引用标准实现或经过验证的库；不得自行实现 JSON 规范化。
  - 与既有 `DECK-002`（Runtime Lock）的关系：本 Issue 提供 lock 中 `artifact_digest` 和 `manifest_hash` 的验证能力。

---

### DECK-SC-004

- 标题: Runtime 端摘要校验与 Load Receipt 绑定
- 类型: backend
- 优先级: P0
- 标签: `supply-chain`,`digest`,`runtime`,`verification`
- 描述:
  实现 runtime 端的制品摘要二次校验，并将校验结果绑定到 `RuntimeLoadReceipt`。基于设计稿 §4.2.1 第 4 点：运行时物化后再次验证摘要；运行阶段只消费已冻结的验证结果和摘要，不重新信任 marketplace 标签。

- 验收条件:
  - [ ] Runtime 物化后，对下载的制品字节重新计算 SHA-256，与 lock 中的 `artifact_digest` 比对
  - [ ] 摘要不匹配时拒绝加载，返回 `ARTIFACT_DIGEST_MISMATCH`，记录审计事件
  - [ ] `RuntimeLoadReceipt` 增加字段：`runtime_verified_digest`（运行时计算的摘要）、`runtime_verification_status`、`runtime_verified_at`
  - [ ] Load receipt 中的 `runtime_verified_digest` 必须与 lock 中的 `artifact_digest` 一致，才允许进入 `loaded` 状态
  - [ ] 运行阶段不重新查询 marketplace 验证状态；只消费发布端已冻结的 `verification_status` 和摘要
  - [ ] 节点 cache 中的制品也必须通过摘要校验；cache 命中时比对存储的摘要与 lock 中的摘要
  - [ ] 单元测试覆盖：物化后摘要匹配、物化后摘要不匹配、cache 命中摘要匹配、cache 命中摘要不匹配

- 前置依赖: `DECK-SC-003`, `DECK-002`

- 关联路径:
  - `docs/design/deck/design_002_deck-plugin-decision-gates.md` §4.2.1, §4.2.3
  - `docs/issue/ISSUES_deck-plugin-voice-ink-dream-integration.md` DECK-002, DECK-008
  - 后端: runtime materialization service / load receipt generator

- 分发去向: `@TaskDesignAgent`

- 主责 Agent: `TaskDesignAgent`

- 协作 Agent: 无

- 设计决策引用:
  - `DECK-GATE-DEC-017`: 发布时验证签名、身份、摘要和来源策略；运行时物化后再次验证摘要
  - `DECK-GATE-DEC-016`: ClaudeAgent runtime control 负责 materialization operation 和节点 cache 状态

- 备注:
  - 这是"双路径校验"的后半段；发布端验证（DECK-SC-003）与 runtime 端验证（DECK-SC-004）共同构成完整校验链。
  - 与既有 `DECK-008`（Reconcile 与 Load Receipt）的关系：本 Issue 在 load receipt 中增加摘要校验字段。

---

### DECK-SC-005

- 标题: 制品引用状态机与生命周期留存策略
- 类型: backend
- 优先级: P0
- 标签: `supply-chain`,`retention`,`state-machine`,`lifecycle`
- 描述:
  实现制品的引用感知留存状态机。基于设计稿 §4.2.1 第 5-6 点：只要 published/deprecated/revoked release、runtime lock 或 Workflow Run 仍引用制品，制品必须保留或可从冷存储恢复；全部权威引用归零且无 legal hold 后，进入 90 天可恢复隔离期；期满才允许 purge；revoked 制品进入隔离存储并禁止新执行。

- 验收条件:
  - [ ] 引用状态机完整：`pinned`（有活跃引用）→ `recoverable`（零引用，进入 90 天隔离期）→ `purge_eligible`（隔离期满）→ `purged`（已物理删除）
  - [ ] 制品隔离状态：`quarantined`（revoked 制品，禁止新加载，但保留字节用于取证）
  - [ ] 引用计数器：按 `release_ref_count`、`lock_ref_count`、`run_ref_count`、`legal_hold_count` 分别追踪
  - [ ] 总引用计数 = 上述四项之和；总引用 > 0 时制品状态为 `pinned`
  - [ ] 总引用归零且无 legal hold 时，自动进入 `recoverable` 状态，启动 90 天隔离倒计时
  - [ ] 隔离期内制品可从热存储迁移到冷存储，但必须保留恢复能力（相同 digest 可恢复）
  - [ ] 隔离期满后，制品标记为 `purge_eligible`；物理删除前需二次确认无新引用产生
  - [ ] 物理删除后标记为 `purged`，但保留审计记录（digest、删除时间、删除原因、操作人）
  - [ ] `restore_source_ref` 字段：指向冷存储或备份中的制品位置，用于恢复验证
  - [ ] 管理 API：查询制品留存状态、手动触发 legal hold、查询引用详情
  - [ ] 单元测试覆盖：引用计数增减、隔离期计时、legal hold 阻止 purge、恢复验证

- 前置依赖: `DECK-SC-003`

- 关联路径:
  - `docs/design/deck/design_002_deck-plugin-decision-gates.md` §4.2.1, §4.2.3
  - 后端: retention service / reference tracker / lifecycle manager

- 分发去向: `@TaskDesignAgent`

- 主责 Agent: `TaskDesignAgent`

- 协作 Agent: 无

- 设计决策引用:
  - `DECK-GATE-DEC-017`: 留存以引用为准；90 天隔离期；revoked 制品隔离不删除

- 备注:
  - 与既有 `DECK-002`（Runtime Lock）的关系：lock 增加 `retention_state` 和 `restore_source_ref` 字段。
  - 与既有 `DECK-003`（Installation 生命周期）的关系：installation 状态变化可能影响引用计数。
  - 90 天隔离期参数可配置，但生产环境不得小于 90 天。

---

### DECK-SC-006

- 标题: 冷恢复可用性与运营承诺合同
- 类型: backend
- 优先级: P1
- 标签: `supply-chain`,`disaster-recovery`,`sla`,`operations`
- 描述:
  建立制品冷恢复的可用性运营承诺。基于设计稿 §4.2.1 第 5 点：制品必须保留或可从冷存储恢复为相同摘要。输出可度量的恢复目标、恢复流程、恢复验证机制和运营 SLA。

- 验收条件:
  - [ ] 恢复目标定义：RTO（恢复时间目标，如 4 小时内从冷存储恢复到可下载）、RPO（恢复点目标，如零数据丢失，因为制品不可变）
  - [ ] 冷存储位置：明确冷存储的物理/逻辑位置（如对象存储归档层、异地备份）
  - [ ] 恢复流程：从 `restore_source_ref` 定位冷存储制品 → 验证 digest 匹配 → 恢复到热存储/CAS → 更新 `retention_state` 为 `pinned` 或 `recoverable`
  - [ ] 恢复验证：恢复后的制品必须通过与原制品相同的 SHA-256 摘要校验；摘要不匹配时标记恢复失败并告警
  - [ ] 运营承诺文档：marketplace/制品平台 owner 签署的恢复能力承诺，包含 RTO/RPO、备份频率、恢复演练周期
  - [ ] 恢复失败处理：连续恢复失败时升级 incident，通知 owner，禁止依赖该制品的新运行
  - [ ] 可度量指标：恢复请求次数、恢复成功率、平均恢复时间、冷存储可用性
  - [ ] 单元测试覆盖：正常恢复流程、恢复后摘要不匹配、冷存储不可用、连续失败升级

- 前置依赖: `DECK-SC-005`

- 关联路径:
  - `docs/design/deck/design_002_deck-plugin-decision-gates.md` §4.2.1, §4.2.5
  - 后端: disaster recovery service / cold storage adapter

- 分发去向: `@TaskDesignAgent`

- 主责 Agent: `TaskDesignAgent`

- 协作 Agent: 无

- 设计决策引用:
  - `DECK-GATE-DEC-017`: 引用固定 + 冷恢复足以维持合同

- 备注:
  - 本 Issue 是运营承诺，需要 marketplace/制品平台 owner 的签署。
  - `[CLARIFICATION_NEEDED]` 若冷存储由第三方提供，需明确第三方的 SLA 合同和违约责任。

---

### DECK-SC-007

- 标题: 篡改矩阵测试与可点击证据报告
- 类型: backend
- 优先级: P1
- 标签: `supply-chain`,`tamper-test`,`evidence`,`security`
- 描述:
  建立制品篡改检测矩阵测试，生成可点击的证据报告。基于设计稿 §5.2 Stage 4 / `DECK-017` 验收标准：签名/digest 篡改测试必拒绝。覆盖发布端和 runtime 端的各类篡改场景。

- 验收条件:
  - [ ] 篡改矩阵覆盖以下场景：
    - [ ] 篡改制品字节（修改包内任意文件内容）
    - [ ] 篡改 manifest JSON（修改字段值、增删字段）
    - [ ] 替换签名包（使用不同密钥签名）
    - [ ] 重放旧签名（将旧 release 的签名复制到新 release）
    - [ ] 截断制品（删除包尾部字节）
    - [ ] 中间人替换（在传输过程中替换制品）
    - [ ] 篡改摘要字段（在 lock 中伪造 artifact_digest）
    - [ ] 篡改 manifest_hash 字段（在 lock 中伪造 manifest hash）
  - [ ] 每种篡改场景必须被检测并拒绝，不得进入 `verified` 或 `loaded` 状态
  - [ ] 可点击证据报告：每个测试 case 包含 `test_case_id`、`run_id`（CI run）、`commit_sha`、篡改类型、预期结果、实际结果、日志摘要链接、通过/失败状态
  - [ ] 报告格式：Markdown 或 HTML，包含可点击链接到具体测试日志和代码提交
  - [ ] 报告由独立 reviewer 审阅并签署；签署记录包含 reviewer ID、签署时间、审阅范围
  - [ ] 测试集成到 CI：每次相关代码变更自动运行篡改矩阵测试
  - [ ] 单元测试覆盖：上述每种篡改场景的检测逻辑

- 前置依赖: `DECK-SC-003`, `DECK-SC-004`

- 关联路径:
  - `docs/design/deck/design_002_deck-plugin-decision-gates.md` §5.2
  - 后端: security test suite / tamper detection framework

- 分发去向: `@TaskDesignAgent`

- 主责 Agent: `TaskDesignAgent`

- 协作 Agent: 无

- 设计决策引用:
  - `DECK-GATE-DEC-017`: 篡改必拒绝

- 备注:
  - 本 Issue 是 Stage 4 生产 Gate 的关键证据之一；报告缺失或 reviewer 未签署时，Gate 保持阻断。
  - 与 `DECK-GATE-DEC-019` §4.4.9 的证据包格式对齐：使用 `evidence_pack_id`、`test_run_id`、`manifest_sha256`。

---

### DECK-SC-008

- 标题: 冷恢复演练与引用清理测试
- 类型: backend
- 优先级: P1
- 标签: `supply-chain`,`dr-test`,`cleanup`,`evidence`
- 描述:
  建立冷恢复演练和引用清理测试，生成可点击证据报告。基于设计稿 §5.2 Stage 4 / `DECK-017` 验收标准：冷恢复得到同 digest；有引用时无法 purge。覆盖恢复流程和清理流程的端到端验证。

- 验收条件:
  - [ ] 冷恢复演练：
    - [ ] 定期（至少每季度一次）从冷存储恢复随机选择的制品
    - [ ] 恢复后的 digest 必须与原制品一致
    - [ ] 恢复失败的制品必须触发告警并阻止依赖它的新运行
    - [ ] 演练记录包含：演练时间、选择策略（随机/指定）、恢复制品 ID、恢复耗时、digest 比对结果、通过/失败状态
  - [ ] 引用清理测试：
    - [ ] 模拟制品从 `pinned` → `recoverable` → `purge_eligible` 的完整生命周期
    - [ ] 验证有引用时无法 purge（尝试 purge 有引用的制品必须被拒绝）
    - [ ] 验证 legal hold 阻止 purge（有 legal hold 的制品即使零引用也不得 purge）
    - [ ] 验证 90 天隔离期未满时不得 purge
    - [ ] 验证 purge 后审计记录保留（digest、删除时间、操作人）
  - [ ] 可点击证据报告：每个演练和测试 case 包含 `test_case_id`、`run_id`、`commit_sha`、场景描述、预期结果、实际结果、日志摘要链接
  - [ ] 报告由独立 reviewer 审阅并签署
  - [ ] 测试集成到 CI：引用清理逻辑变更时自动运行清理测试

- 前置依赖: `DECK-SC-006`, `DECK-SC-005`

- 关联路径:
  - `docs/design/deck/design_002_deck-plugin-decision-gates.md` §5.2
  - 后端: disaster recovery test suite / cleanup test framework

- 分发去向: `@TaskDesignAgent`

- 主责 Agent: `TaskDesignAgent`

- 协作 Agent: 无

- 设计决策引用:
  - `DECK-GATE-DEC-017`: 冷恢复得到同 digest；有引用时无法 purge

- 备注:
  - 本 Issue 与 `DECK-SC-007` 共同构成 Stage 4 生产 Gate 的测试证据。
  - 冷恢复演练可能需要专门的测试环境或沙箱；不得在 production 环境直接演练。

---

### DECK-SC-009

- 标题: 下游旧假设对齐与 `legacy_unverified` 路径标记
- 类型: shared
- 优先级: P1
- 标签: `supply-chain`,`legacy`,`migration`,`alignment`
- 描述:
  对齐下游仍以"sha256 占位 / 决策未冻结"描述的旧假设。根据设计稿 §8 增量变更说明和 §4.2.4 兼容策略：既有无签名制品迁移为 `legacy_unverified`，只允许开发/测试或历史只读，不得静默升级为 production-ready。识别所有下游文档、代码和配置中的旧假设，显式标记为 `legacy_unverified` 或更新为与 `DECK-GATE-DEC-017` 一致。

- 验收条件:
  - [ ] 扫描 `docs/task/`、`docs/stage/`、`docs/exec/`、代码仓库中的旧假设：
    - [ ] 任何使用 `"latest"` 或可变标签引用制品的位置
    - [ ] 任何缺少 `artifact_digest` 的 release/lock 定义
    - [ ] 任何使用 "sha256 占位" 或 "TODO: 实现摘要" 的注释或文档
    - [ ] 任何将无签名制品标记为 production-ready 的逻辑
  - [ ] 对每个发现的旧假设，标记为以下之一：
    - `legacy_unverified`：允许开发/测试/历史只读路径，明确禁止 production-ready
    - `updated`：已更新为与 `DECK-GATE-DEC-017` 一致（需引用具体 Issue/提交）
    - `deprecated`：已废弃，需迁移路径
  - [ ] 更新既有 `DECK-017`（SUO-237 Issue 清单中的决策单）的备注，说明已由 `DECK-SC-001` ~ `DECK-SC-008` 替代
  - [ ] 前端管理 UI：对 `legacy_unverified` 制品显示明确警告标签，禁止选择用于生产运行
  - [ ] 后端 API：对 `legacy_unverified` 制品的 production-ready 请求返回 `ARTIFACT_VERIFICATION_REQUIRED`
  - [ ] 单元测试覆盖：legacy 制品的加载限制、production-ready 拒绝、警告标签渲染

- 前置依赖: `DECK-SC-003`

- 关联路径:
  - `docs/design/deck/design_002_deck-plugin-decision-gates.md` §4.2.4, §8
  - `docs/issue/ISSUES_deck-plugin-voice-ink-dream-integration.md` DECK-017
  - 全仓库：代码、文档、配置

- 分发去向: `@TaskDesignAgent`

- 主责 Agent: `TaskDesignAgent`

- 协作 Agent: `TaskDesignAgent`

- 设计决策引用:
  - `DECK-GATE-DEC-017`: 既有无签名制品迁移为 `legacy_unverified`

- 备注:
  - 前端职责：legacy 警告标签、生产运行阻止提示、迁移指引
  - 后端职责：legacy 制品状态标记、production-ready 校验、API 错误响应
  - 这是一个跨域对齐任务，需要扫描全仓库；扫描结果应记录在本 Issue 评论区。

---

## 4. 共享任务与依赖说明

- `DECK-SC-001` 是所有后续 supply-chain Issue 的前置条件；owner 未任命时，技术实现可限域推进，但生产 Gate 保持阻断。
- `DECK-SC-002` 依赖 `DECK-SC-001` 的 owner 任命；trust-policy 的信任根和算法矩阵需要安全 owner 批准。
- `DECK-SC-003` 依赖 `DECK-SC-002` 的 trust-policy；发布端签名验证需要信任根和算法矩阵。
- `DECK-SC-004` 依赖 `DECK-SC-003` 的发布端验证和既有 `DECK-002` 的 runtime lock；runtime 端校验是双路径校验的后半段。
- `DECK-SC-005` 依赖 `DECK-SC-003` 的验证结果；引用状态机需要已验证的制品摘要作为追踪目标。
- `DECK-SC-006` 依赖 `DECK-SC-005` 的留存策略；冷恢复需要引用状态机确定哪些制品需要恢复能力。
- `DECK-SC-007` 依赖 `DECK-SC-003` 和 `DECK-SC-004` 的校验能力；篡改测试需要发布端和 runtime 端校验逻辑就位。
- `DECK-SC-008` 依赖 `DECK-SC-006` 的恢复能力和 `DECK-SC-005` 的清理逻辑；演练需要完整的恢复和清理流程。
- `DECK-SC-009` 是 shared 类型 Issue，由 `TaskDesignAgent` 统一规划，并在 task 文档中显式拆分各 domain 的执行边界。
- 若后续发现某个 Issue 的实现范围超出当前设计稿，必须回到 Issue 评论区记录澄清，不得直接下沉到 task 阶段。
- 若某个 Issue 需要新增设计决策，必须标记 `[CLARIFICATION_NEEDED]`，由 `CEOOrchestrator` 判断是否回退到 `DesignArchitect`。

---

## 5. 分发去向说明

- `CEOOrchestrator`：
  - `DECK-SC-001` 需要具名 owner 任命和签署责任矩阵，属于治理决策，分发给 `CEOOrchestrator`。

- `TaskDesignAgent`：
  - 统一领取 `DECK-SC-002` ~ `DECK-SC-009`（backend / shared 类型 Issue）。
  - 根据 `type`、标签、关联路径与验收条件分别规划 trust-policy 实现、签名验证、摘要校验、留存状态机、冷恢复、测试矩阵和旧假设对齐。
  - domain 必须写入 Issue/task 字段；不得再通过拆分 Agent 身份表达前后端边界。

- `Shared Issue` 处理规则：
  - `DECK-SC-009` 是 shared 类型 Issue，必须明确主责 Agent。
  - 另一个 Agent 作为协作方。
  - 不允许 shared Issue 无主责。

---

## 6. 推荐推进顺序

### 第一阶段：治理与信任基础（P0 前置）

```text
DECK-SC-001 (Owner 任命)
  ↓
DECK-SC-002 (Trust-Policy 包)
```

### 第二阶段：双路径校验（P0 核心）

```text
DECK-SC-003 (发布端验证)
  ↓
DECK-SC-004 (Runtime 端校验) ──→ 依赖既有 DECK-002
  ↓
DECK-SC-005 (引用状态机)
```

### 第三阶段：运营承诺与测试证据（P1）

```text
DECK-SC-006 (冷恢复承诺) ──→ 依赖 DECK-SC-005
DECK-SC-007 (篡改矩阵测试) ──→ 依赖 DECK-SC-003 + DECK-SC-004
DECK-SC-008 (恢复演练与清理测试) ──→ 依赖 DECK-SC-006 + DECK-SC-005
```

### 第四阶段：下游对齐（P1）

```text
DECK-SC-009 (旧假设对齐) ──→ 依赖 DECK-SC-003，可与第三阶段并行
```

### 推进原则

1. `DECK-SC-001` 是治理前置；owner 未任命时，技术 Issue 可限域推进，但生产 Gate 保持阻断。
2. `DECK-SC-002` ~ `DECK-SC-005` 是 P0 核心链路，必须按顺序推进。
3. `DECK-SC-006` ~ `DECK-SC-008` 是 P1 证据和运营承诺，可在核心链路稳定后并行推进。
4. `DECK-SC-009` 可与第三阶段并行，但需要扫描全仓库，可能发现额外阻塞。
5. Stage 4 生产 Gate 在 `DECK-SC-001` ~ `DECK-SC-008` 全部完成、证据报告齐全、独立 reviewer 签署后，方可申请 `approve`。

---

## 7. 阻塞与澄清记录

### [BLOCKED] DECK-SC-001

- 阻塞原因：`DECK-GATE-DEC-017` 仍为 `conditional_frozen`，需要安全 owner、marketplace/制品平台 owner、runtime owner 的具名任命和签署
- 影响范围：所有后续 supply-chain Issue 的生产就绪状态；技术实现可限域推进
- 当前责任 Agent：`CEOOrchestrator`
- 需要唤醒的 Agent：`CEOOrchestrator`（owner 任命）
- 建议处理方式：CEO 可继续以组织最高决策权限临时覆盖缺位 owner，但需显式记录覆盖范围与期限；长期需完成具名任命
- 是否需要回退到 design：否；设计方案已冻结，阻塞在治理层面

### [CLARIFICATION_NEEDED] DECK-SC-006

- 歧义点：冷存储的具体实现（对象存储归档层、异地备份、第三方服务）未在设计稿中指定
- 可能解释 A：由 marketplace/制品平台 owner 选择具体冷存储方案，只要满足 RTO/RPO 合同
- 可能解释 B：需要统一指定冷存储方案，以确保跨环境一致性
- 默认采用解释 A：owner 选择方案，但需在运营承诺中披露具体实现和 SLA
- 需要确认方：`CEOOrchestrator` 或 marketplace/制品平台 owner
- 是否阻塞 task 阶段：否；可在 task 阶段由 owner 确认具体方案

### [CLARIFICATION_NEEDED] DECK-SC-009

- 歧义点：下游旧假设的扫描范围是否包含已关闭的 Issue/Stage/Exec 产物
- 可能解释 A：只扫描当前开放的文档和代码
- 可能解释 B：扫描全部历史产物，包括已关闭的，以建立完整迁移记录
- 默认采用解释 A：扫描当前开放文档和代码；历史产物只记录引用，不强制更新
- 需要确认方：`CEOOrchestrator`
- 是否阻塞 task 阶段：否

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

## 9. 与既有 Issue 清单的差异说明

本文档与 `docs/issue/ISSUES_deck-plugin-voice-ink-dream-integration.md`（SUO-237）的差异：

| 既有 Issue | 既有状态 | 本文档处理 |
|---|---|---|
| `DECK-017` | `docs` 类型决策单，描述为"未定"，分发 `@CEOOrchestrator` | 设计方案已由 SUO-261 确认，转化为 9 条可实施 Issue；`DECK-SC-001` 仍分发给 `@CEOOrchestrator` 处理 owner 任命，其余分发给 `@TaskDesignAgent` |
| `DECK-002` | `backend` 类型，runtime lock | 本文档 `DECK-SC-004` 依赖既有 `DECK-002`，在 lock 中增加摘要校验字段 |
| `DECK-008` | `backend` 类型，reconcile/load receipt | 本文档 `DECK-SC-004` 在 load receipt 中增加 `runtime_verified_digest` 字段 |
| `DECK-015` | `backend` 类型，安全撤销 | 不涉及；由 `DECK-GATE-DEC-019` 覆盖 |

- 既有 `DECK-017` 的"默认假设"（无不可变 digest 不得 production-ready）已升级为具体技术方案，不再标记为"未定"。
- 本文档新增 9 条 Issue，逐项映射 SUO-266 要求的 7 项缺口。
- 本文档不修改既有 `DECK-001` ~ `DECK-020` 的内容；只增量补充 supply-chain 相关的 Issue。

---

## 10. 校验清单

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
- [x] 存在 `[CLARIFICATION_NEEDED]`（DECK-SC-006, DECK-SC-009）
- [x] 存在 `[BLOCKED]`（DECK-SC-001）
- [x] 已说明与既有 Issue 清单的差异
