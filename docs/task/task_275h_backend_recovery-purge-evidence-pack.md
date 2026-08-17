# task_275h_backend_recovery-purge-evidence-pack

> Task ID: `task_275h`
> Source Issue: `DECK-SC-008`
> Paperclip Issue: [SUO-275](/SUO/issues/SUO-275)
> Domain / Priority: `backend` / `P1`

## 1. 任务标题

冷恢复演练、权威引用 Purge Gate 与可点击 Evidence Pack

## 2. 关联 Issue

| 关联 | 内容 |
|---|---|
| 来源条目 | `DECK-SC-008` |
| Task-stage Issue | [SUO-275](/SUO/issues/SUO-275) |
| 来源编排 | [SUO-258](/SUO/issues/SUO-258) |
| Design | `docs/design/deck/design_002_deck-plugin-decision-gates.md` §5.2 |
| Domain / Priority / 标签 | `backend` / P1 / `supply-chain`, `dr-test`, `cleanup`, `evidence` |

## 3. 任务目标

在隔离的非生产环境执行可重复冷恢复演练和引用清理测试：清除热副本/节点 cache 后从冷存储恢复同一 artifact digest，并复核签名包、manifest hash 与 runtime 二次摘要；分别证明 release、runtime lock、Workflow Run、legal hold 任一权威引用存在时 purge 必须拒绝，只有引用归零、hold 解除、90 天隔离届满且二次检查通过后才允许 purge，同时审计仍可查询。

本 task 不在 production 直接演练、不缩短真实生产隔离期、不修复生产源码。失败报告有效，但不能支持 Gate approve。

## 4. 实现步骤

1. 冻结非生产演练环境、随机/指定制品选择策略、seed、artifact digest、manifest/bundle refs、热/冷 CAS 与 runtime node；记录环境和输入 hash。
2. 冷恢复演练：
   - 证明热 CAS 与节点 cache 初始存在；
   - 明确删除/隔离测试命名空间中的热副本和 node cache；
   - 从 `restore_source_ref` 读取冷对象；
   - 重算实际字节 digest，验证 RFC 8785 manifest hash、bundle、publisher identity 和 trust-policy；
   - 恢复热 CAS，再让 runtime 重新物化/重算并生成 receipt；
   - 比较原始、恢复和 runtime 三个 digest 完全一致。
3. 恢复失败场景：冷对象缺失、字节错、bundle/manifest 错、provider 失联；均告警并阻止新运行。
4. purge 矩阵分别建立 release、lock、run、legal hold 引用，尝试 purge 并断言稳定拒绝码和审计。
5. 使用固定时钟模拟零引用后 90 天边界；`89d23:59:59` 拒绝，期满后进入 eligible；purge 事务内注入并发新引用，必须拒绝。
6. 成功 purge 只删除测试对象字节，随后验证 digest/删除时间/原因/actor/引用快照审计和证明引用仍可查询。
7. 生成恢复/清理 evidence pack、Markdown/HTML 索引、日志摘要、截图/trace（如有）、manifest hash 与季度演练 cadence 记录。
8. 独立 reviewer 复核环境隔离、热/cache 清除证据、hash 链、purge matrix 和审计持久性。

## 5. 涉及文件路径

| 路径 / 资源 | 动作 | 最小变更 |
|---|---|---|
| `backend/tests/test_deck_plugin_recovery_purge_e2e.py` | 新建 | 恢复与 purge 自动化矩阵 |
| `backend/tests/drills/deck_plugin_cold_recovery_drill.py` | 新建 | 非生产演练 runner 与安全环境 guard |
| `backend/tests/fixtures/deck_plugin_recovery/` | 新建 | 隔离冷/热/cache fixture |
| `backend/tests/reporting/deck_plugin_evidence.py` | 修改 | 增加 recovery/purge schema，不改 tamper 语义 |
| `.github/workflows/ci-backend.yml` | 修改 | 仅增加 cleanup test 和受控手动 drill artifact |
| `${CI_ARTIFACT_DIR}/deck-plugin-stage4/recovery-purge/` | 运行时生成 | 报告、日志、manifest 与 reviewer refs |
| 当前执行 Issue 的 Paperclip 附件/评论 | 新建 | 可点击报告与独立 reviewer 签署 |

生产 recovery/retention 源码只读；缺陷回流 `task_275e` 或 `task_275f` 的修复 Issue。

## 6. 输入 / 输出说明

### 输入

- `task_275e` retention/purge API 与 `task_275f` recovery API；
- 冷/热 CAS 和 runtime 隔离环境；
- owner 签署 RTO/RPO 与季度 cadence；
- CI run、commit、audit/log 查询。

