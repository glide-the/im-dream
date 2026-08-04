# Story Workspace PRD — Dream Agent 工作空间

> **Design ID**：`design_001_story-workspace-prd`
> **关联 Issue**：[SUO-199](/SUO/issues/SUO-199)
> **增量 Issue**：[SUO-214](/SUO/issues/SUO-214)、[SUO-230](/SUO/issues/SUO-230)、[SUO-236](/SUO/issues/SUO-236)、[SUO-298](/SUO/issues/SUO-298)
> **父 Issue**：[SUO-198](/SUO/issues/SUO-198)
> **最后更新**：2026-08-04
> **文件协议 owner**：[design_006](./design_006_dream-protocol-dir-mapping.md)
> **业务交互 owner**：[design_007](./design_007_dream-business-module-interaction.md)
> **代码现状与缺口**：[design_005](./design_005_dream-module-dataflow-and-sequence.md)
> **任务三实施证据**：[Dream 发起与 writer 生产链接通实施记录](./2026-08-04-dream-launch-writer-integration-implementation-record.md)

## 1. 产品目标

Dream 是由 Dream Agent 工作空间文件驱动的创作页面。它不是手动从零创建内容的后台，也不是逐项审批系统。

页面主生命周期只有四阶段：

```text
Dream Agent 产出 → 页面渲染 → 用户修改并确认 → 同一 Dream Agent 后续执行
```

目标：

- Dream Agent 按 Deck 插件在工作空间写人物、场景、分镜及 `.dream` 描述文件；
- Dream 页面把工作空间文件渲染为 Assets / Outline 与可编辑详情；
- 用户可以修改内容，但只做一次“确认并继续”；
- Dream 专用发起由服务端创建 Dream Agent 与可信 run context，并在首个 turn 完成内建 Dream adapter pack；普通非 Dream turn 不注入该 adapter；
- 确认命令回到同一 Dream Agent，由其写入修改并继续；
- 后续执行持续通过工作空间文件和 stage revision 更新页面；
- 视觉遵循 Ink & Memory UI Design v2 的暖纸、轻纸面、无卡片体系。

## 2. 范围

### 2.1 本期范围内

| 模块 | 说明 |
|---|---|
| 顶部 Dream 入口 | canonical `/story-workspace/dream`，所有 `/story-workspace/*` 子页保持 Dream 选中 |
| Dream 专用发起 | 选择可用 Deck、输入创作目标；服务端创建 Dream Agent、执行 preflight/run、锁定运行快照和 plugin lock，并调度首个 turn；隐藏 Deck-bound thread 仅为技术载体 |
| `.dream` 静态启动层 | packer 物理映射 `README.md + workspace.json`，保持 `dream-surface/v1` 冻结 |
| `.dream` 运行内容层 | Dream Agent 写 canonical 文件，并经 Story Workspace MCP/writer 按 run → characters → scenes → storyboards 更新运行内容层；普通文件工具不得写 `.dream/**` |
| Dream Agent 产出页面 | 人物、场景、Outline/分镜模块按 stage 文件逐步出现 |
| Dream 内容编辑 | 用户修改 Dream Agent 产出的允许字段，修改在确认前保持页面本地草稿 |
| 一次确认 | required stages 齐全后提交“确认并继续”，注入本次 Dream 的同一隐藏 thread |
| 后续执行 | 同一 Dream Agent 写入用户修改并继续插件步骤；页面按 revisions 刷新 |
| 桌面布局 | 产出/修改阶段使用三栏；后续执行使用两层交互深度 |

### 2.2 本期明确不做

- 逐项确认、批量确认或 Review Gate 聚合；
- 驳回、失败、重试或归档业务流程；
- 后续执行后的第二次确认；
- 用户手动新建故事、人物、场景或分镜；
- 平台视频、上传、播放器、外部模型选择；
- 可编辑故事板、时间线、场景布局或交互控件画布；
- World Builder、人物三视图、计费积分；
- 移动端、平板端、触控布局；
- 多用户实时协作；
- 浏览器直接读写工作空间；
- 修改 `backend/database.py` 或新增 DDL。

