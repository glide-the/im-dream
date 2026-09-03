<!-- [输入] Dream Vite 前端、Admin Next.js 16 基线、MCP Apps Browser/Node Host 职责边界。 -->
<!-- [输出] 记录 Dream 必须迁移 Next.js 的决策、改动范围、目标架构、阶段和发布门槛。 -->
<!-- [定位] MCP Apps 的前端框架专项决策；不修改前端代码，不定义 MCP Apps bridge 细节。 -->
<!-- [同步] 2026-09-04：Next.js 迁移确定纳入 MCP Apps 交付，现有问题统一视为工作量和验收项。 -->

# Dream 前端 Next.js 迁移决策与范围

> 状态：设计评审稿，未实施
>
> 结论：**Dream Web 必须从 Vite 迁移到自托管 Next.js App Router，迁移属于 MCP Apps 的交付范围。** MCP Apps 规范本身不限定框架，但 IM 选择用 Next.js 统一 Web Shell、Server/Client 边界、同源 Host 接口、运行时配置和 Node 发布单元。Browser Runtime 作为 Client Component 运行；`PersistentConnectorManager` 由 Next Node 进程启动时创建并长期持有，Route Handler 只做认证、作用域校验和协议适配。Python 只提供受控配置。现有路由、认证、SSE、WebSocket、CSS、部署和测试耦合只决定迁移工作量与验收，不再决定是否迁移。

参考资料（访问日期：2026-09-04）：

