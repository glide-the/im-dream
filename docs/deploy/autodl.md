# AutoDL SSH 部署
<!--
[Input] AutoDL direct-host scripts, Admin env, MCP Apps env, and SeetaCloud mappings.
[Output] Current Next.js/FastAPI/MCP Apps release, verification, and rollback contract.
[Pos] AutoDL Dream production runbook.
[Sync] 2026-09-06: migrate the direct-host release from Vite/npm/dist to standalone Next.js and frozen pnpm.
[Sync] 2026-09-17: derive the opaque MCP Apps sandbox route from the injected Dream mapping; no third public origin is required.
[Sync] 2026-09-11: add safe discovery of the AutoDL-injected public mappings (AutoDLService6006URL/AutoDLService6008URL) and how they fill platform.env origins.
-->

## 拓扑与边界

AutoDL 先发布 Admin，再发布 Dream。Dream 不安装 Docker/nginx：

```mermaid
flowchart LR
  Public["Dream HTTPS"] --> Next["Next.js 127.0.0.1:6006"]
  Sandbox["MCP Apps sandbox HTTPS"] --> Next
  Next -->|API/Auth rewrite| API["FastAPI 127.0.0.1:8765"]
  API --> Admin["Admin/Gateway 127.0.0.1:6008"]
  Admin --> PG["Admin-owned PostgreSQL 127.0.0.1:54329"]
```

唯一 Web 源码位于 `frontend/app/_dream/**`；构建使用
`frontend/pnpm-lock.yaml` 和 standalone Next.js。MCP Apps 的 Browser Host 随
Dream 页面构建，server-only Node Runtime 位于
`frontend/packages/mcp-apps-runtime/**` 并由 Next Route Handler 执行。

MCP Apps sandbox URL 使用 Dream 同一 HTTPS origin 下的 `/mcp-apps-sandbox`；外层
iframe 不授予 `allow-same-origin`，因此浏览器中的有效 document/postMessage origin
仍为 opaque `null`，无需第三个公网映射。Dream 只消费 Admin 已发布的 PostgreSQL
capability，不执行 migration、DDL、restore 或 SQLite fallback。

## 配置

公网 origin 取自 AutoDL 注入的只读服务变量。SSH 登录实例后只输出这两个变量——
不要打印整个 `/etc/profile.d/autodl.env.sh`，其中还包含 AutoDL 面板令牌：

```bash
source /etc/profile.d/autodl.env.sh
printf 'Dream: %s\nAdmin: %s\n' "${AutoDLService6006URL}" "${AutoDLService6008URL}"
```

`AutoDLService6006URL`（前端 6006）填入 `AUTODL_DREAM_PUBLIC_ORIGIN`，
`AutoDLService6008URL`（Admin 6008）填入 `AUTODL_ADMIN_PUBLIC_ORIGIN`。AutoDL
代理不保证转发 `Forwarded` / `X-Forwarded-*`，公网 origin 必须显式配置；更换
实例后地址会重新生成，需重新发现并重新投影 runtime env。

从 `deploy/autodl-ssh/platform.env.example` 创建 gitignored
`platform.env`，设置 SSH、Dream/Admin HTTPS origin 和本机 MCP Apps env 文件。
sandbox route 自动从 Dream origin 派生。然后生成 mode-0600 runtime env：

```bash
./deploy/autodl-ssh/prepare-env.sh
```

投影会移除全部数据库配置键，保留 backend-owned MCP Apps service token，读取 frontend 的 manifest、
feature 和资源/network policy，并覆盖为生产 sandbox/parent origins。AutoDL
固定 `INK_AGENT_SANDBOX_ENABLED=false`：外层容器无法提供 namespace sandbox，
approved Bash 将以 Dream root 身份运行。

## 发布与验证

```bash
./deploy/autodl-ssh/test-topology.sh
./deploy/autodl-ssh/deploy.sh check
./deploy/autodl-ssh/deploy.sh deploy
```

脚本安装固定 Node/pnpm、Claude Runtime 与 Notion CLI，执行 frozen pnpm
install 和 standalone Next build；release gate 验证 MCP Apps Node routes、
FastAPI/Next/同源 API、`robots.txt`、`sitemap.xml`、`llms.txt`、内置
Skills、默认 Deck Plugin、Admin 依赖和公网 origin。全部通过后才推进
`qualified`。

Runtime 由公开 npm `@glide-the/ink-claude-code-dream@0.1.10` 安装。发布门禁验证其相邻 `release-manifest.json`、SDK `0.2.145` 绑定、production eligibility、CLI compatibility `2.1.241` 与 `plugin` 命令；旧的未发布 AutoDL local-core `0.1.9` 不再作为构建输入。

运维命令为 `status`、`logs`、`verify`、`start`、`stop` 和 `rollback`。常规 `deploy` 不直接覆盖 `current`：它先生成不可变 `candidate`，在 `16006`/`18765` 运行完整 Next/FastAPI 隔离冒烟，通过后才停止旧 Dream 并原子切换。若启动或公开验证失败，本轮仍可恢复旧应用；验证成功后立即删除旧 release、`previous` 与 `candidate`，不保留长期回滚版本。共享 workspace、Artifact、Plugin Runtime 与 Admin/PostgreSQL 数据不参与 release 清理。
启动/停止仅处理具名 Dream screen/PID；未知端口占用会 fail closed。回滚只
切换 Dream release，不回滚 Admin migration、PostgreSQL 数据或 workspace。
