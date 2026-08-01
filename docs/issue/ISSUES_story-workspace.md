# Story Workspace Issue 清单（增量更新版）

> **增量 Issue**: SUO-226、**SUO-230**  
> **父 Issue**: SUO-198 / SUO-235 / SUO-237
> **设计增量来源**: SUO-214（DEC-009～DEC-011）、SUO-215（Deck/Claude Agent 集成 Delta）、**SUO-230（DEC-017～DEC-018：Dream 导航与审阅 Gate）**、**SUO-236（Deck-only 统一修订）**
> **生成 Agent**: IssueDispatcher
> **最后更新**: 2026-08-01（SUO-236 Deck-only 修订完成）
> **更新类型**: 增量差异，不重写稳定基线；按 SUO-235 将 Desk 引用统一为 Deck

---

## 0. 文档元信息

- Issue 清单文件：`docs/issue/ISSUES_story-workspace.md`
- 来源设计稿：
  - 主设计稿：`docs/design/story-workspace/story-workspace-prd.md`（DEC-009～DEC-011、**DEC-017～DEC-018**）
  - 布局设计稿：`docs/design/story-workspace/story-workspace-layout-design.md`
  - 增量 Delta 设计稿：`docs/design/deck/deck-integration-delta.md`
  - **SUO-230 增量设计稿**：`docs/design/story-workspace/story-workspace-prd.md` §3.6 / `docs/design/story-workspace/story-workspace-layout-design.md` §2.4
  - 背景设计稿：`docs/CLAUDE.md`（Agent 服务集成说明）
  - 参考设计稿：`docs/design/story-workspace/调研Dreem_app平台.pdf`
- 生成 Agent：`IssueDispatcher`
- 所属流水线阶段：`issue`
- 上游阶段：`design`（SUO-199 → SUO-214 / SUO-215 → **SUO-230**）
- 下游阶段：`task`
- 下游 Agent：
  - `TaskDesignAgent`
- 共享设计稿来源：`docs/design/story-workspace/`
- 是否作为当前实现合同：是
- 备注：
  - 本文档由设计稿拆解生成，经 SUO-236 按 SUO-235 Deck-only 裁决修订。
  - 所有 Desk 引用已统一为 Deck；运行配置、不可变快照、secret-ref、权限、preflight、审计和回滚合同归属 Deck。
  - 分发去向统一为 `@TaskDesignAgent`，由 `type`、标签和范围字段表达 domain。
  - **本文档为增量更新版**：保留 SUO-211 / SUO-212 / SUO-213 已完成基线，仅追加/变更由 SUO-214 / SUO-215 / **SUO-230** 设计增量引入的新 Issue。
  - **SUO-230 增量**：传播 DEC-017（Dream 导航）与 DEC-018（审阅 Gate）到既有 Issue 清单；新增 SUO-230-* 系列 Issue。
  - 若与设计稿冲突，以 `docs/design/story-workspace/` 中稳定设计稿为准。
  - 若与当前 API / 代码实现冲突，必须记录为阻塞或澄清项，不得静默覆盖。

---

## 1. 关联设计稿信息

- 主设计稿：`docs/design/story-workspace/story-workspace-prd.md`
- 重点补充设计稿：`docs/design/story-workspace/story-workspace-layout-design.md`
- **增量 Delta 设计稿**：`docs/design/deck/deck-integration-delta.md`
- **SUO-230 增量设计稿**：`docs/design/story-workspace/story-workspace-prd.md` §3.6、`docs/design/story-workspace/story-workspace-layout-design.md` §2.4
- 关联设计稿：`docs/CLAUDE.md`（claude-agent 服务集成）
- 参考设计稿：`docs/design/story-workspace/调研Dreem_app平台.pdf`

- 本清单覆盖范围：
  - Workspace 布局骨架：三栏桌面端布局、导航、侧边栏、主内容区
  - Agent 产出渲染：剧本/角色/场景由 Agent 自动生成，页面负责渲染展示
  - 审阅确认流程：用户查看 Agent 产出 → 确认通过 / 提出修改 / 重新生成
  - **全局 Dream 导航与 canonical 路由**：`/story-workspace/dream` 入口、选中态、兼容重定向
  - **Dream 页面审阅 gate**：运行级聚合状态、确认幂等、防绕过验证
  - Deck 插件选择与工作流上下文：选择已发布可用 Deck 插件，锁定版本
  - Deck 运行配置预检：解析 Agent 提示词/插件配置就绪状态，执行前强制校验
  - Workflow Binding / Run 记录：版本锁定、来源溯源、幂等执行
  - 审阅闭环与后续执行 Gate：确认后按所选 Deck 插件工作流继续或结束
  - 故事/剧本列表：数据表格呈现 Agent 产出的剧本，展示生成状态
  - 角色资产管理：展示 Agent 生成的角色列表，支持审阅编辑
  - 场景资产管理：展示 Agent 生成的场景列表，支持审阅编辑
  - 空态/加载/错误/选中态：各模块的完整状态设计，含 Agent 生成中状态
  - 桌面端布局：固定三栏桌面端布局，无响应式适配需求

- 明确排除范围：
  - 用户手动创建故事/角色/场景（本期内容由 Agent 产出，用户仅审阅确认）
  - 复杂画布编辑器（故事板/时间线可视化编辑）
  - 视频生成模块（镜头生成、视频预览）
  - 计费/积分系统（积分消耗策略）
  - 移动端适配（完整移动端交互，本期明确排除，仅桌面端）
  - 实时协作（多创作者同时编辑）
  - 四视角转面图（本期仅支持单张头像）
  - 人物三视图维护
  - 历史版本管理
  - @提及系统
  - **Deck 编辑器内部编辑能力**（由 Deck 模块独立负责）
  - **Deck 运行配置管理界面**（由 Deck 模块独立负责）
  - **完整插件运行时/插件市场/第三方插件沙箱**

- 关键约束：
  - 所有业务路径、路由、包名、组件/模块/数据标识均采用 `story-workspace` 前缀
  - 本期仅桌面端（≥1280px），不包含任何移动端或平板端适配
  - Sidebar 始终 240px 展开，不提供折叠为图标栏的模式
  - Review Panel（Detail Panel）始终 360px 展开，不作为抽屉滑出
  - 所有交互基于鼠标（hover、点击），不考虑触控
  - 表格始终完整展示所有列，不提供卡片式简化视图
  - 核心工作流：Agent 产出 → 页面渲染 → 用户审阅确认 → 后续执行
  - 用户不手动创建内容，仅对 Agent 产出进行审阅、编辑、确认
  - **全局 Dream 导航以 `/story-workspace/dream` 为 canonical 入口；`/story-workspace` 与 `/story-workspace/dashboard` 仅作兼容重定向，不维护平行状态**
  - **Dream 页面设置运行级审阅 gate；全部必审产出确认前禁止工作流继续或结束**
  - **确认动作必须幂等：首次合法确认后只发出一次继续/结束信号；重复点击、刷新或网络重试不得重复推进**
  - **服务端必须拒绝过期审阅版本和客户端直接请求绕过 gate**
  - Deck、Deck Editor、Deck Plugin 与 story-workspace 保持独立职责，不合并术语或数据所有权（DEC-009）
  - 每次创作锁定 Deck 插件版本与 Deck 运行配置快照引用；切换只影响新执行（DEC-010）
  - 未选择/不可用 Deck 插件或 Deck 运行配置不完整时禁止启动 Claude Agent（DEC-011）
  - Ink-Dream 不存储 Deck 运行配置密钥或完整提示词正文，只保存版本化引用和脱敏摘要（DEC-012）
  - 重试默认沿用固定版本；升级插件或配置必须创建新 run（DEC-014）

- 补充说明：
  - 本批 Issue 拆解基于已确认业务模型：Agent 产出剧本工作空间 → 页面渲染 → 用户审阅确认 → 后续执行
  - 复杂画布改为数据表呈现，排除平台视频、移动端/平板端、用户手动创建内容
  - SUO-214 / SUO-215 设计增量引入 Deck/Agent 端到端集成，需新增对应 Issue
  - **SUO-230 设计增量引入 Dream 导航与审阅 Gate，需增量更新既有 Issue 并新增 SUO-230-* 系列 Issue**
  - 设计文档中的 CLARIFICATION_NEEDED 已单列，采用默认假设时标注风险

---

## 2. Issue 总览表

### 2.1 稳定基线 Issue（SUO-211/212/213 已完成，保持不变）

| Issue ID | 标题 | 类型 | 优先级 | 标签 | 前置依赖 | 分发去向 | 状态 |
|---|---|---|---|---|---|---|---|
| `SUO-201-BE-001` | 数据库 Schema 与数据表初始化 | backend | P0 | `database`,`schema`,`migration` | 无 | `@TaskDesignAgent` | ✅ 基线稳定 |
| `SUO-201-BE-002` | Story Workspace REST API 实现 | backend | P0 | `api`,`rest`,`crud` | `SUO-201-BE-001` | `@TaskDesignAgent` | ✅ 基线稳定 |
| `SUO-201-BE-003` | 审阅状态流转与批量操作 API | backend | P0 | `api`,`review`,`workflow` | `SUO-201-BE-002` | `@TaskDesignAgent` | ✅ 基线稳定 |
| `SUO-201-BE-004` | Agent 产出数据接收与存储集成 | backend | P0 | `agent`,`integration`,`sse` | `SUO-201-BE-001` | `@TaskDesignAgent` | ✅ 基线稳定 |
| `SUO-201-FE-001` | 三栏布局骨架与全局样式 | frontend | P0 | `layout`,`ui`,`desktop-only` | 无 | `@TaskDesignAgent` | ✅ 基线稳定 |
| `SUO-201-FE-002` | Sidebar 导航与路由配置 | frontend | P0 | `navigation`,`router`,`sidebar` | `SUO-201-FE-001` | `@TaskDesignAgent` | ✅ 基线稳定 |
| `SUO-201-FE-003` | 数据表格组件（故事/角色/场景） | frontend | P0 | `table`,`component`,`data-display` | `SUO-201-FE-002` | `@TaskDesignAgent` | ✅ 基线稳定 |
| `SUO-201-FE-004` | 审阅面板（Review Panel）与审阅操作 | frontend | P0 | `review`,`panel`,`workflow` | `SUO-201-FE-003` | `@TaskDesignAgent` | ✅ 基线稳定 |
| `SUO-201-FE-005` | 工作台首页 Dashboard | frontend | P1 | `dashboard`,`overview` | `SUO-201-FE-003` | `@TaskDesignAgent` | ✅ 基线稳定 |
| `SUO-201-FE-006` | 空态/加载/错误/选中态组件 | frontend | P1 | `state`,`ui`,`ux` | `SUO-201-FE-003` | `@TaskDesignAgent` | ✅ 基线稳定 |
| `SUO-201-SH-001` | 前端-后端联调：审阅工作流 E2E | shared | P0 | `e2e`,`integration`,`review-workflow` | `SUO-201-BE-003`, `SUO-201-FE-004` | `@TaskDesignAgent` | ✅ 基线稳定 |
| `SUO-201-SH-002` | 命名规范与类型定义共享包 | shared | P0 | `naming`,`types`,`shared` | 无 | `@TaskDesignAgent` | ✅ 基线稳定 |
| `SUO-201-DO-001` | Story Workspace 使用文档 | docs | P2 | `documentation`,`user-guide` | `SUO-201-SH-001` | `@TaskDesignAgent` | ✅ 基线稳定 |

