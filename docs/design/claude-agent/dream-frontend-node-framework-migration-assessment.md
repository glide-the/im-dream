<!-- [输入] 54f3bbe5 的 frontend workspace、Next.js App Router、MCP Apps Runtime package 与当前技术验收回执。 -->
<!-- [输出] 定义 Dream Web 当前 source ownership、依赖方向、构建入口、状态语义、验收证据与剩余缺口；迁移期内容仅作历史附录。 -->
<!-- [定位] Dream Web / MCP Apps 当前架构真相源；不定义 Python 业务 API 或 iframe 协议细节。 -->
<!-- [同步] 2026-09-06：迁移已完成，文档由未来式迁移计划重构为 54f3bbe5 当前架构与显式历史记录。 -->

# Dream Web 当前 Next.js 架构与迁移历史

> 代码基线：`54f3bbe539b086035bce5900618bf3d7ae5b9372`。
>
> 当前结论：Dream Web 已是 Next.js `16.1.6` + React `19.1.0` + pnpm workspace。`frontend/` 是唯一 workspace、Web package 和 Next 项目根；`frontend/app/**` 是唯一 App Router；`frontend/app/_dream/**` 是唯一 Dream 应用源码；`frontend/packages/mcp-apps-runtime/src/**` 是合法且唯一的 server-only MCP Apps Runtime package。
>
> MCP Apps 状态：Phase 0—3 provider-free 技术验证已完成，但真实外部 Server、真实账号/OAuth、公开应用发布和生产运维验收未完成；`productionAppsEffective=false`。

当前 MCP Apps 技术结论与逐条命令见[当前候选技术验收](../../exec/mcp-apps/current-candidate-validation.md)。MCP Apps 产品链路见[主设计](./mcp-apps-integration-strategy.md)。

## 1. 背景与问题

早期文档把 Dream Web 描述为 Vite SPA，随后又记录了 `frontend/app/` 嵌套 Next 项目和混放于应用树内的 Node Runtime。这些描述只对应 2026-09-05 之前的迁移阶段，不再是当前实现或操作指南。

代码基线 `54f3bbe5` 已完成结构收敛：

- 根 Next scripts 不再带 `app` 位置参数；
- Next config、TypeScript config 和 lock 都位于 `frontend/`；
- `frontend/app/app/**`、`frontend/src/**`、`frontend/vite.config.*` 和 `frontend/package-lock.json` 均不存在；
- Dream 浏览器代码只在私有、不可路由的 `frontend/app/_dream/**`；
- Node MCP Apps Runtime 已从应用树移入 `frontend/packages/mcp-apps-runtime/src/**`；
- `[serverRef]/route.ts` transport Route 是同源 HTTP 薄适配，不拥有身份、业务数据或上游连接生命周期；status/sandbox Route 的反向 import 另列为代码缺口；
- Python 继续拥有认证、Thread/Run/Workspace、managed MCP 配置和 PostgreSQL 业务访问。

因此本文的任务不再是决定或安排迁移，而是固定当前边界、记录已验证事实和指出仍缺的生产证据。

## 2. 目标与边界

### 2.1 目标

- 为 Web、Browser Host、Route Handler、Node Runtime package 和 Python API 建立唯一 source ownership。
- 固定 pnpm workspace、lock、build/start/standalone 入口。
- 明确 server-only 依赖方向和同源 MCP Apps transport。
- 区分代码存在、技术验证、公开应用和生产启用。
- 保留必要迁移历史，但不让历史路径、命令或验收继续指导当前工作。

### 2.2 非目标

- 不把认证、业务数据、Thread、SSE、OAuth 或 managed MCP 权威迁入 Next.js。
- 不在 Route Handler 创建第二套业务 API、私有 Apps 协议或 request-local 上游 session owner。
- 不把 Admin 的 RBAC、Drizzle、Gateway 或数据库 package 复制进 Dream Web。
- 不以技术 preview 回执代替真实账号、真实外部 Server、真实 OAuth、公开应用或生产发布验收。
- 不通过 `INK_ENVIRONMENT` 等部署环境名改变业务路径或 Apps 状态机。

## 3. 当前目录与 source ownership

