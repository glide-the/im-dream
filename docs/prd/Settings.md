# Settings PRD

> Settings 页面的产品与视觉设计规范。本文引用 [Color System](<./Color System.md>)，仅更新 PRD，不修改产品代码。
> **[Sync] 2026-05-27**: 新增 4.3.5 用户 API 配置区域（`ANTHROPIC_AUTH_TOKEN`、`ANTHROPIC_BASE_URL`、`ANTHROPIC_MODEL` 等按用户存储并注入 Claude SDK 子进程）；关联设计文档 [用户 SDK Env 注入方案设计](../design/claude-agent/user-env-injection-design.md)。

## 1. 文档范围

Settings 是应用的全局配置页面，作为顶部导航栏（`TopNavBar`）和移动端底部导航栏中"设置"入口的对应视图。本次更新新增 **AI 模型配置区域**，将原本位于 Chat 页面侧边栏的模型配置迁移至此，并新增 **用户 API 配置区域**，支持每位用户存储自己的 Anthropic API 密钥及模型端点配置。

该页面包含：
- 语言偏好设置
- 界面展示选项（如能量条开关）
- **AI 模型配置**（主题、模型选择、系统提示词、工作区模式）
- **用户 API 配置**（Anthropic API 密钥、自定义端点、默认模型等 env 变量）
- 关于 Ink & Memory（`AboutView`）

## 2. 设计目标

- 将所有应用级全局配置集中于一处，避免配置入口散落在各页面侧边栏。
- 与 Ink & Memory 的"暖纸张、安静工具台"气质保持一致，不使用高饱和填充块或营销式排版。
- 为 Light/Dark 模式共用同一语义 token。
- 设置项清晰分区，每个区域有标题说明，便于用户快速定位。

## 3. 页面布局

```
SettingsView（position: fixed，overflow: auto）
└── ContentWrapper（maxWidth: 800，width: 100%）
    ├── GeneralSection
    │   ├── 标题：Settings / 设置
    │   └── LanguageGroup（语言选择按钮组）
    ├── DisplaySection
    │   └── EnergyBarToggle
    ├── ModelConfigSection（AI 模型配置）
    │   ├── 标题：AI 模型配置
    │   ├── ThemeGroup（Light / System / Dark 切换）
    │   ├── ModelSelect（模型下拉选择）
    │   ├── SystemPromptTextarea（系统提示词，含保存/重置）
    │   ├── WorkspaceModeToggle
    │   └── UserApiConfigGroup（用户 API 配置）
    │       ├── ANTHROPIC_AUTH_TOKEN 输入框（password 类型）
    │       ├── ANTHROPIC_BASE_URL 输入框
    │       ├── ANTHROPIC_MODEL 输入框（可选）
    │       └── 保存按钮
    └── AboutSection
        └── AboutView
```

| 区域 | 规范 |
|---|---|
| 页面容器 | `color.bg.app`，`overflow: auto`，顶部留 `viewTopOffset` |
| 内容最大宽度 | 800px，居中，桌面端横向内边距 40px，移动端 16px |
| 区域间距 | `marginBottom: 48px` |
| 分组容器 | `color.bg.surface`，`border: 1px solid color.border.paper`，`borderRadius: 8px`，`padding: 24px` |

## 4. 组件层级

### 4.1 GeneralSection（通用设置）

- 标题使用 `color.text.primary`，Georgia 字体，24px，fontWeight 600。
- 语言切换按钮组：激活项使用 `color.action.primary`（炭黑底 + 白字），未激活使用 `color.border.paper` 边框。
- 不使用高饱和背景或渐变表示选中状态。

### 4.2 DisplaySection（展示选项）

- 每项使用 flex 横向排列：左侧标题+描述，右侧切换开关。
- 开关激活时使用 `color.action.primary`（炭黑底），未激活使用 `color.border.paper`。
- 标题 14px，描述 12px `color.text.secondary`。

### 4.3 ModelConfigSection（AI 模型配置）

此区域由 `ModelConfigSection` 组件实现，包含以下子区域：

#### 4.3.1 外观主题 / Theme

- 三个按钮（Light / System / Dark），横向排列，带图标和文字标签。
- 激活项：`border: color.border.focus`，`background: color.bg.paper`，`color: color.text.primary`，fontWeight 600。
- 未激活项：`background: transparent`，`color: color.text.muted`。
- 按钮圆角 `999px`，过渡 `0.2s ease`。
- 选中后立即应用主题，同步写入 `localStorage` 和 `/api/system-config`。

#### 4.3.2 AI 模型 / Model

- 下拉选择框 `<select>`，样式使用 `color.bg.paper` 背景，`color.border.paper` 边框，`borderRadius: 12px`，`padding: 0.75rem 0.85rem`。
- 可选项：Auto、Claude Sonnet、GPT-4.1。
- 选中后立即同步到 `/api/system-config`。

