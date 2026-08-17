# TASK-REQUIREMENT-FORMAT

Status: Reusable Execute Prompt Template
Updated: 2026-08-01
Scope: 单个 task 的 execute 上下文填充与执行约束

> 本文件是通用 Prompt Template，不是最终任务文档，也不包含任何特定 Issue、Task 或 Stage 的预填内容。
> 使用方必须为每一个待执行 task 单独复制并填充本模板；不得把多个 task 合并到同一份 execute prompt。

## 0. 填充 Gate

在调用执行模型前，必须满足以下条件：

- 所有 `{{...}}` 占位符均已替换为当前单一 task 的真实值；不适用项填写 `N/A` 并说明原因。
- 已读取当前执行 Issue、对应 task 文档与 Stage 文档，且三者映射唯一。
- 已把 task 文档中的“涉及文件路径”“允许修改范围”“禁止修改范围”原样带入第 5 节。
- 已把 task 的验收条件与测试策略逐项带入第 6、7 节，不得仅写“按文档执行”。
- 已记录工作树现有未提交内容及冲突处理方式；不得覆盖、丢弃或重置他人改动。
- 关键输入、准入条件或写入边界缺失时，停止执行，通过 Issue 评论记录缺口并按治理规则更新状态。

## 1. 执行角色与目标

你是 `{{EXEC_AGENT_NAME}}`，负责实现且仅实现本模板描述的单一 task。

- 执行目标：`{{EXECUTION_OBJECTIVE}}`
- 交付类型：`{{DELIVERABLE_TYPE}}`
- 明确不负责：`{{OUT_OF_SCOPE_SUMMARY}}`
- 完成定义：实现、验证并回填证据；不得只输出计划或分析。

## 2. Issue 上下文

| 字段 | 填充值 |
|---|---|
| 执行 Issue | `{{PAPERCLIP_ISSUE_ID}}` |
| Issue 标题 | `{{PAPERCLIP_ISSUE_TITLE}}` |
| 来源业务 Issue | `{{SOURCE_ISSUE_ID}}` |
| Parent / Ancestor | `{{PARENT_AND_ANCESTOR_ISSUES}}` |
| Domain | `{{DOMAIN: frontend|backend|full-stack|shared}}` |
| 优先级 | `{{PRIORITY}}` |
| 状态 / Work mode | `{{STATUS_AND_WORK_MODE}}` |
| 标签 | `{{LABELS}}` |
| Assignee | `{{ASSIGNEE}}` |
| Blockers | `{{BLOCKERS_OR_NONE}}` |
| 最新评论 / 评审意见 | `{{LATEST_COMMENTS_OR_NONE}}` |

### Issue 背景

{{ISSUE_BACKGROUND}}

### Issue 级约束

{{ISSUE_LEVEL_CONSTRAINTS}}

## 3. Task 合同

| 字段 | 填充值 |
|---|---|
| Task 文档 | `{{TASK_DOCUMENT_PATH}}` |
| Task 标题 | `{{TASK_TITLE}}` |
| 关联 Issue | `{{TASK_SOURCE_ISSUE}}` |
| Task domain | `{{TASK_DOMAIN}}` |
| Task 目标 | `{{TASK_GOAL}}` |
| 输入 | `{{TASK_INPUTS}}` |
| 输出 | `{{TASK_OUTPUTS}}` |
| 直接依赖 | `{{TASK_DEPENDENCIES}}` |
| 风险 / 澄清项 | `{{TASK_RISKS_AND_CLARIFICATIONS}}` |

### 必须执行的实现步骤

{{TASK_IMPLEMENTATION_STEPS}}

## 4. Stage 合同

| 字段 | 填充值 |
|---|---|
| Stage 文档 | `{{STAGE_DOCUMENT_PATH}}` |
| Stage Issue | `{{STAGE_ISSUE_ID}}` |
| Stage / Wave | `{{STAGE_AND_WAVE}}` |
| 准入条件 | `{{STAGE_ENTRY_CONDITIONS}}` |
| 前序 task | `{{PREDECESSOR_TASKS}}` |
| 并行约束 | `{{PARALLELISM_CONSTRAINTS}}` |
| Gate / 冻结点 | `{{STAGE_GATES_AND_FREEZE_POINTS}}` |
| 回滚要求 | `{{ROLLBACK_REQUIREMENTS}}` |
| Stage 验证要求 | `{{STAGE_VERIFICATION_REQUIREMENTS}}` |

未满足的 Stage 准入条件或冻结点：

{{UNMET_STAGE_CONDITIONS_OR_NONE}}

## 5. 写入边界

### 5.1 允许修改范围（闭集）

仅允许修改下表列出的路径。目录范围必须写出明确的文件模式或子路径；父目录名称不自动授权整个目录。

| 路径 / 模式 | 动作（新建/修改/删除） | 允许的最小变更 | 对应 Task §5 路径 |
|---|---|---|---|
| `{{ALLOWED_PATH_1}}` | `{{ACTION_1}}` | `{{CHANGE_BOUNDARY_1}}` | `{{TASK_PATH_REF_1}}` |
| `{{ALLOWED_PATH_2_OR_REMOVE_ROW}}` | `{{ACTION_2}}` | `{{CHANGE_BOUNDARY_2}}` | `{{TASK_PATH_REF_2}}` |

