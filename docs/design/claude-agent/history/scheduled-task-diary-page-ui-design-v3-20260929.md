<!-- [Input] ../../prd/claude-agent/scheduled-task-diary-page-prd.md、页面结构骨架、用户目标截图，以及现有 CalendarPopup/Modal 生产类名。 -->
<!-- [Output] CalendarPopup 悬浮纸张改版的实现级视觉规范、生产类名映射和完整 HTML/Tailwind/CSS 静态原型。 -->
<!-- [Pos] docs/design/claude-agent 下的现行 UI 实现规范；定义生产视觉参数、类名迁移和可审阅原型。 -->
<!-- [Sync] 2026-09-29: 定稿透明 Modal、独立关闭控件和月历/任务/日记三张同级悬浮纸面。 -->

# CalendarPopup 悬浮纸张 UI 设计稿

## 文档导航

- [现行 PRD](../../../prd/claude-agent/scheduled-task-diary-page-prd.md)
- [页面结构骨架](../../../prd/claude-agent/scheduled-task-diary-page-structure-sketch.md)
- [定时任务系统交互与执行设计](../scheduled-task-loop-interaction-design.md)
- [上一版分卡 UI 设计（历史）](./scheduled-task-diary-page-ui-design-v2-20260929.md)

## 1. 最终视觉结论

本方案采用**温暖纸张感的超感官极简主义**。视觉重点是三张有明确高度的 Paper Cream 纸面直接浮在半透明遮罩上：左侧月历一张，右侧“所选日期的定时任务”和“所选日期的日记”各一张。Modal 仍保留对话框、焦点约束和滚动职责，但其 surface、header 和 content 在视觉上完全透明，不能形成包住三张纸面的第四张卡。

目标图中的红色矩形仅用于指出范围，不属于产品界面。生产 UI 不增加红框、装饰性描边、共享右栏底板、独立日期摘要、可见 `Calendar` 页面标题或额外统计卡。

### 1.1 一眼可见的验收特征

1. 遮罩上只看到三张大圆角纸面，以及一个独立圆形关闭控件。
2. 三张纸面四周都能看到透明间隙和暖棕柔和高度阴影。
3. 月历卡没有内部横线；任务卡和日记卡各只保留一条卡头/正文分隔线。
4. 右栏没有共享白底，任务卡和日记卡的圆角、底边与阴影分别完整可见。
5. 业务标题直接带日期，例如“今天的定时任务”“今天的日记”；不再单列“今天”摘要。
6. 任务配置和执行结果是连续文本组，不使用“计划框、时区框、结果框”套娃。
7. 当前日记由绿色细边、极浅绿色底和“当前笔记”文字共同标识。

## 2. 美学样式表

| 维度 | 最终规范 | 设计目的 | 禁止做法 |
| --- | --- | --- | --- |
| 视觉方向 | Warm Paper / Ultra-Sensory Minimalism | 延续 Ink & Memory 的纸张、手写和安静书写气质 | 玻璃拟态、冷灰企业后台、强渐变 |
| 遮罩 | 暖灰棕半透明，允许轻微背景模糊 | 压低应用背景，使纸张高度清楚 | 白色大底板或纯黑硬遮罩 |
| Modal surface | 完全透明，无 border/radius/shadow | 只保留对话框和布局职责 | 大白框套住全部内容 |
| 主纸面 | Paper Cream，24px 圆角，暖棕双层高度阴影 | 三张卡形成一致的实体纸张 | 粗边框、黑色硬阴影、整卡 hover 上浮 |
| 卡头 | 手写感标题 + 本卡数量；任务/日记卡头下各一条淡分隔线 | 用文字和留白建立层级 | 独立日期摘要、卡头再套卡 |
| 正文 | Noto Sans SC / 生产正文字体，扁平分组 | 保证高密度任务信息仍可读 | 每个字段一个事实框 |
| 选中日期 | 暖棕外轮廓；今天可叠加琥珀内圈 | 同时识别“选中”和“今天” | 只用底色区分 |
| 当前日记 | 绿色 2px 细边、浅绿纸底、文字 badge | 明确当前对象且具备非颜色线索 | 左侧粗色条加多重阴影 |
| 动效 | 不新增纸面入场或悬浮动画；沿用既有控件 hover/focus 反馈 | 保持页面安静并避免无业务价值的运动 | 卡片持续漂浮、弹跳或 hover 缩放 |
| 字体 | 标题优先生产 `Excalifont/Xiaolai`；原型以 Noto Serif SC 模拟；正文 Noto Sans SC | 保留手写标题与清晰正文的对比 | 给正文使用大面积手写字体 |

## 3. 设计 Token 与精确参数

所有生产颜色优先映射既有 `frontend/app/_dream/styles/tokens.css`。以下原型值用于审阅视觉关系，不授权在生产代码中新建另一套主题系统。

```css
:root {
  /* 生产映射：--color-bg-overlay */
  --calendar-overlay: rgba(52, 43, 34, 0.54);

  /* 生产映射：--color-bg-paper */
  --calendar-paper: #fffaf2;
  --calendar-paper-soft: #fcf7ed;
  --calendar-paper-selected: #f2f6ea;

  /* 生产映射：--color-text-primary/body/secondary/muted */
  --calendar-ink: #3f3429;
  --calendar-ink-soft: #746657;
  --calendar-ink-muted: #978775;

  /* 生产映射：--color-border-paper / --color-border-focus */
  --calendar-paper-edge: rgba(169, 142, 111, 0.28);
  --calendar-rule: rgba(155, 126, 94, 0.32);
  --calendar-focus: #6a523d;

  /* 生产映射：--color-state-success / --color-state-warning */
  --calendar-green: #7e9468;
  --calendar-green-soft: rgba(126, 148, 104, 0.09);
  --calendar-amber: #c58b4d;

  /* 高度阴影由既有 shadow token 组合，不增加新业务颜色 */
  --calendar-paper-shadow:
    0 18px 36px rgba(91, 69, 44, 0.18),
    0 8px 18px rgba(91, 69, 44, 0.11);
  --calendar-control-shadow: 0 8px 22px rgba(91, 69, 44, 0.16);

  --calendar-radius-paper: 24px;
  --calendar-radius-item: 14px;
  --calendar-gap-column: 28px;
  --calendar-gap-stack: 22px;
  --calendar-card-padding-x: 28px;
  --calendar-card-padding-y: 24px;
  --calendar-control-size: 44px;
}
```

