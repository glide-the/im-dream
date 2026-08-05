# 「子智能体任务」高保真 UI 设计与 React 映射规格

## 1. 视觉方向

本功能采用“超感官极简主义（Ultra-Sensory Minimalism）”：保留参考图中宽松的纵向留白、低对比深浅层次、彩色代理头像和一眼可读的状态分组，同时服从 Ink & Memory 现有纸张色设计系统。它是聊天的辅助信息层，不应做成高饱和仪表盘，也不应引入与现有界面冲突的玻璃拟态、外部图标字体或整页 Tailwind 风格。

### 1.1 美学风格表

| 设计维度 | 高保真规格 | 与参考图的对应 | 现有应用映射 |
| --- | --- | --- | --- |
| 整体气质 | 安静、克制、状态清晰；以留白和排版建立层级 | 深色背景、灰色分组标题、单条任务卡 | 使用 `tokens.css` 中纸张色与文本 token，自动适配亮暗主题 |
| 面板形态 | 桌面端右侧推挤式 `<aside>`，20rem 基准宽；窄屏覆盖式抽屉 | 参考图是完整详情页，本项目收敛为右侧会话辅助栏 | 复用 `FileSidebar` 的宽度归零、左边框、0.25s 开合方式 |
| 信息密度 | 标题栏紧凑，分组间留出明显呼吸，任务行高度约 64–76px | “已开启”与“完成 · 23”之间大段留白 | 4px 基础网格；内容区 12px 内边距，组间 24px |
| 主色 | 不新增品牌主色；强调使用现有动作色、成功色、警告色 | 彩色代理图标承担局部视觉焦点 | `--color-action-link`、`--color-state-success/warning/error` |
| 字体 | 继承聊天页 `'Excalifont', 'Xiaolai', Georgia, serif`；数字用 tabular nums | 截图标题自然、数字醒目但不机械 | 不加载新字体；标题 15–16px/600，正文 13px，辅助 11–12px |
| 图标 | 1.0–1.1rem 线稿 SVG，`currentColor`；头像为稳定彩色圆形/几何 fallback | 顶部机器人线稿、花形彩色头像 | 新增 `IconSubagents` 到现有 `Icons.tsx`；不依赖 Font Awesome |
| 层级 | 背景 → 面板 → 任务行 → 状态点/头像；只用一层柔和边框 | 截图任务行比背景深一阶 | `--color-bg-app`、`--color-bg-paper`、`--color-border-paper` |
| 动效 | 仅面板开合、hover 变色、运行点轻呼吸、任务迁移淡入 | 保留“运行中”的生命感，不制造噪音 | 140ms hover、250ms panel、900ms pulse；支持 reduced motion |

---

## 2. 设计 Token 与精确尺寸

### 2.1 直接复用的项目颜色

| 语义 | CSS 变量 | 当前亮色值 | 当前暗色值 | 使用位置 |
| --- | --- | --- | --- | --- |
| 应用/面板背景 | `--color-bg-app` | `#f6efe5` | `#1d1916` | B1 面板 |
| 任务卡纸面 | `--color-bg-paper` | `#fffaf2` | `#2a241f` | C2、D2 任务行 |
| 按钮打开/hover | `--color-bg-surface` / `--color-bg-hover` | 半透明暖白 / 暖棕 6% | 半透明深棕 / 白 8% | A1、关闭、加载更多 |
| 实心浮层 | `--color-bg-surface-solid` | `#fffdf8` | `#342d27` | tooltip |
| 边界 | `--color-border-paper` | `#d8c7b3` | `#5a4d3d` | B1 左边框、标题栏分割线、任务行弱边界 |
| 主文本 | `--color-text-primary` | `#3f3429` | `#f3e8d8` | 标题、任务名、耗时 |
| 次文本 | `--color-text-secondary` | `#7a6a59` | `#c8bcae` | 分组标题、摘要 |
| 弱文本 | `--color-text-muted` | `#9a8a78` | `#9f9283` | 空态、更新时间、次级提示 |
| 焦点/链接 | `--color-action-link` | `#4a90e2` | `#81b7d2` | 图标点缀、加载更多、focus 辅助 |
| 成功 | `--color-state-success` | `#7e9468` | `#7bcf8f` | 完成态小图标（不可单独承载语义） |
| 运行/等待 | `--color-state-warning` | `#c78855` | `#f7c96a` | 运行点、未读提示 |
| 错误 | `--color-state-error` | `#a86652` | `#ff7a70` | E3、失败态扩展 |
| 遮罩 | `--color-bg-overlay` | 暖黑 50% | 黑 72% | 窄屏抽屉遮罩 |

