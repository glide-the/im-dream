# task_202c_verify_frontend_story-workspace-browser-network-evidence.md

> **Task ID**: `task_202c_verify`
>
> **Domain**: `frontend`
>
> **类型**: `evidence-only verification`
>
> **优先级**: `P0`（来源业务 Issue）/ `high`（Task 定义 Issue）
>
> **Task 状态**: 合同已定义；Execute 尚未准入
>
> **唯一实现基线**: `task_202c` 既有产物，只读
>
> **正式执行报告**: `docs/exec/exec_task_202c_verify_story-workspace-browser-network-evidence.md`（仅由未来 `ExecTaskAgent` 新建）

---

## 1. 任务标题

**Story Workspace 三路由浏览器、交互与 Network 定向补证**

本 Task 只为 `task_202c` 的既有 Stories、Characters、Scenes 数据表实现补齐浏览器与 Network 证据，不重开、不覆盖、不顺手修订生产实现。

---

## 2. 关联 Issue 与权威输入

### 2.1 Issue 映射

| 关系 | Issue / Task | 状态与用途 |
|---|---|---|
| 当前 Task 定义 Issue | [SUO-307](/SUO/issues/SUO-307) | TaskDesignAgent 的唯一当前工作单；负责生成本文档 |
| 来源业务 Issue | `SUO-299-SH-002` | 来源 domain 为 `shared`；定义三路由浏览器与 Network 定向补证范围 |
| 既有实现 Issue / Task | `SUO-201-FE-003` / `task_202c` | 既有 frontend 实现基线，只读 |
| 历史执行 Issue | [SUO-277](/SUO/issues/SUO-277) | 已取消；其 Task/Exec 产物仅作历史证据，不得恢复 Issue 或复用 checkout |
| Stage parent | [SUO-301](/SUO/issues/SUO-301) | 定义 Direct Repair 严格串行队列与 Execute Gate |

来源 Issue 的 domain 为 `shared`，因为它承载跨运行时的补证需求；本 Task 的 domain 固定为 `frontend`，类型固定为 `evidence-only verification`，因为执行动作只验证浏览器 UI、交互及其列表 Network 合同。该映射不新增 frontend 实现责任。

### 2.2 权威输入

1. `docs/stage/stage_story-workspace.md` §13.1、§13.2、§13.5、§13.6。
2. `docs/task/task_202c_frontend_data-table-components.md`，既有实现合同，只读。
3. `docs/exec/exec_task_202c_story-workspace-data-table-components.md`，既有实现与静态验证证据，只读。
4. `docs/issue/ISSUES_story-workspace.md` §3.4 `SUO-299-SH-002`。
5. `docs/task/TASK-REQUIREMENT-FORMAT.md`，execute prompt 模板，只读；未来 execute Issue 必须单独复制并完整填充，本文档不预填 execute 模板。

如上述输入之间出现新冲突，未来执行者必须先在独立 execute Issue 评论中记录冲突、影响范围和 owner/action，并停止受影响的证据采集；不得自行选择较宽松口径。

---

## 3. 任务目标与范围

### 3.1 任务目标

在固定 1280px 桌面 viewport 下，只读使用当前 execute Issue execution workspace 的既有前后端运行时，为以下 canonical 路由建立可审计证据：

- `/story-workspace/stories`
- `/story-workspace/characters`
- `/story-workspace/scenes`

证据闭集只包括：

1. 三路由可识别页面与表格状态截图。
2. 三页搜索、审阅状态筛选、排序、分页交互；Stories 额外包含类型筛选。
3. pending / confirmed / rejected 状态样式、56px 行、hover、非 pending checkbox 禁用。
4. pending-only 选择与取消、批量栏替换常规 Toolbar 及恢复过程。
5. 三类列表请求的 Network URL、query 与 `{ data, pagination }` 响应结构。
6. 执行前后前后端生产代码内容 hash / diff 一致性证据。

### 3.2 明确不负责

