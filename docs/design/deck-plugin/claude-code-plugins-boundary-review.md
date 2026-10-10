<!-- [Input] 用户确认的插件产品边界、当前前后端代码、历史 Deck Plugin 与 Marketplace 文档。 -->
<!-- [Output] 问题处理结论、代码依据、范围审查和文档验证记录。 -->
<!-- [Pos] Claude Code Plugins 设计修订与设置分类清理记录；不是远程 Marketplace 发布平台设计。 -->
<!-- [Sync] 2026-10-10: 确认选择型产品边界，排除安装管理、独立运行时插件和未设计的 Marketplace 发布平台。 -->

# Claude Code Plugins 边界审查

## 任务目的

本次任务把 Claude Code Plugins 收敛为一个清楚的用户功能：用户创建或编辑思维模式时，从 Admin 已发布的清单中选择插件。设计不扩展插件发布平台，不把 Deck 工作流、运行阶段或测试过程变成新的插件产品。

交付包括[产品需求](../../prd/deck/claude-code-plugins.md)、[现行交互设计](./claude-code-plugins-interaction.md)和设置页分类清理。工作流区域的具体页面改动由[独立工作流设计](./deck-workflow-plugin-interaction.md)负责。

## 问题处理结论

| 问题 | 代码与文档依据 | 处理结论 |
| --- | --- | --- |
| Deck 工作流插件的范围不清 | `deck_plugins` 路由和旧 `PluginAdminPage` 管理工作流发布版本及其运行依赖；Notion 历史与现行 Dream/Story Workspace 表明它组织 Dream Agent、创作 Skill、Project/Episode 内容和同步恢复。 | 按[独立设计](./deck-workflow-plugin-interaction.md)保留为 Dream 工作台的版本化业务工作流，不纳入 Claude Code Plugins 设计，也不在同一页面作为插件分类。 |
| “ClaudeAgent 运行时插件”形成第二分类 | 原 `PluginAdminPage` 把执行依赖投影为单独标签；相关动作仍通过所属工作流执行，没有独立管理对象。 | 已删除分类、联合类型、前端依赖投影及详情分支。工作流目录与 Claude Code Plugins 保持独立。 |
| Claude Code Plugins 的目的被安装管理覆盖 | `DeckEditorModal` 和 `DeckClaudePluginSelector` 已提供思维模式插件选择；`ClaudePluginAdminPage` 另行提供安装、Marketplace 和卸载。 | 现行用户设计只覆盖创建与编辑时的插件选择。安装、卸载和发布不进入本稿。 |
| 同一设置页出现两套插件管理 | `StoryWorkspaceSettingsPage` 同时挂载工作流目录与 Claude Code Plugins。 | 保留明确命名的两个区域；工作流说明创作范围，Claude Code Plugins 说明能力扩展和 Deck 选择入口。既有授权维护动作沿用，不新增发布流程。 |
| 远程 Marketplace 被误认为已有发布平台设计 | `claude-plugin-remote-marketplace.md`描述远程来源同步、版本记录、安装和文件检查；`ClaudePluginAdminPage`提供目录安装入口，但没有完整的注册、提交、审核、发布和运营产品设计。 | 明确远程 Marketplace 发布平台尚未设计。现有文档只作为技术合同与历史证据，不能代表发布平台已经完成设计。 |
| Voice 概念残留 | `DeckEditorModal` 和 voices 路由仍使用 Voice 数据，不能认定该代码概念已经全局删除；它与 Claude Code Plugins 选择没有用户关系。 | 从现行插件 PRD、功能描述、页面和业务图中移除 Voice。历史原文和现有协议字段保留，不做全局替换。 |
| Paperclip 和 Harness 进入业务设计 | 历史工作流集成稿使用 Paperclip 作架构比较；远程 Marketplace 技术稿提到测试 Harness。这些内容都不帮助用户选择插件。 | 从现行产品与交互设计移除。历史研究、实现说明和验证记录保留在原文件，不作为用户需求。 |
| “物化”“制品”“锁”“同构”等词语造成理解偏移 | 历史稿以运行和文件术语描述用户状态，现有选择页面也展示 digest 等技术信息。 | 用户设计改为“Admin 已发布”“当前可选”“尚未保存”“已保存”“当前不可选”。已有代码标识符和协议字段不改名。 |

## 关键代码依据

- [思维模式创建入口](../../../frontend/app/_dream/components/DeckManager.tsx)：创建成功后打开维护弹窗。
- [思维模式维护弹窗](../../../frontend/app/_dream/components/DeckEditorModal.tsx)：现有“Claude 插件”栏目及 Dream Agent 类型入口。
- [插件选择组件](../../../frontend/app/_dream/components/DeckClaudePluginSelector.tsx)：读取可用安装记录、读取当前选择并保存 refs。
- [设置页挂载](../../../frontend/app/_dream/views/story-workspace/StoryWorkspaceSettingsPage.tsx)：同时挂载两套插件管理区域。
- [工作流目录](../../../frontend/app/_dream/components/plugin-admin/PluginAdminPage.tsx)：展示 Dream Story Workflow 用途、工作流清单与详情；多余分类及 Paperclip 说明已删除。
- [Claude 插件安装管理](../../../frontend/app/_dream/components/claude-plugin-admin/ClaudePluginAdminPage.tsx)：安装、Marketplace、最近操作和卸载入口。
- [前端插件接口](../../../frontend/app/_dream/api/claudePluginAdminApi.ts)：安装记录、Marketplace、操作记录及 Deck refs 共用同一客户端文件。
- [Claude 插件公开路由](../../../backend/routers/claude_plugins.py)和[工作流插件公开路由](../../../backend/routers/deck_plugins.py)：两组程序接口当前同时存在，但接口存在不等于应当形成两个用户插件分类。

