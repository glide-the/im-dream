# 「子智能体任务」层级与交互逻辑

## 1. 精炼页面结构图（模块分区）

```text
┌────────────────────────────── ChatViewContent / 当前 threadId ──────────────────────────────┐
│                                                                                              │
│  ┌────────────────────────────── 对话主区 <main> ──────────────────────────┐                 │
│  │                                                                        │                 │
│  │  顶部右侧操作区                                                        │                 │
│  │  [新建] [PlanButton] ┌───────────── A1 ─────────────┐ [更多]           │                 │
│  │                      │ [◎] A2[✿][◆][◉] 2运行·23完成 │                  │                 │
│  │                      └──────────────┬───────────────┘                  │                 │
│  │                                     │ 用户点击                          │                 │
│  │                                     └──────────────────────┐           │                 │
│  │                                                            │           │                 │
│  │                   当前会话消息流                           │           │                 │
│  │                                                            │           │                 │
│  └────────────────────────────────────────────────────────────┼───────────┘                 │
│                                                               ▼                             │
│                                                ┌────────────── B1 ──────────────┐            │
│                                                │ 右侧 SubagentSidebar <aside>   │            │
│                                                │ ┌────────── B2 ──────────────┐│            │
│                                                │ │ ◎ 子智能体             [×]││            │
│                                                │ └───────────────────────────┘│            │
│                                                │ ┌────────── C1 ──────────────┐│            │
│                                                │ │ 已开启 · activeCount       ││            │
│                                                │ └───────────────────────────┘│            │
│                                                │ ┌──── C2 或 C3（互斥）──────┐│            │
│                                                │ │ C2 运行任务列表            ││            │
│                                                │ │ 头像｜标题｜状态｜摘要｜时长││            │
│                                                │ │             或             ││            │
│                                                │ │ C3 没有已开启的子智能体    ││            │
│                                                │ └───────────────────────────┘│            │
│                                                │ ┌────────── D1 ──────────────┐│            │
│                                                │ │ 完成 · completedCount      ││            │
│                                                │ └───────────────────────────┘│            │
│                                                │ ┌────────── D2 ──────────────┐│            │
│                                                │ │ 完成任务列表                ││            │
│                                                │ │ ✿ Task3 quality review 10分││            │
│                                                │ │   复审结论：PASS…          ││            │
│                                                │ └───────────────────────────┘│            │
│                                                │ ┌────────── D3 ──────────────┐│            │
│                                                │ │ [加载更多] / 分页局部骨架  ││            │
│                                                │ └───────────────────────────┘│            │
│                                                └───────────────────────────────┘            │
│                                                                                              │
│  B1 内容替换状态：E1 首次加载骨架 ｜ E2 全局无任务 ｜ E3 错误/离线提示                      │
│  右侧槽位排他规则：B1 打开 ⇄ FileSidebar 关闭；FileSidebar 打开 ⇄ B1 关闭                  │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

布局逻辑：`A1/A2` 是会话级摘要入口，`B1` 是详情承载容器，`C*` 与 `D*` 是按生命周期分组的业务内容，`E*` 是同一内容槽的系统状态。详情不是独立页面，也不嵌在聊天消息气泡中。

`B1` 左边界同时是可访问 resize separator：Pointer 向左移动增加侧栏宽度，向右移动减少；`ArrowLeft`/`ArrowRight` 每次调整 16px，Shift 调整 32px，Home/End 跳到当前 viewport 允许的最小/最大值，双击恢复 480px。拖动期间禁用宽度 transition 与正文选中，结束后恢复并持久化宽度。

---

## 2. 页面父子层级逻辑树

```text
Root：ChatViewContent（当前聊天会话）
│
├── 对话主区 <main>
│   │
│   └── 顶部右侧浮动操作区
│       │
│       └── A1 子智能体入口按钮（用户操作：打开 / 关闭 B1）
│           │
│           ├── 子智能体线稿图标
│           ├── 运行或未读状态点
│           └── A2 最近代理与汇总（入口的渐进增强信息）
│               ├── 最近代理头像栈：按最近活跃时间倒序去重，最多 4 个
│               ├── activeCount：显示“运行中”
│               └── completedCount：显示“完成”
│
└── 右侧辅助槽位（FileSidebar / SubagentSidebar 二选一）
    │
    └── B1 SubagentSidebar（用户操作：Esc、遮罩或关闭按钮收起）
        │
        ├── B2 固定标题栏
        │   ├── 图标 + 本地化标题“子智能体”
        │   └── 关闭按钮（关闭后焦点回到 A1）
        │
        └── 可滚动内容槽
            │
            ├── 正常数据分支（snapshot.counts.total > 0）
            │   │
            │   ├── C1 已开启分组标题
            │   │   └── 数据：counts.active
            │   │
            │   ├── C2 已开启任务列表（counts.active > 0）
            │   │   ├── 数据筛选：status ∈ {pending, running}
            │   │   ├── 排序：startedAt ?? createdAt 倒序
            │   │   └── 行信息：agent、taskName、status、summary、运行时长
            │   │
            │   ├── C3 已开启空状态（counts.active = 0；与 C2 互斥）
            │   │   └── 意图：说明“当前无运行任务”，不等于“从未运行任务”
            │   │
            │   ├── D1 完成分组标题
            │   │   └── 数据：counts.completed（不可用当前分页数组长度替代）
            │   │
            │   ├── D2 已完成任务列表
            │   │   ├── 数据筛选：status = completed
            │   │   ├── 排序：finishedAt 倒序
            │   │   └── 行信息：agent、taskName、脱敏 summary、durationMs
            │   │
            │   └── D3 加载更多（nextCursor 存在）
            │       ├── 用户操作：请求下一页
            │       └── 失败边界：只显示局部失败，不清空 D2
            │
            ├── E1 首次加载分支
            │   └── 条件：loading = true 且无可用快照；替换 C1–D3
            │
            ├── E2 全局空分支
            │   └── 条件：REST 成功且 counts.total = 0；替换 C1–D3
            │
            └── E3 错误 / 离线分支
                ├── 无缓存：错误说明 + 重试，替换 C1–D3
                └── 有缓存：作为列表上方提示，保留最后成功内容