```text
frontend/                              # 唯一 workspace/Web package/Next root
├── package.json                       # dev/build/start/build:docker
├── pnpm-workspace.yaml                # packages: [".", "packages/*"]
├── pnpm-lock.yaml                     # 唯一 Node lock
├── next.config.js                     # 唯一 Next config
├── next-env.d.ts
├── tsconfig.json
├── app/                               # 唯一 App Router
│   ├── layout.tsx
│   ├── client-shell.tsx               # Dream Browser compatibility boundary
│   ├── [[...path]]/page.tsx
│   ├── api/
│   │   ├── health/route.ts
│   │   └── mcp-apps/
│   │       ├── phase1-status/route.ts
│   │       └── [serverRef]/route.ts   # GET/POST/DELETE 薄适配
│   ├── mcp-apps-sandbox/route.ts
│   ├── robots.txt/route.ts
│   ├── sitemap.xml/route.ts
│   ├── llms.txt/route.ts
│   └── _dream/                        # 唯一 Dream 应用源码；不是 route segment
│       ├── App.tsx
│       ├── api/                       # Browser REST/SSE clients
│       ├── components/chat/mcp-apps/  # Browser Host/adapter/fallback
│       ├── contexts/、engine/、hooks/、lib/、router/
│       └── views/
├── packages/
│   └── mcp-apps-runtime/              # 唯一独立 Node MCP Runtime package
│       ├── package.json
│       ├── tsconfig.json
│       └── src/
│           ├── index.ts               # `import 'server-only'` public entry
│           ├── config-provider.ts
│           ├── contracts.ts
│           ├── http-adapter.ts
│           ├── persistent-connector-manager.ts
│           ├── runtime-policy.ts
│           ├── runtime.ts             # process-scoped composition root
│           └── sdk-connector.ts
├── e2e/
├── public/
└── Dockerfile
```

不存在也不得恢复以下路径或并行 owner：

- `frontend/src/**`；
- `frontend/app/app/**`；
- `frontend/app/package.json` 或 `frontend/app/next.config.*`；
- `frontend/app/_dream/server/mcp-apps/**`；
- `frontend/package-lock.json` 或 package 内第二 lock；
- 根 Web package 之外的第二 Web Shell package。

`vite` 和 `@vitejs/plugin-react` 仍出现在根 package 的 development dependencies，只服务于隔离的测试 adapter/历史兼容测试需要；当前生产 dev/build/start scripts 全部调用 Next，仓库没有 Vite config、Vite 应用入口或 Vite production build owner。

## 4. 运行边界与依赖方向

| 边界 | 当前职责 | 禁止越界 |
|---|---|---|
| Next Web Shell | 页面、layout、catch-all、公开资源、Browser Client 加载和同源入口 | 不读取数据库、MCP credential 或 Provider secret；不成为登录态权威 |
| `app/_dream/**` | Chat、Dream、Deck、Writing、Browser API clients、MCP Apps Host adapter | 不导入 server-only Runtime package；不建立第二套 route tree |
| `app/api/mcp-apps/[serverRef]` | 提取同源 transport 请求并调用 package public API | 不持有 manager、credential、catalog 或业务数据；不实现第二套协议 |
| MCP Apps status/sandbox Routes | 投影 preview 状态、sandbox HTML 与 Host policy | 当前仍从 `app/_dream/**/host-policy` 反向导入并在 Route 内组合策略；这是待抽取到中立 shared/server owner 的代码缺口，不是目标依赖方向 |
| `packages/mcp-apps-runtime/src/**` | Python config client、MCP SDK connector、HTTP adapter、进程级 manager、session/catalog/policy | 不依赖 React、DOM 或 `app/_dream/**`；不向 Browser 返回真实 URL/header/env |
| Python FastAPI | 身份、actor/workspace/Server 校验、managed MCP desired/effective/revision、短时 connection view、业务数据 | 不持有 Browser iframe/bridge；不代理 App 页面交互 |
| Admin/PostgreSQL | Schema、capability、模型、订阅、计费和 Gateway | Dream 不创建 migration、runtime DDL 或 SQLite fallback |

MCP transport 主链允许的 server import 方向是：

```text
frontend/app/api/mcp-apps/[serverRef]/route.ts
  → @ink-dream/mcp-apps-runtime
  → frontend/packages/mcp-apps-runtime/src/**
```

上图精确适用于 `[serverRef]/route.ts` transport 入口。当前 `phase1-status/route.ts` 与 `mcp-apps-sandbox/route.ts` 仍直接导入 Browser 树中的 `host-policy`，前者还在 Route 内组合策略；它们是现存例外。后续应把共享 manifest/Host contract 抽到中立 shared/server package，再恢复单向图；在代码修复前不得把“所有 `app/api/**` 都是薄委派”写成已满足事实。

Browser 的方向是同源 HTTP，而不是 package import：