不得在新组件内复制这组 HEX；表中的数值仅用于设计验收，生产代码必须引用变量。

### 2.2 局部几何与排版 Token

建议在组件局部 CSS 使用以下别名，数值对齐现有 `PlanButton` 与 `FileSidebar`：

```css
.subagents-ui {
  --subagents-sidebar-width: 20rem;
  --subagents-drawer-max-width: 22rem;
  --subagents-space-1: 0.25rem;  /* 4px */
  --subagents-space-2: 0.5rem;   /* 8px */
  --subagents-space-3: 0.75rem;  /* 12px */
  --subagents-space-4: 1rem;     /* 16px */
  --subagents-space-6: 1.5rem;   /* 24px */
  --subagents-radius-sm: 0.55rem;
  --subagents-radius-row: 0.75rem;
  --subagents-motion-fast: 140ms;
  --subagents-motion-panel: 250ms;
}
```

### 2.3 尺寸规范

| 模块 | 高/宽 | 内边距与间距 | 字号/行高 | 备注 |
| --- | --- | --- | --- | --- |
| A1 入口 | 高 32px；宽随内容，最小 32px | 横向 7px；图标与 A2 间 6px | 13px / 1 | 与 PlanButton 完全同高 |
| A2 头像 | 18px；重叠时负间距 4px | 每个 1px 背景描边 | 汇总 12px/600 | 最多 4 个，更多显示 `+N` |
| B1 面板 | 320px 桌面宽；最大建议 352px | 内容区 12px | 继承 ChatView 字体 | 关闭时 `width/min-width:0` |
| B2 标题栏 | 最小高 56px | 16px；左右两端对齐 | 16px/600 | 底部 1px 分割线；sticky top |
| C1/D1 分组标题 | 最小高 24px | 0 4px，组前 20–24px | 13px/600；字距 0.01em | 数字使用 `font-variant-numeric: tabular-nums` |
| C2/D2 任务行 | 最小高 68px | 10px 12px；行间 6px | 标题 14px/1.3；摘要 12px/1.45；耗时 12px | 圆角 12px；长文本截断 |
| 行内头像 | 32px × 32px | 与正文间 10px | fallback 字符 12px/700 | `flex-shrink:0` |
| C3 分组空态 | 最小高 44px | 8px 4px | 13px/1.5 | 不用大插画，避免误解为全局空 |
| E2 全局空态 | 内容区垂直居中，建议最小高 220px | 24px | 标题 14px；说明 12px | 可用 32px 线稿图标 |
| D3 加载更多 | 高 32px | 0 10px | 12px/600 | 文本按钮，不做实心主按钮 |

---

## 3. 组件结构与模块映射

