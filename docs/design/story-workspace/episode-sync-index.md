<!-- [Input] Run-scoped Episode registry, successful Dream Hook publication, Episode artifact/index read models, and Execution route state. -->
<!-- [Output] Product and interaction contract for the Dream synchronization Episode index, per-Episode artifact page, and return navigation. -->
<!-- [Pos] Story Workspace Episode synchronization planning and implementation source of truth. -->
<!-- [Sync] 2026-09-02: define index-first synchronization, stable Episode selection, deterministic registry catch-up, per-Episode data isolation, and ambiguity-free titles. -->

# 剧本产物同步：Episode 索引与产物页

## 1. 背景与问题

Dream Execution 的“同步”视图目前直接渲染 Run 返回的单个 active Episode。页面没有 Episode
索引，路由也没有 Episode 选择，因此用户无法确认当前有哪些 Episode、正在读取哪一集，或从
产物页返回 Episode 列表。

现有后端已经持有 Run-scoped Episode registry，但生产 Hook 只保证 EP01 关联；前端 Episode
Artifact 请求、ETag 和 last-known-good cache 也只以 Run ID 隔离。于是同一 Run 新增 EP02 后，
canonical EP02 文件、registry active Episode、页面选择和缓存可能不一致。EP02 暂无产物时，
页面还可能继续显示此前 Run 级缓存中的 EP01。初稿 Outline 的 storyboard 条目标题来自
`EPxx 分镜` 数据映射，也把 Episode 容器误写成单一产物类型。

## 2. 目标与边界

### 目标

1. “同步”默认先显示 Run 内已注册 Episode 的索引。
2. 选择 Episode 后，路由、请求、缓存、标题、状态和产物使用同一个稳定 Episode UID。
3. EP02 暂无产物时显示 EP02 的真实空态，不回退到 EP01。
4. 产物页顶部提供可键盘操作的返回入口，回到同一 Run 的 Episode 索引。
5. 初稿 Outline 的 Episode 条目标题显示 `EPxx`，不再显示 `EPxx 分镜`。

### 边界

- 保持现有 Dream Run、共享 Thread、Claude session、SSE、turn、resume、cancel、确认和
  successful after-turn Hook 语义。
- 不新增数据库表、migration、runtime DDL、SQLite fallback、消息队列或 Agent 控制通道。
- Episode 索引和产物查询都是 actor-scoped 只读接口；选择 Episode 不修改 registry active
  Episode，也不启动 Agent turn。
- 不恢复已经删除的推荐动作、阶段按钮、completion fact 或 Episode 工作流状态机。

## 3. 用户场景

1. 用户完成 EP01 后开启 EP02 创作；进入同步视图先看到 EP01、EP02 两条索引项，EP02 标记为
   当前执行或暂无产物，而不是继续进入 EP01。
2. 用户选择 EP02，页面标题、状态、空态和全部产物只来自 EP02。
3. 用户从 EP02 产物页返回索引，再进入 EP01；页面只显示 EP01，证明选择不是把默认值改成
   EP02。
4. 用户通过浏览器前进/后退恢复同一 Run 的索引或指定 Episode，不创建新任务。
5. 用户在初稿 Outline 看到 `EP01`、`EP02`，点击后仍进入现有聚焦阅读层。

## 4. 概念与产品规则

| 概念 | 规则 |
|---|---|
| Episode registry | Run 内 Episode 身份的唯一索引真相；不得按目录或数组首项在页面推断身份。 |
| Episode UID | 服务端生成的稳定身份，只用于 React key、路由查询和 API 参数，不在页面展示。 |
| Episode code | 用户可见编号，如 EP01、EP02；来自 registry，不由前端计数生成。 |
| Active Episode | successful Hook 根据本轮唯一变更 Episode，或在无 Episode 文件变化时唯一新发现的 registry 成员，更新 Run 事实；只用于“当前执行”提示，不强迫页面进入该 Episode。 |
| Selected Episode | Execution URL 中的稳定 UID；只控制当前页面读取，不写 registry。URL 无该参数时表示索引页。 |
| Has artifacts | allowlist Episode 产物中至少一项可读；不等于 Episode 完成。 |
| Episode title | Episode 容器标题始终为 `EPxx`；可靠的 Episode 名称存在时可作为次级文本，不替换容器身份。 |
| Last-known-good | 只能在同一 Run + 同一 Episode UID 内保留；不得跨 Episode 合并。 |

successful Hook 只把 canonical 工作台中已经存在、编号连续且不超过 `project.yaml` 计划总集数的
Episode 写入 registry。本轮若恰好只有一个仍然存在的 Episode 的 allowlist 文件发生变化，则将
该 Episode 设为 active；若没有 Episode 文件变化、但 registry 恰好补注册一个已经存在的连续
canonical Episode，则将这个唯一新成员设为 active。多 Episode 同时变化、同时新发现多个成员或
身份存在其他多义性时保留原 active，避免按列表位置或消息文本猜测用户意图。

