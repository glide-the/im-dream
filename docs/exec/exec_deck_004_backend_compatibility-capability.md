# Exec Report: SUO-274 / DECK-004 - 兼容性判定与能力交集权限

## 1. 执行上下文

- Task ID: `task_deck_004_backend_compatibility-capability`
- 执行 Issue: `SUO-274`
- 来源业务 Issue: `DECK-004`
- 关联父项: `SUO-217`
- 关联设计稿: `docs/design/deck-plugin-voice-ink-dream-integration.md` §6.3、§6.4
- 关联 Task: `docs/task/task_deck_004_backend_compatibility-capability.md`
- 关联 Stage: `docs/stage/stage_deck-plugin-voice-ink-dream-integration.md`，Stage 1 / Wave 4
- 执行 Agent: `ExecTaskAgent`
- 执行时间: `2026-08-01 17:15–17:24 CST`
- Execution lock: harness 已为本次 run checkout；按 wake payload 要求未重复 checkout
- Paperclip work product: `342897c4-de24-4814-8089-518ff7b90f17`（workspace-file 主工件）

工作树基线包含其他任务留下的已修改/未跟踪文件。本任务没有重置、覆盖或清理这些改动；本次写入严格限制在 Issue 授权的五个精确路径。

## 2. TASK-REQUIREMENT-FORMAT.md 填充摘要

- 模板路径: `docs/task/TASK-REQUIREMENT-FORMAT.md`
- 执行角色: `ExecTaskAgent`
- 输入 Issue: `SUO-274 [execute][deck-plugin][task_004] 实现兼容性判定与能力交集`
- 输入 Task: `task_deck_004_backend_compatibility-capability`
- Domain / 优先级: `backend` / `high`（来源业务条目为 P0）
- Stage / Wave: Stage 1 / Wave 4
- 前序依赖: Manifest、Runtime Lock、Installation 基线均已完成
- Gate: `DECK-016` 三域单写边界已冻结；`DECK-019` 仅作设计引用，本 task 不实现撤销服务
- 填充后的执行目标: 实现固定顺序、失败短路的 8 步服务端兼容性判定；计算五域能力交集；未知能力默认拒绝；扩权进入 `upgrade_pending` 并仅允许显式管理员审批
- 明确排除: Binding、Preflight、API/UI、Workflow Run、撤销服务、多节点/临时 runtime、production rollout
- 允许写入: 本报告及四个实现/测试精确路径
- 禁止写入: 除允许闭集外的全部路径，尤其是 design/issue/task/stage、frontend、身份权限内部实现、Installation/Preflight/API/Workflow Run 合同和部署配置
- 验收条件: Issue 所列 7 项完整带入，未放宽或删除
- 测试要求: 目标测试、4 组指定回归、`py_compile`、允许路径差异/whitespace/越界核验
- 回滚要求: 只撤销本 task 的追加模型和三个新增实现/测试文件；不得重置共享工作树
- 未满足准入条件: 无

模板填充完成后生成的模型执行指令为：仅使用数据库中的 release、installation、runtime lock 与服务端裁决信号，按设计顺序实现最小闭集；外部结果仅暴露规范 code、失败步骤和恢复动作；默认拒绝未经运行时支持或管理员批准的能力；完成最小充分测试后回填证据。

## 3. 模型生成的执行任务

- 任务目标: 提供 selection validation 与 execution preflight 可复用的非生产兼容性基础能力
- 实现范围:
  1. 追加 `CompatibilityCheck`、`CompatibilityResult`、`CapabilityDiff` 严格模型及一致性校验
  2. 新增五域能力交集 evaluator，并允许服务端能力注册表进一步收窄结果
  3. 新增 SQLite-backed `CompatibilityService`，按固定 8 步顺序失败短路
  4. 新增扩权 diff、`upgrade_pending` 暂存、默认拒绝的管理员审批边界
  5. 新增覆盖成功、逐维失败、短路、未知能力、deprecated policy、客户端版本替代拒绝和扩权审批的测试