```text
app/_dream Browser Host
  → /api/mcp-apps/{serverRef}
  → thin Route Handler
  → process-scoped Runtime/Manager
  → real MCP Server
```

`frontend/packages/mcp-apps-runtime/src/index.ts` 显式导入 `server-only`。进程级 Runtime 通过 `globalThis.__inkDreamMcpAppsRuntime` 复用 `McpAppsHttpAdapter` 和 `PersistentConnectorManager`；Route Handler 请求结束不等于上游连接结束。

## 5. 身份、数据与同源适配

Next.js 是 Web/BFF 边界，不是身份或数据 owner：

- `next.config.js` 仅在配置 `INK_BACKEND_INTERNAL_URL` 时把通用 `/api/**`、`/auth/**` 和 OAuth 路径 rewrite 到 Python；
- `[serverRef]/route.ts` 是 Next 自有 transport Route Handler，只调用 server-only package；status/sandbox Route 还存在上节记录的反向 import 缺口；
- Browser Bearer 继续由 Python 校验，Node 还必须携带 server-owned `INK_MCP_APPS_NODE_SERVICE_TOKEN` 才能取得 connection view；
- Python 在返回短时单 Server connection view 前校验 actor、workspace、Server、config revision、credential revision、policy revision 和有效期；
- PostgreSQL 业务读写继续由 Python 完成，Schema 继续由 Admin Drizzle 唯一管理。

这意味着“Next Route Handler 存在”不等于“业务迁入 Next”。Route Handler 只处理 Web 同源和 transport 适配，业务授权结果仍来自 Python。

## 6. 当前依赖与命令

| 依赖 | 锁定事实 | 用途 |
|---|---|---|
| Node package manager | `pnpm@10.28.1` | 唯一 workspace 安装和脚本入口 |
| Next.js | `16.1.6` | App Router、自托管 Web、Route Handler、standalone |
| React | `19.1.0` | Dream Web/Browser Host |
| MCP SDK | `@modelcontextprotocol/sdk@1.30.0` | Browser/Node 标准 MCP transport 与 client |
| MCP Apps | `@modelcontextprotocol/ext-apps@1.7.5` | 稳定 Apps 协议与官方 demo 对齐 |
| Host library | `@mcp-ui/client@7.1.1` | 复用 AppBridge/PostMessageTransport；IM adapter 持有权限和 iframe |
| Runtime package | `@ink-dream/mcp-apps-runtime@workspace:*` | server-only sibling package |

当前命令统一从仓库根使用 `--dir frontend`，或在 `frontend/` 内执行等价 pnpm 命令：

```bash
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend build
INK_NEXT_OUTPUT=standalone pnpm --dir frontend build:docker
pnpm --dir frontend start
pnpm --dir frontend test:mcp-apps-runtime
pnpm --dir frontend typecheck:mcp-apps
```

禁止使用 `npm install`/`npm ci` 解析 Dream Web 依赖，禁止生成 `package-lock.json`，也禁止执行 `next dev app`、`next build app` 或 `next start app`。

## 7. MCP Apps 状态语义

| 层次 | 当前事实 | 结论 |
|---|---|---|
| 代码存在 | Browser Host、projection、sandbox、Route Handler、Node Runtime 和 Python connection-view API 均在 `54f3bbe5` | 实现存在 |
| 技术验证 | 当前 pnpm lock 下的 Phase 0—3 provider-free Node/Backend/Browser/Next build/standalone 回执通过 | technical preview complete |
| 公开应用 | 只以未修改的官方 `@modelcontextprotocol/server-basic-vanillajs@1.7.5` 制品验证兼容；没有面向真实用户发布的外部 App/Server catalog 证据 | 不可声明公开应用可用 |
| 生产启用 | `contracts.ts` 的 `PRODUCTION_APPS_EFFECTIVE` 是不可变 `false`；status projection 同样固定返回 `productionAppsEffective: false` | Production No-Go |

Preview 的 `desired` 与 `effective` 仍必须分开：环境开关、plugin lifecycle、Python runtime policy、sandbox URL、revision、timeout 和 capability 必须全部有效，才可能在技术 preview 中得到 effective enabled。它们都不能把 production effective 改为 true。

## 8. 当前验收证据

以下证据来自同一当前 pnpm 候选，详细输出与失败迭代见[统一回执](../../exec/mcp-apps/current-candidate-validation.md)：

