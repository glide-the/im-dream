# task_275f_backend_cold-recovery-operations

> Task ID: `task_275f`
> Source Issue: `DECK-SC-006`
> Paperclip Issue: [SUO-275](/SUO/issues/SUO-275)
> Domain / Priority: `backend` / `P1`

## 1. 任务标题

冷恢复可用性、可度量恢复目标与制品平台运营承诺

## 2. 关联 Issue

| 关联 | 内容 |
|---|---|
| 来源条目 | `DECK-SC-006` |
| Task-stage Issue | [SUO-275](/SUO/issues/SUO-275) |
| 来源编排 | [SUO-258](/SUO/issues/SUO-258) |
| Design | `docs/design/deck/design_002_deck-plugin-decision-gates.md` §4.2.1、§4.2.5 |
| Domain / Priority / 标签 | `backend` / P1 / `supply-chain`, `disaster-recovery`, `sla`, `operations` |
| Clarification | 冷存储实现未指定；默认由 marketplace/制品平台 owner 选择并披露，只要满足冻结合同 |

## 3. 任务目标

实现按 `restore_source_ref` 恢复不可变制品、签名包和 manifest 证明的通用能力，并形成 marketplace/制品平台 owner 签署的可度量运营承诺。恢复后必须重算实际字节 SHA-256、验证 manifest hash/签名证明，并通过 runtime 二次摘要链；摘要不一致或证明不可用时恢复失败且禁止依赖该制品的新运行。

本 task 不擅自设定 RTO/RPO 数值、不选择未获 owner 批准的供应商、不执行正式季度演练；正式冷恢复与清理 evidence 由 `task_275h` 负责。

## 4. 实现步骤

1. 由 marketplace/制品平台 owner 选择并披露冷存储物理/逻辑位置、加密/访问边界、对象不可变性、地域与第三方依赖；记录方案 revision/hash。
2. 定义并签署可度量承诺：RTO、RPO、备份/复制频率、证明留存寿命、恢复演练周期、可用性目标、连续失败阈值、incident 升级与第三方违约责任。
3. 定义 `ColdStorageAdapter` 最小接口：按不可变 digest/ref 读取字节、bundle、manifest/provenance；禁止按 `latest` 或可变路径恢复。
4. 实现恢复状态机：`requested → fetching → verifying → restored|failed`；每次 attempt 有唯一 ID、requester、reason、timestamps 和 audit。
5. 验证链：
   - 从 cold ref 读取实际制品与证明；
   - 重算 artifact digest 和 RFC 8785 manifest hash；
   - 用冻结 trust-policy 验证 bundle/identity；
   - 原子恢复到热 CAS；
   - 由 runtime 路径再次重算并生成 load receipt。
6. 任一摘要/签名/identity/证明不一致时隔离恢复对象、返回 `ARTIFACT_RESTORE_VERIFICATION_FAILED` 并触发告警。
7. 暴露恢复请求/状态查询与指标：request count、success ratio、duration、RTO breach、cold storage availability；指标不得包含私钥或完整 bundle。
8. 连续失败或 RTO breach 建立 incident，通知具名 owner，并阻止依赖制品的新生产运行。
9. 使用 fake adapter 测试正常、字节错、证明错、provider 失联、重试幂等、RTO breach 和热 CAS 原子发布。

## 5. 涉及文件路径

| 路径 / 资源 | 动作 | 最小变更 |
|---|---|---|
| `backend/models/artifact_recovery.py` | 新建 | recovery request/attempt/result/metric 模型 |
| `backend/services/deck_plugin/cold_storage_adapter.py` | 新建 | provider-neutral 只读恢复接口 |
| `backend/services/deck_plugin/artifact_recovery_service.py` | 新建 | 恢复状态机、完整验证与热 CAS 原子发布 |
| `backend/routers/deck_plugin_retention.py` | 修改 | 仅增加恢复请求/状态端点 |
| `backend/database.py` | 修改 | recovery attempt/audit/metric 表 |
| `backend/tests/test_deck_plugin_cold_recovery.py` | 新建 | fake adapter 与失败/指标测试 |
| `artifacts/deck-plugin-stage4/operations/cold-recovery-commitment.json` | 新建 | 机器可读运营承诺与 owner 签署引用 |
| `artifacts/deck-plugin-stage4/operations/cold-recovery-commitment.md` | 新建 | 可点击的人类可读承诺与缺口 |

具体生产 provider adapter 只有在 owner 方案签署并由 Stage 单独加入闭集后才能实现；不得把通用 task 静默扩大到任意云配置。

## 6. 输入 / 输出说明

### 输入

- `artifact_digest`、`restore_source_ref`、manifest/bundle/provenance refs；
- `trust_policy_revision`、retention record、恢复请求 reason；
- owner 签署的 RTO/RPO、failure threshold 与演练周期。