## 3. 调研来源与适配

### 3.1 Dreem 创作者协作页面

唯一交互调研来源是 `调研Dreem_app平台.pdf` 第 3～8 页：

| 页码 | 截图事实 | 本平台适配 |
|---|---|---|
| 第 3 页 | Script Review 可修改；底部一次确认后 Agent 自动化创作 | 用户修改整份 Dream 后一次“确认并继续” |
| 第 3 页 | 创作者协作包含数据/任务进度层和 Agent 指导 | 用 Agent 工作空间文件进度和后续执行内容表达 |
| 第 4 页 | Assets / Outline；人物、地点、完整剧本入口 | 人物/场景/分镜模块索引 |
| 第 5 页 | 确认后 Agent 继续扩展故事 | 同一 Dream Agent 接收确认后继续插件步骤 |
| 第 6 页 | 故事线定位叙事点，点击镜头文稿进入协作窗口 | Outline → 故事线 → 叙事点 → 聚焦上下文 |
| 第 7 页 | 协作窗口含人物、主要信息、镜头说明和历史 | 结构化上下文与工作空间历史 |
| 第 8 页 | 特殊镜头含决策控件 | 只读结构化字段，不做画布编辑 |

### 3.2 UI Design v2 约束

以 `Ink & Memory UI Design v2.pdf` 第 4～5 页和 `frontend/src/styles/tokens.css` 为准：

- Warm Canvas `#F6EFE5` 页面背景；
- Paper Cream `#FFFAF2` 轻纸面；
- Charcoal Brown 标题、Body Brown 正文、Action Brown 主操作；
- Memory Yellow / Spark Green 仅小面积强调；
- 少面板、多留白，普通条目静止无卡片阴影或深色底；
- 页面级最多一条 Border Paper `#D8C7B3` 虚线边界。

Dreem 的黑底画布、橙色按钮、视频和卡片堆叠不作为视觉规范。

## 4. 领域与文件所有权

| 参与者 | 负责 | 不负责 |
|---|---|---|
| Deck | 插件定义、版本、提示词/配置、权限、runtime snapshot、plugin lock | Dream 内容文件和页面状态 |
| packer | 首个 agent turn 物理映射 `.dream` 静态启动层 | 运行内容层 |
| 同一 Dream Agent | 按 Deck 插件写 canonical 内容，并经 Story Workspace MCP 请求更新 `.dream/runtime`；确认后写用户修改并继续 | 使用普通文件工具写 `.dream/**`；修改静态 `workspace.json` |
| story-workspace API / gateway | actor-scoped 安全读取文件；由服务端创建 Dream Agent、preflight/run 与可信上下文；只为 Dream turn 选择内建 adapter；接收确认并恢复同一 Dream Agent | 接受客户端 thread/run/来源字段；维护第二份内容真相源 |
| Dream 前端 | 渲染、维护本地编辑草稿、一次确认 | 直接访问文件系统 |

### 4.1 canonical 内容与 `.dream`

- 人物 canonical 文件：插件声明的 `assets/characters/*.md` 等路径；
- 场景 canonical 文件：插件声明的 `assets/scenes/*.md` 等路径；
- 分镜 canonical 文件：`stories/<project>/episodes/EP??/storyboard.yaml`；`.dramaforge/runs/<internal_run_id>/{artifacts,reports}/` 只作为可选来源引用；
- `.dream/runtime/runs/<workflow_run_id>/stages/*.json`：页面索引、摘要、source files 与 revision，不复制全文或二进制。

`.dream/workspace.json` 继续只含 deck、plugins、entry route。run/source 字段和 `projection_entry` 只进入运行层 `run.json`。

### 4.2 合同 owner

- 后端 story-workspace 合同只归 `backend/story_workspace/contracts.py`；
- 前端局部 REST 合同只归 `frontend/src/hooks/story-workspace/contracts.ts`；
- 所有新增业务符号使用 `StoryWorkspace*` 前缀；
- `backend/database.py` 只读、零 DDL。