### 3.1 生产 token 映射规则

- 纸色：`var(--color-bg-paper)`。
- 纸边：`color-mix(in srgb, var(--color-border-paper) 42%, transparent)`，边界仅用于补足浅色背景上的轮廓，不能成为主要高度来源。
- 卡头分隔线：`color-mix(in srgb, var(--color-border-paper) 52%, transparent)`。
- 高度阴影：近层使用 `var(--color-shadow-soft)`，远层使用 `var(--color-shadow-medium)`；宽屏组合为 `0 8px 18px var(--color-shadow-soft), 0 18px 36px var(--color-shadow-medium)`，在明确悬浮高度的同时完整容纳于主滚动边界；深色主题继续使用现有 token 自动变换。
- 当前日记：`var(--color-state-success)` 与 `color-mix(in srgb, var(--color-state-success) 9%, var(--color-bg-paper))`。
- 选中日期：`var(--color-border-focus)`；今天内圈：`var(--color-state-warning)`。
- 所有正文和控件颜色继续使用现有 text/action/state token，不硬编码业务色。

## 4. 页面尺寸与布局网格

### 4.1 宽屏（视口宽度 > 1024px）

| 对象 | 尺寸/规则 |
| --- | --- |
| 遮罩 | `position: fixed; inset: 0; padding: 32px; overflow: auto` |
| 透明 dialog | `width: min(1180px, calc(100vw - 64px)); height: min(800px, calc(100dvh - 64px))` |
| 主布局/滚动 | 两列 `minmax(440px, 1.05fr) minmax(400px, .95fr)`；月历固定，右侧 `.calendar-popup__workspace-scroll` 在可用高度内独立纵向滚动 |
| 月历纸面 | 占满 dialog 可用高度，内边距 30px 32px；不受右侧内容拉伸；宽屏短视口时仅月历内部滚动以保持最后一周可达 |
| 右侧卡栈 | 完全透明，`display: grid; align-content: start; gap: 22px` |
| 任务/日记纸面 | 自然高度，卡头横向内边距 28px，正文 24px 28px 28px |
| 关闭按钮 | dialog 右上角外侧安全区，44×44px；不得覆盖卡头 |
| 阴影安全区 | 右侧滚动卡栈左右至少 36px、底部至少 56px；完整容纳宽屏 `0 18px 36px` 远层阴影 |

月历卡与任务卡顶部基线一致。日记卡紧随任务卡自然向下，不为了与月历等高而拉伸。任务编辑或历史展开只增加右侧卡栈的滚动内容高度，旁边的月历保持原位。

### 4.2 中窄屏（视口宽度 ≤ 1024px）

- 改为单列，DOM 顺序固定为月历 → 定时任务 → 日记。
- 单列时取消右侧独立滚动，改由 `.calendar-popup` 统一滚动，避免嵌套滚动。
- dialog 宽度 `min(720px, calc(100vw - 32px))`，三张纸面间距 22px。
- 三张卡继续保持独立 20px 圆角与阴影。
- 为避免主滚动边界裁切纸面高度，阴影在此断点收敛为 `0 6px 14px var(--color-shadow-soft), 0 10px 20px var(--color-shadow-medium)`；内容左右至少保留 20px，最后一张纸面通过 22px 卡间距和 10px 末尾占位形成 32px 底部安全区。
- 关闭按钮固定在 dialog 内容安全区右上角；第一张卡顶部为其预留至少 52px，不遮挡月份导航。
- 任务标题、状态和操作可以换行；任何字段不得触发横向滚动。

### 4.3 手机（视口宽度 ≤ 640px）

- 遮罩内边距 10px；dialog 宽度 `100%`。
- 纸面圆角 18px，卡内横向内边距 16px，卡间距 14px。
- 阴影收敛为 `0 4px 10px var(--color-shadow-soft), 0 8px 16px var(--color-shadow-medium)`；主滚动边界左右至少保留 16px，最后一张纸面通过 14px 卡间距和 10px 末尾占位形成 24px 底部安全区。
- 月历日期格最小触控区域 42×42px；操作按钮最小高度 42px。
- 月历标题可缩至 1.18rem，星期文字 0.72rem。
- 最后一张日记卡之后保留 24px 透明安全区，确保阴影完整滚入视口。

## 5. 组件结构与视觉职责

| 模块 | 生产视觉职责 | 精确规则 |
| --- | --- | --- |
| A1 `.modal-backdrop` | 遮罩 | 暖灰半透明；背景不可交互；不显示纸色 |
| A2 `.calendar-popup-modal` | 透明 dialog 壳 | `background: transparent; border: 0; border-radius: 0; box-shadow: none; padding` 只保留阴影安全区 |
| 隐藏标题 `.modal-title--default` | dialog 可访问名称 | 视觉隐藏但可被屏幕阅读器读取；不得 `display:none` |
| D1 `.modal-close--default` | 独立关闭控件 | 44px 圆形纸色控件，有轻阴影和焦点环；不依附可见顶栏 |
| E1 响应式滚动边界 | 宽屏为 `.calendar-popup__workspace-scroll`，单列为 `.calendar-popup` | 宽屏右侧滚动且月历固定；单列统一滚动；两种状态都不撑开 dialog 或背景页面 |
| B1 `.calendar-popup__calendar` | 月历悬浮纸面 | Paper Cream、24px 圆角、双层暖棕阴影；常规宽屏固定，短视口内部可滚动；无内部横线 |
| E2 `.calendar-popup__workspace` / `__workspace-scroll` | 右侧透明卡栈 | 无 background/border/radius/shadow；只负责 gap 与内容顺序 |
| C1 `.calendar-popup__task-section` | 定时任务悬浮纸面 | 与月历相同纸色、圆角和阴影；自然高度 |
| D2 `.calendar-popup__diary-section` | 日记悬浮纸面 | 与前两张纸面同级；自然高度 |
| C2/D3 `.calendar-popup__section-heading` | 日期化业务卡头 | 单行或自然换行标题 + 本卡数量；底部唯一分隔线 |
| C5 `.calendar-popup__task` | 扁平任务信息组 | 无完整卡框、无阴影；任务之间用间距或单条低对比分隔线 |
| D6 `.calendar-popup__diary` | 日记行 | 普通条目为轻表面；当前条目绿色细边和浅绿底；无悬浮阴影 |

## 6. 关键组件视觉规范

### 6.1 透明 Modal 与关闭控件

