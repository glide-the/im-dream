# Dream 三合同 E2E 需求追踪与发布门禁

日期：2026-08-11
状态：本地与隔离环境验收完成；真实收费 Provider canary 未获授权
范围：Dream 剧本生产链涉及的订阅计费、模型 Gateway、Workflow/Agent、Episode Artifact 与 Admin 只读 Story 交互。本文不把 Mock、单接口 200 或截图单独作为业务完成证据。

## 1. 证据等级与真值

- `proved`：当前生产等价实现有直接自动化断言；跨服务结果另有隔离 PostgreSQL、零收费 Provider 和真实 Chromium 证据。
- `externally-gated`：设计要求依赖真实收费外部 Provider，且本轮没有授权；本地替身只证明协议和平台结算边界。
- Subscription / Plan Version / Entitlement / Allowance / Gateway route / Token Ledger：Admin PostgreSQL 与 Admin 服务。
- platform model preference / Workflow Run / Agent message / Dream Files / Episode binding、actions、Story Index：Dream PostgreSQL 与对应服务。
- 剧本 bytes：Run 隔离 Artifact Root；浏览器仅拥有展示缓存、focus 与 last-good。

## 2. 需求—实现—测试双向追踪

| ID | 设计要求 / 用户结果 | 真值所有者与实现 | 直接证据 | 状态 |
|---|---|---|---|---|
| SUB-01 | canonical user 与 platform projection、Billing Account 一对一；浏览器不可覆盖 subject | Dream auth、Admin projection trigger、Product BFF | 隔离 Subscription E2E 断言 2 users = 2 projections = 2 accounts；`test_product_bff_routes.py` 校验 PostgreSQL actor 是唯一 subject | proved |
| SUB-02 | Plan/Version/Entitlement 由 Admin 拥有；published snapshot 不可变 | Admin Subscription service/PostgreSQL | `subscription-billing-postgres.spec.ts` 断言发布后的 Version 和 Entitlement 写入均为 409 | proved |
| SUB-03 | Product catalog 由 Admin 返回且 Dream 不补本地套餐/顺序 | Product API → Dream BFF → Subscription UI | Dream strict DTO/source tests 与 Subscription Mock Chromium；非法字段/数量/顺序 fail closed | proved |
| SUB-04 | preview/execute、`expectedVersion`、`Idempotency-Key`；同 payload replay、漂移 409 | Product command service/Event | Dream BFF source tests；隔离 Subscription E2E 覆盖 lifecycle、replay、payload/version conflict | proved |
| SUB-05 | `granted = remaining + reserved + consumed`，Ledger append-only | Admin Allowance/Token Ledger | 当前隔离 Subscription Chromium：4 requests、6 ledger entries、0 conservation mismatch、reserved=0；Dream 主链另有 32 次守恒 | proved |
| SUB-06 | Allowance exhausted 返回 402，不用 cash fallback，不调用 Provider | Admin Gateway + Dream safe error contract | 隔离 Subscription Chromium 断言 402、Provider 计数不变、现金余额/账本不变；Dream launch 402 precheck 不创建 Run/message | proved |
| SUB-07 | 新用户 Free/projection/account 同事务；配置缺失回滚、backfill 幂等 | Admin PostgreSQL provision/migrations | Admin migration/service tests与一次性数据库 canonical projection 断言 | proved |
| MOD-01 | enabled alias 可见；callable/availability/reason 由实时资格决定 | Admin `/v1/models` | Admin model evaluator tests、Dream strict catalog tests、真实 BFF alias 浏览器；locked model 不可选 | proved |
| MOD-02 | 公共 Model DTO strict allowlist；危险 capability/route 字段导致 502 | Admin public DTO + Dream parser | `test_admin_gateway_models.py` 覆盖 capability allowlist、重复 alias 和未知字段 | proved |
| MOD-03 | 浏览器只保存 platform alias；live validation；stale/locked 不 fallback | Dream system config + server resolver | Mock Chromium 保存体仅 `{model}`；真实 PG BFF 保存/移动恢复；空目录测试断言 0 radio、0 PUT；403/409 focused tests | proved |
| MOD-04 | 每个新 Agent turn 由服务端重新解析已保存 alias，客户端不可覆盖 | shared model selection + launch/message/confirmation/guidance | selection/service focused tests；真实链请求 `dream-fast`，Gateway 唯一 upstream 为 `dream-producer-upstream-fast` | proved |
| MOD-05 | reserve 与 Provider I/O、settlement 分事务；成功 capture 并 release remainder | Admin Gateway/Ledger | Admin unit + 隔离 PG；完整 Dream 链 32 reserve/capture/release 且全部 settled | proved |
| MOD-06 | missing usage、流中断、进程崩溃进入有界 reconciliation，不永久悬挂 | proxy state machine + settlement worker/internal route | 当前 Admin `proxy-handler`、`settlement-worker`、internal settlement 定向 Vitest 覆盖 missing usage、post-first-byte interruption、abort/watchdog；63/63 定向通过 | proved |
| MOD-07 | 401/402/403/409/429/502/503 与 SSE error 保真且脱敏 | Dream launch/BFF、Gateway safe envelope、UI | Dream launch 7 个 status subtests均断言无 Run/message/dispatch；Product BFF/UI 状态矩阵；真实浏览器 diagnostics 为 0 | proved |
| MOD-08 | 真实收费 Provider usage 与平台账本一致 | 外部 Provider | 本轮明确禁止未授权收费调用；外部调用为 0，本地 Provider 证明协议、alias、usage/ledger 边界 | externally-gated |
| STY-01 | stable key 只产生一个 UUIDv5 Story；Episode 更新同一 Story | Dream projector/repository/PostgreSQL | Story Artifact PG tests覆盖 insert/noop/update/CAS/跨 thread；真实链只产生一条 canonical Story | proved |
| STY-02 | Artifact availability 与 Index sync 分域；Episode 1–99；无可写第二真值 | migrations 0030/0031、Dream repository、Admin application schema | schema contract 2/2；runner 验证 legacy boolean backfill 仅兼容并由新 `artifact_status`/constraint 管控；PG tests 0 skip | proved |
| STY-03 | Run 生命周期只由 Workflow DB；running 需 receipt + Agent Session；terminal 可刷新恢复 | runtime activation + lifecycle service | runtime activation tests覆盖 receipt/session/合法状态机；同一真实 Run 最终 `completed`，重入 detail 仍为 terminal | proved |
| STY-04 | Dream 原子写 Run snapshot/registry/artifacts，再 materialize Story | Dream tool/runtime、Episode action services、Story projector | `dream-producer-chain-postgres-real.spec.ts` 由真实 Dream API/Agent 工具生成 EP01 全套受控产物并建立 Story；未直接 SQL 制造 completed/Story | proved |
| STY-05 | Admin Story list/detail 是严格 public allowlist，不返回 Thread/path/content | Admin Story API/repository | `admin-dream-story-generated-real.spec.ts` 读取同一 Dream Story；public DTO 与预览响应脱敏断言 | proved |
| STY-06 | FS/Artifact 与 Index 独立；503 不写 missing 或改变业务状态 | Dream observation + Admin reader | observation/reconcile tests覆盖 missing/invalid/degraded；新 schema独立 `artifact_status` 与 sync status | proved |
| STY-07 | Admin 只读精确 Run snapshot；防 traversal/symlink/TOCTOU；ETag/revision | Admin Artifact reader | Reader/route tests与真实 Admin preview按 project/run/episode/kind/revision读取；响应无绝对路径 | proved |
| STY-08 | confirm/reject 绑定 current script revision，CAS 与 audit 原子、replay安全 | Admin review mutation transaction | 当前 Admin story mutation 10/10 覆盖 confirm、reject、notes、revision conflict、replay/audit；真实同 Story confirm 成功 | proved |
| STY-09 | non-artifact、identity invalid、unbound 不被误算 missing/reconcile | Dream classifier/projector | reconcile/projector focused 与 PG tests覆盖分类、strict binding 和安全错误 | proved |
| STY-10 | 1440×1000、390×844；loading/empty/error/last-good、keyboard/focus/ARIA | Dream/Admin browser UI | 主链 desktop→reload→mobile 重入；Subscription responsive Chromium；Mock Episode dialog/focus/Escape/ARIA 与模型 last-good/empty | proved |
| STY-11 | Story 与 Artifact 只由 Dream 生产，Admin 只读/审核 | Dream writer/materializer + Admin reader | 同一隔离数据库中先由 Dream 新 Run 生产，再将其 Story ID/revision交给 Admin 浏览器；无测试夹具冒充主链产物 | proved |
| E2E-01 | 同一 actor/workspace/deck/thread/run/episode 串起订阅、alias、Gateway、Ledger、Artifacts、Story | 三域权威 | `run-dream-business-e2e.mjs` + 三个真实 Chromium spec；Run/Story/revision/correlation 全部来自同一隔离数据库 | proved |
| E2E-02 | 成功、失败、重放无悬挂 reservation、无误报成功，刷新/重入一致 | Gateway Ledger + Workflow DB + messages/artifacts | 主链 launch replay返回同一 Run；message dispatch failure terminal且不会被 GET 重派；Admin 成功/失败结算均 reserved=0；页面 desktop/mobile重入 | proved |
| E2E-03 | 一次性 PG、Artifact Root、自有动态端口；精确清理且不停止用户服务 | QA runner | runner `finally` 清理容器/端口/root/output；当前无匹配容器；5173/PID 83170 与 8765/PID 59958保持运行 | proved |