## 5. 信息架构与路由

```text
/story-workspace/dream
  ├─ 工作流上下文 / Dream Agent 文件写入进度 / 一次确认条
  ├─ /story-workspace/characters?run=<runId>
  ├─ /story-workspace/scenes?run=<runId>
  └─ /story-workspace/runs/<runId>/execution
       ├─ Assets
       ├─ Outline / 故事线 / 叙事点 / 分镜摘要
       └─ 选中项聚焦上下文层
```

兼容路由：

- `/story-workspace` → `/story-workspace/dream`；
- `/story-workspace/dashboard` → `/story-workspace/dream`。

路由只携带 run ID；Deck 来源字段、stage revisions 和文件路径从 actor-scoped REST 取得。

## 6. 页面布局

### 6.1 产出、渲染与修改阶段

桌面端使用三栏：

```text
┌─────────────┬─────────────────────────────────────┬────────────────────┐
│ Sidebar     │ Main Content                        │ Detail / Editor    │
│ 240px       │ 工作流上下文、stage 进度、列表       │ 当前人物/场景/镜头  │
│             │                                     │ 可编辑字段          │
└─────────────┴─────────────────────────────────────┴────────────────────┘
```

右栏是当前内容编辑器，不是逐项 Review Panel；底部/主内容区只有一个整份 Dream “确认并继续”。

### 6.2 后续执行阶段

后续执行不嵌入审阅三栏。采用两层交互深度：

1. Assets / Outline 索引 + 叙事点/执行步骤主工作面；
2. 选择镜头摘要后打开聚焦上下文层。

“两层”不是固定双栏，也不是常驻第三栏。页面只展示 Dream Agent 继续写入的工作空间内容。

## 7. 业务模块

### 7.1 Dream 发起与 stage 进度

| 条件 | 页面表现 | 主操作 |
|---|---|---|
| 无 run | Deck 工作流、创作目标 | 发起 Dream |
| 有 run，required stage 未齐 | 已有模块可查看；其余显示等待 Dream Agent 写入 | 无确认 |
| required stages 已齐 | 完整 Dream 草稿、编辑器、revisions | 确认并继续 |
| 已确认 | Dream Agent 后续执行与最新 revisions | 查看执行内容 |

无 run 时，前端只提交 `deckId + goal + idempotencyKey`。服务端使用登录 actor 与
workspace 校验可用 Deck，创建/复用 Dream Agent 并执行 preflight/run，调度携带可信
run context 与服务端专用 Dream adapter 的首个 turn；浏览器不能指定 thread ID、
run ID、来源五字段或 adapter package spec。
成功后进入 `/story-workspace/dream?run=<workflowRunId>`。

技术实现复用隐藏的 Deck-bound Agent thread 与隐藏 `chat_message` 作为 Dream Agent
的连续性和持久化载体；Dream 前端不挂载 `ChatView`，该载体不属于 Chat 页面或
Chat 业务合同。

### 7.2 人物

stage：`characters.json`。

展示人物名称、摘要、关系和插件提供的结构化字段。用户可修改允许字段；不提供新建、逐项确认或其他审批动作。

### 7.3 场景

stage：`scenes.json`。

展示场景名称、描述、关联人物和故事引用。用户可修改允许字段；不提供场景布局画布。

### 7.4 Outline / 分镜

stage：`storyboards.json`。

- Outline 索引：故事线、叙事点数量；
- 主工作面：叙事点分组、镜头摘要、人物/场景引用；
- 聚焦上下文层：当前镜头主要信息、结构化说明和历史；
- 决策控件只读显示，不提供拖放编辑。

### 7.5 确认条

固定展示：

- required stages 是否齐全；
- characters/scenes/storyboards 当前 revisions；
- 用户修改数量；
- 唯一主操作“确认并继续”。

确认提交后进入 `story-workspace-dream-continuing`，不再显示逐项审批动作。

## 8. 四阶段生命周期