1. `.calendar-popup-modal` 必须覆盖共享 `.modal-surface` 的纸色、边框、圆角和阴影。
2. `.modal-header--default` 对 CalendarPopup 只提供关闭按钮定位，不占据可见标题栏高度；其余页面不受影响。
3. `.modal-title--default` 在 CalendarPopup 作用域内使用标准 visually-hidden 写法：1px 尺寸、负 margin、clip、`white-space: nowrap`。保留 `aria-labelledby`。
4. 关闭按钮是单独的圆形纸面控件，允许轻阴影，但视觉面积远小于主卡，不能被理解为第四张内容卡。
5. 按钮 hover 只改变底色和文字色，不位移；focus-visible 使用 2px focus ring + 3px offset。

### 6.2 月历纸面

- 月份导航上方不显示 `Calendar`。
- 月份标题居中、20–24px 手写/衬线字体，字重 600。
- 上一月/下一月按钮是 44×44px 无边框按钮，hover 使用浅暖灰背景。
- 星期行与日期网格通过 20px 上间距组织，不加横线。
- 普通日期没有常驻边框；有内容日期可用很浅的小纸片底和柔和 2px 小阴影。
- 选中日期为 2px 暖棕外轮廓；今天使用内缩 4px 的琥珀内圈；同一天同时具备二者时两圈都保留。
- 有日记/内容标记继续使用底部蓝色圆点，尺寸 5px，不新增图例。

### 6.3 日期化任务卡头

- 标题格式：今天使用“今天的定时任务”；其他日期使用本地化的“9月30日的定时任务”等价表达。
- 数量属于任务卡自身，使用次级文字“2 项”；有待处理项时在同一元信息组显示“1 项需处理”。
- 加载和失败时只把数量替换为“载入中”或“数量未知”，不得影响日记卡数量。
- 卡头最小高度 78px；标题与元信息自然换行；底部只画 1px 低对比分隔线。

### 6.4 扁平任务信息组

一条任务按下列顺序排版，不创建逐字段小卡：

```text
任务标题                                      [Active] [更多]
每天 09:00 · Asia/Shanghai
下次：9月30日 09:00 · 最近结果：已完成 08:59
[立即运行] [暂停] [历史]
```

- 单条任务本身背景透明，边框和阴影均为 `none`。
- 相邻任务之间以 `padding-block: 20px` 和一条 `border-top` 区分；第一条无顶线。
- 标题 16px/600；配置与执行行 13px，次级颜色；行间距 7px。
- 状态 badge 可保留浅色圆角，但不能与任务条目形成同高度卡片。
- 主操作使用现有按钮层级；更多菜单、输入框、错误提示等有交互含义的边界继续保留。
- 编辑和历史展开区可以使用 4%–7% 的浅纸色差与 12px 圆角，只承担局部分组，不加完整外框和重阴影。

### 6.5 日期化日记卡与当前条目

- 卡头格式与任务卡一致：“今天的日记” + “1 篇”。
- 日记行采用两行信息：第一行时间、当前笔记 badge 和删除；第二行标题。
- 普通条目使用极浅纸底或 1px 低对比边界，无高度阴影。
- 当前日记使用 2px `state-success` 边界、9% 浅绿纸底和文字 badge；不使用左侧粗条。
- 删除按钮保持独立，hover 时才显示浅红背景；点击日记正文与删除仍是两个不同操作。

## 7. 局部状态呈现

| 状态 | 任务纸面 | 日记纸面 |
| --- | --- | --- |
| Loading | 卡头和纸面保留，正文一行加载文案/进度语义 | 正常可用 |
| Error | 正文显示简短原因与“重试”；错误边界只包住反馈行 | 正常可打开、删除 |
| Empty | 纸面保留，正文显示“这一天没有定时任务” | 独立显示“这一天还没有日记” |
| List | 扁平任务信息组按间距排列 | 日记行按间距排列 |
| 操作失败 | 对应任务附近显示可行动错误 | 不改变日记卡 |
| 日记删除失败 | 不改变任务卡 | 对应日记附近显示既有反馈 |

状态切换不能改变三张纸面的同级关系，也不能恢复共享右栏白底。

## 8. 动效约束与 reduced motion

### 8.1 默认行为

三张纸面打开时直接呈现，不新增入场、错峰、持续浮动或整体 hover 位移。按钮、日期格和菜单继续使用现有组件的背景色、边界色和焦点环反馈，不为本轮视觉纠错增加新的时间常量。

### 8.2 减少动态效果

