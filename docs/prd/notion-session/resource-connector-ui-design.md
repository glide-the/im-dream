## ✨ 总体视觉风格（Aesthetic Style）

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
| RC-A | ConnectorSettingsSection | 承载远程 / 本地资源链接索引卡片，「管理」触发页面导航 | Settings 资源卡片、结构化分区、管理按钮 |
| RC-B | ConnectorLandingPanel | Chat 中的轻量 connector 摘要和 Settings CTA | 小型摘要卡、状态条、跳转按钮 |
| RC-C | ConnectorNotionDetailPage | Notion「具体配置页面」，独立导航页，替换整个 Settings 视图 | 面包屑导航（设置 › 资源链接 › Notion 具体配置页面）+ 复用 `ResourceConnectorPage` page mode |
| RC-D | ResourceOptionCard | Notion / 飞书 / CLI 资源卡片 | 状态胶囊、禁用占位、管理按钮 |
| RC-E | ResourceStatusBadge | 健康 / 未连接 / 认证中状态展示 | 小圆点 + 文字胶囊 |

> `ResourceConnectorPage` 作为 Notion 的 page mode 管理页保留，由 `ConnectorNotionDetailPage` 承载并加上面包屑导航；Chat 入口仅保留摘要和 CTA，不再直接承载完整工作台。
> Settings 资源链接区分为远程资源与本地资源两个层级；点击 Notion「管理」是页面级导航（`showNotionConnectorDetail` 状态切换），不是在资源链接卡片内原地展开。
> 页面壳需要保留 Settings 侧的浅纸张感和 Chat 侧的轻量摘要感，不再继续强化黑底 workbench 作为默认连接器入口。

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
| 应用导航状态 | Switch | 应用级导航切换历史/连接器 landing state；Chat 输入区下方不再重复显示切换 pill。 |
| 空状态按钮 | Hover | 轻微上浮并出现更深纸影，箭头图标向右移动 2px。 |
| 来源卡片 | Hover | 卡片整体上移 2px，标题变深，右上角状态标签更清晰。 |
| ActionSheet | Open / Close | 遮罩淡入，底部面板由下向上平滑滑入，关闭时反向执行。 |
| 深色模式 | Toggle | 页面变量切换并带 220ms 颜色过渡，不闪屏。 |

---

## ✅ 说明
- 页面支持 **Light / Dark** 模式切换、Settings 资源链接分区、Notion 具体配置页面和 Chat 轻量 connector 摘要面板。
- `ResourceConnectorPage` 仅作为 Notion 的 page mode 管理页使用，由 `ConnectorNotionDetailPage` 加面包屑导航后承载；Chat 中的 connector 面板只保留状态摘要和跳转 CTA，不承载创建 / 认证 / 来源选择。
- `ConnectorSettingsSection` 只管理远程 / 本地资源的入口分区索引卡片，飞书和本地 CLI 执行器都保持占位，不调用不存在的 API；点击 Notion「管理」触发页面导航而非原地展开。
