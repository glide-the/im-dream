<!-- [Input] APP-06消息阅读PRD、原Native Markdown、消息列表与滚动实现。 -->
<!-- [Output] 消息预览测量、局部横滚、底部跟随的交互和状态合同。 -->
<!-- [Pos] Native Chat消息展示交互；原Web、业务Hook和HTTP协议保持。 -->
# Native对话消息阅读交互

## 背景与问题

原`MessageText`直接展示完整用户正文。`ChatMarkdown.native`代码和表格使用`ScrollView horizontal`；RN默认`flexGrow:1/flexShrink:1`参与父容器尺寸分配，需要核对紧凑内容测量。`ChatMessageList.native`沿滚动事件记录底部距离，布局变化与手势事件可能改变跟随意图。[执行记录](../../exec/app-experience-chat-rendering-20261103.md)区分源码事实、复现及验证。

## 目标与边界

沿`ChatPage.native`、`AIInputDock.native`、`useNativeChatThread`及原消息DTO工作。消息展示层持有预览状态；业务Hook持有提交、运行、Stop、保存与历史。局部Web文档继续承担原输入和Mermaid职责。共享Swift、图标、Admin、数据库及APP-04退出修改范围。

## 概念与规则

`MessageText`读取列表实测可见高度，完整正文使用内层`View.onLayout`测量。完整正文高于预览与44pt展开入口的合计高度时才收起，短屏下的短正文继续显示全文。裁剪外层通过`maxHeight`和`overflow:hidden`控制预览；内层保持自然尺寸，正文继续使用同一个`ChatMarkdown`。气泡最大宽度、现行文字和间距保持。展开入口使用双语文案、`accessibilityState.expanded`与44pt触摸高度。键由原Thread、`messageMergeKey`及正文part确定。

普通代码和表格的横向`ScrollView`显式关闭纵向flex伸缩，内容按顶部对齐，代码`Text`保留原空白与长行。纵向手势由外层消息列表持有。Mermaid继续由原局部文档处理。

消息列表以用户手势更新阅读意图；布局引起的偏移事件更新几何。展开用户正文时进入阅读状态，保持当前可见边界。处于跟随状态时，内容/视口变化后沿原`scrollToEnd`到达末尾；用户主动离开底部后展示原跳转入口。请求调度在下一次布局帧执行，Thread切换或组件卸载清理旧帧。`maintainVisibleContentPosition`继续保护历史读取位置。

## 正常业务时序

```mermaid
sequenceDiagram
  actor User as 用户
  participant Dock as AIInputDock.native
  participant Hook as useNativeChatThread
  participant List as ChatMessageList.native
  participant Text as MessageText
  participant Markdown as ChatMarkdown.native
  User->>Dock: 编辑原消息并发送
  Dock->>Hook: 原send和完整消息
  Hook-->>List: 原UIMessage与当前Thread
  List->>Text: 正文与可见高度
  Text->>Markdown: 完整原文本
  Markdown-->>Text: 正文自然尺寸
  alt 用户正文超过预览高度
    Text-->>User: 收起预览和展开消息
    User->>Text: 展开或收起
    Text-->>List: 原消息高度更新
  else 短正文
    Text-->>User: 完整正文
  end
  Hook-->>List: 原流式增量或完成结果
  alt 用户跟随底部
    List->>List: 布局后scrollToEnd
  else 用户阅读历史
    List-->>User: 保留位置与原滚动到底部入口
    User->>List: 滚动到底部
    List->>List: 恢复底部跟随
  end
  User->>Dock: 原Stop或等待完成
  Dock->>Hook: 原停止入口
  Hook-->>User: 原结果与保存状态
```

## 异常与恢复时序

```mermaid
sequenceDiagram
  actor User as 用户
  participant List as ChatMessageList.native
  participant Text as MessageText
  participant Markdown as ChatMarkdown.native
  participant Hook as useNativeChatThread
  User->>List: 上滑阅读历史
  List->>List: 手势记录离开底部
  Markdown-->>List: 图片或局部文档高度迟到更新
  List-->>User: 保留历史阅读位置
  User->>List: 原滚动到底部入口
  List->>List: 布局后定位最新内容
  User->>List: 软件键盘出现或收起
  List->>Text: 更新可见高度与预览
  List->>List: 按当前阅读意图处理尺寸变化
  User->>Hook: 原历史入口选择另一Thread
  Hook-->>List: 新Thread及已保存消息
  List->>List: 清理旧布局帧并初始化底部跟随
  List->>Text: 新Thread键，初始收起
  Note over List,Hook: 原读取失败反馈和重试由现行历史模块处理
```

## 状态转换

```mermaid
stateDiagram-v2
  [*] --> Measuring: 新Thread或消息
  Measuring --> Full: 正文适配预览
  Measuring --> Collapsed: 正文高于预览与入口合计
  Collapsed --> Expanded: 展开消息
  Expanded --> Collapsed: 收起消息
  Collapsed --> Full: 可见区域增大且收起无法节省空间
  Full --> Collapsed: 可见区域缩小且收起节省空间
  Expanded --> Measuring: 切换Thread
  Collapsed --> Measuring: 切换Thread
  state ScrollIntent {
    [*] --> Following
    Following --> Reading: 用户手势离开底部或展开正文
    Reading --> Following: 原跳转入口或手势回到底部
    Following --> Following: 内容或视口变化后定位末尾
    Reading --> Reading: 新内容或布局变化保留位置
  }
```

## 方案评审与交付

| 评审项 | 判断与选择 | 验证归属 |
| --- | --- | --- |
| 长文本展示 | 使用实测视口和原Markdown裁剪，排除字符截断和固定业务字数 | 原组件测量、全文复制及切换Thread |
| 代码尺寸 | 局部横滚按实际高度布局，保留原生正文和Mermaid局部文档 | Chrome尺寸与Hermes实际触摸 |
| 滚动 | 原列表区分用户手势和布局变化，复用原底部判断与跳转入口 | 流式、键盘、异步高度及历史阅读 |
| 页面规范 | 保留原字号、圆角、间距和输入/栏目关系 | v3.1第6、8、11页及深浅色截图 |
| 范围 | UI层最小修复；复用原业务Hook及公开协议 | provider-free完整旅程；真实模型、真机及发布独立登记 |

方案通过最小范围评审。实现、技术验证、Simulator结果及剩余资格由[独立执行记录](../../exec/app-experience-chat-rendering-20261103.md)维护；PRD页面骨架归[消息阅读PRD](../../prd/chat/message-reading.md)。
