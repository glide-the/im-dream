<!-- [Input] Deck CRUD, content-version capability, binding CAS, and deferred Thread apply receipt. -->
<!-- [Output] Eleven end-to-end Mermaid business sequences. -->
<!-- [Pos] Deck management/version sequence source of truth. -->
<!-- [Sync] 2026-09-15: route content history/preview/commit through Admin and distinguish unknown transport results. -->
<!-- [Sync] 2026-08-16: implement durable draft/explicit commit and retain explicit-only Thread upgrades. -->
<!-- [Sync] 2026-08-17: add typed Deck-preview Demo dispatch to Chat or the dedicated Dream workbench. -->
<!-- [Sync] 2026-08-17: add same-Thread, same-Deck next-turn Agent selection with validation and CAS. -->

# Deck 业务时序

## 背景与问题

草稿/内容版本与运行binding是不同状态。Dream旧版本路由直接连接PG；公开five content操作现由Admin领域事务提供，网络结果不明需与已确认失败区分。

## 目标与边界

保持现有十一条可见业务流程。图2与图3的版本段通过Admin；创建/表单CRUD、其它Deck/Runtime图仍列为待迁移领域依赖，不将旧SQL作为迁移目标。共享FS/CLI仍Dream所有，不以metadata技术fixture代替实际验证。

## 概念与规则

current OAuth→Admin principal/owner/four exact physicalcapability→strict DTO/Service/Repository/Drizzle。preview无业务写，commit在同TX锁/CAS/hash/append/latest revision/receipt；safe409仅两revision。网络unknown保留原UUID、不重发、不把absent解释为rollback。正常/失败与影响范围见[内容版本交互](deck-detail-version-history.md)，本轮验收为actual HTTP/DTO DB-fenced技术合同。

## 1. 打开管理列表并加载内容版本

```mermaid
sequenceDiagram
  actor U as 用户
  participant UI as 前端
  participant A as Deck API
  participant V as 版本/权限校验
  participant DB as PostgreSQL
  U->>UI: 打开 Deck 管理
  UI->>A: GET /api/decks
  A->>DB: 读取 actor-owned Deck/Agent count
  A->>V: 验证 dream.deck-content-versions.v1
  V->>DB: 读取 latest_version/draft_revision/published_revision
  A->>DB: 读取 active runtime binding
  A-->>UI: 内容 vN/未提交 + 草稿状态 + 可选运行插件 vX
  UI-->>U: 扁平列表；无 capability 不伪造版本
```

## 2. 展开和收起版本记录

```mermaid
sequenceDiagram
  actor U as 用户
  participant UI as 前端
  participant A as Dream Deck API
  participant M as Admin DTO/Service/Repository
  participant DB as PostgreSQL
  Note over UI: 默认 folded，不请求 history
  U->>UI: 点击版本记录
  UI->>A: GET /api/decks/{id}/versions
  A->>M: typed history + request OAuth + original UUID
  M->>DB: 验证four capabilities/principal/owner，读取immutable versions DESC
  M-->>A: closed current/history + ISO microseconds
  A-->>UI: 原current state + creator int/history / empty / safe error
  UI-->>U: 桌面流内 300px / 窄屏同组件全宽
  U->>UI: 再次点击、收起或 Escape
  UI-->>U: 关闭并恢复焦点
  Note over U,DB: 展开/收起零业务写入
```

## 3. 创建、保存草稿并提交新版本

创建/表单保存保留原公开入口；该前半段的数据库消费者继续待Admin迁移。版本preview/commit段已经由Admin执行，Dream不生成snapshot/hash或执行版本事务。

