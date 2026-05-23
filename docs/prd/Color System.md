# Color System PRD

> 面向 `docs/prd` 下聊天、文件、侧边栏、Dashboard、历史记录、发送区和暗色模式 PRD 的统一色彩系统。本文是产品与设计文档，不修改源码、不引入新业务逻辑。

## 1. 文档目的

统一当前项目的视觉语言和 PRD 表达，避免新增 PRD 沿用旧稿中的 Tailwind 原型、霓虹橙主色、高级灰营销风或外部资产假设。

本文基于当前产品实际视觉系统抽象 Design Token，用于指导后续设计、前端评审和 QA 验收。当前源码尚未提供集中式 CSS token 文件或 Tailwind 配置，因此本文 token 是 PRD 层的命名规范，取值来自现有界面实现与视觉截图。

## 2. 设计依据与取舍

| 依据 | 结论 |
|---|---|
| `frontend/src/App.css` | 产品底色为暖纸张 `#f8f0e6`，页面纸面为 `#fffef9`，边框为棕灰/中性灰，整体像笔记本。 |
| `frontend/src/App.tsx` 与 `TopNavBar.tsx` | 导航和设置以炭黑 `#2c2c2c`、棕灰 `#d0c4b0`、次级灰 `#666` 为主。 |
| `ChatWidgetUI.tsx` 与 `CommentCard.tsx` | 聊天和评论使用柔和纸面、半透明浅底、手写/衬线字体、低强度 hover 与 pulse。 |
| `deckVisuals.ts` | 语义/声部色包含蓝、紫、粉、绿、黄，适合做分类和声部标记。 |
| `docs/prd/image.png` | 作为聊天流视觉参考：暖灰背景、白色气泡、深色 Terminal、底部输入 Dock、细橙色工具指示线。 |

冲突取舍：

- 旧 PRD 中 `#FF7A00`、`#FF6B00` 不作为全局主色；工具步骤或链接可使用“注意色”，但不得压过产品的纸张与炭黑主视觉。
- 旧 PRD 中 Tailwind、Font Awesome、远程头像和独立 HTML 原型不作为项目约束；项目当前使用 React、CSS/inline style、`react-icons` 和本地字体。
- 暗色模式当前没有完整源码实现；本文给出设计目标和 token 映射，不声称已实现。

## 3. 当前视觉设计概览

Ink & Memory 的视觉关键词是“纸张、笔记、手写、安静工具台”。界面应像一本可交互笔记本，而不是 SaaS 营销页或高饱和控制台。

| 维度 | 规范 |
|---|---|
| 画布 | 使用暖米色背景，避免纯白全屏和冷灰渐变。 |
| 承载面 | 使用奶油纸面、半透明白面板或轻微纸张阴影。 |
| 文本 | 主文本炭黑，正文偏深灰，辅助文本偏棕灰；不要用亮橙作为正文强调。 |
| 字体 | 英文优先 `Excalifont`/Georgia 风格，中文优先 `Xiaolai`，功能控件可使用系统无衬线。 |
| 圆角 | 文档、卡片、弹窗以 4/6/8/12px 为主；聊天输入 Dock 可使用更柔和的 16px 左右圆角。 |
| 动效 | 0.2s 到 0.3s 的 hover、focus、展开过渡；避免大幅旋转、强 glow、持续闪烁。 |

## 4. 品牌与基础色板