## 5. 信息架构

```text
Execution（同一 Run）
└── 同步
    ├── Episode 索引（URL 无 episode 参数）
    │   ├── EP01 · 状态 · 产物可用性
    │   ├── EP02 · 状态 · 产物可用性
    │   └── EP03 · 状态 · 产物可用性
    └── Episode 产物页（URL 带稳定 episode UID）
        ├── 返回 Episode 索引
        ├── EPxx 容器标题与可选名称
        ├── 同步/读取状态
        └── 现有故事线、场景、镜头、辅助产物与审阅工作面
```

Episode 索引复用初稿 Outline 的 manuscript 列表层级、行间距、箭头、键盘上下移动和聚焦样式。
它不是全局侧栏、标签页或新的导航体系。

## 6. 页面状态

| 状态 | 页面表现 | 允许操作 |
|---|---|---|
| Episode 索引页 | 显示 registry 顺序中的全部 Episode；每项显示编号、当前状态和是否有产物。 | 选择任一 Episode；上下方向键移动焦点。 |
| Episode 执行中 | active Episode 且 Run 尚未结束，显示“执行中”；已有产物仍可进入查看。 | 查看当前已到达产物、返回索引。 |
| Episode 已完成并有产物 | 显示“已有产物”；产物页读取该 Episode 的完整 surface。 | 查看、切换叙事条目、返回索引。 |
| Episode 暂无产物 | 显示所选 `EPxx` 和“暂无产物”；不得渲染其他 Episode 内容。 | 返回索引；无需确认弹窗。 |
| Episode 加载失败 | 保留所选 `EPxx` 身份，显示“暂时无法读取”；同 Episode 有 LKG 时明确说明正在显示该集的最近有效内容。 | 重试、返回索引。 |
| Episode 不存在或已失效 | URL UID 不属于当前 Run registry，显示“当前 Episode 不存在或已失效”。 | 返回索引；不选择数组首项。 |
| 从产物页返回索引 | 移除 URL 的 episode 参数，Run ID 与 Execution 上下文不变，焦点返回刚才的 Episode 行。 | 再次选择 EP01/EP02。 |
| 启动 EP02 后 | Hook 将 EP02 注册，并在单集变更或唯一 registry 补注册时设为 active；索引显示 EP02，选择后只请求 EP02。 | EP01、EP02 均可独立进入。 |

索引整体加载失败时显示一个页面级失败状态和“重试”按钮；不得用最近一次 Run 的索引或仅有的
artifact surface 拼出替代列表。

## 7. 交互流程

1. 用户在 Dream Agent 标题栏选择“同步”。
2. 页面读取当前 Run 的 Episode index；URL 没有 `episode` 参数，因此渲染索引。
3. 用户点击或按 Enter/Space 激活 EP02 行。
4. Router 在同一路径写入 `?episode=<opaque-uid>`，不改变 Run、Thread 或任务。
5. Artifact Hook 用 `runId + episodeUid` 建立请求 identity，清空其他 Episode 的 ETag/LKG，读取
   EP02 surface。
6. 页面据实渲染 EP02 的有产物、无产物、执行中或失败状态。
7. 用户激活顶部“返回 Episode 索引”，Router 删除 `episode` 参数并将焦点恢复到 EP02 行。

## 8. 数据来源和 Episode 选择规则

| 页面事实 | 来源 | 选择/隔离规则 |
|---|---|---|
| Episode 列表、code、active、registry revision | actor-scoped Run Episode index read model | 按 registry 顺序；不目录扫描、不首项兜底。 |
| 是否有产物、问题、更新时间 | 每个 registry Episode 的 allowlist manifest facts | 只计该 Episode；不把“有任一产物”等同完成。 |
| 当前 Run 执行状态 | 现有 Workflow Run | 只给 active Episode 提供“执行中”提示。 |
| Selected Episode | Execution 路由 `episode` 查询参数 | 必须属于当前 index；不存在则进入失效态。 |
| Episode 产物 | `episode-artifacts?episode=<uid>` | 服务端验证 actor、Run、registry membership；响应必须回显相同 UID。 |
| 初稿 Episode 列表 | 现有 Dream storyboard stage projection | 标题用动态 `entityId`/Episode code；阅读器按匹配 Episode UID 请求。 |

API 继续使用现有 Run actor/provenance 校验。新增的 index 是直接相关的只读 read model；artifact
接口只增加 registry-member Episode 选择参数，不提供 activate、restart、kill 或派发能力。

## 9. 异常与空状态