| React 组件 | 模块 ID | 职责 | 输入 | 输出/操作 |
| --- | --- | --- | --- | --- |
| `SubagentButton` | A1、A2 | 入口、头像汇总、计数、未读点 | `open`、`summary`、`buttonRef` | `onToggle`、焦点返回锚点 |
| `SubagentAvatarStack` | A2 | 最近代理去重头像 | `agents`、`max=4` | 视觉头像与隐藏的可访问摘要 |
| `SubagentSidebar` | B1、B2 | 面板框架、关闭、焦点与响应式 | `threadId`、`open`、store state | `onClose`、`onRetry` |
| `SubagentSectionHeading` | C1、D1 | 分组标题与全量计数 | `label`、`count?` | 无业务操作 |
| `SubagentTaskList` | C2、D2 | 语义化任务列表 | 排序后的 `tasks`、`variant` | 渲染 `SubagentTaskRow` |
| `SubagentTaskRow` | C2、D2 | 头像、标题、状态、摘要、耗时 | 单条 task、共享 `now` | 点击进入单任务执行详情 |
| `SubagentTaskDetail` | F1–F3 | 任务元信息、结果、错误与脱敏执行时间线 | 单条 task + activity | 面板内详情视图，返回后恢复列表 |
| `SubagentActiveEmpty` | C3 | 当前无运行任务 | 无 | 分组内说明 |
| `SubagentLoadMore` | D3 | cursor 分页 | `loading/error/hasMore` | `onLoadMore` |
| `SubagentSkeleton` | E1 | 首次水合占位 | 无 | 3–5 行骨架 |
| `SubagentEmpty` | E2 | 整个线程无任务 | 无 | 全局说明 |
| `SubagentNotice` | E3 | 错误、离线、旧快照 | `error/stale/hasSnapshot` | `onRetry` |

推荐文件边界：

```text
frontend/src/components/chat/
├── Icons.tsx                         # IconSubagents
├── SubagentPanel.tsx                 # A1–E3 组件
└── SubagentPanel.css                 # 局部样式、响应式、reduced-motion

frontend/src/hooks/
└── useThreadSubagents.ts             # 线程级快照 + 增量 store

frontend/src/lib/
└── claude-agent-transport.ts          # subagent-task-updated 转发，不生成消息气泡
```

---

## 4. 高保真状态规格

### 4.1 A1/A2 入口

- 默认：透明背景、次级文字；不显示外边框。
- hover：`--color-bg-surface` 背景、主文本色，140ms。
- 打开：保持 hover 背景，`aria-expanded=true`。
- 运行中：右上角 6px 警告色圆点；有文字空间时显示“2 运行中 · 23 完成”。
- 未读但无运行：同一位置显示 6px 警告色圆点；打开后清除视觉未读，不改变任务状态。
- 窄屏：隐藏 A2 可见文字和头像，只保留 32px 图标按钮；`aria-label` 包含完整数量。
- 无任务：A1 不渲染，不能留下空白占位。

### 4.2 B1/B2 侧栏

- 桌面：背景 `--color-bg-app`，左侧 `1px solid --color-border-paper`；无额外厚阴影，与 FileSidebar 视觉同源。
- 标题栏：背景继承，`position:sticky; top:0; z-index:1`；底部边界防止滚动内容穿透。
- 关闭按钮：32px 方形点击区，图标 16px；hover 背景使用 `--color-bg-hover`。
- 窄屏：`position:absolute; inset-block:0; right:0; width:min(22rem,100vw)`，叠加 `--color-bg-overlay` 遮罩；面板可加 `0 12px 32px --color-shadow-medium`。

### 4.3 C2/D2 任务行

- 行采用 `grid-template-columns: 32px minmax(0,1fr) auto`，避免耗时挤压标题。
- 标题与耗时同一行；标题 `text-overflow:ellipsis`，耗时不换行并使用 tabular nums。
- 摘要占中间列第二行，最多两行；运行行可在摘要前加可读状态文本“运行中 ·”。
- 默认背景 `--color-bg-paper`；整行使用语义化 `<button>`，hover 只改变纸面背景与弱边框，不使用抬升阴影；`:focus-visible` 必须清晰。
- 点击任务行后在 B1 内容槽切换到 F1–F3：F1 为任务身份和状态元信息，F2 为最新结果/错误，F3 为按时间排列的脱敏执行记录。标题栏左侧变为返回按钮。
- 新完成任务淡入 160ms；迁移后不保留旧运行行。
- 代理头像使用服务端头像；fallback 基于稳定哈希选取现有 voice 色变量。头像边界使用 `--color-bg-app`，保证重叠时可辨识。