| 色板 | 用途 | Light | Dark 目标 | 备注 |
|---|---|---:|---:|---|
| Warm Canvas | App 背景 | `#f8f0e6` | `#1f1b16` | 当前主背景。 |
| Paper Surface | 编辑/聊天纸面 | `#fffef9` | `#2a251e` | 当前主要内容面。 |
| Soft Surface | 设置卡片/轻面板 | `rgba(255,255,255,0.5)` | `rgba(42,37,30,0.82)` | 轻量分组。 |
| Solid Surface | 菜单/弹窗 | `#ffffff` | `#332d25` | 高可读弹出层。 |
| Charcoal | 主文本/主操作 | `#2c2c2c` | `#f3eee6` | 产品主锚点色。 |
| Ink Text | 正文 | `#333333` | `#eee8df` | 内容阅读。 |
| Secondary Text | 次级文本 | `#666666` | `#c8bcae` | 描述、图标默认。 |
| Muted Text | 弱文本 | `#8a7a69` | `#9f9283` | 说明、时间、占位。 |
| Paper Border | 纸面边框 | `#d0c4b0` | `#5a4d3d` | 当前主要分隔线。 |
| Neutral Border | 控件边框 | `#e0e0e0` | `#4a4238` | 工具条、菜单。 |
| Link Blue | 链接/主要异步动作 | `#4a90e2` | `#81b7d2` | 来自登录、评论发送、卡组色。 |
| Success Green | 成功/在线 | `#4CAF50` | `#7bcf8f` | 成功 toast、头像状态。 |
| Error Red | 错误/失败 | `#f44336` | `#ff7a70` | 错误 toast。 |
| Danger Red | 删除/破坏性 | `#d44` | `#ff8a7f` | 删除、关闭危险操作。 |
| Attention Yellow | 工具步骤/提醒 | `#f39c12` | `#f7c96a` | 可承接截图中的橙色细线，但不得作为全局主色。 |

## 5. 语义色彩 Token

| Token 名称 | 用途 | Light 值 | Dark 值 | 使用示例 |
|---|---|---:|---:|---|
| `color.bg.app` | 应用背景 | `#f8f0e6` | `#1f1b16` | Chat Dashboard、File Work 背景。 |
| `color.bg.paper` | 主要阅读/编辑面 | `#fffef9` | `#2a251e` | 消息流、编辑纸张、弹窗主体。 |
| `color.bg.surface` | 次级面板 | `rgba(255,255,255,0.5)` | `rgba(42,37,30,0.82)` | 设置组、文件信息组。 |
| `color.bg.surfaceSolid` | 不透明浮层 | `#ffffff` | `#332d25` | 菜单、Tooltip、Popover。 |
| `color.bg.overlay` | 遮罩 | `rgba(0,0,0,0.5)` | `rgba(0,0,0,0.72)` | Modal 背景。 |
| `color.border.paper` | 暖纸边框 | `#d0c4b0` | `#5a4d3d` | 卡片、输入区、分隔线。 |
| `color.border.neutral` | 中性边框 | `#e0e0e0` | `#4a4238` | 工具条按钮、文件卡。 |
| `color.border.focus` | 焦点边框 | `#2c2c2c` | `#f3eee6` | 键盘焦点、选中项。 |
| `color.text.primary` | 主文本 | `#2c2c2c` | `#f3eee6` | 标题、按钮主文案。 |
| `color.text.body` | 正文 | `#333333` | `#eee8df` | 消息正文、说明正文。 |
| `color.text.secondary` | 次级文本 | `#666666` | `#c8bcae` | 元信息、图标默认。 |
| `color.text.muted` | 弱提示 | `#8a7a69` | `#9f9283` | placeholder、时间戳、辅助说明。 |
| `color.action.primary` | 主操作 | `#2c2c2c` | `#f3eee6` | 主按钮、当前导航。 |
| `color.action.link` | 链接/发送可用 | `#4a90e2` | `#81b7d2` | 文档链接、发送按钮可用态。 |
| `color.state.success` | 成功 | `#4CAF50` | `#7bcf8f` | 上传成功、Exit code 0。 |
| `color.state.warning` | 提醒/工具步骤 | `#f39c12` | `#f7c96a` | 折叠工具步骤左线。 |
| `color.state.error` | 错误 | `#f44336` | `#ff7a70` | 上传失败、请求失败。 |
| `color.state.danger` | 破坏性 | `#d44` | `#ff8a7f` | 删除文件、删除消息。 |
| `color.disabled.bg` | 禁用背景 | `#cccccc` | `#58504a` | 禁用按钮、上传中不可点。 |
| `color.shadow.soft` | 轻阴影 | `rgba(0,0,0,0.08)` | `rgba(0,0,0,0.32)` | 卡片 hover。 |
| `color.shadow.medium` | 中阴影 | `rgba(0,0,0,0.15)` | `rgba(0,0,0,0.45)` | Popover、菜单。 |