- 不实现、不修复、不重构任何前端或后端代码。
- 不重复执行或包装 `task_202c` 已完成的 build、lint 或源码检查成果。
- 不调用 confirm、reject、archive、batch review 等审阅 API；pending 选择只验证 UI 状态。
- 不恢复 [SUO-277](/SUO/issues/SUO-277)，不使用其旧 checkout，不回滚 `task_205b` 或 `task_203`。
- 不创建 execute Issue、不安排 Stage、不把本文档视为 Execute 放行结论。

---

## 4. 验证执行步骤

### 4.1 前置 Gate

未来 `ExecTaskAgent` 开始前必须逐项确认：

1. 前置顺序严格为 `task_205b → task_203 → task_202c_verify`。
2. `task_205b` 与 `task_203` 的独立 execute Issue 均已为 `done`，对应执行锁已释放，无 merge / rollback 进行中。
3. `task_202c_verify` 已有独立 execute Issue、single assignee 与本次 checkout；不得借用 [SUO-301](/SUO/issues/SUO-301)、[SUO-307](/SUO/issues/SUO-307) 或 [SUO-277](/SUO/issues/SUO-277) 的 checkout。
4. 当前 execution workspace 的前后端运行时可稳定启动，且三条 canonical 路由可访问。
5. `PAPERCLIP_RUN_SCRATCH_DIR` 可用；浏览器 profile、会话、cache、临时日志和 hash manifest 只能写入该目录。

任一项未满足时不得进入 execute，必须记录实时状态和缺口并将 execute Issue 置为 `blocked`。

### 4.2 建立只读基线

1. 将 `git status --short` 原始结果保存到 run scratch，明确区分执行前已有 dirty diff 与本次动作。
2. 对 `backend/` 与 `frontend/src/` 中 Git 已跟踪及未忽略的现有文件生成排序后的路径清单和 SHA-256 manifest，保存到 run scratch。
3. 记录运行时启动方式、commit / workspace 标识、viewport 宽高、device pixel ratio、浏览器版本和证据采集时间。
4. 不得暂存、还原、格式化、清理或覆盖工作树中任何既有修改；尤其不得接触 `backend/database.py` 的既有 diff。

### 4.3 启动运行时与浏览器

1. 仅使用 execution workspace 已有命令、依赖和配置启动前后端；不得安装依赖、修改配置或生成仓库内文件。
2. 浏览器 viewport 宽度固定为 `1280` CSS px；高度与 DPR 必须记录并在三路由间保持一致。
3. 浏览器会话和临时网络层响应只能存在于 run scratch / 浏览器会话。若为了补齐视觉状态使用会话内临时响应，证据必须标为 synthetic visual evidence；它不能替代真实列表 endpoint 的 Network 请求/响应证据。

### 4.4 三路由截图与交互矩阵

每次交互必须保留可关联到路由、操作和时间点的截图或浏览器操作记录；搜索与筛选需保留操作前后状态。

| 路由 | 必验交互 | 最小浏览器证据 |
|---|---|---|
| `/story-workspace/stories` | 搜索、审阅状态筛选、Stories 类型筛选、排序、下一页或可用分页动作、返回/切换页 | 初始表格截图；每类交互后的页面状态；分页状态；路由与 viewport 元数据 |
| `/story-workspace/characters` | 搜索、审阅状态筛选、排序、下一页或可用分页动作、返回/切换页 | 初始表格截图；每类交互后的页面状态；分页状态；路由与 viewport 元数据 |
| `/story-workspace/scenes` | 搜索、审阅状态筛选、排序、下一页或可用分页动作、返回/切换页 | 初始表格截图；每类交互后的页面状态；分页状态；路由与 viewport 元数据 |

若数据量不足以产生第二页，必须保留分页控件及真实返回的 `pagination` 证据，记录“无第二页”的可复现输入；不得伪造通过或修改 fixture。

### 4.5 状态样式与 pending-only 选择

