# 「子智能体任务」侧边栏入口与右侧详情面板 PRD 草案

## 1. 产品目标与范围

在现有聊天会话中补齐子智能体（subagent）执行记录的可见性。用户无需翻找消息或阅读原始工具事件，即可从 `PlanButton` 所在的顶部右侧操作区看到本会话是否运行过子智能体、最近涉及哪些代理、已完成多少项，并在点击后通过对话区右侧面板查看正在运行与已完成的具体任务。

本功能只展示当前会话的真实执行事实，不允许从 assistant 正文、任务标题关键字或前端计时器推测任务。首次打开、刷新页面、切换会话和 SSE 重连后，展示结果必须一致。

### 1.1 成功标准

- 有子智能体记录的会话显示入口；无记录的会话不占用顶部操作区。
- 运行中的任务能及时进入“已开启”分组，终态任务能及时移入“完成”分组。
- 页面刷新或重新进入历史会话后，任务数量、状态、摘要和耗时仍可恢复。
- 点击入口在聊天内容右侧打开详情面板；关闭、切换会话、打开文件侧栏时行为明确且无面板叠压。
- 中文、英文文案均通过现有 i18n；键盘、读屏和窄屏均可使用。

### 1.2 非目标

- 首期不提供创建、重试、取消或编辑子智能体任务的操作。
- 不展示子智能体完整思考过程、内部提示词、密钥、工作区绝对路径或未经脱敏的工具输入输出。
- 不创建独立路由或独立 Tailwind 页面；功能属于现有 `ChatViewContent` 的会话辅助面板。

---

## 2. 视觉输入的具体拆解

主图为深色任务详情页：顶部左侧是机器人线稿图标与“子智能体”标题；内容由“已开启”和“完成 · 23”两个纵向分组组成。“已开启”为空时直接显示“没有已开启的子代理”。完成任务以深一阶的圆角横条承载：左侧为彩色花形代理头像，中间第一行是 `Task3 quality review`，第二行是灰色长摘要，右侧对齐显示“10 分”。

辅图为入口元信息：深灰底上方显示“子智能体”，下方横向排列 4 个不同的彩色代理图标，图标后显示“23 完成”。入口表达的是“本会话最近代理 + 已完成数量 + 当前总体状态”，不是静态装饰。

适配当前应用时保留上述信息层级，但沿用项目已有 CSS 变量、字体、圆角、边框、暗色/亮色主题及内联样式/现有样式组织方式，不照搬截图的全屏尺寸。

---

## 3. 页面模块结构（自上而下、自左至右）

| 区块编号 | 所在位置 | 模块名 | 具体视觉与内容 | 功能定位 |
| --- | --- | --- | --- | --- |
| A1 | `ChatViewContent` 顶部右侧浮动操作区，紧邻现有 `PlanButton` | 子智能体入口按钮 | 约 2rem 高、圆角、透明底；使用 `Icons.tsx` 中新增的子智能体线稿图标；有运行任务时出现状态点 | 打开/关闭右侧详情面板，提供可访问名称与展开状态 |
| A2 | A1 的悬浮提示或扩展元信息 | 最近代理与汇总 | 最多 4 个小型彩色头像横向重叠/并排；其后显示“23 完成”或“2 运行中 · 23 完成” | 不打开面板也能快速判断执行规模与当前状态 |
| B1 | `ChatViewContent` 最右侧，复用 `FileSidebar` 的兄弟级 `<aside>` 布局 | 详情面板容器 | 打开时宽度建议 20–24rem，左侧细边框，应用背景色；关闭时宽度与 `min-width` 归零并过渡 | 不覆盖桌面端聊天正文，以现有右侧栏方式承载详情 |
| B2 | B1 顶部 | 面板标题栏 | 左侧机器人/子智能体图标 + “子智能体”；右侧关闭按钮 | 标识面板语义并关闭面板；标题栏在内容滚动时保持可见 |
| C1 | B2 下方第一组 | “已开启”分组标题 | 左侧“已开启”，可选右侧运行数量；文字使用次级色 | 聚合 `pending`/`running` 任务并提供实时状态概览 |
| C2 | C1 下方 | 已开启任务列表 | 每行包含代理头像、任务名、运行状态、摘要、已运行时长；运行态可使用轻量脉冲点，不使用持续旋转的大面积动效 | 展示当前正在执行的任务；按启动时间倒序 |
| C3 | C1 下方（列表为空时） | 已开启空状态 | 单行次级文字“没有已开启的子智能体” | 明确当前没有运行任务，但不误导为“从未有任务” |
| D1 | C2/C3 下方 | “完成 · N”分组标题 | “完成”后使用中点与真实完成数量，如“完成 · 23” | 告知本会话完成任务总量 |
| D2 | D1 下方 | 已完成任务列表 | 深浅主题自适应圆角行；左侧头像，中间标题与最多两行摘要，右侧显示格式化耗时；行间距紧凑 | 回看已完成任务，按结束时间倒序 |
| D3 | D2 列表末尾 | 分页/继续加载 | 仅当服务端返回 `nextCursor` 时显示“加载更多”；加载中显示局部骨架 | 防止大量历史任务一次性渲染拖慢会话 |
| E1 | B1 内容区 | 初次加载/刷新状态 | 头像、标题、摘要形状的 3–5 行骨架，不清空已有快照 | 避免闪烁并说明正在恢复真实数据 |
| E2 | B1 内容区 | 全局空状态 | 简洁机器人线稿 + “此会话还没有子智能体任务” | 区分“整个会话无任务”与“已开启分组为空” |
| E3 | B1 内容区 | 错误与离线状态 | 内联错误提示、“重试”按钮；若有旧快照则保留列表并标“可能不是最新” | REST/SSE 异常时保持信息可用，不伪造成功状态 |

