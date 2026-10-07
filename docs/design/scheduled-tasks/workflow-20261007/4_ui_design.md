<!-- [Input] files/workspace/1_prd_draft.md、files/workspace/3_hierarchy_logic.md、files/inputs/target_image.png、files/inputs/topic.txt。 -->
<!-- [Output] html-design-workflow Stage 4：定时任务 Chat 标记、详情侧栏、间隔编辑、运行历史与窄屏详情页的高保真 UI 规格及 HTML/Tailwind 参考。 -->
<!-- [Pos] 临时设计工作区的视觉设计产物；供后续 HTML 实现和正式交互设计复用。 -->
<!-- [Sync] 2026-10-07: 依据现行 PRD、层级逻辑和参考图统一桌面与窄屏视觉规格。 -->

# Ink & Memory 定时任务 UI 设计（Stage 4）

> 视觉方向：**Ultra-Sensory Minimalism / 暖纸张编辑界面**
> 技术基线：HTML5、Tailwind CSS 2.2.19、Font Awesome 6.0.0、Noto Serif SC、Noto Sans SC。

## 1. 视觉结论

参考图的主要气质来自近白纸面、深墨文字、低对比暖灰边界和宽松留白。Chat 中的任务标记像一张嵌在对话中的纸卡；右侧详情像同一张纸展开后的编辑页。页面不用强色块区分模块，主要依靠字号、间距、细线与轻微底色变化建立层级。

红色矩形仅是参考图标注，不属于产品界面。本设计不增加插画、纹理图案、装饰性渐变或无业务意义的徽章。状态颜色仅作辅助，所有状态同时显示文字。

桌面端保持 `A0 Chat 主区 + B0 任务详情侧栏` 并列；窄屏端以 `M2` 全高详情 sheet 覆盖 Chat。两端使用相同的字段顺序、状态文案与历史行结构，避免响应式切换时改变任务语义。

## 2. 美学样式表（Aesthetic Style）

| 维度 | 规格 | 应用位置 |
| --- | --- | --- |
| 风格 | 暖纸张超感官极简 | 全局；用质感和间距表达层级 |
| 应用底色 | `#EEEAE3` | 桌面双栏外层和窄屏遮罩下的背景 |
| 主纸面 | `#FBF9F4` | Chat、详情主体、窄屏 sheet |
| 抬升纸面 | `#FFFDF9` | 任务标记卡、表单组、历史组 |
| 柔和填充 | `#F3F0EA` | 时钟图标底、选中分段、骨架占位 |
| 主文字 | `#292724` | 标题、正文、表单当前值 |
| 次级文字 | `#746F68` | 规则摘要、时间、辅助说明 |
| 静默文字 | `#9A958E` | 占位、禁用说明 |
| 边界 | `rgba(67, 60, 52, .13)` | 卡片、分组、栏间分隔、行分隔 |
| 强调色 | `#6F604F` | 焦点环、当前分段、文字操作 |
| 成功 | `#5E765E` | “已应用”“已完成”辅助圆点与文字 |
| 进行中 | `#8A6C3D` | “正在应用”“正在运行”辅助圆点与文字 |
| 需要操作 | `#9A5D34` | 待处理状态、会话入口强调 |
| 错误 | `#9B5149` | 字段错误、失败与重试 |
| 标题字体 | `Noto Serif SC`，500–600 | 详情任务名、区块标题；不用于按钮和数据 |
| UI 字体 | `Noto Sans SC`，400–600 | Chat、表单、状态、按钮、时间 |
| 圆角 | 12 / 16 / 20px | 输入 / 卡片与分组 / 窄屏 sheet 顶角 |
| 阴影 | 仅窄屏 sheet 与浮层使用 | 桌面卡片以边框为主，不做悬浮瓷砖效果 |
| 动效 | 160–220ms，位移不超过 6px | 打开详情、hover、保存反馈；支持 reduced motion |

### 2.1 设计变量

生产实现应映射仓库现有语义 token。下面色值仅用于 Stage 4 高保真参考，不作为业务常量。

```css
:root {
  --im-app: #eeeae3;
  --im-paper: #fbf9f4;
  --im-paper-raised: #fffdf9;
  --im-paper-muted: #f3f0ea;
  --im-ink: #292724;
  --im-ink-muted: #746f68;
  --im-ink-quiet: #9a958e;
  --im-line: rgba(67, 60, 52, .13);
  --im-line-strong: rgba(67, 60, 52, .22);
  --im-accent: #6f604f;
  --im-success: #5e765e;
  --im-progress: #8a6c3d;
  --im-attention: #9a5d34;
  --im-danger: #9b5149;
  --im-focus: rgba(111, 96, 79, .28);
  --im-radius-sm: 12px;
  --im-radius-md: 16px;
  --im-radius-lg: 20px;
  --im-space-1: 4px;
  --im-space-2: 8px;
  --im-space-3: 12px;
  --im-space-4: 16px;
  --im-space-5: 20px;
  --im-space-6: 24px;
  --im-space-8: 32px;
  --im-header-h: 64px;
  --im-action-h: 72px;
}
```

