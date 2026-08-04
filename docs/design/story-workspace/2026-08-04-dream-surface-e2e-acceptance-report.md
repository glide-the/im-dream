# Dream Surface Task 6 端到端回归验收报告（含旧会话兼容性）

> 依据：`2026-08-03-dream-surface-execution-implementation-plan.md` Task 6 全节（Step 0–Step 5）+ Task 5 实施记录「给 Task 6 e2e 的验收要点」六条
> 日期：2026-08-04
> 环境：macOS（本机开发环境）；后端 `backend/server.py` 运行于 127.0.0.1:8765（启动于 02:18，晚于 Task 1 00:48 / Task 3 01:27 提交，openapi 实测含 `/api/story-workspace/runs/{id}/guidance`）；claude CLI 2.1.220（真实 CLI 回合）；前端 vite dev（用户既有实例，IPv6 loopback `localhost:5173`；为既有 spec 的 `127.0.0.1:5173` 硬编码临时另起 IPv4 实例，用后已停）；数据库 `backend/data/ink-and-memory.db`

## 一、Step 0（前置检查 E14）：digest 迁移核验 — 通过

防止旧库静默走无 surface 路径造成验收假阳性。实测（后端 venv 重算 + 直查 DB）：

| 检查点 | 结果 | 证据 |
|--------|------|------|
| 重算 digest | `sha256:77d77a10f4b2004de1cf87075b9ff9878fdc05dddaceb3c4fe689512f292b3ed` | `plugin_artifact_digest()` |
| `claude_plugin_installations` | ✅ 已是新值 | 行 `cpi_23b16de00cfb46a6a560ece9eeacf366`（package_name=ink-dream-story）digest 与重算一致 |
| `deck_runtime_plugin_locks.lock_json` | ✅ 已是新值 | 锁 `rpl_d19a954d181a558a82857e4911e1a865` 内 `builtin://ink-dream-story` 条目 digest 一致 |
| `deck_claude_plugin_refs` | 无需迁移 | 现存 2 行均为 `drama-forge@drama-studio`（非内置包），内置包 ref 由 e2e 经真实 PUT refs 端点按需创建 |
| 迁移脚本幂等 | ✅ | `scripts/migrate_ink_dream_story_digest.py` 重跑为 no-op（UPDATE 条件为新值不等） |

结论：**不存在旧库走无 surface 路径的假阳性前提**；e2e 第一性证据为真实 pack 产出 `.dream/`（见 Step 1），存在性本身即证明运行后端含 Task 1 代码。

## 二、逐步验收结果表

### Plan Task 6 Step 1：真实链路 pack → `.dream/` 物理映射 → 三处 surfaces 一致

| 验收点 | 方法 | 结果 | 证据 |
|--------|------|------|------|
| Deck 绑定含 dream surface 的制品 | 真实 API：注册新用户 → `GET /api/decks` → `GET /api/claude-plugins/installations`（发现 ready 安装）→ `PUT /api/decks/{id}/claude-plugins` | ✅ | e2e `dream-surface.spec.ts` beforeAll；refs 响应 digest = `sha256:77d77a10…` |
| 创建 thread → 首个 agent turn 触发 pack | 真实 API + **真实 claude CLI 回合**（`POST /api/claude-agent/threads` → `POST /api/claude-agent`，max_turns=3） | ✅ | e2e test 1，SSE 200 |
| `.dream/` 两文件物理映射 | Node 侧 FS 断言线程工作区 | ✅ | `.dream/workspace.json` 键集合精确等于 `{schema_version: dream-surface/v1, deck_id, plugins, entry_route}`；无 `workflow_run_id`；README 含「只读」「workflow_run_id」边界声明 |
| manifest/receipt/端点三处一致 | FS 读 `.ink/launch-manifest.json`、`.ink/plugin-pack-receipt.json` + `GET …/plugin-load-receipt` | ✅ | 三处 `surfaces` 均 `[{name:dream, protocol_dir:.dream, entry_route:/story-workspace/dream}]`；receipt `init_steps` 含 `materialize-surface` |
| 重 pack 字节一致（DEC-029） | 第二真实回合（frozen 分支）后比对字节 | ✅ | 两文件 bytes 逐一相等 |

