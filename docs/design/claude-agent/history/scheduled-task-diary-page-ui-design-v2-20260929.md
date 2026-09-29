<!-- [Input] html-design-workflow Stage 1 PRD、Stage 2 结构草图、Stage 3 层级逻辑、目标截图、Ink & Memory UI Design v2.1 与现行 CalendarPopup CSS。 -->
<!-- [Output] Calendar 右栏独立 Scheduled tasks / Diary 纸张卡片的历史实现级 UI 规格与完整 HTML/CSS 评审原型。 -->
<!-- [Pos] docs/design/claude-agent/history 下的历史 UI 设计；保留仍有可见外层 Modal 和线框任务信息组的上一版。 -->
<!-- [Sync] 2026-09-29: 采用两个同级独立纸张卡并取消共享大外框；旧版 UI 设计原文移入 history。 -->

# Calendar 日记日期弹窗：独立任务卡与日记卡 UI 设计

## 文档导航

- [同版历史 PRD](../../../prd/claude-agent/history/scheduled-task-diary-page-prd-v2-20260929.md)
- [同版历史页面骨架图](../../../prd/claude-agent/history/scheduled-task-diary-page-structure-sketch-v2-20260929.md)
- [现行系统交互与执行设计](../scheduled-task-loop-interaction-design.md)
- [共享右侧工作区旧版 UI 设计（历史）](./scheduled-task-diary-page-ui-design-v1-20260929.md)

## 0. 设计结论

采用 **Ultra-Sensory Minimalism（超感官纸张极简）**。目标截图中“日期/数量卡头—完整分隔线—两行日记条目”的纸面层级是本轮视觉依据；`Ink & Memory UI Design v2.1` 提供颜色、字体、留白与阴影规则。

右栏取消共享可见大外框，只保留透明布局与滚动职责。`Scheduled tasks` 与 `Diary` 是两个同级、独立闭合的 Paper Cream 卡片，各自拥有标题、计数、分隔线和正文。两卡之间固定显示 16px Warm Canvas 间隙。任务请求的 loading、error、empty、list 都只替换任务卡正文；Diary 卡始终保持自己的轮廓与交互。

这次只重排现有信息和样式，不新增业务状态、确认弹窗、创建入口、折叠规则、排序规则或数据请求。任务的立即运行、暂停/恢复、编辑、历史、删除/撤销、打开执行会话与所有局部失败反馈继续由现有 `ScheduledTaskCard` 和状态管理负责。

## 1. 审美分析

### 1.1 目标截图的可复用特征

| 视觉要素 | 截图证据 | Calendar 映射 |
| --- | --- | --- |
| 单张完整纸面 | 暖白背景、完整圆角轮廓、卡头与正文闭合 | Scheduled tasks 与 Diary 分别成为完整纸面 |
| 卡头层级 | 日期标题与数量上下排列，正文前有贯穿横线 | 分类标题/数量在各自 header，header 与 body 各有完整分隔线 |
| 两行条目 | 第一行时间、状态、删除；第二行标题 | Diary 条目保持时间/当前笔记/删除 + 标题两行结构 |
| 当前笔记 | 绿色文字徽标、绿色细边、极浅绿色底 | 使用现有 success token 的小面积 `color-mix`，同时保留文字标识 |
| 克制材质 | 无厚重悬浮阴影，层级由纸色、细边和留白建立 | 分类卡静止无阴影；菜单等遮挡型浮层保留既有阴影 |

### 1.2 PDF 规范的页面化解释

- 大面积底色使用 `--color-bg-app`（Warm Canvas），卡片使用 `--color-bg-paper`（Paper Cream）。
- 标题、正文、辅助信息依次使用 `--color-text-primary`、`--color-text-body`、`--color-text-secondary`/`--color-text-muted`。
- 所有纸边和卡内分隔线使用 `--color-border-paper`；不引入孤立十六进制颜色。
- 分类卡是用户明确要求的两个业务边界。卡内条目保持轻量，避免继续叠加重阴影和多层卡片表面。
- 手写感只用于月份、日期上下文和分类标题；密集事实、状态、表单与操作继续使用清晰的 UI 正文字体。

## 2. Aesthetic Style 表

| 维度 | 定稿 | 实现规则 |
| --- | --- | --- |
| 风格 | 超感官纸张极简 | 温暖、安静、低饱和，以纸面触感和精确间距表达层级 |
| 页面底 | Warm Canvas | 弹窗内容区与两卡间隙必须能看到 `--color-bg-app` 或等价现有底色 |
| 分类卡 | Paper Cream | 1px Border Paper、16px 圆角、无常驻阴影 |
| 卡头 | 手写标题 + 轻计数 | 14px 上下、16px 左右内边距；计数为 28px 轻量圆形/胶囊 |
| 卡身 | 清晰正文 | 16px 内边距；任务/日记条目间距 12px |
| 卡间距 | 16px Warm Canvas | 不能收缩为共享分隔线，不能由相同 Paper Cream 连成一块 |
| 条目 | Solid Cream 轻行 | 1px Border Paper、12–14px 圆角、静止无阴影 |
| 当前日记 | 小面积 Spark Green 语义 | success 细边 + 8% success 浅底 + `Current note` 文字徽标 |
| 主操作 | Action Brown | 沿用现有主按钮；不因分卡新增按钮 |
| 错误 | 卡内砖红浅底 | 只在任务卡正文出现，保留 Retry；不遮挡 Diary |
| 动效 | 120–160ms 色彩反馈 | 不移动卡片；reduced-motion 下关闭非必要过渡 |

