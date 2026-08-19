# task_deck_sc_002_backend_trust-policy

## 1. 任务标题

Trust-Policy 包：信任根、Publisher Identity、算法与离线 Fail-Closed

## 2. 唯一映射与 Domain

| 字段 | 值 |
|---|---|
| Task ID | `TASK-DECK-SC-002` |
| 来源 Issue | `DECK-SC-002` |
| Paperclip TaskDesign Issue | [SUO-275](/SUO/issues/SUO-275) |
| Canonical design | `docs/design/deck/design_002_deck-plugin-decision-gates.md` §4.2.1-§4.2.5 |
| Domain | `backend` |
| 优先级 | P0 |
| 下游 Stage 映射键 | `stage4.supply_chain.DECK-SC-002` |

## 3. 任务目标与非目标

实现版本化 trust-policy 与离线 verifier 基础能力，统一管理 trust root/publisher identity、签名与 digest 算法 allowlist、轮换、撤销、过期、时间证明、离线缓存 freshness 和审计。所有不确定状态必须 fail closed。

非目标：不计算/持久化 release digest（由 `TASK-DECK-SC-003` 完成）；不执行 runtime 二次校验；不选择未获安全 owner 批准的算法、根或云供应商；不把开发例外升级为生产允许。

## 4. 实现步骤

1. 定义版本化 `TrustPolicy`、`TrustedPublisherIdentity`、`TrustRoot`、`AlgorithmRule`、`RevocationSnapshot` 和 `VerificationContext`，包含 Issue 要求的全部字段。
2. 实现策略加载、schema/签名校验、revision 原子切换和旧 revision 可审计读取；无有效策略时拒绝生产验证。
3. 实现管理员 allowlist 的添加、移除、查询和 append-only 审计，所有写操作要求明确 actor/scope/reason。
4. 接入经安全 owner 批准的标准 DSSE/Sigstore、x509/PKIX/TUF、RFC 3161/透明日志验证能力；依赖库选择和版本需可审计，禁止自造密码学或 JSON canonicalization。
5. 实现 key rotation 窗口（至少 30 天重叠）、`not_before/not_after`、默认 5 分钟 `clock_skew_tolerance`、撤销列表缓存和 freshness deadline。
6. 实现离线验证：只消费签名完整且未过期的 trust/revocation snapshot；cache 过期、撤销状态未知或时间证明不足一律拒绝。
7. 为 unknown root/identity/algorithm、invalid signature、expired/revoked key、stale cache、missing time proof 生成稳定 reason code 和审计事件。
8. 补齐单元/API 测试和证据报告；安全 owner 对生产 policy revision 的 root/identity/algorithm/failure matrix 签署后才可冻结生产配置。

## 5. 涉及文件与写入边界

### 5.1 允许修改闭集

| 路径 | 动作 | 最小变更 |
|---|---|---|
| `backend/models/deck_plugin_supply_chain.py` | 新建 | trust-policy、identity、root、algorithm、revocation snapshot 模型 |
| `backend/services/deck_plugin/trust_policy.py` | 新建 | 策略加载、revision、allowlist 与轮换逻辑 |
| `backend/services/deck_plugin/signature_verifier.py` | 新建 | 标准签名、时间证明、撤销和离线验证适配层 |
| `backend/routers/deck_plugin_trust.py` | 新建 | 管理员 allowlist/trust-policy API |
| `backend/database.py` | 修改 | 仅追加 trust-policy、identity、revocation snapshot 与审计持久化 |
| `backend/pyproject.toml` | 修改 | 仅增加安全 owner 批准的、固定范围的标准验证依赖 |
| `backend/tests/test_deck_plugin_trust_policy.py` | 新建 | policy、轮换、撤销、离线和 API 测试 |
| `output/evidence/deck-plugin/supply-chain/DECK-SC-002/**` | 生成 | 测试摘要、policy hash、覆盖矩阵和签署引用 |

### 5.2 禁止修改范围

- 未列出的实现/测试文件、所有依赖锁和部署配置；
- `docs/design/`、`docs/issue/`、`docs/task/`、`docs/stage/`、`docs/exec/`；
- 自行实现密码学原语、接受未知算法/identity/root、在线失败后 warn-only 降级；
- 在日志、事件或 API 中暴露私钥、完整签名包、完整证书链或敏感策略内容；
- 修改 release/runtime/retention 状态机，或借本 task 宣称生产 Gate 通过。

## 6. 输入 / 输出与 Fail-Closed 矩阵

输入：`TASK-DECK-SC-001` 安全 owner scope/签署、版本化 policy 配置、trust root/identity、签名 bundle 元数据、验证时间与离线 snapshot。

输出：`trust_policy_revision`、不可变验证上下文、allowlist 查询/审计、结构化 `VerificationDecision`（`accepted|rejected`，生产路径无 `unknown`）。