| 范围 | 命令 | 结果 |
|---|---|---|
| lock 安装 | `pnpm --dir frontend install --frozen-lockfile --ignore-scripts` | exit 0；无第二套解析 |
| Runtime | `pnpm --dir frontend test:mcp-apps-runtime` | exit 0；36 passed |
| Runtime types | `pnpm --dir frontend typecheck:mcp-apps` | exit 0 |
| Phase 0 Browser | `pnpm --dir frontend run e2e:mcp-apps-phase0` | exit 0；4 passed |
| Browser/result contracts | Node test runner 执行 `app/_dream/components/chat/mcp-apps/*.test.ts` 等 | exit 0；15 passed |
| Backend Phase 1—3 | 公开 Python 测试入口覆盖 MCP Apps 与 Claude Agent regressions | exit 0；262 passed、8 subtests passed |
| Root shell | test-owned Next server + `e2e/root-next-shell.spec.ts` | exit 0；1 passed |
| Full typecheck/lint | pnpm 调用 TypeScript 与 ESLint | exit 0；lint 0 error |
| Next build | `NODE_ENV=production corepack pnpm --dir frontend build` | exit 0 |
| Standalone | `INK_NEXT_OUTPUT=standalone ... build:docker` 并探测 health/status | exit 0；两个 endpoint HTTP 200，默认 unavailable |

这些是技术验证，不是生产或真实业务验收。

## 9. 当前缺口

下一步围绕仍缺的真实证据和已登记代码缺口，不再围绕旧目录迁移派工：

- 用用户明确授权的真实账号、既有业务实体和正常 Dream/Admin/Gateway/PostgreSQL 路径验收；
- 接入真实外部 MCP Server，验证实际 descriptor/resource、OAuth refresh、权限降级和普通结果 fallback；
- 明确公开应用的制品身份、版本、完整性、回滚和运营 owner；
- 在目标生产拓扑验证 Node lifecycle、优雅退出、连接清理、容量、日志/指标和回滚 image；
- 把 MCP Apps status/sandbox Route 共用的 Host policy/manifest contract 从 `app/_dream/**` 抽到中立 shared/server owner，消除当前 server-to-Browser 源码反向 import；
- 只有新的产品/安全决定和上述证据允许时，才设计 `productionAppsEffective` 的状态转换；当前不得通过配置绕过常量。

## 10. 历史迁移记录（非当前指南）

本节只解释旧文档和旧回执，不可用于构建、部署或 source ownership 判断。当前指南始终以上文第 3—9 节为准。

| 历史阶段 | 当时事实 | 当前处理 |
|---|---|---|
| Vite SPA | `frontend/src/**`、Vite config、Nginx/static build 曾是生产入口 | 已退役；当前 scripts 为 Next，路径不存在 |
| 嵌套 Next 过渡 | `frontend/app/` 曾有第二 package/config，App Router 位于 `frontend/app/app/**` | 已退役；不得恢复 alias 或双写 |
| legacy Node Runtime owner | Runtime 曾混放在 `frontend/app/_dream/server/mcp-apps/**` | 已迁入独立 sibling package |
| npm lock PoC | Phase 0 曾绑定 `frontend/package-lock.json` | 仅历史证据；当前 pnpm lock 已重新验证 |
| Vite rollback plan | 迁移期曾计划切回 Nginx/Vite image | 仅历史方案；当前回滚基线应是上一已验证 Next image，除非另有经过验证的发布决策 |

DEC-005 的架构决定仍有效且已实现：`frontend/` 是唯一 workspace/package/Next 根，`frontend/app/**` 是唯一 App Router，`frontend/packages/mcp-apps-runtime/**` 是唯一 Node MCP Apps Runtime package。

## 11. 维护与回归门

后续修改必须保持：

1. `frontend/pnpm-lock.yaml` 是唯一 Node lock。
2. `frontend/app/_dream/**` 是唯一 Dream 应用源码树。
3. Browser 不导入 `@ink-dream/mcp-apps-runtime`，Runtime 不反向导入 React/DOM/`app/_dream`。
4. `[serverRef]/route.ts` transport Route 保持薄适配；status/sandbox Route 的共享 contract 迁入中立 owner 后才能恢复完整单向依赖。身份、业务数据、managed MCP 权威始终在 Python。
5. provider-free、真实业务、公开应用和生产启用四类证据分别报告，不互相替代。
6. `productionAppsEffective=false` 在未完成单独产品/安全决策前保持不变。
7. 任何历史 Vite、嵌套 Next、npm lock 或旧 Runtime owner 内容必须标为历史并链接本文当前章节。
