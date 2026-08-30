<!-- [Input] Actor credential source, lightweight index scheduler, thread projection, sdk_env CLI binding, and lazy Runtime Read hook design. -->
<!-- [Output] Business sequence diagrams for installation, authorization, index publication, Agent CLI/Read, failures, reauthorization, and disconnect. -->
<!-- [Pos] Current Notion credential/index/Runtime business-sequence source of truth in docs/design/notion-session. -->
<!-- [Sync] 2026-08-28: separate lightweight ID synchronization from on-demand page Markdown reads. -->
<!-- [Sync] 2026-08-29: add full discovery pagination, empty-scope revocation, current-scope projection filtering, and LKG reauthorization semantics. -->
<!-- [Sync] 2026-08-30: add the ntn prerequisite and direct four-variable Agent Runtime injection. -->
<!-- [Sync] 2026-08-30: add dynamic capability-catalog rendering into workspace README and reuse that generated Skill section in per-turn context. -->
<!-- [Sync] 2026-08-30: add explicit new-turn, resume, missing-install/config, Runtime-filter failure, and repaired real-Chat acceptance sequences. -->

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

## 4. 正常新 turn 注入流程

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Chat as Dream Chat
    participant Service as Dream Agent Service
    participant Cred as Credential Provider
    participant WS as Thread Workspace
    participant SDKEnv as sdk_env
    participant SDK as Claude Agent SDK
    participant Native as Native Runtime
    participant Bash as Agent Bash
    participant CLI as ntn
    participant Notion as Notion API

    User->>Chat: 发送需要 Notion 的消息
    Chat->>Service: POST turn(actor, thread)
    Service->>Cred: 读取当前 actor effective credential
    Cred->>WS: 原子刷新 .notion-home 与 .notion
    Service->>SDKEnv: 解析精确 thread projection
    SDKEnv->>SDK: options.env = server-owned binding
    SDK->>Native: spawn(cwd=thread, env=options 覆盖 inherited)
    Native->>Bash: production sandbox 传递校验后的 binding
    Bash->>CLI: 只读 ntn 命令
    CLI->>Notion: 当前 actor 认证请求
    Notion-->>CLI: 只读结果
    CLI-->>Bash: exit 0（不打印凭证）
    Bash-->>Chat: CLI 可用结论（SSE）
```

## 5. resume 环境刷新流程

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Chat as Dream Chat
    participant Service as Dream Agent Service
    participant Cred as Credential Provider
    participant WS as Same Thread Workspace
    participant SDK as Claude Agent SDK
    participant Native as New Runtime Process
    participant Session as Existing Session/Transcript
    participant Bash as Agent Bash

    User->>Chat: 在同一 thread 继续
    Chat->>Service: POST turn(same thread)
    Service->>Cred: 重新读取当前 actor effective credential
    Cred->>WS: 替换为本轮最新 .notion-home
    Service->>SDK: 新建 options.env + resume=session_id
    SDK->>Native: 为本轮重新 spawn Runtime
    Native->>Session: 读取既有 transcript/session identity
    Note over Native,Session: session 可复用，进程环境不缓存
    Native->>Bash: 传递本轮校验后的 binding
    Bash-->>Chat: 与新 turn 一致的 set/unset 与只读结果
```

## 6. CLI 未安装流程

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Settings as Dream Settings
    participant Backend as Dream Backend
    participant Resolver as ntn Installation Resolver
    participant Cred as Credential Provider
    participant Chat as Dream Chat

    User->>Settings: 打开 Notion 资源链接
    Settings->>Backend: GET capabilities
    Backend->>Resolver: 检查固定 ntn 安装
    Resolver-->>Backend: missing/incompatible
    Backend-->>Settings: 需要安装 + 固定说明
    User->>Settings: 点击连接
    Settings->>Backend: POST auth/login
    Backend->>Resolver: 再次 fail closed
    Backend-->>Settings: 不启动 device flow；提示安装后重试
    Note over Cred: 不创建 pending credential home
    User->>Chat: 发送普通消息
    Chat-->>User: 普通 Chat 继续；Notion CLI 局部不可用
