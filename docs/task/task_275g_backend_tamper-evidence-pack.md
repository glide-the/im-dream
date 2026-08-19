# task_275g_backend_tamper-evidence-pack

> Task ID: `task_275g`
> Source Issue: `DECK-SC-007`
> Paperclip Issue: [SUO-275](/SUO/issues/SUO-275)
> Domain / Priority: `backend` / `P1`

## 1. 任务标题

发布端与 Runtime 篡改矩阵及可点击 Evidence Pack

## 2. 关联 Issue

| 关联 | 内容 |
|---|---|
| 来源条目 | `DECK-SC-007` |
| Task-stage Issue | [SUO-275](/SUO/issues/SUO-275) |
| 来源编排 | [SUO-258](/SUO/issues/SUO-258) |
| Design | `docs/design/deck/design_002_deck-plugin-decision-gates.md` §5.2 |
| Domain / Priority / 标签 | `backend` / P1 / `supply-chain`, `tamper-test`, `evidence`, `security` |

## 3. 任务目标

构造发布端与 runtime 的确定性篡改矩阵，证明制品字节、manifest、签名包、publisher identity、算法降级/未知、旧签名重放、lock digest 和 cache/物化字节被修改时均 fail closed，并生成包含可点击 CI/日志/提交链接、结构化错误、审计 ID 与独立 reviewer 签署的 evidence pack。

本 task 只建立测试、报告和 verdict，不在测试任务内修复生产实现。失败意见和失败报告也是有效交付，但只有全部必选 case 通过且 reviewer 签署时，该 evidence 项才可作为 Gate 通过输入。

## 4. 实现步骤

1. 冻结基准 fixture：实际包字节、RFC 8785 manifest、合法 bundle、publisher identity、trust-policy revision、release/lock/runtime IDs，并记录每个输入 hash。
2. 为每个 case 只改变一个维度，避免多重篡改掩盖实际检测点：
   - 制品内任意字节变化；
   - 包截断；
   - manifest 字段修改/增删；
   - bundle 替换；
   - publisher identity 替换；
   - 未允许/未知算法或明确降级；
   - 旧 release 签名重放到新 release；
   - lock 中 `artifact_digest` 伪造；
   - lock 中 `deck_plugin_manifest_hash` 伪造；
   - 传输后或 cache 中实际物化字节替换。
3. 每个 case 分别执行发布验证和适用的 runtime load 路径，断言不得进入 `verified`、`loaded`、`session_loaded` 或 `production_ready`。
4. 断言稳定错误码、audit event、request/run/attempt ID 和失败阶段；日志不得泄露制品、完整 bundle 或密钥。
5. 构建 evidence reporter，生成 case JSON、Markdown/HTML 索引与 `manifest_sha256`；所有 URL 必须指向实际 CI run、日志摘要和 commit。
6. 接入 CI：相关 verifier/materialization/lock 文件变化时运行矩阵并上传 immutable artifact；不把报告 URL 写成占位。
7. 独立 reviewer 逐项复核 fixture 隔离性、预期/实际结果、日志与 hash，记录 reviewer ID、范围、时间和 `approve|request_changes`。
8. 若任一 case 失败检测或缺证据，报告 verdict 为 fail 并保持 Gate 阻断；不得因为 CI job 运行完成就写 approve。

## 5. 涉及文件路径

| 路径 / 资源 | 动作 | 最小变更 |
|---|---|---|
| `backend/tests/test_deck_plugin_tamper_matrix.py` | 新建 | 十类必选篡改 case 与断言 |
| `backend/tests/fixtures/deck_plugin_supply_chain/` | 新建 | 公开、无私钥的基准/篡改 fixture |
| `backend/tests/reporting/deck_plugin_evidence.py` | 新建 | evidence JSON/Markdown/HTML 与 manifest hash |
| `.github/workflows/ci-backend.yml` | 修改 | 仅增加 Stage 4 tamper job/触发路径/artifact 上传 |
| `${CI_ARTIFACT_DIR}/deck-plugin-stage4/tamper/` | 运行时生成 | case 报告、日志摘要、manifest、签署引用 |
| 当前执行 Issue 的 Paperclip 附件/评论 | 新建 | 可点击报告与独立 reviewer 签署 |

生产源码只读；发现缺陷回流对应 `task_275b`、`task_275c` 或 `task_275d` 的修复 Issue，不得在本闭集顺手修改。

## 6. 输入 / 输出说明

### 输入

- `task_275b/275c/275d` 已稳定的 verifier、发布和 runtime 接口；
- 基准 artifact/manifest/bundle/policy/lock；
- CI run ID、commit SHA、日志和审计查询入口。

