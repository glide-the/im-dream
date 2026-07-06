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
| RC-A | ConnectorHeader | 显示连接器身份，并承载分享、更多菜单、主题切换 | 顶部单行、纸张标签式标题、细边按钮 |
| RC-B | ChatInputBar | 发起新聊天，控制模型、语音与发送 | 大圆角输入槽、内嵌工具按钮、暖底描边 |
| RC-C | TabSwitch | 切换“聊天 / 来源”主视图 | 手账胶囊标签、当前态有底色与内阴影 |
| RC-D | EmptySourcePanel | 在无来源时解释价值并给出 CTA | 大面积虚线框、居中图标组、卡片纸板感 |
| RC-E | SourceList | 展示已接入来源与同步状态 | 纵向资源卡、状态胶囊、细分隔线 |
| RC-F | ChatList | 展示历史对话与时间线 | 轻量列表卡、时间标记、摘要层级 |
| RC-G | AddSourceModal | 选择来源接入方式 | 底部 ActionSheet、三类来源入口、柔和遮罩 |

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
| Tab 标签 | Switch | 胶囊背景在 180ms 内滑入，未选中态文字降低对比度。 |
| 空状态按钮 | Hover | 轻微上浮并出现更深纸影，箭头图标向右移动 2px。 |
| 来源卡片 | Hover | 卡片整体上移 2px，标题变深，右上角状态标签更清晰。 |
| ActionSheet | Open / Close | 遮罩淡入，底部面板由下向上平滑滑入，关闭时反向执行。 |
| 深色模式 | Toggle | 页面变量切换并带 220ms 颜色过渡，不闪屏。 |

---

## ✅ 说明
- 页面支持 **Light / Dark** 模式切换、连接器名称行内编辑、更多菜单展开、来源 ActionSheet 打开/关闭。