<!-- [Input] 2026-11-13拆分前现行前端稿。 -->
<!-- [Output] 原文与六幅图逐字保留。 -->
<!-- [Pos] 历史原文；现行职责见Chat及资源专项。 -->

# Chat拆分前完整原文

````markdown
<!-- [Sync] 2026-11-12: 补Web/App共用MCP卡片管理与加载职责；音频仍为App设备工具，默认关闭。 -->
<!-- [Input] Web/App资源连接卡片需求、原MCP管理能力、端侧音频问答与v4.2角色。 -->
<!-- [Output] 两端MCP管理/加载接口、平台工具选择、音频问答与播放器组件接线设计。 -->
<!-- [Pos] 前端接入设计；媒体预览/播放器新增接线待实现，后端已接入。 -->
<!-- [Sync] 2026-11-04: 低敏工具无授权弹窗，AskUserQuestion收集播放选择，成功工具结果驱动播放器。 -->

# 工具连接与App时钟音频前端接入设计

## 背景与问题

后端提供默认关闭的`mobile_clock_audio`平台工具组，工具名为`mcp__mobile_clock_audio__ask_user`。Agent提交媒体信息时，原运行时使用AskUserQuestion收集用户选择，随后执行MCP并返回结果。前端负责媒体问答预览及播放器显示，MCP注册与Agent调度由后端承担。

产品规则与桌面／窄屏骨架归[独立组件设计](../../prd/mobile-app/ios-system-player.md)，schema、低敏分类和后端接线归[开发合同](ios-system-player-technical.md)。本轮新增前端媒体组件与原生播放器均待实现。

## 目标与边界

正常显示v4.2脸型交互主体。App调用方明确启用且本机播放器能力就绪时，发送`tools: [{"type":"mobile_clock_audio"}]`；缺省false时省略或传空数组。Web与App的工具连接卡片共用下文管理交互；音频type只由App设备工具选择提供，原Editor及其他工具继续沿原配置和tool_choice。

音频工具为Low-Sensitivity Tools，工具授权弹窗为零。AskUserQuestion独立收集本次播放选择，auto/manual/full-access均保留问答。组件不设置权限策略、不执行Agent循环、不注册MCP、不签发播放批准回执。

## 概念与规则

### 模块、输入与输出

| 模块 | 输入 | 责任／输出 |
| --- | --- | --- |
| 建议调用方选项 | enableMobileClockAudio缺省false，原Native播放器能力事实 | 普通发送与排队的当次tools选择 |
| 原Chat请求／观察 | 原消息、Thread、tools和原事件 | 原鉴权、保存、Stop、草稿和恢复；零新增SSE |
| 原AskUserQuestion区域 | 音频工具当前input中的questions、媒体及toolCallId | 展示问题/选项，提交answers或取消；不再显示独立工具批准 |
| 建议音频问答内容组件 | 音频列表、原因、队列影响 | 原问题内的媒体预览，原表单继续管理选项和提交 |
| 建议结果消费器 | 当前音频调用的tool-output-available、isError、output | 匹配与校验；playback_requested交播放器，declined保持原呈现 |
| 原v4.2组件 | 原时钟／心情／主题 | 默认主体与原交互，不消费Agent文本播放指令 |
| 建议NativeMediaPlayback | 本次播放请求及当前资源上下文 | 认证读取、实际准备与播放、真实状态 |
| 建议IOSSystemMediaAdapter | 角色及实际媒体快照 | 系统状态投影，不持有MCP或Agent，不直接读取媒体 |

### 请求构造

```ts
type AppAudioOptions = { enableMobileClockAudio?: boolean }; // default false
// 建议：在原请求构造处投影；本轮前端接线待实现。
const tools = options.enableMobileClockAudio === true && audioPlaybackReady
  ? [{ type: 'mobile_clock_audio' as const }]
  : [];
```

[useNativeChatThread](../../../frontend/app/_dream/components/chat/useNativeChatThread.native.ts)及原共享请求构造传递当次选择，发送与排队保持一致。下一条消息缺省关闭，重连只观察原运行。平台能力来自原App/Native入口，UA猜测与部署环境名称不参与选择。设备工具卡复用原设置资源链接页，范围为本次App运行；新增卡片选择与请求投影待实现，不增加问答前的授权确认。