### 5.2 禁止修改范围

| 禁止路径 / 对象 | 禁止规则 | 原因 |
|---|---|---|
| `{{FORBIDDEN_PATH_OR_OBJECT_1}}` | `{{FORBIDDEN_RULE_1}}` | `{{FORBIDDEN_REASON_1}}` |
| `{{FORBIDDEN_PATH_OR_OBJECT_2_OR_REMOVE_ROW}}` | `{{FORBIDDEN_RULE_2}}` | `{{FORBIDDEN_REASON_2}}` |

强制边界规则：

- 未出现在“允许修改范围”中的路径默认禁止修改。
- 禁止通过重命名、移动、复制、符号链接、生成文件或扩大 glob 绕过允许范围。
- 对共享文件只允许修改与本 task 直接相关的最小区段；禁止顺手重构、格式化或清理无关内容。
- 保留工作树中既有改动；若允许路径与既有改动重叠且无法安全合并，停止并在 Issue 评论说明冲突、owner 与所需动作。
- 未被 task 明确授权时，禁止修改 `docs/design/`、`docs/issue/`、`docs/task/`、`docs/stage/`、`docs/exec/`、依赖锁文件、生成物与部署配置。

## 6. 验收要求

| 验收 ID | 验收条件 | 验证证据 | 来源（Issue/Task/Stage） |
|---|---|---|---|
| `{{ACCEPTANCE_ID_1}}` | `{{ACCEPTANCE_CRITERION_1}}` | `{{EXPECTED_EVIDENCE_1}}` | `{{ACCEPTANCE_SOURCE_1}}` |
| `{{ACCEPTANCE_ID_2_OR_REMOVE_ROW}}` | `{{ACCEPTANCE_CRITERION_2}}` | `{{EXPECTED_EVIDENCE_2}}` | `{{ACCEPTANCE_SOURCE_2}}` |

不得删除任何原始验收项。若 Issue、Task 与 Stage 的验收口径冲突，先在 Issue 评论记录冲突并停止受影响部分，不得自行选择较宽松口径。

## 7. 测试与验证要求

| 层级 | 命令 / 方法 | 覆盖场景 | 通过标准 |
|---|---|---|---|
| 静态检查 | `{{STATIC_CHECK_COMMAND_OR_NA}}` | `{{STATIC_CHECK_SCOPE}}` | `{{STATIC_CHECK_PASS_CRITERIA}}` |
| 单元测试 | `{{UNIT_TEST_COMMAND_OR_NA}}` | `{{UNIT_TEST_SCENARIOS}}` | `{{UNIT_TEST_PASS_CRITERIA}}` |
| 集成测试 | `{{INTEGRATION_TEST_COMMAND_OR_NA}}` | `{{INTEGRATION_TEST_SCENARIOS}}` | `{{INTEGRATION_TEST_PASS_CRITERIA}}` |
| E2E / 人工验证 | `{{E2E_METHOD_OR_NA}}` | `{{E2E_SCENARIOS}}` | `{{E2E_PASS_CRITERIA}}` |
| 差异检查 | `{{DIFF_CHECK_COMMAND}}` | 允许/禁止路径、意外改动、格式 | 无越界写入且差异可解释 |

- 优先执行能证明本 task 的最小相关验证；只有 Task 或 Stage 明确要求时才运行全工作区构建/测试。
- 无法运行的测试必须记录具体原因、影响范围和替代证据，不得写成“未测试”后直接宣称完成。
- 测试产生的快照、缓存或报告也受第 5 节写入边界约束。

## 8. 执行规则

1. 开始前读取 Issue、Task、Stage 和相关实现上下文，并记录 `git status --short` 基线。
2. 按第 3 节步骤实施，只修改第 5.1 节闭集中的路径。
3. 每个共享文件采用最小增量改动，保留现有风格和用户改动。
4. 执行第 7 节验证，并把结果逐项映射到第 6 节验收条件。
5. 结束前检查实际变更路径、格式、测试结果和未决风险；禁止使用破坏性命令清理工作树。
6. 通过 Issue 评论记录差异、验证、阻塞、回退或补充上下文，并按 Paperclip 状态规则给出明确最终 disposition。

## 9. 必须回填的完成报告

完成报告必须包含：

- 实际修改文件与每个文件的最小变更摘要；
- 未修改的禁止范围确认；
- 验收条件逐项结果与证据；
- 实际执行的测试/检查命令、结果与未运行项原因；
- 工作树冲突及处理方式；
- 剩余风险、澄清项、后续 owner/action；
- 最终 Issue 状态与理由。

## 10. Model Execution Instruction

基于以上已填充的单一 Issue、Task、Stage、写入边界、验收和测试合同，立即完成实现与最小充分验证。不要扩展任务范围，不要覆盖既有工作树改动，不要只输出计划。若发现关键输入缺失、Stage 准入不满足、允许/禁止范围冲突或无法安全合并，停止受影响写入，通过 Issue 评论记录证据并按治理规则更新状态。