## 6. 声部、分类与高亮色

| Token | Light | Dark 目标 | 使用规则 |
|---|---:|---:|---|
| `color.voice.blue` | `#4a90e2` | `#81b7d2` | 链接、蓝色声部、常规异步动作。 |
| `color.voice.purple` | `#9b59b6` | `#c99be1` | 创意、洞察类声部。 |
| `color.voice.pink` | `#e91e63` | `#ff8fbd` | 情绪、关系类声部。 |
| `color.voice.green` | `#27ae60` | `#7bdba0` | 成功、成长、正向反馈。 |
| `color.voice.yellow` | `#f39c12` | `#f7c96a` | 提醒、重点、工具步骤。 |
| `color.highlight.blue` | `#a3d5ff` | `rgba(129,183,210,0.38)` | 文本高亮背景，透明度低。 |
| `color.highlight.pink` | `#ffb3d9` | `rgba(255,143,189,0.34)` | 文本高亮背景。 |
| `color.highlight.green` | `#b3ffb3` | `rgba(123,219,160,0.30)` | 文本高亮背景。 |
| `color.highlight.yellow` | `#ffff43` | `rgba(247,201,106,0.36)` | 文本高亮背景，不用于大面积面板。 |
| `color.highlight.purple` | `#ddb3ff` | `rgba(201,155,225,0.34)` | 文本高亮背景。 |

## 7. 明暗模式规则

明暗模式采用同一套语义 token，不允许在模块 PRD 中直接新增孤立十六进制色值。

Light 模式：

- 背景保持暖米色，主内容是奶油纸面。
- 当前项以炭黑文字、炭黑底或炭黑下划线表示。
- 工具步骤、上传提醒、终端命令提示可使用低面积注意色。

Dark 模式目标：

- 保留“夜间纸张”气质，使用暖黑和深棕灰，不改成赛博黑、纯黑或霓虹橙主题。
- 纸张层级通过亮度差、边框和阴影区分，不依赖高饱和背景。
- 所有声部和状态色降低大面积使用，只保留小面积图标、左线、徽标、按钮状态。
- 终端区可使用更深的 `#111820` 到 `#151a1f`，但外围仍遵循暖色纸面体系。

## 8. 背景、边框、文本、图标与状态规范

### 背景

- 一级页面背景使用 `color.bg.app`。
- 消息流、编辑区、弹窗主体使用 `color.bg.paper`。
- 轻量面板使用 `color.bg.surface`，需要文字密集时使用 `color.bg.surfaceSolid`。
- 禁止使用冷灰渐变或大面积纯白替代产品背景。

### 边框

- 纸面、侧边栏、设置组使用 `color.border.paper`。
- 工具按钮、附件卡、菜单项使用 `color.border.neutral`。
- 键盘焦点使用 `color.border.focus`，并可增加 2px 低透明 ring。

### 文本

- 标题、当前项、强操作使用 `color.text.primary`。
- 聊天正文、说明正文使用 `color.text.body`。
- 时间、计数、placeholder 使用 `color.text.muted`，不得承载关键内容。

### 图标

- 默认图标使用 `color.text.secondary`。
- 当前/选中图标使用 `color.text.primary`。
- 状态图标使用对应 `color.state.*`，同时提供文本说明或 aria label。

### 状态色

| 状态 | 色彩规则 | 反馈 |
|---|---|---|
| Hover | 背景轻微加深或阴影增强 | 0.2s ease，不超过 4px 位移。 |
| Focus | 明确边框或 ring | 键盘可见，不能只靠颜色变化。 |
| Selected | 炭黑文本/底或暖纸边框加强 | 与 hover 区分。 |
| Disabled | 降低对比、禁用光标、保留说明 | 不隐藏核心信息。 |
| Loading | 低对比 pulse 或 spinner | 不使用高频闪烁。 |
| Error | 红色文本/边框加说明 | 不只用红色。 |
| Success | 绿色文本/徽标加完成文案 | 上传/发送完成后可短暂显示。 |