### 4.4 E1–E3 系统状态

- E1 骨架使用 `--color-bg-hover` 与 `--color-bg-active` 的水平柔光，不使用纯白高亮。
- E2 全局空态居中；图标弱色、文案主次两级。C3 只是一行分组内空文案，两者视觉重量必须不同。
- E3 无缓存时用 `color-mix(in srgb, var(--color-state-error) 10%, var(--color-bg-paper))` 背景；有缓存时压缩为顶部 36–44px 通知，不挡住列表。

---

## 5. 可映射到现有 React 的核心代码示意

以下示意使用当前应用的 React、内联状态控制、CSS 变量和本地图标方式；它是实现骨架，不包含真实 store 的全部合并逻辑。

### 5.1 图标与入口

```tsx
// Icons.tsx：沿用项目现有 SVGProps 签名与 currentColor
export function IconSubagents(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" {...props}>
      <path d="M9 4h6M12 2v2" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      <rect x="5" y="5" width="14" height="11" rx="4" stroke="currentColor" strokeWidth="1.7" />
      <circle cx="9.5" cy="10.5" r="1" fill="currentColor" />
      <circle cx="14.5" cy="10.5" r="1" fill="currentColor" />
      <path d="M9.5 14h5M7 18.5c-1.4.6-2.5 1.8-3 3.5M17 18.5c1.4.6 2.5 1.8 3 3.5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}

interface SubagentButtonProps {
  open: boolean;
  activeCount: number;
  completedCount: number;
  recentAgents: SubagentIdentity[];
  hasUnseenUpdate: boolean;
  onToggle: () => void;
  buttonRef: React.RefObject<HTMLButtonElement | null>;
}

function SubagentButton(props: SubagentButtonProps) {
  const { t } = useTranslation();
  const visible = props.activeCount + props.completedCount > 0;
  if (!visible) return null;

  const label = props.activeCount > 0
    ? t('chat.subagents.summaryRunning', {
        active: props.activeCount,
        completed: props.completedCount,
      })
    : t('chat.subagents.summaryCompleted', { count: props.completedCount });

  return (
    <button
      ref={props.buttonRef}
      type="button"
      className="subagent-trigger"
      aria-label={`${t('chat.subagents.title')}，${label}`}
      aria-controls="chat-subagent-sidebar"
      aria-expanded={props.open}
      data-open={props.open || undefined}
      onClick={props.onToggle}
    >
      <IconSubagents className="subagent-trigger__icon" />
      <span className="subagent-trigger__wide">
        <SubagentAvatarStack agents={props.recentAgents} max={4} />
        <span className="subagent-trigger__summary">{label}</span>
      </span>
      {(props.activeCount > 0 || props.hasUnseenUpdate) && (
        <span className="subagent-trigger__dot" aria-hidden="true" />
      )}
    </button>
  );
}
```

### 5.2 任务行与详情面板

