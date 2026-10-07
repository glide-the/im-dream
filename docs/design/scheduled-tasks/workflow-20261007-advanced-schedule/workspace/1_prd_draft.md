<!-- [Input] Codex.app 任务编辑截图、重复菜单截图、topic.txt 与现行 scheduled-tasks PRD。 -->
<!-- [Output] 高级重复规则、新聊天开关和模型选择的页面结构及产品需求草稿。 -->
<!-- [Pos] html-design-workflow 第 1 阶段过程证据；不替代 docs/prd/scheduled-tasks/ 下的正式 PRD。 -->
<!-- [Sync] 2026-10-07: 完成高级任务周期桌面/窄屏、配置语义、状态与错误草案。 -->

# 定时任务编辑弹窗：高级任务周期 PRD 草稿

> 本文是图片逆向与需求收敛后的过程草稿。正式产品规则仍应合并到 `docs/prd/scheduled-tasks/`，正式交互时序与状态图仍应写入 `docs/design/scheduled-tasks/`。截图中的红色矩形是标注范围，不是页面边框或品牌样式。

## 1. 背景与问题

现行定时任务已经具备 `once`、`daily`、`interval` 定义，Admin 负责 definition、revision、下一次运行时间、trigger 和运行历史，Dream 复用现有 TaskSession、Thread、Turn、事件流与持久化入口执行任务。当前编辑界面仍以“一次 / 每天 / 间隔”技术规则为主，缺少用户熟悉的“每小时、每天、工作日、每周、自定义”入口，也不能明确控制每次触发是在创建任务的原聊天中继续，还是新建独立聊天。

模型目前由普通 Chat 的当前选择决定，任务 definition 没有把用户选择的模型固定到 revision。若模型在后续停用、订阅变化或维护中不可调用，系统也缺少面向本次 trigger 的明确反馈。

本次把任务周期改为图片所示的五项重复菜单，并在“高级”折叠区加入两个配置：

- “每次运行时都开启新聊天”；关闭时在创建任务的源 Thread 中继续运行。
- “模型”；从当前用户可调用的 Admin 模型目录选择，并保存到任务 revision。

## 2. 目标与边界

### 2.1 目标

- 重复菜单按固定顺序提供“每小时、每天、工作日、每周、自定义”。
- “高级日程 / 编辑规则”承接日期、时间、时区、间隔和星期选择，不把复杂字段堆在首屏。
- 高级区只包含“每次运行时都开启新聊天”和“模型”。
- 新建任务默认关闭新聊天开关；关闭时运行目标是任务的 `source_thread_id`，开启时每个 trigger 创建独立 Thread。
- 模型选择来自当前用户的 Admin Gateway 模型目录，保存精确 `modelAlias`，trigger 执行前再次校验可调用性。
- 定义清楚桌面与窄屏布局、配置 revision、加载/保存/执行状态以及可恢复错误。
- 复用现有 `ScheduledTask`、`ScheduledTrigger`、`AdminScheduledTaskData`、`ScheduledTaskCoordinator`、TaskSession、Thread、Turn、SSE 和历史结果能力。

### 2.2 边界

- 不增加“项目”“归档成功运行记录”“强度”；它们虽出现在参考截图中，但不属于本轮需求。
- 不增加自然语言 cron 输入、月份规则、节假日日历、结束次数或通用工作流编排器。
- “工作日”固定指任务时区中的周一至周五，不推断法定节假日或调休。
- 不改变现有定时会话工具审批、Editor Session 目标、并发 open trigger、`state_unknown` 恢复和工具成功回执语义。
- 不让前端计算 effective schedule，不新增 Dream 数据表、runtime DDL、SQLite fallback 或第二套 scheduler。
- 不用“模型不可用时换成默认模型”作为降级策略。

## 3. 概念与配置规则

### 3.1 default、desired、effective、revision

