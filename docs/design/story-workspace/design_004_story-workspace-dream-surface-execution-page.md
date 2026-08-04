# Chat ↔ Dream 工作台联动：`.dream` 协议目录、Dream 入口与独立执行页

> **Design ID**: `design_004_story-workspace-dream-surface-execution-page`
> **稳定基线**: [story-workspace-prd.md](./story-workspace-prd.md)、[story-workspace-layout-design.md](./story-workspace-layout-design.md)、[design_003_story-workspace-episodes-metadata-review.md](./design_003_story-workspace-episodes-metadata-review.md)
> **上游机制**: [drama-forge-workspace-init-design.md](./drama-forge-workspace-init-design.md)（workspace-init profile 与 packer 扩展点）
> **调研来源**: [调研Dreem_app平台.pdf](./调研Dreem_app平台.pdf) 第 3-7 页（创作者协作页面：数据层、故事线/叙事点、上下文协作与确认动线）
> **状态**: design 完成；`.dream` 合同已迁移至 design_006，执行页布局有 2026-08-04 增量修订
> **更新日期**: 2026-08-04
> **2026-08-03 兼容性修订（任务二）**: 见审计报告 [2026-08-03-dream-surface-audit-report.md](./2026-08-03-dream-surface-audit-report.md)（A1–E15；本文修订点：§0.1 决策 4、§0.2、§2.2、§3.2/§3.4/§3.5、§4、§5.3、§8/§9/§10）
> **2026-08-04 专项修订**: `.dream` 触发、schema、物理映射、冻结、Agent 边界、前端发现与异常的唯一 canonical 已迁移至 [design_006_dream-protocol-dir-mapping.md](./design_006_dream-protocol-dir-mapping.md)；本文 §3 保留为历史细节与摘要，不再是第二 owner。执行页目标布局见 §5.1 与 DEC-030 新注记。

## 0. 增量适用规则

本文是 story-workspace 稳定设计与 drama-forge 工作区初始化设计的**受控增量附录**，不是平行 PRD。

- 顶部 Dream 导航、canonical `/story-workspace/dream`、确认前桌面三栏、结构化内容替代复杂画布与排除平台视频保持不变；右栏是内容编辑器，整页只有一次“确认并继续”，后续执行采用两层协作工作台。
- design_003 只作为代码与历史设计背景；其中逐项审批模型不进入现行 Dream 主业务链。合同归属与 `backend/database.py` 只读仍保持不变。
- drama-forge-workspace-init-design 已确认的 workspace-init profile（=制品内 `.ink/workspace-init.json`，schema `workspace-init/v1`，由 `load_init_profile()` 解析；区别于 Agent profile=Deck 提示词/配置归属物，代码侧归 `services/deck/`）schema（`workspace-init/v1`）、受管 venv、packer（`pack_workspace_plugins()`，`backend/services/claude_plugin/workspace_packer.py`）扩展插槽与冻结语义均保持不变。
- 本文只补充三件事：①插件制品如何声明 `.dream` 协议目录并经 launch manifest 透出；②Dream 入口如何跳转到当前 run；③「后续执行」阶段独立执行页的布局与状态。
- 若本文与稳定基线冲突，仅本文显式标记为增量的 `.dream` surface、跳转链与执行页规则生效；其余以稳定基线为准。

### 0.1 已拍板决策（本文不重新讨论）

| # | 决策 | 日期 |
|---|------|------|
| 1 | `.dream` 协议目录由**插件制品内声明**（`.ink/workspace-init.json` 扩展字段），随 digest 固定 | 2026-08-03 |
| 2 | 前端**经 launch manifest / pack-receipt 透出**感知 surface（载体为既有 `plugin-load-receipt` 端点，见 §3.5 与 §9 DEC-028 修订注记），不探测文件系统 | 2026-08-03（2026-08-03 兼容性修订：「会话 API」明确为 `plugin-load-receipt` 端点，审计报告 B7） |
| 3 | 后续执行阶段使用**独立执行页** `/story-workspace/runs/:storyWorkspaceRunId/execution`，布局参照 Dreem 创作者协作页面 | 2026-08-03 |
| 4 | Chat → Dream 跳转入口 = **Dream 审阅面板侧按钮**（挂在既有审阅面板/列表行），不做线程级常驻入口，也不新建 Chat 消息卡片 | 2026-08-03（2026-08-03 兼容性修订：原决策为「Chat 消息内卡片按钮」，因代码中不存在 Chat 消息流内的提案卡片挂靠点而改写，见 §9 DEC-031 修订注记与审计报告 C9） |

### 0.2 术语对照表（业务术语 → 技术命名）

> 术语表已收编至唯一权威来源 **`docs/architecture/术语表.md`**（按模块分类，含实现状态与 commit 追溯）。本文用到的 packer/workspace-init profile/launch-manifest/pack-receipt/插件制品/协议目录 `.ink/`/`.dream/`/`surfaces[]`/会话/run/Gate/Deck/Dream 提案生命周期帧/后端合同/attempt/supersede 等术语，见该文件 §1–§5。注意其中两条 2026-08-03 修订记录：pack 发生在首个 agent turn（审计 B6）；代码中不存在 Chat 消息流内的「提案卡片」（审计 C9）。

---

## 1. 背景与目标

### 1.1 背景

现行链路为「Agent 产出 → 页面渲染 → 用户修改并确认 → 同一 Chat Agent 后续执行」。用户在 Dream 页面修改整份内容，只确认一次。仍需说明两块：