#### 4.3.3 系统提示词 / System Prompt

- `<textarea>`，`rows: 5`，样式与 Model select 一致，`resize: vertical`。
- 底部操作行：左侧"恢复默认"（text button，`color.text.muted`），右侧"保存"（`color.action.link` 填充圆角按钮，白色文字）。
- "保存"按钮在 `dirty` 为 `false` 或 `saving` 时 `opacity: 0.55`，`cursor: not-allowed`。
- 保存中显示"保存中…"，完成后恢复。

#### 4.3.4 工作区模式 / Workspace Mode

- flex 横向排列：左侧标题 + 描述说明，右侧切换开关（`flexShrink: 0`）。
- 开关激活：`background: color.action.link`，未激活：`background: color.disabled.bg`。
- 过渡 `0.2s ease`。
- 立即同步到 `/api/system-config`。

#### 4.3.5 用户 API 配置 / User API Config

> 关联设计文档：[用户 SDK Env 注入方案设计](../design/claude-agent/user-env-injection-design.md)

此子区域允许每位用户配置自己的 Anthropic API 密钥和模型端点，存储到 `system_config.env_vars` 中，并在用户发起 Claude Agent 会话时优先注入到 Claude SDK 子进程环境。

**UI 布局**：

- 区域标题：`API 配置 / API Config`，与上方 Workspace Mode 用分割线隔开，`marginTop: 24px`，`paddingTop: 24px`，`borderTop: 1px solid color.border.paper`。
- 每个配置项独占一行，左侧 label + 说明，右侧输入框。

**配置项列表**：

| 字段标签 | env key | 输入类型 | 说明 |
|---------|---------|---------|------|
| API 密钥 | `ANTHROPIC_AUTH_TOKEN` | `<input type="password">` | Anthropic API 密钥，留空则使用服务器默认 |
| API 端点 | `ANTHROPIC_BASE_URL` | `<input type="text">` | 自定义 API 端点（代理/自建），留空则使用 Anthropic 默认 |
| 默认模型 | `ANTHROPIC_MODEL` | `<input type="text">` | 模型名称，留空则由服务器 `.env` 或 Claude Code 默认值决定 |

**视觉规范**：

- 输入框样式与 §4.3.2 Model select 一致：`color.bg.paper` 背景，`color.border.paper` 边框，`borderRadius: 12px`，`padding: 0.75rem 0.85rem`，`width: 100%`。
- `ANTHROPIC_AUTH_TOKEN` 输入框右侧提供"显示/隐藏"切换图标按钮（`color.text.muted`），不改变 type 以外的样式。
- 已保存的 `ANTHROPIC_AUTH_TOKEN` 值在页面加载时显示为掩码（如 `sk-ant-***`），不还原明文。其余字段显示实际值。
- 底部操作行与 §4.3.3 一致：左侧"恢复默认"（清空三个字段），右侧"保存"圆角按钮（`color.action.link`）。
- "保存"按钮仅在 `dirty=true` 且非 `saving` 状态时可用，否则 `opacity: 0.55`，`cursor: not-allowed`。

**行为规范**：

- 用户点击"保存"后，将三个字段的当前值作为 `env_vars` 字典提交到 `PUT /api/system-config`。非空字段写入对应 key；**留空字段从 `env_vars` 中删除该 key**（而非写入空字符串），以便回退到服务器默认配置。
- 用户点击"恢复默认"后，清空三个输入框并立即保存（`env_vars` 中移除这三个 key）。
- 保存成功后 `dirty` 置 `false`，按钮恢复禁用态。

### 4.4 AboutSection

- 复用 `AboutView` 组件，不做额外样式包裹。

## 5. 色彩与视觉规范

| 元素 | Token | 说明 |
|---|---|---|
| 页面背景 | `color.bg.app` | 暖纸张背景。 |
| 分组容器 | `color.bg.surface` | 半透明白，轻量分组。 |
| 边框 | `color.border.paper` | 棕灰纸张感。 |
| 标题 | `color.text.primary` | 区域标题、配置项标题。 |
| 说明文字 | `color.text.secondary` | 配置项描述、辅助说明。 |
| 弱提示 | `color.text.muted` | placeholder、"恢复默认"按钮文字。 |
| 激活操作 | `color.action.primary` | 语言/主题选中状态。 |
| 链接/保存 | `color.action.link` | 保存按钮、Workspace Mode 开关激活色。 |
| 开关禁用 | `color.disabled.bg` | Workspace Mode 未激活背景。 |
| 焦点边框 | `color.border.focus` | Theme 选中按钮边框。 |

## 6. 状态设计

