# Story Workspace PRD — Dreem 创作者 Workspace 设计

> **Design ID**: `design_001_story-workspace-prd`  
> **关联 Issue**: [SUO-199](/SUO/issues/SUO-199)  
> **增量 Issue**: [SUO-214](/SUO/issues/SUO-214)、[SUO-230](/SUO/issues/SUO-230)、[SUO-236](/SUO/issues/SUO-236)、[SUO-298](/SUO/issues/SUO-298)
> **父 Issue**: [SUO-198](/SUO/issues/SUO-198)  
> **设计阶段**: design → issue → task → stage  
> **最后更新**: 2026-08-01  
> **设计负责人**: DesignArchitect  

---

## 1. 背景与目标

### 1.1 背景

Ink & Memory 是一个以「暖纸张、手写、安静工具台」为产品气质的原创潮玩 IP 品牌平台。当前平台已具备 Chat 对话工作区、Deck 编辑器、Claude Agent 会话、Workspace 文件管理、Notion 资源连接器等核心能力。

随着平台发展，创作者需要一个集中管理工作区来组织故事/剧本创作资产。参考 Dreem 创作者平台的 World Builder、角色系统、资产协作页等模式，结合 Ink & Memory 的品牌视觉体系，设计本平台的创作者 workspace。

### 1.2 设计目标

- 为创作者提供一个**审阅 Agent 产出的剧本工作空间**，而非手动创作工具
- 核心工作流：**创作者在 Deck 中配置并选择 Deck 插件 → story-workspace 执行 `WorkflowPreflight`（调用 Deck 解析运行配置并锁定快照）→ Claude Agent 按所选工作流产出剧本 → 页面渲染 → 用户审阅确认 → 所选工作流继续或结束**
- 在现有全局顶部导航提供 **Dream** 入口，并把 Claude Agent 产出、页面渲染、用户审阅与确认 gate 收拢到同一个 `story-workspace` 页面域
- 遵循 Ink & Memory UI Design v2 的视觉体系（暖纸张、轻纸面分区、无卡片设计）
- 本期聚焦布局骨架与基础交互，复杂画布以数据表形式呈现
- 所有业务路径、路由、包名、组件标识使用 `story-workspace` 前缀

---

## 2. 范围界定

### 2.1 范围内（本期实现）

| 模块 | 说明 |
|------|------|
| Workspace 布局骨架 | 三栏桌面端布局、导航、侧边栏、主内容区 |
| **全局顶部 Dream 入口** | **在现有 AppHeader / TopNavBar 增加 Dream 导航项，定义目标路由及选中、未选中状态** |
| **Agent 产出渲染** | **剧本/角色/场景由 Agent 自动生成，页面负责渲染展示** |
| **审阅确认流程** | **用户查看 Agent 产出 → 确认通过 / 提出修改 / 重新生成** |
| **Dream 页面审阅 gate** | **Dream 页面持续展示运行与审阅阶段；全部必审产出确认前，后续工作流保持锁定** |
| **Deck 工作流选择与执行前校验** | **选择已发布、可用的 Deck 插件；展示其版本及 Deck 运行配置就绪状态；执行记录保留来源快照** |
| 故事/剧本列表 | 数据表格呈现 Agent 产出的剧本，展示生成状态 |
| 角色资产管理 | 展示 Agent 生成的角色列表，支持审阅编辑 |
| 场景资产管理 | 展示 Agent 生成的场景列表，支持审阅编辑 |
| 空态/加载/错误/选中态 | 各模块的完整状态设计，含 Agent 生成中状态 |
| 桌面端布局 | 固定三栏桌面端布局，无响应式适配需求 |

### 2.2 范围外（本期不实现）

| 模块 | 说明 | 后续计划 |
|------|------|----------|
| **用户手动创建故事/角色/场景** | **本期内容由 Agent 产出，用户仅审阅确认** | 后续迭代考虑手动创建 |
| 复杂画布编辑器 | 故事板/时间线可视化编辑 | 后续迭代，本期以表格呈现 |
| 视频生成模块 | 镜头生成、视频预览 | 明确排除 |
| 计费/积分系统 | 积分消耗策略 | 后续迭代 |
| 移动端适配 | 完整移动端交互 | 本期明确排除，仅桌面端 |
| 实时协作 | 多创作者同时编辑 | 后续迭代 |
| **Deck 编辑器内部编辑能力** | **Deck 插件的工作流编排、发布、版本管理，以及 Agent 提示词、模型/工具策略、secret-ref 和插件运行配置均由 Deck 负责；story-workspace 仅消费可选择版本、快照引用和脱敏状态** | **由 Deck 模块独立设计与实现** |

---

## 3. 方案摘要

### 3.1 核心设计决策

| 决策 ID | 决策内容 | 理由 |
|---------|----------|------|
| DEC-001 | 采用「轻纸面分区」布局，无卡片堆叠 | 对齐 Ink & Memory UI v2 设计原则 |
| DEC-002 | 复杂画布以数据表呈现，不实现可视化编辑 | 本期范围约束，降低实现复杂度 |
| DEC-003 | 三栏桌面布局：左侧导航 + 中间内容 + 右侧详情 | 参考 Dreem 创作者协作页结构，符合内容创作工具惯例 |
| DEC-004 | 使用 `story-workspace` 前缀命名所有业务标识 | Issue 要求，确保命名空间隔离 |
| DEC-005 | 排除视频模块 | 父 Issue SUO-198 范围约束 |
| DEC-006 | **仅桌面端设计，不包含任何移动端/平板端适配** | **2026-08-01 评论确认：「没有移动端设计，也没用移动端」** |
| **DEC-007** | **核心工作流：Agent 产出 → 页面渲染 → 用户审阅确认 → 执行** | **2026-08-01 评论确认：「交互流程应该是 Agent 产出剧本工作空间，然后页面渲染剧本信息，用户确认，后续执行」** |
| **DEC-008** | **用户不手动创建内容，仅对 Agent 产出进行审阅、编辑、确认** | **业务需求明确：页面渲染 Agent 产出，用户确认后执行** |
| **DEC-009** | **Deck 是唯一业务模块；Deck Editor、Deck Plugin、Deck 运行配置与 binding 是其内部职责，story-workspace 只消费公开合同并保存运行/结果，不编辑 Deck 定义或配置** | **落实 Deck-only 领域边界，关闭独立配置 owner 假设** |
| **DEC-010** | **每次创作锁定 Deck 插件版本、`deck_runtime_snapshot_id` 与 `runtime_plugin_lock_id`；切换只影响新执行** | **保证同一剧本可复现、历史产出可溯源** |
| **DEC-011** | **Deck release、运行配置、权限或 runtime preflight 任一不通过时禁止启动 Claude Agent** | **避免以默认工作流或不完整配置静默执行** |
| **DEC-019** | **按 SUO-235 将提示词、运行配置、secret-ref、权限与不可变快照统一归属 Deck** | **统一字段、错误码、participant 和下游 owner** |
| **DEC-017** | **全局 Dream 导航以 `/story-workspace/dream` 为 canonical 入口，既有 `/story-workspace/dashboard` 只作兼容重定向** | **形成确定导航合同，同时保留已完成 story-workspace 路由的兼容性** |
| **DEC-018** | **Dream 页面设置运行级审阅 gate；全部必审产出确认前禁止工作流继续或结束** | **让“用户确认后才执行”成为可见且不可绕过的业务约束** |
| **DEC-026** | **story-workspace 业务合同按领域归属：后端统一放在 `backend/story_workspace/contracts.py`，前端局部 REST 合同统一放在 `frontend/src/hooks/story-workspace/contracts.ts`；禁止用通用 `types` 目录承载** | **避免顶层 `backend/types/` 遮蔽 Python 标准库 `types`，并让合同 owner 可定位** |

### 3.2 从 Dreem 提取的参考点与适配差异

