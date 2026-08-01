# Exec Report: task_deck_014_backend_api-error-codes - API 路由与错误码规范

## 1. 执行上下文

- Task ID: `task_deck_014_backend_api-error-codes`（逻辑任务 `DECK-014`）
- 执行 Issue: `SUO-331`，`[execute][deck-plugin][task_014] 实现 API Routes 与 Error Codes`
- 来源业务 Issue: `SUO-217`；Parent / Ancestor: `SUO-217`、`SUO-216`
- 关联 Issue 文档: `docs/issue/ISSUES_deck-plugin-voice-ink-dream-integration.md` §3 `DECK-014`
- 关联设计稿: `docs/design/deck-plugin-voice-ink-dream-integration.md` §12.1、§14.1、§14.2、§14.3
- 关联 Stage: `docs/stage/stage_deck-plugin-voice-ink-dream-integration.md` §21.2，Stage 4 / Wave 1
- 执行 Agent: `ExecTaskAgent` (`2a7a15fe-2ebb-4dc5-91a8-48ae2bcc5471`)
- 执行时间: 2026-08-01 23:16–23:27 CST
- Checkout: Paperclip harness 已在本 run 预先完成 checkout；未重复请求执行锁
- 限域: development/test、单节点 persistent runtime；不声明 Stage 4 production Gate 通过

## 2. TASK-REQUIREMENT-FORMAT.md 填充摘要

- 模板路径: `docs/task/TASK-REQUIREMENT-FORMAT.md`
- 输入 Issue: `SUO-331`；来源业务 Issue `DECK-014`；来源控制项 `SUO-217`
- 输入 Task: `docs/task/task_deck_014_backend_api-error-codes.md`
- 填充后的执行目标: 实现三组规范逻辑 API adapter、27 项共享错误注册表、安全错误 envelope 与目标测试；保持 Deck control plane、ClaudeAgent runtime control、story-workspace 三域单写
- 交付类型: backend router / error contract / unittest / exec report
- 明确不负责: 物理服务拆分、gateway/部署注册、底层业务服务实现、前端、设计/Issue/Task/Stage 重写、第三业务服务、共享表双写
- Task 直接依赖: `DECK-004`、`DECK-006`、`DECK-007`；Stage §21.2 已复核通过
- 允许范围: 三个 router、错误注册表、目标测试和本报告共六个闭集路径
- 禁止范围: 未列明路径默认禁止；特别包含其他 `docs/exec/`、`docs/design/`、`docs/issue/`、`docs/task/`、`docs/stage/`、`frontend/`、`backend/server.py`、gateway/部署配置和底层业务服务
- 验收条件: Task §9 全部 12 项原样纳入执行 Gate
- 测试要求: 指定 `unittest` 命令、`git diff --check`、TestClient 逻辑集成调用和安全/来源不可变断言
- 回滚要求: 只回退本 Task 新文件及 `story_workspace.py` 的 DECK-014 增量区段；保留其他既有内容及本执行证据

### 工作树基线与冲突处理

- 开始时共享工作树已有大量未提交/未跟踪改动，涉及 backend、frontend、design、issue、task、stage 和其他 exec 报告；未执行 reset、checkout、clean 或全局格式化。
- `backend/routers/story_workspace.py` 在开始时已是未跟踪的 883 行既有文件，与本 Task 授权路径重叠。处理方式为仅追加 DECK-014 workflow preflight/run 请求模型、gateway hook 和六个 route handler，并保留全部既有 Story Workspace 路由。
- 其余四个实现/测试目标在开始时不存在，按闭集新建；唯一正式报告在开始时不存在。
- `docs/task/task_deck_014_backend_api-error-codes.md` 与 Stage 文档已有他人改动，仅读取，未修改。

## 3. 模型生成的执行任务

- 任务目标: 将冻结的设计合同转为可导入、可映射、无权威状态的逻辑 router，并用统一注册表生成安全错误响应。
- 实现范围:
  - 9 个 Deck Plugin 管理端路由
  - 4 个 Voice Deck binding 路由
  - 6 个 Story Workspace preflight/run 路由
  - 27 个规范错误码与统一 `{ "error": ... }` envelope
  - 管理权限、幂等 key 一致性、来源字段拒绝覆盖、安全异常降级测试
- 文件范围: 严格限制为 Task §11 的六路径闭集
- 实现方式:
  1. router 仅依赖可注入 gateway protocol，不读写跨域共享状态；部署 adapter 负责接入各自权威业务服务。
  2. 认证复用既有 `get_current_user`；管理端按 `plugin:read`、`plugin:admin`、`plugin:service` 最小权限判定。
  3. Story Run 创建模型使用 `extra="forbid"`，只接受 preflight/token/idempotency/source thread；不接受 `deck_plugin_version` 或 `deck_runtime_snapshot_id`。
  4. 已知与未知异常都映射到注册表安全文案；不回显异常字符串、堆栈、路径、prompt、secret 或完整命令输出。
  5. 用注入 fake domain gateway 的 FastAPI TestClient 覆盖全部 19 个路由，同时验证 adapter 不创建额外 Workflow Run。
