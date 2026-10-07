<!-- [Input] 现行 v5 PRD、结构草图、层级逻辑和用户参考图。 -->
<!-- [Output] Calendar/Chat 定时任务完整交互的视觉规范、生产映射与 HTML/Tailwind/CSS 原型。 -->
<!-- [Pos] docs/design/claude-agent 下的现行 UI 设计；业务规则以 docs/prd/claude-agent/scheduled-task-diary-page-prd.md 为准。 -->
<!-- [Sync] 2026-09-29: html-design-workflow v5 将详情栏固定为任务信息、Conversations、任务周期，并隔离通用 TaskSession 列表。 -->

# Ink & Memory 定时任务完整 UI 设计 v5（现行）

> 产物类型：实施级 UI 规范 + 可独立审阅的 HTML5 原型
> 输入：`1_prd_draft.md`、`2_structure_sketch.md`、`3_hierarchy_logic.md`、主图与三张辅助参考图
> 设计方向：**Ultra-Sensory Minimalism / Warm Paper Editorial**
> 图片只提供视觉与交互证据，示例文字不构成业务字段；原型只呈现现有协议支持的信息与操作。

---

## 1. 设计结论

本轮把定时任务从“线框内堆信息”收敛为两类有明确阅读顺序的纸面：

1. **Calendar 任务纸面**：顶部是轻量安排入口，下面是可扫描任务行；任务主体、编辑、更多为三个独立点击目标。点击主体后，原纸面切换为最近一次运行结果，不增加第四张浮层。
2. **Chat 任务关联**：Tool 成功后，在所属 assistant turn 下显示单一按钮式任务标记；点击后占用既有右侧栏槽，窄屏变为 Drawer。

视觉上保留 Ink & Memory 的暖白纸张、深棕墨色和鼠尾草绿状态色。主要层级依靠纸面色差、留白和柔和阴影建立，边线只用于内容分隔和输入边界。任务列表自身不套连续的小卡片，避免出现过强线框感。

---

## 2. 图像证据转译

| 视觉证据 | 本稿采用方式 | 协议边界 |
| --- | --- | --- |
| 长圆安排入口 | 纸面顶部胶囊输入；左侧加号为装饰；右侧圆形提交 | 只把非空文字带入新的 Chat 可编辑草稿，不直接创建、不自动发送 |
| 左状态、中标题摘要、右操作 | 任务行为三列；运行中行使用暖灰浅填充 | 不制造分类字段；第二行只投影真实状态、规则与下次时间 |
| 锚定操作菜单 | 菜单悬浮在行尾，阴影高于纸面 | 仅承载现有 run、target Thread、history、pause/resume、delete 动作 |
| 最近结果阅读页 | 任务纸面内 LIST/RESULT 互斥；正文独立滚动；底部动作稳定可达 | 结果只匹配 latest trigger 的 `final_message_id`；聊天只打开同一 trigger 的 `target_thread_id` |
| 独立编辑面板 | 共用 Modal 壳；标题、prompt、规则在内部纵向滚动；页脚固定 | 只编辑 title、prompt、once/daily、日期、时间、IANA 时区与任务状态 |
| Chat turn 内标记与右栏 | 标记紧跟 Tool 成功所在 turn；详情栏与消息区并列 | 标记只由持久化 Tool success 投影；详情栏重新读取 current effective |

---

## 3. 视觉系统

### 3.1 美学样式表

| 项目 | 设计值 | 使用说明 |
| --- | --- | --- |
| 页面底色 | `--canvas: #eee7dd` | 半透明遮罩后的应用背景，不承担内容边界 |
| 主纸面 | `--paper: #fffaf2` | 月历、任务、Diary、Modal |
| 抬升纸面 | `--paper-raised: #fffdf8` | 菜单、任务标记、详情分组 |
| 运行态填充 | `--wash-active: #f0eee8` | 仅活动任务整行填充；不加卡片阴影 |
| 主文字 | `--ink: #3f352c` | 标题、正文、关键值 |
| 次文字 | `--muted: #817568` | 时间、计划摘要、字段标签 |
| 品牌强调 | `--accent: #9a6743` | 提交、选中、焦点环 |
| 成功状态 | `--sage: #7d9670` | 已启用、完成、当前状态 |
| 危险状态 | `--danger: #ba4e42` | 删除和失败；同时使用文字/图标 |
| 分隔 | `--hairline: rgba(93,73,54,.14)` | 仅一像素内容分隔 |
| 大纸面圆角 | `28px` | Calendar 三纸面和 Modal |
| 控件圆角 | `16px / 999px` | 表单组 / 胶囊输入 |
| 纸面阴影 | `0 22px 54px rgba(76,55,37,.14)` | 仅独立浮层使用 |
| 轻抬升阴影 | `0 12px 30px rgba(76,55,37,.10)` | 菜单、marker hover、侧栏组 |
| 标题字体 | `Noto Serif SC` | 纸面标题和结果阅读标题 |
| UI 字体 | `Noto Sans SC` | 控件、列表、状态与正文 |

### 3.2 排版、间距与层级

- 纸面主标题：24/32，`600`；Chat 侧栏标题：20/28，`600`。
- 任务标题：16/24，`600`；摘要：13/20，`400`；正文阅读：15/26。
- 触控目标最小 `44×44px`；图标视觉尺寸约 `18px`。
- 主纸面 padding：宽屏 `28px`，窄屏 `20px`；纸面透明间隙 `18–24px`。
- 任务行默认高度不小于 `72px`；长标题和摘要各单行省略。

```text
Z4 共享 Edit Modal surface
Z3 Modal backdrop / Chat mobile drawer backdrop
Z2 任务行更多菜单
Z1 Calendar 三张悬浮纸面 / Chat marker / side panel
Z0 被遮罩的现有应用页面
```

任务行之间用留白和 `hairline` 分隔；任务行不再各自使用粗边框与大阴影。当前运行行使用整行浅填充，让状态识别来自面而不是边框。

---

## 4. 组件结构与生产映射

| 设计 ID | 产品组件 | 建议生产类名 | 关键行为 |
| --- | --- | --- | --- |
| C3 | Scheduled Paper | `.calendar-popup__scheduled-paper` | LIST / RESULT 互斥；属于右侧外滚动栈 |
| C4 | Arrange Task | `.calendar-popup__arrange` | 非空提交后进入新 Chat 草稿；不直接写 API |
| C6 | Scheduled Task Row | `.calendar-popup__task-row` | 行主体查看结果；编辑和更多独立 |
| C7 | Task Action Menu | `.calendar-popup__task-menu` | 锚定行尾；键盘跳过 disabled 项 |
| C8 | Latest Result | `.calendar-popup__task-result` | header/footer 固定，正文独立滚动 |
| C9 | Edit Form in shared Modal | `.scheduled-task-edit-modal` | effective 初始化 desired；保存携带 revision |
| H2/H3 | Marker Group / Marker | `.chat-scheduled-markers` / `.chat-scheduled-marker` | 单一 button；从严格 Tool success 投影 |
| H4 | Detail Sidebar | `.chat-scheduled-detail` | 读取 current effective 与 trigger Conversations；只读 |
| HM1 | Mobile Drawer | `.chat-scheduled-detail--drawer` | 覆盖式右 Drawer；限制焦点并锁定背景滚动 |

### 4.1 建议组件树