### 2.2 增量新增/变更 Issue（由 SUO-214/SUO-215 设计增量引入）

| Issue ID | 标题 | 类型 | 优先级 | 标签 | 前置依赖 | 分发去向 |
|---|---|---|---|---|---|---|
| `SUO-226-BE-001` | Workflow Binding 与 Run 数据模型 | backend | P0 | `database`,`schema`,`workflow-run`,`delta` | `SUO-201-BE-001` | `@TaskDesignAgent` |
| `SUO-226-BE-002` | Deck 插件目录查询与选择 API | backend | P0 | `api`,`deck-plugin`,`directory` | `SUO-201-BE-002` | `@TaskDesignAgent` |
| `SUO-226-BE-003` | Deck 运行配置预检与就绪状态 API | backend | P0 | `api`,`deck-runtime-config`,`preflight` | `SUO-226-BE-002` | `@TaskDesignAgent` |
| `SUO-226-BE-004` | Workflow Run 创建与执行上下文 API | backend | P0 | `api`,`workflow-run`,`agent-context` | `SUO-226-BE-001`, `SUO-226-BE-003` | `@TaskDesignAgent` |
| `SUO-226-BE-005` | Agent 集成适配：带锁定上下文的执行触发 | backend | P0 | `agent`,`integration`,`deck-runtime` | `SUO-201-BE-004`, `SUO-226-BE-004` | `@TaskDesignAgent` |
| `SUO-226-FE-001` | Dashboard Deck 工作流上下文条 | frontend | P0 | `dashboard`,`deck-selector`,`workflow-context` | `SUO-201-FE-005` | `@TaskDesignAgent` |
| `SUO-226-FE-002` | 审阅面板来源溯源与版本信息展示 | frontend | P1 | `review`,`provenance`,`version` | `SUO-201-FE-004` | `@TaskDesignAgent` |
| `SUO-226-FE-003` | 配置/执行/失败状态 UI 组件 | frontend | P1 | `state`,`error-ui`,`workflow-status` | `SUO-201-FE-006` | `@TaskDesignAgent` |
| `SUO-226-SH-001` | Deck 运行配置技术传输合同定义 | shared | P0 | `contract`,`api-spec`,`deck-runtime` | `SUO-201-SH-002` | `@TaskDesignAgent` |
| `SUO-226-SH-002` | 端到端工作流集成 E2E（Deck→Agent→审阅） | shared | P0 | `e2e`,`integration`,`deck-agent-review` | `SUO-226-BE-005`, `SUO-226-FE-001` | `@TaskDesignAgent` |

### 2.3 SUO-230 增量新增 Issue（由 DEC-017/DEC-018 设计增量引入）

| Issue ID | 标题 | 类型 | 优先级 | 标签 | 前置依赖 | 分发去向 |
|---|---|---|---|---|---|---|
| `SUO-230-FE-001` | TopNavBar Dream 导航项与 canonical 路由 | frontend | P0 | `navigation`,`router`,`dream-entry`,`delta` | `SUO-201-FE-002` | `@TaskDesignAgent` |
| `SUO-230-FE-002` | Dream 页面与 ReviewGate 组件 | frontend | P0 | `dream-page`,`review-gate`,`workflow-ui`,`delta` | `SUO-226-FE-001`, `SUO-201-FE-004` | `@TaskDesignAgent` |
| `SUO-230-BE-001` | 审阅 gate 服务端聚合与防绕过验证 | backend | P0 | `api`,`review-gate`,`idempotency`,`security`,`delta` | `SUO-201-BE-003`, `SUO-226-BE-004` | `@TaskDesignAgent` |
| `SUO-230-SH-001` | 确认幂等与审阅版本校验联调 | shared | P0 | `e2e`,`idempotency`,`review-gate`,`security` | `SUO-230-BE-001`, `SUO-230-FE-002` | `@TaskDesignAgent` |

---

## 3. Issue 明细

### 3.1 稳定基线 Issue 明细（保持不变，仅追加引用）

> 以下 Issue 为 SUO-211 / SUO-212 / SUO-213 已完成基线，**不得反向改写其 exec 结论**。本次增量仅追加对新设计决策（DEC-009～DEC-016）的引用，不修改原有验收条件或范围。

#### SUO-201-BE-001（基线稳定）

- 标题：数据库 Schema 与数据表初始化
- 类型：backend
- 优先级：P0
- 标签：`database`,`schema`,`migration`
- 描述：根据设计稿数据表结构，创建 story-workspace 相关的数据库表及索引。
- **增量影响**：
  - 既有六表（stories, characters, scenes, story_characters, scene_characters, workspaces）可保留
  - 需追加 workflow binding/run 相关表（见 SUO-226-BE-001），采用 additive migration
- 验收条件：保持原基线不变，追加 `workflow_run_id` 字段已存在于 stories 表
- 前置依赖：无
- 关联路径：`backend/src/db/migrations/`
- 分发去向：`@TaskDesignAgent`
- 主责 Agent：`TaskDesignAgent`
- 设计决策引用：`DEC-004`，**新增引用 `DEC-010`（版本锁定）、`DEC-012`（数据最小化）**
- 备注：基线稳定，不修改。新增表由 SUO-226-BE-001 处理。

---

#### SUO-201-BE-002（基线稳定）

- 标题：Story Workspace REST API 实现
- 类型：backend
- 优先级：P0
- 标签：`api`,`rest`,`crud`
- 描述：实现 story-workspace 的 REST API 路由 CRUD 操作。
- **增量影响**：既有 CRUD 端点保持兼容；新增端点由 SUO-226-BE-002～004 处理
- 验收条件：保持原基线不变
- 前置依赖：`SUO-201-BE-001`
- 关联路径：`backend/src/routes/story-workspace/`
- 分发去向：`@TaskDesignAgent`
- 主责 Agent：`TaskDesignAgent`
- 设计决策引用：`DEC-004`，**新增引用 `DEC-009`（职责独立）**
- 备注：基线稳定，不修改。

---

#### SUO-201-BE-003（基线稳定）

- 标题：审阅状态流转与批量操作 API
- 类型：backend
- 优先级：P0
- 标签：`api`,`review`,`workflow`
- 描述：实现审阅状态流转的核心 API。
- **增量影响**：审阅状态枚举保持 `pending/confirmed/rejected`；确认后需关联 `workflow_run_id` 回写
- 验收条件：保持原基线不变，追加确认操作需保留来源 `workflow_run_id`
- 前置依赖：`SUO-201-BE-002`
- 关联路径：`backend/src/routes/story-workspace/`
- 分发去向：`@TaskDesignAgent`
- 主责 Agent：`TaskDesignAgent`
- 设计决策引用：`DEC-007`, `DEC-008`，**新增引用 `DEC-010`（版本锁定）、`DEC-014`（重试规则）**
- 备注：基线稳定，不修改。驳回重生成需绑定原 run 版本，见 SUO-226-BE-005。

---

#### SUO-201-BE-004（基线稳定，需适配）

- 标题：Agent 产出数据接收与存储集成
- 类型：backend
- 优先级：P0
- 标签：`agent`,`integration`,`sse`
- 描述：实现 claude-agent 服务与 story-workspace 的数据集成。
- **增量影响**：**高**。原有"Chat 直接触发 Agent"需变为"已选择插件 + Deck 运行配置版本引用 → Agent"。输出需关联 `workflow_run_id`。
- 验收条件：保持原基线不变，追加：
  - [ ] Agent 接收执行请求时必须携带已锁定的 `deck_plugin_id` + `deck_plugin_version` + `deck_runtime_snapshot_id`
  - [ ] 产出数据必须关联 `workflow_run_id`
  - [ ] 未绑定工作流的 Chat 输入不得直接触发 Agent 执行
- 前置依赖：`SUO-201-BE-001`
- 关联路径：`backend/src/services/story-workspace/agent-integration.ts`
- 分发去向：`@TaskDesignAgent`
- 主责 Agent：`TaskDesignAgent`
- 设计决策引用：`DEC-007`，**新增引用 `DEC-009`～`DEC-014`**
- 备注：
  - **[CLARIFICATION_NEEDED]** Agent 产出的触发方式：设计稿收敛为"先在 story-workspace 选择 Deck 插件并通过 Deck 运行配置校验，再由现有 Chat 指令携带该工作流上下文触发 Claude Agent"
  - **[RISK]** 既有实现已按 Chat 直触发推进，需兼容适配层过渡
  - 具体适配由 SUO-226-BE-005 处理

---

#### SUO-201-FE-001～FE-006（基线稳定）

- 标题：前端布局/导航/表格/审阅面板/Dashboard/状态组件
- 类型：frontend
- 优先级：P0/P1
- **增量影响**：低至中。三栏骨架、Sidebar、表格、审阅面板核心交互不变。
- **增量影响（SUO-230）**：**中**。需追加：
  - Dashboard 页面需升级为 Dream 页面（`StoryWorkspaceDreamPage`），`/story-workspace/dashboard` 重定向至 `/story-workspace/dream`
  - 审阅面板需与 `StoryWorkspaceReviewGate` 联动；确认需带运行 ID 与审阅版本
  - 路由配置需追加 `/story-workspace/dream` canonical 入口
