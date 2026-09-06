<!-- [输入] 单一具体工作项、直接设计合同、技术依赖、验收要求与执行前工作树状态。 -->
<!-- [输出] 可直接实施、验证和回滚的任务 requirement。 -->
<!-- [定位] 可复用的技术执行输入模板；用于把业务目标转换为明确工作项和证据合同。 -->
<!-- [同步] 2026-09-06：改用技术依赖、写入边界、验收证据和实际缺口。 -->

# TASK-REQUIREMENT-FORMAT

Evidence scope: Reusable technical execution template
Updated: 2026-09-06
Scope: 将一个具体工作项转换为可实施、可验证、可回滚的输入；不合并互不相关的工作项。

## 0. 输入完整性

开始实现前必须明确以下事实：

- [ ] 业务目标、用户可观察结果和非目标已经写清。
- [ ] 直接设计合同、当前源码和历史证据已经读取；历史结果只作为事实来源，不自动代表当前版本通过。
- [ ] 必要技术依赖及其判断方式已经列出，例如版本、lock digest、capability、配置、服务或浏览器条件。
- [ ] 允许修改、禁止修改和允许删除的路径可以机械检查；未列路径默认不修改。
- [ ] 每个验收 ID 都有可观察条件、命令或方法、通过标准和证据位置。
- [ ] 已记录执行前 `git status --porcelain=v1 --untracked-files=all`；现有改动将被保留。
- [ ] 回滚对象、顺序和清理范围明确，不会停止或删除非本轮资源。
- [ ] 所有占位字段均已替换为具体值，或写明带原因的 `N/A`。

缺少关键输入时，继续完成不受影响的只读调查，并把缺少的具体技术事实记录为实际缺口；旧报告或口头结论不能代替证据。

## 1. 工作目标与边界

| 字段 | 内容 |
|---|---|
| 工作项 | `{{WORK_ITEM_ID_AND_TITLE}}` |
| 目标 | `{{EXECUTION_OBJECTIVE}}` |
| 用户可观察结果 | `{{USER_VISIBLE_RESULT}}` |
| 交付类型 | `{{DELIVERABLE_TYPE}}` |
| 非目标 | `{{OUT_OF_SCOPE_SUMMARY}}` |
| 完成定义 | `{{COMPLETION_DEFINITION}}` |

目标必须说明本工作项会产生什么结果，以及哪些下游功能、生产开关或部署结论仍需独立证据。

## 2. 技术上下文与依赖

| 字段 | 内容 |
|---|---|
| 来源需求 | `{{SOURCE_REQUIREMENT}}` |
| 直接设计合同 | `{{DIRECT_DESIGN_CONTRACTS}}` |
| 当前实现入口 | `{{CURRENT_IMPLEMENTATION_ENTRYPOINTS}}` |
| 必要技术依赖 | `{{TECHNICAL_DEPENDENCIES}}` |
| 已验证历史事实 | `{{VERIFIED_HISTORICAL_EVIDENCE}}` |
| 当前实际缺口 | `{{CURRENT_EVIDENCE_GAPS}}` |

依赖必须对应真实技术关系，例如版本、capability、配置、服务、测试工具和前序代码行为。

## 3. 写入边界

### 3.1 允许修改范围

| 路径或有限 glob | 动作 | 最小变更 |
|---|---|---|
| `{{ALLOWED_PATH_1}}` | `{{ACTION_1}}` | `{{CHANGE_BOUNDARY_1}}` |
| `{{ALLOWED_PATH_2_OR_REMOVE_ROW}}` | `{{ACTION_2}}` | `{{CHANGE_BOUNDARY_2}}` |

目录 glob 必须同时写出排除项和允许删除的精确集合。共享 lock、配置、schema 或部署入口必须采用单一写入方，并在并发任务间提前协调。

### 3.2 禁止修改范围

| 路径或对象 | 规则 | 原因 |
|---|---|---|
| `{{FORBIDDEN_PATH_OR_OBJECT_1}}` | `{{FORBIDDEN_RULE_1}}` | `{{FORBIDDEN_REASON_1}}` |
| `{{FORBIDDEN_PATH_OR_OBJECT_2_OR_REMOVE_ROW}}` | `{{FORBIDDEN_RULE_2}}` | `{{FORBIDDEN_REASON_2}}` |

未列出的路径默认不修改。不得通过复制、重命名、符号链接、生成物、扩大 glob、全局格式化、`reset`、`restore` 或清理工作树绕过边界。

## 4. 实现步骤