```text
CalendarPopup
├─ CalendarPaper
└─ RightCardStack                  // 宽屏唯一外滚动
   ├─ ScheduledPaper
   │  ├─ ArrangeTaskInput          // LIST 时保留
   │  ├─ ScheduledTaskRow[]        // LIST
   │  └─ ScheduledTaskResult       // RESULT，与 LIST 互斥
   └─ DiaryPaper

Modal                              // 覆盖 Calendar，不参与两列排版
└─ ScheduledTaskEditForm

ChatWorkspace
├─ ConversationColumn
│  └─ AssistantTurn
│     ├─ ChatMarkdown
│     ├─ ExistingToolPartUI
│     └─ ScheduledTaskMarkerGroup  // Tool success 所属 turn
└─ ExistingSidePanelSlot           // 互斥 union
   └─ ScheduledTaskDetailSidebar
```

---

## 5. 组件实施规格

### 5.1 安排任务输入 C4

- 胶囊高度 `58px`，左右 padding `14/12px`，背景使用 `paper-raised`，边界为半透明暖色线并投下轻阴影。
- 加号只是入口识别，`aria-hidden=true`，不响应附件或菜单。
- 输入 placeholder 为“安排任务”；空白值时提交按钮 `disabled`。
- Enter 与圆形提交等价。提交后关闭 Calendar，打开新 Chat，把内容写入可编辑且未发送的 composer 草稿。
- 焦点在提交后落到 Chat composer。

### 5.2 任务行 C6

```text
┌──────────────────────────────────────────────────────┐
│ [状态]  标题……………………………………        [编辑] [更多] │
│         真实状态 / 计划摘要…………………………………… │
└──────────────────────────────────────────────────────┘
```

- 行主体是一个 button；编辑和更多是同级按钮，不能嵌套在主体 button 内。
- 状态图形 `aria-hidden`；摘要必须出现可见状态文字。
- 活动行使用 `wash-active`，普通行透明。hover 只提高背景明度，不产生明显位移。
- 摘要优先级：活动 trigger → 失败/待确认 → effective 规则与 next run → 暂停/结束。
- 点击行主体进入 C8；返回后焦点精确回到原任务行。

### 5.3 更多菜单 C7

- 宽度 `210px`，`paper-raised`，圆角 `18px`，`shadow-pop`。
- 每项高度 `44px`；危险动作位于 `hairline` 分隔线下。
- 可见动作由当前状态和最新 trigger 决定。没有 target Thread 时不渲染对应入口。
- Escape 关闭并回到更多按钮；ArrowUp/ArrowDown/Home/End 只在 enabled 项中移动。

### 5.4 最近运行结果 C8

- 结果头保留状态、标题、规则摘要及编辑/更多，左侧返回按钮建立 LIST/RESULT 关系。
- 正文使用 `min-height:260px; max-height:min(46vh,520px); overflow:auto`。长结果只滚动正文，不改变月历高度，也不让 Diary 离开右卡栈。
- 成功正文由现有 Chat Markdown 渲染。必须精确匹配 trigger 的 final message 关系；匹配不到则显示结果暂不可用。
- 底部动作条稳定可达；只有 latest trigger 存在精确 target Thread 时显示“打开聊天”。

### 5.5 编辑 Modal C9

- 宽度 `min(760px, calc(100vw - 32px))`；最大高度 `min(820px, calc(100vh - 40px))`。
- `grid-template-rows:auto minmax(0,1fr) auto`；只有 body 滚动，header/footer 始终可达。
- body 顺序：标题 → prompt → once/daily selector → 条件字段。
- `once`：日期、时间、IANA 时区；`daily`：时间、IANA 时区。
- effective 初始化 desired；dirty 后保存可用。字段/API/冲突错误保留 desired。
- 暂停/恢复为独立 revision action。关闭/Escape 后焦点回原编辑按钮。

### 5.6 Chat 任务标记 H3

- 位于成功 Tool part 所属 assistant turn 正文之后、message actions 之前。
- 整张 marker 是一个 button：左时钟图标，中间标题与规则快照，右侧“打开”文字和箭头只是视觉尾标。
- Tool result 是创建时快照；点击后侧栏必须重新读取 current effective。
- 同一 turn 多个合法成功结果按 Tool part 顺序纵向排列，间距 `8px`。

### 5.7 Chat 详情栏 / Drawer H4

- 桌面宽度建议 `380–430px`，边界由既有 side panel shell 提供；详情自身滚动，不改变 composer 高度。
- 信息分组顺序固定为：任务信息 → Conversations → 任务周期。组内使用 label/value 行，不套多层边框盒。
- 任务信息显示状态和完整 prompt；标题保留在侧栏头部。
- Conversations 首项打开 source Thread，后续按时间倒序展示具备 target Thread 的 trigger；每一行打开自身精确 Thread。
- scheduled trigger 复用的 TaskSession 不进入通用 `CreatedTaskSessionList`；普通独立 TaskSession 继续保留。
- 任务周期显示 once/daily、日期、时间、IANA 时区和下次执行。
- 窄屏复用同一内容，投影为右侧 Drawer；宽度 `min(92vw,420px)`，带 backdrop、focus trap 和 Escape 关闭。

---

## 6. 交互状态与微动效

| 状态 | 视觉反馈 | 动效 |
| --- | --- | --- |
| hover | 背景加深 2–3%，图标墨色增强 | `160ms ease-out` |
| active | 按钮缩放到 `0.985` | `90ms` |
| focus-visible | 2px accent ring + 3px paper offset | 无位移 |
| 菜单出现 | opacity 0→1，translateY -4→0 | `160ms cubic-bezier(.2,.8,.2,1)` |
| Modal / Drawer | backdrop 淡入；surface 轻微上移/侧移 | `220ms` |
| 保存中 | 固定宽度文案 + 低对比进度环 | 不修改布局宽度 |

```css
@keyframes paper-rise {
  from { opacity: 0; transform: translateY(8px) scale(.992); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}
@keyframes drawer-in {
  from { transform: translateX(24px); opacity: 0; }
  to   { transform: translateX(0); opacity: 1; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: .01ms !important;
    transition-duration: .01ms !important;
    scroll-behavior: auto !important;
  }
}
```

---

## 7. 响应式、滚动与无障碍

| 视口 | Calendar | Chat |
| --- | --- | --- |
| 宽屏 | 左月历固定；右卡栈独立滚动，任务与 Diary 为分离纸面 | conversation 与详情栏并列；两者分别滚动 |
| 短高宽屏 | 两列保留；月历必要时自身滚动；结果正文/右卡栈继续独立 | composer 保持固定关系，详情栏内容滚动 |
| 窄屏 | 三纸面按月历 → 任务 → Diary 单列；透明间隙保留 | 详情变为覆盖式 Drawer |
| 极窄屏 | 任务标题/摘要省略；动作保持 44px；Modal 单列字段 | marker 标题/摘要省略；Drawer 不横向溢出 |

- Calendar 背景页不因弹窗内容滚动；任务列表随右卡栈滚动，不再增加同方向内滚动。
- 结果正文、Modal body、prompt textarea、Chat messages、Chat details 各自只拥有指定滚动边界。
- Drawer 打开时锁定背景 Chat 滚动；关闭后恢复 marker 焦点和消息位置。
- 状态不得只用颜色；状态图形旁必须有摘要文字。
- C6 主体、编辑、更多是同级交互节点；H3 是单一 button，禁止嵌套 button。
- Modal 使用 `role=dialog`、`aria-modal=true`；结果加载用 `aria-live=polite`，失败用 `role=alert`。
- 任务菜单使用 `role=menu/menuitem`；禁用项不进入方向键焦点序列。
- 文本与纸面对比至少达到 WCAG AA；所有图标按钮提供明确可访问名称。