- **需增量适配项**：
  - Dashboard 需新增 Deck 工作流上下文条（SUO-226-FE-001）
  - 审阅面板需展示来源溯源信息（SUO-226-FE-002）
  - 状态组件需增加配置/权限/运行错误态（SUO-226-FE-003）
  - **Dream 导航与路由（SUO-230-FE-001）**
  - **Dream 页面 ReviewGate 与审阅闭环（SUO-230-FE-002）**
- 分发去向：`@TaskDesignAgent`
- 主责 Agent：`TaskDesignAgent`
- 设计决策引用：`DEC-004`，**新增引用 `DEC-017`（Dream 导航）、`DEC-018`（审阅 Gate）**
- 备注：基线稳定，不推翻布局与审阅 UI。通过新增组件和状态适配推进。

---

#### SUO-201-SH-001（基线稳定，需扩展 E2E 场景）

- 标题：前端-后端联调：审阅工作流 E2E
- 类型：shared
- 优先级：P0
- **增量影响（SUO-226）**：既有审阅 E2E 保留；需新增 Deck→Agent→审阅端到端场景（SUO-226-SH-002）
- **增量影响（SUO-230）**：**中**。需追加 Dream 导航 → 产出 → 渲染 → 确认/驳回 → gate 放行/阻断 的端到端验证场景（SUO-230-SH-001）
- 分发去向：`@TaskDesignAgent` + `@TaskDesignAgent`
- 主责 Agent：`TaskDesignAgent`
- 协作 Agent：`TaskDesignAgent`
- 设计决策引用：**新增引用 `DEC-017`（Dream 导航）、`DEC-018`（审阅 Gate）**
- 备注：基线 E2E 保留。新增端到端场景由 SUO-226-SH-002 和 **SUO-230-SH-001** 处理。

---

#### SUO-201-SH-002（基线稳定，需扩展类型）

- 标题：命名规范与类型定义共享包
- 类型：shared
- 优先级：P0
- **增量影响**：需增加 manifest 摘要、binding、run、配置引用、运行状态和错误码类型
- 验收条件：保持原基线不变，追加：
  - [ ] `StoryWorkflowBinding` 类型定义
  - [ ] `StoryWorkflowRun` 类型定义
  - [ ] `DeckPluginManifest` 摘要类型
  - [ ] `DeckRuntimeSnapshot` 引用类型
  - [ ] 工作流运行状态枚举：`configuring` | `ready` | `queued` | `running` | `output_validating` | `pending_review` | `confirmed` | `rejected` | `failed` | `cancelled`
  - [ ] 错误码类型：`WORKFLOW_SELECTION_REQUIRED` | `PLUGIN_VERSION_UNAVAILABLE` | `DECK_RUNTIME_CONFIG_INVALID` | `DECK_RUNTIME_CONFIG_UNAVAILABLE` | `WORKFLOW_PERMISSION_DENIED` | `AGENT_EXECUTION_FAILED` | `OUTPUT_CONTRACT_INVALID` | `CONFIG_VERSION_DRIFT`
- 分发去向：`@TaskDesignAgent` + `@TaskDesignAgent`
- 主责 Agent：`TaskDesignAgent`
- 协作 Agent：`TaskDesignAgent`
- 设计决策引用：`DEC-004`，**新增引用 `DEC-009`～`DEC-016`**
- 备注：类型版本兼容后再传播，不得破坏现有枚举和字段。

---

### 3.2 增量新增 Issue 明细

#### SUO-226-BE-001

- 标题：Workflow Binding 与 Run 数据模型
- 类型：backend
- 优先级：P0
- 标签：`database`,`schema`,`workflow-run`,`delta`
- 描述：
  根据 SUO-215 设计增量，创建 workflow binding 与 workflow run 的数据模型。Binding 记录用户选择的 Deck 插件与 Deck 运行配置组合；Run 记录单次执行上下文与状态。保证版本锁定、来源溯源和审计能力。

- 验收条件：
  - [ ] `story_workspace_workflow_bindings` 表创建，字段：
    - `id` (UUID, PK), `workspace_id` (UUID), `creator_id` (UUID)
    - `plugin_id` (string), `plugin_version` (string)
    - `deck_runtime_profile_id` (string), `config_version` (string)
    - `created_at`, `updated_at`
  - [ ] `story_workspace_workflow_runs` 表创建，字段：
    - `id` (UUID, PK), `binding_id` (UUID, FK)
    - `idempotency_key` (string, unique)
    - `input` (jsonb)
    - `status` (enum: configuring/ready/queued/running/output_validating/pending_review/confirmed/rejected/failed/cancelled)
    - `agent_session_id` (string)
    - `error_code` (string), `failed_step` (string)
    - `retry_of_run_id` (UUID, nullable)
    - `config_summary_hash` (string)
    - `started_at`, `finished_at`, `created_at`
  - [ ] stories 表追加 `workflow_run_id` 外键（如尚未添加）
  - [ ] 索引：`idx_bindings_workspace` (workspace_id), `idx_runs_binding` (binding_id), `idx_runs_status` (status), `idx_runs_idempotency` (idempotency_key)
  - [ ] Migration 可回滚，additive 方式（不重建既有表）

- 前置依赖：`SUO-201-BE-001`

- 关联路径：
  - `backend/src/db/migrations/`
  - `backend/src/db/schema/story-workspace/workflow-binding.ts`
  - `backend/src/db/schema/story-workspace/workflow-run.ts`

- 分发去向：`@TaskDesignAgent`

- 主责 Agent：`TaskDesignAgent`

- 协作 Agent：无

- 设计决策引用：
  - `DEC-010`：单次运行锁定 Deck 插件版本与 Deck 运行配置快照
  - `DEC-012`：Ink-Dream 只保存版本引用/脱敏摘要
  - `DEC-013`：选择 Deck 插件即建立可审计 workflow binding
  - `DEC-014`：重试默认沿用固定版本
  - 设计稿 §6.1 最小对象 / §5.6 工作流运行记录

- 备注：
  - 采用 additive migration，不得重建或破坏既有 story-workspace 表
  - `config_summary_hash` 用于审计，不存储敏感配置值

---

#### SUO-226-BE-002

- 标题：Deck 插件目录查询与选择 API
- 类型：backend
- 优先级：P0
- 标签：`api`,`deck-plugin`,`directory`
- 描述：
  实现 Deck 插件目录查询 API，供 story-workspace 展示当前用户/工作区有权限且已发布、启用的 Deck 插件列表。仅返回非敏感 manifest 字段（plugin_id, version, display_name, workflow_key, capabilities, status）。

- 验收条件：
  - [ ] `GET /api/story-workspace/deck-plugins` — 返回当前 workspace 可用插件列表
  - [ ] 过滤条件：status = published，用户有权限，workspace 隔离
  - [ ] 返回字段：plugin_id, version, display_name, workflow_key, capabilities, input_schema_summary, status, published_at
  - [ ] 不返回 Deck 运行配置详情、提示词正文或密钥引用
  - [ ] 支持按名称搜索、按能力筛选
  - [ ] 空态：无可用的 Deck 插件时返回空数组 + 提示前往 Deck 编辑器
  - [ ] 权限校验：仅返回当前用户/工作区有权限的插件

- 前置依赖：`SUO-201-BE-002`

- 关联路径：
  - `backend/src/routes/story-workspace/deck-plugins.ts`
  - `backend/src/services/story-workspace/deck-plugin-directory.ts`

- 分发去向：`@TaskDesignAgent`

- 主责 Agent：`TaskDesignAgent`

- 协作 Agent：无

- 设计决策引用：
  - `DEC-009`：Deck/Deck Plugin/story-workspace 职责独立（已废弃"Desk"口径，统一为 Deck）
  - `DEC-012`：不存储 Deck 运行配置密钥或完整提示词（已废弃"Desk"口径）
  - 设计稿 §5.1 选择工作流 / §6.1 DeckPluginManifest

- 备注：
  - **[CLARIFICATION_NEEDED]** Deck 插件 manifest 的物理存储/API 合同尚未确定
  - Clarification owner：`@CEOOrchestrator` 路由 Deck 运行配置 owner
  - 在合同确定前，采用 mock 或最小适配层实现接口，不得阻塞 schema 和 run 模型开发

---

#### SUO-226-BE-003

- 标题：Deck 运行配置预检与就绪状态 API
- 类型：backend
- 优先级：P0
- 标签：`api`,`deck-runtime-config`,`preflight`
- 描述：
  实现 Deck 运行配置预检 API。根据所选 Deck 插件解析其所需的 Deck Agent 提示词与插件配置，校验发布/启用状态、访问权限、配置完整性与版本兼容性。校验通过后返回就绪状态与 `deck_runtime_snapshot_id`；任一校验失败返回具体错误类别，不启动 Agent。

- 验收条件：
  - [ ] `POST /api/story-workspace/deck-runtime-preflight` — 提交 plugin_id + plugin_version，返回预检结果
  - [ ] 预检项：Deck runtime profile 存在性、config_version 有效性、权限校验、schema 兼容性
  - [ ] 通过响应：status=`ready`, deck_runtime_profile_id, config_version, deck_runtime_snapshot_id, 脱敏配置摘要
  - [ ] 失败响应：status=`not_ready`, error_code (`DECK_RUNTIME_CONFIG_INVALID`/`DECK_RUNTIME_CONFIG_UNAVAILABLE`/`WORKFLOW_PERMISSION_DENIED`), 缺失类别列表（非敏感）
  - [ ] 前端不获得密钥明文、提示词正文或高敏配置
  - [ ] 预检结果缓存 TTL（建议 60s），避免重复解析
  - [ ] 幂等：同一 plugin + version 在短时间内返回一致结果

- 前置依赖：`SUO-226-BE-002`

- 关联路径：
  - `backend/src/routes/story-workspace/deck-runtime-preflight.ts`
  - `backend/src/services/story-workspace/deck-runtime-preflight.ts`

- 分发去向：`@TaskDesignAgent`

- 主责 Agent：`TaskDesignAgent`

- 协作 Agent：无

- 设计决策引用：
  - `DEC-011`：Deck 运行配置 前置校验未通过时禁止启动 Claude Agent
  - `DEC-012`：Ink-Dream 只保存版本引用/脱敏摘要
  - 设计稿 §4.2 执行前校验 / §8 错误码定义

