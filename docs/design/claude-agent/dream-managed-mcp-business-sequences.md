<!-- [输入] Dream managed-DB MCP 的前端、API、Service、PostgreSQL、标准 MCP Client、OAuth、Claude Agent SDK/Runtime 与真实验收事实。 -->
<!-- [输出] 面向产品、前端、后端、QA 和运维的中文 MCP 业务交互时序图集。 -->
<!-- [定位] dream-managed-mcp-resources.md 的业务流程伴随文档；主设计稿继续拥有数据、协议、安全和迁移合同。 -->
<!-- [同步] 2026-08-25：按已实现的详情自动 force=false inventory、后端认证判定、OAuth 自动 callback、Chat 快照注入和零管理 CLI 路径整理。 -->

# Dream 托管 MCP 业务交互时序图

本文只描述用户或操作员可触发的业务流程。数据模型、安全合同、API DTO、性能证据和测试矩阵以 [Dream 托管 MCP Resources 设计稿](./dream-managed-mcp-resources.md) 为准。

## 1. 阅读约定

| 名称 | 含义 |
|---|---|
| Resources UI | Dream 设置中的 MCP Server 列表与详情页 |
| Dream API | actor 鉴权后的公开 /api/claude-mcp 接口 |
| MCP Service | Server CRUD、状态聚合、缓存失效与错误 DTO 边界 |
| Inventory Service | 复用标准 MCP Client 执行 initialize 和 tools/resources/prompts discovery |
| Runtime | 仅执行 Chat turn；不作为 Dream MCP 管理数据库 |
| PostgreSQL | MCP Server、加密凭据、inventory snapshot 和导入回执的唯一事实来源 |
| inventory snapshot | 某一 config revision + credential revision 下的 tools/resources/prompts 脱敏发现结果 |
| runtime config snapshot | 某个 Chat turn 读取的 enabled Server 配置与 credential refs/revisions；不等于 inventory snapshot |
| single-flight | 同一 actor、Server 和 revision 组合的并发 discovery 只执行一次远端连接，其余请求共享结果 |
| 安全错误 DTO | 只含稳定错误码、retryable、trace id 等脱敏字段，不含 URL query、Token 或远端响应正文 |
| operationId | Dream 生成的有界、非敏感 OAuth operation 标识；详情页写入 Dream 同源 localStorage，callback SPA 读取后立即删除 |

所有正常管理请求均禁止调用 claude --version、claude mcp help/list/get 或其他 MCP 管理 CLI。前端不提供认证方式选择，也不提供 inventory 刷新或重试按钮。

## 2. 业务流程索引

| 场景 | 用户看到的结果 | 关键约束 |
|---|---|---|
| Resources 列表 | Server 配置立即展示 | 只查数据库；零远端 MCP 连接 |
| Server 详情 | 自动出现 Tools、Resources、Prompts | 自动 force=false；缓存优先；无刷新按钮 |
| 新增 Server | 只填写名称、transport 和 URL/profile | 后端连接后判断匿名或 OAuth |
| OAuth | Provider 授权完成后自动返回 Dream | 无复制 callback 地址或授权码 |
| 修改/删除/logout | 状态与 inventory 自动更新 | CAS revision；精确失效 credential/snapshot |
| 多 Server discovery | 成功项正常展示，失败项独立报错 | 有界并行；单 Server 失败不阻塞兄弟 |
| Chat/workspace | Agent 使用数据库中的 MCP 工具 | 每 turn 读取一致快照；临时投影 finally 删除 |
| cancel/resume | 停止当前操作，后续同 Thread 可继续 | resume Agent session，不恢复旧 MCP ClientSession |
| 旧配置迁移 | 显式导入一次，正常页面只读数据库 | 幂等 receipt；不调用 CLI；不覆盖较新配置 |

## 3. 历史慢路径：页面加载触发 11 + N 个管理子进程