- 验证方式: 指定 unittest、route inventory、全工作树 `git diff --check`、六路径 status 审计。

## 4. 实现变更记录

| 文件 | 操作 | 说明 |
|---|---|---|
| `backend/routers/deck_plugins.py` | create | 新增 9 个管理端逻辑路由、最小权限检查、幂等 key 冲突处理、无状态 control-plane gateway hook 与安全错误映射 |
| `backend/routers/voice_decks.py` | create | 新增 4 个 Deck plugin options/binding/validate 路由；只委托 Deck domain gateway，不建立第二份 binding 状态 |
| `backend/routers/story_workspace.py` | update | 在既有文件中增量加入 6 个 workflow preflight/run/retry/cancel 路由；请求来源字段闭集和 story-domain gateway hook |
| `backend/services/errors/error_registry.py` | create | 定义设计稿 §12.1 的 27 个错误码，每项含 phase、meaning、recovery；新增 allowlist-only 安全 payload builder |
| `backend/tests/test_api_routes.py` | create | 新增 8 个测试，覆盖 19 个 endpoint、27 个错误响应、权限、幂等、来源不可变和异常脱敏 |
| `docs/exec/exec_deck_014_backend_api-error-codes.md` | create | 本 Task 唯一正式执行报告 |

### 变更摘要

- 管理端安装响应明确包含 `operation_id`、`capability_diff`、`runtime_readiness`。
- Voice Deck 保存必须由严格模型提供 `expected_binding_revision`，`apply_to` 固定为 `next_run`；validate 响应测试确认不创建 Workflow Run。
- Story Run 创建成功响应的 `deck_plugin_id`、`deck_plugin_version`、`deck_runtime_snapshot_id` 由可信 gateway 复制；客户端提交这些字段会收到 422。
- 默认未绑定部署 adapter 时返回注册的安全 503，不伪造成功，也不在 router/gateway 持有权威状态。
- 未修改任何禁止路径；没有新增第三业务服务、数据库表、共享写路径或部署配置。

## 5. 测试与验证

### 已执行测试

1. 指定目标测试：

   `PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -m unittest backend.tests.test_api_routes -v`

   最终结果: **PASS**，8 tests，0 failures，0 errors，约 0.064s。

2. 差异格式检查：

   `git diff --check`

   结果: **PASS**，exit 0，无 whitespace error。

3. 授权路径差异检查：

   `git diff --check -- backend/routers/deck_plugins.py backend/routers/voice_decks.py backend/routers/story_workspace.py backend/services/errors/error_registry.py backend/tests/test_api_routes.py docs/exec/exec_deck_014_backend_api-error-codes.md`

   结果: **PASS**，exit 0。

4. Route inventory（以既有解释器导入三个 router）：

   - Deck Plugin: 9 个规范 endpoint
   - Voice Decks: 4 个规范 endpoint
   - Story Workspace workflow: 6 个规范 endpoint
   - 合计: 19 个规范 endpoint，method/path 与设计稿 §14.1–14.3 一致

5. 补充静态导入检查：

   `python -m py_compile backend/services/errors/error_registry.py backend/routers/deck_plugins.py backend/routers/voice_decks.py`

   结果: **PASS**。后续正式测试均使用 `PYTHONDONTWRITEBYTECODE=1`。

### 首次失败与修复证据

- 首次目标测试: 7 tests 中 6 pass、1 fail。
- 失败项: known `ApiRouteError` 期望 403，实际安全降级为 503。
- 根因: 仓库双启动路径将同一文件分别加载为 `backend.services.errors.error_registry` 与 `services.errors.error_registry`，异常类身份不相同。
- 修复: 三个 router 统一采用仓库 router 运行方式的顶层 `services...` / `models...` 导入优先，并保留 `backend...` fallback。
- 修复后: 目标测试扩充为 8 项并全部通过；失败未静默跳过。

### 未执行测试及原因

- 未运行全 workspace test/build：Task 仅要求最小目标 unittest 与 diff check，且共享工作树包含大量并行未提交内容；扩大测试范围不能隔离归因。
- 未修改或启动 `backend/server.py`：该路径不在允许闭集；本 Task 交付的是可由 gateway/deployment adapter 映射的规范逻辑 router。
- 未连接真实生产 Deck/runtime/story 服务：物理部署与底层 service wiring 明确禁止；使用注入 gateway 的 TestClient 验证完整 HTTP 合同与单写边界。

### 手动验证步骤

1. 从仓库根执行指定 unittest 命令。
2. 导入三个 router 并枚举 `route.methods` / `route.path`，核对 9 + 4 + 6 路由。
3. POST Workflow Run 时加入 `deck_plugin_version` 或 `deck_runtime_snapshot_id`，确认 422；移除后确认响应来源由 gateway 返回。
4. 让 gateway 抛出包含本地路径、prompt、secret 的异常，确认响应仅为注册表安全 503 文案。
5. 执行 `git diff --check` 并核对 `git status --short -- <六个授权路径>`。