```

---

## 3. 用户操作与界面状态关系

```text
[会话被选中]
      │
      ├── hydrate(threadId) ───────────────────────────────────────────────┐
      │                                                                  │
      ▼                                                                  │
是否存在子智能体任务？                                                    │
  │                                                                      │
  ├── 否 ──> A1 不渲染；B1 保持关闭                                      │
  │                                                                      │
  └── 是 ──> 显示 A1 + A2                                                │
                 │                                                       │
                 ├── 点击 / Enter / Space                               │
                 │        │                                              │
                 │        ├── 关闭 FileSidebar                           │
                 │        ├── 打开 B1                                    │
                 │        ├── 标记 updatedAt 已读                        │
                 │        └── 焦点进入 B2                                │
                 │                                                       │
                 └── B1 打开后                                           │
                          │                                               │
                          ├── active > 0 ──> C1 + C2                     │
                          ├── active = 0 ──> C1 + C3                     │
                          ├── completed > 0 ──> D1 + D2 (+ D3)           │
                          └── 点击 × / Esc / 遮罩 ──> 关闭 B1，焦点返 A1 │
```

### 3.1 任务生命周期引起的界面迁移

```text
服务端 pending / running 任务 T
          │
          ├── A2.activeCount +1
          ├── T 位于 C2
          └── 运行时长 = now - startedAt（仅展示计算）

任务 T 收到更高 revision 的 completed
          │
          ├── 从 C2 移除 T
          ├── 在 D2 顶部插入 T
          ├── A2.activeCount -1
          ├── A2.completedCount +1；D1 同步更新
          ├── 时长 = durationMs，缺失时 finishedAt - startedAt
          └── 面板关闭时点亮 A1 未读提示；面板打开时 polite 播报
```

迁移必须作为一次一致的 store 更新完成；不允许同一任务短暂同时出现在 `C2` 与 `D2`，也不允许已完成任务被乱序旧事件推回运行中。

---

## 4. 数据层级与模块消费关系

```text
后端权威事实
│
├── REST 快照
│   GET /threads/{threadId}/subagent-tasks
│   └── ThreadSubagentSnapshot
│       ├── tasks[]
│       ├── counts{ total, active, completed, failed, cancelled }
│       ├── nextCursor
│       └── snapshotRevision / updatedAt
│
└── SSE 增量
    subagent-task-updated
    └── eventId + task + counts + snapshotRevision
             │
             ▼
useThreadSubagents(threadId) / 专用线程级 Store
│
├── 合并规则
│   ├── eventId 或 (taskId, revision) 去重
│   ├── 只接受更高 revision
│   ├── 终态不被旧 running 回退
│   └── SSE 重连后用 REST 再校准
│
├── 入口选择器 ───────────────────────> A1 / A2
│   └── visible、recentAgents、activeCount、completedCount、hasUnseenUpdate
│
├── 内容选择器 ───────────────────────> C1 / C2 / C3 / D1 / D2
│   └── activeTasks、completedTasks、counts、updatedAt
│
├── 分页状态 ─────────────────────────> D3
│   └── nextCursor、loadingMore、loadMoreError
│
└── 请求状态 ─────────────────────────> E1 / E2 / E3
    └── loading、hasSnapshot、error、connectionStale