## “ClaudeAgent 运行时插件”是否需要独立设计

结论是不需要。

当前证据只表明它是旧工作流界面对 Claude Code 插件依赖的展示名称。它没有独立的用户目的、独立选择对象或独立保存入口。另建产品稿会让用户多理解一个没有必要的分类，并继续混淆工作流与 Claude Code Plugins。

已删除该分类在前端的类型、目录投影、选择状态、列表分支、详情分支和专用样式。后端仍通过既有工作流路径处理执行依赖、检查和日志，现行 Admin 协议字段保留。

## 远程 Marketplace 的处理

本次不编写远程 Marketplace 发布平台设计，也不补充占位流程。现行文档只作如下分工：

- `claude-plugin-marketplace-add.md`保留历史安装入口与交互记录；
- `claude-plugin-remote-marketplace.md`保留远程来源同步、安装和文件检查的技术合同；
- 未来的注册、提交、审核、发布和运营平台需要单独 PRD 与交互设计。

因此，现有安装代码和远程来源数据不能被描述为“Marketplace 发布平台已经设计完成”。

## 设计目标审查

| 审查项 | 结论 |
| --- | --- |
| 是否重申真实目的 | 是。用户任务是为思维模式选择 Admin 已发布的 Claude Code Plugins。 |
| 是否只写必要功能 | 是。功能限于查看、选择、保存和失败恢复。 |
| 是否区分工作流与插件 | 是。Deck 工作流插件属于 Dream 工作台，Claude Code Plugins 属于思维模式配置。 |
| 是否保留多余分类 | 否。“ClaudeAgent 运行时插件”不作为产品分类。 |
| 是否误写 Marketplace 已设计 | 否。远程 Marketplace 发布平台明确标记为未设计。 |
| 是否把程序过程写成业务需求 | 否。Paperclip、Harness、文件准备和命令执行只留在历史或实现资料中。 |
| 是否引入额外页面 | 否。复用思维模式维护弹窗，不增加安装、发布或运行状态页面。 |
| 是否增加额外确认 | 否。普通选择和保存不增加确认弹窗。 |
| 是否区分保存与实际使用 | 是。保存插件选择不等于对话已经加载插件。 |
| 是否掩盖实现差距 | 否。设置分类和首页文案已修正；完整 Admin 发布清单合同与 Deck 选择的差距继续明确列出。 |

结论：Deck 工作流和 Claude Code Plugins 的目的分别定义，设置页的独立运行时分类已删除。远程 Marketplace 发布平台和完整 Admin 发布管理仍在范围外。设置页验证结果单独记录，不能代替工作流生成内容的业务验收。

## 实施前需要解决的差距

1. 当前选择组件以 `ready` 安装记录作为可选清单；需要确认它是否与 Admin “已发布且允许选择”的产品条件完全一致。
2. `DeckClaudePluginSelector`当前显示 package spec 和 digest，缺少插件用途说明。
3. 栏目名称仍为“Claude 插件”，应统一为“Claude Code Plugins”。
4. 保存成功后调用 `onSaved` 刷新，刷新失败可能被显示成保存失败，需要分开反馈。
5. 设置页的多余运行时分类已删除，工作流用途及 Claude Code Plugins 名称已落入代码。完整 Admin 发布管理仍需独立设计。
6. 已保存插件后来不再可选时，当前列表可能无法展示原选择；实施前需要明确只读提示所需的返回字段，不得自动删除或替换。

## 文档验证记录

本节记录 Markdown 清单、引用和 Mermaid 语法验证。验证不访问业务服务，不安装插件，不修改数据库，也不构成功能验收。

2026-10-10 完成以下文档检查：

| 检查 | 命令与范围 | 退出码与关键输出 |
| --- | --- | --- |
| Markdown 围栏与本地链接 | Python 脚本读取本轮 8 份受影响文档，检查代码围栏、相对文件链接和行尾空白 | `0`；`documents=8`、`local_file_links=49`、`errors=[]`。 |
| 目录清单与必需结构 | 同一脚本检查两份新增文档已进入对应 `.folder.md`，PRD 含四幅页面骨架，正式稿含 Double Diamond 判断和三类业务图 | `0`；`mermaid_blocks=3`、`errors=[]`。 |
| Mermaid 语法与渲染 | 使用本机 Chrome 加载仓库已安装 Mermaid，逐图执行 `parse` 与 `render` | `0`；Deck 工作流正式稿 `diagrams=3`、`failures=0`。 |
| 设计用语 | Python 脚本检查两份 Deck 工作流现行稿未使用规则禁止的含糊标签 | `0`；`errors=[]`。 |
| 差异检查 | `git diff --check` 检查本轮相关已跟踪文档；Python 脚本单独检查两份新增文档行尾空白 | `0`；`trailing_whitespace=[]`。 |

Mermaid 检查只解析正文，没有生成或保存图片。上述检查没有启动业务服务、执行插件安装、调用模型或写入数据库。
