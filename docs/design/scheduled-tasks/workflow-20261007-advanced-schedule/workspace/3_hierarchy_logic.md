<!-- [Input] workflow 第 1 阶段 PRD、第 2 阶段结构草图、任务编辑截图、重复菜单截图与 topic.txt。 -->
<!-- [Output] 高级任务周期的精炼页面分区、信息层级树、交互状态、依赖关系和组件层级。 -->
<!-- [Pos] html-design-workflow 第 3 阶段过程证据；供最终 UI 设计与正式交互设计继续细化。 -->
<!-- [Sync] 2026-10-07: 统一 default/desired/effective/revision、重复规则、Thread 路径、模型校验和响应式面板层级。 -->

# 定时任务编辑弹窗：信息层级与交互逻辑

> 本文综合第 1 阶段 PRD、第 2 阶段结构草图与参考截图。A—M 编号沿用第 2 阶段定义；截图外层红框仅用于标注需求范围，不属于界面。高级区只包含新聊天配置和模型选择，不包含截图中的归档、项目和强度。

## 1. 页面结构草图（模块分区，精炼版）

### 1.1 桌面主弹窗

```text
页面遮罩：原 Chat / Calendar 保留上下文，但暂停交互与背景滚动
┌──────────────────────────────────────────────────────────────────────────────┐
│ ┌─ A1 任务编辑弹窗：最大高度受视口约束 ────────────────────────────────────┐ │
│ │ ┌─ A2 固定标题栏 ───────────────────────────────────────────────────────┐ │ │
│ │ │ 编辑任务                                                        [×] │ │ │
│ │ └─────────────────────────────────────────────────────────────────────┘ │ │
│ │ ┌─ A3 正文：主弹窗唯一纵向滚动区 ─────────────────────────────────────┐ │ │
│ │ │ ┌─ B1 任务标题 / 提示词 ─────────────────────────────────────────┐ │ │ │
│ │ │ │ 多行任务内容；必填、长度和字段内部行为沿用现有编辑能力           │ │ │ │
│ │ │ └────────────────────────────────────────────────────────────────┘ │ │ │
│ │ │                                                                    │ │ │
│ │ │ ┌─ C1 日程卡片 ──────────────────────────────────────────────────┐ │ │ │
│ │ │ │ C2 重复：频率分类                         工作日            [⌄] │ │ │ │
│ │ │ ├────────────────────────────────────────────────────────────────┤ │ │ │
│ │ │ │ C3 高级日程：规则摘要       周一至周五 · 09:00 · Asia/Shanghai │ │ │ │
│ │ │ │                                                     [编辑规则] │ │ │ │
│ │ │ └────────────────────────────────────────────────────────────────┘ │ │ │
│ │ │                                                                    │ │ │
│ │ │ D1 高级 [⌃/⌄]：只控制 D2 可见性，不修改任何 desired 值             │ │ │
│ │ │ ┌─ D2 高级配置容器（展开态）────────────────────────────────────┐ │ │ │
│ │ │ │ ┌─ D3 新聊天配置 ───────────────────────────────────────────┐ │ │ │ │
│ │ │ │ │ 每次运行时都开启新聊天                         D4 [开关] │ │ │ │ │
│ │ │ │ │ D5 关闭：在创建此任务的聊天中继续运行                     │ │ │ │ │
│ │ │ │ │    开启：每次运行都会创建独立聊天                         │ │ │ │ │
│ │ │ │ └────────────────────────────────────────────────────────────┘ │ │ │ │
│ │ │ │ ┌─ D6 模型选择 ─────────────────────────────────────────────┐ │ │ │ │
│ │ │ │ │ 模型                                      GPT-5.6 Sol [⌄] │ │ │ │ │
│ │ │ │ │ D7 加载 / 空目录 / 不可用旧值 / 失败 / 重试               │ │ │ │ │
│ │ │ │ └────────────────────────────────────────────────────────────┘ │ │ │ │
│ │ │ └────────────────────────────────────────────────────────────────┘ │ │ │
│ │ │ E1 表单反馈：字段错误 / revision 冲突 / 保存失败 / 恢复动作       │ │ │
│ │ └─────────────────────────────────────────────────────────────────────┘ │ │
│ │ ┌─ A4 固定底部操作栏 ───────────────────────────────────────────────┐ │ │
│ │ │                                     F1 [暂停/恢复]   F2 [保存]    │ │ │
│ │ └─────────────────────────────────────────────────────────────────────┘ │ │
│ └────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

结构意图：A2 和 A4 始终可见；A3 负责页面级滚动。C2 提供可快速识别的频率分类，C3 补充日期、星期、时间和时区。D1 收起后，D4 与 D6 的草稿值仍保留。E1 汇总阻止保存的页面级问题，字段问题仍贴近原字段展示。

### 1.2 桌面叠层关系

```text
A1 任务编辑弹窗
│
├── C2 重复选择
│   └── G1 锚定重复菜单（内部超高时独立滚动）
│       ├── G2 每小时：interval_minutes = 60
│       ├── G3 每天：daily
│       ├── G4 工作日：weekly，星期一至星期五（建议、未实现）
│       ├── G5 每周：weekly，单个星期（建议、未实现）
│       └── G6 自定义：进入 H1，不作为独立调度算法保存
│
├── C3 高级日程
│   └── H1 二级 dialog（A1 暂停交互并保留滚动位置）
│       ├── H2 固定标题栏与关闭入口
│       ├── H3 规范化规则类型：一次 / 间隔 / 每天 / 每周
│       ├── H4 条件字段区
│       │   ├── H5 一次：日期 + 本地时间
│       │   ├── H6 间隔：正整数 + 分钟/小时/天/周
│       │   ├── H7 每天：本地时间
│       │   └── H8 每周：至少一个且不重复的 ISO 星期
│       ├── H9 IANA 时区
│       ├── H10 规范化摘要 + 服务端 next_run_at
│       ├── H11 字段错误 / 计算失败
│       ├── H12 取消：丢弃 H1 本次未应用修改，焦点返回 C3
│       └── H13 应用：只写回表单 desired，仍需 F2 保存
│
└── D6 模型选择
    └── J1 锚定模型菜单（内部超高时独立滚动）
        ├── J2 当前有效模型：展示名 + modelAlias + 勾选
        ├── J3 其他可调用模型：可选
        └── J4 已保存但当前不可用的旧模型：保留展示、禁选
