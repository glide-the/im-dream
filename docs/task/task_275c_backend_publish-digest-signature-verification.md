# task_275c_backend_publish-digest-signature-verification

> Task ID: `task_275c`
> Source Issue: `DECK-SC-003`
> Paperclip Issue: [SUO-275](/SUO/issues/SUO-275)
> Domain / Priority: `backend` / `P0`

## 1. 任务标题

发布端实际字节 SHA-256、RFC 8785 Manifest 与签名包原子验证

## 2. 关联 Issue

| 关联 | 内容 |
|---|---|
| 来源条目 | `DECK-SC-003` |
| Task-stage Issue | [SUO-275](/SUO/issues/SUO-275) |
| 来源编排 | [SUO-258](/SUO/issues/SUO-258) |
| Design | `docs/design/deck/design_002_deck-plugin-decision-gates.md` §4.2.1、§4.2.3 |
| 既有合同 | `task_deck_002_backend_runtime-lock.md` |
| Domain / Priority / 标签 | `backend` / P0 / `supply-chain`, `digest`, `signature`, `manifest` |

## 3. 任务目标

在 release 发布边界对实际分发字节计算 SHA-256，对 RFC 8785 canonical manifest 字节计算 SHA-256，使用 `task_275b` 的冻结 trust-policy 验证 DSSE/Sigstore 签名包确实绑定 `artifact_digest + deck_plugin_manifest_hash + publisher_identity`，并把不可变验证结果与 release/runtime lock 原子关联。

本 task 不信任 marketplace 标签或上传元数据，不实现 runtime 二次摘要、留存清理或 UI。

## 4. 实现步骤

1. 定义流式 `artifact_digest` 计算器：读取最终实际分发包字节，输出 `sha256:<64-lowercase-hex>` 与准确 `artifact_size_bytes`，禁止对解包目录、URL、标签或 cache metadata 计算。
2. 使用经过验证的 RFC 8785 实现生成 manifest canonical bytes；对其计算 `deck_plugin_manifest_hash`，固定 Unicode、数字与键顺序测试向量。
3. 构造规范签名 statement，严格绑定 artifact digest、manifest hash、publisher identity、release identity 和 payload type；拒绝缺字段、重复歧义或额外未识别关键字段。
4. 调用 `signature_verifier` 验证 bundle 格式、信任链/identity、算法、时间证明、撤销与 policy revision。
5. 将 `verification_status`、`verified_at`、`verifier_version`、`trust_policy_revision`、bundle ref、signer 摘要和失败原因与 release/lock 在同一事务中写入；同一 release 的成功验证结果不可变。
6. 只有服务端判定 digest、signature、identity、restore source 与所有 required 依赖全部满足时，才可生成 production-ready 候选；本 task 不做最终 Gate approve。
7. 所有失败路径返回结构化错误并追加审计；失败不得留下 published/verified 半状态。
8. 对并发发布、同版本不同字节、同 manifest 不同包、签名重放、过期/撤销 root、离线策略失效做单元和事务测试。

## 5. 涉及文件路径

| 路径 | 动作 | 最小变更 |
|---|---|---|
| `backend/models/deck_plugin.py` | 修改 | 增量增加 verification/bundle/restore 字段，不改既有字段语义 |
| `backend/services/deck_plugin/artifact_digest.py` | 新建 | 实际分发字节流 SHA-256 与 size |
| `backend/services/deck_plugin/manifest_normalizer.py` | 新建 | RFC 8785 canonical bytes/hash adapter |
| `backend/services/deck_plugin/signature_verifier.py` | 修改 | 消费 `task_275b` trust-policy；不扩大 policy 管理职责 |
| `backend/services/deck_plugin/release_service.py` | 修改 | 发布事务中执行验证并冻结结果 |
| `backend/services/deck_plugin/lock_generator.py` | 修改 | 只消费真实 digest/manifest hash/verification ref |
| `backend/database.py` | 修改 | 增量 verification 字段/表和不可变约束 |
| `backend/tests/test_deck_plugin_publish_verification.py` | 新建 | digest、RFC8785、签名与事务测试 |
| `backend/tests/fixtures/deck_plugin_signatures/` | 新建 | 无私钥的公开测试向量与篡改 fixture |
| `backend/pyproject.toml`、`backend/requirements.txt` | 条件修改 | 仅锁定经批准的 RFC 8785 实现；禁止手写近似 canonicalizer |

## 6. 输入 / 输出说明

### 输入

- 最终分发字节流与 size；
- `DeckPluginManifestV1`；
- `sigstore-bundle/v1` 或显式允许的 DSSE bundle ref；
- publisher identity、release ID 与 `trust_policy_revision`；
- `restore_source_ref` 可读性结果。

### 输出

