<!-- [Input] Stage 1 PRD draft, Stage 2 page sketches, both reference images and current public source modules. -->
<!-- [Output] Stage 3 optimized execution prompt, refined numbered page partition, logical hierarchy and formal interaction design handoff. -->
<!-- [Pos] html-design-workflow Stage 3 process evidence; formal business diagrams belong to priority-activity-sidebar.md. -->
<!-- [Sync] 2026-10-07: document-only hierarchy and formal interaction draft completed; Stage 4, independent review and feature verification pending. -->

# Stage 3：活动视图层级与逻辑映射

## Optimized Prompt:

你是 Ink & Memory 活动视图的信息架构与交互分析师。严格承接已生成的 Stage 1 PRD、Stage 2 页面草图和原始截图，在任何本阶段规划前先记录本优化提示词。读取仓库合同、受影响目录清单、Stage 3 技能说明和当前公开模块，输出编号一致的精细模块草图与父子逻辑树，写入本阶段文件。正式设计保存于 docs/design/claude-agent/priority-activity-sidebar.md，正文直接包含背景与问题、目标与边界、概念与规则、正常业务 Mermaid 时序、异常恢复时序、页面及来源状态图、数据与权限边界、响应式和验收追踪。图中使用真实 ChatViewContent、listChatThreads、getScheduledDay、useStoryWorkspaceDreamRuns、storyWorkspaceFetchDreamRuns、handleSelectThread、openDreamRun、ScheduledTaskDetailSidebar；新 ActivitySidebar 和纯展示 helper 标为建议、未实现。明确20rem桌面、原768px移动判定、390px覆盖抽屉、四项菜单、唯一body列表滚动、来源独立错误和重试、近期Chat公开分页完整扫描至旧记录、今日任务合并、真实运行/业务阶段标签、导航、焦点与窄屏背景隔离、关闭/隐藏停止本功能刷新、晚到请求保护。复用历史/search/pagination，保留原Chat发送、Runtime、数据库及无关工作区改动。保存 Chat Sidebar 原稿逐字全文于同目录历史文件后，仅修正现行侧栏相关入口/宽度/只读范围/新合同引用，并在 Chat Dashboard 增加活动辅助入口说明。同步相关 .folder.md 和现行 PRD 的正式稿链接及本阶段状态。不得实现功能代码，不宣称独立评审、功能或真实业务验收通过。先检查 Markdown 清单、相对引用和 Mermaid，再将可实施映射交下一阶段与独立评审。

## 执行依据与计划

1. 阅读前两阶段与原图，按 A1 到 F3 维持模块编号；核对真实接口、时间、状态、导航、分页与快照。
2. 补充模块精细草图和逻辑树；把完整正常/异常/状态图直接交付到正式设计正文，避免阶段文件替代产品合同。
3. 逐字保留旧 Sidebar 后，对现行侧栏和 Dashboard 只同步本次影响；更新清单和 PRD 状态。
4. 执行文档与 Mermaid 检查并交接。独立评审另行执行，功能实现等待评审。

## 页面结构草图：模块分区

```text
┌──────────────────────── A1 Chat 顶部 ───────────────────────────────────┐
│ 现有 Agent/Deck       新建 [活动铃铛]  原任务与进度 更多                 │
├────────────────── A2 主Chat ──────────────────┬── 右侧20rem ───────────┤
│ 原消息或landing                              │ B1 活动 搜索 刷新 关闭│
│ 原消息滚动位置不变                           ├───────────────────────┤
│                                              │ 单一body列表滚动区    │
│                                              │ C1 优先级           … │
│                                              │ C2 三来源统一排序行   │
│                                              │ 标题／来源／真实状态  │
│                                              │ C3 分来源加载错与重试 │
│                                              │ D1 原日期分组及历史行 │
├────────────── A3 原输入与发送／停止 ──────────┤ D2 历史分页及重试     │
└──────────────────────────────────────────────┴───────────────────────┘
E1 四项菜单从 C1 展开：优先级部分、定时任务、Chat、Dream。
E1 为受视口限制的浮层，不在body裁剪范围内，不增加管理动作。
F1 原历史搜索弹窗位于活动上层；F2任务详情、F3其他侧栏与活动互斥。
```