- 备注：
  - **[CLARIFICATION_NEEDED]** Deck 运行配置 API、权限模型和密钥存储能力未知
  - Clarification owner：`@CEOOrchestrator` 路由平台 owner
  - 在 Deck 运行配置合同确定前，接口可返回 mock 就绪状态，但错误码结构必须按设计稿实现
  - 不得自行编造 Deck 运行配置 API 合同；必须在 Issue 评论区记录待确认项

---

#### SUO-226-BE-004

- 标题：Workflow Run 创建与执行上下文 API
- 类型：backend
- 优先级：P0
- 标签：`api`,`workflow-run`,`agent-context`
- 描述：
  实现 Workflow Run 的创建、查询和状态管理 API。创作者选择 Deck 插件并通过 Deck 运行配置预检后，创建单次 `workflow_run`，固定 `plugin_id + plugin_version + deck_runtime_profile_id + config_version`。支持幂等创建（idempotency_key）、状态查询和取消。

- 验收条件：
  - [ ] `POST /api/story-workspace/workflow-runs` — 创建 run，body: { binding_id, input, idempotency_key }
  - [ ] 创建时自动固定版本：plugin_id, plugin_version, deck_runtime_profile_id, config_version 从 binding 读取
  - [ ] `GET /api/story-workspace/workflow-runs/:id` — 查询 run 详情与状态
  - [ ] `GET /api/story-workspace/workflow-runs` — 列表查询（按状态、时间筛选）
  - [ ] `POST /api/story-workspace/workflow-runs/:id/cancel` — 取消运行（仅限 queued/running 状态）
  - [ ] 状态流转：configuring → ready → queued → running → output_validating → pending_review → confirmed/rejected/failed/cancelled
  - [ ] 重试：`POST /api/story-workspace/workflow-runs/:id/retry` — 默认沿用原固定版本，创建新 run attempt，关联 `retry_of_run_id`
  - [ ] 切换工作流：用户改选插件时创建新 binding + 新 run，不得覆盖原运行

- 前置依赖：`SUO-226-BE-001`, `SUO-226-BE-003`

- 关联路径：
  - `backend/src/routes/story-workspace/workflow-runs.ts`
  - `backend/src/services/story-workspace/workflow-run.service.ts`

- 分发去向：`@TaskDesignAgent`

- 主责 Agent：`TaskDesignAgent`

- 协作 Agent：无

- 设计决策引用：
  - `DEC-010`：单次运行锁定版本
  - `DEC-013`：选择即建立可审计 binding；每次执行创建幂等 run
  - `DEC-014`：重试默认沿用固定版本
  - 设计稿 §5.2 详细规则 / §7.2 工作流运行状态

- 备注：
  - `idempotency_key` 避免重复点击或网络重试产生重复剧本
  - 历史剧本详情必须以只读来源信息展示插件名称/版本、运行 ID 与 Deck 运行配置快照标识

---

#### SUO-226-BE-005

- 标题：Agent 集成适配：带锁定上下文的执行触发
- 类型：backend
- 优先级：P0
- 标签：`agent`,`integration`,`deck-runtime`
- 描述：
  适配现有 claude-agent 服务集成，将"Chat 直接触发 Agent"收敛为"已选择插件 + Deck 运行配置版本引用 → Agent"。Chat 指令必须携带已校验的 Deck 运行上下文（`workflow_run_id` + 锁定版本信息）。Agent 使用服务身份向 Deck 解析已授权的运行配置并执行。

- 验收条件：
  - [ ] Chat 触发 Agent 时，请求必须包含 `workflow_run_id` 或引导用户先选择工作流
  - [ ] Agent 接收 `plugin_id`, `plugin_version`, `deck_runtime_snapshot_id` 及用户输入
  - [ ] Agent 以服务身份向 Deck 解析已授权的运行配置（不在浏览器端解析）
  - [ ] Agent 输出经合同校验后写入 story-workspace 数据表，标记 `review_status=pending`
  - [ ] 输出必须关联 `workflow_run_id`、来源版本与执行状态
  - [ ] 未绑定工作流的 Chat 输入返回 `WORKFLOW_SELECTION_REQUIRED` 错误，引导选择
  - [ ] 与现有 claude-agent SSE 端点集成不破坏现有 Chat / Deck 功能
  - [ ] 错误处理：Agent 执行失败时记录 `error_code` + `failed_step`，不阻塞用户操作

- 前置依赖：`SUO-201-BE-004`, `SUO-226-BE-004`

- 关联路径：
  - `backend/src/services/story-workspace/agent-integration.ts`
  - `backend/src/services/story-workspace/workflow-run.service.ts`
  - `docs/CLAUDE.md`

- 分发去向：`@TaskDesignAgent`

- 主责 Agent：`TaskDesignAgent`

- 协作 Agent：无

- 设计决策引用：
  - `DEC-007`：核心工作流
  - `DEC-009`：职责独立
  - `DEC-011`：预检失败禁止启动
  - `DEC-012`：服务身份解析配置
  - `DEC-014`：重试沿用固定版本
  - 设计稿 §5.1 主序列 / §10.2 端到端集成

- 备注：
  - **[RISK]** 既有实现已按 Chat 直触发推进，需兼容适配层过渡
  - 建议采用"旧路径保留 + 新路径并行"策略，逐步迁移
  - 禁止静默改写 SSE 核心协议

---

#### SUO-226-FE-001

- 标题：Dashboard Deck 工作流上下文条
- 类型：frontend
- 优先级：P0
- 标签：`dashboard`,`deck-selector`,`workflow-context`
- 描述：
  在 Dashboard 页面顶部实现 Deck 工作流上下文条控件。该控件位于 Main Content Area 的 Dashboard 标题下方，不改变三栏宽度。支持选择已发布可用的 Deck 插件、展示 Deck 运行配置就绪状态、显示工作流摘要，并提供"在 Deck 编辑器中配置"跳转。

- 验收条件：
  - [ ] `StoryWorkspaceWorkflowContextBar` 组件实现
  - [ ] Deck 插件选择器：下拉展示可用插件名称 + 版本
  - [ ] 选择后展示：插件名称、版本、工作流摘要（步骤数、输入要求）
  - [ ] Deck 运行配置就绪状态：● 已就绪（绿色）/ ● 未就绪（红色）/ ● 检查中（loading）
  - [ ] "在 Deck 编辑器中配置 ↗" 跳转链接
  - [ ] 未选择状态：占位文案"请选择 Deck 创作工作流"，禁止启动 Agent
  - [ ] 无可用插件状态：空态 + "在 Deck 编辑器中自定义并发布"链接
  - [ ] 插件停用/无权限/版本不可用：保留原选择名称 + 红色原因标记，要求重新选择
  - [ ] Deck 运行配置缺失：展示非敏感缺失类别 + "前往 Deck 运行配置"链接
  - [ ] 执行中状态：选择器只读，展示 `workflow_run_id` 进度摘要
  - [ ] 切换插件只影响下一次创作，已生成剧本保留原版本引用

- 前置依赖：`SUO-201-FE-005`

- 关联路径：
  - `frontend/src/components/story-workspace/workflow/StoryWorkspaceWorkflowContextBar.tsx`
  - `frontend/src/pages/story-workspace/StoryWorkspaceDashboardPage.tsx`

- 分发去向：`@TaskDesignAgent`

- 主责 Agent：`TaskDesignAgent`

- 协作 Agent：无

- 设计决策引用：
  - `DEC-009`：职责独立
  - `DEC-010`：版本锁定
  - `DEC-011`：预检失败禁止启动
  - 设计稿 §2.3 Deck 工作流上下文条 / §4.5.1 核心工作流

- 备注：
  - 该组件不是"新建故事"按钮，而是工作流选择器
  - 选择器只列出已发布、启用且有权限的 Deck 插件版本
  - 不得自动使用"默认 Deck 插件"绕过选择

---

#### SUO-226-FE-002

- 标题：审阅面板来源溯源与版本信息展示
- 类型：frontend
- 优先级：P1
- 标签：`review`,`provenance`,`version`
- 描述：
  在审阅面板（Review Panel）中增加来源溯源信息展示。用户审阅 Agent 生成内容时，可查看该产出的工作流来源：Deck 插件名称/版本、运行 ID、Deck 运行配置快照标识、生成时间。Deck 提示词正文和密钥不展示。

- 验收条件：
  - [ ] 审阅面板标题栏下方增加"来源"折叠区域
  - [ ] 展示：Deck 插件名称 + 版本（只读）
  - [ ] 展示：`workflow_run_id`（可点击复制）
  - [ ] 展示：Deck 运行配置快照标识（只读，非敏感）
  - [ ] 展示：Agent 生成时间
  - [ ] 不展示：Deck 提示词正文、密钥、敏感配置值
  - [ ] 历史剧本详情以只读来源信息展示，不可编辑
  - [ ] 驳回后重新生成的产出显示"重试来源"标记

- 前置依赖：`SUO-201-FE-004`

- 关联路径：
  - `frontend/src/components/story-workspace/review/StoryWorkspaceReviewPanel.tsx`
  - `frontend/src/components/story-workspace/review/StoryWorkspaceProvenanceInfo.tsx`

- 分发去向：`@TaskDesignAgent`

- 主责 Agent：`TaskDesignAgent`

- 协作 Agent：无

- 设计决策引用：
  - `DEC-010`：版本锁定与溯源
  - `DEC-012`：数据最小化
  - 设计稿 §5.2 渲染与审阅 / §6.1 最小对象

- 备注：
  - 来源信息区域默认折叠，点击展开
  - 不得暴露 Deck 敏感配置值到前端

---

#### SUO-226-FE-003

- 标题：配置/执行/失败状态 UI 组件
- 类型：frontend
- 优先级：P1
- 标签：`state`,`error-ui`,`workflow-status`
- 描述：
  实现 Deck 运行配置 配置相关状态 UI 组件。包括：配置缺失状态、权限不足状态、执行失败状态、版本漂移状态。这些组件复用现有空态/错误态视觉规范，但针对工作流场景定制文案和恢复动作。

