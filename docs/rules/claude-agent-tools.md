<!-- [Input] ../../AGENTS.md、../../backend/claude_agent/context_builder.py、../../backend/libs/claude_agent_kit/server/agent_runner.py 与 ../design/claude-agent/claude-agent-permission-policy.md。 -->
<!-- [Output] Claude Agent 注入说明、工具描述及权限分类的维护约束。 -->
<!-- [Pos] Claude Agent 工具规则；由 README.md 索引，权限定义仍由现行 Permission Policy 所有。 -->
<!-- [Sync] 2026-10-15: 将 workflow、Tool description 与 low-sensitivity 的职责边界纳入通用规则。 -->

# Claude Agent 工具规则

本规则适用于 Claude Agent 的系统及每轮上下文、MCP/内置工具注册说明和工具权限分类。无论使用 `*_WORKFLOW`、`*_TOOL_SPECS`、`_LOW_SENSITIVITY*` 还是其他代码名称，都按实际职责遵守以下约束。

## Workflow：相关工具的概念与用法

- `*_WORKFLOW` 及同类注入说明，只解释当前相关 Tools 的基本概念及使用方法。
- 用法可包含调用所需输入、工具之间必要的调用顺序、如何使用返回结果，以及无结果或失败时如何处理；内容必须对应实际工具合同。
- 不提及当前工具组之外的工具或数据源，不加入来源优先级、跨业务路由或无关业务策略。
- 不借上下文说明改变权限、副作用或服务端校验。系统说明和每轮说明使用相同合同，避免恢复会话时出现不同规则。

例如，`_REFLECTIONS_MEMORY_WORKFLOW` 的说明范围仅为 `list_memory_distillations`、`read_memory_distillation`、`resolve_memory_behavior` 的基本概念与用法。

## Tool Specs：单个工具的定位

- `*_TOOL_SPECS` 及同类注册定义中的工具级 `description`，只描述该 Tool 的定位与职责，保持简洁；读写影响属于职责的一部分，应准确说明。参数 schema 的字段说明按字段合同表达。
- 不加入业务场景示例、跨工具流程、来源选择或其他与该工具定位无关的行为引导。
- 输入字段、必填项、类型、默认值和枚举由工具 schema 表达；执行层继续校验真实输入。不得为缩短描述删除 schema 或执行层校验，也不得用描述承诺尚未实现的能力。
- 同一工具在注册说明、注入用法和执行合同中的职责必须一致；不要在不同位置重复堆叠引导。

## Low-sensitivity：按现行权限策略分类

[Claude-Agent Permission Policy](../design/claude-agent/claude-agent-permission-policy.md) 是权限决策的唯一依据。本规则不维护另一套工具名单或例外。

- 修改 `_LOW_SENSITIVITY_QUERY_TOOL_NAMES`、`_LOW_SENSITIVITY_BASH_PREFIXES` 及同类分类或判断逻辑前，必须核对该策略的 §2 模式、§3 low-sensitivity 定义及例外、§4 high-sensitivity 和 §6 决策顺序。
- low-sensitivity 包含策略定义的查询或上下文选择操作，以及策略明确记录的会话状态、Thread 编排等例外。按工具实际执行行为、访问范围及策略中的条件判断，不因名称包含 `read` / `list`、提示词宣称“只读”或使用 `*_TOOL_SPECS` 注册就自动归类。
- 未明确分类为 low-sensitivity 的工具按 high-sensitivity 处理；新增或调整分类时，同步权限策略、具体原因、适用条件和对应权限验证，不用宽泛前缀扩大允许范围。
- low-sensitivity 仅影响策略规定模式下的工具批准流程，不授予身份、资源归属或业务访问权限；保留已有服务端认证、归属与输入校验。
- 保持策略规定的模式及决策顺序：`auto` 的 low-sensitivity 分支显式返回 `permissionDecision: "allow"`；未启用 full-access 且未命中特殊分支时，`manual` 保留确认；`none` 不暴露工具。现有 full-access 例外、前置硬拒绝及无可用确认渠道时的拒绝行为均按原策略执行，不能被 low-sensitivity 分类绕过。

## 修改时检查

1. 注入说明是否只讲相关工具的概念与用法，工具描述是否只讲该工具定位。
2. 描述是否与注册 schema、handler 的输入输出及副作用一致。
3. 权限分类是否有现行策略依据，并保持模式、前置拒绝和业务权限校验。
4. 同步受影响文件头、目录说明与设计；按改动执行文档检查或对应权限测试，分别报告结果，不将文档检查称为业务验收。