```tsx
function SubagentTaskRow({ task, now }: { task: SubagentTask; now: number }) {
  const { t, i18n } = useTranslation();
  const active = task.status === 'pending' || task.status === 'running';
  const duration = active
    ? formatDuration(Math.max(0, now - Date.parse(task.startedAt ?? task.createdAt)), i18n.language)
    : formatDuration(resolveFinalDuration(task), i18n.language);

  return (
    <li className="subagent-task-row">
      <SubagentAvatar agent={task.agent} />
      <div className="subagent-task-row__body">
        <div className="subagent-task-row__top">
          <span className="subagent-task-row__title" title={task.taskName}>
            {task.taskName}
          </span>
          <time className="subagent-task-row__duration">{duration}</time>
        </div>
        <p className="subagent-task-row__summary">
          {active && <span>{t(`chat.subagents.status.${task.status}`)} · </span>}
          {task.summary || t('chat.subagents.noSummary')}
        </p>
      </div>
    </li>
  );
}

function SubagentSidebar({ threadId, open, onClose, returnFocusRef }: Props) {
  const { t } = useTranslation();
  const state = useThreadSubagents(threadId);
  const active = state.tasks.filter(isActiveTask);
  const completed = state.tasks.filter((task) => task.status === 'completed');

  return (
    <aside
      id="chat-subagent-sidebar"
      className="subagent-sidebar"
      data-open={open || undefined}
      aria-labelledby="chat-subagent-sidebar-title"
      aria-hidden={!open}
    >
      {open && (
        <>
          <header className="subagent-sidebar__header">
            <div className="subagent-sidebar__heading">
              <IconSubagents />
              <h2 id="chat-subagent-sidebar-title">{t('chat.subagents.title')}</h2>
            </div>
            <button type="button" className="subagent-icon-button" onClick={onClose}
              aria-label={t('chat.subagents.close')}>
              <IconX />
            </button>
          </header>

          <div className="subagent-sidebar__content">
            {state.loading && !state.hasSnapshot ? <SubagentSkeleton /> : null}
            {!state.loading && state.error && !state.hasSnapshot
              ? <SubagentNotice error={state.error} onRetry={state.retry} /> : null}
            {state.hasSnapshot && state.counts.total === 0 ? <SubagentEmpty /> : null}

            {state.hasSnapshot && state.counts.total > 0 ? (
              <>
                {state.error || state.connectionStale
                  ? <SubagentNotice stale error={state.error} onRetry={state.retry} /> : null}
                <SubagentSectionHeading label={t('chat.subagents.active')}
                  count={state.counts.active} />
                {active.length > 0
                  ? <SubagentTaskList tasks={active} variant="active" />
                  : <SubagentActiveEmpty />}
                <SubagentSectionHeading label={t('chat.subagents.completed')}
                  count={state.counts.completed} />
                <SubagentTaskList tasks={completed} variant="completed" />
                <SubagentLoadMore {...state.pagination} />
              </>
            ) : null}
          </div>
        </>
      )}
    </aside>
  );
}
```

### 5.3 ChatView 开合协调

```tsx
// ChatViewContent 中持有侧栏状态，入口不私藏右侧面板状态
const [fileSidebarOpen, setFileSidebarOpen] = useState(false);
const [subagentSidebarOpen, setSubagentSidebarOpen] = useState(false);
const subagentButtonRef = useRef<HTMLButtonElement>(null);

const toggleSubagentSidebar = () => {
  setSubagentSidebarOpen((current) => {
    const next = !current;
    if (next) setFileSidebarOpen(false);
    return next;
  });
};

const openFileSidebar = () => {
  setSubagentSidebarOpen(false);
  setFileSidebarOpen(true);
};

useEffect(() => {
  setSubagentSidebarOpen(false);
}, [activeThreadId]);

// 顶部右侧操作区
<SubagentButton
  open={subagentSidebarOpen}
  onToggle={toggleSubagentSidebar}
  buttonRef={subagentButtonRef}
  {...subagentSummary}
/>

// 与 <main> 同级；FileSidebar 与它必须互斥
<SubagentSidebar
  threadId={activeThreadId ?? ''}
  open={subagentSidebarOpen}
  onClose={() => {
    setSubagentSidebarOpen(false);
    requestAnimationFrame(() => subagentButtonRef.current?.focus());
  }}
  returnFocusRef={subagentButtonRef}
/>
```

---

## 6. 核心 CSS 示意