```

### 4.1 数据字段到可见信息的映射

| 数据字段 | 消费模块 | 展示/逻辑用途 | 约束 |
| --- | --- | --- | --- |
| `threadId` | Root、B1、Store | 隔离当前会话任务 | 迟到的旧线程响应不得写入当前视图 |
| `taskId` | C2、D2 | React key、事件去重 | 必须稳定且非空 |
| `agent.agentId/displayName/avatarUrl/color` | A2、C2、D2 | 最近头像、行内代理身份 | fallback 颜色应稳定；不泄露内部标识 |
| `taskName` | C2、D2 | 任务标题 | 单行省略，完整文本可访问 |
| `summary` | C2、D2 | 运行摘要或最终结果摘要 | 服务端脱敏；最多两行；纯文本渲染 |
| `status` | A2、C2、C3、D2 | 分组、数量与状态文案 | `completed` 才计入完成；未知状态不伪装完成 |
| `startedAt/finishedAt/durationMs` | C2、D2 | 运行时长与终态耗时 | 优先服务端 `durationMs`；非法时间显示占位 |
| `counts.*` | A2、C1、D1、E2 | 汇总与分支条件 | 使用服务端全量计数，不从分页列表推算 |
| `nextCursor` | D3 | 是否允许继续加载 | 无 cursor 时不显示按钮 |
| `revision/snapshotRevision/eventId` | Store | 去重、防回退和校准 | 不直接展示给用户 |

---

## 5. 响应式与焦点层级

```text
桌面宽屏
Root flex row
├── main：flex:1 / min-width:0
└── B1：20–24rem 推挤式侧栏

窄屏
Root relative
├── main：保持原宽度
├── 遮罩：点击关闭 B1
└── B1：position:absolute/fixed；right:0；width:min(22rem,100vw)
    └── 焦点限制：B2 标题/关闭按钮 → 内容交互 → D3
```

- `A2` 在空间不足时收起为 `A1` 图标与状态点，信息保留在本地化 tooltip 与 `aria-label`。
- 面板打开时，`aria-expanded=true`、`aria-controls` 指向 `B1`；关闭时焦点返回 `A1`。
- `B2` 固定，`C1–E3` 所在内容槽滚动；聊天消息区与面板不共享滚动容器。
- `prefers-reduced-motion` 下关闭宽度/位移动画，状态仍通过文本表达。

---

## 6. 模块逻辑索引

| ID | 层级角色 | 父级 | 主要用户操作 | 状态/数据依赖 | 与其他模块关系 |
| --- | --- | --- | --- | --- | --- |
| A1 | 入口控制 | 顶部右侧操作区 | 打开/关闭面板 | `total`、`hasUnseenUpdate`、`open` | 控制 B1；关闭后接回焦点 |
| A2 | 摘要信息 | A1 | 无独立操作 | recentAgents、activeCount、completedCount | 为 A1 提供不开面板的概览 |
| B1 | 详情容器 | Root 右侧辅助槽 | Esc/遮罩关闭 | `open`、响应式断点 | 与 FileSidebar 互斥；承载 B2–E3 |
| B2 | 标题与关闭 | B1 | 关闭面板 | 本地化标题、焦点状态 | 固定在 B1 顶部 |
| C1 | 运行分组标题 | B1 内容槽 | 无 | counts.active | 控制 C2/C3 语境 |
| C2 | 运行任务列表 | C1 后 | 浏览 | activeTasks、共享 `now` | 与 C3 互斥；任务完成后迁移到 D2 |
| C3 | 当前无运行空态 | C1 后 | 无 | total > 0 且 active = 0 | 与 C2 互斥，不替代全局 E2 |
| D1 | 完成分组标题 | B1 内容槽 | 无 | counts.completed | 为 D2 提供全量总数 |
| D2 | 完成任务列表 | D1 后 | 浏览 | completedTasks | 按 finishedAt 倒序，分页结果追加 |
| D3 | 分页控制 | D2 后 | 加载更多 | nextCursor、loadingMore、loadMoreError | 失败不清空 D2 |
| E1 | 首次加载状态 | B1 内容槽 | 无 | loading 且无快照 | 替换 C1–D3 |
| E2 | 全局空状态 | B1 内容槽 | 无 | REST 成功且 total=0 | 替换 C1–D3；区别于 C3 |
| E3 | 错误/离线状态 | B1 内容槽 | 重试 | error、connectionStale、hasSnapshot | 无缓存时替换；有缓存时叠加提示 |

---

## 7. 逻辑歧义与实现边界

1. 截图只定义“已开启”和“完成”两组，但真实模型还可能返回 `failed/cancelled`。两者不能计入 `completed`；是否新增“已结束”分组需产品确认。
2. 上游是否提供稳定头像、代理显示名和安全摘要尚未确认。缺失时可以使用确定性 fallback，但不可从自然语言正文猜测身份或总结。
3. 若历史任务没有权威持久化接口，仅依赖当前 SSE 将无法满足刷新恢复；此时应先补后端快照能力，不能由前端缓存冒充真实历史。