1. **后续执行阶段如何从 Chat 对话跳转到 Dream 工作台**：Deck 加载的插件有特定的工作空间命名，需要增加固定的前缀协议目录（`.dream`），使系统可以判断一条会话要不要打开渲染页面。
2. **后续执行阶段的页面布局**：应参照调研 PDF 的创作者协作页面——数据/任务层与选中项聚焦上下文层；页面跟随同一 Agent 的工作空间写入。

### 1.2 目标

- 建立 `.dream` 协议目录合同：声明方、内容物、物理映射时机、透出链路、兼容行为。
- 建立 Chat → Dream 的入口链：可见条件、阶段文案、深链路由与 run 定位。
- 建立独立执行页：信息架构、数据层、工作空间持续更新，以及与一次“确认并继续”的关系。

---

## 2. 范围界定

### 2.1 范围内

- workspace-init profile 的 `surfaces[]` 扩展 schema、校验规则与错误码。
- `.dream/` 目录内容物、静态/运行期事实边界、Agent 侧读写约定。
- packer 物理映射 `.dream/` 与 launch-manifest / pack-receipt / `plugin-load-receipt` 端点的 `surfaces` 透出。
- Dream 入口按钮合同、四种阶段文案与深链行为。
- 独立执行页路由、布局线框、数据层与状态表。
- 命名清单、合同归属、验收标准、风险与 DEC 增量记录。

### 2.2 范围外

- 不实现代码、数据库、API、packer 或前端组件；阶段三另行规划。
- 不定义 workspace-init profile 的既有字段（runtime_dirs / workspace_files / python），只扩展 `surfaces[]`。
- 不定义执行引擎本身的步骤语义（Deck workflow 决定继续/结束，沿用基线）。
- 不新增移动端/平板端设计；不提供视频预览、上传、生成、播放器或模型计费。
- 不修改 `backend/database.py`，不新增审计 Schema / DDL。
- 不改变现有 Agent 故事产出 JSON 解析代码；目标态由同一 Chat Agent 的工作空间文件驱动页面，并在 Dream 入口增加 run 深链（§4）。
  > 旁注（2026-08-03 兼容性修订）：Agent 的故事产出 JSON 由后端从 assistant 全文解析（`backend/services/story_workspace/agent_integration.py:29-58`）并持久化为 `story_workspace_*` 表行；SSE 侧发出独立的 `story-workspace-output` 生命周期帧，前端收到后**不进消息气泡**（`frontend/src/components/chat/ChatPanel.tsx:421-424`），只驱动打开 Dream 审阅面板。代码中**不存在**「Chat 消息流中的提案消息类型」这一合同；提案的可见形态是 Dream 域审阅面板/列表行。原旁注「Dream 提案 JSON 合同属 Chat 域既有合同（SSE 消息流中的提案消息类型）」为错误表述，已按审计报告 C9 更正。

---

## 3. `.dream` 协议目录合同（历史摘要，canonical 见 design_006）

> **Canonical 边界（2026-08-04）**：本节保留 2026-08-03 的设计推导与 DEC 上下文；现行规范只认 [design_006](./design_006_dream-protocol-dir-mapping.md)。`dream-surface/v1` 静态启动层继续冻结；同一 Chat Agent 按插件约定通过会话工作空间更新 `.dream/runtime/`，`workspace.json` 仍不加入 run 级字段。

### 3.1 workspace-init profile 扩展：`surfaces[]`

**保持 `workspace-init/v1`，新增可选字段 `surfaces[]`，不升 v2。** v1 全部既有字段语义不变；无 `surfaces` 的 profile 行为与现状完全一致（复用 drama-forge 设计 §7「插件无 profile → 跳过」的兼容模式）；升 v2 会强迫所有存量 profile 与校验器同步迁移，收益为零。

```json
{
  "schema_version": "workspace-init/v1",
  "runtime_dirs": ["stories", "assets", "exports", ".dramaforge"],
  "workspace_files": [
    { "path": "CLAUDE.md", "source": ".ink/workspace-claude.md", "mode": "create-if-missing" }
  ],
  "python": { "requirements": "scripts/requirements.txt", "min_version": "3.11" },
  "surfaces": [
    {
      "name": "dream",
      "protocol_dir": ".dream",
      "entry_route": "/story-workspace/dream"
    }
  ]
}
```

校验规则（非法即 pack 失败 `WorkspacePackError("CLAUDE_PLUGIN_INIT_PROFILE_INVALID")`）：

| 字段 | 规则 | 理由 |
|------|------|------|
| `name` | 枚举白名单，当前仅允许 `"dream"`；未知 name 拒绝 | 防止插件私自圈占前端路由语义 |
| `protocol_dir` | 匹配 `^\.[a-z][a-z0-9-]*$`，单层；不得与保留目录 `.ink` / `.editor` / `.notion` 冲突 | 与既有协议目录命名先例一致 |
| `entry_route` | 必须以 `/story-workspace/` 开头 | surface 入口只指向 story-workspace 域 |
| 唯一性 | 同一 profile 内 `name` / `protocol_dir` 不得重复；多插件声明同名 surface 时按 pack 顺序前者胜出，receipt 记录冲突警告 | 冲突可审计、行为确定 |

`surfaces[]` 的 JSON schema 属 **launch 合同**，归 packer 模块（`backend/services/claude_plugin/`）；story-workspace 只 own surface 的业务语义消费，不反向 own 打包 schema。

### 3.2 `.dream/` 目录内容物