~~~mermaid
sequenceDiagram
    autonumber
    actor U as 用户
    participant UI as Resources UI
    participant API as Dream API
    participant S as 旧 MCP Service
    participant CLI as Claude CLI
    participant M as Remote MCP

    U->>UI: 进入 Resources
    UI->>API: GET capability
    API->>S: capability
    S->>CLI: --version + 四组 mcp help
    UI->>API: GET servers
    API->>S: list
    S->>CLI: 再次 --version + 四组 help
    S->>CLI: mcp list
    CLI->>M: initialize + discovery
    loop N 个 Server 串行
        S->>CLI: mcp get server
        CLI->>M: 再次 initialize + discovery
    end
    S-->>UI: 列表与 inventory
    Note over S,CLI: 管理页总计 11 + N 个 CLI 子进程
~~~

## 4. Server 列表：数据库快速返回

~~~mermaid
sequenceDiagram
    autonumber
    actor U as 用户
    participant UI as Resources UI
    participant API as Dream API
    participant S as MCP Service
    participant DB as PostgreSQL

    U->>UI: 进入 Resources 页面
    par 页面能力
        UI->>API: GET /capability
        API->>S: 校验 capability
        S->>DB: 首次校验精确 schema capability
        DB-->>S: available
        S-->>UI: managed_db
    and Server 列表
        UI->>API: GET /servers
        API->>S: list_servers(actor)
        S->>DB: 查询 actor 可见 Server 与凭据状态
        DB-->>S: Server rows
        S-->>UI: ServerDTO[]
    end
    UI-->>U: 立即展示 Server 卡片
    Note over UI,DB: 列表关键路径无 MCP 网络、无 Runtime、无 CLI
~~~

## 5. Server 详情：自动、缓存优先加载 inventory

~~~mermaid
sequenceDiagram
    autonumber
    actor U as 用户
    participant UI as Server 详情页
    participant API as Dream API
    participant S as MCP Service
    participant DB as PostgreSQL
    participant D as Inventory Service
    participant C as 标准 MCP Client
    participant M as MCP Server

    U->>UI: 点击管理与工具
    UI->>API: GET /capability + GET /servers/{id}
    API->>S: actor-scoped get
    S->>DB: 读取 Server 与 credential revision
    DB-->>S: 当前 ServerDTO
    S-->>UI: ServerDTO
    UI-->>U: 先展示配置、连接和 inventory 加载状态
    UI->>API: 自动 POST /servers/{id}/discoveries<br/>force=false
    API->>D: discover(actor, server id)
    D->>DB: 原子读取当前配置与 config/credential revisions<br/>并查相同 revisions 的有效 snapshot
    alt revisions 匹配且 snapshot 未过期
        DB-->>D: cached inventory
        D-->>UI: DiscoveryDTO cached=true
    else 无有效 snapshot
        D->>C: 创建请求内 ClientSession
        C->>M: initialize
        par Server 声明 Tools
            C->>M: list_tools
            M-->>C: tools
        and Server 声明 Resources
            C->>M: list_resources
            M-->>C: resources
        and Server 声明 Prompts
            C->>M: list_prompts
            M-->>C: prompts
        end
        C-->>D: 聚合 inventory
        D->>DB: 保存 revisions 绑定的安全 snapshot
        D-->>UI: DiscoveryDTO cached=false
    end
    UI-->>U: 自动展示 Tools、Resources、Prompts
    Note over U,UI: 页面没有刷新 inventory 或重试探测按钮
    Note over U,UI: 失败后重新进入或刷新详情页会再次自动 force=false；配置或认证变化也会自动重试
~~~

## 6. 新增 Server：后端自动判断匿名或 OAuth

