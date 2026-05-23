# Chat Send PRD

> 对话输入 Dock、发送行为、已发送消息与反馈状态的视觉和交互规范。本文引用 [Color System](<./Color System.md>)，仅更新 PRD，不修改产品代码。

## 1. 文档范围

Chat Send 覆盖用户输入文本、添加附件、键盘发送、发送前校验、发送中反馈、发送后消息展示，以及输入 Dock 与消息流的视觉一致性。

## 2. 设计目标

- 输入区是聊天体验的主操作，应清晰、安静、可持续停留。
- 发送前输入 Dock 和发送后用户消息共享纸面语言，而不是两个割裂组件。
- 支持空、输入中、可发送、上传中、发送中、失败、禁用、聚焦等状态。
- 避免旧稿中依赖 Tailwind class、孤立 CSS 变量和外部 app 路径的描述。

## 3. 页面结构

```
ChatPanel
├── ChatHistory
└── AIInputDock
    ├── AttachmentTray
    ├── TextInputArea
    │   ├── Placeholder
    │   └── CharacterCounter
    └── ActionRow
        ├── AddButton
        ├── ShortcutHint
        └── SendButton
```

## 4. AIInputDock 视觉规范

| 属性 | 规范 |
|---|---|
| 定位 | 底部 sticky/fixed，根据页面结构避免遮挡消息。 |
| 宽度 | 与消息流主轴对齐，桌面端不超过舒适阅读宽度。 |
| 背景 | `color.bg.paper` 或 `color.bg.surfaceSolid`。 |
| 边框 | `color.border.paper`。 |
| 阴影 | 默认轻阴影，hover/focus 时增强到 `color.shadow.soft`。 |
| 圆角 | 12px 到 16px，保持纸张柔和感。 |
| 字体 | 输入内容使用当前产品手写/衬线体系；功能提示可用系统无衬线。 |

## 5. 输入与发送规则

### 5.1 TextInputArea

- Placeholder 使用 `Press i chat` 或本地化等价文案，颜色 `color.text.muted`。
- 输入文本使用 `color.text.body`，caret 使用 `color.text.primary`。
- 字符计数如存在，放在右下角，使用 `color.text.muted`。
- 多行输入自动增长，但必须设置最大高度，超过后内部滚动。

### 5.2 AddButton

- 默认显示 `+ Add` 或图标 + 文案。
- 点击打开附件菜单，菜单项包括上传文件、最近文件、工作区文件。
- 有上传中附件时 AddButton 仍可打开附件托盘，但不应导致重复上传。

### 5.3 SendButton

- 可发送时使用 `color.action.link` 或 `color.action.primary` 的小面积按钮。
- 不可发送时使用 `color.disabled.bg` 和禁用光标。
- 发送中显示 spinner 或省略号，不改变按钮尺寸。
- 点击反馈使用 `active: scale(0.96)` 等轻量压感。

## 6. 发送前校验

| 校验项 | 结果 |
|---|---|
| 文本为空且无附件 | SendButton 禁用。 |
| 附件仍在上传 | SendButton 禁用，并显示上传中提示。 |
| 附件上传失败 | SendButton 禁用或要求移除失败附件。 |
| 网络或会话不可用 | 输入区显示错误说明和重试入口。 |
| 快捷键发送 | `Cmd/Ctrl + Enter` 发送；`Shift + Enter` 换行。 |

阈值、文件限制、模型策略不得在 PRD 中写死，应由产品策略或配置决定。

## 7. 发送后消息规范

| 元素 | 规范 |
|---|---|
| 用户消息容器 | 与输入 Dock 同轴对齐，使用柔和纸面气泡。 |
| 文本 | `color.text.body`，行高保持阅读舒适。 |
| 附件 | 遵循 [Chat File](<./Chat File.md>)。 |
| 已发送状态 | 小型元信息，不抢占正文。 |
| 发送失败 | 保留原消息草稿，显示重试和编辑入口。 |

用户消息不使用整块高饱和橙色；如需要明显区分发送方，优先使用对齐、头像/字母标记、边框或小徽标。

## 8. 状态设计

| 状态 | 视觉与交互 |
|---|---|
| Idle | 纸面输入区，placeholder 可见。 |
| Focus | 边框或 ring 使用 `color.border.focus`，同时保持文本对比。 |
| Typing | 显示字符计数和可发送按钮。 |
| Attachment Added | AttachmentTray 展开，输入区高度稳定。 |
| Uploading | 附件卡显示进度，发送按钮禁用。 |
| Sending | 输入内容转入 pending 消息，按钮显示加载。 |
| Sent | 清空输入区和附件托盘，消息进入历史。 |
| Failed | 输入 Dock 或消息旁显示错误和重试。 |
| Disabled | 输入区整体降级，但保留原因说明。 |

## 9. 色彩规范

| 场景 | Token |
|---|---|
| Dock 背景 | `color.bg.paper`、`color.bg.surfaceSolid` |
| Dock 边框 | `color.border.paper` |
| 输入文本 | `color.text.body` |
| Placeholder | `color.text.muted` |
| Add 默认 | `color.text.secondary` |
| Send 可用 | `color.action.link` 或 `color.action.primary` |
| Send 禁用 | `color.disabled.bg` |
| 发送失败 | `color.state.error` |

## 10. 暗色模式

- Dock 背景切换到 Dark `color.bg.paper`，边框切换到 Dark `color.border.paper`。
- Placeholder 不得低到不可读。
- SendButton 使用 Dark `color.action.link` 或反色炭黑主操作。
- 附件托盘和错误态沿用对应语义 token。

## 11. 可访问性

- 输入区需要明确 label 或 aria-label。
- SendButton 和 AddButton 的禁用原因要能被读屏或提示文本理解。
- 快捷键提示不是唯一发送方式。
- Focus 状态必须可见，不得只靠 placeholder 变化。

## 12. 验收标准

- 输入 Dock、Add、附件、发送按钮、已发送消息均有统一视觉规范。
- 空、聚焦、输入中、上传中、发送中、失败、禁用、已发送状态均可验收。
- 文档颜色全部映射到 [Color System](<./Color System.md>)。
- 未引入 Tailwind、外部 app 路径或源码实现要求。

## 13. 前端实现备注

本 PRD 不要求本轮实现。后续实现应优先复用现有聊天输入和文件附件组件，并将发送状态、附件状态、键盘快捷键拆分为可测试的 UI 状态。