```

G1 和 J1 都受视口碰撞检测约束：默认向下打开，空间不足时向上翻转，不能遮挡 A4。H1 是模态二级面板，一次只允许该面板接收输入。

### 1.3 窄屏主面板与子面板

```text
┌─ K1 全高任务编辑 sheet：宽度 = 视口；背景锁定滚动 ───────────────────┐
│ ┌─ K2 固定标题栏 ─────────────────────────────────────────────────┐ │
│ │ [返回]                    编辑任务                         [关闭] │ │
│ └────────────────────────────────────────────────────────────────┘ │
│ ┌─ K3 正文：窄屏主面板唯一纵向滚动区 ─────────────────────────────┐ │
│ │ B1 任务标题 / 提示词                                            │ │
│ │ C1 日程卡片                                                      │ │
│ │ ├── C2 重复：工作日 [⌄]                                         │ │
│ │ └── C3 高级日程：周一至周五 · 09:00 · Asia/Shanghai [编辑规则]   │ │
│ │ D1 高级 [⌃/⌄]                                                    │ │
│ │ └── D2 展开内容                                                  │ │
│ │     ├── D3 新聊天配置：D4 开关 + D5 状态说明                     │ │
│ │     └── D6 模型选择：模型名 [⌄] + D7 状态/重试                   │ │
│ │ E1 表单反馈                                                      │ │
│ └────────────────────────────────────────────────────────────────┘ │
│ ┌─ K4 固定操作栏 + 底部安全区 ───────────────────────────────────┐ │
│ │                               F1 [暂停/恢复]       F2 [保存]    │ │
│ └────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘

