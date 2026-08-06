# drama-forge 多 Episode 工作流操作：任务二设计与独立评审记录

> 日期：2026-08-06
>
> 上游裁决：`2026-08-06-drama-forge-multi-episode-workflow-actions-task1-problem-decision-record.md`
>
> 设计稿：`design_011_drama-forge-multi-episode-workflow-actions.md`
>
> 最终结论：第四轮独立评审 PASS；无 P0/P1/P2
>
> 生产代码：本阶段未修改

## 1. 本轮规划前置器

### 1.1 Optimized Prompt

以任务一问题判定记录为唯一产品输入，新增独立、可实现、可测试的中文交互设计稿。设计服务端拥有的多 Episode workflow action projection，覆盖 EP01→EP02→EP03；后端以可信 Episode binding、artifact manifest、workflow facts 和 revisions 生成带 opaque actionId、目标 Episode、推荐性、可派发性、禁用原因、canonical inputs 与 consequences 的选项，前端只负责显示、前两个直接操作、其余折叠、选择、确认、键盘和焦点。严格还原 vendor 工作流，不创建“Outline 分镜”虚构状态；提供完整动作矩阵、依赖图、跨集流程图、时序图、truth ownership、桌面/窄屏线框和恢复图，并接受独立证据化评审。

### 1.2 Optional Enhancers

- 区分服务端事实、UI 投影和 mounted-session 交互状态。
- 定义 recommended、executable alternative、preview、blocked、pending、dispatched 与 stale。
- 用 server-owned inclusion/horizon 让每个 snapshot 的选项集合、顺序和 N 可唯一推导。
- 将设计字段回链到任务三 U1—U10 和测试门。

### 1.3 执行计划与验收

计划：读取任务一、vendor、`design_008`—`design_010`、现有 UI 和 UI Design v2.1；新增 `design_011`；由独立只读代理按十项质量门评审；每次 FAIL 前重新执行 Prompt Architect，再最小修订和复审。

验收：20 项设计主题、7 类图示、全量动作合同、EP01/02/03、刷新/重入、桌面/窄屏/键盘与安全边界齐全；无 P0/P1/P2；本阶段不修改生产代码。

## 2. 技能与规范使用

- 检查了项目 `html-design-workflow` 技能。该技能要求已有 `target_image.png` 并产出 HTML/Tailwind；本任务没有目标截图且只需 canonical 交互设计，故没有运行其四代理流水线，只采用“结构—层级—视觉—验证”的分层方法。
- 通过 `pdf` 技能只读提取 `docs/prd/Ink & Memory UI Design v2.pdf`。原稿第 4—5 页要求以语义 token 为颜色 owner，使用 Warm Canvas、Paper Cream、Action Brown、Border Paper，并遵守少面板、多留白、轻纸面、细线、静态无卡片阴影。
- Dream Agent surface、Episode 内容、artifact 异常隔离分别继续由 `design_008`、`design_009`、`design_010` 拥有；`design_011:3-8` 只增量拥有多 Episode action projection。

## 3. 设计交付

| 必需内容 | 设计位置 |
| --- | --- |
| 背景、目标、非目标 | `design_011:44-66` |
| vendor 多 Episode 工作流 | `design_011:68-135` |
| Outline/script/review/storyboard/Prompt 边界 | `design_011:90-135` |
| action options 缺口 | `design_011:137-148` |
| EP 身份规则 | `design_011:150-178` |
| EP01/02/03 动作矩阵 | `design_011:180-190` |
| Dialog 信息架构、前二、More(N) | `design_011:211-278` |
| 状态/视觉与 OptionV2 | `design_011:280-348` |
| 全量 action 文案/输入/后果 | `design_011:350-368` |
| confirmation/canonical inputs | `design_011:370-448` |
| 提交、pending、REST、重入 | `design_011:450-531` |
| 多 Episode/API/component 边界 | `design_011:533-584` |
| 响应式、键盘、线框 | `design_011:586-681` |
| 非目标与验收 | `design_011:683-727` |
| truth ownership/端到端时序 | `design_011:729-783` |
| U1—U10 TDD 映射 | `design_011:785-799` |

### 3.1 指定图示

