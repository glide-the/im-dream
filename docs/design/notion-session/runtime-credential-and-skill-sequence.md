<!-- [Input] Actor credential source, lightweight index scheduler, thread projection, sdk_env CLI binding, and lazy Runtime Read hook design. -->
<!-- [Output] Business sequence diagrams for installation, authorization, index publication, Agent CLI/Read, failures, reauthorization, and disconnect. -->
<!-- [Pos] Current Notion credential/index/Runtime business-sequence source of truth in docs/design/notion-session. -->
<!-- [Sync] 2026-08-28: separate lightweight ID synchronization from on-demand page Markdown reads. -->
<!-- [Sync] 2026-08-29: add full discovery pagination, empty-scope revocation, current-scope projection filtering, and LKG reauthorization semantics. -->
<!-- [Sync] 2026-08-30: add the ntn prerequisite and direct four-variable Agent Runtime injection. -->
<!-- [Sync] 2026-08-30: add dynamic capability-catalog rendering into workspace README and reuse that generated Skill section in per-turn context. -->

# Notion 凭证、轻量索引与 Agent CLI/Read 业务时序

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
    Backend->>Backend: 检查固定版本 ntn 可执行文件
    alt ntn 未安装
        Backend-->>UI: 需要安装 + 固定安装命令
    else ntn 已安装
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
    end

    Backend->>CLI: 分页发现全部 database/page
    CLI-->>UI: 紧凑资源元数据（无 raw）
    User->>UI: 选择 database/page 并保存
    UI->>Backend: POST resources/select
    Backend->>Store: 原子替换精确 selection
    alt selection 非空
        Backend->>Store: resource=pending，policy=syncing
        loop 每个已选 data source（含 cursor 分页）
            Backend->>CLI: query rows（只取 ID/元数据）
            CLI->>Notion: data_sources/{id}/query
            Notion-->>CLI: page IDs/title/url/last_edited
        end
        Note over Backend,Notion: 不调用 page/markdown/blocks 正文端点
        Backend->>Provider: 原子发布轻量 current.json（pages={}）
        Backend->>Store: 保存 identity/last_synced_at<br/>精确 included resources=synced<br/>policy=applied
        Backend-->>UI: 索引已同步 + counts/identity
    else selection 为空
        Backend->>Provider: 清除 actor current index
        Backend->>Store: 清除 current identity/last success
        Backend-->>UI: 已连接、0 来源、未同步
    end
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
    participant Catalog as Capability Catalog
    participant CLI as ntn CLI
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
    Provider->>Provider: LKG 与当前 selection 求交<br/>移除私有 connector 配置
    Provider->>Catalog: materializer 调用 build_notion_capability_catalog(connector)
    Catalog-->>Provider: Skill rows + availability + catalog revision
    Provider->>Runtime: 原子投影 {thread}/.notion-home 与 {thread}/.notion<br/>README 含动态 Skill index
    Service->>Runtime: workspace context 读取同一 README Skill 段
    Service->>Runtime: sdk_env 注入 NOTION_HOME/API_TOKEN/KEYRING/WORKERS_CONFIG_FILE
    Note over Service,Runtime: 不请求 Notion，不构建 index
    Runtime->>Runtime: 发现 catalog 返回且当前可用的 backend-owned Skills
    alt 使用 notion-cli
        Runtime->>CLI: Bash 调用 ntn
        CLI->>Notion: 使用当前 actor/thread environment
        Notion-->>Runtime: CLI 结果
    else 使用 notion-session
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
    alt 新授权成功
        Backend->>Provider: 原子替换 credential source
        Backend-->>UI: 已连接
    else 新授权失败且旧 credential 有效
        Backend->>Provider: 保留旧 credential source
        Backend-->>UI: 部分可用 + 重试建议
    else 无有效 credential
        Backend-->>UI: 已过期/异常 + 重新授权
    end
    Note over Provider: index LKG 保留，后续同步刷新
    User->>Runtime: 下一 turn
    Provider->>Runtime: 投影当前有效 credential + 范围内 LKG

    User->>UI: 断开 Notion（无确认弹窗）
    UI->>Backend: DELETE connector
    Backend->>Store: 删除 actor connector 数据
    Backend->>Provider: 删除 credential/index source 与已有 thread 投影
    Backend-->>UI: 未连接
    Runtime-->>UI: 后续 Notion Read fail closed，普通对话继续
```