### AskUserQuestion输入与回答

原[toolConfirmation](../../../frontend/app/_dream/components/chat/toolConfirmation.ts)与后端Store已经通过`__ask_user`后缀识别问答。音频工具采用该命名规则，原[ToolConfirmationDock.native](../../../frontend/app/_dream/components/chat/ToolConfirmationDock.native.tsx)和[AskUserQuestionUI](../../../frontend/app/_dream/components/chat/AskUserQuestionUI.tsx)可沿原问题/选项/answers协议处理；媒体预览呈现分支待实现。

Runner根据媒体信息生成固定问题“是否在这台设备播放以下音频？”，选项“播放／不播放”，无默认选择。Agent自填questions/answers在询问前移除。问题同当前Thread、turn、toolCallId及媒体参数fingerprint绑定。

媒体预览位于原问题区域，显示音频标题、来源、类型、已知时长、原因、接收“这台设备”及替换／追加影响。长列表独立滚动，选项与“取消／提交选择”保持可见；未知时长省略数字。角色与已有播放保持。

原`confirmToolCall`与`POST /api/claude-agent/tool-confirm`继续提交：

```json
{"thread_id":"<原Thread>","tool_call_id":"<本次调用>","approved":true,"answers":{"q0":"播放"}}
```

approved在此表示提交回答。用户选择“不播放”时同样提交approved:true与对应answers，MCP返回declined；取消问答时approved:false，原调用被取消。原Store验证必答与选项，将q0映射为原问题文本；Runner回填updatedInput.answers后执行MCP。无第二个工具授权弹窗、接收步骤、新pending Store或媒体批准HTTP。

提交回答成功后保持“等待工具结果”，新播放器仍为零。前端不从approved布尔值推断用户选择播放，不从低敏或full-access推断答案。

### 原工具结果消费

结果来自原tool-output-available。工具名可通过先前tool-input事件按toolCallId取得，不能依赖结果事件一定携带toolName。建议消费器位于App宿主的原事件观察路径，页面仅订阅状态。

消费条件：当前请求显式选中音频工具；owner/runtime、Thread、turn、toolCallId均匹配；工具名精确为`mcp__mobile_clock_audio__ask_user`；isError为false；按原文本/内容块归一化读取本合同JSON。

| 结果 | 组件处理 |
| --- | --- |
| type为mobile_clock_audio，status为playback_requested，choice为播放，媒体与当前调用相符 | 单次消费，展示播放器准备，再交原生认证读取与实际播放 |
| status为declined，choice为不播放 | 记录已回答，保持角色／已有播放，新播放器为零 |
| 取消、超时、Stop、工具错误或无有效结果 | 沿原问答／工具反馈，保留原任务结果，不开始播放 |
| 历史加载、重新挂载、重复或旧代次事件 | 不创建新播放器；当前已消费调用返回原会话，同ID异内容拒绝 |

原资源准备继续核对会话、Thread归属、实际媒体类型和可播性。MCP播放请求与实际播放开始分开。身份或执行情况无法核实时保留原结果，零自动重发与零自动播放。

### 显示与生命周期

默认角色使用原v4.2路径、时钟与心情交互。问答和等待工具结果期间保持主体；资源准备、播放、暂停、失败在收到播放请求后呈现。结束或关闭返回角色。系统入口按允许生命周期显示并返回App，零封面点击代答。

原Agent Stop取消原任务与pending问题；已成功交付播放器的媒体沿独立生命周期。等待用户时释放无实际进展的计算许可，资源准备按独立适用许可执行。原生播放和系统音频能力不承载前面的通用Agent计算。

## 正常接入时序（前端新增接线待实现）

```mermaid
sequenceDiagram
    actor U as 用户
    participant A as Agent与原Runner
    participant Q as 原AskUserQuestion
    participant M as 音频MCP
    participant R as 原v4.2主体
    participant F as 结果消费器（待实现）
    participant P as 原生播放器（待实现）
    A->>A: tools显式启用低敏音频工具
    A->>Q: questions、媒体及当前调用身份
    Q-->>U: 媒体预览，播放／不播放
    R-->>U: 保持角色与已有播放
    U->>Q: 选择播放并提交answers
    Q->>A: 原Store校验并回填answers
    A->>M: 执行音频工具
    M-->>F: 原工具结果playback_requested
    F->>F: 当前调用、媒体及单次消费校验
    F->>P: 展示准备并读取原资源
    P-->>U: 实际播放及控制
    P->>R: 结束或关闭，恢复角色
```