以下路径均输出 `rejected`：未知/不允许算法、unknown root/identity、签名格式或覆盖错误、key 过期/撤销、撤销状态未知、离线 trust/revocation cache 过期、时间证明缺失/无效、系统时间超出容差。错误至少区分 `ARTIFACT_TRUST_ROOT_UNKNOWN`、`ARTIFACT_PUBLISHER_UNTRUSTED`、`ARTIFACT_ALGORITHM_UNSUPPORTED`、`ARTIFACT_REVOCATION_UNKNOWN`、`ARTIFACT_TRUST_CACHE_EXPIRED`、`ARTIFACT_TIME_PROOF_INVALID`。

证据记录至少包含 `test_case_id`、`trust_policy_revision`、`policy_sha256`、`verifier_version`、`decision`、`reason_code`、`run_id`、`commit_sha`、日志摘要引用和安全 owner signoff ref。

## 7. 依赖、并行性与 StagePlanner 输入

- 直接前置：`TASK-DECK-SC-001`。安全 owner 未签署时可实现和演练 draft policy，但 execute 输出必须保持 `production_policy_active=false`。
- 下游：`TASK-DECK-SC-003`。
- 可并行性：模型/持久化、verifier adapter、API、负向测试可在 draft schema 冻结后并行；算法/root/identity production 配置必须等待安全 owner。
- 冻结点：policy schema + reason codes + offline freshness 语义冻结；安全 owner 对具体 `policy_sha256` `approve` 后，production revision 才能 active。
- Execute readiness：SC-001 责任矩阵可读；批准/待批准算法矩阵明确；依赖库安全评审 owner、测试 fixtures 和离线 freshness 参数已具名。

## 8. 验收条件

- [ ] 信任根模型包含 `trust_domain`、`issuer`、`subject`、`key_fingerprint`、`not_before`、`not_after`、`revocation_url`、`algorithm_allowlist`。
- [ ] 签名/digest/key-format 矩阵显式版本化；SHA-256 为生产必选，未知算法拒绝。
- [ ] 轮换包含预热、并行验证和至少 30 天旧 key 重叠期。
- [ ] 过期、撤销、unknown revocation、stale offline cache、缺失时间证明均 fail closed。
- [ ] 离线 verifier 只使用未过期、完整性可验证的 snapshot。
- [ ] 管理员 allowlist API 有鉴权、审计和 revision 语义。
- [ ] 安全 owner 签署绑定真实 `policy_sha256`；签署前不激活生产 policy。

## 9. 最小测试 / 验证命令

```bash
backend/.venv/bin/python -m unittest backend.tests.test_deck_plugin_trust_policy
backend/.venv/bin/python -m compileall -q backend/models/deck_plugin_supply_chain.py backend/services/deck_plugin/trust_policy.py backend/services/deck_plugin/signature_verifier.py backend/routers/deck_plugin_trust.py
rg -n 'ARTIFACT_(TRUST_ROOT_UNKNOWN|PUBLISHER_UNTRUSTED|ALGORITHM_UNSUPPORTED|REVOCATION_UNKNOWN|TRUST_CACHE_EXPIRED|TIME_PROOF_INVALID)' backend output/evidence/deck-plugin/supply-chain/DECK-SC-002
git diff --check -- backend/models/deck_plugin_supply_chain.py backend/services/deck_plugin backend/routers/deck_plugin_trust.py backend/database.py backend/pyproject.toml backend/tests/test_deck_plugin_trust_policy.py
```

测试至少覆盖 allowlist CRUD、轮换窗口、过期 key、撤销 key、unknown root/identity/algorithm、离线可用 snapshot、离线过期 snapshot、clock skew 边界及审计脱敏。

## 10. 完成信号与回滚

完成信号：代码/测试证据齐全，所有负向场景稳定拒绝，draft 与 active revision 可区分，安全 owner 对 production `policy_sha256` 明确 `approve`。独立复审前不得输出 `production_ready=true`。

回滚：保留旧 policy revision 与审计；新 revision 异常时原子退回最近获批 revision或关闭新发布为 non-production-ready。不得回滚到跳过验证、接受 stale cache 或删除历史 proof 的状态。

## 11. 风险与 Clarification

| 风险/澄清 | 处理 | Owner / action |
|---|---|---|
| 标准库/算法矩阵未批准 | draft adapter 可推进，生产激活冻结 | 安全 owner：批准依赖、算法、root/identity 与 freshness policy |
| CRL/OCSP 离线 snapshot freshness 未定 | 默认采用显式过期即拒绝，不猜测宽限 | 安全 owner：给出最大 freshness 和应急更新流程 |
| 时间源或透明日志不可用 | 不改为 warn-only | 安全 owner + 平台 owner：确定受信时间证明与 incident 路径 |

## 12. Gate 声明

本 task 的实现通过不等于 production Gate 通过。任何验证状态未知都按失败处理；只有生产 policy 获安全 owner 签署且后续发布/runtime/留存证据及独立复审完成，才可申请 Gate 审批。