- 文件范围: 仅 Issue 授权的五个精确路径
- 验证方式: 目标 11 项测试、上游 42 项回归、静态编译、whitespace 与范围检查

## 4. 实现变更记录

| 文件 | 操作 | 说明 |
|---|---|---|
| `backend/models/deck_plugin.py` | update | 最小追加 8 步枚举、结构化兼容结果、能力 diff；强制失败字段完整、失败结果不暴露能力、集合排序唯一、扩权与审批标志一致 |
| `backend/services/deck_plugin/compatibility_service.py` | create | 新增固定顺序 8 步服务端判定；校验 release/installation、四项服务端裁决、runtime lock、权限交集及 runtime materialization/loadable；新增扩权暂存和显式管理员审批边界 |
| `backend/services/deck_plugin/capability_evaluator.py` | create | 新增 manifest、installation、runtime snapshot policy、user/workspace grant、ClaudeAgent runtime support 五域严格交集，运行时支持作为默认已知能力注册表 |
| `backend/tests/test_deck_plugin_compatibility.py` | create | 新增 11 项单元/SQLite 集成式测试，覆盖全部验收维度 |
| `docs/exec/exec_deck_004_backend_compatibility-capability.md` | create | 唯一正式执行报告 |

### 变更摘要

- 判定链严格按 `release/installation → Deck host → ClaudeAgent → story schema → runtime config → runtime lock → workflow permission → runtime readiness` 执行，首次失败立即返回。
- runtime lock 必须与 release hash、plugin/version 身份一致；每个声明 plugin 必须有唯一 lock entry，且 source、精确版本和 `sha256` digest 可解析。
- workflow 所需能力必须包含在五域交集中；ClaudeAgent runtime support 默认充当已知能力 allowlist，未知能力默认拒绝。
- `RuntimeContext` 不接受客户端版本字符串或额外字段，只消费上游服务产生的布尔裁决，避免客户端版本比较成为安全边界。
- 扩权检查写入 `upgrade_pending`，在显式管理员审批前不扩大 `approved_capabilities`；默认 authorizer 拒绝全部 actor，必须由身份/权限适配器显式注入。
- 对外失败结果只含 `passed`、`failed_check`、规范 `error_code`、规范恢复动作和空能力列表，不包含 manifest、prompt、secret、内部配置或异常细节。

## 5. 验收结果

| 验收项 | 结果 | 验证证据 |
|---|---|---|
| 1. 固定顺序，失败即停止并返回结构化结果 | 通过 | `test_fixed_order_short_circuits_at_first_failure` 与结构化模型校验通过 |
| 2. 覆盖 8 步判定 | 通过 | release/installation、四项服务端兼容裁决、lock、permission、readiness 均有成功/失败覆盖 |
| 3. 五域交集正确，未知能力默认拒绝 | 通过 | evaluator 两项测试及 permission unknown/registry 收窄测试通过 |
| 4. 扩权进入 `upgrade_pending` 且必须管理员审批 | 通过 | pending 前 approved 集合不变；非管理员拒绝；显式管理员精确审批后才应用 |
| 5. 禁止客户端版本字符串替代服务端裁决 | 通过 | `RuntimeContext` 无版本输入且 `extra=forbid`；额外客户端版本字段测试被拒绝 |
| 6. 外部结果安全且只含规范原因/恢复动作 | 通过 | 逐维失败 payload 检查及失败能力泄露模型校验通过 |
| 7. 判定维度、交集、未知能力、审批、错误与服务端裁决测试通过 | 通过 | 目标 11/11、指定回归 42/42、静态编译通过 |

## 6. 测试与验证

### 已执行测试

1. `PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -m unittest backend.tests.test_deck_plugin_compatibility -v`
   - 结果: `11 tests`, `OK`
