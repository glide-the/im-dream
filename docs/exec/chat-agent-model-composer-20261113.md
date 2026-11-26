<!-- [Input] 用户要求Agent入口替换工具入口并直接迁移GitHub模型组件，数据沿IM。 -->
<!-- [Output] 迁移范围、源码依据、开发项和本轮验证回执。 -->
<!-- [Pos] Chat统一入口与模型组件本轮执行记录；此前工具回执按原范围保留。 -->
<!-- [Sync] 2026-11-13: 复核正常Chat入口并修订保留挂载页面的菜单关闭和模型重新读取。 -->

# Chat统一Agent入口与模型选择

## 优化后的任务定义

将输入栏的独立Agent和工具入口合并为“Agent图标 当前Agent ▾”，菜单继续承载Agent选择与工具配置；新增模型选择。读取Better Chatbot的ToolSelectDropdown、AgentSelector和SelectModel源码，迁移对应UI结构、搜索、选中状态及响应式弹层，接入IM原Agent目录、MCP管理、模型目录与保存接口。保留原Thread、草稿、附件、Skill、排队、权限和Stop；后端与数据库保持当前范围。同步独立Chat产品／开发稿和目录合同，保留修订前原文。

## 发现与方案收敛

- 发现：当前输入栏并列Agent与工具；参考SelectModel采用搜索、分组、选中勾选、不可用项禁用、桌面Popover与移动Drawer。IM通过gatewayModelsApi与useModelConfig读取、校验并保存模型。
- 定义：一个Agent触发入口承载Agent与工具，模型单独选择；组件状态与业务数据分别接线。
- 比较：整体引入参考appStore与服务端API会替换现有数据路径；选定迁移UI模块并适配原IM数据，保留MIT声明和原源码快照。
- 交付：修订Chat专项稿，接入Web／Native组件，执行定向技术验证。自动路由、本地模型服务、价格／榜单与参考项目预设无IM数据来源，本轮沿现有能力。

## 范围与状态

源码迁移、Web／Native组件接线与定向技术验证已完成。真实模型／MCP、真机、原生音频和发布验收保持未执行。

## 交付物

- [Chat交互设计](../prd/chat/agent-tool-composer.md)：单一当前Agent入口、模型选择、桌面／窄屏骨架与业务状态。
- [Chat开发设计](../design/claude-agent/chat-agent-tool-composer.md)：Agent目录、MCP、模型组件与原IM接口的接线和时序。
- [源码来源与MIT声明](../../frontend/third-party/better-chatbot/README.md)：3份原源码快照、Git blob SHA和实际运行组件映射。
- `ComposerToolsMenu`／`ComposerAgentSelector`合并输入栏入口；`SelectModel`与`ComposerModelSelector`复用原目录、配置与保存回执。
- 原输入栏、ChatView／ChatPanel和Native App接入；原消息DTO、Thread、草稿、权限、排队和Stop保持现行通道。

## 技术验证

| 命令 | 退出码 | 结果 |
| --- | --- | --- |
| `pnpm exec tsc --noEmit --incremental false --pretty false` | 0 | Web类型检查通过 |
| `pnpm native:typecheck` | 0 | Native类型检查通过 |
| `pnpm exec playwright test --config=e2e/chat-tools.config.ts e2e/chat-tools.spec.ts app/_dream/components/chat/__tests__/AIInputDockSlashMenuRegression.test.ts --output=output/chat-agent-model-20261113/browser-delivery` | 0 | 23项：18项Agent／模型／MCP／Native呈现与5项原输入栏用例通过 |
| `node frontend/output/chat-agent-model-20261113/checks/check-docs.mjs` | 0 | 文档／引用、2份历史原文、3份上游快照哈希、11个新增源码头与9幅图通过 |

原始命令与输出见[交付验证回执](../../frontend/output/chat-agent-model-20261113/checks/delivery-receipt.md)。主代理复核了桌面模型菜单的末端对齐和Native呈现的单排Agent／模型／发送布局。

初次原输入栏回归的按钮数量断言包含新增模型按钮，已收敛到原Send/Stop动作；上游快照落盘的结构换行已按原文恢复。失败记录与修正后回执分别保留。模型成功以当前值与保存结束反馈，拒绝和未确认继续使用原恢复行为。

## 验收边界

本轮为隔离技术验证，HTTP使用明确fixture。Native用例采用RNW呈现，iOS／Android真机、系统软键盘、真实账户／模型／MCP连接、媒体播放、后台计算、安装构建及部署均未执行。当前工作树中的先前后端及其他并行改动保持；本轮未修改后端、数据库、模型目录DTO或useModelConfig数据实现。

## 正常Chat接线复核

### 执行定义与判断