C2 ──打开──> L1 重复选项 bottom sheet
              ├── L2 拖动柄
              ├── L3 固定标题栏
              └── G2 / G3 / G4 / G5 / G6

C3 ──打开──> M1 高级日程 bottom sheet
              ├── M2 固定标题栏
              ├── M3 内部滚动区：H3—H11
              └── 固定操作区：H12 / H13 + 底部安全区

D6 ──打开──> 模型 bottom sheet（复用 L1 容器形态）
              └── J2 / J3 / J4；列表超高时内容区独立滚动
```

窄屏一次只显示一层可交互子面板。打开 L1、M1 或模型 bottom sheet 时，K1 保留草稿和滚动位置但暂停交互；关闭后焦点分别返回 C2、C3 或 D6。K2、K4 固定，K3 是主面板唯一页面级滚动区；M3 和各菜单内容只负责自身溢出。

## 2. 页面层级结构图（逻辑树）

```text
Root 定时任务编辑体验
│
├── 展示适配层
│   ├── DesktopRoot
│   │   └── A1 任务编辑弹窗
│   │       ├── A2 固定标题栏：关闭与焦点返回
│   │       ├── A3 正文滚动区：承载主表单 B1—E1
│   │       └── A4 固定操作栏：承载 F1、F2
│   └── NarrowRoot
│       └── K1 全高任务编辑 sheet
│           ├── K2 固定标题栏：返回、关闭与焦点返回
│           ├── K3 正文滚动区：复用主表单 B1—E1
│           └── K4 固定操作栏：复用 F1、F2并处理底部安全区
│
├── 任务内容层
│   └── B1 任务标题 / 提示词
│       └── 目的：沿用现有内容编辑、必填和长度校验
│
├── 日程配置层
│   └── C1 日程卡片
│       ├── C2 重复分类
│       │   ├── 桌面入口：G1
│       │   ├── 窄屏入口：L1
│       │   ├── 简单预设：G2 每小时 / G3 每天 / G4 工作日 / G5 每周
│       │   └── 自定义入口：G6 -> H1（桌面）或 M1（窄屏）
│       └── C3 高级日程
│           ├── 只读摘要：日期 / 星期 / 本地时间 / IANA 时区
│           └── 规则编辑：H3—H13
│               ├── 规范化规则类型：once / interval / daily / weekly
│               ├── 条件字段：H5—H8
│               ├── 时区：H9
│               ├── 服务端结果：H10
│               ├── 校验反馈：H11
│               └── 草稿动作：H12 取消 / H13 应用到 desired
│
├── 高级运行配置层
│   ├── D1 展开控制：仅改变 D2 可见性
│   └── D2 高级配置容器
│       ├── D3 新聊天配置
│       │   ├── D4 开关
│       │   └── D5 当前 Thread 路径说明
│       │       ├── source_thread：在创建任务时捕获的源 Thread 中新增 turn
│       │       └── new_thread_each_run：每个 trigger 创建独立 Thread
│       └── D6 模型配置
│           ├── D7 目录加载、旧值状态、失败与重试
│           ├── 桌面入口：J1
│           └── 窄屏入口：模型 bottom sheet
│               ├── J2 当前有效模型
│               ├── J3 其他可调用模型
│               └── J4 不可用旧模型
│
├── 反馈与提交层
│   ├── E1 表单级反馈
│   │   ├── 字段或目录错误
│   │   ├── SCHEDULE_REVISION_CONFLICT
│   │   └── 保存失败与恢复动作
│   └── F 操作
│       ├── F1 暂停 / 恢复：改变 effective 任务状态
│       └── F2 保存：提交完整 desired + expected_revision
│
└── 运行结果层（复用现有任务详情与历史入口，不新增主弹窗模块）
    ├── source_thread 结果：target_thread_id = source_thread_id，定位 target_turn_id
    ├── new_thread_each_run 结果：打开 trigger 的 target_thread_id
    └── trigger 错误：显示可公开原因与对应恢复动作