```mermaid
sequenceDiagram
  actor U as 用户
  participant UI as 前端
  participant A as Dream Deck API
  participant C as 原CRUD领域服务（消费者待迁移）
  participant M as Admin DTO/Service/Repository
  participant DB as PostgreSQL
  U->>UI: 创建 Deck
  UI->>A: POST /api/decks
  A->>C: 原创建与default plugin证据流程
  C->>DB: INSERT Deck durable draft r1
  A-->>UI: deck_id；打开维护弹窗
  U->>UI: 修改 Deck/Agent/插件表单
  UI->>A: 原生产 PUT/POST/DELETE
  A->>C: owner + 字段校验
  C->>DB: 锁Deck、比较旧值、写入并推进draft revision
  U->>UI: 点击提交 v1/vN+1
  UI->>A: POST /versions/preview(expected draft/base)
  A->>M: typed preview + OAuth + UUID
  M->>DB: owner/four capabilities/CAS + snapshot diff/hash；无业务写
  M-->>A: target vN + 分类差异 + 影响范围
  A-->>UI: 原preview响应
  U->>UI: 确认并填写可选说明
  UI->>A: POST /versions(expected draft/base)
  A->>M: typed commit + OAuth + original UUID
  M->>DB: BEGIN + owned Deck FOR UPDATE + CAS/hash/no-op
  alt 已确认冲突或无变化
    M-->>A: safe 409 + closed revisions
    A-->>UI: 刷新事实后重新预览
  else 已确认提交成功
    M->>DB: INSERT immutable vN + UPDATE latest/published revision + receipt + COMMIT
    M-->>A: version + clean draft state
    A-->>UI: 原creator int/ISO微秒响应
  else Admin响应结果不明
    A-->>UI: 安全unknown结果与原request ID
    Note over A,M: 只读取原receipt/版本事实；absent不证明rollback，不自动POST重试
  end
```

## 4. 历史 Thread 检测可升级版本（后续 capability）

```mermaid
sequenceDiagram
  actor U as 用户
  participant UI as 前端
  participant T as Thread API
  participant V as 版本/权限校验
  participant DB as PostgreSQL
  U->>UI: 打开历史 Thread
  UI->>T: GET Thread
  T->>DB: 校验 owner，读取固定 Deck source version
  T->>V: 比较有权限的 latest Deck content version
  V-->>T: source v9 / target v12 / upgradeable
  T-->>UI: 明确 source/target；不自动应用
  UI-->>U: 当前 v9 + 显式升级入口
```

## 5. 用户确认升级历史 Thread（后续 capability）

```mermaid
sequenceDiagram
  actor U as 用户
  participant UI as 前端
  participant T as Thread API
  participant V as 版本/权限校验
  participant DB as PostgreSQL
  U->>UI: 确认 v9 → v12
  UI->>T: source/target/expected Thread revision/idempotency key
  T->>V: owner、target 可见、Thread idle、CAS
  alt 冲突/目标漂移
    V-->>UI: 409 + 最新事实；重新确认
  else apply 失败
    T->>DB: ROLLBACK
    T-->>UI: 原 v9 保持 + 可重试错误
  else 成功
    T->>DB: 原子写 apply receipt 并 CAS v9→v12
    T-->>UI: Thread 当前 v12
  end
```

## 6. 用户取消升级

```mermaid
sequenceDiagram
  actor U as 用户
  participant UI as 前端
  participant T as Thread API
  participant DB as PostgreSQL
  U->>UI: 打开 v9 → v12 确认
  U->>UI: 取消/关闭/Escape
  UI-->>U: 关闭并恢复焦点
  Note over UI,T: 不发送升级请求
  Note over T,DB: Thread 保持 v9，零业务写入
```

## 7. 升级失败并保留原版本

```mermaid
sequenceDiagram
  actor U as 用户
  participant UI as 前端
  participant T as Thread API
  participant V as 版本/权限校验
  participant DB as PostgreSQL
  U->>UI: 确认 v9 → v12
  UI->>T: 定向 apply
  T->>V: 权限、source/target、冲突校验
  V->>DB: 尝试准备 v12 receipt
  DB-->>V: 失败
  V->>DB: ROLLBACK
  T-->>UI: error + source remains v9
  UI-->>U: 明确仍使用 v9，可重试
```

## 8. 新 Thread 与历史 Thread 选择版本差异

```mermaid
sequenceDiagram
  actor U as 用户
  participant UI as 前端
  participant T as Thread API
  participant V as 版本/权限校验
  participant DB as PostgreSQL
  alt 新 Thread
    U->>UI: 选择 Deck/Agent 并创建
    UI->>T: POST Thread
    T->>V: 权限 + 当前已提交 Deck v12
    V->>DB: 同事务固定 v12 snapshot identity
    T-->>UI: 新 Thread 使用 v12
  else 历史 Thread
    U->>UI: 打开固定 v9 的 Thread
    T-->>UI: source v9 / available v12
    Note over UI,DB: 默认继续使用 v9；绝不自动或批量升级
    U->>UI: 可选显式确认升级
  end
```