```css
@media (prefers-reduced-motion: reduce) {
  .calendar-popup *,
  .calendar-popup *::before,
  .calendar-popup *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

关闭、键盘导航、焦点恢复和状态反馈不依赖动画完成。

## 9. 完整可审阅 HTML / Tailwind / CSS 原型

以下为静态视觉原型。它复用生产类名表达迁移目标，并使用 Tailwind 2.2.19 做布局辅助；按钮不连接新业务逻辑，所有文案对应现有月历、任务和日记能力。

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>CalendarPopup floating paper review</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;500;600;700&family=Noto+Sans+SC:wght@300;400;500;700&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="https://lf6-cdn-tos.bytecdntp.com/cdn/expire-100-M/font-awesome/6.0.0/css/all.min.css" />
  <link rel="stylesheet" href="https://lf3-cdn-tos.bytecdntp.com/cdn/expire-1-M/tailwindcss/2.2.19/tailwind.min.css" />
  <style>
    :root {
      --color-bg-overlay: rgba(52, 43, 34, .54);
      --color-bg-paper: #fffaf2;
      --color-bg-surface-solid: #fffcf7;
      --color-bg-hover: #f3ece1;
      --color-text-primary: #3f3429;
      --color-text-body: #524538;
      --color-text-secondary: #746657;
      --color-text-muted: #978775;
      --color-text-on-action: #fffaf2;
      --color-border-paper: #d8c7b3;
      --color-border-focus: #6a523d;
      --color-action-primary: #5f4a36;
      --color-action-link: #4d78ad;
      --color-state-success: #7e9468;
      --color-state-warning: #c58b4d;
      --color-state-danger: #ae5d54;
      --color-shadow-soft: rgba(91, 69, 44, .10);
      --color-shadow-medium: rgba(91, 69, 44, .18);
      --paper-shadow: 0 8px 18px var(--color-shadow-soft), 0 18px 36px var(--color-shadow-medium);
      --paper-radius: 24px;
    }

    * { box-sizing: border-box; }
    html, body { min-height: 100%; }
    body {
      margin: 0;
      min-width: 320px;
      font-family: 'Noto Sans SC', system-ui, sans-serif;
      color: var(--color-text-body);
      background:
        linear-gradient(rgba(255,255,255,.2), rgba(255,255,255,.2)),
        repeating-linear-gradient(0deg, #efe5d5 0 1px, #f8f1e6 1px 42px);
    }
    button { font: inherit; }
    button:focus-visible { outline: 2px solid var(--color-border-focus); outline-offset: 3px; }
    .sr-only {
      position: absolute !important;
      width: 1px !important;
      height: 1px !important;
      padding: 0 !important;
      margin: -1px !important;
      overflow: hidden !important;
      clip: rect(0, 0, 0, 0) !important;
      white-space: nowrap !important;
      border: 0 !important;
    }

    /* A1：暖灰遮罩。 */
    .modal-backdrop {
      position: fixed;
      inset: 0;
      z-index: 60;
      display: grid;
      place-items: center;
      overflow: auto;
      padding: 32px;
      background: var(--color-bg-overlay);
      backdrop-filter: blur(2px);
    }

    /* A2：透明 Modal 交互壳，不是第四张卡。 */
    .modal-surface--default.calendar-popup-modal {
      position: relative;
      display: flex;
      flex-direction: column;
      width: min(1180px, calc(100vw - 64px));
      height: min(800px, calc(100dvh - 64px));
      max-height: calc(100dvh - 64px);
      margin: 0;
      padding: 0;
      border: 0;
      border-radius: 0;
      background: transparent;
      box-shadow: none;
      overflow: visible;
    }
    .calendar-popup-modal > .modal-header--default {
      position: absolute;
      top: 24px;
      right: -22px;
      z-index: 10;
      margin: 0;
    }
    .calendar-popup-modal .modal-title--default { /* 同 .sr-only */
      position: absolute;
      width: 1px;
      height: 1px;
      padding: 0;
      margin: -1px;
      overflow: hidden;
      clip: rect(0, 0, 0, 0);
      white-space: nowrap;
      border: 0;
    }
    .calendar-popup-modal .modal-close--default {
      display: grid;
      width: 44px;
      height: 44px;
      place-items: center;
      padding: 0;
      border: 1px solid color-mix(in srgb, var(--color-border-paper) 52%, transparent);
      border-radius: 999px;
      background: var(--color-bg-paper);
      box-shadow: 0 8px 22px var(--color-shadow-medium);
      color: var(--color-text-secondary);
      cursor: pointer;
    }
    .calendar-popup-modal .modal-close--default:hover {
      background: var(--color-bg-hover);
      color: var(--color-text-primary);
    }
    .calendar-popup-modal > .modal-content--default {
      box-sizing: border-box;
      flex: 1 1 auto;
      min-height: 0;
      width: 100%;
      margin: 0;
      padding: 0;
      overflow: hidden;
    }

    /* 三张纸面的布局；外层均透明。 */
    .calendar-popup {
      display: grid;
      grid-template-columns: minmax(440px, 1.05fr) minmax(400px, .95fr);
      gap: 28px;
      align-items: start;
      min-width: 0;
      min-height: 0;
      height: 100%;
      padding: 36px 36px 56px;
      overflow: hidden;
      overscroll-behavior: contain;
    }
    .calendar-popup__workspace,
    .calendar-popup__workspace-scroll {
      min-width: 0;
      border: 0;
      border-radius: 0;
      background: transparent;
      box-shadow: none;
    }
    .calendar-popup__workspace { height: 100%; }
    .calendar-popup__workspace-scroll {
      display: grid;
      box-sizing: border-box;
      align-content: start;
      gap: 22px;
      width: calc(100% + 72px);
      height: calc(100% + 92px);
      margin: -36px -36px -56px;
      padding: 36px 36px 56px;
      overflow: auto;
      overscroll-behavior: contain;
      scrollbar-gutter: stable;
    }
    .calendar-popup__date-summary { display: none; }

    .calendar-popup__calendar,
    .calendar-popup__section {
      min-width: 0;
      border: 1px solid color-mix(in srgb, var(--color-border-paper) 42%, transparent);
      border-radius: var(--paper-radius);
      background: var(--color-bg-paper);
      box-shadow: var(--paper-shadow);
    }
    .calendar-popup__calendar {
      min-height: 0;
      height: 100%;
      padding: 30px 32px 34px;
      overflow: auto;
      overscroll-behavior: contain;
    }

    .calendar-popup__month-heading,
    .calendar-popup__section-heading,
    .calendar-popup__task-heading {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
    }
    .calendar-popup__month-heading h3,
    .calendar-popup__section-heading h3,
    .calendar-popup__task-heading h4,
    .calendar-popup__diary-open strong {
      margin: 0;
      font-family: 'Noto Serif SC', Georgia, serif;
      color: var(--color-text-primary);
    }
    .calendar-popup__month-heading h3 { font-size: 1.42rem; font-weight: 600; }
    .calendar-popup__month-heading button,
    .calendar-popup__icon-button {
      display: grid;
      width: 44px;
      height: 44px;
      place-items: center;
      border: 0;
      border-radius: 12px;
      background: transparent;
      color: var(--color-text-secondary);
      cursor: pointer;
    }
    .calendar-popup__month-heading button:hover,
    .calendar-popup__icon-button:hover { background: var(--color-bg-hover); color: var(--color-text-primary); }

    .calendar-popup__weekdays,
    .calendar-popup__grid {
      display: grid;
      grid-template-columns: repeat(7, minmax(0, 1fr));
      gap: 8px;
    }
    .calendar-popup__weekdays {
      margin: 30px 0 10px;
      color: var(--color-text-muted);
      font-size: .76rem;
      font-weight: 700;
      text-align: center;
    }
    .calendar-popup__day,
    .calendar-popup__day-placeholder { min-width: 0; min-height: 56px; aspect-ratio: 1; }
    .calendar-popup__day {
      position: relative;
      display: grid;
      place-items: center;
      border: 2px solid transparent;
      border-radius: 14px;
      background: transparent;
      color: var(--color-text-body);
      cursor: pointer;
    }
    .calendar-popup__day:hover { background: var(--color-bg-hover); }
    .calendar-popup__day--has-entry {
      background: var(--color-bg-surface-solid);
      box-shadow: 0 3px 9px var(--color-shadow-soft);
    }
    .calendar-popup__day--selected { border-color: var(--color-border-focus); font-weight: 700; }
    .calendar-popup__day--today::after {
      content: '';
      position: absolute;
      inset: 6px;
      border: 2px solid var(--color-state-warning);
      border-radius: 11px;
      pointer-events: none;
    }
    .calendar-popup__day i {
      position: absolute;
      bottom: 6px;
      width: 5px;
      height: 5px;
      border-radius: 999px;
      background: var(--color-action-link);
    }

    .calendar-popup__section-heading {
      min-height: 78px;
      padding: 21px 28px 18px;
      border-bottom: 1px solid color-mix(in srgb, var(--color-border-paper) 52%, transparent);
    }
    .calendar-popup__section-heading h3 { font-size: 1.14rem; font-weight: 600; }
    .calendar-popup__card-header-meta { display: flex; align-items: center; gap: 9px; color: var(--color-text-secondary); }
    .calendar-popup__card-count { font-size: .78rem; white-space: nowrap; }
    .calendar-popup__count-alert {
      border: 0;
      background: transparent;
      color: var(--color-state-danger);
      font-size: .78rem;
      font-weight: 600;
      cursor: pointer;
    }
    .calendar-popup__card-body { padding: 5px 28px 26px; }

    /* C5：任务是扁平信息组，不再是内嵌卡。 */
    .calendar-popup__task-list { display: grid; }
    .calendar-popup__task {
      min-width: 0;
      padding: 20px 0;
      border: 0;
      border-radius: 0;
      background: transparent;
      box-shadow: none;
    }
    .calendar-popup__task + .calendar-popup__task {
      border-top: 1px solid color-mix(in srgb, var(--color-border-paper) 42%, transparent);
    }
    .calendar-popup__task-heading h4 { overflow-wrap: anywhere; font-size: 1rem; font-weight: 600; }
    .calendar-popup__task-title-row { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; min-width: 0; }
    .calendar-popup__status {
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      padding: 2px 8px;
      border-radius: 999px;
      background: var(--color-bg-hover);
      color: var(--color-text-secondary);
      font-size: .71rem;
      font-weight: 700;
    }
    .calendar-popup__status--succeeded { color: var(--color-state-success); }
    .calendar-popup__task-facts,
    .calendar-popup__recent {
      display: flex;
      flex-wrap: wrap;
      align-items: baseline;
      gap: 5px 8px;
      margin: 8px 0 0;
      padding: 0;
      border: 0;
      background: transparent;
      color: var(--color-text-secondary);
      font-size: .8rem;
    }
    .calendar-popup__task-facts dt { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0,0,0,0); }
    .calendar-popup__task-facts dd { margin: 0; }
    .calendar-popup__task-facts > div { display: contents; }
    .calendar-popup__task-facts > div + div::before { content: '·'; color: var(--color-text-muted); }
    .calendar-popup__recent > span { color: var(--color-text-muted); }
    .calendar-popup__primary-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }
    .calendar-popup__button {
      min-height: 42px;
      padding: 8px 13px;
      border: 1px solid color-mix(in srgb, var(--color-border-paper) 64%, transparent);
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

    /* D6：普通日记是轻量条目；当前日记使用绿色细边与浅底。 */
    .calendar-popup__diary-list { display: grid; gap: 12px; padding-top: 18px; }
    .calendar-popup__diary {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 14px 16px;
      border: 1px solid color-mix(in srgb, var(--color-border-paper) 52%, transparent);
      border-radius: 14px;
      background: color-mix(in srgb, var(--color-bg-surface-solid) 72%, transparent);
      box-shadow: none;
    }
    .calendar-popup__diary--current {
      border: 2px solid var(--color-state-success);
      background: color-mix(in srgb, var(--color-state-success) 9%, var(--color-bg-paper));
    }
    .calendar-popup__diary-open {
      display: grid;
      grid-template-columns: auto minmax(0, 1fr);
      grid-template-rows: auto auto;
      flex: 1;
      align-items: center;
      gap: 5px 8px;
      min-width: 0;
      min-height: 42px;
      padding: 0;
      border: 0;
      background: transparent;
      color: var(--color-text-body);
      text-align: left;
      cursor: pointer;
    }
    .calendar-popup__diary-open > span { color: var(--color-text-secondary); font-size: .78rem; }
    .calendar-popup__diary-open em {
      justify-self: start;
      padding: 2px 8px;
      border-radius: 999px;
      background: var(--color-state-success);
      color: var(--color-text-on-action);
      font-size: .7rem;
      font-style: normal;
    }
    .calendar-popup__diary-open strong {
      grid-column: 1 / -1;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-size: .96rem;
      font-weight: 600;
    }
    .calendar-popup__diary-delete {
      min-width: 42px;
      min-height: 42px;
      padding: 7px;
      border: 0;
      border-radius: 9px;
      background: transparent;
      color: var(--color-text-muted);
      cursor: pointer;
    }
    .calendar-popup__diary-delete:hover { background: rgba(174,93,84,.09); color: var(--color-state-danger); }

    @media (max-width: 1024px) {
      .modal-backdrop { padding: 16px; }
      .modal-surface--default.calendar-popup-modal {
        width: min(720px, calc(100vw - 32px));
        height: calc(100dvh - 32px);
        max-height: calc(100dvh - 32px);
        padding: 0;
      }
      .calendar-popup-modal > .modal-header--default { top: 12px; right: 12px; }
      .calendar-popup-modal > .modal-content--default { padding: 0; overflow: hidden; }
      .calendar-popup { grid-template-columns: minmax(0, 1fr); gap: 22px; height: 100%; padding: 68px 20px 0; overflow: auto; }
      .calendar-popup__workspace-scroll::after { content: ''; display: block; height: 10px; }
      .calendar-popup__calendar,
      .calendar-popup__section {
        border-radius: 20px;
        box-shadow: 0 6px 14px var(--color-shadow-soft), 0 10px 20px var(--color-shadow-medium);
      }
      .calendar-popup__calendar { min-height: 0; height: auto; overflow: visible; }
      .calendar-popup__workspace { height: auto; }
      .calendar-popup__workspace-scroll {
        width: auto;
        height: auto;
        margin: 0;
        padding: 0;
        gap: 22px;
        overflow: visible;
        scrollbar-gutter: auto;
      }
    }
    @media (max-width: 640px) {
      .modal-backdrop { padding: 10px; }
      .modal-surface--default.calendar-popup-modal {
        width: 100%;
        height: calc(100dvh - 20px);
        max-height: calc(100dvh - 20px);
        padding: 0;
      }
      .calendar-popup-modal > .modal-content--default { padding: 0; overflow: hidden; }
      .calendar-popup { gap: 14px; height: 100%; padding: 68px 16px 0; overflow: auto; }
      .calendar-popup__workspace-scroll { gap: 14px; }
      .calendar-popup__calendar,
      .calendar-popup__section {
        border-radius: 18px;
        box-shadow: 0 4px 10px var(--color-shadow-soft), 0 8px 16px var(--color-shadow-medium);
      }
      .calendar-popup__calendar { padding: 16px; }
      .calendar-popup__section-heading { padding-inline: 16px; }
      .calendar-popup__card-body { padding-inline: 16px; }
      .calendar-popup__day,
      .calendar-popup__day-placeholder { min-height: 42px; }
      .calendar-popup__month-heading h3 { font-size: 1.18rem; }
      .calendar-popup__weekdays { font-size: .72rem; }
    }
    @media (prefers-reduced-motion: reduce) {
      .calendar-popup *,
      .calendar-popup *::before,
      .calendar-popup *::after {
        animation-duration: .01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: .01ms !important;
        scroll-behavior: auto !important;
      }
    }
  </style>
</head>
<body>
  <div class="modal-backdrop modal-backdrop--default" role="presentation">
    <section class="modal-surface modal-surface--default calendar-popup-modal" role="dialog" aria-modal="true" aria-labelledby="calendar-dialog-title">
      <div class="modal-header modal-header--default">
        <h2 id="calendar-dialog-title" class="modal-title modal-title--default">日历</h2>
        <div class="modal-toolbar modal-toolbar--default">
          <button type="button" class="modal-close modal-close--default" aria-label="关闭日历">
            <i class="fa-solid fa-xmark" aria-hidden="true"></i>
          </button>
        </div>
      </div>

      <div class="modal-content modal-content--default">
        <main class="calendar-popup">
          <!-- B1：月历悬浮纸面 -->
          <section class="calendar-popup__calendar" aria-labelledby="calendar-month-title">
            <header class="calendar-popup__month-heading">
              <button type="button" aria-label="上一个月"><i class="fa-solid fa-chevron-left" aria-hidden="true"></i></button>
              <h3 id="calendar-month-title">2026年9月</h3>
              <button type="button" aria-label="下一个月"><i class="fa-solid fa-chevron-right" aria-hidden="true"></i></button>
            </header>

            <div class="calendar-popup__weekdays" aria-hidden="true">
              <span>周日</span><span>周一</span><span>周二</span><span>周三</span><span>周四</span><span>周五</span><span>周六</span>
            </div>
            <div class="calendar-popup__grid" role="grid" aria-label="2026年9月">
              <span class="calendar-popup__day-placeholder" aria-hidden="true"></span>
              <span class="calendar-popup__day-placeholder" aria-hidden="true"></span>
              <button class="calendar-popup__day calendar-popup__day--has-entry" role="gridcell" aria-label="2026年9月1日"><span>1</span><i aria-hidden="true"></i></button>
              <button class="calendar-popup__day calendar-popup__day--has-entry" role="gridcell" aria-label="2026年9月2日"><span>2</span><i aria-hidden="true"></i></button>
              <button class="calendar-popup__day" role="gridcell" aria-label="2026年9月3日"><span>3</span></button>
              <button class="calendar-popup__day calendar-popup__day--has-entry" role="gridcell" aria-label="2026年9月4日"><span>4</span><i aria-hidden="true"></i></button>
              <button class="calendar-popup__day calendar-popup__day--has-entry" role="gridcell" aria-label="2026年9月5日"><span>5</span><i aria-hidden="true"></i></button>
              <button class="calendar-popup__day calendar-popup__day--has-entry" role="gridcell" aria-label="2026年9月6日"><span>6</span><i aria-hidden="true"></i></button>
              <button class="calendar-popup__day calendar-popup__day--has-entry" role="gridcell" aria-label="2026年9月7日"><span>7</span><i aria-hidden="true"></i></button>
              <button class="calendar-popup__day calendar-popup__day--has-entry" role="gridcell" aria-label="2026年9月8日"><span>8</span><i aria-hidden="true"></i></button>
              <button class="calendar-popup__day calendar-popup__day--selected calendar-popup__day--today calendar-popup__day--has-entry" role="gridcell" aria-label="今天，2026年9月9日" aria-selected="true"><span>9</span><i aria-hidden="true"></i></button>
              <button class="calendar-popup__day" role="gridcell" aria-label="2026年9月10日"><span>10</span></button>
              <button class="calendar-popup__day" role="gridcell" aria-label="2026年9月11日"><span>11</span></button>
              <button class="calendar-popup__day" role="gridcell" aria-label="2026年9月12日"><span>12</span></button>
              <button class="calendar-popup__day" role="gridcell" aria-label="2026年9月13日"><span>13</span></button>
              <button class="calendar-popup__day" role="gridcell" aria-label="2026年9月14日"><span>14</span></button>
              <button class="calendar-popup__day" role="gridcell" aria-label="2026年9月15日"><span>15</span></button>
              <button class="calendar-popup__day" role="gridcell" aria-label="2026年9月16日"><span>16</span></button>
              <button class="calendar-popup__day" role="gridcell" aria-label="2026年9月17日"><span>17</span></button>
              <button class="calendar-popup__day" role="gridcell" aria-label="2026年9月18日"><span>18</span></button>
              <button class="calendar-popup__day" role="gridcell" aria-label="2026年9月19日"><span>19</span></button>
              <button class="calendar-popup__day" role="gridcell" aria-label="2026年9月20日"><span>20</span></button>
              <button class="calendar-popup__day" role="gridcell" aria-label="2026年9月21日"><span>21</span></button>
              <button class="calendar-popup__day" role="gridcell" aria-label="2026年9月22日"><span>22</span></button>
              <button class="calendar-popup__day" role="gridcell" aria-label="2026年9月23日"><span>23</span></button>
              <button class="calendar-popup__day" role="gridcell" aria-label="2026年9月24日"><span>24</span></button>
              <button class="calendar-popup__day" role="gridcell" aria-label="2026年9月25日"><span>25</span></button>
              <button class="calendar-popup__day" role="gridcell" aria-label="2026年9月26日"><span>26</span></button>
              <button class="calendar-popup__day" role="gridcell" aria-label="2026年9月27日"><span>27</span></button>
              <button class="calendar-popup__day" role="gridcell" aria-label="2026年9月28日"><span>28</span></button>
              <button class="calendar-popup__day" role="gridcell" aria-label="2026年9月29日"><span>29</span></button>
              <button class="calendar-popup__day" role="gridcell" aria-label="2026年9月30日"><span>30</span></button>
            </div>
          </section>

          <!-- E2：透明右侧卡栈，不能添加共享 surface。 -->
          <div class="calendar-popup__workspace">
            <div class="calendar-popup__workspace-scroll">
              <!-- C1：定时任务悬浮纸面 -->
              <section class="calendar-popup__section calendar-popup__task-section" aria-labelledby="scheduled-tasks-title">
                <header class="calendar-popup__section-heading calendar-popup__card-header">
                  <h3 id="scheduled-tasks-title">今天的定时任务</h3>
                  <div class="calendar-popup__card-header-meta" aria-live="polite">
                    <span class="calendar-popup__card-count">2 项</span>
                    <button class="calendar-popup__count-alert" type="button">1 项需处理</button>
                  </div>
                </header>
                <div class="calendar-popup__card-body">
                  <div class="calendar-popup__task-list">
                    <article class="calendar-popup__task calendar-popup__task--succeeded" tabindex="-1">
                      <div class="calendar-popup__task-heading">
                        <div class="calendar-popup__task-title-row">
                          <h4>整理今天的写作回顾</h4>
                          <span class="calendar-popup__status calendar-popup__status--succeeded">Active</span>
                        </div>
                        <button class="calendar-popup__icon-button" type="button" aria-label="更多操作"><i class="fa-solid fa-ellipsis" aria-hidden="true"></i></button>
                      </div>
                      <dl class="calendar-popup__task-facts">
                        <div><dt>计划</dt><dd>每天 21:30</dd></div>
                        <div><dt>时区</dt><dd>Asia/Shanghai</dd></div>
                        <div><dt>下次执行</dt><dd>今天 21:30</dd></div>
                      </dl>
                      <div class="calendar-popup__recent" aria-live="polite">
                        <span>最近结果</span><strong>已完成 · 今天 09:12</strong>
                      </div>
                      <div class="calendar-popup__primary-actions">
                        <button class="calendar-popup__button calendar-popup__button--primary" type="button">立即运行</button>
                        <button class="calendar-popup__button calendar-popup__button--secondary" type="button">暂停</button>
                        <button class="calendar-popup__button calendar-popup__button--quiet" type="button">历史</button>
                      </div>
                    </article>

                    <article class="calendar-popup__task calendar-popup__task--failed" tabindex="-1">
                      <div class="calendar-popup__task-heading">
                        <div class="calendar-popup__task-title-row">
                          <h4>生成每日灵感摘要</h4>
                          <span class="calendar-popup__status">Paused</span>
                        </div>
                        <button class="calendar-popup__icon-button" type="button" aria-label="更多操作"><i class="fa-solid fa-ellipsis" aria-hidden="true"></i></button>
                      </div>
                      <dl class="calendar-popup__task-facts">
                        <div><dt>计划</dt><dd>每天 08:00</dd></div>
                        <div><dt>时区</dt><dd>Asia/Shanghai</dd></div>
                      </dl>
                      <div class="calendar-popup__recent" aria-live="polite">
                        <span>最近结果</span><strong>需要处理 · 会话未能启动</strong>
                      </div>
                      <div class="calendar-popup__primary-actions">
                        <button class="calendar-popup__button calendar-popup__button--secondary" type="button">恢复</button>
                        <button class="calendar-popup__button calendar-popup__button--quiet" type="button">查看历史</button>
                      </div>
                    </article>
                  </div>
                </div>
              </section>

              <!-- D2：日记悬浮纸面 -->
              <section class="calendar-popup__section calendar-popup__diary-section" aria-labelledby="diary-title">
                <header class="calendar-popup__section-heading calendar-popup__card-header">
                  <h3 id="diary-title">今天的日记</h3>
                  <span class="calendar-popup__card-count" aria-live="polite">2 篇</span>
                </header>
                <div class="calendar-popup__card-body">
                  <div class="calendar-popup__diary-list">
                    <article class="calendar-popup__diary calendar-popup__diary--current">
                      <button type="button" class="calendar-popup__diary-open" aria-label="打开日记：Untitled">
                        <span>12:00</span><em>当前笔记</em><strong>Untitled</strong>
                      </button>
                      <button type="button" class="calendar-popup__diary-delete" aria-label="删除日记：Untitled">删除</button>
                    </article>
                    <article class="calendar-popup__diary">
                      <button type="button" class="calendar-popup__diary-open" aria-label="打开日记：晨间记录">
                        <span>09:40</span><strong>晨间记录</strong>
                      </button>
                      <button type="button" class="calendar-popup__diary-delete" aria-label="删除日记：晨间记录">删除</button>
                    </article>
                  </div>
                </div>
              </section>
            </div>
          </div>
        </main>
      </div>
    </section>
  </div>
</body>
</html>
```