## 3. 组件结构

| ID | 生产组件/类 | 视觉职责 | 业务职责 |
| --- | --- | --- | --- |
| A1 | `CalendarPopup` / `.calendar-popup-modal` | 唯一页面级浮层 | 焦点约束、关闭、整体滚动边界 |
| B1 | `.calendar-popup__calendar` | 左侧独立月历纸面 | 月份切换、日期选择、日记标记 |
| C1 | `.calendar-popup__workspace` | **透明、无边框、无背景、无阴影** | 宽屏右栏 / 窄屏月历后内容栈 |
| C2 | `.calendar-popup__date-summary` | 无卡片外框的日期上下文 | 告知两卡共同查询日期，不显示混合计数 |
| C3 | `.calendar-popup__workspace-scroll` | 透明卡片栈、统一纵向滚动 | 排列 D1/E1，维持 16px 卡间距 |
| D1 | `.calendar-popup__task-section` | 第一张独立 Paper Cream 卡 | 承载全部任务日期级状态和任务条目 |
| D2/D3 | `.calendar-popup__card-header` | 任务标题、任务计数、需处理入口 | 数量只归任务；loading/error 只改变任务局部文本 |
| D4 | `.calendar-popup__card-body` | 任务局部正文 | `loading | error | empty | task-list` 互斥呈现 |
| D5 | `ScheduledTaskCard` | 轻量任务条目 | 保留立即运行、暂停/恢复、更多、编辑、历史、删除/撤销、打开会话 |
| E1 | `.calendar-popup__diary-section` | 第二张独立 Paper Cream 卡 | 承载日记空态或列表 |
| E2/E3 | `.calendar-popup__card-header` | 日记标题和日记计数 | 数量只来自 `selectedEntries.length` |
| E4 | `.calendar-popup__card-body` | 日记局部正文 | 日记为空或条目列表 |
| E5/E6 | `.calendar-popup__diary` | 两行日记条目 | 打开与删除为两个独立控制 |

### 3.1 DOM 冻结

```text
Calendar dialog
├── Month calendar paper
└── Detail card stack (transparent, no surface)
    ├── Selected date context
    └── Scroll stack
        ├── Scheduled tasks card
        │   ├── own header + own count
        │   ├── own divider
        │   └── own body: loading | error | empty | task list
        ├── 16px Warm Canvas gap
        └── Diary card
            ├── own header + own count
            ├── own divider
            └── own body: empty | diary list
```

`Scheduled tasks card` 与 `Diary card` 必须是 `.calendar-popup__workspace-scroll` 下的同级 `section`。C1/C3 不得使用伪元素、背景、边框或阴影绘制同时包住两卡的轮廓。

## 4. 视觉标尺

### 4.1 颜色与字体

| 语义 | 现有 token | 用途 |
| --- | --- | --- |
| Warm Canvas | `--color-bg-app` | 右栏底、两卡间隙、弹窗内容底 |
| Paper Cream | `--color-bg-paper` | 月历与两张分类卡 |
| Solid Cream | `--color-bg-surface-solid` | 条目、输入、菜单等不透明表面 |
| Border Paper | `--color-border-paper` | 卡片边框、卡头分隔线、条目边框 |
| Charcoal Brown | `--color-text-primary` | 日期、分类标题、任务/日记标题 |
| Body Brown | `--color-text-body` | 正文、操作 |
| Warm Brown | `--color-text-secondary` | 计划、时区、辅助事实 |
| Muted Tan | `--color-text-muted` | 时间、placeholder、弱信息 |
| Action Brown | `--color-action-primary` | 任务主操作 |
| Spark Green 语义 | `--color-state-success` | 当前笔记、成功状态的小面积强调 |
| Danger 语义 | `--color-state-danger` | 失败、删除 hover、错误边界 |

标题字体：`'Excalifont', 'Xiaolai', 'Noto Serif SC', Georgia, serif`。正文与控制：`'Noto Sans SC', system-ui, sans-serif`。生产实现继续消费仓库现有全局字体和 token，不复制色值。

### 4.2 尺寸

| 元素 | 定稿值 |
| --- | --- |
| 双栏间距 | 16px |
| 日期上下文与任务卡间距 | 12px |
| 任务卡与日记卡间距 | 16px |
| 分类卡圆角 | 16px（窄屏 12px） |
| 分类卡边框 | 1px Border Paper |
| 卡头内边距 | 14px 16px |
| 卡身内边距 | 16px |
| 条目间距 | 12px |
| 条目圆角 | 14px；日记可为 12px |
| 控件最小触控高度 | 42px；主要关闭/月切换维持 44px |
| 分类标题 | 16px / 1.35，手写字体，600–700 |
| 日期上下文 | 18px / 1.35，手写字体，600 |
| 计数 | 最小 28×28px，12px 字号 |

分类卡按内容自然增高，不强制等高。任务编辑和历史展开增加 D1 高度，由 C1 的同一滚动路径承载。

## 5. 状态视觉规则