## 异常与恢复时序

```mermaid
sequenceDiagram
    actor U as 用户
    participant Q as 原AskUserQuestion
    participant A as 原Runner与音频MCP
    participant F as 结果消费器（待实现）
    participant P as 原生播放器（待实现）
    alt 用户选择不播放
        U->>Q: 提交不播放答案
        Q->>A: 原answers
        A-->>F: 正常工具结果declined
        F-->>U: 保持角色或旧播放
    else 取消、超时或Stop
        Q->>A: 原取消或无有效回答
        A-->>F: 取消／错误反馈，新播放为零
    else 播放请求后资源失败
        A-->>F: playback_requested
        F->>P: 原权限读取与实际准备
        P-->>U: 实际失败与关闭入口
    end
    U->>F: 重开／恢复订阅
    F->>A: 读取原历史与pending
    Note over F,P: 历史结果不创建新播放器
```

## 状态转换

```mermaid
stateDiagram-v2
    [*] --> Role
    Role --> Asking: 当前音频工具发起问答
    Asking --> WaitingTool: 用户播放答案已提交
    Asking --> Role: 不播放、取消、超时或Stop
    WaitingTool --> Preparing: 本次playback_requested
    WaitingTool --> Role: 工具错误
    Preparing --> Playing: 实际可播
    Preparing --> Error: 资源失败
    Playing --> Paused: 暂停
    Paused --> Playing: 同会话继续
    Playing --> Role: 结束或关闭
    Paused --> Role: 关闭
    Error --> Role: 关闭
```

## 开发顺序与验收

| 工作项 | 责任位置与验收 |
| --- | --- |
| tools投影 | 原Native请求构造；默认/Web关闭，显式启用、排队与下一条关闭一致 |
| 问题内媒体呈现 | 原AskUserQuestion区域；媒体、原因、队列影响、滚动与必答；无工具授权步骤 |
| 回答与结果消费 | 原Store/answers及原工具流；不播放为declined，取消为原取消；重复/历史/旧账户零新播放 |
| 播放器与系统 | 原App宿主及原生媒体对象；资源权限、文件使用期、真实状态与结束回角色 |
| 相邻业务 | 原AskUserQuestion、Editor批准、tool_choice/full-access、Stop、草稿与Thread保持 |

后端专项、文档原型、前端功能、Simulator、真机及真实资源播放分别留证。当前前端交付为设计。


## Web与App共用的MCP管理交互（2026-11-12）

### 需求来源与范围修订