```

层级关系中，DesktopRoot 与 NarrowRoot 共享同一业务表单和同一 desired；二者只改变容器、弹层形式和滚动边界，不形成两套任务定义或保存逻辑。

## 3. 组件层级与职责

| 父级 | 子级 | 逻辑职责 | 关键输入 | 关键输出 |
|---|---|---|---|---|
| A1 / K1 | A2/K2、A3/K3、A4/K4 | 管理主面板焦点、滚动和固定区域 | 当前任务、打开来源 | 关闭或保存后的焦点返回 |
| A3 / K3 | B1、C1、D1/D2、E1 | 组织可滚动表单内容 | effective 与 desired | 可提交的完整 desired |
| C1 | C2、C3 | 同时展示频率分类与完整规则摘要 | desired schedule | 菜单选择或规则编辑入口 |
| C2 | G1 / L1 | 选择简单预设或进入自定义 | 当前 desired 分类 | 更新分类、打开 H1/M1 |
| H1 / M1 | H2/H3/H4/H9/H10/H11/H12/H13 | 编辑并校验规范化规则 | 打开前 desired schedule | 取消或应用后的 desired schedule |
| H4 | H5/H6/H7/H8 | 只显示当前规则类型所需字段 | H3 规则类型 | 日期、间隔、时间或星期值 |
| D2 | D3、D6 | 承载本轮全部高级运行配置 | desired Thread 模式与模型 | 更新后的 desired |
| D3 | D4、D5 | 映射开关值并解释运行目标 | run_thread_mode | `source_thread` 或 `new_thread_each_run` |
| D6 | D7、J1/模型 sheet | 从用户模型目录选择精确 alias | effective alias、目录状态 | desired `modelAlias` |
| J1 / 模型 sheet | J2/J3/J4 | 区分可选项与不可用旧值 | Admin 模型目录 | 精确 `modelAlias` 或保持旧值 |
| A4 / K4 | F1、F2 | 执行任务状态动作和定义保存 | effective 状态、desired、expected revision | 完整 effective 回执或错误 |

## 4. 配置语义：default、desired、effective、revision

### 4.1 四层定义

| 层 | 所有者与来源 | 页面用途 | 允许影响运行 | 转换条件 |
|---|---|---|---|---|
| `default` | 新建任务表单初始化 | 给出首次可编辑起点：新聊天关闭、预选创建时当前可调用模型、重复规则来自用户请求或创建上下文 | 否 | 用户编辑后形成 `desired`；`default` 本身不代表已保存 |
| `desired` | 当前弹窗草稿 | 汇总 B1、schedule、run_thread_mode、modelAlias 的未保存选择 | 否 | F2 提交完整 desired 且 expected revision 匹配后，服务端生成新 effective |
| `effective` | Admin 事务提交成功后的完整 definition | 作为已保存展示基线，并由调度器消费 | 是 | 只接受服务端完整回执；页面不得把单字段成功与旧 definition 拼接 |
| `revision` | effective definition 的正整数版本 | 并发编辑检查与 trigger 快照标识 | 间接 | 重复规则、Thread 模式或模型任一保存变更后自增；冲突时保留 desired 并载入最新 effective |

```text
新建任务
  default
     │ 用户编辑任一字段
     ▼
  desired ──H13 应用规则──> desired（只更新表单草稿）
     │
     ├──F2 保存 + expected_revision 匹配──> Admin 提交完整 definition
     │                                        │
     │                                        ▼
     │                                  effective + revision+1
     │                                        │
     │                         完整回执整体替换页面保存基线
     │
     └──字段校验/目录失败/revision 冲突──> desired 保留
                                              └──展示错误与恢复动作