```jsonc
{
  "artifact_digest": "sha256:...",
  "artifact_size_bytes": 123,
  "deck_plugin_manifest_hash": "sha256:...",
  "signature_scheme": "sigstore-bundle/v1",
  "signature_bundle_ref": "artifact://signatures/...",
  "publisher_identity": "...",
  "verification_status": "verified|failed|expired|revoked",
  "verified_at": "...",
  "verifier_version": "...",
  "trust_policy_revision": "tp_..."
}
```

失败码至少包含 `ARTIFACT_SIGNATURE_INVALID`、`ARTIFACT_DIGEST_MISMATCH`、`ARTIFACT_TRUST_ROOT_UNKNOWN`、`ARTIFACT_VERIFICATION_EXPIRED`、`ARTIFACT_PUBLISHER_UNTRUSTED`、`ARTIFACT_ALGORITHM_UNSUPPORTED`。

## 7. 依赖项、可并行性与冻结点

- 直接依赖：`task_275b` active trust-policy revision。
- 与既有 `task_deck_002` 对齐 runtime lock 字段；不得反向放宽其不可变性。
- 下游：`task_275d`、`task_275e`、`task_275g`、`task_275i`。
- Freeze point：相同 release 的实际字节、canonical manifest、bundle、publisher identity 与 verification row 原子冻结。
- 与 `task_275b` 串行合并共享 verifier；`task_275d` 只在稳定输出合同后开始。

## 8. 测试策略

最小命令：`python -m unittest backend.tests.test_deck_plugin_publish_verification`

| 场景 | 通过标准 |
|---|---|
| 已知实际字节 | digest/size 与外部工具一致 |
| RFC 8785 标准向量 | canonical bytes/hash 完全一致 |
| 合法 bundle | verified 且绑定三元组和 policy revision |
| 字节或 manifest 任一篡改 | 明确 mismatch，release 不进入 verified/published |
| bundle/identity/算法/时间证明异常 | fail closed，结构化错误和审计存在 |
| 旧 release 签名重放 | 因 statement/release 绑定不一致拒绝 |
| 并发同版本不同字节 | 至多一份事务提交，另一份冲突 |
| 离线 policy cache 过期 | 拒绝，不生成 warn-only 结果 |

执行 `git diff --check --` 指定文件，并用 `shasum -a 256` 交叉验证固定 fixture。

## 9. 完成标志

- [ ] digest 对最终实际分发字节流计算且格式严格。
- [ ] manifest hash 使用 RFC 8785 标准实现和标准向量。
- [ ] bundle 覆盖 digest、manifest hash、publisher identity 与 release statement。
- [ ] trust root、算法、撤销、过期和时间证明按冻结 policy 验证。
- [ ] 结果含 status/time/verifier/policy revision 并与 release/lock 原子冻结。
- [ ] 失败码完整且无半发布状态。
- [ ] 合法、篡改、过期、撤销、未知 root、离线和并发测试通过。

## 10. 风险提示与回滚

| 风险 | 处理 / 回滚 |
|---|---|
| 计算的是解包内容而非分发字节 | 测试 gzip/tar 元数据差异；只读最终包流 |
| 自研 canonical JSON 与 RFC 偏差 | 使用批准库和标准向量 |
| 事务先发布后验证 | 强制同事务/状态机，失败不得留下 published |
| verifier 回滚改变既有结论 | 新 verifier 只产生规范等价结果；旧结果不可变 |

回滚只能暂停新发布、恢复仍获批准的 verifier/policy revision；不得把未验证 release 提升为 production-ready，也不得删除历史验证证明。

## 11. 允许 / 禁止修改范围

- 允许：§5 精确闭集，依赖文件仅允许经批准的最小 pin。
- 禁止：runtime materialization、retention/purge、前端、Stage/Exec、部署配置、完整签名包入日志、未列出源码。
- 禁止改写 `docs/design/`、`docs/issue/`、`docs/task/` 或既有 release/lock 的原摘要。

## 12. StagePlanner / Execute Readiness

| 字段 | 值 |
|---|---|
| 前序 | `task_275b` |
| 可并行 | fixture/标准向量可提前准备；共享 verifier 合并不可并行 |
| Freeze point | release verification row 与 lock 引用原子冻结 |
| Execute readiness | trust-policy revision、bundle test vector、RFC8785 库、事务边界已明确 |
| 证据格式 | 单元测试报告、标准向量/input hash、release verification row、audit ID、CI run 与 commit SHA |
| Clarification owner/action | security owner 批准 RFC 8785/DSSE 依赖与验证语义，marketplace/制品平台 owner 确认最终分发字节和原子发布边界；由 `CEOOrchestrator` 路由 |
| 未满足 Gate | runtime 二次摘要、留存/恢复、真实 evidence pack、owner/reviewer 与复审 |

本 task 完成仅证明发布端合同，不等于 Stage 4 production Gate approve。
