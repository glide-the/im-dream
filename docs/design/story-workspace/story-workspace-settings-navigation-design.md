# Story Workspace 设置中心交互设计稿

## 目标

将订阅和设置统一纳入 Story Workspace。一级导航由 `StoryWorkspaceSidebar` 承载，设置内容始终在一级侧边栏右方显示；设置页面内部再提供分类导航，不再把工作区设置跳转到应用根路径的独立页面。

## 信息架构

```text
StoryWorkspaceSidebar
├── 写作
├── 时间线
├── 分析
├── Decks
├── Dream
├── Chat
└── footer
    ├── 主题切换
    ├── 订阅
    └── 设置

设置右侧内容区的二级导航：常规、资源连接、插件、AI 模型、关于。
```

路由映射：

| 页面 | 路由 |
| --- | --- |
| 订阅 | `/story-workspace/subscription` |
| 设置首页/常规 | `/story-workspace/settings` |
| 资源连接 | `/story-workspace/settings/resources` |
| 插件 | `/story-workspace/settings/plugins` |
| AI 模型 | `/story-workspace/settings/model` |
| 关于 | `/story-workspace/settings/about` |

## 布局

桌面端采用“一级侧边栏 + 设置二级侧边栏 + 内容区”三层结构。一级侧边栏宽度由工作区折叠状态控制；设置二级侧边栏固定在内容区左侧，包含设置标题、搜索框、分组标题和分类导航；右侧内容区负责滚动。

移动端将设置二级导航变为横向可滚动导航，内容区恢复单列布局，避免设置项被固定侧栏遮挡。

## 交互规则

1. LeftSidebar 原有的写作、时间线、分析、Decks、Dream、Chat 导航在 Story Workspace 中保持原顺序和行为。
2. 点击“订阅”时导航到 `/story-workspace/subscription`，左侧工作区布局保持挂载，右侧渲染独立订阅 `section`；订阅紧邻 footer 设置入口上方。
3. 点击 footer“设置”时导航到 `/story-workspace/settings`，默认选中“常规”。
4. 点击设置分类只更新 Story Workspace 路由，不刷新页面；刷新、直接访问、前进和后退均可恢复当前分类。
5. 搜索框即时过滤设置分类标题；无结果时显示“没有匹配的设置”。
6. 当前一级、二级导航均使用 `aria-current="page"` 和视觉高亮表达选中状态。
7. 设置内容使用 `SettingsSection` 语义组件，每个分区提供唯一 `id`、可见标题和 `aria-labelledby` 关联。
8. 资源连接详情仍由现有连接器组件负责保存和返回，迁移只改变其挂载位置。

## 状态与可访问性

- 导航按钮、搜索框、语言按钮和开关均支持键盘焦点。
- 语言和能量条设置保留原有状态与持久化行为。
- 切换设置分类不会自动应用后端保存的主题；主题只在用户主动操作主题控件或模型设置中的主题选项时改变。
- 主题颜色使用现有语义 token，兼容明暗主题。
- 内容区设置合理的最大阅读宽度，长内容在右侧独立滚动。
- `StoryWorkspaceLayout` 负责页面主结构，设置页面不嵌套额外的 `main` 元素。

## 验收标准

- 订阅在设置上方显示。
- 订阅和设置均在 `StoryWorkspaceSidebar` 右方渲染。
- 设置分类导航与 URL 同步。
- 旧工作区设置入口不再把 URL 改回 `/`。
- 设置分区具有语义化 `section` 和标题。
- 路由回归测试、布局回归测试通过。