```text
┌────────────── 390px 覆盖抽屉 ────────────────┐
│ B1 固定标题：活动  搜索 刷新 关闭           │
├─────────────────────────────────────────────┤
│ 唯一body列表滚动区                          │
│ C1 优先级 … → E1四项可勾选菜单             │
│ C2统一活动行／C3来源反馈                    │
│ D1日期历史／D2分页反馈                      │
│ 原安全区留白，列表可滚动到底部              │
└─────────────────────────────────────────────┘
A2/A3 背景不接收抽屉内的点击、滚动或焦点，关闭后还原。
原useMobile判断继续使用，768px是既有视口判定，390px是验证尺寸。
```

## 页面层级结构图：父子关系与职责

```text
Root：ChatViewContent（既有用户工作区与侧栏协调）
├── A1 顶部操作
│   ├── 原新建：原创建语义
│   ├── 活动铃铛：只打开/关闭下方B/C/D，并关闭F2/F3
│   └── 原任务与进度/更多：原入口职责，侧栏开关加入互斥
├── A2 原消息或landing：原主内容与独立消息滚动
├── A3 原输入：原草稿、附件、发送与停止；活动刷新不改发送
├── ActivitySidebar（建议、未实现；B/C/D/E的统一展示外壳）
│   ├── B1 固定标题
│   │   ├── 搜索：打开F1
│   │   ├── 刷新：并行读取来源、重算窗口，不改变业务实体
│   │   └── 关闭：停止本功能刷新、返回铃铛焦点
│   ├── 唯一body列表滚动
│   │   ├── C1 优先级标题与E1菜单入口：收起内容后仍可恢复
│   │   ├── C2 活动行：统一排序，不按来源造三个独立列表
│   │   │   ├── 今日任务：task_id合并，trigger状态，taskId进入F2
│   │   │   ├── 近期Chat：完整公开分页窗口集合，原Thread导航
│   │   │   └── 近期Dream：原重入DTO，canonical href与原导航
│   │   ├── C3 来源反馈：加载/成功空/错误/保留旧行/来源重试
│   │   ├── D1 日期历史：原getThreadDateGroup，排除C2已显示Chat；保留独立删除
│   │   └── D2 分页：原loadMoreThreads；错误不等于全部已显示
│   └── E1 视口内菜单浮层：四项，勾选重算，仅控制C2/C3
├── F1 原HistorySearchDialog产品名称：当前ChatView内联弹窗
├── F2 ScheduledTaskDetailSidebar：与活动互斥，允许无定义快照
└── F3 FileSidebar/子智能体/TaskSessionSidebar：原职责，与活动互斥
```

`activitySidebarModel`（建议、未实现）不是新的业务服务。它只接收原DTO、统一clock、集中窗口配置和筛选，输出活动行及去重后的历史展示数组；日期/权限/持久化/运行状态仍由当前生产模块负责。近期分页网络循环由 `ChatViewContent` 的读取协调执行；纯转换只接收 Thread 批次、统一 now 与已收集 ID，返回筛选/去重结果及停止条件，不直接调用 `listChatThreads`。

## 实现映射与边界