- [Next.js Backend for Frontend](https://nextjs.org/docs/app/guides/backend-for-frontend)
- [Next.js Route Handlers](https://nextjs.org/docs/app/api-reference/file-conventions/route)
- [Next.js Server and Client Components](https://nextjs.org/docs/app/getting-started/server-and-client-components)
- [Next.js Self-Hosting](https://nextjs.org/docs/app/guides/self-hosting)
- [Next.js standalone output](https://nextjs.org/docs/app/api-reference/config/next-config-js/output)

## 1. 背景与问题

Dream 当前是 React 19 + Vite 8 SPA，构建后由 Nginx 提供静态页面；Python 负责既有业务 API、认证、Claude Agent、MCP 配置和实时流。目标形态改为自托管 Next.js App Router：页面和 Browser Runtime 使用 React Server/Client Component 边界，Next Node 侧提供同源 Host 接口并承载进程级 Apps Runtime。

`PersistentConnectorManager` 持有物理 MCP session；Apps Runtime 同时保存 tool catalog、UI resource、App instance、事件顺序和 Browser 订阅。它在 Node 进程启动时创建，Route Handler 是调用它的请求适配器，不把长期连接和状态绑定到单次请求生命周期。

本稿不再判断“是否迁移”，而是确定迁移如何完成：

1. 先用 Next.js compatibility shell 接住现有 React SPA 行为；
2. 在 Next Node 进程建立 Apps Runtime composition root 和同源 Host 接口；
3. 再把自制路由、页面壳和公共资源逐步迁入 App Router；
4. 路由、认证、SSE、WebSocket、CSS、部署和测试问题全部进入工作量清单与发布验收。

## 2. 目标与边界

### 2.1 目标

- 量化当前 Dream 前端迁移面。
- 判断 Admin 的 Node/Next.js 基线能复用什么。
- 定义 compatibility shell、完整 App Router 与 Node Apps Runtime 的迁移顺序。
- 保持 Python 认证、OAuth、Agent SSE、MCP 配置和数据库边界不变；仅新增受控 Node 配置接口。
- 给出可回滚的迁移路径及每阶段发布门槛。

### 2.2 非目标

- 不在本任务中迁移或修改前端业务代码。
- 不借迁移重做认证、Claude Agent、Thread、EventBus、SSE parser 或 MCP 配置。
- 不把 Dream 用户前端并入 Admin 仓库。
- 不让 Next Route Handler 持有 MCP Client/session 或 App instance。
- 不复制 Admin 的 Refine、RBAC、Drizzle、Gateway、账本或管理员 session。

## 3. 概念与规则

### 3.1 四个独立运行边界

| 边界 | 当前/目标职责 | 与 Next.js 的关系 |
|---|---|---|
| Dream Web Shell | Chat、创作页面、Browser Runtime 挂载点、fallback | 迁移为 Next.js App Router |
| Browser Runtime | iframe、Host 侧 AppBridge 和 Host/View 消息处理 | Next.js Client Component，只在浏览器运行 |
| Node Apps Runtime | `PersistentConnectorManager`、tool catalog、UI resource、App instance、事件与 Browser channel | Next Node 进程级服务；Route Handler 只是适配器 |
| Python Config Provider | managed MCP 静态配置、turn-scoped 明文配置、credential/OAuth 投影 | 只提供配置；不持有 Apps session，不参与 UI 链路 |

```mermaid
flowchart LR
    USER["用户浏览器"] --> WEB["Next.js App Router<br/>Dream Web Shell"]
    WEB --> RUNTIME["Client Component<br/>AppBridge + iframe"]
    RUNTIME <--> ADAPTER["同源 Host 接口<br/>Route Handler adapter"]
    ADAPTER <--> NODE["进程级 Node Apps Runtime<br/>MCP session、resource、instance、events"]
    NODE <--> MCP["MCP Server 模块"]
    PY["Python Config Provider<br/>静态配置 + turn-scoped 明文配置"] -."仅配置".-> NODE
```

### 3.2 Next.js 内部职责

- **App Router**：接管页面、layout、metadata、Web 静态公开资源和导航；Python 提供的动态公开资源绕过 Next catch-all。
- **Client Component**：承载 Browser Runtime、AppBridge、iframe、浏览器状态和交互事件。
- **Route Handler**：提供同源 HTTP 命令、资源接口和 SSE 事件流；执行登录态、Thread、Server、tool 与 instance scope 校验。
- **Apps Runtime composition root**：在自托管 Next Node server startup 时创建 `PersistentConnectorManager`，供 Route Handler 调用；不按请求重建。

## 4. Dream 当前前端规模

### 4.1 代码与浏览器依赖

只统计生产源码并排除 `__tests__` / `*.test.*`：

| 项目 | 当前规模 |
|---|---:|
| 生产源码 | 261 个文件，78,513 行 |
| TypeScript / TSX / CSS | 119 / 120 / 22 个文件 |
| CSS | 11,211 行，313,416 bytes |
| `src` 测试 | 70 个文件，14,680 行 |
| E2E | 38 个 Playwright spec，15,117 行 |
| API client | 13 个文件，5,614 行 |
| `public` | 9 个文件，约 39.8 MB |

关键耦合：

- `/Users/dmeck/project/ink-dream-memory/frontend/src/App.tsx:232` 起的应用壳共 2,356 行。
- `/Users/dmeck/project/ink-dream-memory/frontend/src/router/story-workspace.tsx:126` 与 `/Users/dmeck/project/ink-dream-memory/frontend/src/router/storyWorkspacePath.ts:20` 共约 805 行自制路由。
- 90 个生产 TS/TSX 模块出现 `window`、`document`、`localStorage`、WebSocket、AudioContext 等浏览器专属全局。
- 106 个生产模块直接使用 React hooks，当前没有 `'use client'` 文件。
- `/Users/dmeck/project/ink-dream-memory/frontend/src/App.tsx:235` 和 `/Users/dmeck/project/ink-dream-memory/frontend/src/router/story-workspace.tsx:259` 在 render/state initializer 阶段读取 `window`，不能只靠补 `'use client'` 获得安全 SSR；兼容壳必须真正 `ssr:false` 动态挂载。

### 4.2 当前构建和运行方式

- `/Users/dmeck/project/ink-dream-memory/frontend/package.json:6-13` 使用 Vite dev/build/preview。
- `/Users/dmeck/project/ink-dream-memory/frontend/Dockerfile:25-57` 使用 Node 22 构建，最终以 Nginx 1.27 提供 `dist`。
- `/Users/dmeck/project/ink-dream-memory/frontend/docker-entrypoint.sh:9-25` 在容器启动时把 `API_BASE_URL`、`WS_BASE_URL` 写入 `window.__INK_RUNTIME_CONFIG__`。
- `/Users/dmeck/project/ink-dream-memory/frontend/src/lib/apiBase.ts:27-73` 按 runtime config → Vite env → same-origin 解析 REST/WS 地址。
- `/Users/dmeck/project/ink-dream-memory/frontend/nginx.conf.template:24-36` 把 API、认证、OAuth、动态 SEO 资源与 SPA fallback 分流，并为 SSE 关闭代理缓冲。

迁移后前端从静态 Nginx 进程变成长期 Node Web 进程，必须重新测量运行时内存、健康检查、优雅退出、并发与发布回滚，不能沿用当前 256 MiB Nginx预算。

## 5. 业务链路影响

### 5.1 路由

当前 Story Workspace 有 17 条静态路径和 3 条参数路径，定义在 `/Users/dmeck/project/ink-dream-memory/frontend/src/router/storyWorkspacePath.ts:20-71`；`/`、`/story-workspace` 与 dashboard 还有 `/Users/dmeck/project/ink-dream-memory/frontend/src/router/storyWorkspacePath.ts:135-187` 的规范化语义。导航由 `/Users/dmeck/project/ink-dream-memory/frontend/src/router/story-workspace.tsx:310-385` 的 history/popstate 实现。

最小迁移使用 `app/[[...path]]/page.tsx` client-only catch-all，保留现有路由。完整迁移需要约 20 个 filesystem route、legacy redirect、跨路由 provider 和 `App.tsx` 拆分，属于业务架构重构。

### 5.2 认证与 OAuth

- `/Users/dmeck/project/ink-dream-memory/frontend/src/contexts/AuthContext.tsx:63-114` 从 `localStorage` 读取 JWT，并调用 Python `/api/me` 校验。
- `/Users/dmeck/project/ink-dream-memory/frontend/src/lib/authTokenRefresh.ts:23-47` patch `window.fetch` 接收刷新 token header。
- `/Users/dmeck/project/ink-dream-memory/frontend/src/App.tsx:128-200` 在浏览器处理 MCP OAuth callback，避免 code/state 进入 Python 日志。
- `/Users/dmeck/project/ink-dream-memory/frontend/src/components/Auth/DeviceVerificationPage.tsx:22-78` 让同一路径同时承担 HTML 导航和 GET/POST API；Vite 在 `/Users/dmeck/project/ink-dream-memory/frontend/vite.config.ts:95-117` 按 `Accept: text/html` 区分。

Next compatibility shell 必须保持这些语义。只要 JWT 仍在 localStorage，Next Server Component 就不能成为认证权威，也不能在服务端完成真实用户 session redirect。认证 server 化必须单列决策，不能夹带在路由迁移中。

### 5.3 SSE 与 WebSocket

Dream 的 Agent 和 session SSE 使用浏览器 `fetch()` + `ReadableStream`：

- `/Users/dmeck/project/ink-dream-memory/frontend/src/api/voiceApi.ts:209-313`
- `/Users/dmeck/project/ink-dream-memory/frontend/src/components/chat/ChatPanel.tsx:391-433`
- `/Users/dmeck/project/ink-dream-memory/frontend/src/components/chat/ChatPanel.tsx:843-876`
- `/Users/dmeck/project/ink-dream-memory/frontend/src/hooks/useEditSessionEvents.ts:90-166`
- `/Users/dmeck/project/ink-dream-memory/frontend/src/lib/claude-agent-sse-utils.ts:1`
- `/Users/dmeck/project/ink-dream-memory/frontend/src/lib/claude-agent-transport.ts:1`

语音输入在 `/Users/dmeck/project/ink-dream-memory/frontend/src/hooks/useVoiceInput.ts:150` 创建 WebSocket，并依赖麦克风、AudioContext 与 DOM。

最小迁移继续让浏览器直连既有 Python/Node ingress。若改由 Next 代理，必须逐项验证 chunk flush、禁缓冲、abort、断线重连、`Last-Event-ID`、长超时和 WebSocket upgrade，不能用普通 JSON Route Handler 替代。

### 5.4 环境、CSS 与公开资源

- `import.meta.env` 只出现在 3 个生产文件：`main.tsx`、`App.tsx`、`apiBase.ts`，替换量不大。
- 当前启动时可变的 `runtime-config.js` 不能直接换成 build-time `NEXT_PUBLIC_*`；Next image 仍需提供无缓存的 runtime config。
- 22 个 CSS 文件有 28 处组件侧全局 import。兼容壳可保持加载顺序；完整 App Router 才需要整理 global/module 边界。
- `/Users/dmeck/project/ink-dream-memory/frontend/index.html:10-100` 的 metadata、OG/Twitter、JSON-LD 和字体 preload 需要迁到 Next root layout。
- `robots.txt`、`sitemap.xml`、`llms.txt` 目前由 Python 动态生成，不能被 Next catch-all 吞掉。

## 6. Admin Node 框架的复用边界

`/Users/dmeck/project/ink-admin-memory/README.md:21-28` 使用 Next.js 16 App Router、React 19、TypeScript、Refine 和 TanStack Query；`/Users/dmeck/project/ink-admin-memory/package.json:22-32` 提供 Next build/start、Vitest 和 Playwright；`/Users/dmeck/project/ink-admin-memory/next.config.js:15-23` 提供 strict mode 与可选 standalone output。

### 6.1 可以参考

- `/Users/dmeck/project/ink-admin-memory/app/layout.tsx:1` 的 root metadata、viewport、font、theme 与 Provider 组织。
- `/Users/dmeck/project/ink-admin-memory/app/app/providers.tsx:1` 的 Client Provider island。
- 显式 App Router page/layout 和薄 Route Handler → service 分层。
- `/Users/dmeck/project/ink-admin-memory/docker/Dockerfile:5-67` 的 Node 22、非 root、tini、standalone 多阶段镜像思路。
- Playwright 复用系统 Chrome、失败 trace/video/screenshot 和已有服务的测试方式。
- HTTP SSE 的 `ReadableStream`、cancel 和 abort 处理模式；只复用流式处理技术，不复用 Gateway 领域。

### 6.2 不得直接复用

- Refine CRUD、Admin 导航和 access provider。
- PostgreSQL 管理员 session、管理员 cookie、RBAC 和 bootstrap。
- `@ink-memory/db`、embedded PostgreSQL、Drizzle migration 或应用内直接 SQL。
- Gateway 的模型凭据、计费、账本、限流和协议转换。
- Admin Docker entrypoint、DB volume、migration 与 secret。
- `/Users/dmeck/project/ink-admin-memory/AGENTS.md:4` 明确排除用户业务前端；Dream 不能直接并入 Admin 仓库。

Admin 是框架和运维模式参考，不是 Dream 用户前端的宿主。

## 7. 候选方案

| 方案 | MCP Apps 收益 | 改动与风险 | 结论 |
|---|---|---|---|
| Next.js compatibility shell + 进程级 Apps Runtime | 先取得 Next Web/Node 基线，同时保留现有 React 页面行为 | 约 30–35 个配置、部署和文档文件，新增 Next app/layout/composition root | **迁移第一阶段** |
| Idiomatic App Router + 同一 Apps Runtime | 形成最终 Server/Client 边界、同源 Host 接口和统一发布模型 | 预计触及 80–150 个业务模块；需要逐路由迁移 auth、CSS、实时流 | **最终目标** |
| Vite SPA + 独立 Node Apps Runtime | 协议上可行 | 不进入已经确定的 Next.js 目标架构 | 不选；仅作迁移回滚 |
| Apps Host 作为 request-local Route Handler 对象 | 无 | 请求结束或实例切换会丢失连接权威 | 拒绝；Route Handler 只能调用进程级 Runtime |
| Dream 并入 Admin | 无 MCP Apps 独有收益 | 违反仓库边界，混入 RBAC/DB/Gateway 领域 | 拒绝 |

Next.js 已提供本设计需要的框架能力：App Router、Server/Client Component 边界、Route Handler、自托管 streaming、运行时环境变量和 server startup 注册。IM 采用自托管 Node 部署，并把 Apps Runtime 放在进程 composition root；因此浏览器依赖、SSR 边界、Host API 和长期状态都有明确位置。

IM 的 Apps channel 确定为 Route Handler HTTP 命令与 SSE 事件流；Apps Runtime 状态位于自托管 Node 进程，不位于请求对象。现有语音 WebSocket 继续直连原有入口，不要求 Next 接管 upgrade。

Admin 当前 Next 16.1.6 已提供可复用的 App Router、Client Provider、Route Handler、HTTP SSE、Node 22 镜像和 Playwright 基线。它没有直接提供 Dream Apps Runtime，但已经覆盖框架、构建、流式请求和部署模式；Dream 需要新增的是进程级 `PersistentConnectorManager` 与 Host adapter，而不是重新判断是否采用 Next.js。

## 8. 目标部署

目标部署：

```mermaid
flowchart TB
    INGRESS["同域 Ingress"]
    subgraph NEXT["自托管 Next.js Node"]
        WEB["App Router<br/>Dream Web Shell"]
        API["Host Route Handlers<br/>HTTP commands + SSE events"]
        NODE["进程级 Apps Runtime<br/>PersistentConnectorManager + Host"]
        API <--> NODE
    end
    BROWSER["Client Component<br/>AppBridge + iframe"]
    PY["Python Dream<br/>业务 API + Managed MCP Config Provider"]
    MCP["MCP Server 模块"]

    INGRESS -->|"页面与静态资源"| WEB
    WEB --> BROWSER
    BROWSER <--> API
    INGRESS -->|"业务 API、Agent SSE、OAuth"| PY
    PY -."仅静态配置 / turn-scoped 明文配置".-> NODE
    NODE <--> MCP
```

Next Node 进程是 Web 与 Apps Host 的共同发布单元。Apps Runtime 保持独立模块和生命周期，由进程启动/退出管理；Route Handler 不拥有连接。Python 仍是业务 API 与 managed MCP 配置源，不参与 UI 协议。

## 9. Next.js 迁移阶段

### Stage 1：Compatibility shell

- 在 Dream 仓库建立 Next 16 基线。
- 用 client-only catch-all 和 `ssr:false` 动态挂载现有 App。
- 保留 custom router、localStorage auth、Python API、SSE/WS 和 OAuth callback。
- 保留启动时 runtime config，不把它降级成 build-time 环境变量。

验收：现有主要页面 URL、刷新、OAuth callback、Agent streaming、语音 WebSocket 和动态 SEO 资源与 Vite 版本一致。回滚为原 Nginx `dist` image。

### Stage 2：Apps Runtime 与构建部署切换

- 在 Next Node 进程 composition root 创建 `PersistentConnectorManager` 和 Apps Runtime。
- Route Handler 提供同源 Host 命令与事件接口，只做认证、scope 和协议适配。
- Browser Runtime 迁为 Client Component，挂载 AppBridge 与 iframe。
- 完成 Python 受控配置接口和 Node 建连。

至少影响：

- `frontend/package.json`、lockfile、tsconfig、ESLint、Vite config、index、main、Dockerfile、entrypoint、Nginx template；
- `.github/workflows/ci-frontend.yml`、`.github/workflows/deploy-frontend.yml`；
- 根 `docker-compose.yml`；
- `deploy/docker`、`deploy/local`、`deploy/google-cloud`、`deploy/remote-ssh`、`deploy/autodl-ssh`；
- README、前端与部署 `.folder.md`。

当前 AutoDL 脚本检查 `dist/index.html` 并启动 `vite preview`，Cloud Run 前端使用端口 80 和 256 MiB；这些不能直接沿用。

验收：同一 Next 发布单元可以提供 Dream 页面、Host 接口和进程级 Apps Runtime；连续请求复用同一 connection generation；Node 重启后以新 epoch 重连；Browser 不获得 credential。回滚为 Stage 1 Next shell 或迁移前 Vite image。

### Stage 3：逐路由迁移

先迁静态 Settings/资源页，再迁 Story Workspace，Chat、Dream、Writing 最后。每次只替换一组路由，不同时重做认证或流协议。

### Stage 4：清理旧壳

删除 custom history adapter、Vite test harness 和遗留 static deploy 前，必须确认所有 filesystem route、OAuth、安全回调、SSE/WS 和 38 条 E2E journey 已切换。

## 10. 测试与验收

| 场景 | 可观察标准 |
|---|---|
| Compatibility shell | 现有 URL 直接打开和刷新均返回正确页面；无 SSR `window is not defined` |
| Next Browser Runtime | AppBridge 与 iframe 只在 Client Component 初始化；服务端渲染不访问 `window`、`document` 或 `localStorage` |
| 进程级 Apps Runtime | 多次 Route Handler 请求复用同一 Node epoch 和 connection generation；请求结束不销毁 MCP session |
| OAuth callback | code/state 只由前端专用路径消费，不进入通用 Python request log |
| Agent SSE | 首 chunk、连续 chunk、取消、断线恢复与 Vite 基线一致，无代理缓冲 |
| Voice WebSocket | 能建立、关闭并在页面卸载时释放；Next 不拦截 upgrade |
| Runtime config | 同一 image 启动时可切换 API/WS base，不需重新 build |
| CSS | 现有页面关键视觉回归截图无布局、字体、主题和层叠顺序差异；全局样式只从允许的 App Router 入口加载 |
| 动态公开资源 | `robots.txt`、`sitemap.xml`、`llms.txt` 继续来自 Python |
| 部署 | Next Node 健康检查、优雅退出、端口、内存与回滚镜像在每个目标部署拓扑通过；不再依赖 `dist/index.html` 或 `vite preview` |
| E2E | 38 个 spec 的核心 journey 在目标 Web server 上通过 |
| Node Apps Runtime | Next Node 重启后 epoch 变化，Browser 重新绑定，Connector 使用最新受控配置重连 |
| 回滚 | 切回旧 Vite image 后 Python API、数据和 OAuth 状态无需迁移 |

现有测试中有 15 个文件直接导入 Vite server、5 个文件注入 `/@vite/client` 或 React refresh、27 个文件写有 5173 端口。Compatibility shell 可暂时保留 Vite test-only harness；彻底移除 Vite 至少需要修改约 20 个测试文件。

## 11. Go / No-Go

Next.js 迁移决策已经为 **Go**，不再设置“是否采用 Next.js”的条件。实施按 Stage 1—4 推进，工作量增加不改变目标架构。

每阶段只有满足以下条件才允许发布到下一阶段：

- compatibility shell 的路由、OAuth、Agent SSE、语音 WebSocket、runtime config 和 E2E 基线通过；
- Apps Runtime 是进程级服务，Route Handler 请求结束不释放 MCP session；
- Python 仍是 managed MCP 配置和 credential 事实源，但不参与 Apps UI 链路；
- Browser 和 App View 不获得 MCP credential；
- rollback image 与回滚步骤可执行。

以下情况阻止当前阶段发布，但不撤销 Next.js 迁移决策：

- 路由、认证、SSE、WebSocket 或 OAuth callback 与当前用户行为不一致；
- Apps Runtime 被实现成 request-local Route Handler 对象；
- 计划直接复制 Admin RBAC、DB 或 Gateway；
- 无法验证 credential 隔离、连接重建或回滚路径。

## 12. 调研命令回执

| 命令 | 退出码 | 关键输出 |
|---|---:|---|
| `find frontend/src ...` 统计生产 `.ts/.tsx/.css` | 0 | 261 files，78,513 lines |
| `find frontend/e2e -name '*.spec.ts' ...` | 0 | 38 specs，15,117 lines |
| `rg -l` 统计生产源码浏览器专属全局 | 0 | 90 files |
| `rg -l "from ['\"']vite['\"']" frontend/src frontend/e2e` | 0 | 15 files 直接依赖 Vite test harness |
| 本地 Markdown link 检查 | 0 | `6` files，`10` local links，`0` broken |
| Frontend Node + `mermaid.parse()` | 0 | `16` Mermaid blocks，`0` failures |