| 概念 | 本功能中的定义 |
|---|---|
| default | 新建任务表单初始值。新聊天开关关闭；模型预选创建任务时当前可调用的模型；重复规则来自用户请求或任务创建上下文。default 不等于已保存。 |
| desired | 用户在弹窗中尚未保存的重复规则、Thread 模式与模型选择。关闭弹窗时按现有未保存草稿规则处理，不产生新的 definition。 |
| effective | Admin 事务成功提交的完整任务 definition。调度器只消费 effective，不读取浏览器临时值。 |
| revision | effective definition 的正整数版本。重复规则、新聊天开关或模型任一变化并保存后 revision 自增。 |

保存回执必须返回完整 effective definition。UI 用回执整体替换本地值；不能把单个成功字段与旧 definition 拼接。已领取的 trigger 保存 `definition_revision`、Thread 模式和 `modelAlias` 快照，后续编辑只影响下一次领取的 trigger。

### 3.2 重复菜单与规范化规则

“自定义”是编辑入口与展示分类，不建议作为数据库中的独立调度算法。Admin 仍保存可以计算 `next_run_at` 的规范化规则。

| 菜单项 | 用户看到的含义 | 建议的规范化规则 | “高级日程”可编辑内容 |
|---|---|---|---|
| 每小时 | 从创建、保存或恢复时点起，每 60 分钟运行一次 | 复用 `interval`，`interval_minutes=60` | 时区；展示下一次运行时间 |
| 每天 | 在任务时区中每天固定时刻运行 | 复用 `daily` | 本地时间、IANA 时区 |
| 工作日 | 在任务时区的周一至周五固定时刻运行 | 建议、未实现：`weekly`，星期集合为周一至周五 | 本地时间、IANA 时区 |
| 每周 | 每周在一个用户选择的星期和时刻运行 | 建议、未实现：`weekly`，星期集合为一个值 | 星期、本地时间、IANA 时区 |
| 自定义 | 编辑一次性、任意正整数分钟间隔或多个星期组合 | 复用 `once` / `interval` / `daily`；建议扩展 `weekly` | 规则类型、日期或间隔、星期集合、本地时间、IANA 时区 |

规则细节：

- 选择“每小时”后，第一次执行沿用 interval 的 `DB now + 60 minutes` 规则，不解释为下一个整点。
- 选择“每天、工作日、每周”必须有合法本地时间和 IANA 时区；“每周”还必须选择一个星期。
- 自定义 interval 接受正整数分钟；页面可以用“分钟 / 小时 / 天 / 周”帮助输入，但提交前转换成可精确表示的规范化值。日历日与固定分钟存在夏令时差异时，必须使用日历规则，不能偷换成分钟乘法。
- 自定义星期集合至少一个且不得重复。正好等于周一至周五时展示为“工作日”；正好一个星期时可展示为“每周”；其他组合展示为“自定义”。
- `once` 在重复菜单中显示为“自定义”，由“高级日程”中的“一次”规则表达，保留现有一次性任务能力。
- daily/weekly 的夏令时缺失或重复时刻继续使用现行调度规则；页面展示最终 `next_run_at`，不在浏览器自行推算。

### 3.3 每次运行时都开启新聊天

UI 使用 switch，持久层建议保存含义明确的枚举，而不是只保存界面布尔值：

```text
run_thread_mode = source_thread | new_thread_each_run
```

| 开关 | effective 语义 | trigger 结果入口 |
|---|---|---|
| 关闭（新建任务默认） | 每次 trigger 将新的 scheduled turn 追加到任务创建时保存的 `source_thread_id` | 打开源聊天，并定位到该 trigger 的 `target_turn_id` |
| 开启 | 每次 trigger 通过现有 TaskSession/Thread 创建能力生成独立运行 Thread | 打开该 trigger 的 `target_thread_id` |

补充规则：

- `source_thread_id` 在创建任务时由服务端从已认证当前 Thread 捕获；prompt、浏览器参数和后续最近打开聊天不能改写它。
- 关闭开关时不得因源 Thread 忙碌、删除、归档后不可继续、权限变化或持久化异常而静默创建新聊天。本次 trigger 明确失败并给出可行动反馈。
- 源 Thread 当前不能接纳输入时沿用现有 Thread admission 判断，本次 trigger 失败；用户可以“打开原聊天”查看状态或在任务详情中“立即运行”。
- 开启开关时，新 Thread 创建失败即为本次 trigger 失败；不得回退到源 Thread。
- 暂停、编辑和删除只影响后续 trigger；已经领取的 trigger 继续使用领取时快照。
- 存量任务在当前实现中每次 trigger 创建独立 Thread。正式迁移必须为存量 definition 保留 `new_thread_each_run`，避免因新增字段默认值而改变既有任务；只有新建任务的产品 default 为 `source_thread`。