### 8.1 Dream Agent 产出

1. 专用 Dream 发起创建隐藏 Deck-bound thread、source message、preflight/run，并向首个 turn 注入可信 run context 与服务端 Dream adapter；
2. Dream Agent 调用 `write_dream_run`，由 writer 写 `.dream/runtime/runs/<run_id>/run.json`；
3. 写人物 canonical 文件后调用 `write_dream_stage(characters)` 原子写 `characters.json`；
4. 写场景 canonical 文件后调用 `write_dream_stage(scenes)` 原子写 `scenes.json`；
5. 写分镜 canonical 文件后调用 `write_dream_stage(storyboards)` 原子写 `storyboards.json`；
6. writer 当前不直接发布 run-scoped SSE；页面以至少 5 秒 REST 轮询发现 revisions。若收到携带匹配 `runId` 的兼容 `story-workspace-output`，可提前重新读取。

stage 文件不存在表示等待 Dream Agent；存在且 schema 有效表示该模块可渲染。

### 8.2 页面渲染

1. 页面 GET `dream-files`；
2. 后端校验 actor、run、schema、revision 与 source path containment；
3. 页面显示已存在模块并保存 base revisions；
4. 用户修改暂存为页面本地草稿。

### 8.3 用户修改并确认

1. required stages 全部存在；
2. base revisions 未变化；
3. 用户点击一次“确认并继续”；
4. 页面提交 `StoryWorkspaceDreamConfirmationCommand`，包含 edits、base revisions 与幂等键；
5. 服务端把命令作为 `metadata.kind="story-workspace-dream-confirmation"` 的唯一隐藏 user 消息持久化到本次 Dream 的同一 thread，初始 `dispatch_status="pending"`；
6. 后台确认协调器在提交后及服务启动后的周期扫描中透明交付 pending 命令，并从服务端事实重新装载同一可信 run context；只有同一 Dream Agent turn 依次产生 `message-final` 与非 error 终止帧才持久确认为 dispatched；基础设施未完成消费时保持 pending 并自动协调，页面不提供额外业务动作。

不建立逐项 review_status。

### 8.4 同一 Dream Agent 后续执行

1. Dream Agent 读取确认命令；
2. 写入用户修改的 canonical 文件；
3. 更新受影响 stage revisions；
4. 按同一 Deck 插件、runtime snapshot 和 plugin lock 继续；
5. 后续文件写入由至少 5 秒轮询 GET `dream-files` 发现并刷新；匹配 run 的兼容事件可提前触发读取。

后续执行到此为止，不附加审批或异常业务分支。

完整业务时序图见 `design_007` §5；文件写入合同见 `design_006` §4～§9。

## 9. API 与消息合同

### 9.1 发起 Dream

```text
POST /api/story-workspace/dream-runs/start
```

请求只包含：

```json
{
  "deckId": "<deck id>",
  "goal": "创作目标",
  "idempotencyKey": "dream_<uuid>"
}
```

请求字段只接受上述 camelCase 名称；额外字段、snake_case 别名、空值或带首尾空白的
值返回 422，服务端不静默改写目标文本。

响应返回服务端派生的 `workflowRunId`、`threadId`、Deck 来源五字段与锁定上下文。
幂等重放复用同一隐藏 source 与 run，并使用该 run 冻结的 binding，不受当前 active
binding 漂移影响；同键改 Deck/goal 返回冲突。首个调度采用持久 claim，同一时刻只有
claim 获得者投递 source message；fresh claim 不抢占，stale claim 可恢复，派发未完成
时回到 pending，而不是创建第二个 thread/run。

### 9.2 读取 Dream 文件

```text
GET /api/story-workspace/workflow-runs/{run_id}/dream-files
```

响应至少包含：

- `storyWorkspaceRunId`、`threadId`；
- Deck 来源五字段；
- required stages；
- 已存在 stage 的 revision、entry route、items、source files 与可编辑字段；
- `canConfirm`；
- 固定 `confirmationLabel = "确认并继续"`。