| 图示 | 位置 |
| --- | --- |
| 单 Episode 命令与产物依赖 | `design_011:72-88` |
| EP01 → EP02 → EP03 | `design_011:192-209` |
| facts → options → dialog → confirmation → Agent | `design_011:750-783` |
| truth ownership | `design_011:729-747` |
| 桌面折叠/展开线框 | `design_011:613-656` |
| 窄屏线框 | `design_011:660-681` |
| 刷新/重入恢复时序 | `design_011:481-509` |

## 4. 第一轮独立评审：FAIL

结果：无 P0；4 个 P1、4 个 P2。

| 问题 | 修订结果 |
| --- | --- |
| canonical inputs 把 assets 误当 Episode manifest artifact | 改为 episode/project/asset/fact 判别联合；`design_011:393-448` |
| pending 缺少 dispatched 和 turn 无新 revision 收敛 | 增加技术终态与重新开放规则；`design_011:523-531` |
| 未覆盖 allowlist 全量文案 | 增加 plan 至 render/none 全量表；`design_011:350-368` |
| current/next relation 无法表达 previous | 升集后 previous 不再投影；`design_011:533-541` |
| 第二直接项相关性错误 | 固化排序与矩阵；`design_011:184-190,230-238` |
| OptionV2 状态不变量不足 | 增加 truth table；`design_011:330-348` |
| 取消确认试图聚焦已卸载 DOM | parent 保存 actionId+wasOverflow，重挂载 ref map；`design_011:370-391` |
| 409/412 guidance owner 不一致 | 提升到 Execution mounted-session state；同上与 `:481-485` |

## 5. 第二轮独立评审：FAIL

上一轮 7/8 项闭环；发现 2 个新 P1、2 个 P2：

1. options inclusion/cap 缺失，线框中的“更多（5）”不可唯一推导；修订为 current suffix + regeneration + two-step next horizon，最大 9，Prompt 场景精确 7 项（`design_011:240-264`）。
2. plan/script/Prompt context 未完整承接 vendor；增加 worldbuilding、character-arc ledger、asset inventory 和 script emotional context（`design_011:350-368,393-448`）。
3. preview/blocked 仍允许非 idle；修订为 strict-invalid（`design_011:330-348`）。
4. 最后一集 validation current 没有唯一 recommended；修订为 render guide recommended，render completion 后 options empty（`design_011:253-264,368`）。

## 6. 第三轮独立评审：FAIL

结果：无 P0/P2；2 个 P1。

1. 动作矩阵残留旧 next horizon；已将 EP01/02 validation 与 EP03 storyboard-stale 场景改为精确 current/next 集合（`design_011:184-190`）。
2. `/drama-plan` context 仍少 asset inventory；已补入 action 表和 canonical input 说明（`design_011:356,444`）。

## 7. 第四轮独立评审：PASS

独立代理 `/root/task2_multi_episode_design_review` 全程只读。第四轮确认无 P0/P1/P2，十项门全部通过：

| 质量门 | 结论 | 主要证据 |
| --- | --- | --- |
| vendor 命令与依赖 | PASS | `design_011:68-135,350-368` |
| EP 编号与稳定身份 | PASS | `design_011:150-178,533-541` |
| 无虚构状态 | PASS | `design_011:60-66,90-99` |
| option 状态、集合和 N | PASS | `design_011:230-348` |
| 服务端 truth ownership | PASS | `design_011:393-448,543-584,729-747` |
| revision/idempotency/恢复 | PASS | `design_011:450-531` |
| UI v2、桌面、窄屏、键盘 | PASS | `design_011:586-681` |
| 20 项与 7 类图示 | PASS | 本记录第 3 节 |
| U1—U10 可实施性 | PASS | `design_011:785-799` |
| 安全边界 | PASS | `design_011:543-584,683-727,816-818` |

## 8. 任务二最终裁决

任务二通过。任务三必须以 `design_011` 第四轮版本为唯一实现输入：

- 服务端 Episode binding 和 workflow facts 拥有身份与动作；前端不生成 EP、命令或路径。
- 最终用户名称为“基于最新剧本更新 EPxx 详细分镜”“生成 EPxx Prompt 包”“开始 EPnext 分集规划”。
- 默认最多两个 direct；`N` 严格等于 server options 的 overflow 数量。
- current+next 是唯一 projection 窗口；previous 不进入当前 Dialog。
- 202/pending 不表示产物成功；REST facts/revisions 是刷新和重入 owner。
- 本阶段只新增任务一记录、`design_011` 和本评审记录；未修改生产代码，未执行归档。