1. 使用页面实际可见的 pending / confirmed / rejected 数据，分别保存状态样式证据。
2. 在浏览器中测量并记录代表行的渲染高度为 56px；源码或 CSS 文本扫描不算证据。
3. 对代表行执行 hover，保留 hover 前后状态。
4. 证明 confirmed 与 rejected 行的 checkbox 不可选择；保留 disabled 状态及实际尝试结果。
5. 选择 pending 行，保留批量栏替换常规 Toolbar 的截图；执行取消，保留常规 Toolbar 恢复与选择清空的截图。
6. 同步检查 Network，证明上述选择 / 取消过程没有发出任何审阅写请求。

如果现有运行时缺少某个必需状态的数据，可使用仅存在于浏览器会话的临时响应补充视觉/交互证据，并清楚标注；不得将其用于证明真实 API 响应合同，也不得把 mock、fixture 或快照写入仓库。

### 4.6 Network 请求与响应

对三个列表 endpoint 分别保存 request URL、method、query、status 和 response JSON 顶层结构。交互证据与 Network 条目必须可互相定位。

| Endpoint | 必须由交互产生的 query | 响应合同 |
|---|---|---|
| `/api/story-workspace/stories` | `q`、`review_status`、`type`、`sort`、`order`、`page`、`per_page` | 顶层保持 `{ data, pagination }` |
| `/api/story-workspace/characters` | `q`、`review_status`、`sort`、`order`、`page`、`per_page` | 顶层保持 `{ data, pagination }` |
| `/api/story-workspace/scenes` | `q`、`review_status`、`sort`、`order`、`page`、`per_page` | 顶层保持 `{ data, pagination }` |

要求：

- 证据必须来自浏览器 Network 观察；禁止用源码扫描、build、lint 或仅引用旧 Exec 报告替代。
- 可分多条请求覆盖 query 参数，但报告必须给出“交互 → request → response → AC”的索引。
- 响应证据需显示 `data` 与 `pagination` 两个顶层 key 及足以证明结构未迁移的字段形状；敏感值、认证 token 和个人数据应脱敏，但不得抹去合同 key。
- 搜索、筛选、排序或分页若未触发预期请求，视为真实缺陷候选，按 §11.2 处理，不得在本 Task 中修复。

### 4.7 零生产代码 diff 与报告闭合

1. 重新生成 `backend/` 与 `frontend/src/` 的排序路径清单和 SHA-256 manifest，与 §4.2 基线逐项比较；路径集合与内容 hash 必须完全一致。
2. 再次记录 `git status --short`，与基线对比。除未来执行报告 `docs/exec/exec_task_202c_verify_story-workspace-browser-network-evidence.md` 外，不得出现本次新增或改变的仓库路径。
3. 把浏览器、交互、Network、hash/diff 和未验证项逐项映射到 `AC-202C-V-01`～`AC-202C-V-06`。
4. 证据文件作为 execute Issue 附件上传；仓库内不得新增截图、HAR、cache、日志或临时报告。

---

## 5. 涉及文件路径与写入边界

### 5.1 本文档的边界

本文档是 [SUO-307](/SUO/issues/SUO-307) 唯一允许新增的仓库文件。未来 execute 必须将本文档视为只读输入。

### 5.2 未来 Execute Allowed（完整闭集）

| 路径 / 对象 | 动作 | 允许内容 |
|---|---|---|
| 当前 execute Issue execution workspace | 只读启动 / 访问 | 使用既有前后端运行时，不修改仓库 |
| `$PAPERCLIP_RUN_SCRATCH_DIR/**` | 临时新建 / 修改 | 浏览器 profile、session、cache、临时日志、hash manifest；run 结束后可丢弃 |
| 当前 execute Issue 附件 | 新增 | 截图、交互记录、Network 请求/响应、必要的脱敏导出 |
| `docs/exec/exec_task_202c_verify_story-workspace-browser-network-evidence.md` | 唯一仓库新增 | 正式验证报告；仅由 `ExecTaskAgent` 写入 |

### 5.3 Future Execute Forbidden（完整闭集）