### 3.4 模型选择

- 模型列表复用前端现有 `fetchGatewayModels()` 与 `/api/gateway/models`，只允许选择目录中 `enabled=true`、`callable=true`、`availability=included` 的 `modelAlias`。
- 下拉主文案使用 `displayName`，辅助文案可显示稳定的 `modelAlias`；不向用户展示协议、内部 capability、max output 或计费实现细节。
- 新建任务预选创建时当前有效模型；保存时把精确 `modelAlias` 写入任务 definition revision，不保存“自动”“默认”之类动态占位符。
- 编辑任务时优先展示 effective `modelAlias`。若该 alias 已停用或不在目录中，保留原值并标注“不可用”，不能悄悄选中目录默认模型。
- trigger 领取时将 `modelAlias` 与 `definition_revision` 一起快照。执行前使用同一用户身份再次校验目录与权限；不可用时本次 trigger 记为失败，definition 保持 active，后续仍按计划触发。
- 用户修改模型并保存后，只有新 trigger 使用新 alias；运行中或 `state_unknown` trigger 不换模型、不重放。
- 存量 definition 的模型回填应读取其源 Thread 已持久化的有效模型选择并记录精确 alias；无法解析时标记为“模型待选择”，不能把当时的 Admin 默认模型伪装成已保存值。

## 4. 页面模块结构

### 4.1 自上而下、自左至右

| 区块 | 模块名 | 图片中的具体形态 | 功能要求 |
|---|---|---|---|
| A1 | 弹窗框架 | 深灰色大圆角面板，右上角关闭图标；正文与底部操作分区 | 承载任务编辑；正文单一纵向滚动，桌面底部操作固定，关闭后焦点返回触发入口 |
| A2 | 标题与提示词 | 左上“编辑任务”；下方为大面积多行文本框 | 展示并编辑任务标题/提示词；沿用现有必填、长度和保存校验 |
| B1 | 重复选择行 | 圆角描边卡片第一行；左侧“重复”，右侧当前值与向下箭头 | 打开五项菜单；选中项有勾选；支持键盘方向键、Enter、Escape |
| B2 | 高级日程入口 | 与 B1 同一卡片第二行，以细分隔线隔开；左侧“高级日程”，右侧“编辑规则” | 打开受限规则编辑 sheet/dialog；自定义选中时立即进入编辑，取消则恢复先前 desired |
| C1 | 高级折叠标题 | 卡片下方独立“高级”文字和上/下箭头 | 展开或收起高级配置；仅影响可见性，不修改 desired 值 |
| C2 | 新聊天开关 | 圆角单行卡片；左侧标签，右侧蓝色 switch | 映射 `run_thread_mode`；关闭为源 Thread，开启为每次新建 Thread |
| C3 | 模型选择 | 圆角单行卡片；左侧“模型”，右侧模型名与箭头 | 打开可调用模型菜单；加载、空目录、不可用旧值和请求失败都有行内状态 |
| D1 | 底部操作 | 右下并排“暂停/恢复”和“保存”；主按钮用高对比填充 | 保存提交整个 desired + expected revision；按钮按 task 状态显示暂停或恢复；执行中避免重复提交 |

参考图中“归档成功运行记录、项目、强度”三行不进入本轮页面。高级展开后，C2 与 C3 直接相邻；不保留空白占位行。

### 4.2 视觉与层级