| Dreem 功能 | 本平台适配 | 差异说明 |
|------------|-----------|----------|
| World Builder（三步审核流程） | **Agent 产出 → 审阅确认工作流** | **核心差异：Dreem 是手动构建，本平台是 Agent 自动生成 + 用户审阅** |
| 角色六可视化模块（面部/身体/情绪/服装/贴纸/道具） | 角色属性表格展示 Agent 生成结果 | 本期以数据表呈现，后续迭代可视化编辑 |
| @提及系统 | 暂不实现 | 后续迭代考虑 |
| Dreem Agent 一键生成 | **本平台核心工作流：Agent 产出剧本** | **Agent 生成是起点，非后续迭代** |
| 镜头生成与预览 | 排除 | 本期明确排除视频模块 |
| 交互控件/故事线分支 | 以表格字段呈现选项 | 简化成交互类型字段 |
| 积分制计费 | 排除 | 后续迭代 |

**关键差异说明**：
- Dreem 是「创作者手动构建世界」的工具，本平台是「Agent 产出内容，用户审阅确认」的协作界面
- Dreem 的创建流程是用户主动发起，本平台的内容由 Agent 自动生成后推送给用户审阅
- 本平台的用户操作以「确认 / 驳回 / 编辑」为主，而非「创建 / 删除」

### 3.3 Dreem 截图视觉参考分析

以下分析基于 Dreem 调研 PDF 中的实际截图，提取其布局结构、组件样式与交互模式，作为本平台设计的直接参考。

#### 3.3.1 创作者协作页布局（PDF 第 3-4 页截图）

**Dreem 截图特征**：
- **三栏布局**：左侧窄边栏（图标导航）+ 中间资产列表 + 右侧详情/预览
- **资产分类**：Characters / Locations / Script / World assets 分组展示
- **资产卡片**：缩略图（头像/场景图）+ 名称 + artifact 数量
- **面包屑导航**：`< Ordinary Waiting Day > Storylines > A`
- **标签切换**：Assets / Outline 标签页

**本平台适配**：
- ✅ 采纳三栏布局结构（Sidebar 240px + Main + Detail Panel 360px）
- ✅ 采纳资产分组展示模式（故事 / 角色 / 场景 分组）
- ✅ 采纳缩略图 + 名称 + 数量的卡片信息密度
- ❌ 不采纳 Dreem 的暗色主题（本平台使用暖纸色浅色主题）
- ❌ 不采纳面包屑导航（Sidebar 导航替代）
- ❌ 不采纳 World assets 分组（本期排除视频/世界构建）

#### 3.3.2 角色资产页布局（PDF 第 3 页截图）

**Dreem 截图特征**：
- **左侧属性面板**：角色名称、身份、性格、背景等字段
- **中央大图区**：角色主图 + 四视角转面图（正面/侧面/背面）
- **标签系统**：角色属性以标签形式展示
- **可维护三视图**：人物三视图维护入口

**本平台适配**：
- ✅ 采纳左侧属性面板结构（对应 Detail Panel 表单）
- ✅ 采纳角色字段体系（名称、身份、性格、背景、口头禅）
- ✅ 采纳标签系统（性格标签以胶囊标签展示）
- ❌ 不采纳四视角转面图（本期仅支持单张头像，四视角为后续迭代）
- ❌ 不采纳人物三视图（本期以数据表呈现）
- ❌ 不采纳 Dreem 的大图居中布局（本平台以表格列表 + 右侧详情面板替代）

#### 3.3.3 场景资产页布局（PDF 第 4 页截图）

**Dreem 截图特征**：
- **场景缩略图网格**：多场景以缩略图网格展示
- **场景详情面板**：场景名称、描述、关联角色
- **添加场景**：通过添加按钮创建多个场景布局

**本平台适配**：
- ✅ 采纳场景列表 + 详情面板的结构
- ✅ 采纳场景描述 + 关联角色的字段设计
- ❌ 不采纳缩略图网格（本期以表格列表呈现，网格视图为后续迭代）
- ❌ 不采纳场景布局可视化（本期以数据表呈现）

#### 3.3.4 故事线/叙事点布局（PDF 第 6 页截图）

**Dreem 截图特征**：
- **左侧故事线列表**：Late Start, Dull Ache / The Interview... / Bug Report...
- **右侧叙事点分组**：与故事线相关的叙事点窗口
- **节点计数**：每个故事线显示 nodes 数量（如 "4 nodes"）
- **镜头呈现文稿**：点击叙事点展开镜头描述

**本平台适配**：
- ✅ 采纳「故事线 → 叙事点」的层级概念（对应故事 → 场景的层级）
- ✅ 采纳节点计数展示（对应角色数/场景数字段）
- ❌ 不采纳故事线可视化编辑（本期以表格呈现，后续迭代）
- ❌ 不采纳镜头文稿呈现（本期排除视频模块）

#### 3.3.5 交互控件/决策点布局（PDF 第 7-8 页截图）

**Dreem 截图特征**：
- **决策控件**：Hold 1500ms → Into the Afternoon 选项
- **选项编辑**：可添加/编辑交互选项
- **预览窗口**：镜头预览 + 控件叠加
- **历史版本**：History / version 切换

**本平台适配**：
- ✅ 采纳「选项/决策」概念（以故事内容中的交互类型字段记录）
- ❌ 不采纳可视化决策控件（本期以纯文本/Markdown 记录）
- ❌ 不采纳预览窗口（本期排除视频模块）
- ❌ 不采纳历史版本（后续迭代）

#### 3.3.6 创作台页布局（PDF 第 2 页截图）

**Dreem 截图特征**：
- **左侧大纲导航**：故事结构大纲
- **中间主编辑区**：剧本内容编辑
- **右侧属性面板**：场景、人物、故事大纲属性
- **底部进度栏**：创作进度指示

**本平台适配**：
- ✅ 采纳「大纲 → 内容 → 属性」的三区结构
- ✅ 采纳左侧导航 + 中间内容 + 右侧属性的布局
- 🔄 **适配智能体驱动表单**：本平台的 Agent 产出内容在此区域渲染展示，用户审阅确认
- ❌ 不采纳底部进度栏（本期简化）
- ❌ 不采纳 Dreem 的手动编辑为主模式（本平台以审阅确认为主）

### 3.4 Dreem → Ink & Memory 视觉适配对照表

| Dreem 截图元素 | Dreem 风格 | Ink & Memory 适配风格 |
|----------------|-----------|----------------------|
| 主题 | 暗色/浅色双主题 | 暖纸色浅色单主题（Warm Canvas #F6EFE5） |
| 边栏 | 窄图标边栏（~60px） | 240px 文字边栏（图标+文字） |
| 资产卡片 | 缩略图+名称+数量 | 表格行：头像+名称+字段+操作 |
| 选中态 | 背景色块高亮 | 右侧 2px Action Brown 竖线 |
| 按钮 | 橙色强调（#FF6B35） | Action Brown #5F4A36 |
| 标签 | 圆角胶囊，深色底 | 圆角胶囊，Paper Cream 底 |
| 分割线 | 实线细边框 | Border Paper #D8C7B3 虚线 |
| 字体 | 系统无衬线 | 系统无衬线 + Excalifont 标题 |

### 3.5 Deck / Ink-Dream 关系声明

#### 3.5.1 术语映射（保留原始概念）

| 用户原始术语 | 本设计中的明确含义 | 不等同于 |
|--------------|-------------------|----------|
| **Deck 模块** | 唯一业务模块和配置控制面；拥有插件工作流、Deck Plugin Binding、Agent profile、提示词、模型/工具策略、插件运行配置、secret-ref、权限和不可变运行快照 | story-workspace、Claude Agent |
| **Deck 编辑器** | Deck 内部的创作、校验、发布和运行配置界面 | 可被选择执行的 Deck 插件实例及 Deck 运行配置 |
| **Deck 插件** | Deck 发布的、可选择且带版本的创作工作流定义；描述步骤顺序、输入要求和运行配置合同 | 不是独立配置域，也不是 story-workspace 页面 |
| **Ink-Dream 模块** | 本文中的 `story-workspace` 业务域；负责工作流选择上下文、preflight、执行状态、产出渲染、审阅与溯源 | Deck 配置编辑界面 |
| **Claude Agent / `claude-agent`** | 运行时执行者；根据所选 Deck 插件和锁定的 Deck 运行快照生成剧本/角色/场景 | 工作流定义、配置存储或业务结果真相源 |