### Plan Task 6 Step 2：Agent 产出 → 审阅面板 → 六态按钮走查

| 验收点 | 方法 | 结果 | 证据 |
|--------|------|------|------|
| Agent 输出故事产出 → 审阅面板打开 | 既有 `e2e/deck-dream.spec.ts`（mock SSE `story-workspace-output` + 真实后端）回归 | ✅ 通过 | 2 passed（与 claude-plugin-settings 一起） |
| 六态按钮走查（含 supersede 降级） | **seam 测试替代** | ⚠️ 集成替代 | `StoryWorkspaceSurfaceLinkButton.test.ts` 14 例（六态文案×目标路由、supersede 两种降级、显隐）全绿；**浏览器实测不可得**：Task 4 既定降级——服务端「提案↔run 聚合端点」缺位，两处挂载点无调用方注入，按钮在线上默认隐藏（安全缺省，DEC-028 同构）。本次 e2e 同时实测：Dream 页无任何 surface link 按钮渲染（test 4 step 3） |

### Plan Task 6 Step 3：confirmed → 执行页 → 指导 → 审计字段 + 无气泡

| 验收点 | 方法 | 结果 | 证据 |
|--------|------|------|------|
| 执行页直开渲染 continuing 态 | 浏览器直开 `/story-workspace/runs/<run>/execution`，run 来自真实后端 | ✅ | 面包屑/「执行中」徽章/「任务进度随执行实时更新」均渲染（快照证据） |
| 提交指导 → 202 | 侧边栏真实提交自由文本 | ✅ | 响应 202 `{review_action:guide, replayed:false, dispatched:true, request_id}` |
| 审计字段（chat_message.metadata）可见 | 真实 `GET …/messages` 断言 | ✅ | `metadata` 含 `kind/story_workspace_run_id/actor/request_id/idempotency_key/command_kind/text_summary/review_action=guide/command_fingerprint`；message id = `guide_swg_…` |
| 幂等：同键同内容 202 replayed | 真实端点重发 | ✅ | `replayed:true`，不重复落库 |
| 幂等：同键不同内容 409 | 真实端点 | ✅ | `IDEMPOTENCY_CONFLICT` |
| 非可指导状态 409 | pending_review run | ✅ | `WORKFLOW_RUN_NOT_GUIDABLE` |
| Chat 消息流无指导气泡 | 浏览器打开该 thread，DOM 断言 | ✅ | `[story-workspace guidance · run` 计数为 0，真实用户消息正常可见 |
| 指导历史（指令+状态+时间） | 侧边栏 DOM | ✅ | 「自由指导 / 第二集节奏放慢，保留雨夜电台主线 / 时间」条目 |

**Task 4 评审遗留第 3 条（guidance 是否应发给模型）——显式确认为设计行为，实测闭环**：

- 提交指导时线程空闲 → `dispatched:true`，服务端将指导作为**同 thread 新 user turn** 注入 runner（resume 既有 claude session）。
- DB 实测消息序列：`guide_swg_…`（user，18:54:54）→ assistant 回合（18:55:17）真实落库；assistant 推理逐字引用指导（"The user wants: 第二集节奏放慢，保留雨夜电台主线"）并产出符合指导的提案 JSON（《雨夜电台 · 第二集：慢下来的频率》）。
- 结论：**指导本应给 Agent 看**——这是 DEC-032 注入通道的设计语义；客户端侧 `prepareSendMessagesRequest` 只发送最后一条消息、且历史加载已按 `metadata.kind` 过滤，指导行不会经客户端历史回传，模型可见性完全由服务端新 turn 注入承载。记录备查。