### 输出

- `ArtifactRecoveryAttempt`：attempt/status/start/end/duration/digest comparisons/proof result/hot CAS ref/audit ID；
- 结构化错误：`ARTIFACT_RESTORE_UNAVAILABLE`、`ARTIFACT_RESTORE_VERIFICATION_FAILED`、`ARTIFACT_RESTORE_RTO_BREACHED`；
- 指标与 owner 签署的运营承诺 JSON/Markdown。

## 7. 依赖项、可并行性与冻结点

- 直接依赖：`task_275e`；验证链还消费 `task_275b`、`task_275c`、`task_275d` 的稳定接口。
- 下游：`task_275h` 正式演练。
- Clarification owner/action：marketplace/制品平台 owner 选择方案并签署 RTO/RPO、备份频率、演练周期、指标、第三方 SLA/违约责任；CEOOrchestrator 负责路由。
- Freeze point：方案 revision、可读 restore source、完整证明链和运营承诺均具名签署。
- 在签署前可实现 provider-neutral adapter 和 fake 测试，但不得启用 production recovery 或宣称达标。

## 8. 测试策略

最小命令：`python -m unittest backend.tests.test_deck_plugin_cold_recovery`

| 场景 | 通过标准 |
|---|---|
| 正常恢复 | 同 digest、manifest/bundle 有效、热 CAS 原子发布 |
| 实际字节或 manifest 被改 | 恢复失败、隔离、结构化审计 |
| bundle/identity 不匹配 | fail closed，不恢复 |
| provider 失联 | 有界重试后失败/incident，不把旧 cache 当恢复证据 |
| 重复 request/attempt | 幂等或新 attempt 明确关联，不产生分叉结果 |
| RTO breach | 指标和 incident 产生，owner 通知记录存在 |
| 热 CAS 发布失败 | 不留下可读半对象，重试安全 |

对 commitment JSON 执行 `python -m json.tool` 与内容 hash 校验；真实 RTO/RPO 只由签署值判定，测试不得用示例值伪造承诺。

## 9. 完成标志

- [ ] 冷存储位置/adapter/不可变引用由 owner 具名披露。
- [ ] RTO/RPO、备份频率、演练周期、可用性与失败升级已签署。
- [ ] 恢复后 artifact digest 与原值一致。
- [ ] manifest hash、签名包、publisher identity 与 trust-policy 均重新验证。
- [ ] 热 CAS 发布原子且 runtime 二次摘要链可继续。
- [ ] 连续失败/RTO breach 产生 incident 并阻止新生产运行。
- [ ] request/success/duration/availability 指标可查询。
- [ ] fake adapter 单元/集成测试与承诺 schema/hash 校验通过。

## 10. 风险提示与回滚

| 风险 | 处理 / 回滚 |
|---|---|
| 用示例 4 小时/零丢失冒充承诺 | 禁止；只消费 owner 签署数值 |
| 第三方可用但证明包丢失 | 恢复失败；摘要、bundle、manifest 缺一不可放行 |
| 恢复覆盖热 CAS 正确对象 | 按 digest 写临时位置并原子 compare/publish |
| provider 回滚导致 ref 不可读 | 禁止新运行并触发 incident；不改原 digest |

回滚只能禁用 provider adapter、保留恢复记录并阻断相关制品；不得把未知恢复状态写成成功。

## 11. 允许 / 禁止修改范围

- 允许：§5 精确闭集；生产 provider adapter 需 Stage 增量授权。
- 禁止：云部署配置、secret 值、retention 状态机重写、runtime loader 重写、前端、季度 evidence 报告和未列出源码。
- 禁止修改 design/issue/task/stage/exec 文档；运营 artifact 不得包含凭证。

## 12. StagePlanner / Execute Readiness

| 字段 | 值 |
|---|---|
| 前序 | `task_275e`；验证接口依赖 `275b/275c/275d` |
| 可并行 | fake adapter/模型可准备；production provider 与承诺等待 owner |
| Freeze point | owner 签署的 provider revision + RTO/RPO + 完整证明链 |
| Execute readiness | provider 选择、凭证注入方式、热/冷 CAS 接口、incident/metrics owner 明确 |
| 证据格式 | owner 签署的 commitment JSON/Markdown 与 hash、fake-adapter 测试报告、recovery attempt/audit/incident/metric refs |
| Clarification owner/action | marketplace/制品平台 owner 选择 provider 并签署 RTO/RPO、频率、cadence、指标和第三方责任；`CEOOrchestrator` 负责路由 |
| 未满足 Gate | 正式冷恢复/清理演练、独立 reviewer、独立复审 |

本 task 完成不等于 Stage 4 production Gate approve。