> **关系结论**：Deck 同时定义“按什么工作流执行”“用什么提示词、插件配置及权限策略执行”，并权威保存下一次运行的 binding；story-workspace 提供选择交互并管理“发起哪次运行、运行到什么状态、产出了什么以及用户如何审阅”。两者通过不可变 Deck 运行快照协作，不复制敏感配置。

#### 3.5.1.1 技术命名索引（代码对齐，2026-08 核实）

> 技术命名索引已收编至唯一权威来源 **`docs/architecture/术语表.md`**（按模块分类，含实现状态与 commit 追溯）。上表业务术语对应的技术命名见该文件：Deck 模块 → §1；Ink-Dream/story-workspace 与 `workflow_run_id`/preflight/`review_status` → §4–§5；Claude Agent 与每线程会话工作区 → §3；Agent profile 与 workspace-init profile 的区分 → §1/§2。本 PRD 正文与设计决策不变。

#### 3.5.2 职责与数据所有权

| 模块 | 负责 | 权威数据/配置来源 | 明确不负责 |
|------|------|------------------|------------|
| Deck | 维护 Agent 提示词、插件配置、权限策略及其版本；自定义、校验、发布 Deck 插件；权威保存 Deck Plugin Binding；为 preflight 生成不可变运行快照 | Deck 目录、binding、发布记录与运行配置存储 | 剧本产出和审阅状态 |
| Deck Editor | 提供 Deck 工作流与运行配置的编辑/发布 UI | Deck 领域数据 | 独立业务模块或 API owner |
| Deck Plugin | 定义版本化创作流程、输入约束、步骤和 Deck runtime contract | Deck 发布版本 | 持久化剧本资产、绕过 Deck 权限 |
| story-workspace | 列出/选择可用 Deck 插件（选择写入 Deck 权威 binding），调用 preflight，记录运行与来源，渲染并审阅 Agent 产出 | Deck 目录/binding + runtime readiness + story-workspace 运行/内容数据 | 权威保存 Deck binding，编辑 Deck 工作流、提示词或运行配置 |
| Claude Agent | 使用已锁定的工作流版本、Deck 运行快照与 runtime lock 执行 | 单次执行上下文 | 自行选择工作流、静默补齐缺失配置 |

#### 3.5.3 数据与配置交互合同

单次创作至少携带以下关联信息；字段名是跨模块语义合同，具体 API/存储形态由下游技术设计确定：

| 信息 | 来源 | story-workspace 的处理 |
|------|------|------------------------|
| `deck_plugin_id` / `deck_plugin_version` | Deck 可用插件目录 | 选择时展示；启动时锁定；历史产出只读保留 |
| `deck_plugin_binding_id` / `binding_revision` | Deck Plugin Binding | 选择时通过 Deck API 更新；运行时冻结精确 ID/revision，不在本域建立第二份 binding |
| `workflow_definition_ref` | Deck Plugin 发布版本 | 传给 Claude Agent，不在 story-workspace 内编辑 |
| `deck_runtime_snapshot_id` | `WorkflowPreflight` 调用 Deck 生成 | 仅保存受控引用与版本；不复制或展示敏感配置值 |
| `runtime_plugin_lock_id` | Deck Plugin 发布锁 | preflight/run 保存不可变引用；历史来源只读展示 |
| `deck_runtime_snapshot_contract` / 脱敏 readiness | Deck 运行快照 | 仅用于兼容判定和“已就绪/缺失/无权限”展示；提示词、插件配置及 secret-ref 由 Claude Agent 按 `deck_runtime_snapshot_id` 服务端解析 |
| `workflow_run_id` / `status` | story-workspace / 执行服务 | 用于进度、失败重试、审计和产出关联；`pending_review` 为唯一 API 审阅态 |
| 剧本、角色、场景及 `review_status` | Claude Agent → story-workspace | 持久化并进入现有审阅流程 |

**版本规则**：创作者切换 Deck 插件或插件版本时，只改变下一次执行；既有剧本继续关联原 `deck_plugin_binding_id + binding_revision`、`deck_plugin_version`、`deck_runtime_snapshot_id` 与 `runtime_plugin_lock_id`。驳回后默认沿用原快照/锁并附加修改意见重试；若用户改选工作流，则创建新的 `workflow_run_id`，不得覆盖原运行来源。

#### 3.5.4 story-workspace 业务合同归属（SUO-298 增量）

| 边界 | Canonical 设计 | 禁止项 |
|------|----------------|--------|
| 后端业务合同 | `backend/story_workspace/contracts.py`；承载 story-workspace 的请求、响应、事件和值对象合同 | 禁止创建或继续使用 `backend/types/`、顶层/共享 `types/`、通用 `types.py` 承载 story-workspace 业务合同 |
| 前端局部 REST 合同 | `frontend/src/hooks/story-workspace/contracts.ts`；由本域 hooks 与页面组件消费 | 禁止迁入全局/共享 `types` 目录，也不将其包装成无业务 owner 的通用合同 |
| 业务符号 | 后端与前端均保留 `StoryWorkspace*` 前缀，例如 `StoryWorkspaceRunRecord` | 文件已位于领域目录也不得省略前缀或改成无领域限定的 `RunRecord`、`ReviewEvent` |
| 数据库边界 | `backend/database.py` 对本增量及兼容迁移只读；现有审计语义只作为业务合同消费 | 禁止新增审计 Schema、DDL 或以数据库改造作为合同搬迁前置条件 |

兼容迁移只改变**合同的代码归属与 import 来源**：新代码直接引用上述 canonical 文件；既有 story-workspace 调用方按消费者逐一迁移，不改变 REST payload、字段名、状态机、数据库表或产品行为。不得在通用 `types` 路径保留 re-export、alias 或 shim；如需短期兼容适配，只能置于对应 story-workspace canonical 模块内，并明确删除条件。该修订不扩展产品范围：复杂画布仍以数据表/结构化详情替代，视频仍不实现。

### 3.6 SUO-230 增量：顶部 Dream 入口与页面审阅 gate

> 本节只定义 SUO-230 的新增/变化项；SUO-211/212/213 已完成结论、SUO-214/215 经 SUO-236 修订后的 Deck-only 关系、桌面三栏、复杂画布数据表化、排除平台视频与 UI Design v2 视觉约束均保持不变。

#### 3.6.1 全局顶部 Dream 导航合同

| 项 | 确定设计 |
|----|----------|
| 用户可见文案 | `Dream`；这是全局产品导航文案，不作为无前缀的代码标识 |
| 导航标识 | `story-workspace-dream`；组件 `StoryWorkspaceDreamNavItem` |
| Canonical 目标 | `/story-workspace/dream`，进入 Dream 概览与最近一次运行/待审阅上下文 |
| 兼容路由 | `/story-workspace` 与 `/story-workspace/dashboard` 重定向至 `/story-workspace/dream`；既有 `/story-workspace/stories`、`characters`、`scenes` 保持不变 |
| 选中判定 | 当前路径为 `/story-workspace/dream` 或任一 `/story-workspace/*` 子页时选中；进入 Writing、Timeline、Analysis、Decks、Chat、Settings 等其他平台页面时未选中 |
| 选中表现 | `aria-current="page"`，Charcoal Brown 600 字重，Memory Yellow 3px 短下划线；不使用整块深色背景 |
| 未选中/交互 | Warm Brown 常态、下划线透明；hover 使用现有 `--color-bg-hover` 与 Charcoal Brown，键盘 focus 使用可见 Action Brown 轮廓 |
| 布局位置 | 沿用现有 AppHeader / `TopNavBar` 的 Logo 后横向导航组；不新增第二层顶部栏，不改变三栏宽度 |

该路由是 `story-workspace` 业务域的全局入口。用户从 Dream 进入故事、角色、场景或详情审阅子页时，顶部 Dream 仍保持选中，避免把域内二级导航误表现为另一个顶级产品。

#### 3.6.2 Dream 页面可见布局与审阅 gate

