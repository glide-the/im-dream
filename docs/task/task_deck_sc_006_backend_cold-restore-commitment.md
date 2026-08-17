# task_deck_sc_006_backend_cold-restore-commitment

## 1. 任务标题

冷存储同 Digest 恢复能力与具名运营承诺

## 2. 唯一映射与 Domain

| 字段 | 值 |
|---|---|
| Task ID | `TASK-DECK-SC-006` |
| 来源 Issue | `DECK-SC-006` |
| Paperclip TaskDesign Issue | [SUO-275](/SUO/issues/SUO-275) |
| Canonical design | `docs/design/deck/design_002_deck-plugin-decision-gates.md` §4.2.1、§4.2.5 |
| Domain | `backend`（含 marketplace/制品平台运营签署） |
| 优先级 | P1 |
| 下游 Stage 映射键 | `stage4.supply_chain.DECK-SC-006` |

## 3. 任务目标与非目标

实现从 `restore_source_ref` 定位冷存储、恢复不可变制品、重新验证同一 SHA-256、回填热存储/CAS 与 retention 状态的能力，并形成可度量 RTO/RPO、演练周期、告警和具名 marketplace/制品平台 owner 承诺。

非目标：不指定 canonical design 未冻结的云厂商；不在 production 直接试验破坏性恢复；不把“runbook 已写”当恢复能力；不在 digest 不一致或 cold source 不可读时允许新运行。

## 4. 实现步骤

1. 冻结 provider-neutral `ColdStorageAdapter`、restore request/receipt、指标和错误合同；具体 provider 由具名 owner 选择并披露。
2. 从 SC-005 `restore_source_ref` 读取冷制品到隔离临时位置，流式计算 SHA-256，与原 digest 比对后才原子发布回热存储/CAS。
3. 成功后按当前权威引用恢复为 `pinned` 或保持 `recoverable`；失败/不一致不得改写原记录，隔离错误字节并告警。
4. 实现幂等 restore request、超时/重试上限和连续失败 incident 升级；依赖制品的新运行在恢复未知/失败时 fail closed。
5. 输出指标：请求数、成功率、恢复耗时分布、冷源可用性、digest mismatch、连续失败/incident 数。
6. 编写并验证 operator runbook：定位、恢复、校验、原子发布、状态回填、失败隔离、升级和回滚。
7. 由 marketplace/制品平台 owner 对具体 provider/location、RTO、RPO、备份频率、演练周期、告警/升级和责任边界签署；第三方 SLA 作为证据引用。
8. 在非生产/专用 sandbox 完成正常、mismatch、provider unavailable、timeout、连续失败测试，生成可点击 evidence；真实定期演练由 SC-008 验收。

## 5. 涉及文件与写入边界

### 5.1 允许修改闭集

| 路径 | 动作 | 最小变更 |
|---|---|---|
| `backend/models/artifact_retention.py` | 修改 | 仅追加 restore request/receipt/metric 字段 |
| `backend/services/deck_plugin/cold_storage.py` | 新建 | provider-neutral cold storage adapter |
| `backend/services/deck_plugin/artifact_restore.py` | 新建 | 同 digest 恢复、幂等、隔离和状态回填 |
| `backend/routers/deck_plugins.py` | 修改 | 仅增加受控 restore/status API |
| `backend/services/errors/error_registry.py` | 修改 | 仅增加 restore/availability/digest 错误码 |
| `backend/tests/test_artifact_cold_restore.py` | 新建 | 正常、mismatch、不可用、重试/升级测试 |
| `docs/evidence/deck-plugin/supply-chain/DECK-SC-006/restore-commitment.json` | 新建/追加 | RTO/RPO/provider/频率/owner 签署，append-only |
| `docs/evidence/deck-plugin/supply-chain/DECK-SC-006/restore-runbook.md` | 新建/修改 | 可操作、已验证的 runbook 与证据链接 |
| `output/evidence/deck-plugin/supply-chain/DECK-SC-006/**` | 生成 | 测试报告、receipt/metric 摘要和日志链接 |

### 5.2 禁止修改范围

- 未列出的实现/测试、依赖/锁、部署/生产存储配置和前端；
- `docs/design/`、`docs/issue/`、`docs/task/`、`docs/stage/`、`docs/exec/`；
- 在 task 内硬编码未批准的 provider/credential，记录 secret 或完整制品；
- digest 不一致仍发布、cold source 未知时继续新运行、删除原始 restore/audit；
- 在 production 直接执行演练或破坏真实冷存储数据。

## 6. 输入 / 输出与证据格式