- 除 §5.2 的未来 exec report 外，禁止修改任何仓库文件。
- 禁止修改全部前后端生产代码，尤其是 `task_202c` 表格、Hooks、页面、合同文件、router、App 与 `backend/database.py`。
- 禁止修改 Schema、DDL、migration、SQL、测试、仓库内 mock / fixture / 快照、测试 runner、依赖、lockfile、运行配置、部署配置和生成物。
- 禁止修改 `docs/design/**`、`docs/issue/**`、`docs/task/**`、`docs/stage/**` 及其他既有 `docs/exec/**`。
- 禁止以补证名义修复缺陷、顺手重构、扩大范围、恢复 [SUO-277](/SUO/issues/SUO-277) 或回滚 `task_205b` / `task_203`。
- 未列入 Allowed 的路径和动作默认禁止；不得通过复制、移动、重命名、符号链接或扩大 glob 绕过闭集。

---

## 6. 输入 / 输出说明

### 6.1 输入

- 已完成的 `task_205b` 与 `task_203` 冻结基线及其 exec 结论。
- `task_202c` 既有 Task、实现和静态 Exec 证据。
- 当前 execute Issue execution workspace 的既有前后端运行时。
- 能覆盖 pending / confirmed / rejected 与分页、筛选场景的实际数据；仅视觉缺态时允许浏览器会话内临时响应并显式标注。

### 6.2 输出

- 三条 canonical 路由的 1280px 截图证据。
- 搜索、筛选、排序、分页、pending-only 选择 / 取消的交互记录。
- 三类列表 endpoint 的 request / query / response shape 证据。
- 执行前后生产路径清单、hash manifest 和仓库状态对比摘要。
- execute Issue 附件索引。
- 正式报告 `docs/exec/exec_task_202c_verify_story-workspace-browser-network-evidence.md`，逐项映射六项验收条件、缺口、复现、回滚和最终 disposition。

### 6.3 非输出

- 任何实现代码、测试代码、fixture、mock、快照、依赖或配置变更。
- 新的产品能力、REST 字段、Schema、数据库迁移或审阅操作结果。
- build / lint / 源码扫描的重复结果，除非仅作为背景且明确不充当浏览器验收证据。

---

## 7. 依赖项与 Stage Readiness

### 7.1 严格依赖顺序

```text
task_205b → task_203 → task_202c_verify
```

- `task_205b` 未完成或未释放锁：`task_203` 与 `task_202c_verify` 均不得 checkout。
- `task_203` 未完成或未释放锁：`task_202c_verify` 不得 checkout。
- 任一前序进入 rollback、重新执行或失败：`task_202c_verify` 保持 `blocked`，直至前序重新通过 Gate。
- 该串行顺序用于避免在合同迁移中或审阅路由变化中的运行时采集失真证据，即使本 Task 本身不写共享路由也不得并行。

### 7.2 Execute Readiness

| Gate | 本 Task 文档完成时 | 未来 Execute 放行要求 |
|---|---|---|
| 独立 Task 文档 | `PASS` | 本文档存在且保持只读 |
| `task_205b` 冻结 | 待 execute 前实时核验 | execute Issue `done`、证据齐全、锁释放 |
| `task_203` 冻结 | 待 execute 前实时核验 | execute Issue `done`、证据齐全、锁释放 |
| 独立 execute Issue / checkout | 尚不由本 Task 定义 Issue创建 | single assignee、独立 checkout，不复用历史锁 |
| 运行时稳定 | 待 execute 前实时核验 | 三路由和对应 REST 列表端点可访问 |
| Evidence-only 边界 | `PASS` | execute 全程保持，生产代码零 diff |

**当前 Stage readiness：`BLOCKED / NOT READY FOR EXECUTE`。** 本文档只补齐 Stage §13.6 的“独立 Task 产物”缺口，不代表前序状态、execute Issue、checkout 或运行时 Gate 已满足，也不授权提前 @mention / 指派 `ExecTaskAgent`。

---

## 8. 验收条件

