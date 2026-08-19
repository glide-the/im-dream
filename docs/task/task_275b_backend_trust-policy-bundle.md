# task_275b_backend_trust-policy-bundle

> Task ID: `task_275b`
> Source Issue: `DECK-SC-002`
> Paperclip Issue: [SUO-275](/SUO/issues/SUO-275)
> Domain / Priority: `backend` / `P0`

## 1. 任务标题

Trust-Policy 包：信任根、Publisher Identity 与算法生命周期

## 2. 关联 Issue

| 关联 | 内容 |
|---|---|
| 来源条目 | `DECK-SC-002` |
| 来源编排 | [SUO-258](/SUO/issues/SUO-258) |
| Task-stage Issue | [SUO-275](/SUO/issues/SUO-275) |
| Design | `docs/design/deck/design_002_deck-plugin-decision-gates.md` §4.2.1、§4.2.5 |
| Issue 清单 | `docs/issue/ISSUES_deck-plugin-stage4-supply-chain.md` |
| Domain / Priority / 标签 | `backend` / P0 / `supply-chain`, `trust-policy`, `signature`, `security` |

## 3. 任务目标

实现版本化 trust-policy 包和离线 verifier 基础合同，覆盖管理员允许的 publisher identity、根/中间证书或密钥来源、DSSE/Sigstore 算法矩阵、轮换、撤销、过期、时间证明与离线缓存生命周期。任何未知、降级、失联或过期路径必须 fail closed 并产生结构化错误与审计事件。

本 task 不计算发布制品 digest、不修改 release 状态、不实现 runtime materialization，也不代表安全 owner 已批准 production rollout。

## 4. 实现步骤

1. 定义 `TrustPolicyRevision`、`TrustedPublisherIdentity`、`TrustRoot`、`AlgorithmRule`、`RevocationSnapshot` 与 `VerificationDecision` 严格模型。
2. 定义版本化算法矩阵：
   - signature：至少明确 `ECDSA-P256-SHA256`、`Ed25519` 的 allow/deny；
   - digest：`SHA-256` 必选，其他算法只有显式允许才可消费；
   - key/metadata：x509/PKIX/TUF 的来源、链验证与允许组合；
   - bundle：DSSE payload type 与 `sigstore-bundle/v1` 版本。
3. 实现管理员 allowlist CRUD；写操作使用乐观 revision/事务，记录 actor、request ID、before/after hash 和审计事件。
4. 实现根与 identity 生命周期：`not_before/not_after`、至少 30 天双验证轮换窗口、撤销来源、吊销快照版本和最大缓存有效期。
5. 实现时间证明校验：RFC 3161 或 Sigstore transparency entry；证明缺失、签署晚于撤销/过期或时钟超出默认 5 分钟容差均拒绝。
6. 实现离线 verifier：
   - 只读取签名时被冻结的 policy revision 与未过期缓存；
   - 缓存撤销快照过期、根链不全、identity 未命中或状态未知时返回 deny；
   - 网络恢复不得把先前 deny 静默改为 warn-only。
7. 对所有拒绝分支映射稳定错误码和 append-only 审计摘要；日志只保存 signer 摘要和 bundle ref，不内联完整签名包。
8. 增加单元测试与数据库幂等初始化，覆盖并发 policy 更新、轮换交叠、撤销、过期、离线缓存边界与算法降级。

## 5. 涉及文件路径

| 路径 | 动作 | 最小变更 |
|---|---|---|
| `backend/models/deck_plugin_trust.py` | 新建 | trust-policy、identity、root、algorithm、decision 模型 |
| `backend/services/deck_plugin/trust_policy_service.py` | 新建 | revision、allowlist、轮换与撤销生命周期 |
| `backend/services/deck_plugin/signature_verifier.py` | 新建 | DSSE/Sigstore bundle 与离线 fail-closed verifier |
| `backend/routers/deck_plugin_trust.py` | 新建 | 管理员 allowlist 查询/变更 API |
| `backend/database.py` | 修改 | 增量新增 trust-policy/identity/root/revocation/audit 表 |
| `backend/server.py` | 修改 | 仅注册 trust-policy router |
| `backend/tests/test_deck_plugin_trust_policy.py` | 新建 | 本 task 单元与 API 测试 |
| `backend/pyproject.toml`、`backend/requirements.txt` | 条件修改 | 仅在 security owner 批准后加入并锁定一个经过维护的 DSSE/Sigstore 依赖；不得手写密码学 |

## 6. 输入 / 输出说明

### 输入

```jsonc
{
  "trust_policy_revision": "tp_...",
  "publisher_identity": {"issuer": "...", "subject": "..."},
  "signature_scheme": "sigstore-bundle/v1",
  "signature_algorithm": "ECDSA-P256-SHA256",
  "digest_algorithm": "SHA-256",
  "verification_time": "...",
  "offline": true
}
```

