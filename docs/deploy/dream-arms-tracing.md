<!-- [Input] Dream server instrumentation, W3C propagation and the existing Admin ARMS deployment contract. -->
<!-- [Output] Private configuration, trace lookup, failure diagnosis and acceptance boundaries. -->
<!-- [Pos] Dream server operations guide; deployment and cloud configuration require separate authorization. -->

# Dream 调用链查询与接入

## 范围与入口

Dream Web 的 Next.js BFF、Python HTTP 请求、Admin HTTP 调用和本地插件校验采用 OpenTelemetry。Deck 页面首次加载先等待 `POST /api/decks/defaults/reconcile`，随后发起目录读取；两个浏览器 HTTP 请求分别拥有 Trace ID，页面顺序保持现行实现。

本轮交付源码、隔离合同和跨语言集成验证。服务部署、服务重启、云端配置和真实 ARMS 数据到达分别验收。真实 reconcile 会写业务数据，执行需有对应业务授权。

既有 Admin 合同见 [Admin 监控发布部署要求](https://github.com/glide-the/dream-im-platform/blob/main/docs/observability-deployment-requirements.md)和[Admin 运维手册](https://app.notion.com/p/41830b7547c3810d9056c656f54c35af)。已读取的 2026-11-15 运维记录使用 `cn-beijing`、`default-cms-1230976711767463-cn-beijing`、应用 `ink-memory-admin`，HTTP、Next.js、undici 与 pg 由服务器 preload 管理。部署人员核对现场配置、W3C 提取和父级采样继续生效。资源与数据库指标使用既有 Prometheus 数据源，Trace 使用 ARMS 调用链存储。

## 服务端装配与配置

Python 入口为 `backend/server.py` 的 `TracedFastAPI`，容器仍执行原 `uvicorn server:app`。普通 `uv sync --locked` 可运行关闭追踪的路径；启用服务使用 `uv sync --locked --extra tracing`。容器沿原带 hash 的 `requirements.txt` 安装，导出命令为 `uv export --extra tracing --no-dev --no-emit-project --output-file requirements.txt`。

Next 的 `createApiProxy` 接入独立 provider，通过 `AsyncLocalStorage` 传递当前上下文，保持 Next 全局 provider 和已有 preload 的所有权。关闭追踪时桥接模块跳过 SDK import。Python 同样延迟加载可选依赖。Dream 手动接缝覆盖原认证和 HTTP DTO 边界，服务端无需叠加 FastAPI、httpx、Next 或 undici 自动探针。Admin 保留现有服务器探针，仓库无需修改。

部署方将以下项注入两个服务进程的私有配置文件，保留受限权限、现有启动设置和回滚制品。服务分别设置应用名；建议值为 `ink-memory-dream-bff` 和 `ink-memory-dream-api`，云端验收使用实际配置值。

| 配置 | 默认与约束 | 用途 |
| --- | --- | --- |
| `INK_TRACE_ENABLED` | 未设置时关闭；启用值为 `true` | 控制本进程追踪 |
| `OTEL_SERVICE_NAME` | 启用时必填 | ARMS 应用名 |
| `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` | 启用时必填，完整 HTTP(S) Trace 接入点 | 使用同一北京工作空间授权的 HTTP 接收入口；私有 URL 可含授权信息 |
| `OTEL_EXPORTER_OTLP_TRACES_HEADERS` | 按接入点要求配置 | 私有授权头；SDK 同时支持标准通用 OTLP headers |
| `INK_TRACE_CONTEXT_SECRET` | 启用时必填，至少 32 字节，两服务相同 | BFF 到 Python 的上下文签名；专用随机密钥 |
| `OTEL_TRACES_SAMPLER_ARG` | 根 Trace 比例 `0.1`，范围 `0..1` | 有父上下文时跟随父级决定 |
| `OTEL_BSP_MAX_QUEUE_SIZE` | 2048，正整数 | 每进程最大待导出 Span 数 |
| `OTEL_BSP_MAX_EXPORT_BATCH_SIZE` | 512，正整数，至多等于队列 | 每批最大 Span 数 |
| `OTEL_BSP_SCHEDULE_DELAY` | 5000 毫秒，正整数 | 批处理间隔 |

导出超时为三秒，SDK 采用有界批处理；队列满时丢弃观测数据。每进程预算需要结合 worker 数和主机容量核对。Python 在装配时读取配置，BFF 在首次 API 调用时初始化；修改通过另行授权的原发布流程生效。配置缺失、SDK 缺失或初始化失败时记录固定诊断并继续原业务路径；导出失败独立于业务响应，凭据和异常正文保留在私有配置与原业务边界内。

阿里云接入点按控制台地域、网络和 HTTP 协议获取，见[官方 Python 接入说明](https://www.alibabacloud.com/help/zh/opentelemetry/user-guide/use-managed-service-for-opentelemetry-to-submit-the-trace-data-of-python-applications)。部署方须核对该接入点与已有 ARMS 应用处于同一查询工作空间，使用同一个 Trace ID 在控制台确认跨应用拼接。通用 OTLP 接收成功与 ARMS 云端查询成功分别留存证据。

服务配置放在独立服务器环境文件，避开移动构建读取的 `backend/.env` 和 `frontend/.env.local`。iOS `bundle-node.py` 检测到 `OTEL_*`、`ARMS_*` 或 `INK_TRACE_*` 赋值时在复制前停止；`bundle-python.py` 包含可选依赖桥接模块。端侧 Python 使用原 FastAPI 装配，本次未启用设备追踪，也未进行设备构建或验收。

## 传播与采集规则

BFF 为每次公开请求创建根 Span，忽略浏览器提供的 `traceparent`、`tracestate`、`baggage`、诊断字段和签名。向 Python 注入 W3C `traceparent`，以 HMAC-SHA256 对秒级时间戳、traceparent、HTTP 方法和解码路径签名；Python 接受六十秒窗口内有效的专用密钥签名，拒绝重复字段。签名校验仅决定 Span 父级，原 OAuth、Cookie、CSRF、scope、principal 和资源归属照常校验。

Python 对直接客户端、过期签名、密钥不匹配和无签名请求创建根 Trace。服务间须保持时钟同步；BFF 与 Python 使用同一个入口路径。`tracestate` 与 `baggage` 在 Dream 边界丢弃。向 Admin 仅传播当前服务端 `traceparent`；Admin 已有探针负责生成 HTTP、pg 子段。原 `x-request-id`、DTO `request_id` 和业务幂等键保持原有生成与校验，Trace ID 用于诊断关联。

只记录固定阶段名、HTTP 方法、路由模板、状态、尝试次数、服务地址和耗时。Python 路由模板包含 `/api/decks/defaults/reconcile`，BFF 共享入口模板为 `/api/[[...path]]`。导出内容排除 Cookie、Authorization、请求与响应正文、查询参数、用户标识、插件路径与摘要、SQL 参数、模型和工具正文；错误状态只保存状态码。应用日志只增加安全关联字段，不新增日志或指标 exporter。

## 一次请求的耗时结构

| Span | 含义 |
| --- | --- |
| `POST /api/[[...path]]` | BFF 从处理请求到响应流完成的总耗时 |
| `bff.authentication` | Cookie/Origin/CSRF 检查与可选 Admin handle 解析；原生 Bearer 复用原分支 |
| `admin.http`（BFF） | 原 Admin handle / capability / profile HTTP 与响应读取 |
| `dream.http` | BFF 到 Python 的 HTTP 与响应流 |
| `POST /api/decks/defaults/reconcile` | Python 完整请求，包括认证、业务与响应发送 |
| `dream.authentication` | 原 JWT/JWKS、服务令牌、capabilities、principal 链路 |
| `admin.oauth.token`、`admin.jwks` | 原冷路径的令牌与 JWKS 获取 |
| `admin.http`（Python） | 每次原 HTTP DTO 尝试，`dream.transport.attempt` 区分现有只读恢复 |
| `dream.deck.default_plugin.resolve` | Admin 默认插件解析 |
| `dream.deck.artifact.verify` | 本机制品校验 |
| `dream.deck.cli.compatibility` | 本机 CLI 兼容性检查 |
| `dream.deck.reconcile` | Admin 对账与原回执恢复 |
| Admin HTTP / pg 子段 | 由原服务器探针提供，区分事务、SQL 与连接申请 |

```mermaid
sequenceDiagram
    participant U as 浏览器
    participant B as Dream BFF
    participant P as Dream Python
    participant A as Admin
    participant D as PostgreSQL
    participant R as ARMS
    U->>B: POST /api/decks/defaults/reconcile
    B->>B: 创建根 Trace，验证原 Cookie/Origin/CSRF
    opt Browser handle
        B->>A: handle resolve + traceparent
        A-->>B: 原 access token DTO
    end
    B->>P: 原请求 + traceparent + 签名
    P->>P: 校验签名，开始 SERVER Span
    P->>A: 原认证与 principal HTTP + traceparent
    A-->>P: 原身份与能力 DTO
    P->>A: deck.default-plugin.resolve + traceparent
    A-->>P: 原安装候选
    P->>P: 制品摘要校验与 CLI 兼容性检查
    P->>A: deck.reconcile-default + traceparent
    A->>D: 原事务与业务 SQL
    D-->>A: 原事务结果
    A-->>P: 原 request_id 与业务结果
    P-->>B: 原结果 + X-Trace-Id / X-Trace-Sampled
    B-->>U: 原结果 + BFF Trace ID / sampled / linked
    B-->>R: 采样后批量导出安全 Span
    P-->>R: 采样后批量导出安全 Span
    A-->>R: 原探针父子段
```

```mermaid
sequenceDiagram
    participant U as 浏览器
    participant B as Dream BFF
    participant P as Dream Python
    participant A as Admin
    participant O as 运维人员
    U->>B: 原 API 请求
    B->>P: 原请求与签名上下文
    alt 签名过期或配置不同
        P->>P: 创建独立根 Trace，继续原鉴权
        P-->>B: 原业务结果 + Python Trace ID
        B-->>U: BFF Trace ID，X-Trace-Linked=0
        O->>O: 核对双端配置、时钟和中间代理头转发
    else 原认证或插件验证失败
        P-->>B: 原 401/403/409 等响应 + Trace ID
        B-->>U: 保留原状态和正文，附关联头
        O->>O: 用 Trace 定位失败阶段，沿原业务恢复规则处理
    else 导出不可用
        P->>A: 原 Admin 操作
        A-->>P: 原结果
        P-->>B: 原业务结果 + Trace ID
        B-->>U: 原业务结果 + sampled 标记
        O->>O: 核对固定导出诊断、接入点与采样，再验云端
    end
```

## 从浏览器或日志定位

1. 在开发者工具 Network 找到 `POST /api/decks/defaults/reconcile`，记录请求时间、状态及响应头 `X-Trace-Id`、`X-Trace-Sampled`、`X-Trace-Linked`。`linked=1` 表示 Python 响应与 BFF Trace ID 相同；该字段覆盖已到达 Python 的共享代理请求，BFF 提前拒绝会返回 `0`。
2. 服务日志以 `trace_id` 检索。BFF 输出 `dream.request` JSON；Python 的 `dream.trace` 输出 `trace_id`、`span_id`、`sampled`、方法、路由模板、状态和 `duration_ms`。原 Uvicorn 单行访问日志只有路径和状态，无法反推唯一 Trace ID。
3. 打开[北京 ARMS 应用列表](https://cmsnext.console.aliyun.com/next/region/cn-beijing/workspace/default-cms-1230976711767463-cn-beijing/app/apm/application-list)，选择实际 `OTEL_SERVICE_NAME`。在提供服务查 `POST /api/decks/defaults/reconcile`，或进入调用链分析按 Trace ID 和对应时间窗口查询。接口请求方法和路径应以 Python Span 的精确名称核对。操作参见[官方调用链查询说明](https://www.alibabacloud.com/help/zh/arms/application-monitoring/user-guide/trace-query)。
4. 展开 BFF、Python 和 `ink-memory-admin` 的父子段，比较认证、插件解析、本地制品、CLI 校验、对账及 Admin pg 子段。连接申请可能包含排队与新连接成本，具体等待类型结合数据库统计判断。

| 现象 | 判断与下一步 |
| --- | --- |
| BFF 无关联头、日志无追踪字段 | 核对显式开关、SDK 和配置初始化；确认经过共享 BFF API 入口 |
| `X-Trace-Sampled=0` | 根采样未命中；可保留日志关联，按另行授权的采样配置安排后续观测 |
| `sampled=1`，云端无 Trace | 核对时间/地域/工作空间、导出诊断、网络、授权及接收点；该标记仅表达本地采样决定 |
| `linked=0`，请求到达 Python | 对比双端日志时间与 Trace ID，核对签名密钥、时钟、路径和代理头；业务鉴权继续有效 |
| Python 下游 Span 存在，Admin 单独成链 | 核对 Admin preload 的 W3C extractor、父级采样、代理转发及云端接收工作空间 |
| Admin HTTP 段存在，pg 段缺失 | 核对原 pg 探针与实际数据库调用；缓存命中和提前失败按业务回执确认 |

## 验证与发布证据

隔离验证走生产 BFF 工厂、普通认证依赖、Deck 路由、插件校验调用和真实 Admin HTTP 构包，外部身份、制品与 Admin 响应使用合成输入，接收端使用内存 exporter 和随机 loopback 端口。测试中的 `admin.fixture.request` 为传播接收替身，云端 Admin/pg 子段由后续部署验收确认。

对应命令和结果维护在[执行记录](../exec/dream-arms-tracing-20261118.md)。文档路径、清单和 Mermaid 检查归文档验证。PR 检查与合并归远程交付；云端出现同一个 Trace ID 的 BFF、Python、Admin 和 pg 段后，方可记录 ARMS 到达验收。