## 3. 用户显式负向矩阵

| 场景 | 直接证据 | 结果 |
|---|---|---|
| 新用户无订阅 / paused / future period | Admin Gateway eligibility tests | fail closed；Provider 前拒绝 |
| 有订阅但显式模型 deny / 模型 stale 或下架 | Admin eligibility + Dream selection tests | 403/409；不 fallback |
| Allowance 耗尽 | 隔离 Subscription Chromium + Dream 402 precheck | 402；不创建虚假 Run；Provider 0 |
| Gateway 未配置/不可达 | Dream selection/launch tests、Model refresh Mock | 503；首次 fail closed，refresh保留 last-good |
| 目录 success/empty/retry/save | Model Settings Chromium 3/3 | 空目录不保存；refresh失败不丢 last-good |
| Run create/replay/conflict/cross actor/refresh/reentry | launch/workflow focused + real chain | 同 key同 Run；drift 409；跨 actor拒绝 |
| Agent SSE/cancel/retry/tool confirm/repeated poll | runner/service/message/hook tests | disconnect可恢复；decision幂等；terminal failed不重派 |
| Provider error/missing usage/stream abort | Admin proxy/settlement tests | safe terminal或有界 reconciliation；无永久 reserve |
| Dream Files、人物、场景、剧本、分镜、审阅、Prompt、渲染指引 | 同一真实 EP01 Run | 全部由受控 Agent 工具产生并可重读 |
| 404/409/422/503、PostgreSQL native types | route/service/PG integration | 安全合同；datetime/JSONB/boolean/nullable使用原生 psycopg 值 |
| console/pageerror/requestfailed/Secret/path | 所有 real specs导航前 diagnostics + DTO/response扫描 | 0 非预期应用诊断；未发现敏感信息 |