- 延续现有深色界面：弹窗底色为深炭灰，字段卡片略深或略亮一阶，描边为低对比中灰，主文字为近白，次文字为浅灰。
- 卡片使用大圆角和充足上下留白。重复与高级日程共用一个卡片，两个高级字段各自为一张卡片。
- switch 开启使用当前产品蓝色，关闭为中灰；错误使用现有危险色文字与字段描边，不用整块红色高亮。
- 参考图外层红色矩形只用于指出需求区域，成品中不渲染。
- “重复”是主要频率摘要；“高级日程”显示补充摘要，例如“周一至周五 · 09:00 · Asia/Shanghai”，让用户不进入二级编辑也能检查结果。

## 5. 桌面与窄屏页面骨架

### 5.1 桌面弹窗

```text
┌────────────────────────── 编辑任务 ────────────────────────── [×] ┐
│ 任务标题 / 提示词                                               │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ 多行任务内容；该区域按现有编辑能力展示                       │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ 重复                                      工作日         [⌄] │ │
│ ├─────────────────────────────────────────────────────────────┤ │
│ │ 高级日程                    周一至周五 · 09:00       编辑规则 │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                │
│ 高级 [⌃]                                                       │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ 每次运行时都开启新聊天                              [开关]  │ │
│ └─────────────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ 模型                                      GPT-5.6 Sol    [⌄] │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                │
│ 行内错误或 revision 冲突信息                                    │
├────────────────────────────────────────────────────────────────┤
│                                           [暂停/恢复]   [保存]  │
└────────────────────────────────────────────────────────────────┘
```

- 弹窗不超过可视区；标题栏和底部操作固定，只有中间正文滚动。
- 重复菜单定位在 B1 右侧下方，宽度容纳最长标签；不遮挡底部按钮。
- “高级日程”打开二级 dialog/sheet。关闭后焦点返回“编辑规则”。
- 高级区默认收起；模型不可用、模型目录失败或新聊天相关错误需要用户处理时自动展开并把焦点移到错误摘要。

### 5.2 窄屏 sheet

```text
┌────────────── 编辑任务（全高 sheet） ──────────────┐
│ [返回]                 编辑任务              [关闭] │  ← 固定
├────────────────────────────────────────────────────┤
│ 任务标题 / 提示词                                  │
│                                                    │
│ ┌────────────────────────────────────────────────┐ │
│ │ 重复                                   工作日⌄ │ │
│ ├────────────────────────────────────────────────┤ │
│ │ 高级日程                                  编辑 │ │
│ │ 周一至周五 · 09:00 · Asia/Shanghai           │ │
│ └────────────────────────────────────────────────┘ │
│                                                    │
│ 高级 ⌃                                            │
│ ┌ 每次运行时都开启新聊天                   [开关] ┐ │
│ └────────────────────────────────────────────────┘ │
│ ┌ 模型                                  GPT-5.6⌄ ┐ │
│ └────────────────────────────────────────────────┘ │
│ 行内反馈                                           │  ← 正文滚动
├────────────────────────────────────────────────────┤
│                              [暂停/恢复]   [保存]  │  ← 固定
└────────────────────────────────────────────────────┘
```

- 窄屏采用全高 sheet 和单列布局，不在右侧弹出容易越界的浮层。
- 重复菜单、模型菜单和高级日程编辑器使用底部 sheet；每次只显示一层可交互面板。
- sheet 内容超高时自身滚动，背景 Chat/Calendar 锁定滚动。底部安全区不能遮挡“保存”。
- 标签过长时允许左侧文本换行，右侧当前值保持可读；模型 displayName 过长时单行省略，并在选项列表显示完整值。

## 6. 交互流程

### 6.1 编辑重复规则

1. 用户点击“重复”，菜单展示“每小时、每天、工作日、每周、自定义”，当前 desired 右侧显示勾选。
2. 选择简单预设后，B1 立即更新标签，B2 更新规则摘要；涉及时间或星期且字段尚未完整时，自动打开“高级日程”。
3. 选择“自定义”时打开规则编辑器；用户完成规则后点击“应用”回到任务弹窗，规则仍是 desired，尚未提交 Admin。
4. 用户点击“保存”，前端提交完整 desired 和 `expected_revision`。
5. Admin 返回新 effective revision 后，弹窗与任务卡用回执更新；失败则保留 desired，不伪造成功。