~~~mermaid
sequenceDiagram
    autonumber
    actor U as 用户
    participant UI as Resources UI
    participant API as Dream API
    participant S as MCP Service
    participant DB as PostgreSQL
    participant D as Inventory Service
    participant M as MCP Server

    U->>UI: 输入名称、transport、URL 或 stdio profile
    Note over U,UI: 不选择认证方式，不输入任意 stdio command/env
    UI->>API: POST /servers
    API->>S: 校验 actor、URL/SSRF、transport/profile
    S->>DB: INSERT Server revision=1
    DB-->>UI: configured
    U->>UI: 打开 Server 详情
    UI->>API: 自动 POST discovery force=false
    API->>D: 使用标准 MCP Client 连接
    alt 匿名 initialize 成功
        D->>M: list tools/resources/prompts
        M-->>D: inventory
        D->>DB: 保持 auth_kind=none + 保存 snapshot
        D-->>UI: connected / anonymous
        UI-->>U: 自动展示 inventory，不显示 OAuth 动作
    else 标准 credential-required 或已验证 OAuth challenge
        D->>DB: CAS auth_kind=oauth
        D-->>UI: needs_auth / required
        UI-->>U: 显示开始认证
    else timeout、不可达或非法响应
        D-->>UI: 安全错误 DTO
        UI-->>U: 显示该 Server 的连接错误
    end
~~~

## 7. OAuth：Provider 授权后自动回到 Dream

~~~mermaid
sequenceDiagram
    autonumber
    actor U as 用户
    participant UI as Dream 详情页
    participant API as Dream API
    participant O as OAuth Coordinator
    participant P as OAuth Provider
    participant CB as Dream 同源 callback SPA
    participant DB as PostgreSQL
    participant D as Inventory Service

    U->>UI: 点击开始认证
    UI->>API: POST /servers/{id}/auth-operations
    API->>O: 创建 actor-owned operation
    O->>P: 标准 SDK metadata + PKCE
    P-->>O: authorization URL
    O-->>UI: operationId + authorizationUrl
    UI->>UI: 写入 Dream 同源 localStorage<br/>仅保存有界、非敏感 operationId
    UI->>P: 打开 Provider popup
    U->>P: 登录并同意授权
    P-->>CB: /oauth/callback?code&state
    CB->>CB: 从 Dream 同源 localStorage 读取 operationId<br/>并立即删除
    CB->>API: 自动 POST 完整 callback URL + operationId
    Note over U,CB: 用户不复制 URL、授权码或 state
    API->>O: 校验 actor、state、PKCE、expiry
    O->>P: exchange token
    P-->>O: access/refresh token
    O->>DB: AES-GCM 加密凭据<br/>credential revision++
    O->>DB: 失效旧 inventory snapshot
    O->>D: 完成认证后的 discovery
    D->>DB: 保存新 revision inventory
    loop operation 为 active
        UI->>API: GET /auth-operations/{operationId}
        API->>O: 查询 actor-owned operation
        O-->>UI: waiting / exchanging / connected
    end
    UI->>API: 自动 force=false inventory
    API-->>UI: 命中新 snapshot
    UI-->>U: 已认证连接 + Tools/Resources/Prompts
~~~

## 8. 修改、logout 与删除：revision 绑定失效

~~~mermaid
sequenceDiagram
    autonumber
    actor U as 用户
    participant UI as Server 详情页
    participant API as Dream API
    participant S as MCP Service
    participant DB as PostgreSQL
    participant D as Inventory Service

    alt 修改显示名称或连接配置
        U->>UI: 保存配置
        UI->>API: PATCH /servers/{id}<br/>expected_revision
        API->>S: actor + CAS update
        S->>DB: SELECT FOR UPDATE
        alt revision 匹配
            S->>DB: revision++，失效 snapshot
            opt endpoint/transport 等安全字段变化
                S->>DB: 删除/失效 Dream 本地密文凭据<br/>credential revision++
            end
            S-->>UI: 新 ServerDTO
            UI->>API: 自动 discovery force=false
            API->>D: 读取新 revision
            D-->>UI: 新 inventory 或 needs_auth
        else revision 冲突
            S-->>UI: 409 revision conflict
        end
    else logout
        U->>UI: 点击退出认证
        UI->>API: DELETE /servers/{id}/credential
        S->>DB: 删除密文凭据 + credential revision++<br/>失效 snapshot
        S-->>UI: logged_out
        UI->>API: 自动 discovery force=false
        alt Server 仍允许匿名访问
            API-->>UI: connected / anonymous + inventory
        else Server 继续要求凭据
            API-->>UI: needs_auth / required
        end
    else 删除 Server
        U->>UI: 确认移除
        UI->>API: DELETE /servers/{id}?expected_revision
        S->>DB: actor-owned CAS delete
        DB-->>S: cascade credential/snapshot
        S-->>UI: removed
        UI-->>U: 返回数据库 Server 列表
    end