1. `{{IMPLEMENTATION_STEP_1}}`
2. `{{IMPLEMENTATION_STEP_2}}`
3. `{{IMPLEMENTATION_STEP_3_OR_REMOVE}}`

步骤必须从公开生产入口和现有 DTO/协议出发，不复制状态机、传输层或测试专用业务入口。

## 5. 验收合同

| 验收 ID | 可观察条件 | 命令或方法 | 通过标准 | 证据位置 |
|---|---|---|---|---|
| `{{ACCEPTANCE_ID_1}}` | `{{OBSERVABLE_1}}` | `{{METHOD_1}}` | `{{PASS_CRITERIA_1}}` | `{{EVIDENCE_1}}` |
| `{{ACCEPTANCE_ID_2_OR_REMOVE_ROW}}` | `{{OBSERVABLE_2}}` | `{{METHOD_2}}` | `{{PASS_CRITERIA_2}}` | `{{EVIDENCE_2}}` |

无法运行的验收必须记录具体命令、失败类型、影响范围和仍缺少的证据。不得把未运行、旧版本通过或文档存在写成当前实现通过。

## 6. 测试与证据策略

| 层级 | 命令或方法 | 覆盖场景 | 通过标准 |
|---|---|---|---|
| 静态检查 | `{{STATIC_CHECK_COMMAND_OR_NA}}` | 路径、依赖方向、配置/lock、秘密边界 | `{{STATIC_CHECK_PASS_CRITERIA}}` |
| 单元/契约 | `{{UNIT_TEST_COMMAND_OR_NA}}` | DTO、parser、状态、错误、权限、回滚 | `{{UNIT_TEST_PASS_CRITERIA}}` |
| 集成 | `{{INTEGRATION_COMMAND_OR_NA}}` | 公开入口、真实 DTO/协议和显式 capability | `{{INTEGRATION_PASS_CRITERIA}}` |
| 浏览器/E2E | `{{E2E_METHOD_OR_NA}}` | 用户可见流程、隔离、失败恢复 | `{{E2E_PASS_CRITERIA}}` |
| 差异检查 | `{{DIFF_CHECK_COMMAND}}` | 允许/禁止路径、格式、引用和生成物 | `{{DIFF_CHECK_PASS_CRITERIA}}` |

浏览器验证优先复用本机兼容 Chrome。浏览器或 runner 无法启动属于 harness 前置失败，应记录缺少的运行条件，不能据此判断页面或 API 有缺陷。

## 7. 工作树与并发协作

1. 执行前记录完整工作树状态，并识别目标路径上的既有改动。
2. 未属于本工作项的现有改动保持不变；不做 broad format 或顺手清理。
3. 若目标文件在执行期间发生外部变化，暂停该文件写入，与并发任务协调后基于最新内容继续。
4. 每轮修改后检查实际变更路径；发现越界时只撤销本轮可明确归属的改动。
5. 测试只停止或删除本轮具名创建的进程、端口、数据库和临时文件。

## 8. 回滚与停止条件

| 条件 | 处理方式 |
|---|---|
| 必要版本、capability、配置或服务不可用 | 保持安全默认值，记录缺少的事实与受影响验收，不伪造通过。 |
| 写入边界或既有改动无法安全合并 | 停止受影响文件，与并发任务协调；不覆盖或清理他人改动。 |
| 需要改变设计、schema、权限、协议、部署拓扑或生产开关 | 保留现有行为，记录新增决策点并等待对应设计/能力落地。 |
| 安全、凭证、用户数据或共享服务存在风险 | fail closed；仅清理本轮资源并保留可审计证据。 |

回滚必须列出精确文件、制品或本轮资源，不得使用“恢复旧版本”“回到之前状态”等不可验证描述。

## 9. 完成报告

完成报告必须包含：

- 实际修改、创建和删除的逐路径清单，以及每项最小摘要。
- 未修改的关键边界和现有工作树改动的保留情况。
- 每个验收 ID 的结果、命令、退出码、关键输出和证据路径。
- 未运行项、真实失败、剩余技术缺口和下一步所需事实。
- 回滚对象、清理结果和生产开关最终状态。

## 10. Model Execution Instruction

基于以上已填充的目标、技术依赖、写入边界、验收和回滚合同，完成实现与最小充分验证。不要扩展任务范围，不要覆盖既有工作树改动，不要只输出计划。若关键技术输入缺失或无法安全合并，继续完成不受影响的工作，并明确记录剩余缺口与验证影响。