2. `PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -m unittest backend.tests.test_deck_plugin_installation backend.tests.test_deck_plugin_lock backend.tests.test_deck_plugin_manifest backend.tests.test_database -v`
   - 结果: `42 tests`, `OK`
3. `PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -m py_compile backend/models/deck_plugin.py backend/services/deck_plugin/compatibility_service.py backend/services/deck_plugin/capability_evaluator.py backend/tests/test_deck_plugin_compatibility.py`
   - 结果: 通过，无语法错误
4. 允许路径 whitespace 检查
   - 结果: 无行尾空白
5. 允许路径状态与写入范围检查
   - 结果: 本 task 仅写入五个授权路径；首次 `py_compile` 产生的四个精确 bytecode 文件已清除，最终编译缓存定向到 Paperclip run scratch，不留越界生成物

### 验证证据

- 目标测试覆盖 8 步全通过路径、首次失败短路、各服务端裁决维度、lock digest 失败优先级、能力交集、已知能力收窄、deprecated policy、客户端版本额外字段拒绝、扩权审批前后状态。
- 指定 Manifest、Runtime Lock、Installation 与 Database 回归全部通过，未发现上游基线回归。
- 测试日志中的 `Memory workspace config backfill skipped` 与数据库初始化提示为仓库既有测试输出，不影响测试结果。

### 未执行测试及原因

- 未运行无关全仓测试：Issue 明确只要求本 task 与四组上游回归。
- 未验证多节点、临时 runtime、真实身份服务、API/UI、Workflow Run 或 production rollout：均在禁止/非生产范围外，不作为本 task 完成声明。

## 7. 风险与阻塞

- 风险: 下游集成必须由 Deck host、ClaudeAgent、story schema 和 runtime config 的 owning service 产生服务端裁决；不得把 `RuntimeContext` 暴露为客户端自报合同。
- 风险: 管理员 authorizer 默认 fail closed；接入真实身份/权限服务属于后续授权任务。
- 风险: 本实现是单节点 SQLite 非生产基础能力，不声明多节点一致性、临时 runtime 或 production readiness。
- 阻塞: 无。
- 控制面说明: sandbox 内初次读取 heartbeat-context 时本地 API bridge 暂不可达；按受控方式使用本地 bridge 后，heartbeat context、workspace-file 主工件和最终 `done` 状态均已成功回写。
- 需要上游澄清的问题: 无。

## 8. 完成状态

- [x] 已完成实现
- [x] 已完成目标测试
- [x] 已完成指定回归
- [x] 已记录变更和验证证据
- [x] 已满足 7 项验收条件
- [x] 未修改禁止范围
- [x] 可进入 review / audit

Issue 最终状态已更新为 `done`：实现和要求内验证均完成，无待处理 follow-up 或真实阻塞。

## 9. 回滚建议

- 从 `backend/models/deck_plugin.py` 精确移除本 task 追加的 `CompatibilityCheck`、`CompatibilityResult`、`CapabilityDiff`，保留 Manifest/Runtime Lock/Installation 上游模型。
- 删除本 task 新增的 `compatibility_service.py`、`capability_evaluator.py` 和 `test_deck_plugin_compatibility.py`。
- 删除本执行报告时仅删除本文件，不触碰其他 `docs/exec/`。
- 回滚后重新执行 Manifest、Runtime Lock、Installation 与 Database 四组回归，确认上游能力仍为 `42 tests OK`。
- 禁止使用 `git reset --hard`、目录级清理或覆盖共享工作树；所有回滚必须按上述精确区段/路径执行。

## 10. 执行完成报告

`SUO-274 / DECK-004` 的非生产兼容性判定与能力交集基础能力已实现，五个授权输出路径完整，目标测试、指定回归、静态编译、whitespace 和范围验证均通过。结果可作为后续 Binding selection validation 与 Workflow Preflight 的服务端基础，但不得据此宣称 API/UI、Workflow Run、多节点 runtime 或 production rollout 就绪。