- 验收条件：
  - [ ] `StoryWorkspaceWorkflowUnselectedState`：未选择 Deck 插件，引导选择
  - [ ] `StoryWorkspacePluginUnavailableState`：插件停用/删除/无权限，要求重新选择
  - [ ] `StoryWorkspaceDeckRuntimeConfigNotReadyState`：Deck 运行配置缺失，展示缺失类别 + Deck 入口
  - [ ] `StoryWorkspaceWorkflowRunningState`：执行中，展示步骤进度与 `workflow_run_id`
  - [ ] `StoryWorkspaceWorkflowFailedState`：执行失败，展示失败步骤/错误码 + 重试按钮
  - [ ] `StoryWorkspaceOutputInvalidState`：输出合同不匹配，展示诊断信息
  - [ ] 所有状态组件遵循 Ink & Memory 视觉规范（暖纸色、轻纸面分区）
  - [ ] 恢复动作按钮明确：重试（沿用原版本）、选择新工作流（创建新 run）

- 前置依赖：`SUO-201-FE-006`

- 关联路径：
  - `frontend/src/components/story-workspace/state/`

- 分发去向：`@TaskDesignAgent`

- 主责 Agent：`TaskDesignAgent`

- 协作 Agent：无

- 设计决策引用：
  - `DEC-011`：预检失败禁止启动
  - 设计稿 §4.5 配置、执行与失败状态 / §8 错误码

- 备注：
  - 错误码展示为非敏感摘要，不泄露配置细节
  - 重试按钮默认沿用锁定快照，不自动升级版本

---

#### SUO-226-SH-001

- 标题：Deck 运行配置 技术传输合同定义
- 类型：shared
- 优先级：P0
- 标签：`contract`,`api-spec`,`deck-runtime`
- 描述：
  定义 story-workspace 与 Deck 插件目录、Deck 运行配置服务之间的技术传输合同。包括：可用插件查询接口、Deck 运行配置预检接口、配置引用格式、权限校验规则、错误码规范。该合同是前后端实现 Deck 运行配置集成的共同依据。

- 验收条件：
  - [ ] 定义 `DeckPluginManifest` 最小字段合同（plugin_id, version, display_name, workflow_key, capabilities, input_schema, output_schema, status, owner_id）
  - [ ] 定义 `DeckAgentProfile` 消费合同（deck_runtime_profile_id, prompt_version, model_policy, permission_policy, status）
  - [ ] 定义 `DeckPluginRuntimeConfig` 引用合同（deck_runtime_profile_id, plugin_id, config_version, schema_version, status）
  - [ ] 定义可用插件查询接口：请求/响应格式、筛选参数、权限头
  - [ ] 定义 Deck 运行配置预检接口：请求/响应格式、就绪/错误状态码
  - [ ] 定义错误码规范：`WORKFLOW_SELECTION_REQUIRED`, `PLUGIN_VERSION_UNAVAILABLE`, `DECK_RUNTIME_CONFIG_INVALID`, `DECK_RUNTIME_CONFIG_UNAVAILABLE`, `WORKFLOW_PERMISSION_DENIED`, `AGENT_EXECUTION_FAILED`, `OUTPUT_CONTRACT_INVALID`, `CONFIG_VERSION_DRIFT`
  - [ ] 定义版本锁定格式：plugin_id + plugin_version + deck_runtime_profile_id + config_version
  - [ ] 定义幂等键格式与重试规则
  - [ ] 文档化权限假设：workspace 隔离、服务身份访问、前端不脱敏

- 前置依赖：`SUO-201-SH-002`

- 关联路径：
  - `docs/contracts/story-workspace-deck-runtime-api.md`（新建）
  - `shared/types/story-workspace/deck-runtime.ts`

- 分发去向：`@TaskDesignAgent` + `@TaskDesignAgent`

- 主责 Agent：`TaskDesignAgent`

- 协作 Agent：`TaskDesignAgent`

- 设计决策引用：
  - `DEC-009`：职责独立
  - `DEC-012`：数据最小化
  - 设计稿 §6 最小数据与配置边界 / §8 错误码

- 备注：
  - **[CLARIFICATION_NEEDED]** Deck 运行配置的内部组件边界（manifest vs runtime config vs secret provider）尚未确认
  - **[CLARIFICATION_NEEDED]** Deck manifest 与 Deck 运行配置子组件的物理存储/API 分工尚未确定
  - Clarification owner：`@CEOOrchestrator` 路由产品/平台 owner
  - **本 Issue 不得自行编造 API 合同**；在合同确定前，采用设计稿中的默认假设定义接口草案，标记为 `[DRAFT]` 待确认
  - 合同冻结前，下游实现使用 mock 或最小适配层

---

#### SUO-226-SH-002

- 标题：端到端工作流集成 E2E（Deck→Agent→审阅）
- 类型：shared
- 优先级：P0
- 标签：`e2e`,`integration`,`deck-runtime-agent`
- 描述：
  端到端验证完整工作流：创作者在 Deck 编辑器发布插件 → 在 story-workspace 选择插件 → Deck 运行配置预检通过 → 锁定版本 → Chat 携带上下文触发 Agent → Agent 按工作流执行 → 产出持久化 → 页面渲染 → 用户审阅确认 → 工作流继续或结束。

- 验收条件：
  - [ ] Deck 插件发布后可被 story-workspace 查询到
  - [ ] 选择插件后 Deck 运行配置预检正确返回就绪/错误状态
  - [ ] 预检通过后创建 workflow run，版本正确锁定
  - [ ] Chat 携带 workflow_run_id 触发 Agent，Agent 接收锁定上下文
  - [ ] Agent 产出后 story-workspace 正确展示待审阅项
  - [ ] 审阅面板展示来源溯源信息（插件名称/版本、run_id）
  - [ ] 确认后工作流状态正确流转，run 状态更新
  - [ ] 驳回后重试沿用原版本，创建新 run attempt
  - [ ] 切换插件后创建新 binding + 新 run，历史产出不受影响
  - [ ] 预检失败时 Agent 不被启动，页面展示明确恢复动作
  - [ ] 执行失败时展示失败状态与重试入口

- 前置依赖：`SUO-226-BE-005`, `SUO-226-FE-001`

- 关联路径：
  - `frontend/src/components/story-workspace/`
  - `backend/src/routes/story-workspace/`
  - `backend/src/services/story-workspace/`

- 分发去向：`@TaskDesignAgent` + `@TaskDesignAgent`

- 主责 Agent：`TaskDesignAgent`

- 协作 Agent：`TaskDesignAgent`

- 设计决策引用：
  - `DEC-007`～`DEC-014`
  - 设计稿 §5.1 主序列 / §10.2 端到端集成

- 备注：
  - 前端职责：工作流选择 UI、预检状态展示、审阅面板来源信息、错误状态 UI
  - 后端职责：插件目录、Deck 运行配置预检、run 创建与管理、Agent 适配、状态流转
  - 联调验证点：版本锁定不可被后续选择覆盖、驳回重试沿用原版本、切换插件创建新 run

---

### 3.3 SUO-230 增量 Issue 明细（由 DEC-017/DEC-018 引入）

#### SUO-230-FE-001

- 标题：TopNavBar Dream 导航项与 canonical 路由
- 类型：frontend
- 优先级：P0
- 标签：`navigation`,`router`,`dream-entry`,`delta`
- 描述：
  在现有全局 AppHeader / TopNavBar 中增加 Dream 导航项。该导航项是 `story-workspace` 业务域的全局入口，以 `/story-workspace/dream` 为 canonical 路由。兼容既有 `/story-workspace` 与 `/story-workspace/dashboard` 重定向。任一 `/story-workspace/*` 子页保持 Dream 选中，其他平台页面显示未选中。

- 验收条件：
  - [ ] `StoryWorkspaceDreamNavItem` 组件实现，内部标识 `story-workspace-dream`
  - [ ] 用户可见文案为 `Dream`
  - [ ] Canonical 目标：`/story-workspace/dream`
  - [ ] 兼容路由：`/story-workspace` 与 `/story-workspace/dashboard` 重定向至 `/story-workspace/dream`
  - [ ] 选中判定：当前路径为 `/story-workspace/dream` 或任一 `/story-workspace/*` 子页时选中
  - [ ] 选中表现：`aria-current="page"`，Charcoal Brown 600 字重，Memory Yellow 3px 短下划线
  - [ ] 未选中表现：非 story-workspace 页面为 Warm Brown、透明下划线；hover 复用 `--color-bg-hover`
  - [ ] 布局位置：沿用现有 AppHeader / TopNavBar 的 Logo 后横向导航组，不新增第二层顶部栏
  - [ ] 不改变三栏宽度（240px / 自适应 / 360px）
  - [ ] 键盘 focus 使用可见 Action Brown 轮廓

- 前置依赖：`SUO-201-FE-002`

- 关联路径：
  - `frontend/src/components/story-workspace/navigation/StoryWorkspaceDreamNavItem.tsx`
  - `frontend/src/components/TopNavBar.tsx`
  - `frontend/src/router/story-workspace.tsx`

- 分发去向：`@TaskDesignAgent`

- 主责 Agent：`TaskDesignAgent`

- 协作 Agent：无

- 设计决策引用：
  - `DEC-017`：全局 Dream 导航以 `/story-workspace/dream` 为 canonical 入口
  - 设计稿 §3.6.1 / §2.4.1

- 备注：
  - Dream 是业务域入口，Sidebar 的概览/故事/角色/场景是域内二级导航
  - 不得维护两份平行页面状态（Dashboard 与 Dream）
  - 重定向不得创建额外 store、重复请求或独立 `workflow_run_id`

---

#### SUO-230-FE-002

- 标题：Dream 页面与 ReviewGate 组件
- 类型：frontend
- 优先级：P0
- 标签：`dream-page`,`review-gate`,`workflow-ui`,`delta`
- 描述：
  实现 `StoryWorkspaceDreamPage` 页面与 `StoryWorkspaceReviewGate` 组件。Dream 页面是 canonical 入口页，同时展示工作流上下文条、四步审阅 gate（Agent 产出 → 页面渲染 → 用户审阅 → 继续/结束）、产出数据表及右侧 Review Panel。ReviewGate 在活动 `workflow_run_id` 存在时固定显示于 Main Content 标题/工作流上下文条下方、数据表上方。