```text
.dream/
├── README.md          # 自述：目录用途、只读约定、投影入口、事实边界（≤40 行）
└── workspace.json     # 绑定事实，schema_version: "dream-surface/v1"
```

> 上述为 2026-08-03 的**静态启动层摘要**。2026-08-04 用户修订新增 `.dream/runtime/`：同一 Chat Agent 写 run context 与人物/场景/分镜 stage 文件；完整 schema 只以 `design_006` 为准，不在本历史摘要复制。

`workspace.json`：

```json
{
  "schema_version": "dream-surface/v1",
  "deck_id": "<deck id>",
  "plugins": [
    {
      "package_spec": "drama-forge@drama-studio",
      "artifact_digest": "sha256:…",
      "resolved_version": "1.0.1"
    }
  ],
  "entry_route": "/story-workspace/dream"
}
```

**字段边界：`workspace.json` 只含 pack 期可知的 launch 事实（deck_id、插件制品清单、入口路由），且不含时间戳——同一 digest 重 pack 产物必须字节一致。** `workflow_run_id`、`binding_revision`、`deck_runtime_snapshot_id`、`runtime_plugin_lock_id` 等 **run 级事实不进 workspace.json**：pack 发生在会话首个 agent turn（thread 创建仅锁定 `chat_thread.deck_id`，不分配工作区、不 pack，见 §3.4.1；2026-08-03 兼容性修订，审计报告 B6），run 此时尚未存在，写入即自相矛盾；这些事实由 `plugin-load-receipt` 端点与 story-workspace REST API 在运行期提供。

**静态 vs 运行期边界：packer 物理映射并冻结的是 `README.md + workspace.json` 静态启动层，而不是整个 `.dream` 根目录。** `.dream/runtime/` 由当前 Chat Agent 写 run/stage 文件，不参与 artifact digest，也不由冻结 pack 重建或删除。前端通过 actor-scoped REST 读取，不直接探测工作区。

### 3.3 与 `.editor` / `.notion` 先例的一致性

- `.dream` 是**真实文件**（packer 物理映射），不走 `.editor` 的 PreToolUse 钩子重定向虚拟索引模式——它无需映射到 EditorState，真实文件更简单且冻结友好。
- Agent 侧读取：与普通文件一致（Read 工具）；README.md 即协议说明；注入版工作区 CLAUDE.md 中加一行指向 `.dream/README.md`。
- 写权限：静态层只由 packer 写；当前 Chat Agent 只可通过 `StoryWorkspaceDreamFileWriter` 写 `.dream/runtime/**`。浏览器不直接读写工作区。

### 3.4 `.dream/` 生成逻辑（触发链路 / 输入来源 / 生成物全文 / 时序）

#### 3.4.1 触发链路（谁在什么时候生成 `.dream/`）

```text
用户在 Dream 页选 Deck、点击 Chat
  → POST /api/claude-agent/threads：仅校验 Deck 存在且 enabled，
    create_chat_thread 锁定 chat_thread.deck_id
    （backend/routers/claude_agent.py:435-468；此刻不分配工作区目录、不 pack）
  → 会话首个 agent turn（POST /api/claude-agent → assemble_context）：
    get_or_create_workspace 建目录后调 pack_workspace_plugins(workspace, deck_id)
    （backend/claude_agent/service.py:1172-1187；此后每个 turn 幂等重调，
     冻结语义保证等价于「生效一次」）
      ├─ 该 Deck 的插件制品均未声明 surfaces
      │    → 不生成 .dream/；会话为普通 Deck 对话，前端无 Dream 入口
      └─ 任一制品 profile 声明 surfaces 含 dream
           → 物理映射 .dream/（下方时序第 5 步）
           → launch-manifest / pack-receipt 写入 surfaces
  → 首个 turn pack 完成后，GET …/threads/{id}/plugin-load-receipt 透出 surfaces
    → 前端据此渲染 Dream 入口（§4）
```

静态启动层只在 **pack 时刻（会话首个 agent turn，非 thread 创建）**物理映射，不在 run 创建时或 Agent 运行中重写。**surfaces 首次可见时机 = 首个 agent turn pack 完成、manifest 落盘之后**；此前 `plugin-load-receipt` 返回 `workspace_found: false`（`backend/routers/claude_agent.py:500-507`），前端按「无 surface」处理。pack 完成后，同一 Chat Agent 才能按 `design_006` 写 `.dream/runtime/**`。（2026-08-03 兼容性修订：原表述「后端创建 thread → pack_workspace_plugins # 每个会话创建时执行一次」与代码事实不符，已按审计报告 B6 更正。）

#### 3.4.2 输入来源（每个字段从哪来）

| 生成物字段 | 来源 | 说明 |
|------------|------|------|
| 是否生成 `.dream/` | 制品内 `.ink/workspace-init.json` 的 `surfaces[]`（随 digest 固定） | 无声明 → 不生成，行为与现状一致 |
| `workspace.json.deck_id` | pack 入参（thread 创建时锁定的 deck_id） | 与 launch-manifest 的 deck_id 同值 |
| `workspace.json.plugins[]` | 时序第 2 步复制制品的结果（package_spec / artifact_digest / resolved_version） | 与 launch-manifest 的 plugins[] 同值 |
| `workspace.json.entry_route` | profile `surfaces[i].entry_route`（已通过 §3.1 校验） | 当前恒为 `/story-workspace/dream` |
| `README.md` 全文 | packer 内置静态模板（见 3.4.3） | 不含变量插值、不含时间戳 |
| manifest / receipt 的 `surfaces[]` | 各制品 profile 的 surfaces 经冲突裁决（§3.1）后合并 | 前端感知的唯一来源 |

