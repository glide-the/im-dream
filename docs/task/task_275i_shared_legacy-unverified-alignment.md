# task_275i_shared_legacy-unverified-alignment

> Task ID: `task_275i`
> Source Issue: `DECK-SC-009`
> Paperclip Issue: [SUO-275](/SUO/issues/SUO-275)
> Domain / Priority: `shared` / `P1`

## 1. 任务标题

旧假设扫描、`legacy_unverified` 生产阻断与跨端对齐

## 2. 关联 Issue

| 关联 | 内容 |
|---|---|
| 来源条目 | `DECK-SC-009` |
| Task-stage Issue | [SUO-275](/SUO/issues/SUO-275) |
| 来源编排 | [SUO-258](/SUO/issues/SUO-258) |
| Design | `docs/design/deck/design_002_deck-plugin-decision-gates.md` §4.2.4、§8 |
| 旧 Issue 清单 | `docs/issue/ISSUES_deck-plugin-voice-ink-dream-integration.md` 的 `DECK-017` |
| Domain / Priority / 标签 | `shared` / P1 / `supply-chain`, `legacy`, `migration`, `alignment` |

## 3. 任务目标

扫描当前开放文档与代码中的可变标签、digest 占位、缺失摘要和无签名 production-ready 旧假设，形成可复核迁移台账，并在后端建立权威 `legacy_unverified` 状态与 production-ready/preflight/run 拒绝，在管理 UI 显示明确警告和禁用生产选择。开发/测试/历史只读路径必须显式，不能静默扩张。

默认扫描当前开放文档与代码；已关闭历史产物只登记引用，不强制反写。若 board 要求全历史改写，CEOOrchestrator 必须创建增量 Issue。

### 3.1 shared 边界

| 边界 | 责任 |
|---|---|
| Frontend | 展示 `legacy_unverified`、生产选择禁用、原因和迁移/owner 指引；不自行判定 verification |
| Backend | 权威状态、环境/用途校验、production-ready/preflight/run 拒绝和审计 |
| 联调 | API 状态/reason code 与 UI 标签、禁用动作、历史只读路径一致 |
| 验收 | 扫描台账完整，跨端不能绕过；上游旧 Issue 备注由 IssueDispatcher owner 处理 |

## 4. 实现步骤

1. 扫描 `docs/task/`、`docs/stage/`、`docs/exec/`、backend、frontend 和配置中：
   - `"latest"`、分支或可变 marketplace 标签；
   - release/lock 缺 `artifact_digest`；
   - “sha256 占位”/`TODO` 摘要；
   - 无签名/未知 verification 却标 production-ready；
   - UI 只显示“已下载/已安装”却暗示可信。
2. 输出 inventory；每条含 path/line、owner、当前语义、风险和分类：
   - `legacy_unverified`：仅开发/测试/历史只读；
   - `updated`：已符合 `DECK-GATE-DEC-017`，附 Issue/commit；
   - `deprecated`：废弃并给迁移路径。
3. 后端：
   - 在 release/lock API 模型中显式返回 verification state/reason；
   - 无签名历史制品迁移为 `legacy_unverified`，不伪造 digest/signature；
   - production-ready/preflight/run 请求返回 `ARTIFACT_VERIFICATION_REQUIRED`；
   - 只允许策略显式的 dev/test 或历史只读，写审计。
4. 前端：
   - 管理 UI 展示不可混淆的 `legacy_unverified` badge/warning；
   - production 环境禁用选择/运行并展示 reason/owner/迁移入口；
   - 历史详情可只读，不提供“信任此制品”绕过。
5. 联调验证浏览器请求无法篡改 environment/use case 绕过服务端；UI 与 API 的 reason code/status 唯一映射。
6. 对旧 `DECK-017` 备注的更新不得由本 shared execute task 越权改写 `docs/issue/`。若仍未对齐，在执行 Issue 评论中 @mention IssueDispatcher/CEOOrchestrator，并以一等 follow-up 产物记录；该外部缺口不被本 task 静默标为完成。
7. 对关闭历史产物只保存 inventory 引用和 hash；不批量重写历史证据。
8. 生成跨端测试、扫描复核和可点击 inventory 报告。

## 5. 涉及文件路径

| 路径 / 资源 | 动作 | 最小变更 |
|---|---|---|
| `backend/models/deck_plugin.py` | 修改 | 增加/传播 `legacy_unverified` verification state |
| `backend/services/deck_plugin/release_service.py` | 修改 | 历史状态迁移与不可伪造规则 |
| `backend/services/deck_plugin/compatibility_service.py` | 修改 | production/preflight 资格 fail-closed |
| `backend/routers/deck_plugins.py` | 新建 | 只暴露权威 verification 状态/拒绝 |
| `backend/server.py` | 修改 | 仅注册 deck plugin router |
| `backend/tests/test_deck_plugin_legacy_unverified.py` | 新建 | 环境、用途、API 与绕过测试 |
| `frontend/src/api/deckPluginApi.ts` | 新建 | 结构化 verification 状态/reason API |
| `frontend/src/components/deck-plugin/ArtifactVerificationBadge.tsx` | 新建 | 精确 verification badge |
| `frontend/src/components/deck-plugin/LegacyUnverifiedWarning.tsx` | 新建 | 警告、禁用和迁移指引 |
| `frontend/src/components/deck-plugin/__tests__/legacy-unverified.contract.tsx` | 条件新建 | 仅在已有前端测试 harness 可用时加入 |
| `${CI_ARTIFACT_DIR}/deck-plugin-stage4/legacy/alignment-inventory.json` | 运行时生成 | 扫描台账与 source hash |
| 当前执行 Issue 评论/附件 | 新建 | inventory 链接与 IssueDispatcher 外部对齐记录 |