```css
.subagent-trigger {
  position: relative;
  display: inline-flex;
  align-items: center;
  height: 2rem;
  min-width: 2rem;
  gap: 0.375rem;
  padding: 0 0.4375rem;
  border: 1px solid transparent;
  border-radius: 0.55rem;
  background: transparent;
  color: var(--color-text-secondary);
  font: inherit;
  font-size: 0.75rem;
  cursor: pointer;
  transition: background var(--subagents-motion-fast) ease,
              color var(--subagents-motion-fast) ease;
}

.subagent-trigger:hover,
.subagent-trigger[data-open],
.subagent-trigger:focus-visible {
  background: var(--color-bg-surface);
  color: var(--color-text-primary);
}

.subagent-trigger:focus-visible,
.subagent-icon-button:focus-visible,
.subagent-load-more:focus-visible {
  outline: 2px solid var(--color-border-focus);
  outline-offset: 2px;
}

.subagent-trigger__icon { width: 0.95rem; height: 0.95rem; flex: 0 0 auto; }
.subagent-trigger__wide { display: inline-flex; align-items: center; gap: 0.375rem; }
.subagent-trigger__summary { white-space: nowrap; font-variant-numeric: tabular-nums; }
.subagent-trigger__dot {
  position: absolute;
  top: 0.25rem;
  right: 0.25rem;
  width: 0.375rem;
  height: 0.375rem;
  border-radius: 50%;
  background: var(--color-state-warning);
  box-shadow: 0 0 0 2px var(--color-bg-app);
}

.subagent-sidebar {
  width: 0;
  min-width: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-app);
  border-left: 0 solid var(--color-border-paper);
  transition: width var(--subagents-motion-panel) ease,
              min-width var(--subagents-motion-panel) ease;
}

.subagent-sidebar[data-open] {
  width: var(--subagents-sidebar-width);
  min-width: var(--subagents-sidebar-width);
  border-left-width: 1px;
}

.subagent-sidebar__header {
  position: sticky;
  top: 0;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 3.5rem;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--color-border-paper);
  background: var(--color-bg-app);
}

.subagent-sidebar__heading { display: flex; align-items: center; gap: 0.5rem; }
.subagent-sidebar__heading svg { width: 1.1rem; height: 1.1rem; color: var(--color-action-link); }
.subagent-sidebar__heading h2 { margin: 0; color: var(--color-text-primary); font-size: 1rem; font-weight: 600; }
.subagent-sidebar__content { flex: 1; min-height: 0; overflow-y: auto; padding: 0.75rem; }

.subagent-section-title {
  margin: 1.25rem 0 0.5rem;
  padding: 0 0.25rem;
  color: var(--color-text-secondary);
  font-size: 0.8125rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.subagent-section-title:first-child { margin-top: 0.25rem; }

.subagent-task-list { display: flex; flex-direction: column; gap: 0.375rem; margin: 0; padding: 0; list-style: none; }
.subagent-task-row {
  display: grid;
  grid-template-columns: 2rem minmax(0, 1fr);
  gap: 0.625rem;
  min-height: 4.25rem;
  padding: 0.625rem 0.75rem;
  border: 1px solid color-mix(in srgb, var(--color-border-paper) 66%, transparent);
  border-radius: 0.75rem;
  background: var(--color-bg-paper);
  animation: subagent-row-enter 160ms ease-out both;
}

.subagent-task-row__body { min-width: 0; }
.subagent-task-row__top { display: flex; align-items: baseline; gap: 0.5rem; }
.subagent-task-row__title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  color: var(--color-text-primary);
  font-size: 0.875rem;
  font-weight: 600;
  line-height: 1.3;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.subagent-task-row__duration {
  flex: 0 0 auto;
  color: var(--color-text-secondary);
  font-size: 0.75rem;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.subagent-task-row__summary {
  display: -webkit-box;
  margin: 0.25rem 0 0;
  overflow: hidden;
  color: var(--color-text-muted);
  font-size: 0.75rem;
  line-height: 1.45;
  overflow-wrap: anywhere;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

@keyframes subagent-row-enter {
  from { opacity: 0; transform: translateY(-3px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes subagent-live-pulse {
  0%, 100% { opacity: 0.72; transform: scale(0.92); }
  50% { opacity: 1; transform: scale(1); }
}
.subagent-status-dot--running {
  animation: subagent-live-pulse 900ms ease-in-out infinite;
}

@media (max-width: 860px) {
  .subagent-trigger__wide { display: none; }
  .subagent-sidebar[data-open] {
    position: absolute;
    inset-block: 0;
    right: 0;
    z-index: 41;
    width: min(var(--subagents-drawer-max-width), 100vw);
    min-width: min(var(--subagents-drawer-max-width), 100vw);
    box-shadow: -12px 0 32px var(--color-shadow-medium);
  }
}

@media (prefers-reduced-motion: reduce) {
  .subagent-trigger,
  .subagent-sidebar,
  .subagent-task-row,
  .subagent-status-dot--running {
    animation: none;
    transition: none;
  }
}
```