---

## 4. 功能需求详述

### 4.1 入口按钮与元信息（A1–A2）

1. 入口仅在当前 `threadId` 存在且该会话至少有一条真实子智能体任务记录时渲染；快照加载期间不因短暂空值反复出现/消失。
2. 图标由 `frontend/src/components/chat/Icons.tsx` 提供统一 React SVG 组件，使用 `currentColor`，不得写死只适用于深色主题的描边色。
3. 默认紧凑形态与现有 `PlanButton`、新建、更多按钮同高；桌面宽度允许时可展示头像与汇总文字，窄宽度下只保留图标和运行状态点，完整信息放入 tooltip/`aria-label`。
4. 最近代理头像按最近活跃时间倒序去重，最多显示 4 个；超过 4 个时显示 `+N`。代理没有头像资源时，根据稳定的 `agentId` 或 `taskName` 生成确定性颜色与首字符/统一 glyph，刷新后不得变色。
5. 汇总文案规则：
   - 有运行任务：`{runningCount} 运行中 · {completedCount} 完成`；
   - 仅有完成任务：`{completedCount} 完成`；
   - 数字以服务端快照为准，不从当前已分页加载的列表长度计算。
6. 点击入口切换详情面板；入口设置 `aria-controls`、`aria-expanded`、本地化 `aria-label`。键盘 `Enter`/`Space` 与点击等价。
7. 有任务状态更新但面板未打开时，可显示与现有计划按钮一致的小圆点；打开面板后记录当前 `updatedAt` 为已读水位。已读状态仅影响提示点，不改变任务事实。

### 4.2 面板开合与会话联动（B1–B2）

1. 在 `ChatViewContent` 增加受控状态，例如 `subagentSidebarOpen`；入口组件通过回调改变该状态，不能把右侧面板开合状态私藏在按钮内部弹层中。
2. 新面板作为聊天 `<main>` 的兄弟节点挂载，复用 `FileSidebar` 的 `open`、`onClose`、宽度归零、左边框和开合动画模式；不复用文件上传、目录树等业务逻辑。
3. 文件侧栏与子智能体侧栏互斥：打开任意一个时关闭另一个，避免右侧同时占用 40rem 以上空间。切换当前会话时关闭面板并清除前一会话的临时选中/分页状态。
4. `Escape` 关闭面板；关闭按钮具备本地化可访问名称。打开后焦点移动到面板标题或第一个可操作元素，关闭后焦点返回入口按钮。
5. 桌面端使用推挤式侧栏；当可用宽度不足以同时保证聊天主区最低可读宽度时，切换为右侧抽屉覆盖模式（宽度 `min(22rem, 100vw)`），带半透明遮罩，点击遮罩可关闭。遵循 `prefers-reduced-motion` 关闭非必要过渡。
6. 面板列表独立纵向滚动，标题栏不随列表滚走；不能让整个 `ChatViewContent` 横向溢出。

### 4.3 已开启任务（C1–C3）

