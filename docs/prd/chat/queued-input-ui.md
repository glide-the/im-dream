<!-- [Input] html_design_skill PRD, structure sketch, hierarchy logic, Dream tokens, and three user screenshots. -->
<!-- [Output] Visual decisions for the queued-input PRD and its standalone sample. -->
<!-- [Pos] Chat module UI appendix; production components remain under frontend/app/_dream/components/chat/. -->
<!-- [Sync] 2026-09-27: replace the Stage 4 two-button layout with the user-specified single Send/Stop action. -->

# Dream Chat 运行中输入：UI 视觉决策

## 背景与问题

`target_image.png` 展示当前故障：队列错误贴近输入框、停止与发送同时出现且相距过远、发送按钮越过右边界。两张 `reference_*.png` 只提供队列卡片与菜单的结构参照。用户补充的操作位截图明确要求发送与停止互斥。本稿承接前三阶段的业务状态及模块 ID，不将参考产品的蓝色与灰色移入 Dream。

## 目标与边界

- 同一 Chat 主列内依次显示消息、已确认的排队卡片、紧凑错误和输入 Dock；宽度变化时各层使用同一左右轴线。
- 排队卡片可读、可辨状态、可访问菜单；错误是独立反馈，不伪装成已入队卡片。
- Dock 右端只有一个操作位：有草稿显示发送，草稿为空且主轮次运行显示停止；当前按钮保持完整点击区域和准确名称。
- [运行中队列样稿](./queued-input-visual.html) 默认展示一条待处理卡片；`?state=menu`、`?state=multiple`、`?state=error` 分别展示菜单、多条消息和错误状态。样稿只演示视觉结构；真实状态更新仍由现有 Chat 组件根据服务端回执处理。

## 概念与规则

| 层级 | 视觉决策 | 行为边界 |
| --- | --- | --- |
| 页面底色 | `--color-bg-app: #1d1916`，弱化背景噪声 | 沿用 Dream 暗色主题 |
| 主表面 | `--color-bg-paper: #2a241f`、`--color-bg-surface-solid: #342d27` | 卡片与 Dock 同列，表面深浅分层 |
| 描边 | `--color-border-neutral: #4a4238`、`--color-border-paper: #5a4d3d` | 暖色细线，聚焦才加亮 |
| 文字 | 主文 `#f3e8d8`，次文 `#c8bcae`，弱文 `#9f9283` | 正文先于状态和操作进入视线 |
| 动作 | 发送使用 `--color-action-primary: #f3e8d8`；停止使用 `--color-state-danger: #ff8a7f` | 单一按钮按草稿和主轮次状态切换；当前动作有对应 `aria-label` 与焦点框 |
| 错误 | `--color-state-error: #ff7a70` 配低对比度暖红背景 | 先说明服务端回执及草稿是否保留，再提供适用的状态检查动作 |
| 字体 | Dream 的 Excalifont / Xiaolai 优先，系统字体回退 | 保留手写气质，长正文保证可读性 |

### 组件结构

```text
Chat 主列
├─ 现有消息列表
└─ 底部堆叠区
   ├─ QueueCardList：两个已确认队列卡片，限高滚动
   │  └─ QueueCard：正文 / 状态 / 调整方向 / 删除 / 更多
   │     └─ Menu：编辑消息 / 在侧边聊天中打开 / 关闭排队
   ├─ InlineQueueError：短文案 + 操作
   └─ AIInputDock：提示 / 草稿 / 附件与模式 / [发送或停止]
```

### 尺寸与响应

- 主列在宽视口限制内容宽度，侧栏展开或窄视口时按**容器宽度**收缩。卡片正文使用 `min-width: 0` 与省略显示；完整正文通过卡片标题和编辑操作可读。
- 队列最多占底部可用高度的一部分，卡片区自己滚动；Dock 保持可见。菜单朝上并向列内展开，不能被卡片滚动容器裁切。
- Dock 操作行使用 `margin-left: auto` 固定右端单一按钮。空间不足时左端控件先换行，按钮保持右对齐；状态切换不改变按钮位置。
- 焦点框使用暖色 `#ead8bd`。菜单用 Escape 关闭并回到触发按钮；错误用 `role="alert"`。按钮最小点击尺寸 44px。

### 动效

卡片进入只做 180ms 的淡入与 6px 上移；菜单 120ms 淡入。交互悬停改变表面与描边，不进行漂浮、缩放或持续动画。`prefers-reduced-motion: reduce` 关闭动画。

### 实现映射

在现有 `ChatPanel` 排队区、`ThreadInputQueueCard` 和 `AIInputDock` 内复用 Dream token 与业务状态；样稿没有引入外部 CSS、字体或图标 CDN。真实系统仅在服务端确认 `queued` 后显示卡片；提交失败保留草稿并继续显示发送，提交成功清空草稿后若主轮次仍运行则显示停止；`selected`、`dispatching`、`state_unknown` 的操作可用性依 [主 PRD](./queued-input.md) 更新。菜单中的侧边打开必须等待服务端完成消息转移后再显示新 Thread。
