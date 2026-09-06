<!-- [输入] 当前 root Next source、pnpm lock、strict build、standalone health 与 root-shell Browser test。 -->
<!-- [输出] N1-01—N1-05 当前 build/start/health/compatibility/rollback 证据。 -->
<!-- [定位] 当前 Phase 1 N1 回执；不执行远程部署或修改用户服务。 -->
<!-- [同步] 2026-09-06：完成 canonical root pnpm/Next/standalone 最终重验。 -->

# N1 Build、Health 与 Rollback

- `frontend/` 是唯一 Web workspace/package；App Router 只有根 `app/**`，现有 SPA 通过 client-only compatibility shell 加载。
- Browser-only 模块不进入 Server Component；Node MCP Runtime 只被 Route Handler 导入。
- 现有 REST/SSE/voice URL 继续由 runtime config 与 Next rewrite owner 解析；root shell 对 login、canonical URL、refresh、direct load 无 diagnostics。
- MCP Runtime 是进程级 singleton；公开 status 永远返回 `productionAppsEffective:false`，缺少 preview/manifest/config 时 state=`unavailable`。

| Command / observation | Exit | Result |
|---|---:|---|
| `corepack pnpm --dir frontend exec tsc --noEmit --incremental false` | 0 | 全量 TypeScript 无诊断。 |
| `corepack pnpm --dir frontend lint` | 0 | 0 errors；17 个既有 hooks warnings。 |
| `NODE_ENV=production corepack pnpm --dir frontend build` | 0 | Next 16.1.6 pages、types 与 traces 完成。 |
| `INK_NEXT_OUTPUT=standalone NODE_ENV=production corepack pnpm --dir frontend build:docker` | 0 | standalone 产物完整。 |
| 隔离 standalone port `43177` | 0 | `/api/health` 与 `/api/mcp-apps/phase1-status` HTTP 200；默认 Apps unavailable/false。 |
| test-owned Next dev + `pnpm exec playwright test e2e/root-next-shell.spec.ts --reporter=line --workers=1` | 0 | 1 passed (8.0s)。 |

Rollback：先关闭 Apps preview/plugin capability；Next image 独立回退到上一已验证 image。测试只停止并删除自己创建的 port/process/`.next`/probe output，不触碰用户服务。