```

### 4.2 保存与触发边界

- H13 只把规则编辑器结果应用到当前 `desired`；F2 才提交完整任务 definition。
- F2 在没有变化、字段不完整或正在保存时不可提交；保存中阻止重复请求。
- `SCHEDULE_REVISION_CONFLICT` 不覆盖最新 effective。页面保留 desired，同时加载最新 effective，并指出重复规则、新聊天或模型中发生差异的字段。
- trigger 领取时快照 `definition_revision`、规范化规则、`run_thread_mode` 和 `modelAlias`。后续编辑只影响尚未领取的新 trigger。
- 已处于 `claimed`、`queued`、`running` 或 `state_unknown` 的 trigger 继续使用领取时快照，不改模型、不换 Thread 模式、不重放。

## 5. 重复规则交互状态

### 5.1 简单预设与自定义的分流

```text
C2 打开 G1 / L1
│
├── G2 每小时
│   └── desired.schedule = interval(60 分钟)
│       └── 首次执行沿用 DB now + 60 minutes，不解释为下一个整点
│
├── G3 每天
│   └── desired.schedule = daily(本地时间, IANA 时区)
│       └── 缺少时间或时区 -> 打开 H1 / M1 补齐
│
├── G4 工作日
│   └── desired.schedule = weekly(星期一至星期五, 本地时间, IANA 时区)
│       └── weekly 为建议、未实现；缺少字段 -> 打开 H1 / M1
│
├── G5 每周
│   └── desired.schedule = weekly(一个星期, 本地时间, IANA 时区)
│       └── weekly 为建议、未实现；缺少字段 -> 打开 H1 / M1
│
└── G6 自定义
    └── 立即打开 H1 / M1
        ├── H12/关闭 -> 恢复打开前 desired
        └── H13 应用 -> 写回规范化 once / interval / daily / weekly
```

“自定义”是 UI 分类和规则编辑入口。保存层接收可计算 `next_run_at` 的规范化规则，不保存一个名为 custom 的调度算法。规范化结果恰好为周一至周五时，C2 显示“工作日”；恰好一个星期时显示“每周”；其他星期组合、once 或一般 interval 显示“自定义”。

### 5.2 规则编辑器状态

| 状态 | 入口 | 页面行为 | 离开结果 |
|---|---|---|---|
| `closed` | 主表单 | C3 显示当前 desired 摘要 | 点击 C3 或 G6 进入 editing |
| `editing` | H1 / M1 | H4 随 H3 只显示当前规则类型字段 | H12 放弃；H13 进入 validating |
| `validating` | H13 | 校验日期、正整数间隔、星期集合、本地时间与 IANA 时区 | 失败回 editing 并写 H11；成功进入 applied |
| `applied` | 校验通过 | 关闭编辑器，更新 C2/C3 与主表单 desired | F2 保存前不影响 effective |
| `calculation_failed` | 服务端无法返回规则摘要或 next_run_at | H11 显示失败原因和重试 | 修正字段或重试后回 validating |

日历日规则必须按任务时区解释，不能用固定分钟替换。页面展示服务端返回的 `next_run_at`，不在浏览器计算 effective schedule。

## 6. Thread 目标状态与运行路径

### 6.1 编辑状态

```text
新建任务 default：D4 关闭
    └── desired.run_thread_mode = source_thread

D4 关闭 ──用户开启──> desired.run_thread_mode = new_thread_each_run
D4 开启 ──用户关闭──> desired.run_thread_mode = source_thread

D1 收起/展开：只改变 D2 可见性；不改变 desired.run_thread_mode
F2 保存成功：effective.run_thread_mode = 服务端完整回执中的值
```

存量任务当前行为是每次 trigger 创建独立 Thread。迁移时应把存量 effective 固定为 `new_thread_each_run`；“默认关闭”只适用于新建任务，不能借字段缺省值改写存量行为。

### 6.2 trigger 执行路径

```text
trigger 领取
  └── 快照 definition_revision + run_thread_mode + modelAlias
      │
      ├── run_thread_mode = source_thread
      │   ├── 读取任务创建时由服务端捕获的 source_thread_id
      │   ├── 校验 owner / 权限 / Thread 存在 / admission
      │   ├── 通过 -> target_thread_id = source_thread_id -> 创建 target_turn_id
      │   └── 失败 -> trigger failed
      │              └── “无法在原聊天中运行” + 打开原聊天 / 修改后续模式
      │
      └── run_thread_mode = new_thread_each_run
          ├── 通过现有 TaskSession / Thread 入口创建独立 Thread
          ├── 成功 -> 保存新 target_thread_id -> 创建 target_turn_id
          └── 失败 -> trigger failed
                     └── “新聊天创建失败” + 重试本次运行