## 3. 响应式画布与滚动合同

| 视口 | 布局 | 尺寸与滚动 |
| --- | --- | --- |
| `≥ 1180px` | Chat 与详情按约 `42% / 58%` 并列 | 外层固定为视口高；`A2` 与 `B8` 分别滚动 |
| `768–1179px` | Chat 保留最小阅读宽度，详情固定 `min(54vw, 640px)` | 栏间 1px 分隔；不得产生横向滚动 |
| `< 768px` | Chat 单页；任务详情作为全高 `M2` sheet 覆盖 | `B1` 与 `B7` 固定，只有 `B8` 滚动 |

- 桌面 `A1`、`A4`、`B1`、`B7` 始终可见；`B5` 不建立第二个滚动容器。
- 桌面打开详情后保留 Chat 的阅读位置；关闭时焦点回到触发详情的 `A3`。
- 窄屏从执行 Thread 返回时恢复 `M3` 滚动位置；从详情返回 Chat 时恢复 `M1` 并聚焦原任务卡。
- 所有长标题在任务卡和顶栏单行省略；prompt 与失败摘要在详情正文内换行。
- 点击目标最小 `44 × 44px`；键盘焦点使用 2px 外环且不依赖颜色。

## 4. UI 组件结构

| 编号 | 组件建议名 | 结构与视觉职责 | 交互职责 |
| --- | --- | --- | --- |
| `A3` | `ScheduledTaskMarker` | Chat turn 内的整卡入口；时钟、标题、计划摘要、应用状态、打开提示 | 以真实 task ID 打开 `B0/M2`；整卡单一点击面 |
| `B0` | `ScheduledTaskDetail` | 详情侧栏 / 窄屏 sheet；固定头尾，中部单滚动轴 | 加载 task、effective 状态和 history；关闭后恢复焦点 |
| `B2` | `TaskBrief` | 展示任务说明、来源 Chat、运行目标摘要 | prompt 保留换行；来源和目标只展示真实对象 |
| `B4` | `ApplyStatus` | 计划、下次运行和应用结果 | 不一致时区分已保存计划与当前计划，并给出恢复动作 |
| `B3` | `TaskScheduleForm` | 运行目标、规则、规则字段、时区、通知 | 编辑 desired；规则切换只显示适用字段 |
| `B3.3c` | `IntervalEditor` | 正整数输入、分钟单位、10 分钟快捷项 | 输入错误贴近字段，保留原值，不提交非法数据 |
| `B5` | `ScheduledRunHistory` | 实际执行、需要操作、失败、状态待确认、skipped 范围 | 有精确 target Thread 时打开会话；skipped 不显示入口 |
| `B7` | `DetailActions` | 固定底栏；取消与保存 | 合法修改直接保存；保存中防重复提交 |
| `M2` | `MobileTaskSheet` | 全高详情页 / sheet，复用 B1–B8 | 覆盖 Chat；保持唯一纵向滚动区 |

### 4.1 信息层级顺序

```text
B1 详情顶栏
└─ B8 单一滚动正文
   ├─ B2 任务说明
   ├─ B4 应用状态与下次运行
   ├─ B3 任务编辑表单
   │  ├─ 运行于
   │  ├─ 规则类型
   │  ├─ 规则字段（interval 时为 B3.3c）
   │  ├─ 时区
   │  └─ 通知
   └─ B5 运行历史
B7 固定操作区
```

## 5. 核心组件高保真规格

### 5.1 `A3` Chat 定时任务标记

**外观**

- 与所属 assistant 正文使用同一最大阅读宽度，正文后留 12px。
- 背景 `--im-paper-raised`，1px 暖灰边框，16px 圆角；桌面内边距 `16px`，窄屏 `14px`。
- 左侧时钟放在 44px 浅灰圆角方块内；图标 18px、1.5px 视觉线宽。
- 标题 15px/22px、600；副标题 13px/20px，格式为“规则摘要 · 应用状态”。
- 右侧“打开”是视觉提示，不是卡片内第二个 button；箭头仅指示去向。

**状态**