```

## 7. 凭证或配置缺失流程

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Chat as Dream Chat
    participant Service as Dream Agent Service
    participant Cred as Credential Provider
    participant WS as Thread Workspace
    participant SDKEnv as sdk_env
    participant Native as Native Runtime
    participant Bash as Agent Bash

    User->>Chat: 创建或继续 turn
    Service->>Cred: 请求当前 actor projection
    alt 未连接、认证无效或 Workspace Mode 关闭
        Cred-->>Service: unavailable
        Service->>WS: 清除旧 .notion-home（若存在）
        Service->>SDKEnv: credential_home=None
        SDKEnv->>Native: 四项 binding 显式 empty/fail closed
        Native->>Bash: 不提供 Notion capability
        Bash-->>Chat: 提示连接/重试；普通回答继续
    else 有效认证但没有 workers.json
        Cred->>WS: 投影 auth/config/workspaces
        SDKEnv->>Native: home/token/keyring set；workers unset
        Native->>Bash: 普通 API/doctor 可用
        Bash-->>Chat: CLI 可用；workers 能力按需提示配置
    else foreign/symlink/越界 projection
        Cred-->>Service: safe projection error
        Service->>WS: 清除本 thread 无效 projection
        Service-->>Chat: Notion 局部失败；不影响 turn/SSE
    end
```

## 8. Runtime/Bash 环境被过滤时的失败链路

```mermaid
sequenceDiagram
    autonumber
    participant Cred as Current Actor Credential
    participant WS as Current Thread .notion-home
    participant SDKEnv as Dream sdk_env
    participant SDK as SDK 0.2.144
    participant Native as Runtime 0.1.3
    participant Filter as production cleanEnvironment
    participant Bash as Agent Bash
    participant CLI as ntn

    Cred->>WS: auth/config/workspaces 投影成功
    WS->>SDKEnv: 精确 current-thread path
    SDKEnv->>SDK: home/token/keyring set；workers unset
    SDK->>Native: options.env 覆盖 inherited
    Native->>Filter: 创建 production Bash
    Filter->>Filter: 仅保留 LANG/LC_*/PATH/TERM
    Filter-->>Bash: Notion binding 被删除
    Bash->>CLI: doctor/identity
    CLI-->>Bash: 未认证或默认 home 不可用
    Bash-->>Native: 目标变量 unset
    Native-->>SDK: Bash tool result（可正常退出但业务失败）
    Note over SDKEnv,Filter: 根因位于最后的 Runtime Bash env filter，非 projection/SDK/resume
```

## 9. 修复后的真实 Chat → Agent Bash → ntn 验收链路

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as Normal Dream Chat UI
    participant API as Public Chat API/SSE
    participant Service as Dream Agent Service
    participant Cred as Current Actor Provider
    participant WS as Persisted Thread Workspace
    participant SDK as Claude Agent SDK
    participant Runtime as Qualified Native Runtime
    participant Bash as Production Agent Bash
    participant CLI as ntn 0.15.1
    participant Notion as Notion API
    participant Store as Normal PostgreSQL/Admin Evidence

    User->>UI: 新建 Chat，要求安全检查 Notion CLI
    UI->>API: 创建 thread + 首轮消息
    API->>Service: 正常生产入口
    Service->>Cred: 当前 actor credential
    Cred->>WS: 当前 thread projection
    Service->>SDK: server-owned options.env
    SDK->>Runtime: exact version/manifest/capability
    Runtime->>Bash: exact workspace binding
    Bash->>Bash: 仅输出三个目标的 set/unset
    Bash->>CLI: --version + doctor/只读身份
    CLI->>Notion: 只读认证请求
    Notion-->>CLI: success
    CLI-->>Bash: exit 0；不输出 body/token
    Bash-->>API: persisted output-available
    API->>Store: 正常 thread/Gateway/turn 记录
    API-->>UI: 安全成功结论

    User->>UI: 同一 thread 继续验证
    UI->>API: resume turn
    API->>Service: 重复 projection/options/Runtime launch
    Runtime->>Bash: 本轮最新 binding
    Bash->>CLI: 只读复核成功
    API-->>UI: resume 与新 turn 一致；普通 Chat 正常
```