### 9.3 一次确认

```text
POST /api/story-workspace/workflow-runs/{run_id}/dream-confirmation
```

`StoryWorkspaceDreamConfirmationCommand`：

```json
{
  "storyWorkspaceRunId": "run_<32hex>",
  "threadId": "<thread id>",
  "baseRevisions": {
    "characters": 2,
    "scenes": 1,
    "storyboards": 3
  },
  "edits": [],
  "idempotencyKey": "swc_<uuid>"
}
```

同 actor+run 只允许一次确认；同幂等键同内容返回同一结果，换键或同键不同内容返回冲突。隐藏消息同时是零 DDL 的 durable work item：基础设施未完成消费或进程退出时保持 pending，并由后台按 message ID 协调；只有 `message-final` 与非 error 终止帧同时出现才确认 dispatched。Dream Agent 已完成、SQLite 确认前退出可能重复交付同一 message ID，因此语义为 at-least-once，不承诺 exactly-once。该隐藏消息不显示在 Dream 页面，也不构成 Chat 业务交互。

### 9.4 revision 发现与兼容事件

REST `dream-files` 是运行内容真相源。waiting、editing、continuing 页面至少每 5 秒轮询；writer 主动 run-scoped SSE 仍是遗留。既有链路若发出带匹配 `runId` 的兼容 `story-workspace-output`，只作为立即重新 GET 的加速信号，不在事件中传全文；无 `runId` 或 run 不匹配的事件不得刷新当前 Dream。

## 10. 页面状态

| `StoryWorkspaceDreamState` | 条件 | 页面表现 |
|---|---|---|
| `story-workspace-dream-waiting-files` | required stage 未齐 | 等待 Dream Agent；已有模块可查看 |
| `story-workspace-dream-editing` | stage 已齐、尚未确认 | 可编辑内容与确认条 |
| `story-workspace-dream-confirming` | 确认请求提交中 | 禁止重复点击 |
| `story-workspace-dream-continuing` | 确认已交付同一 Dream Agent | Dream Agent 正在继续；刷新 revisions |
| `story-workspace-dream-completed` | 插件后续步骤结束 | 只读展示最终结果 |

不定义 rejected、failed、retrying 或 archived 页面状态。

Dream 路由的工作流上下文固定投影为 `story_workspace_dream`，显示“Dream 协作中”；底层 `WorkflowRun.status` 不进入 Dream 页面，因此既有 rejected、failed、cancelled 标签和 cancel/retry/review 动作不会成为 Dream 业务交互。非 Dream 页面继续保留原有状态语义。

## 11. 文件一致性与安全

- 静态层由 packer 单写；Dream Agent 的普通文件工具与 Bash 不能写 `.dream/**`，只有持有服务端可信 run context 的 Story Workspace MCP 可以调用 `StoryWorkspaceDreamFileWriter` 更新该 run 的 `.dream/runtime/**`；
- stage 写入使用 expected revision、同目录临时文件、flush/fsync、`os.replace`；
- 同一技术 thread 同时只允许一个修改当前 Dream run 的 Dream Agent turn；
- 同一 stage revision 串行，不同 stage 可独立写；
- source files 必须是工作空间内相对路径，禁止绝对路径、`..` 与 symlink 逃逸；
- `dream-files` REST 必须 actor-scoped；
- 临时写未完成时页面保留上一 revision 或继续等待，不增加业务异常页面；
- 静态冻结分支不删除或重建 runtime 文件。

## 12. 验收标准

### 12.1 功能