`workspace.json` **不含** `workflow_run_id`、binding_revision、runtime snapshot、时间戳——pack 时 run 尚未创建；含时间戳会破坏「同一 digest 重 pack 字节一致」。

#### 3.4.3 生成物全文

`.dream/workspace.json` 见 §3.2。`.dream/README.md` 模板全文：

```markdown
# .dream/ — Dream Surface 协议目录

本目录由 packer 在会话首个 agent turn 的 pack 时物理映射到会话工作区，标识本工作区由 Dream 驱动插件加载。

- workspace.json：静态 launch 事实（deck_id、插件制品清单、入口路由）。
  它在 pack 后不再变化，不含 workflow_run_id 等 run 级事实。
- README.md 与 workspace.json 是静态启动层，Agent 不得修改。
- runtime/ 是 Agent 运行内容层；同一 Chat Agent 仅通过
  StoryWorkspaceDreamFileWriter 写入 run/stage 文件。
- Dream 页面经 story-workspace REST/SSE 安全读取，不直接访问文件系统。

入口路由：/story-workspace/dream
```

#### 3.4.4 生成时序

物理映射时机与 drama-forge 设计 §6 同一插槽：**复制制品之后、写 manifest 之前**。完整时序：

```text
pack_workspace_plugins()                       # 会话首个 agent turn 执行，其后每 turn 幂等重调（冻结语义）
 1. 读 deck refs（digest 固定）
 2. 校验制品 → 复制到 .ink/plugins/<spec>@<mp>@<digest>/
 3. 读制品内 .ink/workspace-init.json（无 profile → 跳过 4~6，行为与现状一致）
 4. 非冻结工作区：建 runtime_dirs；写 workspace_files（create-if-missing）
 5. profile.surfaces 非空 → 物理映射协议目录：
      .dream/README.md       # 3.4.3 静态模板，无时间戳
      .dream/workspace.json  # 3.4.2 来源组装：deck_id + plugins[] + entry_route
 6. profile.python 存在 → 确保受管 venv（懒创建，按 digest 缓存）
 7. 写 .ink/launch-manifest.json（含 surfaces[]）
 8. 写 .ink/plugin-pack-receipt.json（含 surfaces[] 与 init_steps 审计）
```

> 注（2026-08-03 兼容性修订，审计报告 A1）：上表为逻辑时序；**第 5 步在全部制品复制与 init（第 2~4 步的逐 ref 循环）完成后执行一次**——`workspace.json.plugins[]` 需要全量插件清单，而代码中 manifest 条目在逐 ref 循环内增量构建（`workspace_packer.py:192`），循环内物理映射会导致多插件 Deck 拿到不完整的 plugins[]。

| 规则 | 语义 |
|------|------|
| 仅非冻结执行 | 第 4~5 步只在首次 pack 执行；冻结分支不重复物理映射 |
| 冻结校验 | 已有 manifest 的工作区：仅校验 `.dream/workspace.json` 存在且与 manifest 中 surfaces 一致；缺失不重建（属初始化结果，非 venv 类派生缓存） |
| 幂等 | `create-if-missing`；同一 digest 重 pack 的 `.dream/` 产物字节一致（README 模板与 workspace.json 均不含时间戳） |
| 原子性 | 第 5 步采用「临时目录写入 → 校验两文件齐全 → `os.rename` 原子就位」；任一文件写失败 → 整个 pack 失败 `CLAUDE_PLUGIN_INIT_PROFILE_INVALID`，不留半截目录（2026-08-03 兼容性修订：采纳审计报告 A4 的 temp-dir + rename 方案，原子性要求不变、由实现保证） |
| 多插件 | 多个制品声明同名 surface 时按 pack 顺序前者胜出，receipt 记录冲突警告（§3.1） |

#### 3.4.5 manifest 透出

launch-manifest（`claude-launch/v1`）与 pack-receipt 同步增加紧凑形式：

```json
"surfaces": [
  { "name": "dream", "protocol_dir": ".dream", "entry_route": "/story-workspace/dream" }
]
```

**不在 manifest 中放执行页路由模板。** 执行页路由是 story-workspace 命名合同的一部分（§5.1），前端已知模板 `/story-workspace/runs/:storyWorkspaceRunId/execution`；manifest 只透传「surface 存在 + 入口」这一 launch 事实，避免同一事实两处 owner。

### 3.5 透出端点与兼容

- **透出端点（2026-08-03 兼容性修订，审计报告 B7）**：前端感知 surfaces 的载体是既有端点 `GET /api/claude-agent/threads/{thread_id}/plugin-load-receipt`（`backend/routers/claude_agent.py:471-523`）。该端点把 `.ink/launch-manifest.json` 与 `.ink/plugin-pack-receipt.json` **整文件透传**（`launch_manifest` / `receipt` 两个键，:509-522）——packer 一旦在 manifest/receipt 写入 `surfaces`，该端点**零改动**自动透给前端；前端取 `launch_manifest.surfaces`，兜底 `receipt.surfaces`。代码中不存在「与 plugins / receipt 同层的会话 payload」对象（`<workspace_context>` 是注入 agent 用户消息的提示块，不是前端 API payload），原表述已更正。
- **首次可见时机（2026-08-03 兼容性修订，审计报告 B6）**：pack 发生在会话首个 agent turn（§3.4.1）。thread 创建后、首个 turn pack 完成前，该端点返回 `workspace_found: false`、两个文件键为 `null`；前端一律按「无 surface」处理。
- **冻结 / 旧会话 manifest 无 `surfaces` 键时，端点原样返回无该键的 JSON，前端按「无 surface」处理：隐藏入口按钮，不报错、不补探测。** 前端零文件系统探测是已拍板决策，缺省即关闭是唯一安全的缺省。