### Plan Task 6 Step 4：旧会话兼容性（DEC-028）

| 验收点 | 方法 | 结果 | 证据 |
|--------|------|------|------|
| 无 deck thread → receipt 无 surfaces | 真实端点 | ✅ | `launch_manifest`/`receipt` 均无 `surfaces` 键（前端解析为 `undefined` → 隐藏入口） |
| 存量 pre-Task-1 工作区共存无 surface | FS 扫描 `backend/data/agent-workspace/`（1132 个） | ✅ | 抽验 ≥3 个含旧 launch-manifest（无 surfaces 键）的工作区，均无 `.dream/` 目录 |
| UI 壳无入口无报错 | 浏览器 Dream 页 | ✅ | 页面正常加载，六态按钮任一态计数为 0，无控制台级故障 |
| 行为与改动前一致 | 既有 e2e 回归 | ✅ | `deck-dream.spec.ts` + `claude-plugin-settings.spec.ts` 2 passed |

### Plan Task 6 Step 5：全量套件 + 制品校验

| 项 | 命令 | 结果 |
|----|------|------|
| 后端全量 | `backend/.venv/bin/python -m pytest backend/tests -q` | **754 passed, 1 skipped, 262 subtests passed**（44.33s） |
| 前端单元/seam | `npx playwright test src/ --reporter=line` | **59 passed**（含本 Task 新增 surfaces 原子失败 2 例后 backend 侧 19 passed + 6 subtests） |
| 类型检查 | `npx tsc -b` | exit 0 |
| 制品校验（Task 1 新增 profile） | `claude plugin validate plugins/ink-dream-story` | **✔ Validation passed** |
| 新 e2e | `npx playwright test e2e/dream-surface.spec.ts` | **4 passed** |
| 既有 e2e 回归 | `npx playwright test e2e/deck-dream.spec.ts e2e/claude-plugin-settings.spec.ts` | **2 passed** |

### Task 1 评审遗留：原子失败路径测试（已补，并入本 Task）

`backend/tests/test_workspace_init_surfaces.py` 新增 2 例（独立小改，随本 Task 提交并注明）：

- `test_materialize_write_failure_leaves_no_partial_dream`：mock `Path.write_text` 在 README 写入时抛 `OSError` → 整个物理映射失败，workspace 下既无 `.dream/` 也无 `.dream.tmp-*` 残留；
- `test_materialize_rebuilds_half_written_dream`：既有半截 `.dream/`（仅 README）被清除重建完整。

## 三、Task 5 验收要点六条对照

| # | 要点 | 结果 | 说明 |
|---|------|------|------|
| 1 | 路由直开 execution → story-workspace 视图；直开 episode review → Dream 工作区 + run 定位 | ✅（F-2 已修复） | 直开执行页落 story-workspace 视图、run 加载（test 3）；episode-review 直开渲染 Dream 工作区（test 4 step 2）；fresh-load `?run=` 定位在 dev StrictMode 下曾不生效（F-2，commit `dec5a92` 已修复），SPA 路径定位已实测（test 4 step 1） |
| 2 | 六态按钮 SPA 导航无整页刷新 + 四态执行页渲染 | ⚠️ 部分实测 | 执行页四态渲染由 seam 测试 + 本次 continuing 真实渲染承载；按钮点击 SPA 导航**浏览器不可测**（聚合端点缺位按钮默认隐藏，见 Step 2）；router `handleNavigate` 无刷新导航已由 Gate 重定向路径实测（无整页加载完成跳转） |
| 3 | Gate 重定向 + 可关闭提示 + run 定位 | ✅ | pending_review run 直开执行页 → URL 变 `/story-workspace/dream?run=<id>` + 「先完成审阅确认」提示条可关闭 + WorkflowContextBar 显示 run（test 4 step 1，全真实后端） |
| 4 | 指导闭环（202 / dispatched:false 文案 / 历史 / replayed / 无气泡） | ✅（dispatched:false 例外） | 202、历史、replayed、无气泡全真实通过；**`dispatched:false` 需线程 in-flight 回合，未真实构造**（后端单测 `test_guidance_dispatch_failure_still_accepted` 与侧边栏 seam 文案测试覆盖）；本次实测为 `dispatched:true` 并完成真实注入 |
| 5 | 降级态（无投影空态不报错；旧会话无入口无报错） | ✅ | 执行页「暂无步骤数据：执行事实投影尚未透出…」空态渲染非报错（真实）；旧会话见 Step 4 |
| 6 | query 保留（canonical 化 + SPA 导航） | ✅ | Gate 重定向后 `?run=` 完整保留于 URL（test 4 step 1 断言 URL 精确匹配） |