| 状态 | Scheduled tasks card | Diary card |
| --- | --- | --- |
| loading | 卡头保留；计数显示加载文案；body 显示轻量 loading | 保持可读可操作 |
| error | 卡头保留；计数显示未知；body 内 alert + Retry | 保持可读可操作 |
| empty | 卡头计数 0；body 显示无任务文案 | 保持自身状态 |
| list | 卡头显示任务数；body 显示完整现有任务条目 | 保持自身状态 |
| diary empty | 不变 | 卡头计数 0；body 显示无日记文案 |
| current diary | 不变 | success 细边/浅底 + `Current note` 文字徽标 |

状态反馈不显示 HTTP 状态、capability、调用 ID 或内部错误详情。任务 API 失败不能改变 Diary 计数或清空 `selectedEntries`。

## 6. 响应式与滚动

### 宽屏（`> 56rem`）

- 月历与右栏保持现有两列比例。
- 月历纸面顶部对齐；右栏 C1 无可见表面。
- C1 是右栏唯一滚动边界；D1/E1 不创建常驻嵌套滚动。
- 卡片保持自然高度，完整显示两卡间 Warm Canvas。

### 中窄屏（`<= 56rem`）

- 使用现有断点切为单列，顺序为月历 → 日期上下文 →任务卡 → 日记卡。
- C1 继续透明；D1/E1 仍有各自完整外轮廓。
- 弹窗内容承担纵向滚动，卡片内部不新建滚动区。

### 小屏（`<= 40rem`）

- 沿用现有全视口 Modal 规则与 12px 卡片圆角。
- 任务事实收为单列，主操作可占整行。
- 日记第一行放时间、Current note、删除；标题占第二行。超长标题截断但 `aria-label` 保留全文。
- 禁止横向滚动；按钮换行不能挤掉状态文字或删除入口。

## 7. 微交互与无障碍

1. 分类卡静止无阴影，也不在 hover 时整体上浮；仅条目/按钮改变背景或边框色。
2. 可交互条目过渡只包含 `background-color`、`border-color` 和 `color`，时长 140ms。
3. 所有焦点继续使用 `--color-border-focus` 2px 外描边，不能被卡片 overflow 裁切。
4. D1/E1 分别使用 `section[aria-labelledby]`，标题 ID 唯一；计数容器使用 `aria-live="polite"`。
5. 任务错误使用 `role="alert"`。自动刷新不能反复播报相同错误。
6. 日记打开按钮与删除按钮保持两个独立焦点；当前笔记同时由文字和颜色表达。
7. `prefers-reduced-motion: reduce` 下把非必要过渡缩短到 0.01ms，不增加位移动画。

## 8. 生产类名改造要点

现行 `.calendar-popup__workspace` 同时拥有 border、Paper 背景、圆角和阴影，应改为透明布局容器。现行 `.calendar-popup__section + .calendar-popup__section` 通过共享大面板内的顶部横线分区，应由两张卡自己的边框和卡间 `gap` 取代。

建议复用现有 JSX 和业务状态，只做以下结构调整：

```tsx
<section className="calendar-popup__workspace" aria-labelledby="calendar-popup-date-title">
  <header className="calendar-popup__date-summary">
    <h3 id="calendar-popup-date-title">{selectedDateLabel}</h3>
  </header>

  <div className="calendar-popup__workspace-scroll">
    {isAuthenticated ? (
      <section className="calendar-popup__section calendar-popup__task-section"
        aria-labelledby="calendar-popup-task-title">
        <header className="calendar-popup__card-header">
          <h3 id="calendar-popup-task-title">{t('calendar.scheduledSectionTitle')}</h3>
          <div className="calendar-popup__card-count" aria-live="polite">…</div>
        </header>
        <div className="calendar-popup__card-body">…existing task states and ScheduledTaskCard list…</div>
      </section>
    ) : null}

    <section className="calendar-popup__section calendar-popup__diary-section"
      aria-labelledby="calendar-popup-diary-title">
      <header className="calendar-popup__card-header">
        <h3 id="calendar-popup-diary-title">{t('calendar.diarySectionTitle')}</h3>
        <span className="calendar-popup__card-count" aria-live="polite">{selectedEntries.length}</span>
      </header>
      <div className="calendar-popup__card-body">…existing diary empty/list…</div>
    </section>
  </div>
</section>
```

实现时注意：已认证且已选择日期时任务卡始终渲染，空列表进入 D4c；不能沿用当前 `scheduledTasks.length > 0` 才渲染整个任务 section 的条件。

## 9. 完整 HTML/CSS 评审原型

以下是独立可打开的静态视觉原型。它使用技能要求的 Tailwind CSS 2.2.19、Font Awesome 6.0.0、Noto Serif/Sans SC，并用与生产一致的语义 token 和组件类名表达布局。静态示例只用于评审；生产逻辑继续由 `CalendarPopup.tsx`、`ScheduledTaskCard`、现有 API/i18n/路由和服务端数据驱动。