### 输出

```jsonc
{
  "evidence_pack_id": "deck-sc-tamper-...",
  "test_run_id": "...",
  "commit_sha": "...",
  "cases": [{
    "test_case_id": "...",
    "tamper_type": "...",
    "input_sha256": "sha256:...",
    "expected": "deny",
    "actual": "deny|allow|error",
    "error_code": "...",
    "audit_event_id": "...",
    "log_summary_url": "...",
    "status": "pass|fail"
  }],
  "manifest_sha256": "sha256:...",
  "reviewer": {"principal_id": "...", "decision": "...", "signed_at": "..."}
}
```

## 7. 依赖项、可并行性与冻结点

- 直接依赖：`task_275c`、`task_275d`；信任策略来自 `task_275b`。
- 与 `task_275f` 可并行；与 `task_275h` 可共享 reporter 但不得并发修改同一文件，Stage 应先合并 reporter 基础或指定单 writer。
- Freeze point：所有必选 case 都有真实 run/commit/log/audit 证据，全部 deny，manifest hash 可重算，独立 reviewer approve。
- reviewer 未具名或 `request_changes` 时只完成失败交付，Gate 仍冻结。

## 8. 测试策略

最小命令：`python -m unittest backend.tests.test_deck_plugin_tamper_matrix`

| Case 组 | 通过标准 |
|---|---|
| artifact bytes / truncation / transfer/cache replacement | `ARTIFACT_DIGEST_MISMATCH`，无 verified/loaded |
| manifest field/hash | manifest/hash mismatch 或 signature invalid，拒绝 |
| bundle / identity / replay | signature/identity/replay 拒绝并审计 |
| unknown/downgraded algorithm | `ARTIFACT_ALGORITHM_UNSUPPORTED`，fail closed |
| forged lock digest/manifest hash | runtime 或发布端拒绝，receipt 不成功 |
| 报告完整性 | 每项有真实链接、run/commit、audit、hash 与 reviewer |

另执行 reporter 自测、`python -m json.tool`、`shasum -a 256` 和 `git diff --check --` 指定闭集。

## 9. 完成标志

- [ ] 十类必选篡改场景均已独立执行。
- [ ] 每个场景有 expected/actual、结构化错误和审计证据。
- [ ] 任一篡改不得进入 verified/loaded/session_loaded/production_ready。
- [ ] CI 自动触发并上传不可变报告。
- [ ] 报告含 case/run/commit/log/audit/manifest hash 与实际可点击链接。
- [ ] 独立 reviewer 已签署范围与 verdict。
- [ ] 若存在失败，报告明确列出 owner/action 且 Gate 保持阻断。

## 10. 风险提示与回滚

| 风险 | 处理 / 回滚 |
|---|---|
| fixture 含真实私钥/敏感 bundle | 只用公开测试向量；secret 扫描 |
| case 同时修改多个维度 | 单变量 mutation，保留输入 hash |
| 报告 job 通过但断言未执行 | 报告 manifest 必须列出完整 case 集和测试计数 |
| 链接短期有效或可变 | CI immutable artifact/permalink + 内容 hash |

回滚 CI job 时必须保持 production Gate 阻断并保留最近 evidence；不得用旧报告覆盖当前 commit verdict。

## 11. 允许 / 禁止修改范围

- 允许：§5 测试、fixture、reporter、单个 CI job 和运行时 evidence。
- 禁止：生产源码、设计/Issue/task/Stage/Exec、部署/依赖配置、真实密钥、其他 CI job。
- 未列出的路径默认禁止。

## 12. StagePlanner / Execute Readiness

| 字段 | 值 |
|---|---|
| 前序 | `task_275c`, `task_275d` |
| 可并行 | 与 `task_275f`；reporter 与 `275h` 单 writer |
| Freeze point | 全矩阵 deny + immutable evidence + independent reviewer approve |
| Execute readiness | 非生产 fixture、审计查询、CI artifact/permalink、reviewer 已指定 |
| 证据格式 | evidence-pack JSON/Markdown/HTML、manifest SHA-256、不可变 CI/log/commit/audit URL 与 reviewer 签署 verdict |
| Clarification owner/action | `CEOOrchestrator` 路由 security owner 指定独立 reviewer 和证据留存位置；失败 case 由报告中的对应 `275b/275c/275d` owner 接单修复 |
| 未满足 Gate | recovery/purge evidence、owner 全签、独立总复审 |

本 task 的“完成”可包含 fail verdict；只有 pass evidence 才能支持后续 Gate 复审。