---

## 4. Chat → Dream 跳转链（surface 入口）

> 代码中不存在 Chat 消息流内的 Dream 卡片；`story-workspace-output` 是不进消息气泡的 SSE 生命周期帧。既有 `StoryWorkspaceSurfaceLinkButton` 仍可作为 Dream surface 入口，但目标业务不再绑定逐项审阅状态；页面内容与一次“确认并继续”以 `design_006`/`design_007` 为准。

### 4.1 按钮合同

`StoryWorkspaceSurfaceLinkButton` 可见条件：

1. 当前 thread 经 `GET …/plugin-load-receipt` 透出的 `surfaces` 含 `name="dream"`（§3.5；面板所在会话上下文提供，前端不探测文件系统）；
2. 当前 Dream 上下文已绑定 `storyWorkspaceRunId`。

按钮状态由服务端结合 Dream stage 文件与 continuation 状态返回，前端不做文件探测或逐项 review 推断。

### 4.2 文案与跳转目标随阶段变化

| Dream 阶段 | 主按钮文案 | 目标 |
|---|---|---|
| required stage 文件未齐 | 查看 Dream 进度 | Dream run 页面 |
| required stage 文件已齐、尚未确认 | 打开 Dream | Dream 可编辑页面 |
| `continuing` | 查看执行进度 | 执行页深链 |
| `completed` | 查看执行结果 | 执行页深链 |

路由：

- Dream 深链：`/story-workspace/dream?run=:storyWorkspaceRunId`。
- 执行页深链：`/story-workspace/runs/:storyWorkspaceRunId/execution`。

### 4.3 深链上下文与 run 定位

- URL 必须携带 `storyWorkspaceRunId`（`?run=` query）。
- Dream 页加载时若 URL 带 `run` 参数，**以该 run 为选中上下文**而非默认最新 run；run 不存在或不属于当前用户 → 提示并回退默认。
- 深链只做初始定位；stage revision 由 `dream-files` 响应提供。
- 运行来源五字段（workflow_run_id 等）由页面按 run 拉取，不进 URL。

### 4.4 缺省态

| 场景 | 行为 |
|------|------|
| 会话无 dream surface（含首个 agent turn pack 完成前） | 不渲染按钮 |
| run 尚无 stage 文件 | 打开 Dream 后显示“等待 Agent 写入” |
| runId 缺失 | 退化为 Dream 主页，不猜测最新文件目录 |

---

## 5. 独立执行页 `/story-workspace/runs/:storyWorkspaceRunId/execution`

### 5.1 布局归属

**独立页面 = AppHeader（Dream 选中态）+ breadcrumb + 两层执行协作工作台，不嵌入 Dream 审阅三栏。** 第一层用于 Assets/Outline 定位，第二层用于查看当前叙事点或执行步骤的结构化上下文；确认后页面只跟随同一 Chat Agent 的工作空间更新。

2026-08-04 目标布局对齐 `调研Dreem_app平台.pdf` 第 3、6、7 页：第一层使用 `Assets / Outline` 索引定位叙事点或执行步骤；第二层由选中项打开上下文协作区。当前已实现的「左数据 Tabs + 常驻 360px 指导侧边栏」是过渡形态，任务三应调整为下述目标，不再把固定 360px 右栏当执行页最终合同。

```text
┌─ AppHeader：Dream（选中态） ─ breadcrumb：Dream / Runs / <runId> / 执行 ──────┐
├──────────────────────┬───────────────────────────────────────────────────────┤
│ 第一层索引            │ 第一层主工作面                                         │
│ Assets │ Outline     │ 运行摘要 · 阶段 n/N · 当前步骤 · 状态                   │
│                      │                                                       │
│ 故事线 / 资产分组     │ 叙事点 / 执行步骤轻纸面条目                            │
│ 节点数 / revision     │ 人物、场景、产物引用与 Agent 最新写入                    │
│                      │                                                       │
│ 运行记录入口          │ 选中条目 → 打开第二层上下文协作区                        │
├──────────────────────┴───────────────────────────────┬───────────────────────┤
│ 第二层：当前叙事点的结构化产物摘要 / 执行状态           │ 上下文协作区            │
│ 不含视频、上传、播放器或可编辑画布                      │ 结构化上下文与历史        │
└──────────────────────────────────────────────────────┴───────────────────────┘
```

PDF 取舍：采用「Assets / Outline 索引 → 叙事点/执行步骤 → 上下文协作区」操作动线；结构化产物摘要替代镜头预览，运行记录替代视频历史；舍弃视频预览、上传、播放器、外部模型选择与可编辑图库（沿用 design_003 §7.1）。视觉服从 `Ink & Memory UI Design v2.pdf` 第 4～5 页：Warm Canvas / Paper Cream、少面板、多留白、浅纸面分区、页面级单一虚线边界、静止条目无卡片阴影。

### 5.2 数据层

- **资产**：来自 Chat Agent 工作空间文件的角色 / 场景 / 分镜引用与 stage revision。
- **执行内容**：显示插件后续步骤持续写入的结构化文件和更新时间顺序。
- **运行历史**：只读展示确认与 Agent 后续写入，不提供新的内容处置动作。

### 5.3 既有 guidance 能力的适用说明

