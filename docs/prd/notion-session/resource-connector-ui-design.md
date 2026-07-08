## ✨ 总体视觉风格（Aesthetic Style）

> [Sync] 2026-07-08: 组件命名回收到 Chat `WorkspaceTabBar` + Settings `ConnectorNotionDetailPage` 体系；保留纸张审美、色板与微交互定义，Chat 不再承载完整配置下钻。
> [Sync] 2026-07-08: Settings 详情页改为单平台单账号资源配置页，不再使用 `ResourceConnectorPage` 的集合型新建、刷新、列表布局。
> [Sync] 2026-07-08: ResourceScopeSection 合并 data_source / page 为统一资源列表，操作行包含搜索、保存、刷新；每页显示 10 条；保存后 MountedSourcesSection 立即显示所选来源；底部授权状态卡移除。

| 维度 | 设计定义 |
| --- | --- |
| 风格关键词 | 暖纸张、手写感、安静工具台、资料贴签、低饱和编辑台 |
| 视觉气质 | 像一本被轻轻摊开的研究手账：留白充足、边界柔和、信息层级克制，强调“整理资源后再开始思考”的安静秩序。 |
| 光影策略 | 使用极浅阴影、纸边高光、虚线边框与雾面卡片，不做强烈玻璃拟态，避免打断阅读节奏。 |
| 排版策略 | 标题采用 **Noto Serif SC** 增加书卷感，正文与操作采用 **Noto Sans SC**，形成“文档感 + 工具感”的双重语气。 |
| 色彩策略 | Light 模式以米白、奶油、暖灰、墨棕为主；Dark 模式保留暖感，转为深炭褐、烟灰、柔米白，避免冰冷蓝黑。 |
| 交互策略 | 所有反馈都控制在轻量级：悬停上浮 1~2px、边框加深、按钮产生柔和墨色涟漪，强调“可操作但不喧哗”。 |

---

## 🧩 UI 组件结构（Component Structure）

| 模块 | 名称 | 作用 | 关键视觉表现 |
| --- | --- | --- | --- |
| RC-A | `WorkspaceTabBar` | Chat 工作区主切换，固定承载 `HistoryTab` / `ResourceConnectorTab` | 胶囊 tab、位于居中 Input Dock 下方、切换时不改变头部结构 |
| RC-B | `ResourceConnectorTabPanel` | Chat 内连接器内容区，承载 `ConnectorToolbar`、空态和列表 | 虚线空状态卡、筛选 / 排序工具栏、状态化连接器卡片 |
| RC-C | `ConnectorNotionDetailPage` | Settings 内连接器详情 / 配置页的整体页面壳 | 顶部面包屑 `← 资源连接器 > Notion Connector`、连续纸面区块 |
| RC-D | `TopNavigation` + `ConnectorHeader` + `NotionAccountStatusSection` | 详情页上半部分：导航、头卡、单账号状态概览 | Notion 图标、状态胶囊、连接 / 关闭真实操作、账号状态指标 |
| RC-E | `ResourceScopeSection` + `MountedSourcesSection` | 详情页下半部分：资源范围与已挂载来源 | 禁用态虚线框、统一资源列表、搜索框、分页、来源卡 |

> Chat 中的 `ResourceConnectorTabPanel` 负责“看见连接器、筛选连接器、跳转设置”；复杂配置全部进入 Settings 内的 `ConnectorNotionDetailPage`。
> Notion 详情页不出现集合级的创建按钮、刷新列表按钮或连接器列表；无账号时「连接 Notion」隐式创建唯一 connector。
> 授权 / 同步解释不再放到底部独立卡片，统一收敛到 `NotionAccountStatusSection`。
> 「保存资源」不是静默动作：保存完成后，`MountedSourcesSection` 必须立刻从空态切换为来源卡片，展示标题、类型、同步状态和最近更新时间。

---

## 🎨 CSS Variables 色彩系统

```css
:root {
  --paper-bg: #f6f0e6;
  --paper-panel: rgba(255, 250, 242, 0.9);
  --paper-card: #fffaf2;
  --paper-card-strong: #f2e8d8;
  --paper-border: rgba(114, 92, 72, 0.18);
  --paper-border-strong: rgba(114, 92, 72, 0.32);
  --paper-text: #3f3429;
  --paper-text-soft: #7a6a59;
  --paper-accent: #5f4a36;
  --paper-accent-soft: #d9c6ad;
  --paper-success: #7e9468;
  --paper-warning: #c78855;
  --paper-danger: #a86652;
  --paper-shadow: 0 18px 40px rgba(106, 83, 58, 0.08);
}

html[data-theme='dark'] {
  --paper-bg: #1d1916;
  --paper-panel: rgba(43, 37, 33, 0.92);
  --paper-card: #2a241f;
  --paper-card-strong: #342d27;
  --paper-border: rgba(222, 206, 186, 0.12);
  --paper-border-strong: rgba(222, 206, 186, 0.26);
  --paper-text: #f3e8d8;
  --paper-text-soft: #b7a894;
  --paper-accent: #ead8bd;
  --paper-accent-soft: #544739;
  --paper-success: #9db487;
  --paper-warning: #e2a674;
  --paper-danger: #cd8b78;
  --paper-shadow: 0 20px 48px rgba(0, 0, 0, 0.28);
}
```

---

## 🎞 微交互定义（Micro-interactions）

| 交互对象 | 触发方式 | 反馈定义 |
| --- | --- | --- |
| 顶栏按钮 | Hover / Focus | 背景由透明过渡为纸卡底色，边框略微加深，整体上浮 1px。 |
| 输入框容器 | Focus within | 外圈出现暖棕色柔和 ring，阴影略加深，强化“可以开始提问”的入口感。 |
| `WorkspaceTabBar` | Switch | 活跃 tab 背景加深并切换 `MainContentArea`；输入区与头部不抖动。 |
| 空状态按钮 | Hover | 轻微上浮并出现更深纸影，箭头图标向右移动 2px。 |
| 连接器状态面板 | Hover | 仅小型「管理」入口强化可点击反馈；面板正文保持信息展示属性，不做整卡按钮。 |
| 来源树节点 | Expand / Select | 展开箭头旋转，子级以轻量缩进进入，不使用重动画。 |
| 警告状态卡 | Toggle | 开关切换时保持文案区稳定，仅切换状态色与开关位置。 |
| 深色模式 | Toggle | 页面变量切换并带 220ms 颜色过渡，不闪屏。 |

---

## ✅ 说明
- 页面支持 **Light / Dark** 模式切换，并统一服务于 Chat 内 `WorkspaceTabBar` 与 Settings 内 `ConnectorNotionDetailPage`。
- `ResourceConnectorTabPanel` 要求默认保留筛选 / 排序工具栏位置；空态与加载态都不能挤掉该布局锚点。
- 已连接态使用非按钮状态面板，正文展示平台、授权 / 同步状态、已链接资源数量和来源摘要；只有明确的「管理」入口跳转 Settings。
- `ConnectorNotionDetailPage` 必须复用同一纸面视觉语言，组件层级固定为 `TopNavigation` → `ConnectorHeader` → `NotionAccountStatusSection` → `ResourceScopeSection` → `MountedSourcesSection`。
- 资源连接器入口在 Chat 工作区呈现为轻量摘要；完整配置归属于 Settings「资源链接」，详情页是 Settings 内管理层。