以下 `AC-202C-V-01`～`AC-202C-V-06` 原样固化自 `docs/stage/stage_story-workspace.md` §13.5，不得删除、改写或降级：

- `AC-202C-V-01`：三条 canonical 路由各有可识别路由与表格状态的 1280px 截图。
- `AC-202C-V-02`：三页均完成搜索、审阅状态筛选、排序、分页；Stories 额外完成类型筛选。
- `AC-202C-V-03`：pending / confirmed / rejected 样式、56px 行、hover、非 pending checkbox 禁用均有交互证据。
- `AC-202C-V-04`：pending 选择后批量栏替换常规 Toolbar，取消后恢复；不调用审阅 API。
- `AC-202C-V-05`：Network 证明请求命中三类 `/api/story-workspace/*` 列表端点并产生 `q`、`review_status`、`sort`、`order`、`page`、`per_page`，Stories 另含 `type`；响应保持 `{ data, pagination }`。
- `AC-202C-V-06`：生产代码零 diff；报告逐项映射证据、未验证项、复现信息与 evidence-only 回滚建议。

### 8.1 验收—证据映射

| 验收 ID | 必需证据 | 通过标准 |
|---|---|---|
| `AC-202C-V-01` | 三路由初始状态截图 + route / viewport 元数据 | 三页各至少一份可识别路由与表格状态的 1280px 证据 |
| `AC-202C-V-02` | 三页交互前后截图/记录；Stories 类型筛选记录 | 所有指定交互均实际执行且页面状态变化可追溯 |
| `AC-202C-V-03` | 三状态截图、浏览器行高测量、hover 前后、disabled checkbox 尝试 | 六类视觉/交互检查全部有浏览器证据 |
| `AC-202C-V-04` | pending 选择、批量栏、取消恢复截图；同期 Network 记录 | UI 替换/恢复成立且无审阅写请求 |
| `AC-202C-V-05` | 三 endpoint 的 URL/query/status/response shape；交互关联索引 | 参数覆盖完整，响应顶层保持 `{ data, pagination }` |
| `AC-202C-V-06` | before/after path + hash manifest、status 对比、报告证据矩阵 | 生产路径集合与内容完全一致，仓库新增仅为允许的 exec report |

任一 AC 缺少证据时不得宣称整体完成或将 execute Issue 标记 `done`。

---

## 9. 测试与验证策略

| 层级 | 方法 | 覆盖范围 | 通过标准 |
|---|---|---|---|
| 源码扫描 / build / lint | `N/A`，禁止作为替代证据 | 不适用 | 不运行也不重复包装旧结果；不得据此宣称 AC 通过 |
| 单元测试 | `N/A` | evidence-only，禁止新增/修改测试 | 仓库测试零改动 |
| 浏览器路由 | 固定 1280px viewport 访问三条 canonical 路由并截图 | `AC-202C-V-01` | 三路由证据齐全且元数据一致 |
| 浏览器交互 | 搜索、状态筛选、排序、分页、Stories 类型筛选、pending-only 选择/取消 | `AC-202C-V-02`～`04` | 每项有操作前后状态，禁止项确实不可用 |
| Network | 浏览器 Network 观察 request / query / response | `AC-202C-V-04`～`05` | 三 endpoint、全部 query 与 response shape 可核验；选择/取消无审阅写请求 |
| 零写入检查 | 前后生产路径清单 + SHA-256 manifest + `git status --short` 对比 | `AC-202C-V-06` | 生产路径/内容不变；只新增允许的 exec report |

验证失败必须记录：route、viewport、数据前置、操作序列、期望、实际、Network 条目、截图/附件索引和首次失败时间。禁止用“源码看起来正确”替代失败证据。

---

## 10. 完成标志