现有 guidance 端点和侧边栏实现保留为代码事实，但**不进入本次 Dream 主业务链**。目标流程只有“用户在 Dream 修改 → 一次确认并继续 → 同一 Chat Agent 后续执行”；执行页不追加业务操作或二次确认。后续若重新启用 guidance，必须另行评审，不从本设计推导。

### 5.4 执行页目标状态表

| UI 状态 | 进入条件 | 页面表现 | 可用动作 |
|---------|----------|----------|----------|
| `story-workspace-execution-continuing` | “确认并继续”已注入原 thread | Agent 持续写入 workspace，页面按 revision 刷新 | 查看 Assets / Outline |
| `story-workspace-execution-completed` | 执行完成 | 完成摘要、产物深链 | 查看、返回 Dream |
| `story-workspace-execution-not-confirmed` | 尚未提交一次“确认并继续” | 提示返回 Dream 完成修改 | 重定向 Dream run 页面 |

### 5.5 与一次确认的关系

- 执行页只承接第四步；未提交 `StoryWorkspaceDreamConfirmationCommand` 的 run 访问执行页时，重定向 Dream run 页面。
- 确认命令校验 required stages、base revisions 和幂等键，然后注入原 Chat thread。
- 同一 Chat Agent 先写入用户修改再继续；执行页不提供第二次确认或其他内容处置动作。

---

## 6. 命名与合同归属

| 类型 | 规范命名 |
|------|----------|
| 执行页路由 | `/story-workspace/runs/:storyWorkspaceRunId/execution` |
| Dream 深链 | `/story-workspace/dream?run=:storyWorkspaceRunId` |
| 页面组件 | `StoryWorkspaceExecutionPage` |
| 数据层组件 | `StoryWorkspaceExecutionProgressTable`、`StoryWorkspaceExecutionAssetPanel` |
| 聚焦上下文组件 | `StoryWorkspaceExecutionFocus` |
| 跳转组件 | `StoryWorkspaceSurfaceLinkButton` |
| UI 状态 | `story-workspace-execution-*`（§5.4） |
| 确认命令 | `StoryWorkspaceDreamConfirmationCommand` |
| 合同值对象 | `StoryWorkspaceSurface`、`StoryWorkspaceDreamStage` |
| 后端业务合同 | `backend/story_workspace/contracts.py` |
| 前端局部 REST 合同 | `frontend/src/hooks/story-workspace/contracts.ts` |
| launch 合同 | `surfaces[]` JSON schema 归 packer 模块（`backend/services/claude_plugin/`） |

禁止通用 `types` 路径承载本文任何业务合同；禁止兼容 re-export / alias / shim；`backend/database.py` 保持只读。

---

## 7. 验收标准

### 7.1 协议目录

- [ ] 含 `surfaces` 的 profile 经 pack 后，工作区出现 `.dream/README.md` + `workspace.json`；`workspace.json` 含 deck_id 与插件制品清单（spec / digest / version），不含 run 级事实与时间戳。
- [ ] 同一 digest 重 pack 的 `.dream/` 产物字节一致；冻结工作区不重复物理映射，仅校验一致性。
- [ ] 无 `surfaces` 的旧 profile / 冻结会话行为与现状完全一致。
- [ ] 非法 surface（保留目录冲突 / 越界 entry_route / 未知 name）pack 失败并报 `CLAUDE_PLUGIN_INIT_PROFILE_INVALID`。
- [ ] launch-manifest 与 pack-receipt 透出 `surfaces`；`plugin-load-receipt` 端点同步透出；旧会话与首个 agent turn pack 完成前缺省隐藏入口。

### 7.2 跳转链

- [ ] 有 / 无 surface 的会话分别显示 / 隐藏 `StoryWorkspaceSurfaceLinkButton`；四种阶段文案与目标正确。
- [ ] 带 `?run=` 深链打开 Dream 页定位指定 run 而非默认最新 run。
- [ ] 入口携带当前 run，前端不猜测最新工作区目录。

### 7.3 执行页

- [ ] 未提交“确认并继续”时访问执行页，重定向对应 Dream run 页面。
- [ ] 确认命令幂等注入原 Chat thread，同一 Agent 写入用户修改后继续。
- [ ] 执行页只展示 Agent 后续写入，不提供第二次确认或其他内容处置动作。

### 7.4 命名与视觉

- [ ] 全部新符号带 `story-workspace` / `StoryWorkspace*` 前缀；合同只归两个 canonical 文件；`backend/database.py` 未改、无新 DDL。
- [ ] 视觉符合 UI Design v2（暖纸、少面板、无视频控件、表格替代画布）；AppHeader Dream 保持选中态。

---

## 8. 风险与依赖

| 风险 / 依赖 | 影响 | 处理 |
|-------------|------|------|
| workspace-init profile / dream surface 声明发生漂移 | `.dream` 物理映射与入口发现不一致 | 当前 profile 解析、`surfaces[]` 校验与物理映射已实现；后续变更以 design_006 为 canonical，并保留无 surface 缺省隐藏 |
| 旧会话无 `surfaces` 字段（含 thread 创建后、首个 agent turn pack 完成前） | 入口不一致 | 缺省即隐藏，不补探测；行为文档化（§3.5） |
| 深链 `?run=` 与 stage revision 漂移 | 用户基于旧版本确认 | 确认时校验 base revisions；深链只做初始定位 |
| Dream 页面与 Agent 同时更新内容 | 本地修改被覆盖 | 前端保留本地草稿，发现新 revision 后要求重新核对合并 |
| 插件声明恶意 / 未知 surface | 前端路由语义被圈占 | name 枚举白名单 + entry_route 前缀校验，pack 期拒绝 |
| `.dream/workspace.json` 被误当运行内容 | run 级信息缺失 | README 与 §3.2 明确静态/运行层分工；页面经 actor-scoped REST 读取 runtime 文件 |
| 多插件声明同名 surface | 行为不确定 | pack 顺序前者胜出 + receipt 冲突警告（§3.1） |