把任务正文的 `data-state="list"` 改为 `loading`、`error` 或 `empty`，即可查看已有任务局部状态；这不是新增业务状态。

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Ink &amp; Memory — Calendar card review</title>
  <link rel="stylesheet" href="https://lf3-cdn-tos.bytecdntp.com/cdn/expire-1-M/tailwindcss/2.2.19/tailwind.min.css" />
  <link rel="stylesheet" href="https://lf6-cdn-tos.bytecdntp.com/cdn/expire-100-M/font-awesome/6.0.0/css/all.min.css" />
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;500;600;700&amp;family=Noto+Sans+SC:wght@300;400;500;700&amp;display=swap" />
  <style>
    :root {
      /* Standalone preview fallbacks mirror frontend/app/_dream/styles/tokens.css.
         Production must consume the existing tokens instead of redeclaring values. */
      --color-bg-app: #f6efe5;
      --color-bg-paper: #fffaf2;
      --color-bg-surface-solid: #fffdf8;
      --color-bg-overlay: rgba(39, 31, 24, 0.5);
      --color-bg-hover: rgba(95, 74, 54, 0.06);
      --color-border-paper: #d8c7b3;
      --color-border-focus: #5f4a36;
      --color-text-primary: #3f3429;
      --color-text-body: #4b3f33;
      --color-text-secondary: #7a6a59;
      --color-text-muted: #9a8a78;
      --color-action-primary: #5f4a36;
      --color-action-link: #4a90e2;
      --color-state-success: #7e9468;
      --color-state-warning: #c78855;
      --color-state-danger: #b85c4d;
      --color-text-on-action: #fff;
      --color-shadow-soft: rgba(91, 69, 44, 0.08);
      --calendar-card-gap: 1rem;
      --calendar-card-radius: 1rem;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      background: var(--color-bg-app);
      color: var(--color-text-body);
      font-family: 'Noto Sans SC', system-ui, sans-serif;
    }

    button { font: inherit; }

    button:focus-visible {
      outline: 2px solid var(--color-border-focus);
      outline-offset: 2px;
    }

    .prototype-backdrop {
      min-height: 100vh;
      padding: 2rem;
      background: var(--color-bg-overlay);
    }

    .calendar-popup-modal {
      width: min(70rem, calc(100vw - 2rem));
      height: min(48rem, calc(100vh - 2rem));
      margin: 0 auto;
      padding: 1rem;
      overflow: hidden;
      border: 1px solid var(--color-border-paper);
      border-radius: 22px;
      background: var(--color-bg-app);
      box-shadow: 0 18px 48px rgba(39, 31, 24, 0.18);
    }

    .calendar-popup__dialog-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
      min-height: 2.75rem;
      margin-bottom: .75rem;
    }

    .calendar-popup__dialog-header h2,
    .calendar-popup__month-heading h3,
    .calendar-popup__date-summary h3,
    .calendar-popup__card-header h3,
    .calendar-popup__task h4 {
      margin: 0;
      color: var(--color-text-primary);
      font-family: 'Noto Serif SC', Georgia, serif;
    }

    .calendar-popup__dialog-header h2 { font-size: 1.25rem; font-weight: 700; }

    .calendar-popup__close,
    .calendar-popup__month-heading button,
    .calendar-popup__icon-button {
      display: inline-grid;
      place-items: center;
      width: 2.75rem;
      height: 2.75rem;
      padding: 0;
      border: 0;
      border-radius: 10px;
      background: transparent;
      color: var(--color-text-secondary);
      cursor: pointer;
    }

    .calendar-popup__close:hover,
    .calendar-popup__month-heading button:hover,
    .calendar-popup__icon-button:hover { background: var(--color-bg-hover); color: var(--color-text-primary); }

    .calendar-popup {
      display: grid;
      grid-template-columns: minmax(19rem, .85fr) minmax(22rem, 1.15fr);
      gap: 1rem;
      height: calc(100% - 3.5rem);
      min-width: 0;
    }

    .calendar-popup__calendar {
      align-self: start;
      min-width: 0;
      padding: 1rem;
      border: 1px solid var(--color-border-paper);
      border-radius: 16px;
      background: var(--color-bg-paper);
    }

    .calendar-popup__month-heading,
    .calendar-popup__card-header,
    .calendar-popup__task-heading {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: .75rem;
    }

    .calendar-popup__month-heading h3 { font-size: 1.1rem; }

    .calendar-popup__weekdays,
    .calendar-popup__grid {
      display: grid;
      grid-template-columns: repeat(7, minmax(0, 1fr));
      gap: .35rem;
    }

    .calendar-popup__weekdays {
      margin: .75rem 0 .35rem;
      color: var(--color-text-muted);
      font-size: .75rem;
      font-weight: 700;
      text-align: center;
    }

    .calendar-popup__day,
    .calendar-popup__day-placeholder {
      min-width: 0;
      min-height: 2.75rem;
      aspect-ratio: 1;
    }

    .calendar-popup__day {
      position: relative;
      display: grid;
      place-items: center;
      border: 2px solid transparent;
      border-radius: 11px;
      background: transparent;
      color: var(--color-text-body);
      cursor: pointer;
    }

    .calendar-popup__day:hover { background: var(--color-bg-hover); }
    .calendar-popup__day--has-entry { background: var(--color-bg-surface-solid); }
    .calendar-popup__day--selected { border-color: var(--color-border-focus); font-weight: 700; }

    .calendar-popup__day--today::after {
      content: '';
      position: absolute;
      inset: .28rem;
      border: 2px solid var(--color-state-warning);
      border-radius: 9px;
      pointer-events: none;
    }

    .calendar-popup__day i {
      position: absolute;
      bottom: .3rem;
      width: .32rem;
      height: .32rem;
      border-radius: 999px;
      background: var(--color-action-link);
    }

    /* C1: layout only. No shared right-column card surface. */
    .calendar-popup__workspace {
      display: flex;
      min-width: 0;
      min-height: 0;
      flex-direction: column;
      overflow: hidden;
      border: 0;
      border-radius: 0;
      background: transparent;
      box-shadow: none;
    }

    .calendar-popup__date-summary {
      flex: 0 0 auto;
      padding: .1rem .15rem .75rem;
      border: 0;
      background: transparent;
    }

    .calendar-popup__date-summary h3 { font-size: 1.125rem; font-weight: 600; }

    .calendar-popup__workspace-scroll {
      display: grid;
      flex: 1 1 auto;
      align-content: start;
      gap: var(--calendar-card-gap);
      min-height: 0;
      padding: 0 .15rem .15rem;
      overflow-y: auto;
      overflow-x: visible;
      overscroll-behavior: contain;
    }

    /* D1/E1: two sibling paper cards, each with its own closed outline. */
    .calendar-popup__section {
      min-width: 0;
      overflow: visible;
      border: 1px solid var(--color-border-paper);
      border-radius: var(--calendar-card-radius);
      background: var(--color-bg-paper);
      box-shadow: none;
    }

    .calendar-popup__card-header {
      min-height: 3.5rem;
      padding: .875rem 1rem;
      border-bottom: 1px solid var(--color-border-paper);
    }

    .calendar-popup__card-header h3 { font-size: 1rem; font-weight: 700; }

    .calendar-popup__card-meta {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: flex-end;
      gap: .4rem;
    }

    .calendar-popup__card-count {
      display: inline-grid;
      min-width: 1.75rem;
      min-height: 1.75rem;
      padding: 0 .45rem;
      place-items: center;
      border-radius: 999px;
      background: var(--color-bg-hover);
      color: var(--color-text-secondary);
      font-size: .75rem;
      line-height: 1;
    }

    .calendar-popup__count-alert {
      min-height: 1.75rem;
      padding: .2rem .5rem;
      border: 0;
      border-radius: 999px;
      background: color-mix(in srgb, var(--color-state-danger) 8%, transparent);
      color: var(--color-state-danger);
      font-size: .75rem;
      font-weight: 700;
      cursor: pointer;
    }

    .calendar-popup__card-body { padding: 1rem; }

    .calendar-popup__task-list,
    .calendar-popup__diary-list { display: grid; gap: .75rem; }

    .calendar-popup__task,
    .calendar-popup__diary {
      min-width: 0;
      border: 1px solid var(--color-border-paper);
      border-radius: 14px;
      background: var(--color-bg-surface-solid);
      box-shadow: none;
    }

    .calendar-popup__task {
      padding: .95rem 1rem 1rem 1.15rem;
      border-left: 3px solid var(--color-state-success);
    }

    .calendar-popup__task-heading > div { min-width: 0; }
    .calendar-popup__task h4 { overflow-wrap: anywhere; font-size: 1rem; font-weight: 700; }

    .calendar-popup__status {
      display: inline-flex;
      align-items: center;
      min-height: 1.5rem;
      margin-top: .35rem;
      padding: .1rem .5rem;
      border-radius: 999px;
      background: var(--color-bg-hover);
      color: var(--color-text-secondary);
      font-size: .72rem;
      font-weight: 700;
    }

    .calendar-popup__task-facts {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: .65rem;
      margin: .85rem 0;
    }

    .calendar-popup__task-facts > div,
    .calendar-popup__recent {
      min-width: 0;
      padding: .65rem;
      border-radius: 10px;
      background: color-mix(in srgb, var(--color-bg-paper) 72%, transparent);
    }

    .calendar-popup__task-facts dt,
    .calendar-popup__recent > span {
      color: var(--color-text-muted);
      font-size: .72rem;
      font-weight: 700;
    }

    .calendar-popup__task-facts dd { margin: .25rem 0 0; color: var(--color-text-body); font-size: .82rem; }
    .calendar-popup__recent strong { display: block; margin-top: .3rem; font-size: .82rem; }
    .calendar-popup__recent small { color: var(--color-text-secondary); }

    .calendar-popup__primary-actions {
      display: flex;
      flex-wrap: wrap;
      gap: .5rem;
      margin-top: .8rem;
    }

    .calendar-popup__button,
    .calendar-popup__alert button {
      min-height: 2.625rem;
      padding: .55rem .85rem;
      border: 1px solid var(--color-border-paper);
      border-radius: 10px;
      background: var(--color-bg-surface-solid);
      color: var(--color-text-body);
      cursor: pointer;
    }

    .calendar-popup__button--primary {
      border-color: var(--color-action-primary);
      background: var(--color-action-primary);
      color: var(--color-text-on-action);
    }

    .calendar-popup__button--quiet { border-color: transparent; background: transparent; color: var(--color-action-link); }

    .calendar-popup__diary {
      display: flex;
      align-items: center;
      gap: .5rem;
      padding: .75rem .85rem;
      border-radius: 12px;
      transition: background-color 140ms ease, border-color 140ms ease;
    }

    .calendar-popup__diary--current {
      border-color: color-mix(in srgb, var(--color-state-success) 52%, var(--color-border-paper));
      background: color-mix(in srgb, var(--color-state-success) 8%, var(--color-bg-surface-solid));
      box-shadow: inset 3px 0 0 var(--color-state-success);
    }

    .calendar-popup__diary-open {
      display: grid;
      grid-template-columns: auto auto minmax(0, 1fr);
      flex: 1 1 auto;
      align-items: center;
      gap: .35rem .45rem;
      min-width: 0;
      min-height: 2.625rem;
      padding: 0;
      border: 0;
      background: transparent;
      color: var(--color-text-body);
      text-align: left;
      cursor: pointer;
    }

    .calendar-popup__diary-open > span { color: var(--color-text-secondary); font-size: .75rem; }

    .calendar-popup__diary-open em {
      padding: .15rem .4rem;
      border-radius: 999px;
      background: var(--color-state-success);
      color: var(--color-text-on-action);
      font-size: .68rem;
      font-style: normal;
    }

    .calendar-popup__diary-open strong {
      grid-column: 1 / -1;
      min-width: 0;
      overflow: hidden;
      color: var(--color-text-primary);
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .calendar-popup__diary-delete {
      min-width: 2.625rem;
      min-height: 2.625rem;
      padding: .4rem;
      border: 0;
      border-radius: 8px;
      background: transparent;
      color: var(--color-text-muted);
      cursor: pointer;
    }

    .calendar-popup__diary-delete:hover {
      background: color-mix(in srgb, var(--color-state-danger) 10%, transparent);
      color: var(--color-state-danger);
    }

    .calendar-popup__loading,
    .calendar-popup__empty { margin: 0; color: var(--color-text-secondary); font-size: .82rem; }

    .calendar-popup__alert {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: .5rem;
      margin: 0;
      padding: .7rem .8rem;
      border: 1px solid color-mix(in srgb, var(--color-state-danger) 35%, var(--color-border-paper));
      border-radius: 10px;
      background: color-mix(in srgb, var(--color-state-danger) 8%, var(--color-bg-surface-solid));
      color: var(--color-text-body);
      font-size: .82rem;
    }

    .calendar-popup__task-state > * { display: none; }
    .calendar-popup__task-state[data-state='loading'] > .calendar-popup__loading { display: block; }
    .calendar-popup__task-state[data-state='error'] > .calendar-popup__alert { display: flex; }
    .calendar-popup__task-state[data-state='empty'] > .calendar-popup__empty { display: block; }
    .calendar-popup__task-state[data-state='list'] > .calendar-popup__task-list { display: grid; }

    @media (max-width: 56rem) {
      .prototype-backdrop { padding: .5rem; }
      .calendar-popup-modal { width: calc(100vw - 1rem); height: calc(100vh - 1rem); padding: .75rem; }
      .calendar-popup { grid-template-columns: minmax(0, 1fr); overflow-y: auto; }
      .calendar-popup__calendar { align-self: auto; }
      .calendar-popup__workspace { min-height: 30rem; overflow: visible; }
      .calendar-popup__workspace-scroll { flex: none; overflow: visible; }
    }

    @media (max-width: 40rem) {
      .prototype-backdrop { padding: 0; }
      .calendar-popup-modal { width: 100vw; height: 100vh; padding: .65rem; border: 0; border-radius: 0; }
      .calendar-popup { height: auto; overflow: visible; }
      .calendar-popup__calendar,
      .calendar-popup__section { border-radius: 12px; }
      .calendar-popup__calendar { padding: .65rem; }
      .calendar-popup__day,
      .calendar-popup__day-placeholder { min-height: 2.625rem; }
      .calendar-popup__task-facts { grid-template-columns: minmax(0, 1fr); }
      .calendar-popup__primary-actions .calendar-popup__button--primary { flex: 1 0 100%; }
      .calendar-popup__card-header { padding: .8rem .875rem; }
      .calendar-popup__card-body { padding: .875rem; }
    }

    @media (prefers-reduced-motion: reduce) {
      .calendar-popup *,
      .calendar-popup *::before,
      .calendar-popup *::after {
        transition-duration: .01ms !important;
        animation-duration: .01ms !important;
        animation-iteration-count: 1 !important;
      }
    }
  </style>
</head>
<body>
  <main class="prototype-backdrop flex items-center justify-center">
    <section class="calendar-popup-modal" role="dialog" aria-modal="true" aria-labelledby="calendar-dialog-title">
      <header class="calendar-popup__dialog-header">
        <h2 id="calendar-dialog-title">Calendar</h2>
        <button class="calendar-popup__close" type="button" aria-label="Close calendar">
          <i class="fa-solid fa-xmark" aria-hidden="true"></i>
        </button>
      </header>

      <div class="calendar-popup">
        <section class="calendar-popup__calendar" aria-label="Month calendar">
          <header class="calendar-popup__month-heading">
            <button type="button" aria-label="Previous month"><i class="fa-solid fa-chevron-left" aria-hidden="true"></i></button>
            <h3>September 2026</h3>
            <button type="button" aria-label="Next month"><i class="fa-solid fa-chevron-right" aria-hidden="true"></i></button>
          </header>
          <div class="calendar-popup__weekdays" aria-hidden="true">
            <span>Sun</span><span>Mon</span><span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Sat</span>
          </div>
          <div class="calendar-popup__grid" role="grid" aria-label="September 2026">
            <span class="calendar-popup__day-placeholder"></span><span class="calendar-popup__day-placeholder"></span>
            <button class="calendar-popup__day calendar-popup__day--has-entry" role="gridcell" aria-selected="false"><span>1</span><i></i></button>
            <button class="calendar-popup__day calendar-popup__day--has-entry" role="gridcell" aria-selected="false"><span>2</span><i></i></button>
            <button class="calendar-popup__day" role="gridcell" aria-selected="false">3</button>
            <button class="calendar-popup__day" role="gridcell" aria-selected="false">4</button>
            <button class="calendar-popup__day" role="gridcell" aria-selected="false">5</button>
            <button class="calendar-popup__day calendar-popup__day--has-entry" role="gridcell" aria-selected="false"><span>6</span><i></i></button>
            <button class="calendar-popup__day" role="gridcell" aria-selected="false">7</button>
            <button class="calendar-popup__day" role="gridcell" aria-selected="false">8</button>
            <button class="calendar-popup__day" role="gridcell" aria-selected="false">9</button>
            <button class="calendar-popup__day" role="gridcell" aria-selected="false">10</button>
            <button class="calendar-popup__day calendar-popup__day--has-entry" role="gridcell" aria-selected="false"><span>11</span><i></i></button>
            <button class="calendar-popup__day calendar-popup__day--has-entry" role="gridcell" aria-selected="false"><span>12</span><i></i></button>
            <button class="calendar-popup__day calendar-popup__day--has-entry" role="gridcell" aria-selected="false"><span>13</span><i></i></button>
            <button class="calendar-popup__day calendar-popup__day--has-entry" role="gridcell" aria-selected="false"><span>14</span><i></i></button>
            <button class="calendar-popup__day calendar-popup__day--has-entry" role="gridcell" aria-selected="false"><span>15</span><i></i></button>
            <button class="calendar-popup__day" role="gridcell" aria-selected="false">16</button>
            <button class="calendar-popup__day calendar-popup__day--has-entry" role="gridcell" aria-selected="false"><span>17</span><i></i></button>
            <button class="calendar-popup__day calendar-popup__day--has-entry" role="gridcell" aria-selected="false"><span>18</span><i></i></button>
            <button class="calendar-popup__day calendar-popup__day--has-entry" role="gridcell" aria-selected="false"><span>19</span><i></i></button>
            <button class="calendar-popup__day" role="gridcell" aria-selected="false">20</button>
            <button class="calendar-popup__day" role="gridcell" aria-selected="false">21</button>
            <button class="calendar-popup__day" role="gridcell" aria-selected="false">22</button>
            <button class="calendar-popup__day" role="gridcell" aria-selected="false">23</button>
            <button class="calendar-popup__day" role="gridcell" aria-selected="false">24</button>
            <button class="calendar-popup__day" role="gridcell" aria-selected="false">25</button>
            <button class="calendar-popup__day" role="gridcell" aria-selected="false">26</button>
            <button class="calendar-popup__day calendar-popup__day--has-entry" role="gridcell" aria-selected="false"><span>27</span><i></i></button>
            <button class="calendar-popup__day calendar-popup__day--has-entry" role="gridcell" aria-selected="false"><span>28</span><i></i></button>
            <button class="calendar-popup__day calendar-popup__day--selected calendar-popup__day--today calendar-popup__day--has-entry" role="gridcell" aria-selected="true"><span>29</span><i></i></button>
            <button class="calendar-popup__day" role="gridcell" aria-selected="false">30</button>
          </div>
        </section>

        <section class="calendar-popup__workspace" aria-labelledby="calendar-popup-date-title">
          <header class="calendar-popup__date-summary">
            <h3 id="calendar-popup-date-title">Today</h3>
          </header>

          <div class="calendar-popup__workspace-scroll">
            <section class="calendar-popup__section calendar-popup__task-section" aria-labelledby="calendar-popup-task-title">
              <header class="calendar-popup__card-header">
                <h3 id="calendar-popup-task-title">Scheduled tasks</h3>
                <div class="calendar-popup__card-meta" aria-live="polite">
                  <span class="calendar-popup__card-count">1</span>
                </div>
              </header>
              <div class="calendar-popup__card-body calendar-popup__task-state" data-state="list">
                <p class="calendar-popup__loading" aria-busy="true">Loading scheduled tasks…</p>
                <div class="calendar-popup__alert" role="alert">
                  <span>Tasks are temporarily unavailable.</span>
                  <button type="button">Retry</button>
                </div>
                <p class="calendar-popup__empty">No scheduled tasks for this day.</p>
                <div class="calendar-popup__task-list">
                  <article class="calendar-popup__task" tabindex="-1">
                    <header class="calendar-popup__task-heading">
                      <div>
                        <h4>Morning review</h4>
                        <span class="calendar-popup__status">Enabled</span>
                      </div>
                      <button class="calendar-popup__icon-button" type="button" aria-label="More actions for Morning review">
                        <i class="fa-solid fa-ellipsis" aria-hidden="true"></i>
                      </button>
                    </header>
                    <dl class="calendar-popup__task-facts">
                      <div><dt>Schedule</dt><dd>Daily at 09:00</dd></div>
                      <div><dt>Time zone</dt><dd>Asia/Shanghai</dd></div>
                      <div><dt>Next run</dt><dd>Tomorrow, 09:00</dd></div>
                      <div><dt>Latest run</dt><dd>Succeeded · Today, 09:01</dd></div>
                    </dl>
                    <div class="calendar-popup__recent">
                      <span>Latest result</span>
                      <strong>Daily reflection completed</strong>
                      <small>Execution record remains linked to its Thread and Run.</small>
                    </div>
                    <div class="calendar-popup__primary-actions">
                      <button class="calendar-popup__button calendar-popup__button--primary" type="button">Run now</button>
                      <button class="calendar-popup__button" type="button">Pause</button>
                      <button class="calendar-popup__button calendar-popup__button--quiet" type="button">History</button>
                      <button class="calendar-popup__button calendar-popup__button--quiet" type="button">Open thread</button>
                    </div>
                  </article>
                </div>
              </div>
            </section>

            <section class="calendar-popup__section calendar-popup__diary-section" aria-labelledby="calendar-popup-diary-title">
              <header class="calendar-popup__card-header">
                <h3 id="calendar-popup-diary-title">Diary</h3>
                <span class="calendar-popup__card-count" aria-live="polite">2</span>
              </header>
              <div class="calendar-popup__card-body">
                <div class="calendar-popup__diary-list">
                  <article class="calendar-popup__diary calendar-popup__diary--current">
                    <button class="calendar-popup__diary-open" type="button" aria-label="Open diary: Untitled">
                      <span>02:16 PM</span><em>Current note</em><strong>Untitled</strong>
                    </button>
                    <button class="calendar-popup__diary-delete" type="button" aria-label="Delete diary: Untitled">Delete</button>
                  </article>
                  <article class="calendar-popup__diary">
                    <button class="calendar-popup__diary-open" type="button" aria-label="Open diary: A quiet afternoon">
                      <span>01:14 AM</span><strong>A quiet afternoon</strong>
                    </button>
                    <button class="calendar-popup__diary-delete" type="button" aria-label="Delete diary: A quiet afternoon">Delete</button>
                  </article>
                </div>
              </div>
            </section>
          </div>
        </section>
      </div>
    </section>
  </main>
</body>
</html>
```

## 10. 实现映射与验收

### 10.1 必须复用

- 复用 `CalendarPopup` 的月历选择、日期键盘导航、日记读取/删除和焦点逻辑。
- 复用 `ScheduledTaskCard` 的状态、操作、编辑、历史、删除/撤销及 Thread 跳转。
- 复用 `scheduledTaskApi`、现有 DTO、事件刷新、i18n 与服务端 `effective/revision/next_run_at`。
- 复用 `frontend/app/_dream/styles/tokens.css`；原型中的 token 值仅为脱离应用运行时的预览 fallback。

### 10.2 不进入实现

- 不增加 Calendar 内任务创建入口、Tabs、Accordion、拖拽、卡片排序或等高规则。
- 不新增任务/日记数据模型、请求、状态机或移动端业务分支。
- 不增加共享右栏背景、共享边框、共享阴影或包围两卡的伪元素。
- 不把任务执行历史混入 Diary，也不把日记当作任务运行结果。

### 10.3 视觉与结构验收

- [ ] `.calendar-popup__workspace` 无 border、background、border-radius、box-shadow。
- [ ] `.calendar-popup__task-section` 与 `.calendar-popup__diary-section` 是同一父级下的两个独立 sibling `section`。
- [ ] 两卡各自存在 Paper Cream 背景、1px Border Paper、圆角、标题、计数、完整 header/body 分隔线。
- [ ] 两卡之间固定显示 16px Warm Canvas，不使用共享横线替代。
- [ ] 已认证用户任务为 0 时任务卡仍存在，并在卡内显示空态。
- [ ] 任务 loading/error/empty/list 全部发生在任务卡 body；error 时 Diary 仍可见且可操作。
- [ ] 当前日记同时有 `Current note` 文字、success 细边与极浅 success 背景；静止条目无浮层阴影。
- [ ] 任务的立即运行、暂停/恢复、编辑、历史、删除/撤销、打开执行会话及反馈均保留。
- [ ] `<=56rem` 顺序为月历 → 日期上下文 → 任务卡 → 日记卡；`<=40rem` 无横向滚动。
- [ ] 自动化测试按 section/heading/父级关系断言两卡分离，并验证任务错误不移除 Diary；不能只检查两个标题文本出现。

## 11. Stage 4 自检

| 检查项 | 结果 |
| --- | --- |
| 已读取 Stage 1/2/3 与目标截图 | 通过 |
| 已读取 PDF 颜色、字体、分区、阴影规则 | 通过 |
| 已核对现有 CalendarPopup CSS/类名/token | 通过 |
| 右栏无共享可见大外框 | 通过 |
| Scheduled tasks / Diary 为独立 sibling cards | 通过 |
| 两卡各有 header/count/divider/body | 通过 |
| 任务局部状态与日记持续可用 | 通过 |
| 窄屏顺序和单一滚动路径明确 | 通过 |
| 保留现有任务动作与历史 | 通过 |
| 原型包含 Tailwind 2.2.19、Font Awesome 6.0.0、Google Fonts | 通过 |
| 未新增业务状态、弹窗或入口 | 通过 |