1. `pending` 和 `running` 映射到“已开启”分组；`pending` 显示“等待开始”，`running` 显示“运行中”。排序按 `startedAt`/`createdAt` 倒序。
2. 每条运行任务展示：代理头像、非空任务名、状态文本、可选实时摘要、从 `startedAt` 计算的“已运行时长”。计时只负责展示；刷新后必须重新以服务端时间戳计算，不能把前端计时结果写回事实状态。
3. 运行时长建议每 30 秒更新一次可见文本；标签页后台或面板关闭时暂停 UI interval，重新显示时即时重算。
4. 没有运行任务但存在完成记录时，保留分组和“没有已开启的子智能体”空文案，与参考图一致。

### 4.4 完成任务（D1–D3）

1. `completed` 进入“完成”分组；数量使用服务端 `counts.completed`。
2. 每条任务必须展示：
   - `taskName`：如 `Task3 quality review`，单行省略并提供完整 title；
   - `summary`：使用子智能体最终结果的脱敏摘要，最多两行，缺失时显示“没有可用摘要”；不得退回展示序列化 JSON；
   - `durationMs`：优先使用服务端值，否则仅在 `startedAt` 与 `finishedAt` 均合法时计算；如 `10 分`、`48 秒`、`1 小时 12 分`；
   - 代理身份：头像及本地化可读名称。
3. 完成列表按 `finishedAt` 倒序。新完成任务从“已开启”原位移出并出现在完成列表顶部，数量同一状态提交内更新，避免短暂重复或遗漏。
4. 首屏建议返回最近 50 条；更多记录使用 cursor 分页。分页失败只影响“加载更多”区域，不替换已有任务。
5. 任务行是可点击按钮；点击后在同一个右侧栏内从分组列表切换到单任务执行详情，并提供“返回任务列表”。键盘焦点、hover 与选中态必须明确。
6. 单任务详情展示任务名称、Agent 类型、状态、开始时间、耗时、委派深度、最新结果、错误和执行记录。执行记录只包含 Agent 可见更新、工具名、工具开始/完成/失败状态与时间，不返回 thinking、原始 prompt、工具入参、成功工具输出或内部绝对路径。
7. 桌面侧栏左边界提供可拖动分隔线，向左拖动扩大、向右拖动缩小；宽度必须受 viewport 与聊天区最小宽度约束并持久化。分隔线同时支持方向键、Home/End 和双击恢复默认宽度。
8. 详情栏使用清晰的系统无衬线操作字体，不继承聊天主界面的手写字体；Markdown 结果字号不得小于 15px，并保持标题、正文、元信息和时间线的层级差异。

### 4.5 空、加载、异常和乱序状态（E1–E3）

1. 首次快照加载成功且 `total === 0` 时显示全局空状态；不能同时显示“已开启空状态”和全局空状态。
2. SSE 先于 REST 返回时，先暂存增量事件；REST 快照到达后按 `revision`/`updatedAt` 合并，禁止旧快照覆盖新事件。
3. 重复事件以 `eventId` 或 `(taskId, revision)` 去重；单任务更新只接受更高 revision。终态不得被较旧的 running 事件回退。
4. SSE 断线时保留最后成功快照并显示非阻塞提示；连接恢复后重新拉取 REST 快照校准，不仅依赖漏失的增量事件。
5. 非法记录（缺少 `taskId`、状态未知、时间戳不可解析）不得导致面板崩溃；跳过非法行并记录可诊断日志。未知终态可归入错误监控，但首期不伪装成“完成”。

---

## 5. 状态与数据需求

### 5.1 前端标准化数据模型

```ts
type SubagentTaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

interface SubagentIdentity {
  agentId: string;
  displayName?: string | null;
  avatarUrl?: string | null;
  color?: string | null;
}

interface SubagentTask {
  taskId: string;
  threadId: string;
  parentTaskId?: string | null;
  taskName: string;
  summary?: string | null;
  status: SubagentTaskStatus;
  agent: SubagentIdentity;
  createdAt: string;
  startedAt?: string | null;
  finishedAt?: string | null;
  durationMs?: number | null;
  revision: number;
}

interface ThreadSubagentSnapshot {
  threadId: string;
  tasks: SubagentTask[];
  counts: {
    total: number;
    active: number;
    completed: number;
    failed: number;
    cancelled: number;
  };
  nextCursor?: string | null;
  updatedAt?: string | null;
  snapshotRevision: number;
}
```