```text
AppHeader:  Ink & Memory  …  Dream（选中）  …  头像/设置
└─ StoryWorkspaceThreeColumnLayout
   ├─ StoryWorkspaceSidebar：概览 / 故事 / 角色 / 场景
   ├─ Main Content
   │  ├─ StoryWorkspaceWorkflowContextBar（Deck release / runtime snapshot / workflow_run_id）
   │  ├─ StoryWorkspaceReviewGate（产出 → 渲染 → 审阅 → 继续/结束）
   │  └─ StoryWorkspace*Table（复杂画布数据表化，待审阅项可见）
   └─ StoryWorkspaceReviewPanel（完整内容、确认、编辑后确认、驳回）
```

`StoryWorkspaceReviewGate` 在存在活动 `workflow_run_id` 时固定显示于 Main Content 标题/工作流上下文条下方、数据表上方；选中待审阅行后，右侧 `StoryWorkspaceReviewPanel` 展示同一运行来源及操作。关闭面板或离开再返回不会改变 gate。

| `StoryWorkspaceReviewGateState`（UI 状态） | 来源运行/审阅状态 | 页面表现 | 后续执行 gate |
|---------------------------------------------|-------------------|----------|----------------|
| `story-workspace-agent-running` | `queued` / `running` | 第一步“Claude Agent 产出”高亮，数据区骨架态 | 锁定 |
| `story-workspace-rendering` | `output_validating`，完整结果尚未提交 | 第二步“页面渲染”高亮；不得展示部分结果为可确认内容 | 锁定 |
| `story-workspace-pending-review` | canonical `pending_review`；必审项已完整持久化 | 第三步“用户审阅”高亮；待审阅行黄条，Review Panel 可操作 | 锁定 |
| `story-workspace-rejected` | 任一必审项为 `rejected` | 第三步红色状态，显示修改意见与“沿原快照重新生成” | 锁定；驳回不触发后续步骤 |
| `story-workspace-confirming` | 确认请求提交中 | 操作按钮 Loading 且防重复提交 | 锁定 |
| `story-workspace-confirmed` | 当前运行的全部必审项为 `confirmed` | 第三步完成，第四步解锁 | 仅此状态可请求继续或结束 |
| `story-workspace-continuing` / `story-workspace-completed` | 已确认后继续下一步 / 工作流终点 | 第四步显示执行中或已结束；来源信息只读 | 已解锁 |
| `story-workspace-failed` | 产出、渲染、确认或继续失败 | 显示非敏感错误、失败步骤与可恢复动作 | 锁定；按幂等规则重试 |

Gate 规则：

1. `pending_review` 是与 SUO-215 运行状态机一致的 canonical API 状态；既有文案“待审阅/awaiting review”只是展示语义，不新增第二个 API 枚举。
2. 运行级 gate 以该 `workflow_run_id` 的全部必审故事、角色、场景为聚合集合；任一项仍为 `pending` 或 `rejected` 时，不得进入 `confirmed`、`continuing` 或 `completed`。
3. “保存”只更新内容并保持待审阅；只有“确认通过”或“保存并确认”可确认当前版本。确认必须校验运行 ID 与审阅版本，避免对过期 Agent 产出放行。
4. 确认动作必须幂等：首次合法确认后只发出一次继续/结束信号；重复点击、刷新或网络重试不得重复推进 Claude Agent。
5. 驳回只记录意见并锁住 gate；重新生成创建可审计的新 run attempt，默认沿用 DEC-010 的插件/配置快照，不能在原运行上静默覆盖。
6. 若内容已确认但后续继续失败，确认事实不回滚；页面进入失败态，并以同一已确认运行幂等重试继续动作。

#### 3.6.3 对下游 issue / task / stage 的影响（仅声明，不直接生成）

| 下游层级 | 新增/变化合同 | 保持不变 |
|----------|---------------|----------|
| issue | 需由 `@CEOOrchestrator` 创建唯一 IssueDispatcher 传播单，确定覆盖全局 Dream 导航、canonical 路由/兼容重定向、Dream 页审阅 gate 与防绕过验证 | 不重拆 SUO-211/212/213，不复写既有 Deck Issue |
| task | Frontend 增量需覆盖现有 `TopNavBar` / App 视图路由、`StoryWorkspaceDreamPage`、`StoryWorkspaceReviewGate` 及选中/可访问性测试；Backend/Shared 增量需覆盖“未全部确认禁止继续”、确认幂等与 canonical `pending_review` 合同 | 既有三栏、表格、Review Panel、Deck 选择与来源字段可复用；运行快照字段按本修订迁移 |
| stage | 需在新增 task 收口后安排独立增量验证：顶部入口 → Agent 产出 → 页面渲染 → 确认/驳回 → gate 放行/阻断；旧 Stage 不能替代本差异验收 | 不重排已稳定 Stage，不进入平台视频、复杂画布或移动端验证 |

---

## 4. 详细设计

### 4.1 信息架构

```
story-workspace/
├── /dream                        ← 顶部 Dream 的 canonical 入口（工作流上下文 + 产出概览 + 审阅 gate）
├── /dashboard                    ← 兼容入口，重定向至 /story-workspace/dream
├── /stories                      ← 故事/剧本列表（Agent 产出的剧本）
│   ├── /stories/:storyId         ← 故事详情审阅（右侧审阅面板）
│   └── /stories/:storyId/review  ← 审阅确认页面
├── /characters                   ← 角色资产（Agent 生成的角色列表）
│   ├── /characters/:characterId  ← 角色详情审阅
│   └── /characters/:characterId/review
├── /scenes                       ← 场景资产（Agent 生成的场景列表）
│   ├── /scenes/:sceneId          ← 场景详情审阅
│   └── /scenes/:sceneId/review
└── /settings                     ← 工作区设置（复用全局 Settings）
```

**核心工作流路由**：
```
Deck 编辑器自定义并发布 Deck 插件
    ↓
顶部 Dream → /story-workspace/dream → 选择 Deck 插件并执行 WorkflowPreflight（调用 Deck 校验）
    ↓（校验通过；锁定插件版本与配置快照）
Dream 页内输入携带所选工作流上下文，触发 Claude Agent
    ↓
/story-workspace/stories/:storyId/review  ← Dream 域内审阅（用户确认/驳回/编辑）
    ↓
全部必审项确认 → gate 解锁 → 按所选 Deck 插件的下一步继续或结束
任一项驳回/待审阅 → gate 保持锁定 → 沿用原执行快照重新生成或继续审阅
用户编辑 → 保存修改 → 再确认
```

### 4.2 命名映射

| 类型 | 命名规范 | 示例 |
|------|----------|------|
| 路由路径 | `/story-workspace/*` | `/story-workspace/stories` |
| 页面组件 | `StoryWorkspace*Page` | `StoryWorkspaceDreamPage` |
| 布局组件 | `StoryWorkspace*Layout` | `StoryWorkspaceThreeColumnLayout` |
| 业务组件 | `StoryWorkspace*` | `StoryWorkspaceStoryTable` |
| API 路由 | `/api/story-workspace/*` | `/api/story-workspace/stories` |
| 数据库表 | `story_workspace_*` | `story_workspace_stories` |
| 类型/接口 | `StoryWorkspace*` | `StoryWorkspaceStory` |
| 状态管理 | `useStoryWorkspace*` | `useStoryWorkspaceStore` |
| 审阅 gate 状态 | `StoryWorkspace*State` / `story-workspace-*` | `StoryWorkspaceReviewGateState` / `story-workspace-pending-review` |
| CSS 类名 | `.story-workspace-*` | `.story-workspace-table-row` |

### 4.3 页面/模块范围

#### 4.3.1 Dream 入口页 (`/story-workspace/dream`)

> `/story-workspace/dashboard` 仅作兼容重定向；不得维护两份平行页面状态。

**功能**：
- **Deck 工作流上下文**：选择已发布、可用的 Deck 插件，展示名称、版本、工作流摘要与 Deck 运行配置就绪状态；提供「在 Deck 编辑器中配置」跳转
- **可见审阅 gate**：持续展示“Claude Agent 产出 → 页面渲染 → 用户审阅 → 继续/结束”；未全部确认时第四步锁定
- **Agent 产出概览**：待审阅剧本数、已确认剧本数、最近 Agent 生成活动
- **待审阅快捷入口**：Agent 最新生成的剧本/角色/场景，点击直达审阅
- **空态**：首次进入时的引导（等待 Agent 产出）