复用当前候选组件，核对正常Chat的新建会话和已有会话入口、目录与保存回调、原Thread及消息协议。仅修订当前前端接线缺口，保留既有工作树、原权限、音频不可用状态和后端边界；以当前源码、隔离界面及文档检查分别交付证据。

源码复核确认：`ChatView`新会话传入原完整目录；已有会话经`ChatPanel`传入当前Deck的Agent范围。`createChatThread`和`buildClaudeChatRequest`继续传递原Deck／Voice与Thread身份。`ComposerModelSelector`沿原`useModelConfig`和目录；保存确认经Web配置重读或Native的`setup.refreshConfig`交回原页面。

发现保留挂载的Web Chat缺少菜单可见状态传递，模型选择器在离开后返回时保留旧偏好。选定复用原`isVisible/active`和`modelLoadNonce`：隐藏关闭菜单，返回在保存结束后重新读取已保存配置与目录。草稿、附件及运行流分别沿原生命周期管理。

### 复核交付

- Web `ChatView → ChatPanel → AIInputDock`透传场景可见状态，统一Agent菜单与模型菜单收到相同状态。
- Web／Native模型适配器在返回场景时推进原读取代次；进行中的保存先完成。
- 已有会话入口复用原顶部Agent的`threadVoiceEntry/badgeDeckId`投影，保留旧Thread通过`Voice.thread_id`识别当前Agent与所属目录的展示。
- `chat-route-cache.spec.ts`通过生产Router／ChatView／ChatPanel验证新建Thread、首次发送、同Deck切换Agent、原工具模式、同Thread后续发送、模型保存、隐藏关闭、返回重读和草稿保留，覆盖1200px与390px。
- 原缓存／历史水合规格补现有模型目录fixture，`chat-tools.spec.ts`补Native返回后读取已保存模型；公开业务DTO及后端实现保持原范围。

### 当前验证

以下命令均使用当前工作树；前端命令工作目录为`frontend/`。本次29项浏览器检查为23项组件／原输入栏与6项正常页面组件接线的合计，HTTP全部由规格提供合成响应。

| 命令 | 退出码 | 当前结果 |
| --- | --- | --- |
| `pnpm exec tsc --noEmit --incremental false --pretty false` | 0 | Web完整类型检查通过；最后Agent投影修订后在`current-route-final`重跑通过 |
| `pnpm native:typecheck` | 0 | Native完整类型检查通过 |
| `pnpm exec playwright test --config=e2e/chat-tools.config.ts e2e/chat-tools.spec.ts app/_dream/components/chat/__tests__/AIInputDockSlashMenuRegression.test.ts --output=output/chat-agent-model-20261113/current-review-final/browser` | 0 | 23项通过，包含Native场景返回模型重读；RNW呈现 |
| `pnpm exec playwright test --config=e2e/chat-tools.config.ts e2e/chat-route-cache.spec.ts --output=output/chat-agent-model-20261113/current-route-delivery/browser` | 0 | 6项通过，16.4秒；1200px／390px原请求、Agent范围、旧Thread、菜单关闭、模型重读、草稿、正文与原水合回归 |

完整命令回执见[组件及类型检查](../../frontend/output/chat-agent-model-20261113/current-review-final/validation-receipt.md)、[最后Web类型检查](../../frontend/output/chat-agent-model-20261113/current-route-final/validation-receipt.md)与[正常页面接线验证](../../frontend/output/chat-agent-model-20261113/current-route-delivery/validation-receipt.md)。正常页面的两项状态重试规格各注入一次503并恢复；统一入口及模型旅程要求零额外请求路径、零页面与控制台错误。

主代理复核桌面和390px截图，四项操作保持同排。视觉复核曾发现合成流缺少原`turnId`导致重复回复，夹具现使用`message-metadata/message-final`并与回读消息保持同一`turnId`，补充每条回复仅显示一次的断言；最后6项回执包含该修订。原正常服务、数据库与既有进程保持。

正常页面规格首轮退出1：新增用例在Agent选择处超时，6项中1项失败、5项未执行。原路由夹具在AuthProvider取得会话前挂载Chat，目录读取缺少当前CSRF；生产App按认证完成状态挂载业务页面。夹具已改为等待原AuthProvider完成会话读取，失败回执保留于`frontend/output/chat-agent-model-20261113/current-route-review/`，修订后结果独立登记。

随后两次运行分别因夹具回读固定旧Voice、缺少现有插件安装目录响应退出1，各执行1项并停止其余5项。夹具现按原`ThreadSelectVoice`行为回读已提交的Voice，返回记录的公开消息，并为`/api/claude-plugins/installations`提供原空列表DTO。两次失败分别保留于`current-route-final/`和`current-route-confirmed/`；断言继续要求当前Agent、原请求、零未登记接口和零运行错误。