| 状态 | 副标题示例 | 辅助表现 |
| --- | --- | --- |
| 已应用 | `每 10 分钟 · 已应用` | 成功色 6px 圆点 |
| 正在应用 | `每 15 分钟 · 正在应用` | 进行中色圆点；无需循环动画 |
| 配置异常 | `仍按每 10 分钟运行 · 查看详情` | 错误色圆点与明确影响 |
| 加载详情失败 | 卡片本身保持可点击 | 在详情区域提供重试，不把卡片改成失败记录 |

**交互**

- hover 只将边框加深并上移 1px；active 恢复到原位。
- focus-visible 显示 2px 外环；Enter 与 Space 打开详情。
- 同一 turn 有多个成功结果时，卡片垂直排列，间距 8px，顺序与 Tool result 一致。

### 5.2 `B0` 右侧任务详情

**布局**

- 桌面以栏间 1px 分隔线进入，不使用覆盖阴影；建议最小宽度 480px，最大阅读宽度由双栏比例控制。
- `B1` 高 64px，左右内边距 24px。时钟与标题同组，更多和关闭使用 44px 图标按钮。
- `B8` 使用 `overflow-y:auto`，内边距 `24px 28px 40px`；内容最大宽度 720px，在宽侧栏内居中。
- `B7` 最小高 72px，1px 顶边界，背景使用 96% 不透明主纸面并支持安全区内边距。

**区块**

- 区块标题用 Noto Serif SC 16px/26px、600；标题下方 10px 放内容。
- `B2`、`B3`、`B5` 使用白纸分组和细边框；`B4` 可用浅色状态带，避免所有内容都变成相同卡片。
- 区块垂直间距 28px；组内行高至少 56px，最后一行不保留分隔线。
- 加载失败按区块局部替换；历史失败不禁用表单，保存失败不清空历史。

### 5.3 `B4` 应用状态

| 界面状态 | 信息顺序 | 用户动作 |
| --- | --- | --- |
| 已应用 | `已应用` → 当前计划 → 下次运行 | 无需额外动作 |
| 正在应用 | `正在应用` → 已保存计划 → `上一版仍在运行`及当前计划 | 自动刷新；可重试读取 |
| 保存失败 | `保存失败，当前计划保持不变` → 原因摘要 | 修正或重试保存 |
| 配置异常 | `配置异常，仍按上一版计划运行` → 当前生效计划 | 重试读取或打开设置 |

状态带不用内部名词解释 revision、snapshot 或 last-known-good。revision 只在诊断页面按需出现。

### 5.4 `B3.3c` 间隔编辑器

1. “规则”使用单次 / 每天 / 间隔三段选择器；切换后只渲染所需字段。
2. 选择“间隔”后显示“每隔 [数字输入] 分钟”；数值是整行第一视觉焦点。
3. 输入框使用 `inputmode="numeric"`，不依赖浏览器 stepper；页面校验正整数，服务端仍执行最终校验。
4. “10 分钟”快捷项是显式按钮，只在用户点击后填入 10，不作为隐藏 default。
5. 空值、0、负数、小数、非数字及超出服务端安全边界时，错误显示在输入下方并保留输入。

- 分段选择器高 40px，背景 `--im-paper-muted`，选中项为白纸面并带 1px 边界。
- 数字输入桌面宽 120px、窄屏自适应；数字 18px/26px、500，单位 14px。
- 正常边框为 `--im-line`；focus 为强调色边框和外环；错误为错误色边框与 13px 提示。
- 合法修改使 `B7` 保存按钮可用；非法修改使保存按钮不可提交，但取消始终可用。

### 5.5 `B5` 运行历史行

每一行对应一个真实 trigger 或一个 skipped 范围，不能把 skipped 范围画成执行会话。

| 行类型 | 左侧 | 主文案 | 次文案 | 右侧 |
| --- | --- | --- | --- | --- |
| 已完成 | 成功圆点 | `已完成` | `今天 10:30 · 用时 42 秒` + 结果摘要 | 有 target Thread 时“打开会话” |
| 正在运行 | 进行中圆点 | `正在运行` | `计划于 10:40 · 已运行 2 分钟` | 有 Thread 时“查看会话” |
| 需要操作 | 注意圆点 | `需要操作` | `等待确认：删除段落` | “打开会话”并定位待确认项 |
| 状态待确认 | 中性圆点 | `状态待确认` | `计划于 10:20` | 有 Thread 时“查看会话” |
| 失败 | 错误圆点 | `执行失败` | 可行动摘要，如“目标笔记授权已失效” | 有记录时“打开会话”；可另有“重新授权” |
| skipped 范围 | 静默图标 | `已跳过 2 次` | `10:00–10:10 · 上一次仍在运行` | 无箭头、无会话入口 |