### 输出

- `RecoveryDrillResult`：选择策略、artifact、原始/恢复/runtime digest、duration、RTO verdict、proof refs；
- `PurgeGateCase[]`：reference type、hold、quarantine time、expected/actual/error/audit；
- evidence pack：`evidence_pack_id`、`test_run_id`、`commit_sha`、case URLs、`manifest_sha256`、reviewer 签署。

## 7. 依赖项、可并行性与冻结点

- 直接依赖：`task_275e`、`task_275f`；runtime 复核消费 `task_275d`。
- 与 `task_275g` 可执行并行，但 reporter/CI 文件单 writer 串行合并。
- Freeze point：真实非生产演练已清除热/cache、恢复三摘要一致；四类引用/hold 拒绝及唯一允许 purge 路径均有不可变证据；独立 reviewer approve。
- RTO/RPO 未签署、演练环境未隔离或冷对象不可读时 task 只能输出 fail verdict。

## 8. 测试策略

最小自动化命令：`python -m unittest backend.tests.test_deck_plugin_recovery_purge_e2e`

受控演练入口：`python -m backend.tests.drills.deck_plugin_cold_recovery_drill --environment <non-production-id> --artifact-digest <sha256:...> --output <CI_ARTIFACT_DIR>`

| 场景 | 通过标准 |
|---|---|
| 清除热/cache 后恢复 | 原始/恢复/runtime digest 完全一致，证明链有效 |
| 冷对象/证明异常 | 恢复失败、告警、阻止新运行 |
| release/lock/run 引用 | 每类单独拒绝 purge |
| legal hold | 零其他引用仍拒绝 |
| 90 天边界 | 未满拒绝，期满只进入 eligible |
| purge 并发新引用 | 二次检查发现并拒绝 |
| 合法 purge | 仅测试对象字节删除，审计/证明保留 |
| 报告 | 真实链接、run/commit/log/audit/hash/reviewer 完整 |

## 9. 完成标志

- [ ] 至少一次隔离非生产冷恢复演练完整执行。
- [ ] 热副本和节点 cache 清除有可复核证据。
- [ ] 恢复 artifact、manifest、bundle 与 runtime digest 全部一致。
- [ ] 恢复失败告警并阻止新运行。
- [ ] release/lock/run/legal hold 四类阻断逐项通过。
- [ ] 90 天边界、并发新引用与合法 purge 路径均有测试。
- [ ] purge 后 append-only 审计仍可查询。
- [ ] 报告有真实可点击链接、manifest hash 与独立 reviewer 签署。
- [ ] 任一失败明确保持 Gate 阻断并点名修复 owner/action。

## 10. 风险提示与回滚

| 风险 | 处理 / 回滚 |
|---|---|
| 演练误删生产/共享对象 | environment guard、测试 namespace、digest allowlist；不满足即退出 |
| 固定时钟被误用于生产配置 | 只在测试依赖注入，生产 90 天下限不变 |
| 热/cache 未真正清除 | 记录对象列表与清除前后证据，恢复前断言不可读 |
| 报告只证明 API 响应不证明字节 | 保存三份 digest、证明验证与 load receipt |

回滚 CI/drill runner 时保留最近报告并关闭 Gate；不得删除失败演练审计或用旧报告代表当前 commit。

## 11. 允许 / 禁止修改范围

- 允许：§5 测试、drill、fixture、reporter、单个 CI job 和 evidence。
- 禁止：production 源码、生产数据/环境、隔离期配置、design/issue/task/stage/exec、依赖/部署配置。
- 未列出的资源和任何真实 secret 默认禁止。

## 12. StagePlanner / Execute Readiness

| 字段 | 值 |
|---|---|
| 前序 | `task_275e`, `task_275f`, runtime 接口 `task_275d` |
| 可并行 | 与 `task_275g` 执行并行；共享 reporter/CI 串行合并 |
| Freeze point | cold restore + purge matrix + immutable evidence + reviewer approve |
| Execute readiness | 非生产环境 ID、对象 allowlist、演练权限、CI artifact、reviewer 已具名 |
| 证据格式 | recovery/purge evidence-pack、三摘要链、reference/hold case、manifest SHA-256、不可变 run/log/audit URL 与 reviewer 签署 |
| Clarification owner/action | marketplace/制品平台 owner 提供隔离演练环境与已签 RTO/RPO；`CEOOrchestrator` 路由独立 reviewer，失败项回流 `275e/275f` owner |
| 未满足 Gate | owner 总签署与独立总复审 |

本 task 的“完成”可记录 pass 或 fail；只有全 pass evidence 才支持 Gate 复审。