## 10. 现有生产类名迁移映射

本轮应修改既有类的视觉职责，不创建平行的 Calendar V2 组件。

| 现有生产类名 | 当前问题 | 目标职责/样式 |
| --- | --- | --- |
| `.modal-backdrop:has(.calendar-popup-modal)` | 仅通用遮罩 | 保留遮罩与背景隔离；为阴影提供安全内边距 |
| `.modal-surface--default.calendar-popup-modal` | 仍绘制大纸底和大圆角 | 改为透明、无 border/radius/shadow；只控制最大尺寸和定位 |
| `.calendar-popup-modal > .modal-header--default` | 形成可见顶栏 | 改为绝对/安全区定位层，不占标题栏高度 |
| `.calendar-popup-modal .modal-title--default` | 可见 `Calendar` 标题重复 | 视觉隐藏，继续为 `aria-labelledby` 提供名称 |
| `.calendar-popup-modal .modal-close--default` | 依赖顶栏定位 | 成为独立 44px 圆形关闭控件，轻阴影，键盘语义不变 |
| `.calendar-popup-modal > .modal-content--default` | 可能裁切卡片阴影 | 固定可用高度并隐藏自身溢出，把滚动职责交给响应式业务布局 |
| `.calendar-popup` | 两列线框容器 | 宽屏固定布局且不滚动；单列时成为统一滚动边界 |
| `.calendar-popup__calendar` | 边框较强、阴影偏弱 | Paper Cream、24px 圆角、双层暖棕高度阴影 |
| `.calendar-popup__workspace` | 可能仍像右侧面板 | 完全透明，无边框/背景/阴影 |
| `.calendar-popup__date-summary` | 重复日期摘要 | 移除可见呈现；日期并入两张业务卡标题 |
| `.calendar-popup__workspace-scroll` | 右栏内部滚动且可能裁影 | 宽屏独立滚动并保留阴影安全区，使月历固定；单列时恢复为透明普通卡栈 |
| `.calendar-popup__section` | 独立卡但缺少悬浮高度 | 与月历相同纸色、24px 圆角和高度阴影 |
| `.calendar-popup__section-heading` | 通用标题，日期上下文缺失 | 显示日期化标题和本卡数量；只保留底部一条淡线 |
| `.calendar-popup__card-count` | 圆形数字徽章偏统计面板 | 改为“2 项/2 篇”次级文字；不再绘制独立圆形底 |
| `.calendar-popup__task` | 每条任务有完整边框、底色和状态左边框 | 改为透明扁平信息组；相邻条目仅单线分隔 |
| `.calendar-popup__task-facts > div` | 每个事实形成小框 | `display: contents` 或连续文字行；移除背景和 padding |
| `.calendar-popup__recent` | 结果形成另一块事实框 | 并入次级文本组；保留 live region |
| `.calendar-popup__edit-panel`, `.calendar-popup__history` | 卡中卡线框较重 | 仅浅色分组面；保留输入、错误等有意义边界，不加重阴影 |
| `.calendar-popup__diary` | 普通条目边框可保留但不能悬浮 | 轻底/细边，无阴影 |
| `.calendar-popup__diary--current` | 左侧粗色条偏线框 | 2px 绿色完整边界 + 极浅绿色底 + 文字 badge |