- [ ] `task_205b` 与 `task_203` 均已 `done` 且释放锁，独立 execute Issue / checkout 就绪。
- [ ] 已记录 execution workspace、运行时、浏览器、1280px viewport 与执行前 dirty baseline。
- [ ] `/story-workspace/stories`、`/story-workspace/characters`、`/story-workspace/scenes` 均有初始截图。
- [ ] 三页搜索、审阅状态筛选、排序、分页均有证据；Stories 类型筛选有证据。
- [ ] pending / confirmed / rejected 样式、56px 行、hover、非 pending checkbox 禁用均有证据。
- [ ] pending 选择后批量栏替换常规 Toolbar，取消后恢复，且未调用审阅 API。
- [ ] 三类列表 endpoint 的全部必需 query 与 `{ data, pagination }` 响应结构均有 Network 证据。
- [ ] 执行前后前后端生产路径与 SHA-256 manifest 完全一致。
- [ ] 仓库差异仅新增正式 exec report；截图、HAR、会话与 cache 均未写入仓库。
- [ ] 正式 exec report 逐项映射 `AC-202C-V-01`～`AC-202C-V-06`、未验证项、复现信息与回滚建议。
- [ ] 六项 AC 全部通过后，未来 execute Issue 才可标记 `done`。

---

## 11. 风险提示、阻塞与回滚

### 11.1 风险提示

| 风险 | 影响 | 处理方式 |
|---|---|---|
| 前序 task 未冻结或锁未释放 | 运行时基线可能变化，证据失真 | execute Issue `blocked`，等待 `task_205b` / `task_203` owner 完成并释放锁 |
| 浏览器控制或运行时不可用 | 无法形成硬性浏览器 / Network 证据 | 记录工具/服务错误与 owner/action，`blocked`；不得用 build/lint替代 |
| 数据不足以覆盖状态或分页 | 部分视觉/交互 AC 缺证据 | 记录数据缺口；视觉状态可用浏览器会话内临时响应且显式标注，真实 Network 合同仍必须由实际 endpoint 证明 |
| 交互触发错误 query、响应 shape 变化或页面异常 | 发现真实产品缺陷 | 按 §11.2 记录复现并 `blocked`，另拆修复 Issue |
| 执行期间出现仓库或生产 hash 变化 | evidence-only 边界被破坏或存在并发写入 | 立即停止，记录 before/after 与冲突 owner，不静默覆盖 |
| Network 证据包含敏感值 | 附件泄露风险 | 仅脱敏值，保留 method、path、query key、status 与 response key 供核验 |

### 11.2 真实缺陷处理

发现真实缺陷时，本验证单只能：

1. 记录最小可复现步骤、期望/实际结果、截图与 Network 证据。
2. 将未来 execute Issue 标记 `blocked`，明确修复 owner 与动作。
3. 另行拆分修复 Issue；修复完成并重新通过前序 Gate 后再重新采集受影响证据。

本验证单不得直接修改代码、测试、mock、fixture、配置、Schema 或依赖。

### 11.3 回滚策略

- 无生产代码回滚项。
- 错误、过期或不完整证据只能标记为废弃 / superseded，并重新采集对应截图、交互或 Network 证据。
- 正式报告中的错误区段只由 `ExecTaskAgent` 在当前 execute Issue 边界内修正；不得改写既有 `task_202c` Task/Exec、前序 Task/Exec 或 Stage 结论。
- 不得恢复旧合同路径、回滚 `task_205b` / `task_203` 或恢复 [SUO-277](/SUO/issues/SUO-277)。

---

## 12. 下游执行提示

未来 execute Issue 必须先复制并完整填充 `docs/task/TASK-REQUIREMENT-FORMAT.md`，把本文档的依赖、Allowed、Forbidden、六项 AC、浏览器 / Network 验证与回滚闭集原样带入。该 filled prompt 应属于 execute Issue 的 run scratch 或治理产物，不得覆盖模板源文件。

本文档完成只解决“缺少独立 `task_202c_verify` Task 产物”的 Task-stage 缺口；后续由 `CEOOrchestrator` 建立独立 execute Issue 与一等 blocker 串行边，并仅在全部 Gate 满足后唤醒 `ExecTaskAgent`。