### 6.2 配置运行聊天

1. 用户展开“高级”。新建任务的开关默认关闭，编辑任务显示 effective 值。
2. 关闭时，说明文字为“在创建此任务的聊天中继续运行”；开启时为“每次运行都会创建独立聊天”。
3. 保存成功后，新 trigger 使用新 mode。已在 `claimed/queued/running/state_unknown` 的 trigger 保持领取时 mode。
4. 历史列表的“打开聊天”始终读取 trigger 的 `target_thread_id` 与 `target_turn_id`，不根据当前 switch 重新判断。

### 6.3 选择模型

1. 展开高级区时加载当前用户 Admin 模型目录；同一弹窗会话内复用已成功结果，重新打开时刷新。
2. 用户打开模型菜单，只能选可调用项。effective alias 已不可用时仍显示在顶部，带“不可用”标记但不能再次选择。
3. 用户选择模型，desired 立即更新；直到保存成功，任务仍使用旧 effective model。
4. trigger 开始执行前，服务端再次校验 alias。校验失败则写入 trigger 错误并结束本次运行，不启动其他模型。

## 7. 状态、反馈与恢复

### 7.1 表单状态

| 状态 | 页面行为 |
|---|---|
| idle | 显示 effective 值；保存仅在 desired 有变化且字段完整时可用。 |
| loading_catalog | 模型行显示轻量加载状态；保留已有 alias，不清空字段。 |
| editing | 字段变化只更新 desired；重复摘要和高级摘要同步预览。 |
| saving | 保存按钮显示进行中并防止重复提交；关闭行为沿用现有未保存草稿规则。 |
| revision_conflict | 保留用户 desired，获取最新 effective，列出“重复 / 新聊天 / 模型”中发生冲突的字段，允许用户检查后重新保存。 |
| saved | 使用服务端回执替换本地 definition，关闭弹窗或显示现有成功反馈。 |

### 7.2 错误与可行动反馈

| 场景 | 结果 | 用户反馈与动作 |
|---|---|---|
| 模型目录加载失败 | 不清空已保存 alias；新建任务不能完成模型选择 | “模型目录暂不可用，请重试”，提供“重试” |
| 目录为空或无可调用模型 | 禁止新建/保存缺少有效模型的 revision | “当前没有可调用模型”，提供“查看模型与订阅设置” |
| 已保存模型停用、权限不足、额度耗尽或维护 | 本次 trigger `failed`；definition 保持 active | 最近结果显示具体可公开原因，提供“选择其他模型”或相应设置入口 |
| 源 Thread 不存在、无权限或不能接纳 turn | `source_thread` 模式的本次 trigger `failed` | “无法在原聊天中运行”，提供“打开原聊天”和“改为每次新建聊天” |
| 新 Thread 创建失败 | `new_thread_each_run` 模式的本次 trigger `failed` | “新聊天创建失败”，提供“重试本次运行”；不回退到原聊天 |
| 重复规则缺字段或本地时间无效 | 不提交 | 错误贴近日期、时间、星期或时区字段；高级日程自动展开 |
| `SCHEDULE_REVISION_CONFLICT` | 不覆盖他人/其他页面的新 definition | 保留 desired、载入最新 effective、提示重新检查并保存 |
| capability 或 Admin 不可用 | 不在浏览器创建 timer，也不局部保存 | “定时任务暂不可用”，保留 desired 并提供重试 |
| trigger `state_unknown` | 不重放模型 | 最近结果显示“正在确认运行结果”，保留“打开聊天” |

错误信息不得暴露内部堆栈、数据库字段或凭证。模型错误可以展示 Admin 返回的面向用户原因，但不能通过 displayName 猜测权限或可用性。

## 8. 状态转换摘要

### 8.1 definition

```text
default ──编辑──> desired ──保存且 revision 匹配──> effective(active)
                         └─冲突/校验失败──────────> desired 保留

active ──pause──> paused ──resume──> active
active/paused/exhausted ──delete──> deleted
once active ──成功领取到期 trigger──> exhausted
```

### 8.2 trigger 与 Thread 目标