[Notion新增ui交互](https://app.notion.com/p/40b30b7547c380cd9930c384ab35023c#41530b7547c380f48038c931c30580b8)指定两端采用连接工具入口、已连接卡片网格、状态及断开操作。原图已核对，卡片属于MCP服务连接管理。[产品规则与两端骨架](../../prd/resource-connections/mcp-tool-management.md)维护页面；[补充前原文与三图](history/mobile-clock-audio-frontend-before-mcp-management-20261112.md)保留。

当前复用原Settings资源链接页及两个连续区域；原Notion/飞书连接器保持原owner。新MCP网格、快捷启停及设备工具卡为建议、未实现。音频MCP的已有后端入口与本轮UI设计分开验收。

### 三条状态链

| 状态链 | 所有者与输入 | 输出及边界 |
| --- | --- | --- |
| 远程MCP管理 | 原ClaudeMcpResourceSection／useClaudeMcpResources；capability与Server列表 | 当前配置、认证、enabled与revision；列表不逐卡discovery |
| 当次Agent加载 | 原Service的actor/workspace快照与原Runner | 后端读取enabled服务和原凭据，冻结当前turn的claude_mcp_servers；配置更新不热修改运行中的turn |
| 设备音频选择 | 建议App内owner/runtime作用域内的选择状态及原Native能力事实 | 默认空；显式选择且能力就绪时在发送/排队携带mobile_clock_audio；Web不发送该type |

`ClaudeAgentRequestBody.tools`继续只选择后端固定平台type。远程MCP服务由原管理API配置和启停；浏览器不传MCP配置、连接URL、env、凭据、schema或自选远程server列表到Chat请求。公共MCP与Editor基线按原配置保留。

原MCP Apps使用策略继续控制工具结果内的App能力，`ClaudeMcpAppSettings`的default/desired/effective/revision沿原合同。音频设备选择使用本次App运行中的本机状态，零新增数据库schema；这两类状态独立。

### 界面与源码接入

| 模块 | 当前源码与建议改动 |
| --- | --- |
| 原设置入口 | [Settings PRD](../../prd/Settings.md)的资源链接页；原ConnectorSettingsSection保留远程/本地连续结构 |
| 服务卡片 | [Web列表](../../../frontend/app/_dream/components/claude-mcp/ClaudeMcpResourceSection.tsx)与[Native列表](../../../frontend/app/_dream/components/claude-mcp/ClaudeMcpResourceSection.native.tsx)改为同一信息结构的卡片；沿原主题与各端布局 |
| 数据与认证操作 | [useClaudeMcpResources](../../../frontend/app/_dream/hooks/useClaudeMcpResources.ts)继续管理列表、原新增、授权operation、取消、退出及移除；不建立第二个连接store |
| 详情与工具清单 | 原ClaudeMcpServerDetailPage与[useClaudeMcpServer](../../../frontend/app/_dream/hooks/useClaudeMcpServer.ts)保持自动cache-first inventory与原策略保存；列表不增加批量探测 |
| 请求边界 | [claudeMcpApi](../../../frontend/app/_dream/api/claudeMcpApi.ts)及Native注入transport保持原session/CSRF与DTO；新增卡片只调用原公开边界 |
| 设备工具卡 | 建议原本地资源区接入App音频能力状态；默认关闭，能力未就绪禁用，Web只读展示仅App可用 |
| Agent/问答/播放器 | 继续本稿原音频时序；启用工具只改变可见性，AskUserQuestion和实际媒体状态分别处理 |

列表图标优先使用已有安全展示数据，缺图显示原通用工具图标；计数由当前列表计算。截图中的Gmail/GitHub等应用不成为静态连接记录或额外集成依赖。

### 接口与并发

- `getClaudeMcpCapability / listClaudeMcpServers`保留原页面读取；连接不支持时显示原能力反馈。当前列表状态来自后端记录，陈旧信息保留最近状态，零“配置存在即已连接”推断。
- “连接工具”沿`configureClaudeMcpServer`及原新增弹窗。成功后更新列表，授权采用原start/cancel/operation；认证方式由服务端判定，客户端不选择凭据策略。
- 卡片启停建议复用`updateClaudeMcpServer(server, changes)`。当前helper提交完整配置及expected_revision，changes取当前回执中的配置，仅改变enabled；缺少id/revision/可编辑配置时回详情，不能猜测默认字段。
- 保存中保留当前已确认状态并展示操作进度。409读取原Server最新revision并保留用户期望，提示核对后显式重试；失败不更新已确认enabled。旧owner、旧revision及旧请求回调不覆盖新卡片。
- 停用保留配置和认证，下一turn快照排除该服务。退出认证调用原logout；移除按原removable和确认执行。当前running turn保持原快照，原Stop单独处理。
- 详情inventory沿原cache-first请求，重建和失败恢复沿原操作。禁止通过列表轮询或客户端“重新加载所有MCP”形成额外远端调用。

### 默认、期望、实际与版本

| 状态 | 远程服务 | 设备音频工具（建议） |
| --- | --- | --- |
| default | 原CreateServerRequest.enabled缺省true，revision取实际配置回执 | tools为空，设备选择关闭 |
| desired | 当前用户待保存的enabled | 当前owner/runtime中的选择 |
| effective | 后端已保存状态及当前turn冻结快照各自维护；缺少turn回执时只展示已启用 | Native能力可用、当次选择和tool_choice共同决定本次可提供工具；不从选择推断播放器已可用 |
| revision | Server.revision、credential_revision由原后端维护 | 本地选择代次与原提交身份绑定，仅用于快照/迟到事件校验，不增加公开DTO字段 |

设备选择在本次App运行内保存，owner变化、进程重开及能力失效回到关闭。发送和排队在原提交边界捕获选择快照；之后修改选择只影响后续提交。前端显示“已启用”并保留对应连接／授权状态，设备卡显示“已选择”；缺少当前turn MCP加载回执时，不宣称本轮加载成功。

### 平台与未完成边界

Web和App共享服务管理含义及原API；Native继续注入现有transport和外链授权入口。传输方式依据原capability和经核对的本地执行能力呈现；当前DTO缺少某项端侧执行资格时列为接入前置，不能因Web支持stdio就允许App执行任意本地命令。

[Notion未完成功能边界](https://app.notion.com/p/40b30b7547c380cd9930c384ab35023c#41530b7547c380f48038c931c30580b8)中Web分发Bridge、多Agent生命周期、IDENTITY/USER/HEARTBEAT仅记录为后续研究。当前页面不提供设备发现、跨端调度或心跳启停，不把MCP服务卡创建等同于创建Agent。

### 正常管理与加载时序（新卡片接线待实现）

```mermaid
sequenceDiagram
    actor U as 用户
    participant L as ClaudeMcpResourceSection（Web／Native）
    participant H as useClaudeMcpResources
    participant API as 原claudeMcpApi
    participant D as 原详情／inventory
    participant A as 原Service／Runner
    U->>L: 打开资源链接
    L->>H: 原capability与列表读取
    H->>API: 原认证请求
    API-->>L: 实际Server状态、enabled与revision
    L-->>U: 卡片网格、计数及连接工具入口
    U->>L: 连接工具
    L->>H: 原新增表单提交
    H->>API: configureClaudeMcpServer
    API-->>L: 实际配置／授权状态
    U->>L: 管理某服务
    L->>D: 原详情与cache-first清单
    U->>L: 启用／停用（卡片接线建议）
    L->>API: 原update，expected_revision
    API-->>L: 新enabled与revision
    U->>A: 后续发送一次原任务
    A->>A: 原actor/workspace MCP快照
    A-->>U: 原工具调用与结果；当前turn按冻结快照执行
```

### 失败与恢复时序

```mermaid
sequenceDiagram
    actor U as 用户
    participant L as 服务卡片（建议）
    participant API as 原MCP管理接口
    participant Auth as 原授权operation
    U->>L: 改变服务enabled
    L->>API: 原expected_revision更新
    alt 保存成功
        API-->>L: 新状态及revision，更新已确认卡片
    else 版本冲突
        API-->>L: 原冲突错误
        L->>API: 原Server读取最新版本
        L-->>U: 保留期望，核对后显式重试
    else 网络或权限失败
        API-->>L: 原错误
        L-->>U: 保留原已确认状态与用户选择
    end
    U->>Auth: 取消本次授权
    Auth-->>L: 原operation状态与保留的连接记录
    U->>L: 返回／重新打开
    L->>API: 原当前账户列表
    Note over L,API: 旧账户与旧revision回执不覆盖当前卡片
```

### 配置与运行状态转换

```mermaid
stateDiagram-v2
    [*] --> Reading: 原账户读取
    Reading --> Listed: 当前服务列表
    Reading --> ReadError: 原读取失败
    ReadError --> Reading: 原恢复入口
    Listed --> Creating: 连接工具
    Creating --> Listed: 原配置或授权状态回执
    Creating --> Listed: 用户取消
    Listed --> Saving: 用户改变enabled
    Saving --> Listed: 新revision保存确认
    Saving --> Conflict: 原版本冲突
    Conflict --> Listed: 读取最新版本并保留期望
    Saving --> SaveError: 原失败
    SaveError --> Saving: 用户明确重试
    Listed --> Listed: 后续turn冻结当前已确认配置
```

### 评审与实施顺序

先复用现有两端列表与管理入口组织卡片，再补卡片保存反馈和App设备工具选择，最后对接音频问答媒体呈现与原生播放器。远程MCP现有DB快照读取和权限合同保持。新UI、当次选择与实际MCP加载分别验证；当前文档检查不形成真实连接或播放验收。

````