| 编号 | 复用或最小变更 | 防止过度设计的依据 |
| --- | --- | --- |
| A1/F3 | 现有threadSidebarOpen及原侧栏setter | 不造全局通知状态机；“更多→历史”指向同一面板。 |
| B1/D1/D2/F1 | 原历史与搜索；listChatThreads保留失败 | 不复制搜索协议或历史入口；补错误不将失败写成空；保留原独立删除回调。 |
| C2 | 待实现纯转换与独立近期扫描 | 不加后端聚合接口；不固定最多页数；历史分页offset独立。 |
| C2任务/F2 | getScheduledDay与原详情 | 快照只能来自定义；孤立触发传taskId与空snapshot，不伪造rule。 |
| C2 Dream | 原hook/data.runs和真实href | 不改变原重入排序，不猜实时Runtime；普通点击复用openDreamRun，修饰键保持链接。 |
| C3 | 来源独立序号、活动会话与任务日期 | 单源失败可重试；旧响应丢弃；旧运行状态不当作当前事实。 |
| E1 | 四项带勾选菜单 | 无归档、已读、置顶或二级管理页；偏好仅当前生命周期。 |
| 窄屏 | 原useMobile；覆盖抽屉与原焦点工具 | 不另造屏幕业务规则，标题固定，单body滚动，背景隔离。 |

## 正式稿与交接

### 原能力保留修正的 Optimized Prompt:

仅更新原 Chat 删除能力的边界：打开、刷新、筛选和点击行导航不自动写入，但日期历史的原独立删除按钮及 handleDeleteThread 必须保留；近期 Chat 去重后可复用同一回调，避免原能力丢失。不新增删除机制或确认，不增加任务控制、归档、已读、置顶。同步现行 PRD、正式交互稿和 Sidebar 的相关句子与验收条件，保留其他目标和授权，仍不写功能代码。

### 独立评审收口修正的 Optimized Prompt:

仅核对并明确正常时序中的纯转换职责：ChatViewContent 的读取协调负责公开分页网络循环，activitySidebarModel 接收 Thread 批次、统一 now 与已收集 ID，返回时间筛选、去重及停止条件，不调用 listChatThreads。当前图已有 V→C 修正，不重复新增模块、架构或业务规则；把输入和 Stage 3 说明写明，仅重新解析受影响的正常时序图并记录实际命令与退出码，交独立评审收口。

[正式交互设计稿](../../priority-activity-sidebar.md)正文含正常 sequenceDiagram、异常恢复 sequenceDiagram、页面 stateDiagram-v2 和来源 stateDiagram-v2，直接覆盖流程、条件、错误反馈、恢复和并发。其产品规则与[现行 PRD](../../../../prd/chat/priority-activity.md)一致。本文件仅作为 Stage 3 的逻辑过程证据。

下一阶段细化主题token、按钮/行间距、菜单层级和窄屏视觉。后续独立评审需直接核对 PRD 骨架及正式稿业务图；本阶段不可自称独立评审已通过。功能代码与技术验证尚未开始，已存在权限/时间/数据集合限制必须保留在交付说明。

## 本阶段文档检查回执

- `python3 <<'PY'` 聚焦检查上述正式稿、阶段稿、现行PRD/Sidebar/Dashboard、完整旧稿及四份相关目录清单：退出0；`markdown_files=10 local_links=31 failures=0`。Sidebar 历史与 `git show HEAD:docs/prd/Chat Sidebar.md` 字节一致，SHA-256 为 `d09a7c3d1f96b1f16aef315a7d6fd59ddad77c7a8b2d82df521f7860ea9a4929`。
- `node --input-type=module` 直接解析在两张时序图之后遇到 Mermaid/DOMPurify 无DOM前置限制，退出1；不能据此判为图语法缺陷。随后 `node <<'JS'` 使用已有 Playwright 和本机已安装 Chrome，仅加载本地 Mermaid 到空页面，对正式稿四图执行 parse/render：退出0；四图均输出 SVG，`mermaid_blocks=4 failures=0`。未下载浏览器、访问业务页面或修改现有服务。
- `git diff --check`：退出0，无输出。此为文档检查，不是功能或真实业务验收；独立评审仍待执行。
- 独立评审指出的正常时序纯转换边界已明确；`node --input-type=module <<'JS'` 仅提取正式稿第一张 Mermaid 图，检查没有 `M->>C` 且有 `V->>C` 分页循环，再调用 `mermaid.parse`：退出0，`normal_sequence=PASS type=sequence network_owner=ChatViewContent model_network_calls=0`。未重复其他图或全范围验证，独立评审结论由评审者记录。