## 6. 验收条件逐项结果

| # | Task §9 完成标志 | 结果 | 证据 |
|---|---|---|---|
| 1 | 管理端 API 路由完整，覆盖 §14.1 | ✅ | route inventory 9/9；`test_all_nine_admin_routes_and_install_contract` |
| 2 | Deck 创建/编辑 API 路由完整，覆盖 §14.2 | ✅ | route inventory 4/4；`test_four_voice_deck_routes_preserve_next_run_and_revision` |
| 3 | Story Workspace 执行 API 路由完整，覆盖 §14.3 | ✅ | route inventory 6/6；`test_six_story_routes_copy_frozen_source_and_reject_client_override` |
| 4 | 25+ 规范错误码定义完整 | ✅ | 27 项注册；测试逐码生成并验证安全响应 |
| 5 | 每个错误码包含含义和恢复动作 | ✅ | registry loop 对全部 27 项断言 phase/meaning/recovery 非空 |
| 6 | 客户端只展示安全文案 | ✅ | known/unknown/unexpected error 测试；无异常字符串、堆栈、路径、prompt、secret 回显 |
| 7 | 安装响应包含三个必需字段 | ✅ | install contract 测试断言 `operation_id`、`capability_diff`、`runtime_readiness` |
| 8 | 创建运行来源由服务端复制且客户端不可覆盖 | ✅ | 成功响应使用 gateway 冻结来源；额外来源字段请求 422 |
| 9 | 单元测试覆盖所有 API 路由和错误响应 | ✅ | 19 个 endpoint 均调用；27 个错误 payload 逐项验证；8 tests 全绿 |
| 10 | 三域单写、无状态 gateway、不引入第三服务/双写 | ✅ | router 仅调用各自 gateway protocol；无数据库/schema/service/deployment 改动 |
| 11 | 实际变更只位于五个实现/测试路径及唯一报告 | ✅ | scoped status 仅显示这六个授权路径；其他基线差异未改动 |
| 12 | 报告回填命令、结果、验收、diff、回滚 | ✅ | 本报告 §5、§6、§8 |

## 7. 风险与阻塞

- 风险: 部署层尚需把三个 gateway dependency hook 绑定到各自权威服务并注册 router；这是 gateway/deployment/底层业务 service owner 的后续集成边界，不属于本 Task 写入授权。
- 风险: 共享工作树中 `story_workspace.py` 原为未跟踪文件，最终集成/提交时需确保同一工作树 owner 保留其既有 883 行内容与本次增量。
- 阻塞: **无**。本 Task 的逻辑 API、错误合同和授权范围内验证均完成。
- 需要上游澄清的问题: 无；DECK-016 已 frozen，DECK-017/019 production Gate 不阻塞 development/test 限域实现。

## 8. 完成状态

- [x] 已完成实现
- [x] 已完成测试
- [x] 已记录变更
- [x] 已满足 Task §9 的 12 项验收条件
- [x] 可进入 review / audit

建议 Paperclip 最终 disposition: `done`。本 Issue 的授权交付已完成且无剩余 follow-up；StagePlanner 的后续 Stage readiness/audit 属于上游独立流程，不作为本 Issue 留在 `in_progress` 的理由。

## 9. 回滚建议

- 回滚文件:
  - 完整移除本 Task 新建的 `backend/routers/deck_plugins.py`、`backend/routers/voice_decks.py`、`backend/services/errors/error_registry.py`、`backend/tests/test_api_routes.py`
  - 仅从 `backend/routers/story_workspace.py` 移除本 Task 新增的 error import、四个 workflow request model、gateway protocol/hook、安全调用 helper 和六个 workflow route handler；保留该文件开始时已有的全部 Story Workspace 内容
  - 保留本执行报告，并追加实际回滚时间、原因和结果；不得用代码回滚删除证据
- 回滚验证:
  - 回滚前后执行目标 unittest（回滚后预期该目标模块不存在或由替代合同更新）
  - 执行 `git diff --check`
  - 枚举 router，确认没有留下部分重复注册或跨域写入
- 注意事项:
  - 不得回滚或清理共享工作树其他既有差异
  - 不得用 gateway 权威状态、共享表双写或内部异常回显作为临时替代
  - 若下游 adapter 不可用，保持注册表安全不可用错误，不伪造成功或部分提交

## 10. 执行完成报告

- 执行报告路径: `docs/exec/exec_deck_014_backend_api-error-codes.md`
- 变更文件清单: 本报告 §4 的六个授权路径
- 测试结果: 指定 unittest 8/8 PASS；`git diff --check` PASS
- 验证证据: 19 个 endpoint inventory、27 项错误 payload、权限/幂等/来源不可变/脱敏断言
- 阻塞记录: 无；首次导入身份失败已修复并在 §5 留证
- 回滚建议: 见 §9
- Review / audit readiness: **是**