## 四、完整链路结论

**主链路真实贯通**：Deck 绑定（真实 API）→ thread 创建 → 首个 agent turn（真实 claude CLI 2.1.220）→ pack → `.dream/` 两文件物理映射（静态、无 run 级事实、重 pack 字节一致）→ launch-manifest / pack-receipt / `plugin-load-receipt` 端点三处 surfaces 一致透出 → 执行页真实渲染 → 指导提交（202/幂等/冲突/状态守卫全真实）→ 审计字段落 `chat_message.metadata` → 指导经服务端新 turn 真实注入执行 Agent 并获得遵循指导的 assistant 产出 → Chat 视图无指导气泡。

**旧会话兼容性结论**：无 surfaces 的会话/工作区在端点响应、文件系统、UI 三层均无 surface 痕迹，行为与改动前一致（DEC-028 成立）；既有 e2e 零回归。

## 五、假阳性排除（逐项给证据）

1. **E14 digest 前置**：第一节四处核验，旧库不存在「静默无 surface」前提；且 `.dream/` 的物理映射产物为存在性证据，不可能由无 Task 1 代码的进程产出。
2. **运行后端版本**：进程启动 02:18 晚于 Task 1（00:48）/Task 3（01:27）提交；openapi 实测列出 guidance 端点；真实 pack 产出 `.dream/`。
3. **DB 暂存的边界**：`stage_guidance_run.py` 仅替代「preflight 令牌仪式 + 工作流执行器推进 run 至 continuing/pending_review」这一段（真实执行需要完整 Deck 运行时，超出本回归可达层级）；暂存行的 id/哈希格式经 pydantic 合同全量校验（前两轮因格式不符 503 已修复并清理脏行），其后的 run read、guidance 端点、审计落库、前端执行页**全部走真实产品代码**，无任何 mock。
4. **指导闭环非自导自演**：guidance 提交、审计断言、气泡断言分属三个独立通道（REST 写 / REST 读 / 浏览器 DOM），且 assistant 真实产出内容逐字引用指导文本。
5. **遗留脏文件隔离**：`install_service.py`、`PluginReceiptBadge.tsx`、`i18n.ts`、`test_install_service_reinstall.py` 及多份 docs 改动为工作区既有 WIP，与本 Task 无关，未纳入提交；全量套件在含这些 WIP 的工作区通过，已如实记录环境。

## 六、新发现缺陷（已修复——修复记录见下）

- **F-1（真实产品缺陷，轻微）**：指导提交成功反馈（「指导已发送给执行 Agent。」/「已记录，待执行 Agent 拾取」）在线上**永不可见**——`StoryWorkspaceGuidanceSidebar.submit` 在同一 React 批次内 `setFeedback` 后立即 `onSubmitted → loadRun()`，`isLoading=true` 使执行页整体切换到加载分支、侧边栏卸载，反馈未能绘制。seam 测试 `describeStoryWorkspaceGuidanceResult` 锁定文案映射（单元层正确），但 live 页面只剩指导历史条目作为提交证据。
  - **修复记录（2026-08-04，commit `8510ddc`）**：页面分支判断移入 executionState 新 seam `resolveStoryWorkspaceExecutionPageView`，loading 分支仅首屏（无 run 时）进入；已有 run 的背景刷新（含指导提交后的 `onSubmitted → loadRun`）保持页面与侧边栏挂载，`setFeedback` 正常绘制。验证：`StoryWorkspaceExecutionPage.test.tsx` 新增「page view seam: refresh with a loaded run never re-enters loading (F-1)」用例（先红后绿）；全量 `npx playwright test src/` 63 passed；`npx tsc -b` 与 eslint 改动文件均 exit 0。