~~~

## 9. 多 Server discovery：有界并行与部分成功

此流程用于批量 discovery API 或后台聚合，不进入 Server 列表首屏关键路径。

~~~mermaid
sequenceDiagram
    autonumber
    participant C as API 调用方
    participant API as Dream API
    participant D as Discovery Coordinator
    participant DB as PostgreSQL
    participant A as Server A
    participant B as Server B
    participant N as Server N

    C->>API: POST /discoveries {server_ids}
    API->>D: actor-scoped bulk request
    D->>DB: 一次读取配置、凭据引用和 revisions
    DB-->>D: detached inputs
    par semaphore slot 1
        D->>A: initialize + list capabilities
        A-->>D: success inventory
    and semaphore slot 2
        D->>B: initialize
        B--xD: timeout / 401 / invalid response
    and 后续 slot
        D->>N: initialize + list capabilities
        N-->>D: success inventory
    end
    D->>DB: 分别保存成功 snapshot 与安全错误
    D-->>API: complete / partial / failed + per-item DTO
    API-->>C: A、N 正常；B 独立失败
    Note over D,N: 单 Server 失败不取消兄弟；同 revision 请求 single-flight
    Note over C,N: 聚合请求等待每项成功、失败或独立 timeout 后返回，不无限等待
~~~

## 10. Chat/workspace：每个 turn 从数据库投影 MCP 配置

~~~mermaid
sequenceDiagram
    autonumber
    actor U as 用户
    participant UI as Dream Chat UI
    participant API as Dream Chat API
    participant DB as PostgreSQL
    participant L as MCP Snapshot Loader
    participant R as Agent Runner
    participant SDK as Claude Agent SDK
    participant RT as Runtime
    participant M as MCP Server

    U->>UI: 发送新 turn 或继续同 Thread
    UI->>API: Chat request<br/>不携带 MCP secret/config
    API->>DB: 校验 actor、Thread、Deck/workspace
    API->>L: load enabled MCP snapshot
    L->>DB: 读取 Server + credential refs/revisions
    L->>L: 内存解密并生成 detached mcp_servers
    L-->>R: AgentRunOptions
    R->>R: 合并内置 Server并检查名称冲突
    alt 与内置 MCP 名称冲突
        R-->>API: fail closed 安全错误
        API-->>UI: 当前 turn 未启动
    else 名称无冲突
    R->>R: 在 thread .claude-tmp 原子写 0600 临时配置
    R->>SDK: mcp_servers=Path<br/>strict_mcp_config=true
    SDK->>RT: 有既有 Claude session id 时 resume<br/>否则启动新 Agent session
    RT->>M: 按注入配置连接并调用 MCP
    M-->>RT: tool/resource/prompt result
    RT-->>API: Agent events
    API-->>UI: SSE 增量消息与工具确认
    UI-->>U: 可见结果
    R->>R: finally 删除临时配置
    end
    Note over DB,RT: 数据库是配置真相源；Runtime 不执行 MCP 管理 list/get
    Note over U,RT: 普通连续对话和异常恢复都在每个 turn 重读 runtime config snapshot
~~~

## 11. Cancel、Runtime 异常与 session resume