`docs/task/`、`docs/stage/`、`docs/exec/` 在扫描时只读；发现旧假设应分别回流其 owner 的增量 Issue，不得由单个 execute task 批量跨阶段改写。

## 6. 输入 / 输出说明

### 输入

- `task_275c` 的权威 verification 结果；
- release/lock/environment/use case；
- 当前开放文档/代码扫描结果；
- 后端错误码与前端展示映射。

### 输出

- `verification_state = verified|legacy_unverified|failed|expired|revoked|quarantined`；
- `ARTIFACT_VERIFICATION_REQUIRED` 与脱敏 reason/action；
- inventory JSON：path/line/source hash/classification/owner/action/Issue/commit；
- UI badge、禁用行为、迁移/owner 指引和联调证据。

## 7. 依赖项、可并行性与冻结点

- 直接依赖：`task_275c`。
- 可在 `task_275f/275g` 后续工作期间并行；与 backend release/model 共享文件时 Stage 必须基于 `275c` 后串行合并。
- 旧 `DECK-017` 备注的 owner/action：CEOOrchestrator 路由 IssueDispatcher 创建/完成最小 follow-up；不形成 execute 对上游文档的反向写入授权。
- 前端测试 harness 当前需 Stage 验证；若不存在，必须安排独立 bootstrap 或批准可追溯 agent-browser 验证，不得在本 task 临时扩大依赖。
- Freeze point：服务端权威拒绝、UI 禁用、inventory 无未分类开放命中、外部 issue-stage 对齐记录存在。

## 8. 测试策略

后端最小命令：`python -m unittest backend.tests.test_deck_plugin_legacy_unverified`

静态/前端最小检查：

```text
rg -n -i '"latest"|sha256.*(placeholder|todo)|legacy_unverified|production_ready|artifact_digest' docs/task docs/stage docs/exec backend frontend
npm --prefix frontend run lint
```

| 场景 | 通过标准 |
|---|---|
| legacy + production-ready/preflight/run | 服务端 `ARTIFACT_VERIFICATION_REQUIRED` |
| legacy + dev/test | 仅显式策略允许，并有审计/警告 |
| legacy + 历史详情 | 只读可见，不可触发新执行 |
| 篡改前端 environment/use case | 服务端仍拒绝 |
| UI | badge/warning/禁用/reason/迁移指引准确 |
| inventory | 所有开放命中均分类、有 owner/action；历史只登记 |

若无前端测试 harness，使用经 Stage 批准的 agent-browser 场景并保存请求、响应、关键截图和时间；不得把 lint 当 UI 行为测试。

## 9. 完成标志

- [ ] 当前开放文档、代码与配置完成扫描并生成 source-hashed inventory。
- [ ] 每条命中分类为 `legacy_unverified|updated|deprecated`，无未分类项。
- [ ] 历史无签名制品不伪造摘要/签名，显式为 legacy。
- [ ] production-ready/preflight/run 服务端拒绝并审计。
- [ ] dev/test/历史只读路径显式且最小化。
- [ ] UI 显示明确警告并禁止生产选择/执行。
- [ ] 跨端绕过、API 错误和 UI 映射验证完成。
- [ ] 旧 `DECK-017` 对齐已由 IssueDispatcher 产物或显式外部 blocker 记录。

## 10. 风险提示与回滚

| 风险 | 处理 / 回滚 |
|---|---|
| 扫描命中多但误改历史 | 当前开放范围强制；关闭历史只登记 |
| UI 禁用但 API 可绕过 | 服务端为唯一权威，测试直接调用 API |
| 把 legacy 当可人工信任 | 不提供 bypass；必须重新发布并通过完整验证 |
| 全仓修订吞并其他阶段 owner | inventory + 一等 follow-up，不跨阶段批量写 |

回滚前端仅可隐藏入口但服务端拒绝必须保留；回滚后端时 production Gate 必须全局关闭，不能恢复 legacy 生产运行。

## 11. 允许 / 禁止修改范围

- 允许：§5 精确 backend/frontend/测试路径、运行时 inventory 与 Issue 证据。
- 禁止：`docs/design/`、`docs/issue/`、`docs/task/`、`docs/stage/`、`docs/exec/` 的直接 execute 写入；未列出的源码、依赖锁、部署配置。
- 扫描权限不等于写权限；关闭历史产物一律只读。

## 12. StagePlanner / Execute Readiness

| 字段 | 值 |
|---|---|
| 前序 | `task_275c` |
| 可并行 | 与 `275f/275g`；共享 release/model 路径在 `275c` 后串行 |
| Freeze point | backend deny + frontend disable + classified inventory + issue-stage owner record |
| Execute readiness | API owner/route、管理 UI 宿主、环境策略、测试 harness/agent-browser 方案明确 |
| 证据格式 | source-hashed inventory JSON、后端测试报告、前端 contract/E2E 请求响应与截图、外部 Issue 对齐链接 |
| Clarification owner/action | `CEOOrchestrator` 路由 IssueDispatcher 完成旧 `DECK-017` 对齐；`StagePlanner` 确认前端 harness 或排入可追溯 agent-browser 验证 |
| 未满足 Gate | 其他实现/演练、三方 owner、独立 reviewer 与总复审 |

本 task 完成不等于 Stage 4 production Gate approve。