输入：SC-005 retention record/restore source、原始 artifact digest、cold adapter、当前权威引用、owner 批准的 RTO/RPO 和演练策略。

输出：`ArtifactRestoreReceipt`（request/artifact/source/destination、expected/actual digest、start/end/duration、status/reason、actor/attempt）、状态回填、指标、runbook、owner commitment。

`restore-commitment.json` 至少包含 `commitment_id`、`owner_principal_id`、`provider_class`、脱敏 `location_ref`、`rto_seconds`、`rpo_seconds`、`backup_frequency`、`drill_frequency`、`metric_refs`、`material_sha256`、`decision`、`signed_at`、`third_party_sla_ref|null`。

## 7. 依赖、并行性与 StagePlanner 输入

- 直接前置：`TASK-DECK-SC-005`；治理依赖：`TASK-DECK-SC-001` 的 marketplace/制品平台 owner。
- 下游：`TASK-DECK-SC-008`。
- 可并行性：adapter interface、restore service、metrics/runbook 草案可并行；provider integration 与承诺签署需 owner 决策后串行。
- 冻结点：同 digest restore + state transition + failure block 测试通过；owner 对具体 commitment 材料 hash `approve`。未签署或 provider SLA 未确认时 production Gate 继续阻断。
- Execute readiness：SC-005 restore/ref schema 可用；测试 cold store/sandbox、原子 CAS 写接口、metrics/incident sink 和 owner 已具名。

## 8. 验收条件

- [ ] RTO/RPO、provider/location、备份/演练周期和责任边界可度量且具名签署。
- [ ] 恢复流程从 `restore_source_ref` 到隔离校验、原子发布和 retention 状态回填完整。
- [ ] 恢复后 digest 与原值完全一致；mismatch 隔离并拒绝新运行。
- [ ] provider unavailable/timeout/连续失败触发稳定错误、指标、告警和 incident 升级。
- [ ] restore request 幂等，receipt 不可变且能追溯 source/destination/attempt。
- [ ] 正常与失败测试在专用 sandbox 完成，可点击证据包含 run/commit/log/receipt。
- [ ] “文档已写”未被当成能力完成；SC-008 真实演练仍为后续 Gate。

## 9. 最小测试 / 验证命令

```bash
backend/.venv/bin/python -m unittest backend.tests.test_artifact_cold_restore
backend/.venv/bin/python -m compileall -q backend/models/artifact_retention.py backend/services/deck_plugin/cold_storage.py backend/services/deck_plugin/artifact_restore.py
python -m json.tool docs/evidence/deck-plugin/supply-chain/DECK-SC-006/restore-commitment.json >/dev/null
rg -n 'rto_seconds|rpo_seconds|owner_principal_id|material_sha256|ARTIFACT_RESTORE_UNAVAILABLE|ARTIFACT_DIGEST_MISMATCH' docs/evidence/deck-plugin/supply-chain/DECK-SC-006 backend output/evidence/deck-plugin/supply-chain/DECK-SC-006
git diff --check -- backend/models/artifact_retention.py backend/services/deck_plugin backend/routers/deck_plugins.py backend/services/errors/error_registry.py backend/tests/test_artifact_cold_restore.py docs/evidence/deck-plugin/supply-chain/DECK-SC-006
```

## 10. 完成信号与回滚

完成信号：sandbox 恢复和所有失败矩阵通过、指标/incident 可观察、具名 owner 对真实 provider/RTO/RPO 材料 `approve`，证据可点击。季度真实演练和独立复审前不解除 Gate。

回滚：关闭新 restore 请求并保持 artifact `pinned|recoverable|quarantined`，回到最近稳定 adapter；不删除 cold source、receipt 或 audit。回滚后恢复源不可读时必须阻止依赖制品的新运行。

## 11. 风险与 Clarification

| 风险/澄清 | 处理 | Owner / action |
|---|---|---|
| 具体 cold provider 未指定 | provider-neutral 接口先行，不猜测供应商 | Marketplace/制品平台 owner：选择 provider/location 并签 RTO/RPO/SLA |
| 第三方 SLA 不覆盖同 digest/取回时间 | production Gate 保持阻断 | Owner + 法务/采购（如适用）：补合同或选择替代 provider |
| 恢复影响线上 CAS | 仅 sandbox 演练，生产需独立变更窗 | Runtime/SRE owner：批准隔离、容量和原子切换方案 |

## 12. Gate 声明

只有真实恢复能力、同 digest 证据和具名运营承诺同时成立，才能作为 Gate 输入；runbook 或 mock 测试单独不构成 production-ready。
