<!-- [Input] Actor credential source, lightweight index scheduler, thread projection, and lazy Runtime Read hook design. -->
<!-- [Output] Business sequence diagrams for authorization, index publication, thread Read, failures, reauthorization, and disconnect. -->
<!-- [Pos] Current Notion credential/index/Runtime business-sequence source of truth in docs/design/notion-session. -->
<!-- [Sync] 2026-08-28: separate lightweight ID synchronization from on-demand page Markdown reads. -->

# Notion 凭证、轻量索引与按需 Read 业务时序

## 1. 连接、选择与首次轻索引

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as Dream UI
    participant Backend as Dream Backend
    participant Provider as Actor Agentdata Provider
    participant CLI as ntn CLI
    participant Notion as Notion API
    participant Store as Connector Store

    User->>UI: 连接 Notion
    UI->>Backend: POST auth/login
    Backend->>Provider: 创建该 actor 的 pending credential home
    Backend->>CLI: device login（显式 pending home）
    CLI-->>UI: 验证链接与验证码
    User->>Notion: 确认授权
    UI->>Backend: POST auth/poll
    Backend->>CLI: poll 同一 pending home
    CLI->>Notion: 查询授权状态
    Notion-->>CLI: credential
    Backend->>Provider: 原子提升 actor credential source
    Backend-->>UI: authenticated

    User->>UI: 选择 database/page 并保存
    UI->>Backend: POST resources/select
    Backend->>Store: 保存精确 selection，resource=pending
    Backend->>Store: policy=syncing
    loop 每个已选 data source（含 cursor 分页）
        Backend->>CLI: query rows（只取 ID/元数据）
        CLI->>Notion: data_sources/{id}/query
        Notion-->>CLI: page IDs/title/url/last_edited
    end
    Note over Backend,Notion: 不调用 page/markdown/blocks 正文端点
    Backend->>Provider: 原子发布轻量 current.json（pages={}）
    Backend->>Store: 保存 identity/last_synced_at<br/>精确 included resources=synced<br/>policy=applied
    Backend-->>UI: 索引已同步 + counts/identity
    Note over User,Provider: 不需要先创建 Chat/workspace
```

## 2. 定时更新、thread 投影与页面按需读取

```mermaid
sequenceDiagram
    autonumber
    participant Worker as Dream Index Worker
    participant Store as Connector Store
    participant Provider as Actor Agentdata Provider
    participant Notion as Notion API
    actor User
    participant UI as Dream UI
    participant Service as Agent Service
    participant Runtime as Agent Runtime
    participant Hook as Notion Read Hook

    loop policy sweep
        Worker->>Store: authenticated + selected + due candidates
        alt effective enabled and due
            Worker->>Store: policy=syncing
            Worker->>Notion: 分页枚举 ID/元数据
            alt index 成功
                Worker->>Provider: 原子替换 current LKG
                Worker->>Store: exact resources=synced<br/>policy=applied
            else 401/403/timeout/cancel
                Worker->>Store: policy=error + safe code
                Note over Provider: 保留上一成功 current
            end
        else disabled or not due
            Worker->>Worker: 跳过
        end
    end

    User->>UI: 创建/继续对话
    UI->>Service: Agent turn(thread_id, actor)
    Service->>Provider: 读取 actor credential + current index
    Provider->>Runtime: 原子投影 {thread}/.notion-home 与 {thread}/.notion
    Note over Service,Runtime: 不请求 Notion，不构建 index
    Runtime->>Runtime: 发现 backend-owned notion-session Skill
    Runtime->>Runtime: Read .notion/index.json 定位 page_id
    Runtime->>Hook: Read .notion/pages/<page_id>.json
    Hook->>Hook: 校验 workspace/path/symlink/index membership
    alt ID 已选择且 credential 有效
        Hook->>Notion: 获取该页 Markdown
        Notion-->>Hook: 当前正文
        Hook->>Runtime: 0600 thread tmp JSON redirect
        Runtime-->>UI: 正文结果（既有 SSE）
    else ID 未选择
        Hook-->>Runtime: NOTION_RESOURCE_NOT_SELECTED<br/>不请求 Notion
        Runtime-->>UI: 引导选择并同步 index；普通对话继续
    else credential/permission/API 失败
        Hook-->>Runtime: 安全错误码 + nextAction
        Runtime-->>UI: Notion 局部失败；普通对话继续
    end
```

## 3. 重新授权、策略修改与断开

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as Dream UI
    participant Backend as Dream Backend
    participant Store as Connector Store
    participant Provider as Actor Agentdata Provider
    participant Runtime as Next Agent Runtime

    User->>UI: 修改自动同步开关/频率
    UI->>Backend: PUT sync-policy
    Backend->>Store: 校验 desired，推进 revision/effective
    Backend-->>UI: effective/status/next sync

    User->>UI: 重新连接 Notion
    UI->>Backend: auth/login + auth/poll
    Backend->>Provider: pending 成功后原子替换 credential source
    Note over Provider: index LKG 保留，后续同步刷新
    User->>Runtime: 下一 turn
    Provider->>Runtime: 投影新 credential + 最近成功 index

    opt 用户确认断开
        User->>UI: 断开 Notion
        UI->>Backend: DELETE connector
        Backend->>Store: 删除 actor connector 数据
        Backend->>Provider: 删除 credential/index source 与已有 credential projection
        Backend-->>UI: 未连接
        Runtime-->>UI: 后续 Notion Read fail closed，普通对话继续
    end
```