---

## 9. 关键决策记录（增量）

| 决策 ID | 日期 | 决策 | 原因 | 影响 |
|---------|------|------|------|------|
| DEC-027 | 2026-08-03 | `.dream` surface 由插件制品 workspace-init profile 的 `surfaces[]` 声明，随 digest 固定；profile 保持 v1 不升级 | 「哪些会话算 Dream 驱动」是制品事实；可选字段零迁移成本 | packer、profile 校验、Deck 引用 |
| DEC-028 | 2026-08-03 | surface 经 launch-manifest / pack-receipt / 会话 API 透出；旧会话缺省隐藏，前端不探测文件系统 | manifest 是 launch 唯一事实源；缺省关闭最安全 | 会话 payload、前端入口显隐 |
| DEC-029 | 2026-08-03 | `.dream/` 全部为 packer 物理映射的静态 launch 事实（deck_id、插件制品清单、入口路由），运行期不回写；`workflow_run_id` 等 run 级事实不进文件，只认 REST API | pack 时 run 尚未创建，写入即矛盾；维护工作区冻结语义与 digest 不变量 | workspace.json 合同、README 边界、生成时序 |
| DEC-030 | 2026-08-03 | 后续执行使用独立执行页（AppHeader + 自有双区），不嵌入 Dream 三栏 | 审阅右栏与指导侧边栏是两种职责，不可混用 | 路由、布局、状态表 |
| DEC-031 | 2026-08-03 | Chat 跳转入口为 Dream 提案消息卡片按钮，文案与目标随 Gate 阶段由服务端聚合返回 | 入口与具体产出绑定；前端不做状态推断 | 卡片合同、深链行为 |
| DEC-032 | 2026-08-03 | 指导指令复用发起 run 的同一 Chat thread 作传输通道但不渲染为 Chat 消息；审计复用 ReviewEvent / ExecutionGateRecord 信封，不新增 DDL | 避免双入口写混淆；`backend/database.py` 只读 | 指导链路、审计合同 |
| DEC-033 | 2026-08-04 | `.dream` 分为冻结静态启动层和 Chat Agent 运行内容层；同一 Agent 按插件约定写人物、场景、分镜 stage 文件，用户修改后一次“确认并继续”，随后原 Agent 继续 | 用 workspace 文件直接驱动页面并保持四阶段主链简单 | runtime schema、G3/G5、确认命令、页面刷新 |

### 2026-08-03 兼容性修订注记（任务二）

> 以下注记保留原决策文本不变，仅追加修订说明与原因；依据为审计报告 [2026-08-03-dream-surface-audit-report.md](./2026-08-03-dream-surface-audit-report.md)。

- **DEC-028（2026-08-03 修订，审计报告 B6/B7）**：「会话 API 透出」明确为既有端点 `GET /api/claude-agent/threads/{thread_id}/plugin-load-receipt`（整文件透传 launch-manifest 与 pack-receipt，`backend/routers/claude_agent.py:471-523`），该端点零改动自动携带 `surfaces`；代码中不存在原设想的「与 plugins/receipt 同层的会话 payload」对象。另补充时序：pack 发生在会话首个 agent turn 而非 thread 创建，surfaces 首次可见时机 = 首个 turn pack 完成之后，此前（`workspace_found: false`）与旧会话一律按无 surface 缺省隐藏——与「缺省即隐藏」决策同向，仅细化触发时机。
- **DEC-029（2026-08-03 修订，审计报告 B6）**：决策内容不变（`.dream/` 全静态、run 级事实不进文件）；仅修正其背景表述——pack 时刻是「会话首个 agent turn」而非「会话创建」（thread 创建仅锁定 `chat_thread.deck_id`，`backend/routers/claude_agent.py:435-468`；pack 调用点 `backend/claude_agent/service.py:1172-1187`）。「pack 时 run 尚未创建」的结论在两个时序下均成立。
- **DEC-031（2026-08-03 修订，审计报告 C9）**：跳转入口由「Dream 提案消息卡片按钮」改写为「**Dream 审阅面板侧按钮**」（挂 `StoryWorkspaceReviewDetail` 提案详情区与故事列表行操作列）。原因：代码中不存在 Chat 消息流内的提案卡片——`story-workspace-output` 是不进消息气泡的 SSE 生命周期帧（`frontend/src/components/chat/ChatPanel.tsx:421-424`），提案的可见形态是审阅面板/列表行；新建 Chat 卡片会引入第二条渲染链路与新 Chat 域消息合同，成本与风险均高于复用既有面板。「文案与目标随 Gate 阶段由服务端聚合返回、前端不做状态推断」维持不变。
- **DEC-032（2026-08-03 修订，审计报告 D11/D12/D13）**：「复用 thread 传输但不渲染」的承载方式明确为：指导以 `metadata.kind="story-workspace-guidance"` 标记的 user 消息落 `chat_message` 表（metadata 列与 `save_chat_message(metadata=...)` 均已存在，`backend/database.py:603-611`、:4249-4296），Chat 视图在消息消费层按 kind 过滤不渲染；指导历史按 kind 反查。幂等键作 `chat_message.id`（`INSERT OR REPLACE` 去重），服务层先查比对，同键不同内容返回 409。审计字段（actor / run / request ID / timestamp）承载于同一 metadata。`awaiting-guidance` 为投影态而非 `RunStatus` 新枚举。「不新增 DDL」维持不变。