- [x] Dream 从 Dream Agent workspace 文件渲染，不依赖第二份内容数据库。
- [x] 专用发起页创建 Dream Agent、preflight/run 并调度首个 turn；隐藏 Deck-bound thread 仅为技术载体，浏览器不提交可信来源字段。
- [x] 内建 Dream adapter 仅由服务端选择，普通 Chat turn 不注入；同一 adapter 指示 run → characters → scenes → storyboards writer 链。
- [x] `run.json` 包含 run/source 字段、`projection_entry` 与 required stages。
- [x] 人物、场景、分镜 canonical 文件完成后，Dream Agent 经受控 writer 原子写对应 stage 描述。
- [x] 页面按 stage 文件出现人物、场景和 Outline/分镜模块。
- [x] 用户可以修改内容，但只有一次“确认并继续”。
- [x] 确认命令注入本次 Dream 的同一隐藏 thread，并复用可信 run context。
- [x] 同一 Dream Agent 先写入用户修改，再继续后续插件步骤。
- [x] 后续执行只展示 workspace 持续更新，不出现驳回、失败、重试、归档或第二次确认。
- [x] 浏览器不直接访问工作空间文件。
- [x] G3、G5 已实现；G1 仅保留为旧 `WorkflowRun.status` 聚合仍停 `queued` 的技术遗留；G6 仍为遗留。

### 12.2 视觉与布局

- [x] 产出/修改阶段三栏与后续执行两层交互职责分离。
- [x] 执行“两层”不实现为固定第三栏或静态双栏。
- [x] 对齐 PDF 第 3 页一次确认、第 4～7 页 Assets/Outline 和聚焦上下文动线。
- [x] 使用 Warm Canvas / Paper Cream、轻纸面和无卡片规则。
- [x] 不实现视频、上传、播放器或可编辑画布。

### 12.3 合同与工程边界

- [x] 后端业务与 Agent-visible MCP 输入合同只归 `backend/story_workspace/contracts.py`。
- [x] 前端局部合同只归 `frontend/src/hooks/story-workspace/contracts.ts`。
- [x] 新符号统一 `StoryWorkspace*` 前缀。
- [x] `backend/database.py` 只读、无 DDL。
- [x] stage writer 覆盖 revision、原子替换、路径 containment 和静态层保护测试。

## 13. 代码现状诚实边界

任务三后的现状：

- G1：旧 `WorkflowRun.status` 聚合在 create 后仍停 `queued`，这是执行状态展示与旧 guidance 合同的技术遗留；首个生产 Dream Agent 已由隐藏 source message 独立调度，不能再表述为“无生产推进方”；
- G2：Dream confirmation 已恢复同一 Dream Agent，并用同一可信 run context 排队 continuation；旧 story review confirm 仍不驱动 run，但已退出 Dream 主链；
- G3：专用 Dream 发起页 → `dream-runs/start` → preflight/run → 首个 Dream Agent turn 已接通；
- G5：actor-scoped `dream-files` REST 已实现；
- G6：入口六态聚合端点仍缺位，既有 surface link 继续默认隐藏；
- writer 主动 run-scoped SSE 仍未实现，前端以 REST 轮询保证正确性。

runtime stage 文件、一次确认和确认后的 Dream Agent continuation 已实现。当前诚实遗留是
G1 的旧状态聚合、G6 入口聚合、丰富 Outline 字段与 writer 主动 SSE；不宣称真实
Claude 外部服务端到端运行已由单元/契约测试替代验证。

## 14. 决策记录

### 14.1 历史 DEC 原文（保留）

