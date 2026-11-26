<!-- [Sync] 2026-11-13: 复核正常ChatView／ChatPanel接线，沿原Agent投影和场景状态关闭菜单、返回重读模型。 -->
<!-- [Sync] 2026-11-13: 合并Agent／工具触发器，登记SelectModel迁移、IM数据适配及保存状态。 -->
<!-- [Input] Chat专项交互稿、现有AIInputDock／DeckChatSelector与MCP API。 -->
<!-- [Output] 双端组件职责、接口、提交语义、失败恢复与接入图。 -->
<!-- [Pos] Chat工具输入栏开发设计；权限策略与原生播放器由各专项维护。 -->
<!-- [Sync] 2026-11-13: 独立定义Chat组件开发合同，保留原Thread及队列协议。 -->

# Chat Agent、工具与模型输入栏：开发设计

产品规则、桌面／窄屏骨架及用户时序见[Chat专项设计](../../prd/chat/agent-tool-composer.md)。远程连接管理见[资源前端接线](mcp-tool-management-frontend.md)，音频问答和媒体结果见[音频前端接线](../multi-platform/mobile-clock-audio-frontend.md)。

## 模块与所有权

| 模块 | 输入与职责 | 输出 |
| --- | --- | --- |
| `ChatView`／Native App | 原Deck目录、所选Agent、Thread与发送协调 | 沿原入口提交消息；保留原Thread、Claude会话与队列 |
| `ComposerToolsMenu`／`ComposerAgentSelector`（Web／Native） | 原DeckChatSelectorProps目录、selectedAgentId、onChange；统一入口与Agent子菜单 | 原`{deckId, agentId}`回调；原Thread范围保持 |
| `AIInputDock`／`useComposerDraft` | 草稿、附件、权限模式与原发送／停止回调 | 原`onSendMessage(message, files, toolChoice)` |
| `SelectModel`（Web／Native） | IM目录、保存值、loading／saving／error与选择回调 | 模型搜索、分组、当前勾选和响应式面板 |
| `ComposerModelSelector` | 原`useModelConfig`与平台transport | 原模型目录／偏好读取和保存、未确认恢复、发送阻塞反馈 |
| `ComposerPopover` | 原触发元素、焦点、关闭与内容 | 桌面Popover／窄屏Sheet边界 |
| `useClaudeMcpResources` | 原capability、列表与操作API | Server状态；按revision更新enabled；失败／冲突恢复 |
| Service／Runner | 原actor/workspace配置快照 | 当前turn冻结的远程MCP配置；原工具权限判定 |
| 音频MCP／问答组件 | 显式启用的平台工具与媒体参数 | AskUserQuestion；回答匹配后返回播放请求或declined |
| 播放器适配器（未实现） | 同一调用的播放请求及本机媒体资源 | 实际准备／播放状态，再更新系统控件 |

Agent、MCP、UI组件分别拥有执行决策、工具协议、呈现与用户输入。前端组件通过原工具确认入口提交回答，原MCP处理器返回结果；播放器按结果执行本机媒体操作。

## 参考与选型

已读取Better Chatbot的`ChatBot → PromptInput → ToolSelectDropdown`调用链，采用输入正文与底部工具行、Agent图标及选中反馈、服务分组和搜索。现行`MarkdownInputEditor`、`useComposerDraft`、Agent目录／回调及MCP API继续承担原职责。接入层沿现有DTO，避免引入外部项目的会话store、认证、API和服务端执行协议。

两个方案中，整体移植外部ChatBot会覆盖原Thread恢复、队列和权限通道；选定的组件重构复用原调用边界。工作流、工具预设及多Agent控制退出本轮。

## 工作流与工具预设的源码核对