### 2026-08-04 专项修订注记

> 以下继续遵循“保留原决策文本，只追加修订说明”的惯例；依据为任务一实施记录、`design_006`、Dreem 调研 PDF 第 3～7 页与 Ink & Memory UI Design v2.1 第 4～5 页。

- **DEC-029（2026-08-04 修订）**：决策内容不变，并明确否决“人物、场景、分镜生成期向 `.dream/` 追加元信息”与“把 `workflow_run_id`、运行来源五字段、`projection_entry` 写入 `workspace.json`”。drama-forge 上游没有 `.dream` 写行为；其分镜唯一源为 `stories/<project>/episodes/EP??/storyboard.yaml`，内部运行产物与报告位于 `.dramaforge/runs/<internal_run_id>/{artifacts,reports}/`。动态事实继续通过 Agent 输出解析、story-workspace 数据库、SSE 与 actor-scoped REST API 消费；`.dream` 完整合同迁移至 design_006。
- **DEC-030（2026-08-04 修订）**：“独立执行页、不嵌入 Dream 审阅三栏”的原则不变；内部布局由「通用数据层 + 常驻 360px 指导栏」调整为“两层执行协作工作台”：第一层 `Assets / Outline` 索引与叙事点/执行步骤主工作面，第二层为选中项触发的上下文协作区。该修订对齐调研 PDF 的定位—协作动线，同时用 UI Design v2.1 的暖纸、轻纸面、无卡片规则替换截图视觉；视频、上传、播放器仍排除。

### 2026-08-04 用户审阅二次修订注记

> 用户要求明确人物、场景、分镜生成阶段与 `.dream` 的更新关系，并补齐业务交互时序。以下注记保留 DEC-029 原文和上一条修订的历史，不静默覆盖；现行合同以本注记、DEC-033、`design_006` 和 `design_007` 为准。

- **DEC-029（二次修订）**：把原文“.dream 全部静态”的适用范围缩窄为 `.dream/README.md + workspace.json` 静态启动层；`workspace.json` 仍不含 run 级字段且保持冻结。新增 `.dream/runtime/`，由同一 Chat Agent 按插件步骤通过工作空间写 `run.json` 与人物/场景/分镜 stage 文件。run/source 字段与 `projection_entry` 写入运行层，而非 `workspace.json`。前端经 REST/SSE 读取，不直读文件。
- **DEC-033（最终用户修订）**：不采用 host event/projection 状态机。stage 文件存在且有效即页面可渲染；用户只在整份 Dream 中修改内容并一次“确认并继续”，确认作为隐藏消息注入原 Chat thread，同一 Agent 写入修改后继续后续执行。不设计逐项确认、驳回、失败、重试或归档业务分支。

---

## 10. 相对基线的增量变更说明

| 基线稳定项 | 本文新增 / 变化 | 未改变内容 |
|------------|----------------|------------|
| 顶部 Dream 导航与 canonical 路由 | 新增执行页路由与 `?run=` 深链定位语义 | Dream 入口、选中态、兼容重定向 |
| 四阶段主链 | 整份 Dream 修改后一次“确认并继续”，随后同一 Chat Agent 后续执行 | 不采用逐项审批 |
| 确认前三栏 240 / 自适应 / 360 | 执行页独立两层协作工作台（索引 + 主工作面；选中项上下文协作区） | Dream 三栏骨架；右栏改为内容编辑器 |
| workspace-init profile（v1） | 新增可选 `surfaces[]` 字段与校验规则 | v1 既有字段语义、受管 venv、冻结语义 |
| launch-manifest（claude-launch/v1） | 新增 `surfaces` 透出字段，经既有 `plugin-load-receipt` 端点整文件透传到前端 | deck_id、plugins[]、receipt 既有字段 |
| `.dream` 静态启动层 | 新增 `.dream/runtime/`：Agent 写 run.json 与 stages/*.json，revision 驱动页面刷新 | `workspace.json` v1 字段、digest、冻结与 surface 发现不变 |
| 确认传输 | `StoryWorkspaceDreamConfirmationCommand` 作为隐藏消息注入原 thread | 不新增 Schema / DDL；`backend/database.py` 只读 |
| 排除平台视频 | 执行页同样排除视频预览 / 上传 / 播放器 | 无视频能力边界 |
| PDF 调研取舍 | 采用创作者协作页「数据/任务层 + 聚焦上下文层」；舍弃视频与可编辑图库 | design_003 §7.1 既有取舍 |

---

## 11. 阻塞或澄清说明

当前无阻止 design 完成的外部 blocker。以下按默认假设收敛，后续若合同明确则在同一 Design ID 下增量修订：

- `surfaces[]` 当前仅定义 `dream` 一个枚举值；未来新增 surface 需在同一 schema 下扩展白名单并补充对应协议目录合同。
- 既有 guidance 能力不进入本次主业务链；后续若重新启用需独立评审。
- 当前 Chat Agent 只可通过 `StoryWorkspaceDreamFileWriter` 写 `.dream/runtime/**`；静态启动层继续禁止 Agent 修改，任务三需测试路径与 revision 边界。
- 执行页数据层的「执行步骤」粒度由 Deck workflow 快照决定；本页只消费投影，不定义步骤语义。