`failed`、`cancelled` 在模型中保留，防止真实终态丢失；首期视觉至少保证运行中和已完成正确展示。若产品不新增独立异常分组，失败/取消记录应通过清晰状态标签进入“已结束”扩展分组，而不能计入 `completed`。该分组可作为实现时的兼容项，不改变参考图的“已开启 / 完成”主结构。

### 5.2 数据来源与接口建议

1. 增加线程级权威快照接口，例如：

   `GET /api/claude-agent/threads/{threadId}/subagent-tasks?limit=50&cursor=...`

   返回上面的 `ThreadSubagentSnapshot`；鉴权、用户/线程归属校验与现有 thread API 一致。
2. SSE 增加不进入消息气泡的生命周期帧，例如 `subagent-task-updated`，至少携带 `eventId`、`threadId`、完整任务记录、`counts`、`snapshotRevision`。前端 transport 应像 `plan-updated`、`todo-updated` 一样转发给专用 store，而不是映射成 `UIMessageChunk`。
3. 建议新增 `useThreadSubagents` store/hook，以 `threadId` 隔离缓存，暴露 `hydrateThreadSubagents(threadId)`、增量合并、分页、loading/error/connectionStale 等状态。`ChatView` 在线程状态水合时与 plan/todo 并行请求。
4. 如果 SDK 原始事件只提供任务开始与工具输出，后端适配层负责把它们归一为稳定 task lifecycle 并持久化。不能仅从当前 `tool-input-available` / `tool-output-available` 的临时 UI parts 拼装历史，因为现有历史消息或重连链路可能不保留完整中间事件，正是“最近对话未正确显示”的主要风险。
5. `summary` 应在子智能体终态时由执行结果的安全摘要字段提供；长度由服务端限制并脱敏。前端只负责截断显示，不负责解析一段自然语言来猜测总结。

### 5.3 状态映射表

| 服务端状态 | UI 分组 | 入口状态 | 行内文案 | 时长规则 |
| --- | --- | --- | --- | --- |
| `pending` | 已开启 | 运行中计数的一部分 | 等待开始 | 从 `createdAt` 显示等待时长，或不显示 |
| `running` | 已开启 | 显示运行提示点及数量 | 运行中 | `now - startedAt` |
| `completed` | 完成 | 增加完成数量 | 已完成 | `durationMs`，或 `finishedAt - startedAt` |
| `failed` | 已结束（兼容扩展） | 不计入完成 | 失败 | 同终态规则，可显示安全错误摘要 |
| `cancelled` | 已结束（兼容扩展） | 不计入完成 | 已取消 | 同终态规则 |

---

## 6. 技术实现建议（适配现有 React 应用）

### 6.1 推荐组件边界

- `frontend/src/components/chat/Icons.tsx`
  - 新增可复用的 `IconSubagents`，SVG 使用 `currentColor`、统一 `viewBox` 与 `SVGProps` 约定。
- `frontend/src/components/chat/SubagentPanel.tsx`（建议新增）
  - `SubagentButton`：只处理入口呈现、tooltip、未读点、聚合元信息与触发回调。
  - `SubagentSidebar`：接收 `threadId/open/onClose`，渲染标题、分组、列表、空态及分页。
  - `SubagentTaskRow`、`SubagentAvatarStack`、`formatDuration`：保持纯展示/纯函数，便于单测。
- `frontend/src/hooks/useThreadSubagents.ts`（建议新增）
  - 负责按线程缓存、REST 水合、SSE 增量归并、版本防回退、错误和分页状态。
- `frontend/src/lib/claude-agent-transport.ts`
  - 声明并接收 `subagent-task-updated`；转发到 store 后返回空 chunk，确保不会产生错误消息气泡。
- `frontend/src/components/chat/ChatView.tsx`
  - 持有 `subagentSidebarOpen`；渲染入口和根级右侧面板；协调与 `fileSidebarOpen` 互斥；线程切换时触发水合与复位。
- `frontend/src/i18n.ts`
  - 增加 `chat.subagents.*` 的中英文文案、数量复数和耗时单位，避免 JSX 内硬编码中文。

### 6.2 样式与主题