- registry 尚未建立：显示“Episode 尚未同步”，持续按现有刷新机制重试，不构造 EP01。
- registry 已建立但无所选 UID：显示失效态，不跳到 active Episode。
- 所选 Episode 六项产物均 `not_generated`：显示该 `EPxx` 的暂无产物状态。
- 单项 `invalid/unavailable`：只影响该 Episode 的对应模块；同 Episode 的其他模块继续显示。
- 网络失败且同 Episode 有 LKG：可显示同 Episode LKG；若 LKG 属于别的 UID，必须丢弃。
- Hook 发现 Episode 编号不连续、超过计划总集数或 registry 身份冲突：fail closed，不修改
  registry，不让页面宣称新 Episode 已同步。

## 10. 可访问性要求

- Episode 索引使用可命名区域和有序列表；每行是原生 `button`，可由 Tab、Enter、Space 操作。
- 复用 Outline 的 ArrowUp/ArrowDown 同级焦点移动；不拦截其他键。
- 每行 accessible name 同时包含 Episode code、状态和产物可用性。
- 返回入口使用原生 `button` 或 SPA link，名称为“返回 Episode 索引”，具备可见 `:focus-visible`。
- 路由进入产物页后把焦点移动到 Episode h2；返回后恢复到原 Episode 行。
- 加载、执行、失败和 LKG 提示使用恰当的 `role=status` / `aria-live=polite`，避免重复播报。
- 窄屏保持单列列表和同一语义顺序，不出现横向页面溢出。

## 11. 验收标准

1. 同步视图首次进入显示 Episode 索引，不直接显示 active Episode 产物。
2. 索引从真实 registry 渲染 EP01、EP02，二者 UID/key 不同且顺序稳定。
3. 选择 EP02 后 URL、请求、响应 identity、标题、状态和产物均为 EP02。
4. EP02 无产物或失败时不出现 EP01 标题、正文、镜头或 LKG。
5. 返回索引不改变 Run/Thread，不创建任务；焦点回到 EP02。
6. 再进入 EP01 正确显示 EP01，浏览器前进/后退可恢复选择。
7. 初稿 Outline 标题为动态 `EPxx`，不再出现 `EPxx 分镜`。
8. 键盘操作、accessible name、焦点可见性和 390px 窄屏无横向溢出通过。
9. 普通 Dream turn、SSE、resume、cancel、确认、reader 和 Story Index 回归通过。

## 12. 不做什么

- 不增加 Episode 搜索、筛选、排序、批量操作、分页或拖拽。
- 不增加确认弹窗、手动“同步/构建关联”按钮或自动进入 active Episode。
- 不展示 Run ID、Episode UID、revision、内部路径、缓存键或 Hook 技术说明。
- 不恢复推荐动作矩阵、下一步按钮、专用派发器或 completion state machine。
- 不修改 Admin schema、订阅、Gateway、Runner、ThreadFactory、EventBus 或 SSE 协议。
- 不把 Project 标题、Storyboard 标题或数组位置当作 Episode 身份。

## 13. 编码前设计评审

### 目标覆盖

| 问题 | 设计中的直接处理 | 结论 |
|---|---|---|
| 不知道有哪些 Episode | 默认 index-only 页面读取 registry | 保留 |
| EP02 显示 EP01 | Router、request、response、ETag、LKG 共用 Run + Episode UID | 保留并设为测试门禁 |
| 无法返回上层 | 删除 `episode` 参数，保留 Run 路径并恢复焦点 | 保留 |
| `EPxx 分镜` 歧义 | 通用 storyboard Episode 映射改为 `EPxx` | 保留 |
| EP02 任务未关联 | successful Hook 只同步真实、连续、计划内 Episode；唯一变更或唯一补注册才更新 active | 保留，禁止消息文本猜测 |

### 已删除的过度设计

- 不为索引增加搜索、筛选、进度条、更新时间强制展示或 Episode 名称占位；只有数据真实存在且
  对决策有用时才显示更新时间/名称。
- 不增加“切换 active Episode”的写接口；页面选择是纯路由状态，Hook active 是成功业务事实。
- 不把六项 artifact 全部可用定义为“Episode 完成”，避免创建新的 completion 状态机。
- 不增加新的全局导航、左侧栏、标签页、弹窗或二次确认。
- 不恢复历史推荐动作矩阵，不解析用户消息中的 `EP02` 来决定身份。

### 实现门禁

1. Episode UID 必须来自 registry，并在 index、URL、API、response 和 cache 中逐项相等。
2. index endpoint 只读 artifact metadata/allowlist facts，不为列表解析或加载完整正文。
3. 选择无效 UID 返回明确失效态；任何 `episodes[0]` 回退均视为缺陷。
4. Hook 发现编号空洞、计划上限冲突、registry CAS 冲突、多 Episode 同时变化或同时补注册多个
   Episode 时 fail closed 或保留原 active，不猜测。
5. 组件只复用/提取现有 Outline manuscript 模式；不得复制一套近似样式。