| 状态 | 设计要求 |
|---|---|
| 加载态 | 配置加载中显示"Loading config…"弱文本，不显示骨架屏 |
| 保存中 | 保存按钮文案变为"保存中…"，opacity 降低，cursor 为 not-allowed |
| 已保存 | dirty 置 false，按钮恢复为禁用态（内容未变时无需再次保存） |
| 悬停态 | 主题/语言按钮轻微改变颜色，0.2s ease |
| 焦点态 | 输入框 focus 使用 `color.border.focus` 或系统默认 outline |

## 7. 暗色模式适配

- 使用同一套语义 token，背景切换为 `color.bg.app` Dark 值（`#1f1b16`）。
- 分组容器使用 `color.bg.surface` Dark 值（`rgba(42,37,30,0.82)`）。
- 输入框、下拉框使用 `color.bg.paper` Dark 值（`#2a251e`）。
- 文字使用对应 Dark token，保持可读性。
- 不使用霓虹橙或纯黑背景。

## 8. API 交互

- 页面挂载时调用 `GET /api/system-config` 加载当前配置。
- Theme、Model、Workspace Mode 变更后立即调用 `PUT /api/system-config` 保存。
- System Prompt 在用户点击"保存"后调用 `PUT /api/system-config`。
- **用户 API 配置**在用户点击"保存"后调用 `PUT /api/system-config`，将三个 env key 作为 `env_vars` 字典传入。留空的字段通过传入空字符串或在前端过滤后不包含该 key 来实现删除（与服务端 `_sanitize_env_vars` 保持一致：空字符串 key 会被过滤；value 为空字符串则保留 key，建议前端在保存前将空值字段从 `env_vars` 中省略）。
- 请求失败时保留 UI 状态，不清除用户输入，可选添加错误提示。

## 9. 导航入口

Settings 页面通过以下入口访问：

- 桌面端顶部导航栏（`TopNavBar`）的 Settings 选项。
- 移动端底部导航栏的 Settings 图标。

## 10. 可访问性

- 所有表单控件需有可见 label 或 aria-label。
- 开关按钮使用 `aria-pressed` 表示状态。
- 主题选择按钮使用 `title` 属性说明作用。
- 禁用按钮保持文字可读，不能只靠颜色表达状态。

## 11. 验收标准

- Settings 页面包含 AI 模型配置区域（主题、模型、系统提示词、工作区模式）。
- Settings 页面包含用户 API 配置区域（API 密钥、API 端点、默认模型三个输入项）。
- Chat 页面不再渲染模型配置侧边栏，也不在左侧 `VerticalNav` 中提供 Settings 入口。
- 所有颜色引用 [Color System](<./Color System.md>) token，无孤立十六进制值。
- Light/Dark 模式均可正常显示。
- 配置变更后正确同步到 `/api/system-config`。
- 语言、展示选项、AI 模型配置、用户 API 配置、关于内容分区清晰，各自有标题说明。
- `ANTHROPIC_AUTH_TOKEN` 输入框已保存的值以掩码形式展示，不反向暴露明文。
- 用户 API 配置保存后，该用户的后续 Agent 会话使用用户配置的 API 密钥和端点（而非全局 `backend/.env`）。
- 清空字段并保存后，该 key 从 `env_vars` 中移除，回退到服务器默认配置。

## 12. 前端实现备注

本轮已完成以下前端实现：
- 新建 `ModelConfigSection.tsx`，封装主题、模型、系统提示词、工作区模式的配置 UI 与 API 交互逻辑。
- 在 `App.tsx` Settings 视图中注入 `<ModelConfigSection />`，作为独立区域显示。
- `VerticalNav.tsx` 不再渲染 Settings 图标；Settings 保留顶部导航栏和移动端底部导航栏入口。
- `ChatView.tsx` 移除 `Sidebar` 组件，不再触发模型配置侧边栏弹出。

**用户 API 配置（待实现）**：
- 在 `ModelConfigSection.tsx`（或提取后的 `UserApiConfigGroup.tsx`）中新增 §4.3.5 描述的三个输入框区域。
- 页面挂载时从 `GET /api/system-config` 的 `env_vars` 字段读取初始值；`ANTHROPIC_AUTH_TOKEN` 有值时显示掩码，其余字段显示实际值。
- 保存时将非空字段组成 `env_vars` dict 通过 `PUT /api/system-config` 提交；空字段对应 key 从 dict 中省略（服务端会保留旧值），如需清除则显式发送空字符串（服务端 `_sanitize_env_vars` 会写入空字符串，效果等同清除）。
- 建议后续在 `GET /api/system-config` 路由层对 `ANTHROPIC_AUTH_TOKEN` 返回掩码，避免前端 JS 中出现明文密钥。

后续如需扩展 Settings 页面，建议将整个 Settings 视图提取为独立 `SettingsView.tsx` 组件，与 `App.tsx` 解耦。