---

## 8. 完整 HTML5 + Tailwind 2.2.19/CSS 交互原型

以下代码可保存为单个 `.html` 文件直接打开。顶部场景切换器只供设计审阅，不属于生产页面。Calendar 任务行、结果、菜单、编辑 Modal，以及 Chat marker、桌面侧栏和移动 Drawer 均可操作。

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Ink & Memory · 定时任务 UI v5</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;500;600;700&family=Noto+Sans+SC:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://lf3-cdn-tos.bytecdntp.com/cdn/expire-1-M/tailwindcss/2.2.19/tailwind.min.css">
  <link rel="stylesheet" href="https://lf6-cdn-tos.bytecdntp.com/cdn/expire-100-M/font-awesome/6.0.0/css/all.min.css">
  <style>
    :root {
      --canvas: #eee7dd; --paper: #fffaf2; --paper-raised: #fffdf8;
      --wash-active: #f0eee8; --wash-hover: #f7f2ea;
      --ink: #3f352c; --muted: #817568; --faint: #a89b8e;
      --accent: #9a6743; --accent-soft: #ead9c7;
      --sage: #7d9670; --sage-soft: #edf2e8;
      --danger: #ba4e42; --danger-soft: #f8ebe7;
      --hairline: rgba(93,73,54,.14);
      --shadow-paper: 0 22px 54px rgba(76,55,37,.14);
      --shadow-pop: 0 14px 36px rgba(76,55,37,.17);
      --radius-paper: 28px; --radius-control: 16px;
    }
    * { box-sizing: border-box; }
    html, body { min-height: 100%; }
    body {
      margin: 0; color: var(--ink);
      background: radial-gradient(circle at 18% 12%, rgba(255,255,255,.72), transparent 32%), linear-gradient(145deg,#e6ddd1,var(--canvas));
      font-family: "Noto Sans SC", sans-serif;
    }
    button, input, textarea, select { font: inherit; }
    button { color: inherit; }
    .serif { font-family: "Noto Serif SC", serif; }
    :focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
    .icon-button {
      display:inline-grid; width:44px; height:44px; flex:0 0 44px; place-items:center;
      border:0; border-radius:999px; background:transparent;
      transition:background .16s ease,color .16s ease,transform .09s ease;
    }
    .icon-button:hover { color:var(--accent); background:var(--wash-hover); }
    .icon-button:active { transform:scale(.985); }
    .paper {
      border:1px solid rgba(161,128,95,.20); border-radius:var(--radius-paper);
      background:linear-gradient(150deg,rgba(255,253,248,.98),rgba(255,248,238,.98));
      box-shadow:var(--shadow-paper);
    }
    .eyebrow { color:var(--muted); font-size:12px; font-weight:600; letter-spacing:.12em; text-transform:uppercase; }
    .review-nav {
      position:fixed; z-index:80; top:14px; left:50%; display:flex; gap:4px; max-width:calc(100vw - 20px);
      padding:5px; transform:translateX(-50%); overflow-x:auto; border:1px solid var(--hairline);
      border-radius:999px; background:rgba(255,253,248,.90); box-shadow:0 10px 28px rgba(63,53,44,.12); backdrop-filter:blur(14px);
    }
    .review-nav button { border:0; border-radius:999px; padding:8px 14px; color:var(--muted); background:transparent; font-size:12px; white-space:nowrap; }
    .review-nav button[aria-selected="true"] { color:var(--paper-raised); background:var(--ink); }
    .scene { display:none; min-height:100vh; }
    .scene.is-active { display:block; }

    /* Calendar：透明画布 + 三张独立纸面 */
    .calendar-shell { min-height:100vh; padding:76px 24px 24px; background:rgba(63,53,44,.36); }
    .calendar-dialog {
      position:relative; display:grid; grid-template-columns:minmax(420px,.9fr) minmax(500px,1.1fr);
      gap:24px; width:min(1460px,100%); height:min(760px,calc(100vh - 100px)); max-height:calc(100vh - 100px); margin:0 auto;
    }
    .calendar-close { position:absolute; z-index:4; top:-12px; right:-12px; border:1px solid var(--hairline); background:var(--paper-raised); box-shadow:var(--shadow-pop); }
    .calendar-paper { min-height:0; height:100%; padding:28px; overflow:auto; }
    .month-head { display:grid; grid-template-columns:44px 1fr 44px; align-items:center; margin-bottom:28px; }
    .month-title { text-align:center; font-size:26px; font-weight:600; }
    .week-grid,.date-grid { display:grid; grid-template-columns:repeat(7,minmax(0,1fr)); gap:8px; }
    .week-grid { margin-bottom:10px; color:var(--muted); font-size:12px; text-align:center; }
    .date-button { position:relative; aspect-ratio:1; min-height:48px; border:0; border-radius:16px; background:transparent; transition:background .16s,box-shadow .16s; }
    .date-button:hover { background:var(--paper-raised); box-shadow:0 7px 18px rgba(76,55,37,.08); }
    .date-button.has-note::after { position:absolute; left:50%; bottom:8px; width:5px; height:5px; content:""; transform:translateX(-50%); border-radius:999px; background:var(--accent); }
    .date-button[aria-current="date"] { background:var(--paper-raised); box-shadow:inset 0 0 0 2px var(--accent),0 8px 18px rgba(76,55,37,.10); font-weight:700; }
    .right-card-stack { display:grid; align-content:start; gap:22px; min-height:0; overflow-y:auto; overscroll-behavior:contain; padding:2px 10px 28px 2px; }
    .scheduled-paper,.diary-paper { padding:26px; }
    .paper-header { display:flex; align-items:flex-start; justify-content:space-between; gap:20px; margin-bottom:22px; }
    .paper-header h2 { margin:2px 0 4px; font-size:24px; font-weight:600; }
    .paper-meta { margin:0; color:var(--muted); font-size:13px; }
    .arrange {
      display:grid; grid-template-columns:44px minmax(0,1fr) 48px; align-items:center; height:60px; margin-bottom:18px; padding:5px 7px 5px 8px;
      border:1px solid rgba(138,105,72,.18); border-radius:999px; background:var(--paper-raised); box-shadow:0 10px 28px rgba(76,55,37,.08);
    }
    .arrange .leading { display:grid; place-items:center; font-size:18px; }
    .arrange input { min-width:0; border:0; outline:0; color:var(--ink); background:transparent; }
    .arrange input::placeholder { color:var(--faint); }
    .round-submit { display:grid; width:46px; height:46px; place-items:center; border:0; border-radius:999px; color:white; background:var(--accent); box-shadow:0 8px 18px rgba(154,103,67,.22); }
    .round-submit:disabled { cursor:default; opacity:.34; }
    .task-list { display:grid; gap:2px; }
    .task-item { position:relative; border-bottom:1px solid var(--hairline); }
    .task-item:last-child { border-bottom:0; }
    .task-item.is-running { margin:2px 0; border-bottom-color:transparent; border-radius:18px; background:var(--wash-active); }
    .task-row { display:grid; grid-template-columns:minmax(0,1fr) auto; align-items:center; min-height:76px; padding:8px 8px 8px 4px; }
    .task-main { display:grid; grid-template-columns:44px minmax(0,1fr); align-items:center; min-width:0; height:100%; border:0; border-radius:14px; text-align:left; background:transparent; }
    .task-main:hover { background:rgba(255,255,255,.48); }
    .task-state { display:grid; width:34px; height:34px; place-items:center; justify-self:center; border-radius:999px; color:var(--accent); background:rgba(154,103,67,.10); }
    .task-item.is-running .task-state { color:var(--sage); background:var(--sage-soft); }
    .task-copy { min-width:0; padding:4px 8px 4px 4px; }
    .task-copy strong,.task-copy span { display:block; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; }
    .task-copy strong { margin-bottom:4px; font-size:16px; font-weight:600; }
    .task-copy span { color:var(--muted); font-size:13px; }
    .task-actions { display:flex; align-items:center; }
    .task-menu {
      position:absolute; z-index:20; top:62px; right:4px; display:none; width:210px; padding:8px;
      border:1px solid var(--hairline); border-radius:18px; background:var(--paper-raised); box-shadow:var(--shadow-pop); animation:menu-in .16s ease-out;
    }
    .task-menu.is-open { display:block; }
    .task-menu button { display:grid; grid-template-columns:28px 1fr; align-items:center; width:100%; min-height:44px; border:0; border-radius:11px; text-align:left; background:transparent; }
    .task-menu button:hover { background:var(--wash-hover); }
    .task-menu .danger { margin-top:6px; padding-top:6px; border-top:1px solid var(--hairline); color:var(--danger); }
    .task-result { display:none; grid-template-rows:auto minmax(0,1fr) auto; }
    .scheduled-paper.show-result .task-list-view { display:none; }
    .scheduled-paper.show-result .task-result { display:grid; }
    .result-header { display:grid; grid-template-columns:44px minmax(0,1fr) auto; align-items:center; gap:8px; padding-bottom:18px; border-bottom:1px solid var(--hairline); }
    .result-heading { min-width:0; }
    .result-heading h3 { overflow:hidden; margin:0 0 4px; white-space:nowrap; text-overflow:ellipsis; font-size:20px; font-weight:600; }
    .result-heading p { margin:0; color:var(--muted); font-size:13px; }
    .result-actions { display:flex; }
    .result-scroll { min-height:280px; max-height:min(46vh,520px); overflow:auto; overscroll-behavior:contain; padding:24px 6px 26px 4px; line-height:1.8; }
    .result-scroll .time { margin-bottom:18px; color:var(--muted); font-size:13px; }
    .result-scroll p { margin:0 0 16px; }
    .result-scroll ul { margin:0 0 16px; padding-left:20px; }
    .result-footer { display:flex; justify-content:flex-end; padding-top:16px; border-top:1px solid var(--hairline); }
    .secondary-button,.primary-button,.danger-button { min-height:44px; border-radius:999px; padding:0 18px; font-weight:600; }
    .secondary-button { border:1px solid var(--hairline); background:var(--paper-raised); }
    .primary-button { border:0; color:white; background:var(--accent); }
    .danger-button { border:0; color:var(--danger); background:var(--danger-soft); }
    .diary-entry { display:grid; grid-template-columns:74px minmax(0,1fr) auto; align-items:center; gap:10px; min-height:70px; padding:12px 4px; border-top:1px solid var(--hairline); }
    .diary-entry time { color:var(--muted); font-size:13px; }
    .diary-entry strong { overflow:hidden; white-space:nowrap; text-overflow:ellipsis; }

    /* Shared modal */
    .modal-layer { position:fixed; z-index:90; inset:0; display:none; place-items:center; padding:20px; background:rgba(63,53,44,.38); backdrop-filter:blur(5px); }
    .modal-layer.is-open { display:grid; }
    .edit-modal {
      display:grid; grid-template-rows:auto minmax(0,1fr) auto; width:min(760px,calc(100vw - 32px)); max-height:min(820px,calc(100vh - 40px)); overflow:hidden;
      border:1px solid rgba(161,128,95,.18); border-radius:28px; background:var(--paper-raised); box-shadow:0 30px 80px rgba(49,36,25,.26); animation:paper-rise .22s cubic-bezier(.2,.8,.2,1);
    }
    .modal-head,.modal-foot { padding:22px 26px; }
    .modal-head { display:flex; align-items:flex-start; justify-content:space-between; border-bottom:1px solid var(--hairline); }
    .modal-head h2 { margin:3px 0 0; font-size:22px; font-weight:600; }
    .modal-body { overflow-y:auto; overscroll-behavior:contain; padding:24px 26px 30px; }
    .field { display:grid; gap:8px; margin-bottom:22px; }
    .field label,.field legend { color:var(--muted); font-size:13px; font-weight:600; }
    .field input,.field textarea,.field select { width:100%; border:1px solid var(--hairline); border-radius:var(--radius-control); color:var(--ink); background:#fffefb; }
    .field input,.field select { min-height:48px; padding:0 14px; }
    .field textarea { min-height:190px; max-height:280px; resize:vertical; padding:14px; line-height:1.65; }
    .frequency-select { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
    .frequency-select button { min-height:48px; border:1px solid var(--hairline); border-radius:15px; background:#fffefb; }
    .frequency-select button[aria-pressed="true"] { border-color:var(--accent); color:var(--accent); background:var(--accent-soft); }
    .rule-grid { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
    .once-only { display:none; }
    .edit-modal[data-frequency="once"] .once-only { display:grid; }
    .modal-foot { display:flex; align-items:center; justify-content:space-between; gap:12px; border-top:1px solid var(--hairline); }
    .modal-foot-right { display:flex; gap:10px; }

    /* Chat marker / sidebar / drawer */
    .chat-scene { min-height:100vh; padding-top:60px; background:#f5f2ec; }
    .chat-workspace { display:grid; grid-template-columns:minmax(0,1fr); min-height:calc(100vh - 60px); }
    .chat-scene.detail-open .chat-workspace { grid-template-columns:minmax(0,1fr) 410px; }
    .conversation { display:grid; grid-template-rows:auto minmax(0,1fr) auto; min-width:0; border-right:1px solid var(--hairline); background:rgba(255,255,255,.76); }
    .chat-head { display:flex; align-items:center; justify-content:space-between; min-height:68px; padding:0 26px; border-bottom:1px solid var(--hairline); }
    .chat-head h1 { overflow:hidden; margin:0; white-space:nowrap; text-overflow:ellipsis; font-size:18px; font-weight:600; }
    .messages { overflow-y:auto; overscroll-behavior:contain; padding:34px clamp(22px,5vw,72px) 46px; }
    .assistant-turn { width:min(760px,100%); margin:0 auto; }
    .assistant-turn > p { margin:0 0 16px; line-height:1.8; }
    .tool-success { display:inline-flex; align-items:center; gap:8px; margin:8px 0 12px; color:var(--sage); font-size:13px; font-weight:600; }
    .marker-group { display:grid; gap:8px; margin-top:8px; }
    .scheduled-marker {
      display:grid; grid-template-columns:46px minmax(0,1fr) auto; align-items:center; width:100%; min-height:82px; padding:12px 14px;
      border:1px solid var(--hairline); border-radius:18px; text-align:left; background:var(--paper-raised); box-shadow:0 8px 24px rgba(76,55,37,.06);
      transition:box-shadow .16s ease,transform .16s ease,border-color .16s ease;
    }
    .scheduled-marker:hover { border-color:rgba(154,103,67,.30); box-shadow:var(--shadow-pop); transform:translateY(-1px); }
    .marker-icon { display:grid; width:38px; height:38px; place-items:center; border-radius:12px; color:var(--accent); background:var(--accent-soft); }
    .marker-copy { min-width:0; }
    .marker-copy strong,.marker-copy span { display:block; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; }
    .marker-copy strong { margin-bottom:4px; font-size:15px; }
    .marker-copy span { color:var(--muted); font-size:13px; }
    .marker-tail { display:flex; align-items:center; gap:8px; color:var(--accent); font-size:13px; font-weight:600; }
    .composer-wrap { padding:16px clamp(18px,4vw,52px) 22px; background:linear-gradient(transparent,rgba(255,255,255,.96) 24%); }
    .composer { display:flex; align-items:flex-end; gap:12px; width:min(820px,100%); min-height:72px; margin:0 auto; padding:15px 16px; border:1px solid var(--hairline); border-radius:24px; background:white; box-shadow:0 14px 32px rgba(76,55,37,.09); }
    .composer textarea { flex:1; min-height:38px; max-height:120px; resize:none; border:0; outline:0; background:transparent; }
    .draft-note { display:none; width:min(820px,100%); margin:0 auto 8px; color:var(--muted); font-size:12px; }
    .draft-note.is-visible { display:block; }
    .detail-sidebar { display:none; grid-template-rows:auto minmax(0,1fr); min-width:0; background:var(--paper-raised); }
    .chat-scene.detail-open .detail-sidebar { display:grid; }
    .detail-head { display:flex; align-items:flex-start; justify-content:space-between; gap:12px; min-height:86px; padding:22px 22px 18px; border-bottom:1px solid var(--hairline); }
    .detail-head h2 { margin:3px 0 0; font-size:20px; font-weight:600; }
    .detail-scroll { overflow-y:auto; overscroll-behavior:contain; padding:20px 22px 32px; }
    .detail-group { padding:18px; border-radius:20px; background:#fffaf3; box-shadow:0 7px 22px rgba(76,55,37,.05); }
    .detail-group + .detail-group { margin-top:14px; }
    .detail-group h3 { margin:0 0 14px; color:var(--muted); font-size:12px; font-weight:700; letter-spacing:.08em; }
    .detail-row { display:grid; grid-template-columns:92px minmax(0,1fr); gap:12px; padding:10px 0; border-top:1px solid var(--hairline); }
    .detail-row:first-of-type { border-top:0; }
    .detail-row dt { color:var(--muted); font-size:13px; }
    .detail-row dd { margin:0; overflow-wrap:anywhere; text-align:right; font-size:13px; font-weight:500; }
    .conversation-link { display:grid; width:100%; grid-template-columns:minmax(0,1fr) auto; align-items:center; gap:12px; padding:13px 14px; border:1px solid var(--hairline); border-radius:14px; background:var(--paper); color:var(--ink); text-align:left; cursor:pointer; }
    .conversation-link + .conversation-link { margin-top:8px; }
    .conversation-link span:first-child { display:grid; min-width:0; gap:3px; }
    .conversation-link strong,.conversation-link small { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .conversation-link small { color:var(--muted); }
    .status-pill { display:inline-flex; align-items:center; gap:6px; color:var(--sage); }
    .prompt-block { margin-top:10px; font-size:13px; line-height:1.65; }
    .drawer-backdrop { display:none; }

    @keyframes menu-in { from { opacity:0; transform:translateY(-4px); } to { opacity:1; transform:none; } }
    @keyframes paper-rise { from { opacity:0; transform:translateY(8px) scale(.992); } to { opacity:1; transform:none; } }
    @keyframes drawer-in { from { opacity:0; transform:translateX(24px); } to { opacity:1; transform:none; } }
    @media (max-width:980px) {
      .calendar-shell { padding:70px 14px 14px; overflow-y:auto; }
      .calendar-dialog { display:block; height:auto; max-height:none; }
      .calendar-paper { min-height:auto; height:auto; margin-bottom:20px; }
      .right-card-stack { display:grid; overflow:visible; padding:0; }
      .chat-workspace { grid-template-columns:minmax(0,1fr); }
      .detail-sidebar { position:fixed; z-index:72; inset:60px 0 0 auto; display:none; width:min(92vw,420px); box-shadow:-20px 0 50px rgba(48,35,24,.20); animation:drawer-in .22s ease-out; }
      .chat-scene.detail-open .detail-sidebar { display:grid; }
      .chat-scene.detail-open .drawer-backdrop { position:fixed; z-index:71; inset:60px 0 0; display:block; border:0; background:rgba(63,53,44,.34); }
    }
    @media (max-width:620px) {
      .calendar-paper,.scheduled-paper,.diary-paper { padding:20px; border-radius:22px; }
      .calendar-close { top:8px; right:8px; }
      .date-grid,.week-grid { gap:4px; }
      .date-button { min-height:40px; border-radius:12px; }
      .task-actions .icon-button { width:40px; flex-basis:40px; }
      .result-header { grid-template-columns:40px minmax(0,1fr); }
      .result-actions { grid-column:2; justify-self:end; }
      .rule-grid { grid-template-columns:1fr; }
      .modal-head,.modal-foot { padding:18px; }
      .modal-body { padding:20px 18px 24px; }
      .modal-foot-right { margin-left:auto; }
      .messages { padding:28px 16px 34px; }
      .marker-tail span { display:none; }
      .chat-head { padding:0 16px; }
    }
    @media (prefers-reduced-motion:reduce) {
      *,*::before,*::after { animation-duration:.01ms !important; transition-duration:.01ms !important; scroll-behavior:auto !important; }
    }
  </style>
</head>
<body>
  <nav class="review-nav" aria-label="原型场景（仅设计审阅）">
    <button type="button" data-scene="calendar" aria-selected="true">Calendar</button>
    <button type="button" data-scene="chat" aria-selected="false">Chat 详情</button>
  </nav>

  <main>
    <section id="calendar-scene" class="scene is-active" aria-label="Calendar 定时任务原型">
      <div class="calendar-shell">
        <div class="calendar-dialog" role="dialog" aria-modal="true" aria-labelledby="calendar-title">
          <button class="icon-button calendar-close" type="button" aria-label="关闭日历"><i class="fa-solid fa-xmark" aria-hidden="true"></i></button>

          <section class="paper calendar-paper" aria-label="月历">
            <div class="month-head">
              <button class="icon-button" type="button" aria-label="上个月"><i class="fa-solid fa-angle-left" aria-hidden="true"></i></button>
              <h2 class="month-title serif">2026 年 9 月</h2>
              <button class="icon-button" type="button" aria-label="下个月"><i class="fa-solid fa-angle-right" aria-hidden="true"></i></button>
            </div>
            <div class="week-grid" aria-hidden="true"><span>日</span><span>一</span><span>二</span><span>三</span><span>四</span><span>五</span><span>六</span></div>
            <div class="date-grid" role="grid" aria-label="2026 年 9 月">
              <span></span><span></span>
              <button class="date-button has-note" type="button">1</button><button class="date-button" type="button">2</button><button class="date-button" type="button">3</button><button class="date-button" type="button">4</button><button class="date-button has-note" type="button">5</button>
              <button class="date-button" type="button">6</button><button class="date-button has-note" type="button">7</button><button class="date-button" type="button">8</button><button class="date-button has-note" type="button">9</button><button class="date-button" type="button">10</button><button class="date-button" type="button">11</button><button class="date-button" type="button">12</button>
              <button class="date-button" type="button">13</button><button class="date-button" type="button">14</button><button class="date-button" type="button">15</button><button class="date-button" type="button">16</button><button class="date-button" type="button">17</button><button class="date-button" type="button">18</button><button class="date-button" type="button">19</button>
              <button class="date-button" type="button">20</button><button class="date-button" type="button">21</button><button class="date-button" type="button">22</button><button class="date-button" type="button">23</button><button class="date-button" type="button">24</button><button class="date-button" type="button">25</button><button class="date-button" type="button">26</button>
              <button class="date-button" type="button">27</button><button class="date-button" type="button">28</button><button class="date-button has-note" type="button" aria-current="date">29</button><button class="date-button" type="button">30</button>
            </div>
          </section>

          <div class="right-card-stack">
            <section id="scheduled-paper" class="paper scheduled-paper" aria-labelledby="calendar-title">
              <div class="task-list-view">
                <header class="paper-header">
                  <div><div class="eyebrow">Today</div><h2 id="calendar-title" class="serif">定时任务</h2><p class="paper-meta">2 项任务 · 1 项正在运行</p></div>
                </header>
                <form id="arrange-form" class="arrange">
                  <span class="leading" aria-hidden="true"><i class="fa-solid fa-plus"></i></span>
                  <input id="arrange-input" type="text" autocomplete="off" placeholder="安排任务" aria-label="安排任务">
                  <button id="arrange-submit" class="round-submit" type="submit" aria-label="带入新的聊天草稿" disabled><i class="fa-solid fa-arrow-up" aria-hidden="true"></i></button>
                </form>

                <div class="task-list" aria-label="任务列表">
                  <article class="task-item is-running">
                    <div class="task-row">
                      <button class="task-main" type="button" data-open-result aria-label="查看整理今日工作记录的最近运行结果">
                        <span class="task-state" aria-hidden="true"><i class="fa-solid fa-pause"></i></span>
                        <span class="task-copy"><strong>整理今日工作记录</strong><span>监测中 · 正在运行</span></span>
                      </button>
                      <div class="task-actions">
                        <button class="icon-button" type="button" data-open-edit aria-label="编辑整理今日工作记录"><i class="fa-solid fa-pen" aria-hidden="true"></i></button>
                        <button class="icon-button" type="button" data-menu-toggle aria-haspopup="menu" aria-expanded="false" aria-label="更多任务操作"><i class="fa-solid fa-ellipsis" aria-hidden="true"></i></button>
                      </div>
                    </div>
                    <div class="task-menu" role="menu">
                      <button type="button" role="menuitem"><i class="fa-solid fa-play" aria-hidden="true"></i><span>立即运行</span></button>
                      <button type="button" role="menuitem" data-open-chat><i class="fa-regular fa-comment" aria-hidden="true"></i><span>打开聊天</span></button>
                      <button type="button" role="menuitem"><i class="fa-solid fa-clock-rotate-left" aria-hidden="true"></i><span>运行历史</span></button>
                      <button type="button" role="menuitem"><i class="fa-solid fa-pause" aria-hidden="true"></i><span>暂停</span></button>
                      <div class="danger"><button type="button" role="menuitem"><i class="fa-regular fa-trash-can" aria-hidden="true"></i><span>删除</span></button></div>
                    </div>
                  </article>
                  <article class="task-item">
                    <div class="task-row">
                      <button class="task-main" type="button" data-open-result aria-label="查看每日回顾明日计划的最近运行结果">
                        <span class="task-state" aria-hidden="true"><i class="fa-regular fa-clock"></i></span>
                        <span class="task-copy"><strong>每日回顾明日计划</strong><span>每天 21:30 · 下次运行：今天</span></span>
                      </button>
                      <div class="task-actions">
                        <button class="icon-button" type="button" data-open-edit aria-label="编辑每日回顾明日计划"><i class="fa-solid fa-pen" aria-hidden="true"></i></button>
                        <button class="icon-button" type="button" aria-label="更多任务操作"><i class="fa-solid fa-ellipsis" aria-hidden="true"></i></button>
                      </div>
                    </div>
                  </article>
                </div>
              </div>

              <section class="task-result" aria-labelledby="result-title">
                <header class="result-header">
                  <button class="icon-button" type="button" data-back-list aria-label="返回任务列表"><i class="fa-solid fa-arrow-left" aria-hidden="true"></i></button>
                  <div class="result-heading"><h3 id="result-title" class="serif">整理今日工作记录</h3><p>已完成 · 今天 09:00</p></div>
                  <div class="result-actions">
                    <button class="icon-button" type="button" data-open-edit aria-label="编辑任务"><i class="fa-solid fa-pen" aria-hidden="true"></i></button>
                    <button class="icon-button" type="button" aria-label="更多任务操作"><i class="fa-solid fa-ellipsis" aria-hidden="true"></i></button>
                  </div>
                </header>
                <div class="result-scroll" tabindex="0" aria-live="polite">
                  <div class="time">9 月 29 日星期二 09:00</div>
                  <p>今日工作记录已完成整理。以下内容来自本次运行对应的最终回复：</p>
                  <ul><li>梳理了当前进行中的工作与阻塞项。</li><li>归纳了需要继续跟进的两项决策。</li><li>生成了可直接用于明日计划的行动清单。</li></ul>
                  <p><strong>下一步：</strong>先处理最高优先级阻塞，再按行动清单继续执行。</p>
                </div>
                <footer class="result-footer"><button class="secondary-button" type="button" data-open-chat><i class="fa-regular fa-comment mr-2" aria-hidden="true"></i>打开聊天</button></footer>
              </section>
            </section>

            <section class="paper diary-paper" aria-labelledby="diary-title">
              <header class="paper-header"><div><div class="eyebrow">Writing</div><h2 id="diary-title" class="serif">日记</h2><p class="paper-meta">2 篇记录</p></div></header>
              <article class="diary-entry"><time>14:16</time><strong>今天的工作记录</strong><i class="fa-solid fa-angle-right" aria-hidden="true"></i></article>
              <article class="diary-entry"><time>08:40</time><strong>清晨随笔</strong><i class="fa-solid fa-angle-right" aria-hidden="true"></i></article>
            </section>
          </div>
        </div>
      </div>
    </section>

    <section id="chat-scene" class="scene chat-scene detail-open" aria-label="Chat 定时任务原型">
      <div class="chat-workspace">
        <section class="conversation" aria-label="聊天内容">
          <header class="chat-head"><h1>整理工作记录与明日计划</h1><button class="icon-button" type="button" aria-label="更多会话操作"><i class="fa-solid fa-ellipsis" aria-hidden="true"></i></button></header>
          <div class="messages">
            <article class="assistant-turn">
              <p>我已经按每天 21:30 的计划创建任务。它会在计划时间通过现有任务执行链路运行，你可以从下方标记查看当前设置。</p>
              <div class="tool-success"><i class="fa-regular fa-circle-check" aria-hidden="true"></i><span>定时任务已创建</span></div>
              <div class="marker-group" aria-label="本次回复创建的定时任务">
                <button class="scheduled-marker" type="button" data-open-detail aria-label="打开每日回顾明日计划的任务详情">
                  <span class="marker-icon" aria-hidden="true"><i class="fa-regular fa-clock"></i></span>
                  <span class="marker-copy"><strong>每日回顾明日计划</strong><span>每天 21:30 · Asia/Shanghai</span></span>
                  <span class="marker-tail"><span>打开</span><i class="fa-solid fa-angle-right" aria-hidden="true"></i></span>
                </button>
              </div>
            </article>
          </div>
          <div class="composer-wrap">
            <p id="draft-note" class="draft-note">已带入新的可编辑草稿，尚未发送。</p>
            <div class="composer"><button class="icon-button" type="button" aria-label="添加内容"><i class="fa-solid fa-plus" aria-hidden="true"></i></button><textarea id="chat-draft" placeholder="随心输入" aria-label="聊天输入"></textarea><button class="round-submit" type="button" aria-label="发送消息"><i class="fa-solid fa-arrow-up" aria-hidden="true"></i></button></div>
          </div>
        </section>

        <button class="drawer-backdrop" type="button" data-close-detail aria-label="关闭任务详情"></button>
        <aside class="detail-sidebar" aria-labelledby="detail-title">
          <header class="detail-head"><div><div class="eyebrow">Scheduled task</div><h2 id="detail-title" class="serif">任务详情</h2></div><button class="icon-button" type="button" data-close-detail aria-label="关闭任务详情"><i class="fa-solid fa-xmark" aria-hidden="true"></i></button></header>
          <div class="detail-scroll">
            <section class="detail-group" aria-labelledby="task-info-heading">
              <h3 id="task-info-heading">任务信息</h3>
              <dl><div class="detail-row"><dt>状态</dt><dd><span class="status-pill"><i class="fa-solid fa-circle text-xs" aria-hidden="true"></i>已启用</span></dd></div></dl>
              <p class="prompt-block">整理今天的工作记录，提炼未完成事项，并生成明日优先行动清单。</p>
            </section>
            <section class="detail-group" aria-labelledby="conversations-heading">
              <h3 id="conversations-heading">Conversations</h3>
              <button class="conversation-link" type="button" data-open-chat><span><strong>创建任务的会话</strong><small>整理工作记录与明日计划</small></span><i class="fa-solid fa-angle-right" aria-hidden="true"></i></button>
              <button class="conversation-link" type="button" data-open-chat><span><strong>任务运行会话</strong><small>今天 09:00 · 已完成</small></span><i class="fa-solid fa-angle-right" aria-hidden="true"></i></button>
            </section>
            <section class="detail-group" aria-labelledby="cycle-heading">
              <h3 id="cycle-heading">任务周期</h3>
              <dl><div class="detail-row"><dt>频率</dt><dd>每天</dd></div><div class="detail-row"><dt>时间</dt><dd>21:30</dd></div><div class="detail-row"><dt>时区</dt><dd>Asia/Shanghai</dd></div><div class="detail-row"><dt>下次执行</dt><dd>今天 21:30</dd></div></dl>
            </section>
          </div>
        </aside>
      </div>
    </section>
  </main>

  <div id="edit-layer" class="modal-layer" aria-hidden="true">
    <section id="edit-modal" class="edit-modal" data-frequency="daily" role="dialog" aria-modal="true" aria-labelledby="edit-title">
      <header class="modal-head"><div><div class="eyebrow">每天</div><h2 id="edit-title" class="serif">编辑定时任务</h2></div><button id="edit-close" class="icon-button" type="button" aria-label="关闭编辑弹窗"><i class="fa-solid fa-xmark" aria-hidden="true"></i></button></header>
      <div class="modal-body">
        <div class="field"><label for="task-title">标题</label><input id="task-title" value="每日回顾明日计划"></div>
        <div class="field"><label for="task-prompt">提示词</label><textarea id="task-prompt">整理今天的工作记录，提炼未完成事项，并生成明日优先行动清单。</textarea></div>
        <fieldset class="field"><legend>频率</legend><div class="frequency-select"><button type="button" data-frequency="once" aria-pressed="false">单次</button><button type="button" data-frequency="daily" aria-pressed="true">每天</button></div></fieldset>
        <div class="once-only rule-grid"><div class="field"><label for="task-date">日期</label><input id="task-date" type="date" value="2026-09-30"></div></div>
        <div class="rule-grid"><div class="field"><label for="task-time">时间</label><input id="task-time" type="time" value="21:30"></div><div class="field"><label for="task-timezone">时区</label><select id="task-timezone"><option>Asia/Shanghai</option><option>Asia/Tokyo</option><option>Europe/London</option></select></div></div>
        <p id="form-status" class="text-sm text-gray-500" aria-live="polite"></p>
      </div>
      <footer class="modal-foot"><button class="danger-button" type="button">暂停</button><div class="modal-foot-right"><button id="edit-cancel" class="secondary-button" type="button">取消</button><button id="edit-save" class="primary-button" type="button">保存</button></div></footer>
    </section>
  </div>

  <script>
    const scenes = { calendar: document.getElementById('calendar-scene'), chat: document.getElementById('chat-scene') };
    const scheduledPaper = document.getElementById('scheduled-paper');
    const editLayer = document.getElementById('edit-layer');
    const editModal = document.getElementById('edit-modal');
    const chatDraft = document.getElementById('chat-draft');
    let lastEditOpener = null;
    let lastResultOpener = null;
    let lastMarkerOpener = null;

    function showScene(name) {
      Object.entries(scenes).forEach(([key,node]) => node.classList.toggle('is-active', key === name));
      document.querySelectorAll('[data-scene]').forEach(button => button.setAttribute('aria-selected', String(button.dataset.scene === name)));
    }
    document.querySelectorAll('[data-scene]').forEach(button => button.addEventListener('click', () => showScene(button.dataset.scene)));

    document.querySelectorAll('[data-open-result]').forEach(button => button.addEventListener('click', () => {
      lastResultOpener = button;
      scheduledPaper.classList.add('show-result');
      scheduledPaper.querySelector('[data-back-list]').focus();
    }));
    document.querySelector('[data-back-list]').addEventListener('click', () => {
      scheduledPaper.classList.remove('show-result');
      lastResultOpener?.focus();
    });

    const menuButton = document.querySelector('[data-menu-toggle]');
    const menu = document.querySelector('.task-menu');
    menuButton.addEventListener('click', () => {
      const open = !menu.classList.contains('is-open');
      menu.classList.toggle('is-open', open);
      menuButton.setAttribute('aria-expanded', String(open));
      if (open) menu.querySelector('[role="menuitem"]:not(:disabled)').focus();
    });
    menu.addEventListener('keydown', event => {
      const items = [...menu.querySelectorAll('[role="menuitem"]:not(:disabled)')];
      const current = items.indexOf(document.activeElement);
      if (event.key === 'Escape') { menu.classList.remove('is-open'); menuButton.setAttribute('aria-expanded','false'); menuButton.focus(); }
      if (event.key === 'ArrowDown') { event.preventDefault(); items[(current + 1) % items.length].focus(); }
      if (event.key === 'ArrowUp') { event.preventDefault(); items[(current - 1 + items.length) % items.length].focus(); }
      if (event.key === 'Home') { event.preventDefault(); items[0].focus(); }
      if (event.key === 'End') { event.preventDefault(); items[items.length - 1].focus(); }
    });

    document.querySelectorAll('[data-open-edit]').forEach(button => button.addEventListener('click', () => {
      lastEditOpener = button;
      editLayer.classList.add('is-open');
      editLayer.setAttribute('aria-hidden','false');
      document.getElementById('task-title').focus();
    }));
    function closeEdit() {
      editLayer.classList.remove('is-open');
      editLayer.setAttribute('aria-hidden','true');
      lastEditOpener?.focus();
    }
    document.getElementById('edit-close').addEventListener('click', closeEdit);
    document.getElementById('edit-cancel').addEventListener('click', closeEdit);
    document.getElementById('edit-save').addEventListener('click', () => {
      document.getElementById('form-status').textContent = '已保存当前任务设置。';
      window.setTimeout(closeEdit, 450);
    });
    document.querySelectorAll('.frequency-select [data-frequency]').forEach(button => button.addEventListener('click', () => {
      editModal.dataset.frequency = button.dataset.frequency;
      document.querySelectorAll('.frequency-select [data-frequency]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
    }));

    const arrangeInput = document.getElementById('arrange-input');
    const arrangeSubmit = document.getElementById('arrange-submit');
    arrangeInput.addEventListener('input', () => { arrangeSubmit.disabled = !arrangeInput.value.trim(); });
    document.getElementById('arrange-form').addEventListener('submit', event => {
      event.preventDefault();
      const value = arrangeInput.value.trim();
      if (!value) return;
      showScene('chat');
      chatDraft.value = '请创建定时任务：' + value;
      document.getElementById('draft-note').classList.add('is-visible');
      chatDraft.focus();
    });

    function openDetail(opener) {
      lastMarkerOpener = opener;
      scenes.chat.classList.add('detail-open');
      scenes.chat.querySelector('[data-close-detail]').focus();
    }
    function closeDetail() {
      scenes.chat.classList.remove('detail-open');
      lastMarkerOpener?.focus();
    }
    document.querySelectorAll('[data-open-detail]').forEach(button => button.addEventListener('click', () => openDetail(button)));
    document.querySelectorAll('[data-close-detail]').forEach(button => button.addEventListener('click', closeDetail));
    document.querySelectorAll('[data-open-chat]').forEach(button => button.addEventListener('click', () => showScene('chat')));
    document.addEventListener('keydown', event => {
      if (event.key !== 'Escape') return;
      if (editLayer.classList.contains('is-open')) return closeEdit();
      if (scenes.chat.classList.contains('detail-open')) return closeDetail();
      if (menu.classList.contains('is-open')) { menu.classList.remove('is-open'); menuButton.setAttribute('aria-expanded','false'); menuButton.focus(); }
    });
  </script>
</body>
</html>
```

---

## 9. 状态覆盖清单

### Calendar 列表与结果

| 状态 | 设计呈现 |
| --- | --- |
| tasks loading | 保留纸面头和安排入口；显示 2–3 行低对比骨架，`aria-live=polite` |
| tasks empty | 保留安排入口；显示“暂无定时任务，可从上方开始安排” |
| tasks API error | 局部暖红提示 + 重试；月历与 Diary 继续可用；任务数显示未知而非 0 |
| trigger running | 活动行浅填充；左状态图形 + “正在运行”文字 |
| result loading | C8 header/footer 保留；正文显示加载状态 |
| succeeded | 精确 final message 交给现有 Chat Markdown |
| failed | 失败原因 + 重试/历史；若同一 trigger 有 target Thread，保留打开聊天 |
| state unknown | “结果待确认” + 刷新；不自动再次运行 |
| result missing | “结果尚不可用”；不回退其他 assistant message |

### 编辑 Modal

| 状态 | 设计呈现 |
| --- | --- |
| pristine | 保存不可用；状态动作按 effective 显示 |
| dirty | 保存可用 |
| saving | 表单与动作禁用，保存按钮显示固定宽度进度反馈 |
| field error | 错误靠近对应字段，desired 保留 |
| revision conflict | Modal body 顶部显示冲突提示和 latest effective 摘要；desired 不覆盖 |
| API error | 表单级错误与重试；Modal 不关闭 |

### Chat marker 与详情

| 状态 | 设计呈现 |
| --- | --- |
| Tool pending/running | 只显示现有 Tool UI，不生成成功 marker |
| valid completed success | 在 owning turn 下生成 marker |
| Tool explicit failure / malformed | 不生成成功 marker；不影响 Thread hydration |
| detail loading | header + group skeleton |
| detail API error | 标题快照 + 局部错误 + 重试，Chat 主区继续可用 |
| deleted / inaccessible | 历史 marker 保留；详情说明当前不可用 |

---

## 10. 生产接入说明

1. `CalendarPopup` 持有 LIST/RESULT、selected task、anchored menu 与 edit modal 协调；`ScheduledTaskCard` 只负责单行和动作事件。
2. C8 使用既有 history 与 actor scoped Thread message 读取边界；正文复用 `ChatMarkdown`。
3. C9 放入现有 `Modal`，不复制 focus trap、body lock 或 Escape 管理。
4. Chat marker 投影函数保持无状态；实时与 hydration 共用同一函数：

```ts
type ScheduledTaskMarkerViewModel = {
  taskId: string;
  titleSnapshot: string;
  ruleSnapshot: ScheduledTaskRule;
  statusSnapshot: ScheduledTaskStatus;
  revisionSnapshot: number;
};

function projectScheduledTaskMarker(toolPart: ExistingToolPart): ScheduledTaskMarkerViewModel | undefined {
  // 严格匹配真实 tool name、completed lifecycle 与成功 output schema。
  // 任一字段缺失即返回 undefined；不读取 assistant Markdown，不发网络请求。
}
```

5. `ChatView` 作为右侧栏 owner，原子协调 `ScheduledTaskDetailSidebar`、File、Subagent 和 TaskSession；任一打开时关闭其他类型，不得叠出第二条右栏。
6. C4 通过 App/ChatView 的草稿交接回调进入新 Chat，输入保持可编辑且未发送。

---

## 11. 验收清单

- [ ] Calendar 仍是月历、任务、Diary 三张独立悬浮纸面；透明间隙清晰，外层没有共享线框盒。
- [ ] 宽屏右卡栈独立滚动，任务列表和结果不会撑高或移动左侧月历。
- [ ] 安排入口为空时不可提交；非空提交只进入新的 Chat 可编辑草稿，且不自动发送。
- [ ] 任务行左状态、中标题摘要、右编辑/更多；三个点击边界互不嵌套。
- [ ] 更多菜单只显示当前协议可执行动作；危险操作位于分隔线后。
- [ ] 点击任务主体后在同一纸面展示 latest trigger；返回后焦点回原行。
- [ ] 成功结果只渲染精确 final message；“打开聊天”只导航同一 trigger 的 target Thread。
- [ ] 结果长正文自身滚动；结果头、底部动作和 Diary 保持可达。
- [ ] 编辑使用共享 Modal；字段只覆盖现有 title/prompt/once/daily/date/time/timezone/status 能力。
- [ ] Modal 的 desired 在字段错误、API 错误和 revision 冲突后仍保留。
- [ ] Chat 成功 marker 只来自持久化 `create_scheduled_task` Tool success；刷新后可恢复。
- [ ] marker 是单一 button；点击后右侧栏重读 current effective，不直接信任创建快照。
- [ ] 桌面侧栏与消息列表分别滚动；窄屏变为 Drawer，并恢复焦点与背景滚动。
- [ ] loading、empty、failed、state unknown、result missing、deleted 等状态均局部呈现。
- [ ] 键盘可以完成打开结果、编辑、菜单导航、打开/关闭详情；所有图标按钮有可访问名称。
- [ ] reduced motion 下禁用位移动画；任何断点没有横向页面滚动。

---

## 12. 实现边界

- 不增加现有 DTO 未定义的调度字段、协作操作或输入媒介。
- 不增加新的任务分类、推荐区、筛选器和管理仪表盘。
- 不展示内部 task/thread/message ID、revision 数字、claim 或 schema capability。
- 不复制消息 parser、SSE reducer、Thread hydration、Markdown renderer、Modal 或 side panel shell。