```

两条路径都复用现有 Turn、SSE、持久化和结果入口。任何一条路径失败时都不自动切换到另一种 Thread 模式。历史“打开聊天”始终读取 trigger 已保存的 `target_thread_id` 与 `target_turn_id`，不根据当前开关重新推断。

## 7. 模型目录、任务快照与触发校验

### 7.1 模型配置依赖链

```text
Admin Gateway 模型目录
  └── fetchGatewayModels() / GET /api/gateway/models
      ├── enabled = true
      ├── callable = true
      └── availability = included
          │
          ▼
      D6 / D7 页面投影
          ├── J2 当前有效 modelAlias
          ├── J3 其他可调用 modelAlias
          └── J4 effective 旧值已不可用：保留展示、禁选、不得静默替换
          │
          ▼ 用户选择精确 alias
      desired.modelAlias
          │ F2 保存完整 definition
          ▼
      effective.modelAlias + revision
          │ trigger 领取
          ▼
      ScheduledTrigger 快照：modelAlias + definition_revision
          │ 执行前用同一用户身份再次查询/校验目录与权限
          ├── 可调用 -> 使用快照 alias 启动现有运行入口
          └── 不可调用 -> 本次 trigger failed
                         ├── definition 保持 active，后续仍按计划触发
                         └── 展示可公开原因与“选择其他模型”或设置入口
```

模型主文案使用 `displayName`，辅助文案显示稳定 `modelAlias`。页面不保存“自动”或“默认”等动态占位符；模型执行失败时也不切换到目录默认模型。

### 7.2 模型行状态

| 状态 | D6 / D7 表现 | 保存条件 | 恢复动作 |
|---|---|---|---|
| `idle` | 展示 effective 或 desired 的模型 | alias 可调用且表单完整时可保存 | 打开菜单选择 |
| `loading_catalog` | 保留已有 alias，显示轻量加载 | 新建任务未取得有效 alias 时不可保存 | 等待或重试 |
| `catalog_ready` | J2/J3 可选，当前项有勾选 | 选择精确 alias 后形成 desired | F2 保存 |
| `catalog_empty` | “当前没有可调用模型” | 不可保存缺少有效模型的新 revision | 打开模型与订阅设置 |
| `catalog_failed` | “模型目录暂不可用，请重试” | 不清空 effective 旧值；新建任务不能完成选择 | 重试 |
| `saved_alias_unavailable` | J4 保留旧值并标注不可用 | 必须选择新的可调用 alias 才能保存相关变更 | 选择其他模型 |

## 8. 主表单交互状态

```text
idle（展示 effective）
  │ 修改 B1 / schedule / Thread 模式 / modelAlias
  ▼
editing（desired 与 effective 有差异）
  │ F2 + 字段完整 + 模型可调用
  ▼
saving（防重复提交）
  ├── 成功 -> saved -> 用完整回执替换 effective、desired 与 revision 基线
  ├── revision 冲突 -> revision_conflict
  │                    ├── 保留 desired
  │                    ├── 载入最新 effective
  │                    └── 检查差异后重新保存
  └── 其他失败 -> editing
                  └── E1 显示失败原因与重试