### 10.1 对应 JSX 结构调整边界

- `Modal` 仍由 `CalendarPopup` 使用，不复制 portal、focus trap 或 Escape 逻辑。
- `title={t('calendar.title')}` 继续传入；只在 CalendarPopup 的 CSS 作用域内将标题视觉隐藏。
- `.calendar-popup__date-summary` 的可见标题移除后，任务和日记 heading 分别组合 `selectedDateLabel` 与现有业务标题。不得增加一个新的共享日期容器。
- `.calendar-popup__task-section` 与 `.calendar-popup__diary-section` 继续是 `.calendar-popup__workspace-scroll` 的直接子级，父级保持透明。
- `ScheduledTaskCard` 的数据、操作、状态机、菜单、编辑和历史不变；只把 facts/recent/展开区从多层线框改为排版分组。
- 日记打开与删除仍是独立按钮，不能把整个 `<article>` 改成嵌套交互控件。

## 11. 可访问性与语义验收

1. dialog 保持 `role="dialog"`、`aria-modal="true"`、隐藏标题和稳定 `aria-labelledby`。
2. 隐藏标题不能使用 `display: none` 或 `visibility: hidden`。
3. 关闭按钮、上月、下月、更多、日记打开和删除均有本地化名称，触控目标至少 42px。
4. DOM 顺序为月历 → 定时任务 → 日记，与宽窄屏视觉顺序一致。
5. 今天、选中日期、有内容、当前日记、任务状态和失败状态均有文字或 ARIA 表达，不只依赖颜色。
6. 任务卡和日记卡分别拥有 heading/section 关系；局部 live region 不播报整个 dialog。
7. focus-visible 在浅色和深色主题均清晰；卡片阴影不能代替焦点环。
8. Tab 循环、Escape 关闭和关闭后焦点恢复继续由现有 Modal 提供。