- 使用现有 `--color-bg-app`、`--color-bg-surface`、`--color-bg-paper`、`--color-border-paper`、`--color-text-primary/secondary/muted`、`--color-shadow-medium` 等 token。
- 任务行建议 10–12px 圆角、8–12px 内边距；标题与耗时同一基线，摘要使用次级色和 1.45–1.6 行高。亮色主题不能出现“黑底黑字”，暗色主题不能用低对比灰字。
- 头像图案可使用已有代理头像 URL；fallback 只生成简单几何/字形，不复制截图中的品牌化花朵资产。
- 不引入 Tailwind 依赖或独立页面级 CSS 框架；可沿用当前内联样式，若交互状态过多则创建与组件同目录的局部 CSS 文件并继续使用设计 token。

### 6.3 性能与一致性

- store 选择器只订阅当前线程及必要聚合值，避免任一 task tick 导致整个 `ChatView` 重渲染。
- 时长 interval 只在面板可见且存在运行任务时启用，所有行共享一个 `now`，不得每行各建 timer。
- 头像列表按 `agentId` 去重并 memoize；已完成列表分页，稳定使用 `taskId` 作为 React key。
- 线程切换请求使用 AbortController 或 request sequence，迟到的旧线程响应不得写入当前线程视图。

### 6.4 安全、隐私与审计

- API 必须校验调用者对 thread 的读取权限；禁止仅凭 `threadId` 越权读取他人的 agent 记录。
- `summary`、错误内容和代理名称在进入 SSE/REST 前完成敏感信息脱敏；前端以普通文本渲染，不使用 `dangerouslySetInnerHTML`。
- 日志只记录 `threadId/taskId/eventId/status/revision` 等诊断字段，不记录子智能体全文输出。

---

## 7. 国际化、可访问性与响应式要求

- 所有可见文案、tooltip、`aria-label`、状态和耗时格式均从 i18n 获取；数字/时间使用当前语言 locale。
- 分组使用语义化标题；任务列表使用 `<ul>/<li>`。入口为 `<button>`，右侧面板使用带 `aria-labelledby` 的 `<aside>`。
- 实时完成更新通过面板内 `aria-live="polite"` 简短播报“任务 X 已完成”，不得把持续计时变化放入 live region。
- 文本与背景满足 WCAG AA；仅靠颜色不可区分 running/completed，必须同时提供文本或图形状态。
- `:focus-visible` 清晰可见；关闭面板后焦点恢复；抽屉模式开启时焦点限制在面板内。
- 320px 宽度下入口文字可收起，面板占满可用宽度，任务标题/摘要允许截断但耗时不得挤出视口。

---

## 8. 验收场景

1. 当前会话无子智能体记录：顶部无入口；不会因 plan/todo 存在而误显示。
2. 启动 1 个子智能体：入口出现“1 运行中”，面板“已开启”出现任务行，完成分组数量不提前增加。
3. 同时运行多个不同代理：入口最多显示 4 个最近代理头像，数量与已开启列表一致。
4. 任务完成：该行只出现一次，从“已开启”移到“完成”顶部，摘要和耗时来自服务端事实，`完成 · N` 原子增加。
5. 已完成 23 项且无运行项：面板显示“没有已开启的子智能体”和“完成 · 23”；入口显示最近头像与“23 完成”，与参考图一致。
6. 刷新包含历史任务的会话：REST 水合后还原相同任务、数量、摘要、耗时；不要求重新执行任务。
7. SSE 重复、乱序或短暂断线：列表无重复，completed 不回退为 running；重连快照完成校准。
8. 在任务面板打开时打开文件侧栏：任务面板先关闭，文件侧栏打开；反向操作同理。
9. 切换线程：旧线程任务不闪现在新线程，面板关闭；返回旧线程后可从缓存/快照恢复。
10. REST 失败：有缓存时保留内容并标注可能过期，无缓存时显示错误和重试；应用其余聊天功能保持可用。
11. 键盘操作：可打开、浏览、加载更多并用 Escape 关闭；焦点返回入口；读屏可获知标题、状态与数量。
12. 中英文、亮暗主题和窄屏下均无硬编码溢出、低对比或不可见按钮。

---

## 9. 待产品/后端确认项

- 上游子智能体运行时可稳定提供哪些身份字段（`agentId/displayName/avatarUrl`）以及最终摘要字段。
- 历史执行记录当前是否已有可查询的持久化来源；若没有，必须先补持久化与线程归属查询，前端展示不能只依赖当前 SSE 内存态。
- `failed`、`cancelled` 是否在首期增加“已结束”分组；无论视觉是否首期展示，都不得计入“完成”。
- 完成记录的默认保留周期与最大数量，以确定分页和归档策略。
