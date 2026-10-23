<!-- [Sync] 2026-09-17: close Deck detail empty/raw legacy Memory projection parity. -->
<!-- [Sync] 2026-09-15: route current-user picture history reads through Admin Registry103. -->
<!-- [Sync] 2026-09-15: record Admin-owned Deck detail and unchanged legacy Memory projection. -->
<!-- [Sync] 2026-09-15: index five Admin Deck writes, shared schema gate and closed deletion feedback. -->
<!-- [Sync] 2026-09-15: index current Voice mutation design separately from retained Deck/Voice legacy flows. -->
<!-- [Sync] 2026-09-15: replace social flows with Admin while preserving the original in history. -->
<!-- [Input] Module business flows, current Admin consumers and byte-preserved pre-migration sequence source. -->
<!-- [Output] Module flow reference with explicit current ownership and retained migration dependencies. -->
<!-- [Pos] Sequence index; focused current designs own authentication, Session, Deck, preferences and social rules. -->
<!-- [Sync] 2026-10-23: 6.1 展开后台 Engine、栏目 Runner、统一 Agent 执行、转录校验和持久化优先的任务 SSE；原图保留于既有历史稿。 -->
<!-- [Sync] 2026-09-15: public user preferences use Admin; retain original whole source in history. -->

认证/Session/Deck的现行程序行为以[Admin交互](../architecture/admin-auth-data-interaction.md)和各功能稿为准；本稿其余尚未更新的旧issuer/直接SQL说明仅是迁移依赖，不作为现行规范。[原十模块时序原文](history/pre-admin-user-preferences-20260915/sequence-diagrams.md)字节保持；用户偏好正常、状态、失败和验收见[现行稿](user-preferences-current.md)。

Voice四公开mutation的现行正常、状态、失败与验收见[Voice CRUD现行稿](voice-crud-current.md)；下方模块8尚未更新的直接SQL只保留迁移依赖与历史流程。

<!-- [Input] Current Next.js Dream Web modules and Python business routes/services. -->
<!-- [Output] Current cross-module business sequence diagrams. -->
<!-- [Pos] Design-level sequence index; domain details remain in their focused documents. -->
<!-- [Sync] 2026-09-06: replace the retired Vite frontend label with the sole Next.js app/_dream source boundary. -->
<!-- [Sync] 2026-09-01: replace debounced random-Voice inspiration with manual persistent Suggestion Cells on one Session-owned Claude Thread. -->
<!-- [Sync] 2026-08-31: replace daily-picture generation with historical read-only Timeline access and remove its scheduler/runtime. -->


五公开Deck写操作的正常流程、状态、原错误/删除反馈与验收以[现行稿](deck-mutations-current.md)为准；尚未迁移的list/detail/create/default/安装metadata保留依赖。

# Ink & Memory — 业务功能模块时序图

> 本文档梳理了 Ink & Memory 项目的核心业务功能模块，并以 Mermaid 时序图形式呈现各模块的交互流程。

---

## 目录