| 决策 ID | 日期 | 原决策文本 | 影响 |
|---|---|---|---|
| DEC-001 | 2026-08-01 | 采用轻纸面分区布局 | 视觉体系 |
| DEC-002 | 2026-08-01 | 复杂画布以数据表呈现 | 产品范围 |
| DEC-003 | 2026-08-01 | 三栏桌面布局 | 页面布局 |
| DEC-004 | 2026-08-01 | `story-workspace` 前缀命名 | 代码命名 |
| DEC-005 | 2026-08-01 | 排除视频模块 | 产品范围 |
| DEC-006 | 2026-08-01 | 仅桌面端设计，排除移动端/平板端 | 页面范围 |
| DEC-007 | 2026-08-01 | 核心工作流：Agent 产出 → 页面渲染 → 用户审阅确认 → 执行 | 业务模型 |
| DEC-008 | 2026-08-01 | 用户不手动创建内容，仅审阅 Agent 产出 | 用户角色 |
| DEC-009 | 2026-08-01 | Deck 是唯一业务模块；story-workspace 只消费公开合同 | 领域边界 |
| DEC-010 | 2026-08-01 | 单次运行锁定 Deck 插件版本、runtime snapshot 与 plugin lock | 可复现性 |
| DEC-011 | 2026-08-01 | release、配置、权限或 preflight 不通过时禁止启动 Agent | 启动门槛 |
| DEC-017 | 2026-08-01 | `/story-workspace/dream` 为 canonical 入口，Dashboard 只重定向 | 导航 |
| DEC-018 | 2026-08-01 | 运行级审阅 gate 在全部必审项确认前禁止继续或结束 | 原确认模型 |
| DEC-019 | 2026-08-01 | 提示词、运行配置、secret-ref、权限与不可变快照统一归属 Deck | 所有权 |
| DEC-026 | 2026-08-01 | 后端合同归 `backend/story_workspace/contracts.py`，前端局部合同归 `frontend/src/hooks/story-workspace/contracts.ts`；`backend/database.py` 只读 | 合同 owner |

### 14.2 2026-08-04 最终修订注记

- **DEC-003**：三栏只用于 Dream Agent 产出、页面渲染和用户修改阶段；后续执行采用两层交互深度。
- **DEC-007**：“用户审阅确认”收窄为整份 Dream 一次“确认并继续”；确认回到同一 Dream Agent，由其继续。
- **DEC-008**：用户不从零新建内容，但可以修改 Dream Agent 产出的字段。
- **DEC-018**：原逐项 Review Gate 目标不再采用；改为 required stages + base revisions 的一次确认门槛。
- **DEC-029 / DEC-033**：原文及完整修订史保留在 `design_004` §9；现行合同为静态启动层 + Dream Agent 运行内容层。
- **Dream 发起接线**：专用入口只提交 Deck、目标和幂等键；服务端创建隐藏 Deck-bound thread、preflight/run 与可信上下文，并只为该 Dream turn 注入内建 adapter。确认 continuation 回到同一 thread。
- **归档/驳回/失败**：不进入 Dream 业务模型，后续执行没有这些分支。

## 15. 增量变更说明

- **2026-08-01**：初版 Story Workspace PRD。
- **2026-08-01**：改为 Agent 产出 → 页面渲染 → 用户确认 → 执行。
- **2026-08-01**：补 Deck-only 边界、运行快照、Dream 导航、合同 owner 与桌面布局。
- **2026-08-04 首轮专项**：拆分 `.dream` canonical 文档并调整执行布局。
- **2026-08-04 最终用户修订**：全面改为 Dream Agent workspace 文件驱动；用户只修改并一次确认；确认后同一 Dream Agent 继续。新增 design_007 业务时序；删除逐项审批、驳回、失败、重试与归档设计。
- **2026-08-04 任务三发起/writer 集成**：Dream 专用发起、隐藏 Deck-bound thread、服务端 adapter、可信 run context 与 run → characters → scenes → storyboards writer 链接通；G3 关闭，G1 收窄为旧状态聚合技术遗留。

## 16. 验证方式

1. 对照 `调研Dreem_app平台.pdf` 第 3 页验证“一次确认后 Agent 继续”。
2. 对照 PDF 第 4～7 页验证 Assets/Outline、故事线定位与聚焦上下文。
3. 对照 UI Design v2 第 4～5 页验证 token、轻纸面、留白与无卡片。
4. 对照 `design_006` 验证静态层、run/stage schema、Agent 写入时点和 revision。
5. 对照 `design_007` 验证四阶段主时序、文件写入时序和业务导航时序。
6. 检索确认当前业务章节没有逐项确认、驳回、失败、重试或归档流程。
7. 确认 G3/G5 已实现；G1 只描述旧状态聚合仍停 `queued`，不得等同于生产 Dream Agent 缺位；G6、writer 主动 SSE 与丰富 Outline 字段仍为遗留/占位。