| 核对项 | 代码事实 | 本轮处理 |
| --- | --- | --- |
| 参考项目工作流 | `tool-select/index.tsx`渲染`WorkflowToolSelector`，以独立工作流目录和`onSelectWorkflow`选择 | 只采用交互结构；当前Chat没有对应目录和发送处理 |
| 参考项目预设 | `ToolPresets`保存`allowedMcpServers`与`allowedAppDefaultToolkit`的命名组合 | 当前仓库未发现toolPresets状态、CRUD或应用预设入口 |
| 当前Chat请求 | [buildClaudeChatRequest](../../../frontend/app/_dream/lib/claude-chat-request.ts)固定生成空`allowedMcpServers`与`allowedAppDefaultToolkit`，消息走原Claude入口 | 这些兼容字段不构成已接入的可选工具预设协议；本轮保持原请求 |
| 当前工作流 | [storyWorkspaceApi](../../../frontend/app/_dream/api/storyWorkspaceApi.ts)的`WorkflowRun`携带运行、Plugin及执行状态；原Chat元数据记录workflowRunId来源 | Dream执行业务按原入口维护；Chat工具菜单不增加工作流选项 |
| 当前选择能力 | `DeckChatSelector`与`useComposerSkills`提供Agent、原Skill入口，`useComposerDraft`维护调用模式 | 复用这些已接入能力并增加原MCP管理入口 |