**布局**：
- 顶部：页面标题 + 审阅状态统计
- 中部：待审阅项卡片（Agent 最新产出）
- 下部：已确认剧本列表（最近确认）

#### 4.3.2 故事/剧本列表 (`/story-workspace/stories`)

**功能**：
- 表格展示 Agent 产出的剧本：标题、审阅状态、类型、角色数、场景数、生成时间
- 搜索：按标题搜索
- 筛选：按审阅状态（待审阅 / 已确认 / 已驳回 / 已归档）、按类型
- 排序：按生成时间、按确认时间、按标题
- 分页：默认 20 条/页
- **批量操作**：批量确认、批量驳回

**表格字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| 标题 | string | 剧本标题（Agent 生成） |
| **审阅状态** | enum | **待审阅 / 已确认 / 已驳回 / 已归档** |
| 类型 | enum | 短剧 / 长篇 / 剧本 / 大纲 |
| 角色数 | number | Agent 生成的关联角色数量 |
| 场景数 | number | Agent 生成的关联场景数量 |
| 生成时间 | datetime | Agent 生成时间 |
| 操作 | actions | **审阅 / 确认 / 驳回** |

**审阅状态流转**：
```
WorkflowPreflight 通过 → Agent 生成 → 待审阅 → 用户确认 → 已确认 → 所选工作流继续或结束
                ↓
              用户驳回 → 附带修改意见 → Agent 重新生成 → 待审阅
                ↓
              用户编辑后确认 → 已确认
```

#### 4.3.3 角色资产管理 (`/story-workspace/characters`)

**功能**：
- 表格展示 Agent 生成的角色：名称、头像、身份、性格标签、关联故事、审阅状态
- 搜索：按名称/身份搜索
- 筛选：按审阅状态、按性格标签
- **审阅编辑**：在详情面板中编辑 Agent 生成的角色属性，确认后保存

**表格字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| 头像 | image | Agent 生成的角色头像（或占位） |
| 名称 | string | Agent 生成的角色名称 |
| 身份 | string | Agent 生成的角色身份/职业 |
| 性格 | tags | Agent 生成的性格标签 |
| 关联故事 | number | 所属剧本数量 |
| **审阅状态** | enum | **待审阅 / 已确认 / 已驳回** |
| 操作 | actions | **审阅 / 确认 / 驳回** |

**角色属性字段**（审阅面板，Agent 生成内容可编辑）：

| 字段 | 类型 | 必填 | 说明 | 来源 |
|------|------|------|------|------|
| 名称 | string | ✅ | 角色名称 | Agent 生成，用户可编辑 |
| 头像 | image | ❌ | 角色头像 | 占位，后续支持上传 |
| 身份 | string | ❌ | 角色身份/职业 | Agent 生成，用户可编辑 |
| 性格 | text | ❌ | 性格描述 | Agent 生成，用户可编辑 |
| 背景 | text | ❌ | 角色背景故事 | Agent 生成，用户可编辑 |
| 口头禅 | string | ❌ | 标志性台词 | Agent 生成，用户可编辑 |
| 标签 | string[] | ❌ | 性格标签 | Agent 生成，用户可编辑 |
| 备注 | text | ❌ | 用户审阅备注 | 用户填写 |

#### 4.3.4 场景资产管理 (`/story-workspace/scenes`)

**功能**：
- 表格展示 Agent 生成的场景：名称、描述、关联故事、关联角色、审阅状态
- 搜索与筛选
- **审阅编辑**：在详情面板中编辑 Agent 生成的场景信息，确认后保存

**表格字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| 名称 | string | Agent 生成的场景名称 |
| 描述 | text | Agent 生成的场景描述 |
| 关联故事 | string | 所属剧本标题 |
| 关联角色 | number | 出场角色数 |
| **审阅状态** | enum | **待审阅 / 已确认 / 已驳回** |
| 操作 | actions | **审阅 / 确认 / 驳回** |

### 4.4 布局交互

#### 4.4.1 桌面端三栏布局（唯一支持的布局）

> **约束**：本期仅支持桌面端（≥1280px），不包含任何移动端或平板端适配。所有布局、交互和状态设计均基于大屏桌面场景。

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ App Header（全局）：Ink & Memory  …  Dream（选中）  …  用户/设置               │
├──────────┬──────────────────────────────────────────────┬───────────────────┤
│          │                                              │                   │
│  Sidebar │           Main Content Area                  │  Detail Panel     │
│  240px   │           （自适应宽度）                        │  360px            │
│          │                                              │  （可折叠）        │
│  - Logo  │                                              │                   │
│  - Nav   │  ┌────────────────────────────────────────┐  │  - 详情表单       │
│  - 用户  │  │ Review Gate（产出→渲染→审阅→继续/结束） │  │  - 属性编辑       │
│          │  ├────────────────────────────────────────┤  │  - 关联信息       │
│          │  │ Toolbar（搜索/筛选/排序）                │  │                   │
│          │  └────────────────────────────────────────┘  │                   │
│          │                                              │                   │
│          │  ┌────────────────────────────────────────┐  │                   │
│          │  │ Data Table                             │  │                   │
│          │  │ （轻纸面分区，无卡片）                    │  │                   │
│          │  └────────────────────────────────────────┘  │                   │
│          │                                              │                   │
│          │  ┌────────────────────────────────────────┐  │                   │
│          │  │ Pagination                             │  │                   │
│          │  └────────────────────────────────────────┘  │                   │
│          │                                              │                   │
├──────────┴──────────────────────────────────────────────┴───────────────────┤
│ Footer（可选）                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 4.4.2 布局组件规范

| 组件 | 宽度 | 行为 |
|------|------|------|
| Sidebar | 240px | 固定宽度，始终展开 |
| Main Content | 自适应 | 填充剩余空间 |
| Detail Panel | 360px | 默认展开，可手动折叠，选中行时显示详情 |

#### 4.4.3 布局约束说明

> **重要**：本期设计仅针对桌面端（≥1280px）。不考虑任何移动端（<768px）或平板端（768px–1279px）的适配。
>
> - Sidebar 始终 240px 展开，不提供折叠为图标栏的模式
> - Detail Panel 始终 360px 展开，不作为抽屉滑出
> - 所有交互基于鼠标（hover、点击、拖拽），不考虑触控
> - 表格始终完整展示所有列，不提供卡片式简化视图
>
> 若未来需要扩展响应式支持，应作为独立设计 Issue 处理。

### 4.5 交互设计

#### 4.5.1 核心工作流：选择 Deck 工作流 → WorkflowPreflight → Agent 产出 → 审阅确认