effective 任务状态：active ──F1 暂停──> paused ──F1 恢复──> active
```

模型目录问题或新聊天配置错误需要处理时，页面可以自动展开 D1 并把焦点移到 D7 或 E1。关闭行为沿用现有未保存草稿规则；本阶段不新增额外确认弹窗。

## 9. 业务依赖关系

| 上游 | 下游 | 依赖内容 | 失败处理 |
|---|---|---|---|
| 当前已认证 Thread | 任务创建 | 服务端捕获不可由 prompt 或浏览器参数改写的 `source_thread_id` | 缺失或权限失败则不生成可在源 Thread 运行的 effective definition |
| C2 / H1 / M1 | Admin schedule 校验 | 规范化 once、interval、daily、weekly 及 IANA 时区 | 字段错误进入 H11；capability 不可用则 fail closed |
| Admin schedule | C3 / H10 | 服务端返回摘要所需值与 `next_run_at` | 不在浏览器自行计算 effective schedule |
| Admin 模型目录 | D6 / J1 / 模型 sheet | 当前用户可调用模型与旧 alias 状态 | 保留旧值，显示重试或选择动作，不猜测可用性 |
| desired + expected revision | Admin definition 保存 | 一次提交重复规则、Thread 模式与 modelAlias | 冲突时保留 desired，不局部拼接 effective |
| effective definition | 调度器 | 只消费已提交 definition 与 revision | 不读取浏览器草稿 |
| trigger 领取 | ScheduledTrigger 快照 | definition_revision、run_thread_mode、modelAlias | 已领取 trigger 不受后续编辑影响 |
| trigger 快照 | Dream `ScheduledTaskCoordinator` | 决定源 Thread 或新 Thread prepare 路径 | 两条路径失败均记录本次 trigger failed，不互相回退 |
| trigger 快照 + 模型目录 | 模型执行入口 | 以同一用户身份再次校验精确 alias | 不可调用则本次失败，不改 definition、不替换模型 |
| trigger 结果 | 任务历史 | `target_thread_id`、`target_turn_id`、`final_message_id` 与错误 | `state_unknown` 继续现行重查，不重放模型 |

共享 PostgreSQL schema 仍由 Admin Drizzle 管理。若实现 `weekly`、`run_thread_mode`、`model_alias` 或 trigger 快照字段，需要先发布前向 migration 与明确 capability；Dream 只依赖已发布 capability，缺失时停止该功能路径，不在运行时建表或增加第二套 scheduler。

## 10. 响应式组件映射

| 业务职责 | 桌面组件 | 窄屏组件 | 共享状态与行为 |
|---|---|---|---|
| 主编辑容器 | A1 | K1 | 同一 effective、desired、revision；容器形态不同 |
| 标题与关闭 | A2 | K2 | 关闭后焦点返回打开入口 |
| 主表单滚动 | A3 | K3 | 各自主容器唯一页面级滚动区 |
| 固定操作 | A4 | K4 | 共用 F1/F2；窄屏额外处理底部安全区 |
| 重复选项 | G1 | L1/L2/L3 | 共用 G2—G6 与当前 desired 勾选 |
| 高级日程编辑 | H1/H2 | M1/M2/M3 | 共用 H3—H13；应用只写 desired |
| 模型选择 | J1 | 复用 L1 形态的模型 sheet | 共用 J2—J4 与目录状态 |

响应式切换只改变布局容器和叠层表现。若视口变化发生在面板打开期间，应保留 desired、当前字段值和焦点目标，并在新容器中恢复同一业务步骤。

## 11. 说明与待确认项

- `weekly`、工作日与任意星期组合在当前 PRD 中标为建议、未实现；正式设计与实现前需确认 Admin capability、DTO 和 Drizzle 前向 migration。
- 每小时明确复用 `interval_minutes=60`，首次运行基于 `DB now + 60 minutes`。暂停后恢复的锚点继续沿用现行 interval 规则，本文不另设算法。
- daily/weekly 遇到夏令时缺失或重复时刻时继续沿用现行调度规则；最终页面应展示服务端 `next_run_at`。
- 存量 definition 的 `modelAlias` 回填来源是其源 Thread 已持久化的有效模型选择。无法解析时显示“模型待选择”，不能用迁移时的默认模型冒充旧值。
- 正式 PRD 仍归 `docs/prd/scheduled-tasks/`，正式交互设计仍需在 `docs/design/scheduled-tasks/` 正文提供正常流程、异常恢复和状态转换 Mermaid 图；本文保留为第 3 阶段过程证据。