- 验收条件：
  - [ ] `StoryWorkspaceDreamPage` 页面实现，组合既有 Dashboard 概览能力
  - [ ] `StoryWorkspaceReviewGate` 组件实现，包含四步进度指示
  - [ ] Gate 状态映射：
    - `queued`/`running` → "Agent 产出"高亮，表格骨架态
    - `output_validating` → "页面渲染"高亮，部分结果不可审阅
    - `pending_review` → "用户审阅"高亮，待审阅黄条与 Review Panel 可操作
    - 任一必审项 `rejected` → 红色阻断状态、修改意见及重新生成入口
    - 全部必审项 `confirmed` → 第四步解锁，可继续或结束
  - [ ] Gate 聚合当前 `workflow_run_id` 的全部必审故事、角色、场景
  - [ ] 任一项为 `pending` 或 `rejected` 时，继续/结束按钮禁用
  - [ ] 确认动作带运行 ID 与审阅版本校验，防过期确认
  - [ ] 驳回后显示修改意见输入框与"沿原快照重新生成"入口
  - [ ] 关闭面板、刷新、路由切换不改变 gate 状态
  - [ ] 页面同时可见：工作流上下文条、ReviewGate、数据表、Review Panel

- 前置依赖：`SUO-226-FE-001`, `SUO-201-FE-004`

- 关联路径：
  - `frontend/src/pages/story-workspace/StoryWorkspaceDreamPage.tsx`
  - `frontend/src/components/story-workspace/review/StoryWorkspaceReviewGate.tsx`
  - `frontend/src/components/story-workspace/review/StoryWorkspaceReviewPanel.tsx`

- 分发去向：`@TaskDesignAgent`

- 主责 Agent：`TaskDesignAgent`

- 协作 Agent：无

- 设计决策引用：
  - `DEC-017`：Dream 页面为 canonical 入口
  - `DEC-018`：运行级审阅 gate 在全部必审项确认前禁止继续
  - 设计稿 §3.6.2 / §2.4.2 / §2.4.3

- 备注：
  - Dashboard 页面保留复用，不再拥有独立路由状态
  - ReviewGate 与 Review Panel 必须显示同一运行来源
  - "保存"不等于确认；只有"确认通过"或"保存并确认"能确认

---

#### SUO-230-BE-001

- 标题：审阅 gate 服务端聚合与防绕过验证
- 类型：backend
- 优先级：P0
- 标签：`api`,`review-gate`,`idempotency`,`security`,`delta`
- 描述：
  实现服务端审阅 gate 聚合校验与防绕过机制。以 `workflow_run_id` 为维度聚合全部必审故事、角色、场景的审阅状态；任一项为 `pending` 或 `rejected` 时，拒绝继续/结束请求。确认动作必须校验运行 ID 与审阅版本，拒绝过期版本。确认后继续/结束必须幂等。

- 验收条件：
  - [ ] 服务端聚合查询：给定 `workflow_run_id`，返回全部关联 story/character/scene 的审阅状态
  - [ ] Gate 判定逻辑：任一项 `pending` 或 `rejected` → gate 锁定；全部 `confirmed` → gate 解锁
  - [ ] 确认 API (`POST /api/story-workspace/stories/:id/confirm`) 必须接收 `workflow_run_id` + `review_version`
  - [ ] 服务端校验：运行 ID 匹配且审阅版本未过期才允许确认
  - [ ] 确认后继续/结束 API 必须幂等：首次合法确认后只发出一次信号
  - [ ] 重复点击、刷新或网络重试不得重复推进
  - [ ] 客户端直接请求继续/结束时，服务端以聚合审阅状态拒绝未全部确认的请求
  - [ ] 驳回只记录意见并保持锁定；重新生成创建新 run attempt
  - [ ] 若内容已确认但后续继续失败，确认事实不回滚；页面进入失败态，幂等重试继续

- 前置依赖：`SUO-201-BE-003`, `SUO-226-BE-004`

- 关联路径：
  - `backend/src/routes/story-workspace/review-gate.ts`
  - `backend/src/services/story-workspace/review-gate.service.ts`
  - `backend/src/services/story-workspace/workflow-run.service.ts`

- 分发去向：`@TaskDesignAgent`

- 主责 Agent：`TaskDesignAgent`

- 协作 Agent：无

- 设计决策引用：
  - `DEC-018`：运行级审阅 gate
  - `DEC-010`：版本锁定
  - `DEC-014`：重试规则
  - 设计稿 §3.6.2 / §2.4.3

- 备注：
  - 这是安全关键 Issue；客户端 UI 锁定不能替代服务端校验
  - `pending_review` 为 canonical 运行状态；不新增第二个 API 枚举
  - 确认幂等通过数据库唯一约束或分布式锁实现

---

#### SUO-230-SH-001

- 标题：确认幂等与审阅版本校验联调
- 类型：shared
- 优先级：P0
- 标签：`e2e`,`idempotency`,`review-gate`,`security`
- 描述：
  端到端验证审阅 gate 的幂等性与防绕过能力。覆盖场景：正常确认流程、重复确认幂等、过期版本拒绝、客户端绕过请求被服务端拒绝、全部确认后仅放行一次、驳回后重新生成沿用原快照。

- 验收条件：
  - [ ] 正常流程：全部必审项确认后，继续/结束请求成功
  - [ ] 幂等验证：重复发送确认请求，仅第一次生效，后续返回已确认状态
  - [ ] 过期版本拒绝：Agent 重新生成后，对旧版本的确认请求被服务端拒绝
  - [ ] 防绕过验证：客户端直接调用继续 API（跳过 UI），服务端以聚合状态拒绝
  - [ ] 部分确认阻断：部分项确认、部分项待审阅时，继续请求被服务端拒绝
  - [ ] 驳回后锁定：驳回任一必审项后，继续请求被服务端拒绝
  - [ ] 重新生成验证：驳回后重新生成创建新 run，默认沿用原快照版本
  - [ ] 切换工作流验证：改选插件后创建新 run，历史产出确认状态不受影响

- 前置依赖：`SUO-230-BE-001`, `SUO-230-FE-002`

- 关联路径：
  - `frontend/src/components/story-workspace/review/`
  - `backend/src/routes/story-workspace/`
  - `backend/src/services/story-workspace/`

- 分发去向：`@TaskDesignAgent` + `@TaskDesignAgent`

- 主责 Agent：`TaskDesignAgent`

- 协作 Agent：`TaskDesignAgent`

- 设计决策引用：
  - `DEC-018`：运行级审阅 gate
  - `DEC-010`：版本锁定
  - `DEC-014`：重试规则
  - 设计稿 §3.6.2 / §2.4.3

- 备注：
  - 前端职责：正确传递运行 ID 与审阅版本、展示 gate 状态、禁用/启用操作按钮
  - 后端职责：聚合校验、版本校验、幂等控制、防绕过拒绝
  - 建议编写自动化 E2E 测试覆盖上述场景

---

## 4. 共享任务与依赖说明

### 4.1 基线共享任务（保持不变）

- `SUO-201-SH-002`（命名规范与类型定义共享包）是所有前后端工作的前置基础。
- `SUO-201-BE-001`（数据库 Schema）是后端工作的前置基础。
- `SUO-201-FE-001`（三栏布局）是前端工作的前置基础。
- `SUO-201-SH-001`（审阅工作流 E2E）是 shared 类型 Issue，需在前后端审阅能力完成后推进。

### 4.2 增量共享任务

- `SUO-226-SH-001`（Deck 运行配置 技术传输合同定义）是**所有增量 Deck 运行配置集成的阻塞前置**。在该合同未冻结前，下游实现应使用 mock 或最小适配层，不得假设具体 API 形态。
- `SUO-226-SH-001` 依赖 `SUO-201-SH-002`（基础类型定义）。
- `SUO-226-BE-002`（插件目录）和 `SUO-226-BE-003`（Deck 运行配置预检）依赖 `SUO-226-SH-001` 的合同定义。
- `SUO-226-BE-004`（Run 创建）依赖 `SUO-226-BE-001`（数据模型）和 `SUO-226-BE-003`（预检）。
- `SUO-226-BE-005`（Agent 适配）依赖 `SUO-201-BE-004`（既有 Agent 集成）和 `SUO-226-BE-004`（Run 创建）。
- `SUO-226-FE-001`（Dashboard 工作流上下文条）依赖 `SUO-201-FE-005`（Dashboard 基线）。
- `SUO-226-SH-002`（端到端 E2E）依赖 `SUO-226-BE-005` 和 `SUO-226-FE-001`。
- **SUO-230 增量依赖**：
  - `SUO-230-FE-001`（TopNavBar Dream 导航）依赖 `SUO-201-FE-002`（Sidebar 导航与路由基线）。
  - `SUO-230-FE-002`（Dream 页面与 ReviewGate）依赖 `SUO-226-FE-001`（工作流上下文条）和 `SUO-201-FE-004`（审阅面板基线）。
  - `SUO-230-BE-001`（审阅 gate 服务端聚合）依赖 `SUO-201-BE-003`（审阅状态流转 API）和 `SUO-226-BE-004`（Run 创建 API）。
  - `SUO-230-SH-001`（确认幂等联调）依赖 `SUO-230-BE-001` 和 `SUO-230-FE-002`。
- 若后续发现某个 Issue 的实现范围超出当前设计稿，必须回到 Issue 评论区记录澄清，不得直接下沉到 task 阶段。
- 若某个 Issue 需要新增设计决策，必须标记 `[CLARIFICATION_NEEDED]`，由 `CEOOrchestrator` 判断是否回退到 `DesignArchitect`。

---

## 5. 分发去向说明

### 5.1 TaskDesignAgent

- **基线 Issue**（保持不变）：`SUO-201-BE-001`～`SUO-201-BE-004`
- **增量 Issue（SUO-226）**：
  - `SUO-226-BE-001`：Workflow Binding 与 Run 数据模型
  - `SUO-226-BE-002`：Deck 插件目录查询与选择 API
  - `SUO-226-BE-003`：Deck 运行配置预检与就绪状态 API
  - `SUO-226-BE-004`：Workflow Run 创建与执行上下文 API
  - `SUO-226-BE-005`：Agent 集成适配
- **增量 Issue（SUO-230）**：
  - `SUO-230-BE-001`：审阅 gate 服务端聚合与防绕过验证
- **Shared Issue（主责）**：`SUO-201-SH-002`（命名规范）、`SUO-226-SH-001`（技术传输合同）
- **Shared Issue（协作）**：`SUO-230-SH-001`（确认幂等联调）
- 负责接口、数据处理、Schema、Migration、服务端逻辑、校验链路、Agent 适配、审阅 gate 聚合与防绕过。

### 5.2 TaskDesignAgent

