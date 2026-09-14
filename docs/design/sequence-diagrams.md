<!-- [Sync] 2026-09-15: replace social flows with Admin while preserving the original in history. -->
<!-- [Input] Module business flows, current Admin consumers and byte-preserved pre-migration sequence source. -->
<!-- [Output] Module flow reference with explicit current ownership and retained migration dependencies. -->
<!-- [Pos] Sequence index; focused current designs own authentication, Session, Deck, preferences and social rules. -->
<!-- [Sync] 2026-09-15: public user preferences use Admin; retain original whole source in history. -->

认证/Session/Deck的现行程序行为以[Admin交互](../architecture/admin-auth-data-interaction.md)和各功能稿为准；本稿其余尚未更新的旧issuer/直接SQL说明仅是迁移依赖，不作为现行规范。[原十模块时序原文](history/pre-admin-user-preferences-20260915/sequence-diagrams.md)字节保持；用户偏好正常、状态、失败和验收见[现行稿](user-preferences-current.md)。

<!-- [Input] Current Next.js Dream Web modules and Python business routes/services. -->
<!-- [Output] Current cross-module business sequence diagrams. -->
<!-- [Pos] Design-level sequence index; domain details remain in their focused documents. -->
<!-- [Sync] 2026-09-06: replace the retired Vite frontend label with the sole Next.js app/_dream source boundary. -->
<!-- [Sync] 2026-09-01: replace debounced random-Voice inspiration with manual persistent Suggestion Cells on one Session-owned Claude Thread. -->
<!-- [Sync] 2026-08-31: replace daily-picture generation with historical read-only Timeline access and remove its scheduler/runtime. -->

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

分析用户所有笔记，挖掘回响主题、性格特质、行为模式。

### 6.1 回响分析（Analyze Echoes）

```mermaid
sequenceDiagram
    actor User as 用户
    participant FE as Frontend (AnalysisView)
    participant TaskAPI as Reflections Task API
    participant Stream as Reflections SSE
    participant Agent as Reflections Agent
    participant ReportAPI as POST /api/reports

    User->>FE: 点击「分析回响」
    FE->>TaskAPI: POST /api/reflections/tasks\n{sections: ["echoes"], auto_start: false}
    TaskAPI-->>FE: task_id
    FE->>Stream: GET /api/reflections/tasks/{task_id}/events
    FE->>TaskAPI: POST /api/reflections/tasks/{task_id}/start
    TaskAPI->>Agent: 执行 echoes 分区分析
    Agent-->>Stream: reflection.* 增量事件
    Stream-->>FE: SSE 进度事件
    FE->>TaskAPI: GET /api/reflections/tasks/{task_id}/results
    TaskAPI-->>FE: echoes 结果
    FE->>ReportAPI: POST /api/reports {report_type: "echoes", report_data}
    ReportAPI-->>FE: {success: true}
    FE-->>User: 展示回响卡片列表
```

### 6.2 特质分析 / 模式分析

流程与回响分析相同，仅 Reflections section 与返回字段不同：
- **traits** → 返回 `{traits: [{trait, strength, evidence}]}`
- **patterns** → 返回 `{patterns: [{pattern, description, frequency}]}`

---

## 7. 历史图片读取模块

Timeline 只读取并展示数据库中已保留的历史图片，不提供生成、重绘或保存入口。

```mermaid
sequenceDiagram
    actor User as 用户
    participant FE as Frontend
    participant API as GET /api/pictures/range
    participant DB as database.py
    participant FullAPI as GET /api/pictures/{date}/full

    User->>FE: 打开 Timeline
    FE->>API: GET /api/pictures/range?start_date&end_date
    API->>DB: get_daily_pictures_range(user_id, ...)
    DB-->>API: 历史缩略图
    API-->>FE: {pictures: [...]}
    FE-->>User: 展示历史图片

    User->>FE: 点击历史缩略图
    FE->>FullAPI: GET /api/pictures/{date}/full
    FullAPI->>DB: get_daily_picture_full(user_id, date)
    DB-->>FullAPI: full_image_base64
    FullAPI-->>FE: {image_base64}
    FE-->>User: 展示全尺寸图片
```

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