```text
claimed -> queued -> running -> succeeded | failed | state_unknown

definition.run_thread_mode=source_thread
  -> target_thread_id = source_thread_id
  -> 新建 target_turn_id

definition.run_thread_mode=new_thread_each_run
  -> 创建 TaskSession/Thread
  -> target_thread_id = 新 Thread
  -> 新建 target_turn_id
```

任何 Thread 创建或接纳失败都进入 `failed`，两种 mode 之间不自动切换。`state_unknown` 继续使用现行持久化重查，不重复执行模型。

## 9. 技术建议

### 9.1 复用点

- 前端复用 `CalendarPopup` 的任务编辑、`Modal`/sheet、`scheduledTaskApi.ts` 的 revision action 与 `gatewayModelsApi.ts` 的严格模型目录解析。
- Admin 继续拥有 rule 校验、`next_run_at`、revision 比较、trigger 快照和历史；Dream 浏览器层只传 typed DTO。
- `ScheduledTaskCoordinator` 继续调用现有生产入口。Thread mode 只决定 prepare 阶段使用源 Thread 还是创建 Thread，不复制 Turn、SSE 或持久化流程。
- 运行结果继续使用 `ScheduledTrigger.target_thread_id`、`target_turn_id`、`final_message_id`；关闭新聊天时允许多个 trigger 指向同一 Thread，但每个 trigger 仍绑定自己的 turn。

### 9.2 建议、未实现的数据扩展

```text
ScheduledTask
  run_thread_mode: source_thread | new_thread_each_run
  model_alias: string

ScheduledRule
  weekly:
    weekdays: ISO weekday set
    local_time: HH:mm
    time_zone: IANA zone

ScheduledTrigger snapshot
  run_thread_mode
  model_alias
```

- 新增表字段、索引或约束必须先由 Admin Drizzle 提交前向 migration 与新 capability；Dream 只能依赖已发布 capability，缺失时 fail closed。
- 建议发布新的 additive scheduled-task capability，保留当前 v2 的 once/daily/interval 合同供双版本兼容；正式设计稿再确定 capability 名称和 DTO hash，本文不把建议名伪装成已实现接口。
- Admin 保存前重新校验 `source_thread_id` owner、模型 alias 格式、rule 闭集和 revision。模型运行可调用性在 trigger 启动前复查。
- 模型 alias 只能来自 Admin 返回目录或存量精确值，不在 Gateway 按字符串猜测模型能力，不允许浏览器环境覆盖。

## 10. 验收标准

- 桌面和窄屏的重复菜单均按“每小时、每天、工作日、每周、自定义”顺序展示，当前项有明确选中状态。
- 每小时映射现有 60 分钟 interval；每天复用 daily；工作日和每周按任务时区正确计算；自定义可覆盖 once、正整数分钟 interval 和星期组合。
- “工作日”只代表周一至周五，页面不声称处理法定节假日。
- 高级区只出现“每次运行时都开启新聊天”和“模型”，不出现项目、归档成功记录或强度。
- 新建任务开关默认关闭。关闭后 trigger 在 `source_thread_id` 创建新 turn；开启后每次 trigger 获得不同 `target_thread_id`。
- 两种 Thread mode 失败时均有明确历史错误，且不会静默切换 mode。
- 模型选项来自当前用户 Admin 目录，保存精确 alias 到 revision；旧 alias 不可用时保留展示并要求用户处理。
- 模型在执行时不可调用会令本次 trigger 失败；不自动替换，不影响 definition 后续继续调度。
- 编辑重复规则、Thread mode 或模型都会推进 revision；open trigger 继续使用原快照。
- revision 冲突保留 desired 并展示最新 effective，不覆盖其他编辑结果。
- 桌面正文单一滚动、标题/底部操作固定；窄屏为全高 sheet，菜单与规则编辑器不越出视口。
- 键盘可以完成菜单、switch、模型选择、保存与关闭；焦点返回、错误关联和可访问名称完整。
- 现有暂停、恢复、删除、立即运行、历史、“打开聊天”、open trigger 去重、`state_unknown` 重查和工具审批回归通过。