1. [用户认证模块（注册 / 登录）](#1-用户认证模块)
2. [编辑器会话管理模块](#2-编辑器会话管理模块)
3. [历史语音评论兼容](#3-历史语音评论兼容)
4. [Writing 手动建议模块](#4-writing-手动建议模块)
5. [语音对话模块（Chat with Voice）](#5-语音对话模块)
6. [深度分析模块（回响 / 特质 / 模式）](#6-深度分析模块)
7. [历史图片读取模块](#7-历史图片读取模块)
8. [卡组与声音管理模块](#8-卡组与声音管理模块)
9. [好友系统模块](#9-好友系统模块)
10. [语音输入模块（WebSocket 语音识别）](#10-语音输入模块)

---

## 1. 用户认证模块

### 1.1 用户注册

```mermaid
sequenceDiagram
    actor User as 用户
    participant FE as Frontend
    participant API as Backend API
    participant Auth as auth.py
    participant DB as database.py

    User->>FE: 填写邮箱/密码，点击注册
    FE->>API: POST /api/register {email, password, display_name}
    API->>Auth: hash_password(password)
    Auth-->>API: password_hash
    API->>DB: create_user(email, password_hash, display_name)
    DB-->>API: user_id
    API->>DB: auto_fork_system_decks(user_id)
    Note over DB: 为新用户自动克隆系统卡组
    API->>Auth: create_access_token(user_id, email)
    Auth-->>API: JWT token (有效期 7 天)
    API-->>FE: {token, user: {id, email, display_name}}
    FE->>FE: 存储 token 至 localStorage
    FE-->>User: 注册成功，进入主页
```

### 1.2 用户登录

```mermaid
sequenceDiagram
    actor User as 用户
    participant FE as Frontend
    participant API as Backend API
    participant Auth as auth.py
    participant DB as database.py

    User->>FE: 填写邮箱/密码，点击登录
    FE->>API: POST /api/login {email, password}
    API->>DB: get_user_by_email(email)
    DB-->>API: user record (含 password_hash)
    API->>Auth: verify_password(password, password_hash)
    Auth-->>API: true / false
    alt 密码错误
        API-->>FE: 401 Invalid email or password
        FE-->>User: 提示登录失败
    else 密码正确
        API->>DB: get_user_decks(user_id)
        alt 用户无卡组（老用户首次迁移）
            API->>DB: auto_fork_system_decks(user_id)
        end
        API->>Auth: create_access_token(user_id, email)
        Auth-->>API: JWT token
        API-->>FE: {token, user: {id, email, display_name}}
        FE->>FE: 存储 token 至 localStorage
        FE-->>User: 登录成功，进入主页
    end
```

### 1.3 JWT 鉴权（通用依赖）

```mermaid
sequenceDiagram
    participant FE as Frontend
    participant API as Backend API
    participant Auth as auth.py

    FE->>API: 任意受保护请求（携带 Authorization: Bearer <token>）
    API->>Auth: extract_token_from_header(authorization)
    Auth-->>API: token string
    API->>Auth: verify_access_token(token)
    Auth-->>API: {user_id, email} 或 None
    alt token 无效或过期
        API-->>FE: 401 Unauthorized
    else token 有效
        API->>API: 执行业务逻辑（注入 current_user）
        API-->>FE: 正常响应
    end
```

---

## 2. 编辑器会话管理模块

### 2.1 应用启动 — 加载会话

```mermaid
sequenceDiagram
    actor User as 用户
    participant FE as Frontend
    participant Hook as useSessionLifecycle
    participant Admin as Admin DTO/Service/Repository
    participant API as Backend API
    participant DB as database.py

    User->>FE: 打开应用
    FE->>Hook: 初始化 EditorEngine
    Hook->>API: GET /api/sessions?timezone=...
    API->>DB: list_sessions(user_id)
    DB-->>API: sessions 列表（不含 editor_state）
    API-->>Hook: {sessions: [...]}

    alt 今日已有会话
        Hook->>API: GET /api/sessions/{session_id}
        API->>DB: get_session(user_id, session_id)
        DB-->>API: 完整 session（含 editor_state）
        API-->>Hook: session data
        Hook->>Hook: loadState(editor_state)
    else 最近一条为昨天
        Note over Hook: 新的一天，创建空白会话
        Hook->>Hook: buildBlankState()
        Hook->>API: POST /api/sessions （保存空白会话）
        API->>DB: save_session(...)
    end

    Hook->>API: GET /api/preferences
    API->>Admin: user-preferences.get + current OAuth + original UUID
    Admin->>DB: identity/unified/owner校验后读取原配置
    DB-->>Admin: raw config JSON/nullable字段/微秒时间
    Admin-->>API: closed preferences DTO
    API->>API: raw JSON还原voice_configs/state_config，无SQL
    API-->>Hook: preferences
    Hook->>FE: 渲染编辑器
    FE-->>User: 显示今日会话内容
```

### 2.2 自动保存

```mermaid
sequenceDiagram
    actor User as 用户
    participant FE as Frontend
    participant Hook as useSessionLifecycle
    participant API as Backend API
    participant DB as database.py

    User->>FE: 编辑文本
    FE->>Hook: 编辑器状态变更
    Hook->>Hook: 启动 3s 防抖定时器
    Note over Hook: 3 秒无新变化后触发
    Hook->>Hook: ensureStateForPersistence()
    Hook->>API: POST /api/sessions {session_id, editor_state, name}
    API->>DB: save_session(user_id, session_id, editor_state, name)
    DB-->>API: OK
    API-->>Hook: {success: true}
    Hook->>Hook: 更新 currentEntryId
```

### 2.3 手动保存 / 新建会话

```mermaid
sequenceDiagram
    actor User as 用户
    participant FE as Frontend
    participant Hook as useSessionLifecycle
    participant API as Backend API
    participant DB as database.py

    User->>FE: 点击「保存」
    FE->>Hook: handleSaveToday()
    Hook->>API: POST /api/sessions
    API->>DB: save_session(...)
    DB-->>API: OK
    API-->>Hook: {success: true}
    Hook-->>FE: 显示「已保存」提示

    User->>FE: 点击「新建会话」
    FE->>Hook: handleNewSession()
    alt 当前会话有内容
        Hook->>API: POST /api/sessions （保存当前）
        API->>DB: save_session(...)
    end
    Hook->>Hook: buildBlankState()
    Hook->>FE: 加载空白编辑器
```

---

## 3. 历史语音评论兼容

普通 Writing 编辑只更新本地 `cells` 与 `weightPath`，不再自动调用模型，也不再注册 `analyze_text` PolyCLI session。已保存 Edit Session 中的 `commentors` 继续按原位置只读显示；用户显式发起历史评论对话时，前端复用对应 Voice 的 Claude Thread SSE。

---

## 4. Writing 手动建议模块

普通输入、粘贴、IME、回车、标点和停顿都不触发请求。用户点击 `Go deeper` 后，编辑器立即插入独立 Suggestion Cell；该 Writing Session 首次点击时懒创建产品级 Claude Agent Thread，后续建议与 Refresh 复用同一 Thread。

```mermaid
sequenceDiagram
    actor User as 用户
    participant FE as Frontend
    participant Engine as EditorEngine
    participant Hook as useWritingSuggestions
    participant Session as Session 持久化
    participant Thread as Session Claude Thread
    participant Agent as POST /api/claude-agent (SSE)

    User->>FE: 输入/回车/停顿
    FE->>Engine: 仅更新 TextCell 与本地 Weight
    Note over FE,Agent: 不发送模型请求
    User->>FE: 点击 Go deeper
    FE->>Engine: 插入 streaming Suggestion Cell（绑定正文快照）
    FE->>Hook: generateSuggestion(textCellId)
    alt Session 尚未绑定 Thread
        Hook->>Thread: POST /api/claude-agent/threads
        Thread-->>Hook: thread_id
        Hook->>Engine: setWritingThreadId(sessionId, thread_id)
    end
    Hook->>Session: 保存含 writingThreadId 的 EditorState
    Hook->>Agent: resume=true + thread_id + 产品级 Writing prompt + 点击快照
    Agent-->>Hook: text-delta... / finish
    Hook->>Engine: 校验 Session/Cell/request/Thread 后增量更新
    Engine-->>FE: Suggestion Cell completed
    FE-->>User: 蓝色只读建议 + Refresh
```

---

## 5. 语音对话模块

用户与某个语音角色就当前文本进行多轮对话。

```mermaid
sequenceDiagram
    actor User as 用户
    participant FE as Frontend
    participant Hook as useComments
    participant Thread as Voice Claude Thread
    participant Agent as POST /api/claude-agent (SSE)

    User->>FE: 展开评论卡片，输入消息并发送
    FE->>Hook: handleCommentChatSend(commentId, message)
    Hook->>Hook: addCommentChatMessage(commentId, "user", message)
    alt Voice 尚未绑定 Thread
        Hook->>Thread: POST /api/claude-agent/threads
        Thread-->>Hook: thread_id
    end
    Hook->>Agent: resume=true + thread_id + Voice prompt + 历史评论对话
    Agent-->>Hook: text-delta... / finish
    Hook->>Hook: addCommentChatMessage(commentId, "assistant", response)
    Hook->>FE: 更新评论对话历史
    FE-->>User: 显示角色回复
```

---

## 6. 深度分析模块

分析任务处理本次选中的日记与按需读取的 Notion 正文，按 echoes、traits、patterns 保存结构化结果。来源选择、页面入口与骨架见[分析内容交互稿](memory/reflections-analysis-content-design.md)；后台执行、Agent 内部流及任务 SSE 的完整说明见[Reflections Agent 执行设计](memory/reflections-agent-interaction-design.md)。

### 6.1 回响分析（Analyze Echoes）

下图以 `sections=["echoes"]` 展示单栏目执行。当前页面统一入口可提交多个栏目；Deck 提供 Agent 分组，执行选择使用成对的 `deck_id`、`agent_id`。Task API 通过 `start_reflections_task()` 创建后台 Engine，Runner 经 ThreadFactory 执行该栏目 Agent，Engine 按已保存结果发布任务事件。

```mermaid
sequenceDiagram
    actor User as 用户
    participant FE as AnalysisView / voiceApi
    participant TaskAPI as routers.reflections
    participant Admin as Admin Reflections
    participant Engine as ReflectionsTaskEngine
    participant Agent as ClaudeAgentReflectionsRunner
    participant Factory as ClaudeAgentThreadFactory / Service
    participant Notion as ReflectionNotionRuntime / NotionOperationClient
    participant Bus as ReflectionEventBus
    participant Stream as Reflections SSE
    User->>FE: 提交分析来源、栏目和 Agent 选择
    FE->>TaskAPI: POST /api/reflections/tasks，auto_start=false
    TaskAPI->>Admin: v2 创建任务，冻结日记选择、Notion 索引与 Agent prompt
    Admin-->>TaskAPI: task_id、来源范围与栏目
    TaskAPI->>Bus: prepare_reflection_event_bus
    TaskAPI-->>FE: 202 与 task_id
    FE->>Stream: GET /api/reflections/tasks/task_id/events
    Stream->>Admin: 校验权限并读取持久化事件
    Stream-->>FE: reflection.stream.connected 与历史回放
    FE->>TaskAPI: POST /api/reflections/tasks/task_id/start
    TaskAPI->>Admin: reflection-task.start
    TaskAPI->>Engine: start_reflections_task，加载快照并创建后台任务
    TaskAPI-->>FE: 202 与当前状态
    Engine->>Engine: _assemble_context / _start_run
    Engine->>Admin: reflection-section.begin，section=echoes
    Admin-->>Engine: 栏目 thread_id、revision 与 authority
    Engine->>Bus: publish reflection.section.started
    Bus->>Admin: 经 required observer 保存任务事件
    Bus-->>Stream: 已提交的栏目开始事件
    Stream-->>FE: 栏目运行中
    Engine->>Agent: run_section(echoes, load, begin)
    Agent->>Agent: 建立栏目 owner、选择模型、准备工作区与请求
    Agent->>Factory: 经 drain_chat_agent_turn 调用 run_streaming
    Factory->>Factory: assemble_context / execute_session，投影索引并执行模型与工具
    opt v2 Agent 需要 Notion 正文
        Factory->>Notion: 原 Read hook 调用绑定的 Host reader
        Notion->>Admin: v2.notion-context，任务/栏目/Thread/revision和当前范围校验
        Admin-->>Notion: 已记录证据或 null
        opt 首次读取
            Notion->>Notion: 原 get_page_markdown 读取此页
            Notion->>Admin: v2.notion-evidence，保存完整正文、SHA和时间
            Admin-->>Notion: 已确认原读取记录
        end
        Notion-->>Factory: 原 Read 返回已确认的正文与证据
    end
    Factory->>Admin: 通过栏目 persistence 保存用户及 assistant 消息
    Factory-->>Agent: 内部流消费完成；completion 与 owner_completion 已完成
    Agent->>Agent: 关闭栏目资源
    Agent->>Admin: reflection-section.transcript
    Admin-->>Agent: 栏目 Thread 转录
    Agent->>Agent: 解析最终 assistant 文本为 JSON
    Agent-->>Engine: 候选分析结果
    Engine->>Engine: 校验实际读取来源并转换 ReflectionInsightInputDTO
    Engine->>Admin: reflection-section.finish，保存 echoes 结果
    Admin-->>Engine: result_count 与栏目状态
    Engine->>Bus: publish reflection.section.completed
    Bus->>Admin: reflection-event.append 成功后推进 sequence
    Bus-->>Stream: 已提交的栏目完成事件
    Stream-->>FE: 栏目完成与结果计数
    Engine->>Admin: finalize 任务并执行 reflection-report.ensure
    Engine->>Bus: publish 对应任务终态事件
    Bus->>Admin: 持久化终态事件
    Bus-->>Stream: 已提交的终态事件
    Stream-->>FE: 任务终态
    FE->>TaskAPI: GET /api/reflections/tasks/task_id 与 results
    TaskAPI->>Admin: 读取当前任务、结果和失败栏目
    Admin-->>TaskAPI: 当前任务与已保存结果
    TaskAPI-->>FE: 结果与失败栏目
    opt 报告读取或保存恢复
        FE->>TaskAPI: POST /api/reflections/tasks/task_id/report
        TaskAPI->>Admin: 校验终态并 ensure 原任务报告
        TaskAPI-->>FE: 原 task 关联报告
    end
    FE-->>User: 展示回响结果与任务报告
```

#### 执行与事件合同

| 阶段 | 执行模块与输出 |
| --- | --- |
| 启动分析 | Task API 校验启动权限并创建后台 Engine；响应包含 task_id 和当前状态 |
| 执行 Agent | `ClaudeAgentReflectionsRunner.run_section()` 经统一 ThreadFactory/Service 执行；`drain_chat_agent_turn()` 消费内部流并等待轮次和 Factory owner 完成 |
| 取得结果 | Runner 从 Admin 栏目转录提取最后一段 assistant 文本，解析 JSON；Engine 校验冻结来源后保存结构化结果 |
| 发布进度 | Engine 调用 `ReflectionEventBus.publish()`；`TaskPersistenceObserver` 保存事件成功后，SSE 输出 `reflection.*` 状态、计数与错误摘要 |
| 打开报告 | Engine finalize 后执行 `reflection-report.ensure`；前端按原 task_id 查询或恢复关联报告 |

Agent 内部流供 Runner 等待执行完成，栏目消息通过 persistence 保存。Reflections SSE 的事件生产方为 Engine/EventBus；栏目生成期间，页面在任务事件到达时更新状态。单栏目执行、事件持久化、异常恢复和状态转换的正文图见[执行设计](memory/reflections-agent-interaction-design.md)。

[修订前 6.1 原图](history/pre-admin-user-preferences-20260915/sequence-diagrams.md#61-回响分析analyze-echoes)完整保留。

### 6.2 特质分析 / 模式分析

`traits`、`patterns` 使用同一 Task API、Engine、Runner、ThreadFactory 和任务事件链。Engine 按任务 sections 顺序串行执行，分别保存各栏目的结果与错误。持久化结果采用统一 DTO 字段 `title`、`description`、`related_session_ids`、`evidence`、`confidence`，栏目归属由 `section` 标识。

---


v2 按需读取前稿完整保留于[模块六历史原文](memory/reflections-sequence-pre-notion-on-demand-20261023-history.md)。

## 7. 历史图片读取模块

Timeline 只读取并展示Admin中已保留的当前用户历史图片，不提供生成、重绘或保存入口。普通列表与范围列表共享`picture-history.list`；全尺寸读取使用`picture-history.full`。Dream验证日期与limit，Admin从OAuth principal确定owner并执行排序、范围过滤和图片选择。完整规则见[当前用户图片历史](picture-history-current.md)。

```mermaid
sequenceDiagram
    actor User as 用户
    participant FE as Frontend
    participant API as GET /api/pictures/range
    participant Admin as Admin picture-history
    participant FullAPI as GET /api/pictures/{date}/full

    User->>FE: 打开 Timeline
    FE->>API: GET /api/pictures/range?start_date&end_date
    API->>Admin: picture-history.list(start_date, end_date, limit)
    Admin-->>API: owner历史缩略图或原图fallback
    API-->>FE: {pictures: [...]}
    FE-->>User: 展示历史图片

    User->>FE: 点击历史缩略图
    FE->>FullAPI: GET /api/pictures/{date}/full
    FullAPI->>Admin: picture-history.full(date)
    Admin-->>FullAPI: 同日最新full_image_base64或null
    FullAPI-->>FE: {image_base64}
    FE-->>User: 展示全尺寸图片
```

日期非法由Dream返回固定400；full结果为null或空字符串时保持`404 Picture not found for this date`。OAuth、权限、capability、Admin传输与DTO错误保持失败，不回退Dream数据库。普通列表把null prompt映射为空字符串，范围列表保留nullable prompt。

---

## 8. 卡组与声音管理模块

用户可管理「卡组（Deck）」及其下属「声音（Voice）」角色。

### 8.1 查看/创建卡组

```mermaid
sequenceDiagram
    actor User as 用户
    participant FE as Frontend (DeckManager)
    participant API as Backend API
    participant DB as database.py

    User->>FE: 打开卡组管理页
    FE->>API: GET /api/decks
    API->>DB: get_user_decks(user_id)
    DB-->>API: 用户卡组列表（含声音数量）
    API-->>FE: {decks: [...]}
    FE-->>User: 展示卡组列表

    User->>FE: 点击「新建卡组」，填写名称/描述
    FE->>API: POST /api/decks {name, description, icon, color}
    API->>DB: create_deck(user_id, ...)
    DB-->>API: deck_id
    API-->>FE: {deck_id}
    FE-->>User: 刷新卡组列表
```

### 8.2 Fork 社区卡组

```mermaid
sequenceDiagram
    actor User as 用户
    participant FE as Frontend
    participant API as Backend API
    participant DB as database.py

    User->>FE: 浏览社区卡组（GET /api/decks?published=true）
    FE->>API: GET /api/decks?published=true
    API->>DB: get_published_decks()
    DB-->>API: 已发布卡组列表
    API-->>FE: {decks: [...]}

    User->>FE: 点击「安装此卡组」
    FE->>API: POST /api/decks/{deck_id}/fork
    API->>DB: fork_deck(user_id, deck_id)
    Note over DB: 深拷贝卡组及所有声音，创建用户副本
    DB-->>API: new_deck_id
    API->>DB: increment_deck_install_count(deck_id)
    API-->>FE: {deck_id: new_deck_id}
    FE-->>User: 卡组已添加到我的卡组
```

### 8.3 发布卡组到社区

```mermaid
sequenceDiagram
    actor User as 用户
    participant FE as Frontend
    participant API as Backend API
    participant DB as database.py

    User->>FE: 点击「发布到社区」
    FE->>API: POST /api/decks/{deck_id}/publish
    API->>DB: get_deck_with_voices(user_id, deck_id)
    DB-->>API: deck 信息（含 published 状态）

    alt 当前未发布
        API->>DB: publish_deck(deck_id, user_id)
        Note over DB: 设置 published=1，断开 parent_id 链
        API-->>FE: {success, published: true}
    else 当前已发布（取消发布）
        API->>DB: unpublish_deck(deck_id, user_id)
        API-->>FE: {success, published: false}
    end
    FE-->>User: 更新发布状态
```

---

## 9. 好友系统模块

正常流程、状态、失败及验收以[现行稿](social-friendship-current.md)为准；旧SQL/锁缺口说明见已保留的[原文](history/pre-admin-user-preferences-20260915/sequence-diagrams.md)。

### 9.1 生成邀请码与处理申请

```mermaid
sequenceDiagram
    actor A as 邀请方
    actor B as 申请方
    participant F as Dream Browser/BFF
    participant D as Dream public routes/DTO client
    participant P as Admin OAuth/domain/Drizzle
    A->>F: 生成邀请码
    F->>D: POST /api/friends/invite/generate
    D->>P: 当前OAuth + service credential + UUID
    P->>P: server policy生成code/expiry，事务回执
    P-->>A: 原code/expires_at
    A->>B: 线下分享code
    B->>D: POST /api/friends/invite/use {code}
    D->>P: exact UseInviteDTO + 当前OAuth + UUID
    P->>P: 邀请码/pair锁、权限与状态检查
    P->>P: pending + used_by/used_at + 原receipt同TX
    P-->>D: closed success/result 或原业务error
    D-->>B: 原整数ID/label或400 detail
    A->>D: GET requests；POST request accept/reject
    D->>P: 当前recipient OAuth + target requestID + UUID
    P->>P: pair/行锁，pending只一个状态转换
    P-->>A: 原success或400 detail
```

### 9.2 查看历史图片

```mermaid
sequenceDiagram
    actor U as 用户
    participant D as Dream public routes/DTO client
    participant P as Admin domain/Drizzle
    U->>D: GET /api/friends/{friend_id}/timeline?limit=30
    D->>P: current OAuth + decimal friendID + limit
    P->>P: accepted关系检查，thumbnail/image fallback排序
    P-->>D: pictures列表或null
    D-->>U: 原图片字段或403
    U->>D: GET /api/friends/{friend_id}/pictures/{date}/full
    D->>P: current OAuth + friendID/date
    P->>P: 再检查accepted关系与指定图片
    P-->>D: image_base64或null/empty
    D-->>U: 原全图wrapper或404
```

写unknown只查同operation原UUID的receipt，absent不证明rollback或触发新写；其它模块旧流程仍是明确迁移依赖。

---

## 10. 语音输入模块

基于 WebSocket 的实时语音识别（Dashscope ASR）。

```mermaid
sequenceDiagram
    actor User as 用户
    participant FE as Frontend
    participant Hook as useVoiceInput
    participant WS as WebSocket /ws/speech-recognition
    participant ASR as DashScope ASR (paraformer)

    User->>FE: 点击麦克风按钮
    FE->>Hook: 开始录音
    Hook->>WS: WebSocket 连接 /ws/speech-recognition
    WS->>ASR: Recognition.start()

    loop 用户说话期间
        Hook->>Hook: 从麦克风采集 PCM 音频帧
        Hook->>WS: send_bytes(audio_frame)
        WS->>ASR: recognition.send_audio_frame(audio_frame)
        ASR-->>WS: on_event(RecognitionResult)
        WS-->>Hook: send_text({id, sentence: "识别文本..."})
        Hook->>FE: 更新文本输入框（实时显示）
    end

    User->>FE: 点击停止录音
    Hook->>WS: 断开 WebSocket
    WS->>ASR: recognition.stop()
    FE-->>User: 识别文本已插入编辑器
```

---

## 附录：系统架构概览

```mermaid
graph TB
    subgraph Frontend["Dream Web (Next.js 16 + React + TypeScript)"]
        Editor["编辑器<br/>EditorEngine"]
        Hooks["Hooks<br/>useSessionLifecycle<br/>useComments<br/>useWritingSuggestions<br/>useVoiceInput"]
        Views["页面视图<br/>CollectionsView<br/>AnalysisView<br/>FriendsView<br/>DeckManager"]
    end

    subgraph Backend["后端 (FastAPI + Python)"]
        AuthAPI["认证 API<br/>/api/register<br/>/api/login"]
        SessionAPI["会话 API<br/>/api/sessions"]
        PictureAPI["历史图片只读 API<br/>/api/pictures"]
        PrefsAPI["偏好 API<br/>/api/preferences"]
        DeckAPI["卡组 API<br/>/api/decks<br/>/api/voices"]
        FriendAPI["好友 API<br/>/api/friends"]
        WSEndpoint["WebSocket<br/>/ws/speech-recognition"]
    end

    subgraph Storage["存储"]
        SQLite["SQLite<br/>users / user_sessions<br/>daily_pictures / decks / voices<br/>friendships / analysis_reports"]
    end

    subgraph External["外部服务"]
        LLM["LLM API<br/>(Claude / 其他)"]
        ASR["DashScope ASR"]
    end

    Frontend --> Backend
    Backend --> Storage
    Backend --> External
```

公开GET /api/decks/{deck_id}消费deck.detail/current OAuth，four exact schemas/hash，outer与每个Voice deck_id必须匹配。原null404/owner int/时间/Memory值保持；Admin Repository按原字节投影nullable/raw Memory文本，Dream pure projector保留empty text、解析合法JSON并把非法非空JSON映射为null，读取不heal或写库。无read retry或DB fallback。详见[Deck详情现行规则](deck/deck-detail-version-history.md)。