~~~mermaid
sequenceDiagram
    autonumber
    actor U as 用户
    participant UI as Dream UI
    participant API as Dream API
    participant S as ClaudeAgentService
    participant RT as Runtime
    participant DB as PostgreSQL
    participant M as MCP Server

    alt 用户停止正在运行的 Chat turn
        U->>UI: 点击停止生成
        UI->>API: POST /threads/{id}/stop
        API->>S: cancel 当前 bg_task
        S->>RT: interrupt/cancel
        RT->>M: 发送协议 cancel 或关闭当前连接
        S->>DB: 持久化安全终态与已有 partial parts
        S-->>UI: running=false / idle
    else Runtime 异常退出
        RT--xS: process exited
        S->>DB: 记录安全错误与 Thread 状态
        S-->>UI: 可恢复错误
        U->>UI: 在同 Thread 继续对话
        UI->>API: resume turn
        API->>DB: 重新读取最新 MCP revisions
        API->>RT: 新 Runtime + 既有 Claude session id
        RT->>M: 新建 MCP ClientSession
        RT-->>UI: SSE 继续输出
    end
    Note over RT,M: resume 的是 Agent session；不恢复异常前的 MCP transport/session
    Note over RT,M: Server 不响应 cancel 时按 timeout 关闭连接；UI 不无限等待
~~~

## 12. 旧 CLI 配置：显式、幂等导入与回滚

~~~mermaid
sequenceDiagram
    autonumber
    actor O as 操作员
    participant I as 一次性 Importer
    participant F as 明确提供的旧配置文件
    participant DB as PostgreSQL
    participant UI as Dream Resources

    O->>I: 指定 actor + bounded manifest
    I->>F: 只读文件，不启动 Claude CLI
    I->>I: canonicalize、拒绝 secret、计算 hash
    I->>DB: 查询 import receipt 与目标 revision
    alt 相同 source/config hash 已成功
        DB-->>I: unchanged / no-op
    else 数据库已有更新配置
        DB-->>I: conflict / 不覆盖
    else 可安全导入
        I->>DB: transaction insert Server + receipt
        DB-->>I: imported
    end
    I-->>O: 脱敏结果
    UI->>DB: 正常页面只读 managed-DB 配置
    Note over F,UI: cutover 后业务页面永不读取旧 CLI 配置
~~~

## 13. 验收观察点

| 观察点 | 必须看到 | 不允许出现 |
|---|---|---|
| 列表请求 | capability/list 数据库响应 | discovery、Runtime、CLI |
| 详情请求 | 自动 force=false discovery | inventory 刷新/重试按钮 |
| 匿名 Server | anonymous + inventory | OAuth 操作 |
| OAuth Server | required 后才显示认证；callback 自动提交 | 认证方式选择、复制授权 URL/code |
| 配置变更 | revision++ 后自动加载新 inventory | 旧响应覆盖新 revision |
| 多 Server | partial + per-item error | 一个失败导致整体阻塞 |
| Chat/resume | 每 turn 读取数据库 snapshot | 浏览器传 secret、Runtime 管理配置 |
| 日志与 DTO | trace id、安全错误码、duration | Token、Authorization、callback query、响应正文 |

## 14. 边界与证据入口

- logout 或 endpoint/transport 等安全配置变化时的“撤销”仅承诺 Dream 删除或失效本地加密凭据并禁止后续复用；是否支持 Provider 远端 token revocation 取决于 Provider/标准 SDK，不在图中预设。
- 临时 MCP 配置的 finally 清理覆盖正常完成、应用级异常与 cancel；宿主机非正常退出后的残留治理属于运行时目录生命周期风险，不把它伪装成 MCP session resume 能力。
- stdio、Streamable HTTP、SSE adapter，OAuth metadata/challenge、TTL/timeout、错误缓存和 request tracing 的精确合同见主设计稿对应章节；本图集不复制第二份参数表。
- 实现与验收入口：Dream 详情页组件、typed API、MCP Service/Discovery Coordinator、Chat Snapshot Loader 及真实 Comfy OAuth/SeetaCloud 匿名结果，均在[主设计稿证据索引](./dream-managed-mcp-resources.md#证据索引)中维护。