```
┌─────────────────────────────────────────────────────────────────────────────┐
│             Deck 选择 → 运行配置快照 → Agent 产出 → 审阅确认                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Deck Editor → 选择 Deck Plugin → WorkflowPreflight → Claude Agent → 页面 → 审阅 │
│   自定义/发布     锁定 ID/版本       配置快照       执行工作流     渲染      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**详细流程**：

1. **工作流准备与选择阶段**
   - 创作者在 Deck 编辑器中自定义并发布 Deck 插件
   - story-workspace 只列出当前用户/工作区有权限且已发布、启用的 Deck 插件
   - 创作者选择 Deck 插件；页面显示插件名称、版本与工作流摘要

2. **执行前校验阶段**
   - 根据所选 Deck 插件，由 Deck 解析所需的 Agent 提示词、插件配置和权限策略
   - 校验发布/启用状态、访问权限、配置完整性与版本兼容性
   - 校验通过后锁定 `deck_plugin_version`、`deck_runtime_snapshot_id` 与 `runtime_plugin_lock_id`；任一校验失败均不启动 Agent

3. **Agent 产出阶段**（系统侧，Dream 页面内可见）
   - Dream 页面内的创作输入复用现有 Chat 能力，但不跳离 Dream；请求连同已锁定的工作流上下文触发 Claude Agent
   - Agent 按 Deck 插件定义的步骤，使用 Deck 运行快照生成剧本、角色、场景数据
   - 数据存入数据库，标记 `review_status = 'pending'`
   - 记录 `workflow_run_id`、来源版本与执行状态

4. **页面渲染阶段**（UI 侧）
   - 用户进入 story-workspace
   - 页面加载 Agent 生成的数据，按审阅状态分组展示
   - 待审阅项高亮显示

5. **用户审阅阶段**（UI 侧）
   - 用户点击待审阅项 → 右侧审阅面板展开
   - 面板展示 Agent 生成的完整内容
   - 用户可：
     - **确认**：点击「确认」→ 当前项变为 `confirmed`；只有全部必审项确认后 gate 才允许工作流继续或结束
     - **编辑后确认**：修改字段 → 点击「保存并确认」→ 当前版本变为 `confirmed`，仍按运行级 gate 聚合判断
     - **驳回**：点击「驳回」→ 填写修改意见 → 状态变为 `rejected` → Agent 重新生成

6. **工作流继续/结束阶段**（系统侧）
   - 只有当前 `workflow_run_id` 的全部必审项确认后，运行级 gate 才解锁
   - 已确认内容回写当前 `workflow_run_id`；待审阅或已驳回状态不得调用后续执行
   - 若 Deck 插件定义确认后的下一步骤，则 Claude Agent 按同一锁定快照继续；若确认是终点，则该运行完成

#### 4.5.2 表格交互

| 交互 | 行为 |
|------|------|
| 点击行 | 选中该行，右侧 Detail Panel 显示审阅内容 |
| 双击行 | 进入审阅模式 |
| Hover 行 | 显示操作按钮（审阅/确认/驳回），行背景轻微变化 |
| 多选 | Checkbox 多选，启用批量操作栏（批量确认/驳回） |
| 排序 | 点击表头排序，支持升序/降序/取消 |
| 筛选 | 工具栏下拉筛选，支持多条件组合 |

#### 4.5.3 审阅面板交互

| 交互 | 行为 |
|------|------|
| 点击关闭 | 关闭审阅面板，表格恢复全宽 |
| 编辑模式 | 面板内 Agent 生成内容可编辑，保存/取消按钮 |
| 确认 | 点击「确认通过」→ 状态变更 → Toast 提示 → 表格刷新 |
| 驳回 | 点击「驳回」→ 弹出修改意见输入框 → 提交后状态变更 |
| 关联跳转 | 点击关联故事/角色可跳转对应模块 |

#### 4.5.4 审阅确认流程

```
用户选中待审阅项
        ↓
右侧审阅面板展开，显示 Agent 生成内容
        ↓
用户查看内容
        ↓
┌─────────────────┬─────────────────┬─────────────────┐
│   直接确认       │   编辑后确认     │    驳回         │
│   「✓ 确认通过」 │   修改字段      │   「✕ 驳回」    │
│                 │   「保存并确认」 │   填写修改意见   │
└─────────────────┴─────────────────┴─────────────────┘
        ↓                 ↓                 ↓
   状态→confirmed    状态→confirmed     状态→rejected
   Toast「已确认」    Toast「已确认」    Toast「已驳回」
   全部确认后放行       全部确认后放行        原快照下 Agent 重新生成