- **基线 Issue**（保持不变）：`SUO-201-FE-001`～`SUO-201-FE-006`
- **SUO-226 增量 Issue**：
  - `SUO-226-FE-001`：Dashboard Deck 工作流上下文条
  - `SUO-226-FE-002`：审阅面板来源溯源
  - `SUO-226-FE-003`：配置/执行/失败状态 UI
- **SUO-230 增量 Issue**：
  - `SUO-230-FE-001`：TopNavBar Dream 导航项与 canonical 路由
  - `SUO-230-FE-002`：Dream 页面与 ReviewGate 组件
- **Shared Issue（主责）**：`SUO-201-SH-001`（审阅 E2E）、`SUO-226-SH-002`（端到端 E2E）、`SUO-230-SH-001`（确认幂等联调）
- **Docs Issue**：`SUO-201-DO-001`（使用文档，增量补充插件选择、配置 owner、失败恢复、Dream 导航与 gate 说明）
- 负责 UI、交互、状态管理、前端接口消费、页面结构、工作流选择器、错误状态、导航与路由。

### 5.3 Shared Issue 处理规则

- `SUO-201-SH-001`（审阅 E2E）：主责 `TaskDesignAgent`，协作 `TaskDesignAgent`。
- `SUO-201-SH-002`（命名规范）：主责 `TaskDesignAgent`，协作 `TaskDesignAgent`。
- `SUO-226-SH-001`（技术传输合同）：主责 `TaskDesignAgent`，协作 `TaskDesignAgent`。
- `SUO-226-SH-002`（端到端 E2E）：主责 `TaskDesignAgent`，协作 `TaskDesignAgent`。
- **`SUO-230-SH-001`（确认幂等联调）：主责 `TaskDesignAgent`，协作 `TaskDesignAgent`。**
- 所有 shared Issue 均有唯一主责 Agent，不允许无主责状态。

---

## 6. 推荐推进顺序

### 6.1 基线推进顺序（保持不变）

```text
Phase 1: 基础准备（可并行）
├── SUO-201-SH-002  命名规范与类型定义共享包
├── SUO-201-BE-001  数据库 Schema 与数据表初始化
└── SUO-201-FE-001  三栏布局骨架与全局样式

Phase 2: 前后端核心开发（可并行，依赖 Phase 1）
├── Backend:
│   ├── SUO-201-BE-002  REST API 实现
│   └── SUO-201-BE-004  Agent 产出数据接收与存储集成
└── Frontend:
    ├── SUO-201-FE-002  Sidebar 导航与路由配置
    ├── SUO-201-FE-003  数据表格组件
    └── SUO-201-FE-004  审阅面板与审阅操作

Phase 3: 后端审阅工作流（依赖 Phase 2 Backend）
└── SUO-201-BE-003  审阅状态流转与批量操作 API

Phase 4: 前端完善（依赖 Phase 2 Frontend）
├── SUO-201-FE-005  工作台首页 Dashboard
└── SUO-201-FE-006  空态/加载/错误/选中态组件

Phase 5: 联调与验证（依赖 Phase 2-4）
└── SUO-201-SH-001  前端-后端联调：审阅工作流 E2E
```

### 6.2 增量推进顺序（新增，依赖基线）

```text
Phase A: 合同与类型准备（阻塞后续所有增量）
└── SUO-226-SH-001  Deck 运行配置 技术传输合同定义
    ├── 依赖：SUO-201-SH-002（基础类型）
    └── 注意：合同冻结前下游使用 mock/适配层

Phase B: 后端数据模型与 API（可并行，依赖 Phase A）
├── SUO-226-BE-001  Workflow Binding 与 Run 数据模型
│   └── 依赖：SUO-201-BE-001（基线 schema）
├── SUO-226-BE-002  Deck 插件目录查询 API
│   └── 依赖：SUO-201-BE-002（基线 REST API）
└── SUO-226-BE-003  Deck 运行配置预检 API
    └── 依赖：SUO-226-BE-002

Phase C: 后端 Run 管理与 Agent 适配（依赖 Phase B）
├── SUO-226-BE-004  Workflow Run 创建与执行上下文 API
│   └── 依赖：SUO-226-BE-001, SUO-226-BE-003
└── SUO-226-BE-005  Agent 集成适配
    └── 依赖：SUO-201-BE-004, SUO-226-BE-004

Phase D: 前端增量组件（可并行，依赖基线前端）
├── SUO-226-FE-001  Dashboard Deck 工作流上下文条
│   └── 依赖：SUO-201-FE-005（Dashboard 基线）
├── SUO-226-FE-002  审阅面板来源溯源
│   └── 依赖：SUO-201-FE-004（审阅面板基线）
└── SUO-226-FE-003  配置/执行/失败状态 UI
    └── 依赖：SUO-201-FE-006（状态组件基线）

Phase E: 端到端联调（依赖 Phase C + Phase D）
└── SUO-226-SH-002  端到端工作流集成 E2E
    ├── 依赖：SUO-226-BE-005, SUO-226-FE-001
    └── 注意：需验证版本锁定、驳回重试、切换工作流规则

Phase F: 文档更新（依赖 Phase E）
└── SUO-201-DO-001  增量更新（补充插件选择、配置 owner、失败恢复）
```

### 6.3 SUO-230 增量推进顺序（新增，依赖基线 + SUO-226）

```text
Phase G: Dream 导航与路由（可并行，依赖基线前端）
└── SUO-230-FE-001  TopNavBar Dream 导航项与 canonical 路由
    └── 依赖：SUO-201-FE-002（Sidebar 导航与路由基线）

Phase H: Dream 页面与审阅 gate（依赖 Phase G + SUO-226 Phase D）
├── SUO-230-FE-002  Dream 页面与 ReviewGate 组件
│   └── 依赖：SUO-226-FE-001（工作流上下文条）, SUO-201-FE-004（审阅面板基线）
└── SUO-230-BE-001  审阅 gate 服务端聚合与防绕过验证
    └── 依赖：SUO-201-BE-003（审阅状态流转 API）, SUO-226-BE-004（Run 创建 API）

Phase I: 幂等与防绕过联调（依赖 Phase H）
└── SUO-230-SH-001  确认幂等与审阅版本校验联调
    ├── 依赖：SUO-230-BE-001, SUO-230-FE-002
    └── 注意：需验证幂等、过期版本拒绝、客户端绕过阻断
```

### 6.4 整体推进建议

```text
基线 Phase 1-3 与增量 Phase A-C 可部分并行：
├── 基线数据库/布局/表格 可与 增量合同定义 并行
├── 基线审阅 API 可与 增量 Binding/Run 模型 并行
└── 但增量 Phase C（Agent 适配）必须等待基线 Agent 集成（SUO-201-BE-004）稳定

关键路径：
SUO-201-SH-002 → SUO-226-SH-001 → SUO-226-BE-001～003 → SUO-226-BE-004 → SUO-226-BE-005 → SUO-226-SH-002

SUO-230 关键路径（可部分与 SUO-226 并行）：
SUO-201-FE-002 → SUO-230-FE-001 → SUO-230-FE-002 → SUO-230-SH-001
SUO-201-BE-003 + SUO-226-BE-004 → SUO-230-BE-001 → SUO-230-SH-001
```

---

## 7. 既有 Task 文档增量更新建议

### 7.1 需增量更新的 Task 文档

| Task 文档 | 更新原因 | 更新内容 | 负责 Agent |
|---|---|---|---|
| `task_201_backend_story-workspace-schema.md` | 需追加 workflow binding/run 表 | 追加 `story_workspace_workflow_bindings`、`story_workspace_workflow_runs` 表定义；stories 表追加 `workflow_run_id` | `@TaskDesignAgent` |
| `task_202_backend_story-workspace-rest-api.md` | 需新增 Deck 运行配置/run 端点 | 新增插件目录、Deck 运行配置预检、run 创建/查询/取消/重试端点 | `@TaskDesignAgent` |
| `task_205_backend_story-workspace-shared-types.md` | 需扩展类型定义 | 追加 binding、run、manifest、错误码类型 | `@TaskDesignAgent` |
| `task_202e_frontend_dashboard.md` | 需新增工作流上下文条 | 追加 Dashboard Deck 工作流上下文条组件 | `@TaskDesignAgent` |
| `task_202d_frontend_review-panel.md` | 需追加来源溯源 | 追加审阅面板来源信息展示 | `@TaskDesignAgent` |
| `task_202g_frontend_e2e-integration.md` | 需扩展 E2E 场景 | 追加 Deck→Agent→审阅端到端场景 | `@TaskDesignAgent` |
| `task_202h_frontend_user-documentation.md` | 需补充新功能说明 | 追加插件选择、配置 owner、失败恢复 | `@TaskDesignAgent` |

### 7.2 需增量更新的 Task 文档（SUO-230）

| Task 文档 | 更新原因 | 更新内容 | 负责 Agent |
|---|---|---|---|
| `task_202b_frontend_sidebar-navigation.md` | 需追加 Dream 导航与 canonical 路由 | 追加 `StoryWorkspaceDreamNavItem` 组件、路由重定向配置 | `@TaskDesignAgent` |
| `task_202e_frontend_dashboard.md` | 需追加 Dream 页面与 ReviewGate | 追加 `StoryWorkspaceDreamPage` 页面、`StoryWorkspaceReviewGate` 组件 | `@TaskDesignAgent` |
| `task_202d_frontend_review-panel.md` | 需追加 gate 状态与操作 | 追加 ReviewGate 与 Review Panel 的联动、确认版本校验 | `@TaskDesignAgent` |
| `task_202_backend_story-workspace-rest-api.md` | 需追加审阅 gate 聚合端点 | 新增审阅状态聚合查询、确认版本校验、继续/结束幂等端点 | `@TaskDesignAgent` |

### 7.3 无需变更的 Task 文档

| Task 文档 | 原因 |
|---|---|
| `task_202_frontend_story-workspace-overview.md` | 概览文档，不受增量影响 |
| `task_202a_frontend_three-column-layout.md` | 三栏骨架不变，仅可能挂载新组件 |
| `task_202b_frontend_sidebar-navigation.md` | Sidebar 导航不变 |
| `task_202c_frontend_data-table-components.md` | 表格核心不变，仅增加来源字段展示 |
| `task_202f_frontend_state-components.md` | 基础状态组件不变，新增状态由 SUO-226-FE-003 处理 |

### 7.4 需新建的 Task 文档（SUO-226）