窄屏遮罩应作为 `SubagentSidebar` 的相邻元素，仅在 `open && isNarrow` 时渲染；其背景使用 `--color-bg-overlay`，点击调用 `onClose`。不要用 CSS 将 `aria-hidden` 内容留在键盘 Tab 顺序中。

---

## 7. 动效与反馈时序

| 动效 | 时长/曲线 | 触发 | 视觉结果 | 降级 |
| --- | --- | --- | --- | --- |
| A1 hover/open | 140ms ease | hover、focus、打开 | 背景和文字色柔和切换 | reduced motion 下即时切换 |
| B1 开合 | 250ms ease | A1、关闭、Esc | 桌面宽度从 0 到 20rem；窄屏从右侧进入 | reduced motion 下无位移/宽度动画 |
| 运行点呼吸 | 900ms ease-in-out 循环 | 存在 running | 0.92–1 倍缩放与透明度变化 | 保留静态警告色圆点 |
| 任务完成迁移 | 160ms ease-out | 更高 revision 的 completed | C2 原位移除；D2 顶部轻微淡入 | 即时更新，仍保证原子迁移 |
| 骨架柔光 | 1.4s linear 循环 | 首次水合 | 低对比水平渐变 | 显示静态灰块 |

动效不得驱动业务状态；任务是否完成只由权威数据决定。持续运行时长每 30 秒重算，但不得对数字使用跳动动画，也不得将 tick 放入 `aria-live`。

---

## 8. 国际化与可访问性规格

### 8.1 建议 i18n 键

```ts
chat: {
  subagents: {
    title: '子智能体',
    close: '关闭子智能体面板',
    active: '已开启',
    completed: '完成',
    noActive: '没有已开启的子智能体',
    emptyTitle: '此会话还没有子智能体任务',
    noSummary: '没有可用摘要',
    loading: '正在加载子智能体任务',
    loadMore: '加载更多',
    retry: '重试',
    stale: '任务信息可能不是最新',
    summaryRunning: '{{active}} 运行中 · {{completed}} 完成',
    summaryCompleted: '{{count}} 完成',
    status: { pending: '等待开始', running: '运行中', completed: '已完成' },
  },
}
```

- 英文需使用 i18next count plural 规则，不拼接硬编码单复数。
- A1：`button` + `aria-controls` + `aria-expanded`；A2 的可见装饰头像可 `aria-hidden`，数量合并进按钮 label。
- B1：`aside` + `aria-labelledby`；抽屉模式需 focus trap，关闭后返回 A1。
- C2/D2：`ul/li`；状态必须有文字，不能只靠颜色或动画。
- 完成事件只播报一次“{taskName} 已完成”，使用 `aria-live="polite"`；计时变化不播报。
- 所有点击目标不小于 32×32px，窄屏主要控制建议达到 40×40px。

---

## 9. 技能技术要求记录与生产实现决策