- **F-2（dev-only 缺陷）**：fresh-load（直接打开/刷新）`?run=` 深链定位在 React StrictMode 下静默失效——`useRunDeepLink` 的 resolve-once 游标在异步读取**之前**置位，StrictMode 挂载双效应（setup→cleanup→setup）使首次 fetch 回调 `cancelled`、第二次 setup 因游标已置位而早退。SPA 导航路径（效应更新而非挂载）不受影响；生产构建无双效应，预期不受影响。探针证据：直开 episode-review 深链时 run read 请求 200 返回合法 run，但 WorkflowContextBar 与提示条均不渲染。
  - **修复记录（2026-08-04，commit `dec5a92`）**：游标移入可测 seam `createRunDeepLinkResolveGate`，仅在 resolution 被应用后才闩锁（`markResolved`）；cleanup 中 `abort()` 重新打开 gate，StrictMode 第二次 setup 可正常完成 resolve。验证：`useRunDeepLink.test.ts` 新增 3 例（闩锁时机 / abort 后重开模拟 StrictMode 双效应 / reset），先红后绿；全量 63 passed；`npx tsc -b`、eslint 改动文件 exit 0；**生产构建冒烟 `npm run build` 通过**（`tsc -b && vite build` ✓ built in 443ms）。

## 七、遗留未实测项清单（集成替代/未实测）

| 项 | 状态 | 替代/原因 |
|----|------|-----------|
| run 真实创建与状态机推进（preflight → create_run → 执行器推进至 continuing） | **未实测** | 需完整 Deck 运行时执行；以 DB 暂存替代（边界见假阳性排除 3） |
| 六态按钮浏览器点击走查 + SPA 导航 + supersede 降级 UI | **集成替代** | 聚合端点缺位，按钮线上默认隐藏（Task 4 既定降级）；seam 14 例覆盖文案/路由/降级 |
| `dispatched:false`「已记录待拾取」真实触发 | **未实测** | 需线程 in-flight 回合；后端 `test_guidance_dispatch_failure_still_accepted` + 侧边栏文案 seam 覆盖 |
| `awaiting-guidance` 投影态 UI | **未实测** | 无 projection 端点（Task 5 既定降级）；无投影时安全缺省不出现，空态已实测 |
| Agent 真实产出 `story-workspace-output` → 审阅面板打开（产出侧） | **集成替代** | 既有 deck-dream.spec 以 mock SSE 驱动；本次 guidance 回合 assistant 真实产出提案 JSON 可作旁证，但面板打开链路未以真实产出驱动 |
| F-2 在生产构建的行为 | **已实测** | 修复 commit `dec5a92` 后 `npm run build`（含 `tsc -b`）通过；生产无双效应，行为不受 StrictMode 影响 |
| `retry-step` 指导（failed run）真实链路 | **集成替代** | 后端单测覆盖端点；前端 seam 覆盖 payload 构造；未在浏览器提交 |

## 八、Commit 范围

- `backend/tests/test_workspace_init_surfaces.py`（Task 1 评审遗留：原子失败 + 半截重建 2 例）
- `frontend/e2e/dream-surface.spec.ts`（本 Task e2e 主制品）
- `frontend/e2e/helpers/stage_guidance_run.py`（run 暂存辅助，边界见第五节 3）
- `docs/design/story-workspace/2026-08-04-dream-surface-e2e-acceptance-report.md`（本文件）