## 9. 聊天场景色彩规则

- 用户消息：使用 `color.bg.surfaceSolid` 或 `color.bg.paper` 上的柔和气泡；若需要强调发送方，可用 `color.action.primary` 小面积标识，不使用整块高饱和橙色。
- 助手消息：默认无重卡片背景，保持正文阅读感；必要分组使用 `color.bg.surface`。
- 工具步骤：左侧 2px 指示线使用 `color.state.warning`，标题使用 `color.text.secondary`，展开内容使用纸面/代码块。
- Terminal：背景使用深色块，命令提示可使用 `color.action.link`，Exit code 成功/失败使用 success/error。
- 链接：使用 `color.action.link`；如果继承截图中的橙色链接，应先映射到 `color.state.warning` 并限制在链接/步骤小面积。

## 10. 文件与附件场景色彩规则

- 文件卡默认使用 `color.bg.surfaceSolid`，边框 `color.border.paper`。
- 拖拽上传态使用 `color.action.link` 或 `color.state.warning` 的虚线边框，不使用大面积填充。
- 上传中使用中性进度条，完成用 success，失败用 error。
- 删除、移除附件使用 danger，并要求二次确认或明确撤销反馈。
- 图片缩略图不叠加重滤镜，文件类型色仅用于图标或小徽标。

## 11. 模块色彩规则

| 模块 | 规则 |
|---|---|
| Sidebar | 使用 `color.bg.app` 或 `color.bg.surfaceSolid`；当前项以炭黑文字/下划线/左线表示。 |
| Dashboard | 背景为暖纸张，快捷卡为白/半透明纸面；不要使用营销式渐变 Hero。 |
| History | 消息流以阅读为先，工具与终端采用低面积状态色。 |
| Send | 输入 Dock 与已发送卡保持同一纸面语言；发送按钮可用 link blue 或炭黑主操作。 |
| File Work | 上传、文件列表、预览都使用纸面层级，类型色只做辅助。 |
| Dark Mode | 同一语义 token 切换，不重建另一套视觉品牌。 |

## 12. 可访问性与对比度要求

- 正文文本对背景对比度不低于 WCAG AA 4.5:1。
- 图标、边框、焦点态对相邻背景不低于 3:1。
- 状态反馈必须同时包含颜色之外的信息，例如文本、图标、aria label 或位置变化。
- `color.text.muted` 不用于错误、价格、文件状态、发送失败等关键内容。
- 禁用态需要可读，不得把文本降到不可辨认。

## 13. 禁止用法

- 禁止把 `#FF7A00`、`#FF6B00`、霓虹橙或玫瑰金作为全局主色。
- 禁止使用冷灰渐变、赛博 glow、噪点、斜切角等与当前纸张系统冲突的风格。
- 禁止在 PRD 中要求引入 Tailwind、Font Awesome 或外部头像作为必要实现。
- 禁止大面积使用声部色；声部色只用于标记、高亮、图标、徽标。
- 禁止只用颜色表达状态。
- 禁止覆盖 `docs/prd/image.png`；需要更新时先提出视觉更新方向和替换范围。

## 14. 设计验收标准

- 所有 `docs/prd` 文档均引用本文，并避免新增孤立色值。
- 每个 PRD 至少包含布局层级、组件状态、暗色模式适配、可访问性和验收标准。
- 新增或更新的视觉描述能够映射到本文 token。
- 与当前项目冲突的 Tailwind/独立 HTML 原型描述已删除或标注为不采用。
- `image.png` 保持原始文件不变，仅作为聊天视觉参考。

## 15. 前端实现备注

本文不要求本轮修改前端源码。后续如实现 token 化，建议先在前端建立集中式主题 token，再逐步替换 inline style 中重复出现的 `#f8f0e6`、`#fffef9`、`#d0c4b0`、`#2c2c2c`、`#666` 等颜色。