工作流模板指定了以下外部资源，适用于独立静态 HTML/Tailwind 原型：

- Font Awesome 6.0.0：`https://lf6-cdn-tos.bytecdntp.com/cdn/expire-100-M/font-awesome/6.0.0/css/all.min.css`
- Tailwind CSS 2.2.19：`https://lf3-cdn-tos.bytecdntp.com/cdn/expire-1-M/tailwindcss/2.2.19/tailwind.min.css`
- Google Fonts（Noto Serif SC / Noto Sans SC）：`https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;500;600;700&family=Noto+Sans+SC:wght@300;400;500;700&display=swap`

这些链接只作为技能要求记录，**不建议也不允许在现有 React 应用中实际引入**。当前项目已有 `Icons.tsx`、字体栈、主题 token 与组件样式体系；增加 CDN 会造成 CSP、离线可用性、加载性能和视觉一致性问题。

若需要制作与生产隔离的静态视觉原型，以下是 Tailwind 2.2.19 可识别的等价结构类示意；它不应复制到生产组件：

```html
<!-- 仅用于隔离原型；生产使用上文 React + 项目 CSS token 方案 -->
<aside class="w-80 flex-shrink-0 h-screen flex flex-col border-l bg-gray-900 border-gray-700 text-gray-100">
  <header class="h-14 px-4 flex items-center justify-between border-b border-gray-700">
    <div class="flex items-center space-x-2 font-semibold">
      <i class="fas fa-robot" aria-hidden="true"></i><span>子智能体</span>
    </div>
    <button class="w-8 h-8 rounded-lg hover:bg-gray-800" aria-label="关闭">×</button>
  </header>
  <div class="flex-1 overflow-y-auto p-3">
    <h3 class="mt-1 mb-2 text-sm text-gray-400">已开启</h3>
    <p class="mb-6 text-sm text-gray-500">没有已开启的子智能体</p>
    <h3 class="mb-2 text-sm text-gray-400">完成 · 23</h3>
    <ul class="space-y-2">
      <li class="flex items-start space-x-3 p-3 rounded-xl bg-gray-800">
        <span class="w-8 h-8 rounded-full bg-yellow-500 flex-shrink-0"></span>
        <div class="min-w-0 flex-1">
          <div class="flex items-baseline space-x-2">
            <strong class="truncate flex-1 text-sm">Task3 quality review</strong>
            <time class="text-xs text-gray-400 whitespace-nowrap">10 分</time>
          </div>
          <p class="mt-1 text-xs leading-relaxed text-gray-400 truncate">复审结论：PASS…</p>
        </div>
      </li>
    </ul>
  </div>
</aside>
```

---

## 10. 视觉验收清单

- [ ] A1 与 PlanButton 高度、圆角、hover 和焦点轮廓一致，不抢占主要操作视觉权重。
- [ ] A2 在桌面显示最近头像与真实数量；窄屏收起后 `aria-label` 仍包含完整状态。
- [ ] B1 桌面端与 FileSidebar 使用同一右侧槽位和开合节奏，绝不同时并排出现。
- [ ] B2 固定在顶部；内容区独立滚动；无横向溢出。
- [ ] 当前无运行但有 23 个完成任务时，准确显示 C3 与“D1 完成 · 23”，匹配参考图信息层级。
- [ ] D2 行内头像、标题、两行摘要和右侧耗时在 320px 宽度仍不互相覆盖。
- [ ] E1、E2、E3 互斥或按定义叠加，不出现“无任务”和任务列表同时展示。
- [ ] 亮色、显式暗色和系统暗色均只依赖 token；无新硬编码主题色。
- [ ] hover、running、completed 均有文字/形状语义，不只依赖颜色。
- [ ] reduced motion 下无循环动画且功能完整。
- [ ] 不加载 Font Awesome、Tailwind CDN 或 Google Fonts；生产图标来自 `Icons.tsx`。