## 12. 视觉实现验收清单

### 12.1 必须成立

- `.calendar-popup-modal` computed style：`background-color` 透明、`border-width: 0`、`box-shadow: none`。
- 宽屏 `.calendar-popup` 不滚动，`.calendar-popup__workspace-scroll` 为唯一滚动边界；任务或历史增长时旁边的月历位置不变。
- 宽屏短视口下月历纸面保持原位并允许自身内部滚动，最后一周日期必须可达。
- 单列 `.calendar-popup` 为唯一滚动边界，右侧卡栈取消自身滚动，避免嵌套滚动。
- `.calendar-popup__workspace` 与 `__workspace-scroll` 没有可见 surface。
- `.calendar-popup__calendar`、`.calendar-popup__task-section`、`.calendar-popup__diary-section` 分别具有 Paper Cream 背景、完整圆角和非 `none` 暖棕阴影。
- 宽屏可完整看到三张卡之间的透明遮罩间隙；任务卡和日记卡不共享纸色父级。
- 可见文案不含独立 `Calendar` 标题、独立“今天”摘要或跨卡 `Tasks unknown` 汇总。
- 任务和日记标题包含所选日期上下文。
- 任务 facts/recent 不再呈现为多个带背景的小框。
- 当前日记有绿色完整边界、浅绿底和“当前笔记”文字。
- 1024px 与 640px 两个断点下无横向滚动，三张卡仍是独立纸面。
- reduced-motion 下既有控件动画与过渡近似关闭。

### 12.2 不得出现

- 透明 dialog 外再新增一个可见 wrapper。
- 右栏共享白底或任务/日记共同大卡。
- 用阴影、边框和浅底同时重复包裹同一信息层级。
- 新建任务入口、筛选、统计图、装饰图标、确认弹窗或任何新增业务功能。
- 为实现视觉效果改动 Task、Thread、Run、revision、调度、错误或持久化语义。

## 13. 设计自检结论

| 检查项 | 结论 |
| --- | --- |
| 是否忠实于目标图的悬浮纸张关系 | 是。外层透明，纸张独立，使用暖棕柔和高度阴影 |
| 是否删除了无关设计内容 | 是。不保留可见 Calendar 顶栏、独立日期摘要和共享右栏表面 |
| 是否保留业务能力 | 是。任务查看/运行/暂停/恢复/编辑/历史/删除以及日记打开/删除均保留 |
| 是否避免线框套娃 | 是。分类级仅三张纸面，任务内部改为扁平文本组 |
| 是否覆盖宽窄屏和 reduced motion | 是。给出 1024px、640px 规则和 reduced-motion 样式 |
| 是否可直接映射现有实现 | 是。原型和迁移表使用现有 Modal/CalendarPopup 类名，没有建立平行组件 |