本轮范围基于源码核对收敛。参考[WorkflowToolSelector](https://github.com/keinsaasforever/better-chatbot/blob/main/apps/web/src/components/tool-select/workflow-tool-selector.tsx)与[ToolPresets](https://github.com/keinsaasforever/better-chatbot/blob/main/apps/web/src/components/tool-select/tool-presets.tsx)已分别读取，外部store与目录服务保持原项目所有。

## 接口与时序语义

1. Agent：目录继续由原caller读取；合并触发器接收`agentSelection: DeckChatSelectorProps`。`onChange`继续原页面回调，正文和附件保持；已有关联Thread沿原Deck内选择范围处理，菜单不重建Thread。
2. 工具模式：`ToolChoice`沿现有`auto/manual/none`协议，当前UI保留原自动／手动选项；`im_full_access_enabled`沿原全访问展示。AskUserQuestion回答仍通过原通道提交。
3. 远程服务：`getClaudeMcpCapability`与`listClaudeMcpServers`按需读取；面板搜索使用返回的名称。启停调用`updateClaudeMcpServer(server, changes)`，携带原`expected_revision`和完整配置，仅改变`enabled`。缺少可更新配置的来源显示管理入口。
4. 范围：服务开关为原账户／工作区的持久配置，后续turn读取快照；前端不向Chat请求发送远程Server配置或新server白名单。运行中的turn保持原快照。
5. 平台工具：`ClaudeAgentRequestBody.tools`默认空，固定type为`mobile_clock_audio`。App播放器能力及选择接线完成后才可显式携带；当前缺少原生播放器回执，UI保持禁用。
6. 音频：固定MCP名为`mcp__mobile_clock_audio__ask_user`，Low-Sensitivity。工具PreToolUse仍等待AskUserQuestion答案，原Store按调用ID匹配。`playback_requested`到达后再交接播放器；单凭提交答案不展示已播放。
7. 发送：保留原草稿清空／失败还原、附件上传阻塞、正在执行时排队、无草稿时Stop和stopPending。菜单操作不调用send或cancel。

## 组件接入拓扑

```mermaid
flowchart TD
    C[ChatView／Native App] --> D[AIInputDock]
    C --> Catalog[原Deck目录与选择回调]
    Catalog --> T
    T --> AgentMenu[ComposerAgentSelector]
    AgentMenu -->|原onChange| C
    D --> Draft[useComposerDraft]
    D --> T[统一Agent与工具菜单]
    D --> Model[SelectModel Web／Native]
    Model --> MC[ComposerModelSelector]
    MC --> ModelConfig[原useModelConfig]
    ModelConfig --> Models[原gatewayModelsApi／system-config]
    T --> H[useClaudeMcpResources]
    H --> API[原claudeMcpApi]
    API --> Config[原账户／工作区MCP配置]
    Draft --> Submit[原发送／队列入口]
    Submit --> S[Service／Runner]
    Config --> S
    S --> M[MCP工具]
    M --> Q[原ToolConfirmationDock]
    Q --> Answer[原回答接口／Store]
    Answer --> M
    M --> Result[原工具结果]
    Result -. 音频接线待实现 .-> Player[播放器适配器]
```

## 正常开发时序

```mermaid
sequenceDiagram
    actor U as 用户
    participant D as AIInputDock
    participant T as ComposerToolsMenu
    participant H as useClaudeMcpResources
    participant API as claudeMcpApi
    participant R as Service／Runner
    U->>T: 打开当前Agent入口并搜索服务
    T->>H: 读取原列表
    H->>API: capability／list
    API-->>T: Server、enabled、revision
    U->>T: 切换enabled
    T->>H: 当前Server与目标值
    H->>API: update，expected_revision和完整配置
    API-->>H: 保存后的Server
    H-->>T: 确认状态
    U->>D: 原发送操作
    D->>R: message／files／tool_choice
    R->>R: 原actor/workspace MCP配置快照
    Note over D,R: 队列、Thread身份与原工具权限合同保持
```

## 异常与恢复

```mermaid
sequenceDiagram
    actor U as 用户
    participant T as Chat工具菜单
    participant H as useClaudeMcpResources
    participant API as 原MCP API
    U->>T: 保存服务启停
    T->>H: 当前配置与目标enabled
    H->>API: PATCH，expected_revision
    alt 409
        API-->>H: 版本冲突
        H->>API: 读取最新列表
        H-->>T: 最新已确认状态与冲突反馈
        T-->>U: 核对后重新选择
    else 网络／权限失败
        API-->>H: 错误
        H-->>T: 保留已确认状态并解除busy
        T-->>U: 错误与重试
    end
    U->>T: 关闭或切换账户
    T->>T: 关闭面板；旧组件回执不发布到新owner
    Note over T,API: 草稿、附件与原Thread保持
```

## 状态与验证

工具面板采用产品稿的`Draft/Tools/Loading/Saving/Error`状态图。远程配置的default为原创建默认启用，desired为目标enabled，effective为保存后的状态及后续turn各自取得的快照，revision为原Server.revision。凭据与工具权限沿原服务保存；前端无新增数据库字段。

技术验证覆盖真实组件的搜索、开关API请求与expected_revision、409恢复、失败重试、关闭后草稿保持、发送／停止与窄屏边界。Native完成类型验证后单列触摸／键盘与真机验收。音频播放器、系统组件、后台计算和真实MCP连接／模型验收按专项记录，文档与隔离UI用例分别留存结果。

## SelectModel源码迁移与数据适配

[来源与MIT声明](../../../frontend/third-party/better-chatbot/README.md)登记Git blob SHA及完整源码快照。迁移`renderModelItem`的唯一选择值／当前勾选／禁用项、`modelCommand`的搜索／分组结构、桌面Popover与窄屏Drawer交互；IM适配器替换原`appStore`、query hooks及UI primitives。原目录与配置实现继续由`gatewayModelsApi`和`useModelConfig`所有。

| 项目 | 现有IM合同 | 迁移接线 |
| --- | --- | --- |
| 目录 | `fetchGatewayModels`，原`GET /api/gateway/models`及严格GatewayModel DTO | 只呈现已解析的聊天候选，保留callable／upgradeHint／defaultModelAlias |
| 当前偏好 | 原`GET /api/system-config`，`resolveGatewayModelSelection` | 显式保存值优先；缺省沿原有效默认值；失效值给出原恢复操作 |
| 保存 | 原`useModelConfig.handleModelChange`，`PUT /api/system-config`仅`{model: alias}` | 原保存结果判定、403／409、未确认状态与重新读取保持 |
| 反馈 | `selectedModel/configLoading/saving/modelSaveUnconfirmed/modelStatus` | 保存中或结果未确认时，经原draft disabled入口阻塞发送；编辑与Stop保持 |
| 保存后 | 原onConfigSaved | Web重新读取原ChatPanel配置；Native调用原setup.refreshConfig |
| Agent目录 | 原caller读取与Thread上下文 | 当前Agent触发器＋Agent子菜单；原onChange载荷与范围保持 |
| 平台 | Web原fetch；Native原clientFetch | Cookie／CSRF／错误DTO保持；无新后端路由或偏好字段 |

模型选择显示当前偏好，实际turn模型继续由原后端catalog/entitlement解析。Chat消息、Thread、队列、MCP与平台tools字段保持原协议。IM DTO缺少参考项目的自动路由资格、本地模型配置、价格与榜单信息，对应UI沿IM实际能力呈现。

模型配置沿原默认值、待保存选择、服务器确认值与读取代次维护；公开接口保持原字段。原`useModelConfig`的模型加载代次与保存未确认状态负责恢复，迁移组件不新增公开revision。

正常Web入口由`ChatView`装配：新建会话的`AIInputDock`使用完整原Agent目录，已有会话经`ChatPanel`传入当前Deck的Agent目录并设置`allowNone=false`。当前名称、图标和范围复用原`threadVoiceEntry/badgeDeckId`，旧Thread缺少Deck／Voice字段时沿原`Voice.thread_id`匹配展示。选择回调更新原`selectedDeckId/selectedAgentId`；新建Thread沿`createChatThread`，后续消息沿`buildClaudeChatRequest`，保持`deckId/voiceId`与Thread ID。模型保存确认后，`ChatPanel`重新读取原配置；Native沿`setup.refreshConfig`。

保留挂载的Web路由将`ChatView.isVisible`经`ChatPanel.active`与`AIInputDock.active`传至两个菜单。场景隐藏时关闭浮层；返回时`ComposerModelSelector`推进原`modelLoadNonce`重新读取配置和目录，等候中的保存先完成。Native复用原场景`active`执行同一读取规则；原Thread、草稿、附件及流生命周期各自由原所有者维护。

### 正常模型调用时序

```mermaid
sequenceDiagram
    actor U as 用户
    participant C as ChatView／ChatPanel
    participant D as AIInputDock
    participant V as SelectModel
    participant M as ComposerModelSelector／useModelConfig
    participant G as 原gatewayModelsApi
    participant S as 原system-config
    participant R as 原Chat发送／后端模型解析
    M->>G: fetchGatewayModels
    M->>S: GET当前配置
    G-->>M: 原callable目录与defaultModelAlias
    S-->>M: 原已保存model
    M-->>V: 当前值与可选项
    opt 离开Chat后返回
        C->>D: active=false，关闭Agent与模型面板
        C->>D: active=true
        D->>M: 保存完成后推进原modelLoadNonce
        M->>S: GET当前配置
        M->>G: fetchGatewayModels
        S-->>M: 当前已保存model
        G-->>M: 当前目录
        M-->>V: 更新当前名称与选项
    end
    U->>V: 搜索并选择可调用alias
    V->>M: 原handleModelChange
    M->>D: saving，保留编辑与Stop并等待发送
    M->>S: 原PUT，仅model字段
    S-->>M: 已保存model回执
    M->>D: onConfigSaved／解除发送阻塞
    U->>D: 原发送操作
    D->>R: 原message／files／toolChoice
    R->>R: 原模型与资格解析
```

### 模型异常与恢复

```mermaid
sequenceDiagram
    actor U as 用户
    participant V as SelectModel
    participant M as 原useModelConfig
    participant D as 原useComposerDraft
    participant S as 原system-config
    U->>V: 选择可调用模型
    V->>M: 原保存入口
    M->>S: PUT model
    alt 明确拒绝或版本／状态变化
        S-->>M: 原403／409
        M-->>V: 原反馈、旧值或重读
    else 保存结果未确认
        S-->>M: 网络失败或未确认回执
        M->>D: modelSaveUnconfirmed阻塞发送
        M-->>V: 保留草稿、重新读取入口
        U->>V: 重新读取
        V->>M: 原modelLoadNonce
        M->>S: GET当前配置
        S-->>M: 原已保存model
        M->>D: 原状态确认后恢复发送
    end
```

Agent／播放与模型偏好状态分别见[产品稿状态图](../../prd/chat/agent-tool-composer.md#模型偏好状态转换)。迁移前原文与图示见[历史稿](chat-agent-tool-composer-before-agent-model-20261113.md)。本轮验证见[执行记录](../../exec/chat-agent-model-composer-20261113.md)。