### 输出

- `VerificationDecision {decision: allow|deny, trust_policy_revision, signer_fingerprint, reason_code, revocation_snapshot_id, verified_time_proof}`；
- 管理 API 返回脱敏 trust root/identity 列表和 revision，不返回私钥；
- 拒绝码至少包括 `ARTIFACT_TRUST_ROOT_UNKNOWN`、`ARTIFACT_PUBLISHER_UNTRUSTED`、`ARTIFACT_ALGORITHM_UNSUPPORTED`、`ARTIFACT_REVOCATION_UNKNOWN`、`ARTIFACT_TIME_PROOF_INVALID`、`ARTIFACT_OFFLINE_POLICY_EXPIRED`。

## 7. 依赖项、可并行性与冻结点

- 直接依赖：`task_275a` 的 security owner 与签署范围。
- `task_275a` 未完成时可实现模型和 deny-by-default 测试，但 active production policy 不得启用。
- 下游：`task_275c`、`task_275g`。
- Freeze point：security owner 对 policy revision、算法矩阵、缓存 TTL、clock skew 和 fail-closed 决策签署。
- 不允许与 `task_275c` 并行修改 `signature_verifier.py`；Stage 应串行合并 `275b → 275c`。

## 8. 测试策略

最小命令：`python -m unittest backend.tests.test_deck_plugin_trust_policy`

| 场景 | 通过标准 | 证据 |
|---|---|---|
| allowlisted identity + 有效链/算法/时间证明 | allow，返回准确 policy revision | 测试 ID + decision |
| 未知 root/identity/algorithm | deny，不降级 | 错误码 + 审计 ID |
| 撤销状态未知或缓存过期 | 离线/在线均 deny | snapshot/TTL 断言 |
| 轮换窗口 | 新旧根仅在签署窗口并行有效 | 边界时间测试 |
| 过期/未来签名/clock skew | 超界拒绝 | 固定时钟测试 |
| 并发 allowlist 更新 | 一个 revision 成功，冲突显式返回 | DB/API 断言 |

另执行 `git diff --check --` 指定 §5 文件，确认无私钥、完整 bundle 或越界日志写入。

## 9. 完成标志

- [ ] 模型包含 `trust_domain`、issuer、subject、fingerprint、有效期、撤销源和 algorithm allowlist。
- [ ] 算法/格式矩阵显式版本化并由 policy revision 冻结。
- [ ] 新旧密钥有至少 30 天可配置重叠，退役后拒绝新验证。
- [ ] CRL/OCSP 或等价撤销快照可审计；离线缓存过期 fail closed。
- [ ] RFC 3161 或 Sigstore 时间证明被验证。
- [ ] 管理员 allowlist API 有授权、乐观 revision 与审计。
- [ ] 所有未知/降级/失联路径均拒绝且结构化。
- [ ] 精确测试命令通过并留下报告。

## 10. 风险提示与回滚

| 风险 | 处理 / 回滚 |
|---|---|
| 自行实现密码学/JSON 解析 | 禁止；使用批准依赖与固定测试向量 |
| 撤销 provider 失联 | 保留最后有效快照至 TTL；过期后 fail closed |
| 新 policy 错配导致全量拒绝 | 原子激活；可回退到仍有效、已签署的旧 revision |
| 回退弱化算法或延长过期缓存 | 禁止；只能暂停新发布并保持拒绝 |

回滚不得删除历史 policy、撤销快照或审计，不得恢复已撤销 identity。

## 11. 允许 / 禁止修改范围

- 允许：§5 精确闭集；条件依赖变更必须有 security owner 审批证据。
- 禁止：release digest/状态、runtime materialization、前端、Stage/Exec 文档、部署配置、证书私钥与未列出的源码。
- `docs/design/`、`docs/issue/`、`docs/task/`、`docs/stage/` 均禁止由执行者改写。

## 12. StagePlanner / Execute Readiness

| 字段 | 值 |
|---|---|
| 前序 | `task_275a` |
| 可并行 | 模型/fixtures 可与 owner 资料收集限域并行；active policy 不可 |
| Freeze point | security owner 签署的 `trust_policy_revision` |
| Execute readiness | 选定验证库/测试向量、数据库 migration 边界、管理员鉴权方式明确 |
| 证据格式 | 精确测试报告、policy revision/hash、逐项 decision/error/audit ID 与 security owner 签署链接 |
| Clarification owner/action | `CEOOrchestrator` 路由 security owner 选定验证库、信任根、算法矩阵、撤销源、缓存 TTL 与 clock skew 并签署 revision |
| 未满足 Gate | 发布端、runtime、留存、真实 evidence pack 与独立复审 |

本 task 完成不等于 Stage 4 production Gate approve。