## 9. 查看并删除相关对话后删除 Deck

```mermaid
sequenceDiagram
  actor U as 用户
  participant UI as Settings / Work
  participant T as Thread API
  participant D as Deck API
  participant V as 权限/依赖校验
  participant DB as PostgreSQL
  U->>UI: 更多 → 相关对话
  UI->>T: GET /threads?deck_id=deck-a&limit=20
  T->>V: 校验当前 actor
  V->>DB: user_id + deck_id 查询，按 updated_at 降序
  T-->>UI: Chat 历史预览
  loop 用户逐条确认删除
    U->>UI: 删除一条对话
    UI->>T: DELETE /threads/thread-a
    T->>V: thread owner 校验
    V->>DB: 删除 thread 并级联 messages
    T-->>UI: 从预览移除
  end
  U->>UI: 删除 Deck
  UI->>D: DELETE /decks/deck-a
  D->>V: owner + child + related thread + runtime snapshot
  alt 仍有关联对话
    V-->>UI: 409 related_threads；Deck 与绑定保持
  else 存在不可变 runtime snapshot
    V-->>UI: 409 runtime_history；不伪装成 Chat
  else 可以删除
    V->>DB: BEGIN；删除 refs + 未使用 bindings + Deck；COMMIT
    D-->>UI: success；刷新 Work 列表
  end
```

## 10. 同一 Chat 对话切换当前 Deck 内 Agent

```mermaid
sequenceDiagram
  actor U as 用户
  participant UI as Chat / Deck 徽章
  participant A as Claude Agent API
  participant V as DeckChatContext 校验
  participant DB as PostgreSQL
  U->>UI: 展开 Deck 元信息
  UI-->>U: 当前 Agent + 同 Deck 已启用 Agent
  U->>UI: 点击另一 Agent
  Note over UI: 仅更新下一轮选择；Thread/Deck/版本/receipt 不变
  U->>UI: 发送下一条消息
  UI->>A: threadId + fixed deckId + selected voiceId
  A->>V: actor、Deck 可见性、Agent 归属与启用状态
  alt 校验失败
    V-->>UI: 403/404；不写入、不启动 Agent
  else 校验通过
    A->>DB: UPDATE chat_thread.voice_id WHERE actor+deck+old voice CAS
    alt CAS 冲突
      DB-->>UI: 409 CHAT_AGENT_CONFLICT
      Note over DB: 原 Agent 保持；不启动 Agent
    else CAS 成功
      A->>DB: 消息 metadata 记录 deckId + voiceId
      A-->>UI: 使用所选 Agent system prompt 开始本轮 SSE
    end
  end
```

## 11. Deck 预览 Demo 按 Agent 类型分流

```mermaid
sequenceDiagram
  actor U as 用户
  participant UI as Deck 预览
  participant C as Chat 入口
  participant D as Dream API
  participant V as Deck/Agent/权限/版本校验
  participant DB as PostgreSQL
  participant W as Dream 工作台
  U->>UI: 点击某 Agent 的示例 Demo
  UI->>UI: 读取服务端 agent_type + 可见示例文字
  alt Chat Agent
    UI->>C: Deck + Agent + editable input
    C-->>U: 新 Chat 输入框预填；不自动发送
    Note over C,DB: Thread/消息零写入
  else Dream Agent
    UI->>D: POST Dream start(deckId, agentId, goal, idempotencyKey)
    D->>V: actor、Deck 类型、Agent 归属/启用、版本与并发校验
    alt 校验或创建失败
      V-->>UI: 4xx/5xx
      UI-->>U: 留在预览页；保留选择；错误可重试
      Note over D,DB: 不打开伪工作台；不得创建 Chat Thread 替代
    else 创建成功
      V->>DB: 原子创建 Dream Run + source Thread
      D-->>UI: workflowRunId + threadId
      UI->>W: /story-workspace/dream?run=workflowRunId
      W-->>U: 独立 Dream 工作台
    end
  end
```