## 4. 当前验收回执

- Dream 后端正式测试目录：1835 passed、18 skipped、656 subtests passed；focused Gateway/Agent/runtime：107 passed、1 skipped、94 subtests passed。本轮新增 launch 错误矩阵：1 passed、7 subtests passed。
- Admin 当前定向 Subscription/Gateway/settlement：63 passed；Story schema/review：12 passed。
- 隔离 Subscription Chromium：1 passed；4 Gateway requests（2 succeeded、2 failed）、6 Token ledger entries、0 mismatch、reserved=0。
- Dream PostgreSQL runtime：4 passed；Story Artifact PostgreSQL：61 passed；frontend source：370 passed；当前完整 Mock Chromium：8 passed（含模型目录 success/last-good/empty）。
- 完整真实 Dream Chromium：模型保存/移动恢复 1 passed；同一新 Run 的 Episode/重入 1 passed；Admin读取/按 revision确认 1 passed。
- 完整链 Gateway：32 requests全部 HTTP 200、succeeded、settled；reserve 1,836,876 = capture 1,180 + release 1,835,696；reserved=0；外部 Provider调用 0。
- ESLint 0 errors（21个既有 Hooks warnings）；TypeScript、production build、`git diff --check` 通过。

## 5. 发布结论与外部门禁

本地和隔离环境内的 Dream 剧本生产要求均为 `proved`：旧现场消息保持 terminal failed，不伪造成功；用户重新发送会走已修复的 runtime materialization、refreshable Gateway token、服务端 alias 与 Token settlement 主链。

唯一 `externally-gated` 项是未获授权的真实收费 Provider canary。它不阻断本地实现与零收费发布验收，但部署到真实 Provider 的环境仍须在受控额度、脱敏日志和可回滚窗口内执行 canary，才能声明外部 usage 计量也已验真。

## 6. 回滚与清理

- Dream Agent terminal failure、runtime activation、Gateway helper、Dream Files polling gate、Story schema/repository和测试 fixture均可独立回退；保留对应红灯测试。
- 不回退 PostgreSQL-only、canonical actor、server-owned alias/Allowance/Ledger、revision/ETag、权限边界或 fail-closed 错误合同。
- 测试仅删除精确命名容器、动态端口、Artifact Root和output；不停止用户5173/8765，不写共享生产数据，不运行真实收费 Provider。