| 建议 Task ID | 内容 | 负责 Agent |
|---|---|---|
| `task_226_backend_workflow-binding-run-schema.md` | Workflow Binding 与 Run 数据模型 | `@TaskDesignAgent` |
| `task_226_backend_deck-plugin-directory-api.md` | Deck 插件目录查询 API | `@TaskDesignAgent` |
| `task_226_backend_deck-runtime-preflight-api.md` | Deck 运行配置预检 API | `@TaskDesignAgent` |
| `task_226_backend_workflow-run-api.md` | Workflow Run 创建与管理 API | `@TaskDesignAgent` |
| `task_226_backend_agent-deck-runtime-adapter.md` | Agent 集成适配 | `@TaskDesignAgent` |
| `task_226_frontend_workflow-context-bar.md` | Dashboard 工作流上下文条 | `@TaskDesignAgent` |
| `task_226_frontend_review-provenance.md` | 审阅面板来源溯源 | `@TaskDesignAgent` |
| `task_226_frontend_workflow-error-states.md` | 配置/执行/失败状态 UI | `@TaskDesignAgent` |
| `task_226_shared_deck-runtime-contract.md` | Deck 运行配置 技术传输合同 | `@TaskDesignAgent` + `@TaskDesignAgent` |
| `task_226_shared_end-to-end-e2e.md` | 端到端工作流 E2E | `@TaskDesignAgent` + `@TaskDesignAgent` |

### 7.5 需新建的 Task 文档（SUO-230）

| 建议 Task ID | 内容 | 负责 Agent |
|---|---|---|
| `task_230_frontend_dream-nav-item.md` | TopNavBar Dream 导航项与 canonical 路由 | `@TaskDesignAgent` |
| `task_230_frontend_dream-page-review-gate.md` | Dream 页面与 ReviewGate 组件 | `@TaskDesignAgent` |
| `task_230_backend_review-gate-aggregation.md` | 审阅 gate 服务端聚合与防绕过验证 | `@TaskDesignAgent` |
| `task_230_shared_idempotency-e2e.md` | 确认幂等与审阅版本校验联调 | `@TaskDesignAgent` + `@TaskDesignAgent` |

---

## 8. design → issue → task → stage 影响矩阵

### 8.1 影响矩阵

| 设计增量 | Issue 影响 | Task 影响 | Stage 影响 | Exec 影响 |
|---|---|---|---|---|
| DEC-009 职责独立 | 新增职责边界说明 | 各 task 追加职责边界约束 | 新增准入检查：职责不重叠 | 代码审查检查点 |
| DEC-010 版本锁定 | 新增 SUO-226-BE-001 | 新增 binding/run schema task | 新增版本锁定验证 wave | 数据库 migration |
| DEC-011 预检失败禁止启动 | 新增 SUO-226-BE-003 | 新增 Deck 运行配置预检 API task | 新增预检失败场景测试 | 预检 API 实现 |
| DEC-012 数据最小化 | 各 Issue 追加约束 | 各 task 追加安全约束 | 安全审查准入 | 敏感数据过滤 |
| DEC-013 可审计 binding | 新增 SUO-226-BE-001 | 新增 binding 模型 task | 审计追踪验证 | binding 表实现 |
| DEC-014 重试规则 | 新增 SUO-226-BE-004 | 新增 retry API task | 重试场景 E2E | retry 逻辑实现 |
| Deck 运行配置集成 Delta | 新增 10 条增量 Issue | 新增 10+ task | 新增 2-3 waves | 新增实现范围 |
| **DEC-017 Dream 导航** | **新增 SUO-230-FE-001** | **新增 Dream 导航 task** | **新增导航验收 wave** | **TopNavBar 组件 + 路由** |
| **DEC-018 审阅 Gate** | **新增 SUO-230-FE-002 / SUO-230-BE-001 / SUO-230-SH-001** | **新增 gate UI / 服务端聚合 / E2E task** | **新增 gate 验收 wave** | **ReviewGate 组件 + 服务端校验** |

### 8.2 旧 Stage 不得直接作为本次设计变化的 Execute 准入

- `stage_story-workspace.md`（现有 Stage）基于 SUO-199 设计稿制定，**不含 Deck 运行配置 依赖和准入门**。
- 本次设计增量（SUO-214/SUO-215）引入的 Deck 运行配置/Agent 端到端集成**必须在新的增量 Stage 中验证**。
- **SUO-230 增量**引入的 Dream 导航与审阅 Gate**必须在另一独立增量 Stage 中验证**。
- **建议**：
  - 保留现有 `stage_story-workspace.md` 作为基线 Stage
  - 新建 `stage_story-workspace-deck-runtime-integration.md` 作为 Deck 运行配置 增量 Stage
  - 新建 `stage_story-workspace-dream-gate.md` 作为 Dream 导航与 Gate 增量 Stage
  - Deck 运行配置 增量 Stage 置于配置/类型合同完成之后（SUO-226-SH-001 冻结后）
  - Dream/Gate 增量 Stage 置于 SUO-230-BE-001 和 SUO-230-FE-002 完成后
  - **旧 Stage 不能作为 SUO-230 增量的 execute 准入；SUO-230 增量 Stage 必须独立验证：顶部 Dream → 产出 → 渲染 → 确认/驳回 → 放行/阻断**
  - **不得直接以旧 Stage 作为本次设计变化的 execute 准入**

---

## 9. 阻塞与澄清记录

### 9.1 [CLARIFICATION_NEEDED] Deck 运行配置内部组件边界（已废弃"Desk"口径）

- **背景**：按 SUO-235 裁决，Deck 是唯一业务模块；原"Desk"概念已废弃，其内容（运行配置、不可变快照、secret-ref、权限）统一归入 Deck。
- **歧义点**：Deck 内部 manifest、运行配置、secret provider 的组件边界尚未冻结
- **可能解释 A**：Deck 统一存储，内部逻辑分层（manifest / runtime config / secret）
- **可能解释 B**：Deck 保存 manifest；运行配置和密钥引用由内部子组件管理
- **默认采用解释**：对外保持单一 Deck API/owner，内部可按安全边界拆组件（见 `deck-integration-delta.md` §4.2）
- **需要确认方**：`@CEOOrchestrator` 路由产品 owner
- **是否阻塞 task 阶段**：**否**（可采用默认假设继续，但合同冻结前使用 mock/适配层）
- **风险**：内部拓扑泄漏为重复业务域
- **Clarification owner / action**：`@CEOOrchestrator` 确认 Deck 内部组件边界，并在下游增量 Issue/Task 中引用

### 9.2 [CLARIFICATION_NEEDED] Deck manifest 与 Deck 运行配置子组件的物理存储/API 分工

- **歧义点**：Deck 插件 manifest 和 Deck 运行配置子组件的具体物理存储位置、API owner、版本管理方式尚未确定
- **可能解释 A**：Deck 保存 manifest；运行配置子组件保存配置和密钥引用
- **可能解释 B**：统一存储，逻辑分层
- **默认采用解释**：Deck 保存 manifest；运行配置子组件保存配置和密钥引用
- **需要确认方**：`@CEOOrchestrator` 路由 Deck owner
- **是否阻塞 task 阶段**：**否**（接口草案按默认假设定义，标记 `[DRAFT]`）
- **风险**：重复配置、版本不一致
- **Clarification owner / action**：`@CEOOrchestrator` 提供版本和读取合同

### 9.3 [CLARIFICATION_NEEDED] Deck 运行配置停用时已运行任务的策略

- **歧义点**：Deck runtime profile 被停用后，已开始 run 的处理策略
- **可能解释 A**：已解析快照允许完成；禁止新 run
- **可能解释 B**：强制终止所有相关 run
- **默认采用解释**：已解析快照允许完成；禁止新 run
- **需要确认方**：安全 owner
- **是否阻塞 task 阶段**：否
- **风险**：紧急撤销可能不够及时
- **Clarification owner / action**：安全 owner 确认是否需要强制终止能力

### 9.4 [CLARIFICATION_NEEDED] 插件选择的主入口

- **歧义点**：story-workspace Dashboard 和 Chat 是否都可作为插件选择入口
- **可能解释 A**：story-workspace 提供选择器；Chat 可复用 binding 作为输入入口
- **可能解释 B**：仅 story-workspace 可选择
- **默认采用解释**：story-workspace 提供选择器；Chat 可复用 binding 作为输入入口
- **需要确认方**：产品 owner
- **是否阻塞 task 阶段**：否
- **风险**：UI 重复或旧路径绕过选择
- **Clarification owner / action**：产品 owner 确认主入口；下游必须共享同一 binding 合同

### 9.5 [BLOCKED] SUO-226-SH-001（Deck 运行配置 技术传输合同）在 API 合同冻结前无法完全实现

- **阻塞原因**：Deck 运行配置 API 合同尚未由平台 owner 确认
- **影响范围**：SUO-226-BE-002（插件目录）、SUO-226-BE-003（Deck 运行配置预检）、SUO-226-BE-005（Agent 适配）
- **当前责任 Agent**：IssueDispatcher（已标记）
- **需要唤醒的 Agent**：`@CEOOrchestrator` 路由产品/平台 owner 确认 Deck 运行配置合同
- **建议处理方式**：
  1. 按设计稿默认假设定义接口草案（标记 `[DRAFT]`）
  2. 使用 mock/最小适配层实现，不阻塞 schema 和 run 模型开发
  3. 合同确认后更新接口为正式版本
- **是否需要回退到 design**：否（默认假设可继续推进）
- **历史口径说明**：原 Issue 使用 "Deck/Desk" 双术语；按 SUO-235 已统一为 Deck，本阻塞项保留以追踪 Deck 内部运行配置子组件的合同冻结进度

---

## 10. Issue-First 协作说明

- Issue 是最小调度单元。
- 同一 Issue 任一时刻只允许一个主责 Agent。
- shared Issue 必须有主责 Agent 与协作 Agent。
- 必须通过 Issue 评论区补充上下文、阻塞、回退和评审意见。
- 必须通过 `@mention` 唤醒目标 Agent。
- 不假设 Agent 之间存在隐式共享内存。
- 不允许绕过 Issue 直接下发 task。
- 所有 Agent 间协作以 Issue 线程、Issue 文档和关联产物为准。
- **增量 Issue 必须明确标注对基线的影响：新增 / 变更 / 无影响。**
- **基线 Issue（SUO-201-xxx）不得反向改写其 exec 结论。**