```

---

## 5. 状态设计

### 5.1 空态 (Empty State)

| 模块 | 空态文案 | 操作 |
|------|----------|------|
| **Dream 入口页（无 Agent 产出）** | **"还没有剧本内容，请先让 Agent 生成"** | **在 Dream 页面选择工作流并发起创作** |
| **故事列表（无待审阅）** | **"暂无待审阅的剧本"** | **显示已确认剧本列表 / 提示触发 Agent** |
| **角色列表（无 Agent 生成角色）** | "还没有角色，等待 Agent 生成" | 提示触发 Agent |
| **场景列表（无 Agent 生成场景）** | "还没有场景，等待 Agent 生成" | 提示触发 Agent |
| 搜索结果 | "未找到匹配的结果" | 清除搜索条件 |
| **无 Deck 插件** | **"还没有可用的 Deck 工作流"** | **前往 Deck 编辑器自定义并发布插件** |
| **未选择 Deck 插件** | **"请先选择创作工作流"** | **打开 Deck 工作流选择器；不启动 Agent** |

**空态视觉**：
- 居中显示
- 轻纸面图标（Charcoal Brown 线条 + Memory Yellow 点缀）
- 标题：Warm Brown
- 描述：Muted Tan
- **操作提示：引导用户触发 Agent 生成**

### 5.2 加载态 (Loading)

| 场景 | 表现 |
|------|------|
| 表格初始加载 | 骨架屏（Skeleton），5 行占位 |
| 搜索/筛选 | 表格遮罩 + 顶部加载指示器 |
| 保存操作 | 按钮 Loading 状态 |
| 详情面板 | 面板内骨架屏 |

### 5.3 错误态 (Error)

| 场景 | 表现 |
|------|------|
| 加载失败 | 错误提示条 + 重试按钮 |
| 保存失败 | 表单字段级错误提示 + 全局错误提示 |
| 网络错误 | 轻提示（Toast）+ 自动重试 |
| 权限错误 | 错误页面 + 返回首页按钮 |
| **Deck 插件不可用** | **保留当前选择信息并标记“已停用/无权限/版本不可用”，要求重新选择；不自动回退默认插件** |
| **Deck 运行配置缺失或不兼容** | **展示缺失配置项类别与“前往 Deck 配置”入口；不展示敏感值，不启动 Agent** |
| **工作流执行失败/超时** | **显示失败步骤、可安全重试提示与 `workflow_run_id`；默认沿用锁定快照重试** |
| **产出持久化失败** | **运行标记为失败且不生成待审阅行；禁止把部分数据呈现为完整产出** |

### 5.4 选中态 (Selected)

| 元素 | 选中表现 |
|------|----------|
| 表格行 | 右侧细线（Action Brown 2px）+ 轻微背景色变化 |
| Sidebar 导航项 | Memory Yellow 短下划线 |
| 批量操作 | 顶部出现批量操作栏（固定） |
| **待审阅项** | **行左侧 Memory Yellow 竖条标记（4px）提示待审阅** |
| **已驳回项** | **行左侧红色竖条标记（4px）提示需重新生成** |

### 5.5 Dream 审阅 gate 状态

`StoryWorkspaceReviewGateState` 与可序列化的 `story-workspace-*` 状态值以 3.6.2 为唯一新增合同。页面关闭、路由切换或刷新只可重新读取 gate，不可将 `pending_review` 推进为 `confirmed`；任何绕过页面直接请求继续的行为都必须被服务端拒绝。

---

## 6. 视觉设计规范

### 6.1 色彩应用

遵循 [Ink & Memory Color System](../color_system/README.md) 和 `frontend/src/styles/tokens.css`。

| 用途 | Token | 色值 |
|------|-------|------|
| 页面背景 | `--color-bg-app` | Warm Canvas #F6EFE5 |
| 内容区背景 | `--color-bg-paper` | Paper Cream #FFFAF2 |
| 表格行背景（交替） | `color-mix(--color-bg-paper 50%, transparent)` | 淡奶油色 |
| 主标题 | `--color-text-primary` | Charcoal Brown #3F3429 |
| 正文 | `--color-text-body` | Body Brown #4B3F33 |
| 辅助文字 | `--color-text-secondary` | Warm Brown #7A6A59 |
| 弱信息 | `--color-text-muted` | Muted Tan #9A8A78 |
| 主按钮 | `--color-action-primary` | Action Brown #5F4A36 |
| 边框/分割线 | `--color-border-paper` | Border Paper #D8C7B3 |
| 选中态强调 | `--color-voice-yellow` | Memory Yellow #F39C12 |
| 成功状态 | `--color-voice-green` | Spark Green #27AE60 |
| 链接 | `--color-action-link` | Link Blue #4A90E2 |
| Hover 阴影 | `--color-shadow-soft` | rgba(91,69,44,0.08) |

### 6.2 字体应用

| 用途 | 字体 | 字号 | 字重 |
|------|------|------|------|
| 页面标题 | Excalifont / Xiaolai | 28px | 600 |
| 模块标题 | 系统无衬线 | 20px | 600 |
| 表格标题 | 系统无衬线 | 14px | 500 |
| 正文 | 系统无衬线 | 14px | 400 |
| 辅助文字 | 系统无衬线 | 12px | 400 |
| 按钮文字 | 系统无衬线 | 14px | 500 |

### 6.3 分区与留白

遵循「轻纸面分区」原则：
- **无卡片设计**：表格行静止时无阴影、无外框
- **虚线边框**：内容区保留一条 Border Paper 虚线边界
- **留白分区**：以留白和字号层级代替实线边框
- **Hover 效果**：仅 hover 时出现 `--color-shadow-soft` 轻阴影
- **选中态**：右侧细线（2px Action Brown）表达选中

---

## 7. 验收标准

### 7.1 功能验收

- [ ] 桌面端三栏布局正常渲染，各区域比例正确
- [ ] Agent 产出的剧本/角色/场景在表格中正确展示
- [ ] **审阅状态（待审阅/已确认/已驳回）正确显示和流转**
- [ ] **审阅面板可正常展开，展示 Agent 生成内容**
- [ ] **确认/驳回/编辑后确认操作流程完整**
- [ ] 搜索、筛选、排序功能可用
- [ ] 分页功能正常
- [ ] 角色/场景表格完整展示所有字段
- [ ] **批量审阅操作（批量确认/驳回）可用**
- [ ] 空态、加载态、错误态、选中态均有实现
- [ ] **Agent 生成中状态有 Loading 指示**
- [ ] 可选择已发布、可用的 Deck 插件，并清楚展示插件名称与版本
- [ ] 执行前能显示 Deck 运行配置就绪/缺失/不兼容状态；未就绪时 Agent 不会启动
- [ ] 每个剧本产出可追溯到 `deck_plugin_binding_id + binding_revision`、`deck_plugin_version`、`deck_runtime_snapshot_id`、`runtime_plugin_lock_id` 与 `workflow_run_id`
- [ ] 切换 Deck 插件只影响新运行，既有剧本来源不被改写
- [ ] 全局顶部导航可见 Dream，点击进入 `/story-workspace/dream`；任一 `/story-workspace/*` 子页保持 Dream 选中，其他平台页面显示未选中
- [ ] `/story-workspace` 与 `/story-workspace/dashboard` 只重定向至 canonical Dream 入口，不产生平行状态
- [ ] Dream 页面同时可见工作流上下文、四步审阅 gate、产出数据表与右侧 Review Panel
- [ ] 任一必审项待审阅或驳回时，后续继续/结束不可触发；全部确认后仅触发一次

### 7.2 视觉验收

- [ ] 色彩系统与 tokens.css 一致
- [ ] 轻纸面分区原则贯彻（无卡片堆叠、虚线边界、留白分区）
- [ ] 字体层级清晰
- [ ] 选中态使用右侧细线（非背景色块）
- [ ] Hover 仅出现轻阴影

### 7.3 桌面端约束验收

- [ ] 仅桌面端（≥1280px）三栏完整布局
- [ ] 确认无移动端/平板端相关代码或样式
- [ ] Sidebar 始终 240px 展开，不可折叠为图标栏
- [ ] Detail Panel 始终 360px 展开，不作为抽屉

### 7.4 下游可消费性

- [ ] 产物路径存在：`docs/design/story-workspace/story-workspace-prd.md`
- [ ] 范围内/范围外清晰
- [ ] 命名映射完整
- [ ] 数据表结构明确
- [ ] Issue 评论已回填路径、关键决策、未决项

### 7.5 业务合同归属修复

- [ ] 后端 story-workspace 业务合同唯一 canonical 路径为 `backend/story_workspace/contracts.py`
- [ ] 前端局部 REST 合同唯一 canonical 路径为 `frontend/src/hooks/story-workspace/contracts.ts`
- [ ] 不存在把 story-workspace 合同归入 `backend/types/` 或其他通用/共享 `types` 目录的有效设计或兼容指令
- [ ] 所有业务符号保留 `StoryWorkspace*` 前缀，兼容迁移不改变 REST、状态机、数据库表或产品行为
- [ ] `backend/database.py` 保持只读，未新增审计 Schema / DDL
- [ ] 复杂画布继续以数据表/结构化详情替代，视频继续排除

---

## 8. 风险与依赖

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 与现有 Workspace 文件系统命名冲突 | 中 | 使用 `story-workspace` 前缀隔离命名空间 |
| 与现有 Chat Dashboard 布局风格不一致 | 中 | 严格遵循 Ink & Memory UI v2 规范 |
| **Agent 产出与页面渲染的时序问题** | **中** | **设计 Agent 生成中状态，避免用户困惑** |
| **审阅流程的用户体验复杂度** | **中** | **简化审阅操作，提供明确的确认/驳回/编辑路径** |
| 角色可视化模块（六模块）本期无法实现 | 低 | 以数据表呈现，后续迭代可视化 |
| 复杂画布（故事板/时间线）本期无法实现 | 低 | 明确范围外，以表格状态字段替代 |
| Deck 插件版本被停用或删除导致历史来源不可查询 | 中 | story-workspace 保留不可变版本标识与显示快照；历史产出不改绑新版本 |
| Deck 运行配置缺失、无权限或与 Deck 插件不兼容 | 高 | 启动前强制校验，失败时阻断执行并给出 Deck 配置入口 |
| 敏感插件配置被复制到 story-workspace | 高 | 仅保存受控快照引用与非敏感状态，不复制或渲染敏感配置值 |
| 顶部 Dream 入口与既有 Dashboard 形成双状态 | 高 | 以 `/story-workspace/dream` 为 canonical，旧入口只重定向，不复制 store 或运行上下文 |
| 客户端或重试绕过审阅 gate | 高 | 服务端以 `workflow_run_id` + 审阅版本校验全部必审项，确认与继续均幂等 |
| 通用 `types` 目录承载 story-workspace 合同并遮蔽语言/标准库类型模块 | 高 | 合同按 DEC-026 迁回 story-workspace 领域路径；通用路径不保留 re-export 或 shim |

### 依赖

- [SUO-198](/SUO/issues/SUO-198) 父 Issue 的范围约束
- **`claude-agent` 服务**：Agent 产出剧本内容的能力（见 CLAUDE.md）
- **Deck 模块**：提供工作流编辑发布、版本化 Agent profile/提示词/插件配置、secret-ref、权限、执行前解析与不可变运行快照
- **Deck 编辑器 / Deck 插件目录**：提供 Deck 内部编辑发布界面及可选择的已发布版本
- `frontend/src/styles/tokens.css` 色彩系统
- 现有 Workspace 文件管理 API（文件上传/下载能力复用）

---

## 9. 关键决策记录

| 决策 ID | 日期 | 决策 | 决策者 | 影响 |
|---------|------|------|--------|------|
| DEC-001 | 2026-08-01 | 采用轻纸面分区布局 | DesignArchitect | 影响所有页面视觉 |
| DEC-002 | 2026-08-01 | 复杂画布以数据表呈现 | DesignArchitect | 降低本期复杂度 |
| DEC-003 | 2026-08-01 | 三栏桌面布局 | DesignArchitect | 影响布局组件设计 |
| DEC-004 | 2026-08-01 | `story-workspace` 前缀命名 | DesignArchitect | 影响所有代码命名 |
| DEC-005 | 2026-08-01 | 排除视频模块 | DesignArchitect | 明确范围边界 |

| DEC-006 | 2026-08-01 | **仅桌面端设计，排除移动端/平板端** | DesignArchitect + local-board | **明确排除所有移动端适配** |
| **DEC-007** | **2026-08-01** | **核心工作流：Agent 产出 → 页面渲染 → 用户审阅确认 → 执行** | **DesignArchitect + local-board** | **重新定义业务模型：从手动 CRUD 改为审阅确认** |
| **DEC-008** | **2026-08-01** | **用户不手动创建内容，仅审阅 Agent 产出** | **local-board** | **明确用户角色为审阅者而非创作者** |
| **DEC-009** | **2026-08-01** | **Deck 是唯一业务模块；Deck Editor、Deck Plugin、Deck 运行配置与 binding 是其内部职责，story-workspace 只消费公开合同并保存运行/结果，不编辑 Deck 定义或配置** | **local-board + DesignArchitect** | **落实 SUO-235 裁决；见 3.5** |
| **DEC-010** | **2026-08-01** | **单次运行锁定 Deck 插件版本、`deck_runtime_snapshot_id` 与 `runtime_plugin_lock_id`，切换只影响新运行** | **DesignArchitect** | **保证运行可复现和产出可溯源** |
| **DEC-011** | **2026-08-01** | **Deck release、运行配置、权限或 runtime preflight 任一失败时禁止启动 Claude Agent** | **DesignArchitect** | **定义未配置、无权限、不兼容时的失败边界** |
| **DEC-017** | **2026-08-01** | **全局 Dream 导航以 `/story-workspace/dream` 为 canonical 入口，Dashboard 仅兼容重定向** | **DesignArchitect + local-board** | **确定导航与选中态合同，保留既有路由兼容性** |
| **DEC-018** | **2026-08-01** | **运行级审阅 gate 在全部必审项确认前禁止继续或结束** | **DesignArchitect + local-board** | **影响 Dream 页面状态、确认幂等与服务端防绕过合同** |
| **DEC-019** | **2026-08-01** | **提示词、运行配置、secret-ref、权限与不可变快照统一归属 Deck，并使用 `deck_runtime_*` 合同** | **local-board + DesignArchitect** | **统一所有权、字段、错误码和 participant** |
| **DEC-026** | **2026-08-01** | **后端合同归 `backend/story_workspace/contracts.py`，前端局部 REST 合同归 `frontend/src/hooks/story-workspace/contracts.ts`；禁止通用 `types` 业务归属，`backend/database.py` 只读且不新增审计 Schema / DDL** | **local-board + CEOOrchestrator** | **统一合同 owner、兼容迁移与数据库写入边界** |

---

## 10. 增量变更说明

- **初始版本**（2026-08-01）：创建本文档，定义 story-workspace 的 PRD 设计
- **修订 2**（2026-08-01）：根据评论「设计稿的主要属性，应该参考 Dreem 调研 PDF 中的截图」—— 新增 3.3「Dreem 截图视觉参考分析」章节
- **修订 3**（2026-08-01）：**根据评论「交互流程应该是 Agent 产出剧本工作空间，然后页面渲染剧本信息，用户确认，后续执行」—— 重大业务模型修正：从「手动 CRUD」改为「Agent 产出 → 用户审阅确认」模式。影响范围：背景目标、范围内/外、信息架构、交互设计、状态设计、验收标准、风险依赖、关键决策**
- **修订 4 / SUO-214**（2026-08-01）：根据 SUO-198 评论 `41db518b-006f-4289-a89b-dd722ffe8723`，首次补充 Deck Editor、Deck Plugin、运行配置与 story-workspace 的职责、选择/执行时序、失败状态和版本溯源；其中早期独立配置域解释已在修订 6 废弃。未改变桌面三栏、`story-workspace` 前缀、表格替代复杂画布和排除视频的稳定约束。
- **修订 5 / SUO-230**（2026-08-01）：根据 SUO-198 评论 `2eff7996-aa5e-4371-a557-fb9a39037310` 与边界验收，新增全局顶部 Dream 导航、canonical `/story-workspace/dream` 路由、选中/未选中状态、Dream 页面四步可见审阅 gate、确认幂等/防绕过规则及 issue/task/stage 影响；不改写 SUO-211/212/213 的稳定结论。
- **修订 6 / SUO-236**（2026-08-01）：按 SUO-235 将业务模块和设计元语统一为 Deck；保留运行配置、不可变快照、secret-ref、权限、preflight、审计、重试和回滚语义，并统一字段为 `deck_runtime_*`、错误码为 `DECK_RUNTIME_CONFIG_*`。
- **修订 7 / SUO-298**（2026-08-01）：按直接修订授权增量明确 story-workspace 合同的前后端 canonical 路径，禁止通用 `types` 业务归属，补充无行为变更的兼容迁移与 `backend/database.py` 只读边界；表格替代复杂画布、排除视频等产品范围保持不变。

---

## 11. 未决项与澄清

| 项 | 状态 | 说明 |
|----|------|------|
| [CLARIFICATION_NEEDED] 角色头像上传规格 | 待确认 | 是否需要四视角转面图？本期仅支持单张头像？ |
| [CLARIFICATION_NEEDED] 故事/剧本内容编辑器 | 待确认 | 详情面板中故事内容的编辑方式（纯文本/Markdown/富文本）？ |
| 与 Deck 编辑器的关系 | **已关闭** | **按 DEC-009：Deck Editor 编辑/发布 Deck Plugin；story-workspace 选择插件并消费其工作流，不把剧本转成 Deck 卡片，也不在本模块编辑工作流** |
| Agent 产出的触发方式 | **已收敛** | **先在 Dream 页面选择 Deck 插件并通过 story-workspace `WorkflowPreflight`（调用 Deck 校验），再由 Dream 页内创作输入复用现有 Chat 能力并携带工作流上下文触发 Claude Agent；不得跳离 Dream 完成该流程** |
| 驳回后的重新生成流程 | **已收敛** | **默认沿用原 Deck 插件版本、Deck 运行快照与 runtime lock，附加审阅意见重试；改选工作流则创建新运行** |
| 已确认内容的后续执行 | **已收敛** | **按所选 Deck 插件定义的确认后步骤继续；若确认是该工作流终点，则运行结束** |
| **[CLARIFICATION_NEEDED] Deck 技术传输合同** | **不阻塞 design；下游 owner：IssueDispatcher → BackendTaskAgent** | **需在增量 Issue/Task 中明确可用插件查询、`WorkflowPreflight` 与 Deck 校验、运行创建及来源字段的 API/事件合同、权限和幂等；不得改变 DEC-009～DEC-011、DEC-019** |

**默认假设**：
- 角色头像本期仅支持单张图片上传，四视角转面图为后续迭代
- 故事内容编辑本期为纯文本/Markdown，富文本编辑器后续迭代
- **Deck 插件选择为工作区/用户当前创作上下文；单次运行以锁定快照为准，不能被后续选择覆盖**
- **Agent 产出由 Dream 页内创作输入触发；可复用现有 Chat 会话能力，但页面上下文与审阅闭环始终留在 Dream，且请求必须携带已校验的 Deck release、运行快照与 runtime lock**
- **驳回后默认在同一工作流快照下重新生成，并保留原运行与失败记录**
- **已确认内容按所选 Deck 插件的后续步骤继续或结束，不再使用未定义的“Deck 生成”占位语义**

---

## 12. 验证方式

1. **设计稿审查**：下游 Agent（IssueDispatcher、FrontendTaskAgent）审阅本文档
2. **视觉一致性检查**：对照 `tokens.css` 验证色彩/字体应用
3. **范围确认**：对照「范围内/范围外」清单确认实现边界
4. **命名检查**：确认所有业务标识使用 `story-workspace` 前缀
5. **关系与状态检查**：确认 Deck/story-workspace/Claude Agent 职责、选择/执行时序、版本溯源及未配置/失败状态在本文均可定位，且不存在独立配置 owner
6. **Dream 入口与 gate 检查**：检索 `story-workspace-dream`、`/story-workspace/dream`、`StoryWorkspaceReviewGate`、`story-workspace-pending-review`、`DEC-017`、`DEC-018`，并确认待审阅/驳回时没有后续执行路径
7. **合同归属定向检查**：检索 `backend/types`、通用 `types`、`backend/story_workspace/contracts.py`、`frontend/src/hooks/story-workspace/contracts.ts`、`backend/database.py` 与 `DEC-026`；确认前两者仅出现在禁止/风险语境，canonical 路径、`StoryWorkspace*` 前缀、无 Schema / DDL 迁移和产品边界表述一致