- 行内边距 16px，最小高 68px；摘要最多两行，不能用省略号藏掉恢复动作。
- 可打开会话的行允许整行点击，右侧文字是去向提示；skipped 行保持静态。
- “继续加载更早记录”是列表末尾的文字按钮，加载后扩展 `B8`，不创建嵌套滚动区。
- 尚未运行显示安静空态：“尚无运行记录；下次运行 10:40”，不画成功图标。

### 5.6 `M2` 窄屏全高详情 sheet

- 视口宽 `< 768px` 时，详情使用 `position: fixed; inset: 0`，宽高均为视口尺寸；不保留并排 Chat 缩略栏。
- 顶部使用 `env(safe-area-inset-top)`，底部操作区使用 `env(safe-area-inset-bottom)`。
- `B1` 左侧改为“返回 Chat”图标按钮；标题居中区域可省略，更多位于右侧。
- `B8` 是唯一滚动容器，水平内边距 16px；表单组与历史组撑满宽度。
- `B7` 两个按钮等高 44px；保存为深墨实色，取消为纸面描边。
- 打开使用 180ms `translateX(6px) + opacity` 反馈；关闭反向。用户启用 reduced motion 时只切换透明度。

## 6. HTML + Tailwind 2.2.19 参考

下面代码是视觉和结构参考。`task ID`、`target_thread_id`、desired/effective 状态、历史数据与保存操作均应由真实 view model 和生产接口提供；示例脚本只演示响应式 sheet、间隔字段切换和本地校验反馈。

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover" />
  <title>Ink & Memory · 定时任务</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;600&family=Noto+Serif+SC:wght@500;600&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="https://lf6-cdn-tos.bytecdntp.com/cdn/expire-100-M/font-awesome/6.0.0/css/all.min.css" />
  <link rel="stylesheet" href="https://lf3-cdn-tos.bytecdntp.com/cdn/expire-1-M/tailwindcss/2.2.19/tailwind.min.css" />
  <style>
    :root {
      --im-app:#eeeae3; --im-paper:#fbf9f4; --im-raised:#fffdf9;
      --im-muted:#f3f0ea; --im-ink:#292724; --im-sub:#746f68;
      --im-quiet:#9a958e; --im-line:rgba(67,60,52,.13);
      --im-line-strong:rgba(67,60,52,.22); --im-accent:#6f604f;
      --im-success:#5e765e; --im-progress:#8a6c3d;
      --im-attention:#9a5d34; --im-danger:#9b5149;
    }
    * { box-sizing:border-box; }
    html, body { height:100%; }
    body { margin:0; color:var(--im-ink); background:var(--im-app); font-family:"Noto Sans SC",system-ui,sans-serif; }
    button, input, select { font:inherit; }
    .font-editorial { font-family:"Noto Serif SC",serif; }
    .workspace { height:100dvh; display:grid; grid-template-columns:minmax(420px,42%) minmax(480px,58%); overflow:hidden; }
    .paper { background:var(--im-paper); }
    .detail-panel { border-left:1px solid var(--im-line); }
    .workspace.detail-closed { grid-template-columns:1fr; }
    .workspace.detail-closed .detail-panel { display:none; }
    .detail-scroll { min-height:0; overflow-y:auto; overscroll-behavior:contain; scrollbar-gutter:stable; }
    .hairline { border-color:var(--im-line); }
    .surface { background:var(--im-raised); border:1px solid var(--im-line); border-radius:16px; }
    .icon-button { width:44px; height:44px; display:inline-grid; place-items:center; border-radius:12px; }
    .icon-button:hover { background:var(--im-muted); }
    .task-marker { transition:border-color 160ms ease, transform 160ms ease, background 160ms ease; }
    .task-marker:hover { border-color:var(--im-line-strong); transform:translateY(-1px); background:#fffefa; }
    .task-marker:active { transform:translateY(0); }
    .focusable:focus-visible { outline:2px solid rgba(111,96,79,.35); outline-offset:2px; }
    .status-dot { width:7px; height:7px; border-radius:999px; flex:none; margin-top:7px; }
    .form-row + .form-row, .history-row + .history-row { border-top:1px solid var(--im-line); }
    .segment { background:var(--im-muted); padding:3px; border-radius:12px; display:grid; grid-template-columns:repeat(3,1fr); gap:3px; }
    .segment button { min-height:36px; border-radius:9px; color:var(--im-sub); }
    .segment button[aria-selected="true"] { color:var(--im-ink); background:var(--im-raised); box-shadow:0 1px 2px rgba(45,39,33,.08); }
    .field { border:1px solid var(--im-line); background:var(--im-raised); border-radius:12px; }
    .field:focus { outline:none; border-color:var(--im-accent); box-shadow:0 0 0 3px rgba(111,96,79,.16); }
    .field[aria-invalid="true"] { border-color:var(--im-danger); box-shadow:0 0 0 3px rgba(155,81,73,.10); }
    .sheet-enter { animation:sheet-in 180ms ease-out both; }
    @keyframes sheet-in { from { opacity:0; transform:translateX(6px); } to { opacity:1; transform:translateX(0); } }
    @media (max-width:1179px) and (min-width:768px) { .workspace { grid-template-columns:minmax(360px,46%) minmax(440px,54%); } }
    @media (max-width:767px) {
      .workspace { display:block; }
      .detail-panel { position:fixed; inset:0; z-index:40; border-left:0; }
      .desktop-only { display:none !important; }
      .detail-body { padding-left:16px !important; padding-right:16px !important; }
    }
    @media (min-width:768px) { .mobile-only { display:none !important; } }
    @media (prefers-reduced-motion:reduce) {
      *, *::before, *::after { scroll-behavior:auto !important; animation-duration:.01ms !important; transition-duration:.01ms !important; }
    }
  </style>
</head>
<body>
  <main class="workspace" aria-label="Ink & Memory 工作区">
    <!-- A0 Chat 主区 -->
    <section class="paper min-w-0 flex flex-col" aria-label="Chat">
      <header class="h-16 flex-none flex items-center justify-between px-5 border-b hairline">
        <div class="min-w-0 flex items-center gap-3">
          <i class="far fa-folder text-gray-500" aria-hidden="true"></i>
          <h1 class="truncate text-base font-medium">核对 Dream CLI 迁移设计并恢复原包结构</h1>
        </div>
        <button class="icon-button focusable" aria-label="更多 Chat 操作"><i class="fas fa-ellipsis-h" aria-hidden="true"></i></button>
      </header>

      <div class="flex-1 min-h-0 overflow-y-auto px-5 py-8">
        <article class="max-w-3xl mx-auto" aria-label="assistant 回复">
          <p class="text-base leading-8">完整可复制执行稿已交给 Dream 新任务，目标已建立。已并入每 10 分钟的验收跟进。</p>
          <button id="task-marker" type="button" data-task-id="scheduled-task-id"
            class="task-marker focusable surface w-full mt-3 p-4 text-left flex items-center gap-4"
            aria-controls="task-detail" aria-expanded="true">
            <span class="w-11 h-11 flex-none rounded-xl flex items-center justify-center" style="background:var(--im-muted)">
              <i class="far fa-clock text-lg" style="color:var(--im-sub)" aria-hidden="true"></i>
            </span>
            <span class="min-w-0 flex-1">
              <span class="block truncate text-sm font-semibold">Dream 会话与 Notion 修复验收跟进</span>
              <span class="mt-1 flex items-center gap-2 text-xs" style="color:var(--im-sub)">
                <span class="status-dot" style="background:var(--im-success);margin-top:0"></span>
                <span>每 10 分钟 · 已应用</span>
              </span>
            </span>
            <span class="flex-none text-sm font-medium" style="color:var(--im-sub)">打开 <i class="fas fa-chevron-right ml-1 text-xs" aria-hidden="true"></i></span>
          </button>
        </article>
      </div>

      <footer class="flex-none p-4 border-t hairline">
        <div class="max-w-3xl mx-auto surface h-14 px-4 flex items-center gap-3">
          <button class="icon-button focusable -ml-2" aria-label="添加附件"><i class="fas fa-plus" aria-hidden="true"></i></button>
          <span class="flex-1 text-sm" style="color:var(--im-quiet)">随心输入…</span>
          <button class="icon-button focusable" aria-label="发送"><i class="fas fa-arrow-up" aria-hidden="true"></i></button>
        </div>
      </footer>
    </section>

    <!-- B0 / M2：桌面侧栏，窄屏全高 sheet -->
    <aside id="task-detail" class="detail-panel sheet-enter paper min-w-0 flex flex-col" aria-labelledby="detail-title">
      <header class="flex-none flex items-center gap-2 px-4 md:px-6 border-b hairline" style="min-height:64px;padding-top:env(safe-area-inset-top)">
        <button id="detail-back" class="mobile-only icon-button focusable" aria-label="返回 Chat"><i class="fas fa-chevron-left" aria-hidden="true"></i></button>
        <span class="desktop-only w-9 h-9 rounded-xl flex items-center justify-center" style="background:var(--im-muted)"><i class="far fa-clock" aria-hidden="true"></i></span>
        <h2 id="detail-title" tabindex="-1" class="font-editorial min-w-0 flex-1 truncate text-lg font-semibold">Dream 会话与 Notion 修复验收跟进</h2>
        <button class="icon-button focusable" aria-label="更多任务操作"><i class="fas fa-ellipsis-h" aria-hidden="true"></i></button>
        <button id="detail-close" class="desktop-only icon-button focusable" aria-label="关闭任务详情"><i class="fas fa-times" aria-hidden="true"></i></button>
      </header>

      <!-- B8 / M3：详情唯一滚动区 -->
      <div class="detail-scroll detail-body flex-1 px-6 lg:px-7 py-6">
        <div class="max-w-2xl mx-auto space-y-7">
          <section aria-labelledby="brief-title">
            <h3 id="brief-title" class="font-editorial text-base font-semibold mb-3">任务说明</h3>
            <div class="surface p-4">
              <p class="text-sm leading-7">跟进本机 Dream 的修复任务，检查执行进展，并在出现需要处理的结果时通知我。</p>
              <dl class="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                <div><dt style="color:var(--im-sub)">来源 Chat</dt><dd class="mt-1 font-medium truncate">核对 Dream CLI 迁移设计…</dd></div>
                <div><dt style="color:var(--im-sub)">运行于</dt><dd class="mt-1 font-medium truncate">当前笔记 · Editor Session</dd></div>
              </dl>
            </div>
          </section>

          <section aria-labelledby="status-title">
            <h3 id="status-title" class="font-editorial text-base font-semibold mb-3">计划状态</h3>
            <div class="rounded-2xl px-4 py-3 flex items-start gap-3" style="background:var(--im-muted)">
              <span class="status-dot" style="background:var(--im-success)"></span>
              <div class="min-w-0"><p class="text-sm font-semibold">已应用 · 每 10 分钟</p><p class="mt-1 text-sm" style="color:var(--im-sub)">下次运行：今天 10:40 · Asia/Shanghai</p></div>
            </div>
          </section>

          <section aria-labelledby="schedule-title">
            <h3 id="schedule-title" class="font-editorial text-base font-semibold mb-3">任务设置</h3>
            <div class="surface overflow-hidden">
              <div class="form-row px-4 py-4 flex items-center gap-4">
                <label for="target" class="w-20 flex-none text-sm" style="color:var(--im-sub)">运行于</label>
                <select id="target" class="focusable min-w-0 flex-1 bg-transparent text-right text-sm font-medium"><option>当前笔记 · Editor Session</option></select>
              </div>
              <div class="form-row px-4 py-4">
                <span id="rule-label" class="block text-sm mb-3" style="color:var(--im-sub)">规则</span>
                <div class="segment" role="tablist" aria-labelledby="rule-label">
                  <button type="button" role="tab" aria-selected="false" data-rule="once">单次</button>
                  <button type="button" role="tab" aria-selected="false" data-rule="daily">每天</button>
                  <button type="button" role="tab" aria-selected="true" data-rule="interval">间隔</button>
                </div>
              </div>
              <div id="interval-fields" class="form-row px-4 py-4" aria-labelledby="interval-label">
                <div class="flex flex-wrap items-center gap-3">
                  <label id="interval-label" for="interval-minutes" class="text-sm" style="color:var(--im-sub)">每隔</label>
                  <input id="interval-minutes" class="field w-28 px-3 py-2 text-lg font-medium" inputmode="numeric" autocomplete="off" value="10" aria-describedby="interval-help interval-error" />
                  <span class="text-sm">分钟</span>
                  <button id="quick-ten" type="button" class="focusable ml-auto px-3 py-2 rounded-xl text-xs font-medium" style="background:var(--im-muted);color:var(--im-sub)">10 分钟</button>
                </div>
                <p id="interval-help" class="mt-2 text-xs" style="color:var(--im-sub)">输入正整数；更新后影响后续运行。</p>
                <p id="interval-error" class="hidden mt-2 text-xs" style="color:var(--im-danger)" role="alert">请输入大于 0 的整数分钟数。</p>
              </div>
              <div class="form-row px-4 py-4 flex items-center gap-4">
                <label for="timezone" class="w-20 flex-none text-sm" style="color:var(--im-sub)">时区</label>
                <select id="timezone" class="focusable min-w-0 flex-1 bg-transparent text-right text-sm font-medium"><option>Asia/Shanghai</option></select>
              </div>
              <div class="form-row px-4 py-4 flex items-center gap-4">
                <label for="notice" class="w-20 flex-none text-sm" style="color:var(--im-sub)">通知</label>
                <select id="notice" class="focusable min-w-0 flex-1 bg-transparent text-right text-sm font-medium"><option>重要更新</option></select>
              </div>
            </div>
          </section>

          <section aria-labelledby="history-title">
            <div class="flex items-center justify-between mb-3"><h3 id="history-title" class="font-editorial text-base font-semibold">运行历史</h3><span class="text-xs" style="color:var(--im-sub)">按计划时间倒序</span></div>
            <div class="surface overflow-hidden">
              <button class="history-row focusable w-full px-4 py-4 text-left flex gap-3" data-thread-id="thread-success">
                <span class="status-dot" style="background:var(--im-success)"></span>
                <span class="min-w-0 flex-1"><strong class="block text-sm font-semibold">已完成</strong><span class="block mt-1 text-xs leading-5" style="color:var(--im-sub)">今天 10:30 · 用时 42 秒<br />未发现新的阻塞项</span></span>
                <span class="self-center flex-none text-xs font-medium" style="color:var(--im-accent)">打开会话 <i class="fas fa-chevron-right ml-1" aria-hidden="true"></i></span>
              </button>
              <button class="history-row focusable w-full px-4 py-4 text-left flex gap-3" data-thread-id="thread-attention">
                <span class="status-dot" style="background:var(--im-attention)"></span>
                <span class="min-w-0 flex-1"><strong class="block text-sm font-semibold">需要操作</strong><span class="block mt-1 text-xs leading-5" style="color:var(--im-sub)">今天 10:20 · 等待确认：删除段落</span></span>
                <span class="self-center flex-none text-xs font-medium" style="color:var(--im-attention)">打开会话 <i class="fas fa-chevron-right ml-1" aria-hidden="true"></i></span>
              </button>
              <div class="history-row px-4 py-4 flex gap-3">
                <span class="mt-0.5 w-4 text-center flex-none" style="color:var(--im-quiet)"><i class="fas fa-forward text-xs" aria-hidden="true"></i></span>
                <span class="min-w-0"><strong class="block text-sm font-semibold">已跳过 2 次</strong><span class="block mt-1 text-xs leading-5" style="color:var(--im-sub)">10:00–10:10 · 上一次仍在运行</span></span>
              </div>
              <button class="history-row focusable w-full px-4 py-3 text-sm font-medium" style="color:var(--im-accent)">继续加载更早记录</button>
            </div>
          </section>
        </div>
      </div>

      <footer class="flex-none px-4 md:px-6 py-3 border-t hairline" style="background:rgba(251,249,244,.96);padding-bottom:max(12px,env(safe-area-inset-bottom))">
        <div class="max-w-2xl mx-auto grid grid-cols-2 gap-3 sm:flex sm:justify-end">
          <button id="cancel-edit" class="focusable h-11 px-5 rounded-xl border hairline text-sm font-medium">取消</button>
          <button id="save-edit" class="focusable h-11 px-6 rounded-xl text-sm font-semibold text-white" style="background:var(--im-ink)">保存</button>
        </div>
      </footer>
    </aside>
  </main>

  <script>
    const workspace = document.querySelector('.workspace');
    const detail = document.querySelector('#task-detail');
    const marker = document.querySelector('#task-marker');
    const intervalInput = document.querySelector('#interval-minutes');
    const intervalFields = document.querySelector('#interval-fields');
    const intervalError = document.querySelector('#interval-error');
    const save = document.querySelector('#save-edit');
    const tabs = [...document.querySelectorAll('[data-rule]')];

    function openDetail() {
      workspace.classList.remove('detail-closed');
      marker.setAttribute('aria-expanded', 'true');
      document.querySelector('#detail-title').focus();
    }
    function closeDetail() {
      workspace.classList.add('detail-closed');
      marker.setAttribute('aria-expanded', 'false');
      marker.focus();
    }
    function validateInterval() {
      const valid = /^[1-9]\d*$/.test(intervalInput.value.trim());
      intervalInput.setAttribute('aria-invalid', String(!valid));
      intervalError.classList.toggle('hidden', valid);
      save.disabled = !valid;
      save.classList.toggle('opacity-40', !valid);
      return valid;
    }

    marker.addEventListener('click', openDetail);
    document.querySelector('#detail-back').addEventListener('click', closeDetail);
    document.querySelector('#detail-close').addEventListener('click', closeDetail);
    intervalInput.addEventListener('input', validateInterval);
    document.querySelector('#quick-ten').addEventListener('click', () => {
      intervalInput.value = '10'; validateInterval(); intervalInput.focus();
    });
    tabs.forEach(tab => tab.addEventListener('click', () => {
      tabs.forEach(item => item.setAttribute('aria-selected', String(item === tab)));
      intervalFields.hidden = tab.dataset.rule !== 'interval';
      save.disabled = false; save.classList.remove('opacity-40');
    }));
    if (matchMedia('(max-width: 767px)').matches) {
      workspace.classList.add('detail-closed');
      marker.setAttribute('aria-expanded', 'false');
    }
  </script>
</body>
</html>
```

## 7. 状态、空态与错误呈现

| 场景 | 视觉处理 | 保留能力 |
| --- | --- | --- |
| 详情加载中 | 先显示固定顶栏；B2/B4/B3 各用 2–3 条暖灰骨架，不闪烁 | Chat 可继续阅读和输入，详情可关闭 |
| task 不存在或无权限 | 正文上部显示“任务不存在或当前不可访问”与重试 | 关闭 / 返回 Chat |
| history 读取失败 | B5 原位显示局部错误和“重试历史” | B2–B4 与保存仍可使用 |
| 尚未运行 | B5 显示“尚无运行记录”与下次运行时间 | 编辑、返回 Chat |
| 目标身份缺失 | B4 与 B3 运行目标行显示“目标笔记身份缺失，写入未执行” | 打开设置 / 重新授权；不自动换目标 |
| 保存中 | 保存按钮显示“保存中…”，保持表单内容并禁用重复提交 | 取消可按既有提交合同处理 |
| 正在应用 | B4 展示已保存计划和上一版当前计划 | 自动刷新或重试读取 |
| 配置异常 | 错误色状态点 + “仍按上一版计划运行” | 重试读取 / 打开设置 |

## 8. 动效与反馈

只在操作反馈有帮助时使用动效：

- `A3` hover 上移 1px、160ms，提示它是可打开的整体入口。
- 桌面详情首次出现使用 160ms 淡入；不做持续滑动，避免左右阅读区漂移。
- 窄屏 sheet 使用 180ms、6px 的轻位移，帮助理解从 Chat 进入详情的层级。
- 保存成功后，按钮文字短暂变为“已保存”，`B4` 随服务端状态更新为“正在应用”或“已应用”；不使用烟花、弹跳或全屏提示。
- 正在运行与正在应用不使用无限旋转动画；文字与状态点足以表达，减少视觉噪声。
- `prefers-reduced-motion: reduce` 下移除位移与长过渡。

## 9. 可访问性与内容规则

- `A3` 只有一个语义 button；“打开”与箭头放在该 button 内作为提示，避免嵌套点击目标。
- 规则选择器使用 `tablist/tab` 或等价的单选语义；选中状态不得只靠底色。
- interval 错误通过 `aria-invalid` 与 `aria-describedby` 关联，错误出现后不清空输入。
- 状态点全部配套文字；成功、警告和错误的对比度按项目现有标准校验。
- 历史行只有存在真实 `target_thread_id` 时才成为链接或按钮；skipped 行保持普通 `div`。
- prompt、结果摘要和错误文本使用正常文流，不通过 tooltip 承载必须信息。
- 关闭详情后恢复原 `A3` 焦点；窄屏 sheet 打开后焦点进入详情标题或首个可编辑字段。

## 10. 实现交接清单

- [ ] 先复用现有 Chat message、右侧栏、表单行、Thread 导航、按钮与语义 token，再映射本稿尺寸。
- [ ] `A3` 只由含真实 task ID 的创建结果生成；刷新后保持同一 task ID。
- [ ] `B3` 保存 desired，`B4` 只展示服务端给出的应用结果；浏览器不自行判断“已应用”。
- [ ] interval 快捷项必须由用户点击触发；未输入时不隐式提交 10。
- [ ] 规则切换只显示适用字段，非法输入保留并阻止提交。
- [ ] 历史实际执行行使用精确 `target_thread_id`；skipped 范围没有会话入口。
- [ ] 桌面只有 `A2` 与 `B8` 两个独立滚动区；窄屏详情只有 `M3/B8` 一个滚动区。
- [ ] 页面不展示 claim、lease、数据库字段、内部堆栈、fresh snapshot 或 last-known-good 等实现词。
- [ ] 详情中的“需要操作”只负责进入真实执行 Thread；不复制一套工具确认弹窗。
- [ ] 正式实现需覆盖加载、局部错误、尚未运行、授权失效、保存失败、正在应用与配置异常。
