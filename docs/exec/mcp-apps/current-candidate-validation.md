<!-- [输入] 当前 pnpm lock、官方 MCP Apps 制品、Phase 0—3 实现和最终 Backend/Node/Browser/build 回执。 -->
<!-- [输出] Phase 0—3 当前候选的统一技术结论、命令证据、视觉观察、回滚与生产边界。 -->
<!-- [定位] 当前候选总回执；不替代真实账号、真实外部 Server 或 production 发布验收。 -->
<!-- [同步] 2026-09-06：完成两轮独立审阅修复后的 canonical pnpm/official-AppServer/production-module Phase 0—3 provider-free 验收。 -->
<!-- [同步] 2026-09-06：修正官方标准 App 兼容合同：服务端 positive list 可分类缺少可选 risk hints 的工具，显式危险 hints 仍 fail closed。 -->
<!-- [同步] 2026-09-06：补验 turn 前 descriptor inventory 刷新、首次实时 App 结果保留与 final-only 历史恢复。 -->
<!-- [同步] 2026-09-06：补验完成 turn 过程折叠与 MCP App 面板在折叠区外的常驻布局。 -->
<!-- [同步] 2026-09-13：独立端口为旧候选形态；当前 preview 使用动态前端入口和强制 opaque 文档隔离，增量回执另列。 -->

# MCP Apps Phase 0—3 当前候选技术验收

## 1. 结论

| 阶段 | 当前技术状态 | 结论边界 |
|---|---|---|
| Phase 0 | `Go` | 当前 pnpm lock、Chrome 和源码指纹下 P0-01—P0-08 通过。 |
| Phase 1 | `complete / technical preview` | 官方 `1.7.5` AppServer 经 Browser→production Route Handler modules→Manager 完成 Host 闭环；E2E 以隔离 Vite HTTP adapter 加载这些真实模块，另有实际 Next root-shell/build 证据。 |
| Phase 2 | `complete / technical preview` | 低风险 `tools/call`、`ui/message`、Host context 和最小 `window.im` 通过；高风险继续拒绝。 |
| Phase 3 | `complete / technical preview` | manifest/lifecycle、隔离、诊断、版本矩阵和资源策略通过。 |
| Production | `No-Go` | `productionAppsEffective=false` 为不可变公开状态；未执行真实账号、真实外部 Server、真实 OAuth/生产运维验收。 |

技术完成不等于生产发布。当前代码提供默认关闭、显式 desired/effective/revision、逐请求重验和可独立回滚的 preview 能力；没有修改数据库 schema，也没有建立独立 Bridge/Gateway。

2026-09-13 增量修复：[本机恢复与动态入口](./local-startup-recovery.md)。原候选的
独立 URL origin 改为实际前端入口下的版本化相对 sandbox URL；两层 iframe 与响应
CSP 强制文档 opaque origin。以下指纹和旧回执保留追溯，不能当作本轮源码指纹。

## 2. 当前指纹与供应链

- Branch：`codex/mcp-apps-design`（本回执只声明该分支候选的技术状态；合并与发布状态以对应 PR 和发布流程为准）。
- 唯一 Node lock：`frontend/pnpm-lock.yaml`，SHA-256 `68d3c30f35eef1eec745d8c814475615eb7eceaf8866f0f721c4743394c1afd0`。
- Node `v24.13.0`；pnpm `10.28.1`；Chrome `152.0.7977.77`。
- `@modelcontextprotocol/sdk@1.30.0`、`@modelcontextprotocol/ext-apps@1.7.5`、`@mcp-ui/client@7.1.1`、`@playwright/test@1.62.1`。
- 当前官方制品：`@modelcontextprotocol/server-basic-vanillajs@1.7.5`，npm SHA-1 `855c0acd7df70d840b9fdb1bc0868a3f68288e7f`，本地制品 SHA-256 `4256fb45020e34a315733634779513572317885083a68eb6c1a3819e576f51ca`。
- 上一兼容制品：`@modelcontextprotocol/server-basic-vanillajs@1.7.4`；Inspector `2.5.0`。
- `pnpm --dir frontend install --frozen-lockfile --ignore-scripts`：exit `0`，lock 已是最新且没有第二套安装解析。

## 3. 最终验证回执

| 范围 | 命令 | Exit / 关键结果 |
|---|---|---|
| Phase 0 Browser | `pnpm --dir frontend run e2e:mcp-apps-phase0` | `0`；`4 passed (10.5s)`；本机 Chrome；origin/CSP/permission/source/teardown/no-replay 全部通过。 |
| P0 locality | `python backend/tests/fixtures/mcp_apps_phase0/phase0_standard_apps_fixture.py --probe-all` | `0`；stdio、localhost HTTP、Node-reachable SSE 与 fresh sessions 通过，用户设备 stdio 明确排除。 |
| P0 Backend | `PYTHONPATH=backend uv run --native-tls --project backend --frozen --with pytest python -m pytest backend/tests/mcp_apps_phase0 -q` | `0`；`3 passed`。 |
| Official compatibility + lifecycle | `pnpm exec playwright test e2e/mcp-apps/phase-1/official-phase1-3.spec.ts --reporter=line --workers=1`（从 `frontend/`，显式 current/previous artifact roots） | `0`；`3 passed (14.0s)`；官方 `1.7.4/1.7.5` protocol smoke 与 `1.7.5` production-module Host 生命周期通过。 |
| Actor-effective `window.im` | `pnpm exec playwright test e2e/mcp-apps/phase-1/window-im-runtime-policy.spec.ts --reporter=line --workers=1`（从 `frontend/`） | `0`；`1 passed (1.6s)`；握手前方法不存在，tool-only runtime-policy downgrade 会移除整个 `window.im`，另一 actor fail closed。 |
| Inspector | Inspector `2.5.0` CLI 对 `1.7.4/1.7.5` 分别执行 `tools/list --app-info` 与 `resources/read` | `0`；descriptor、`ui://get-time/mcp-app.html`、MIME 和正文一致。 |
| Node Runtime | Node `24.13.0` 执行 package test 命令中的 `--experimental-strip-types --experimental-transform-types --test src/*.test.ts` | `0`；`38 passed`。 |
| Node type contracts | `pnpm --dir frontend typecheck:mcp-apps` | `0`；Runtime 与 integration typecheck 均无诊断。 |
| Browser/result/Chat-ingress/session-cleanup contracts | `node --experimental-strip-types --test frontend/app/_dream/components/chat/mcp-apps/*.test.ts frontend/app/_dream/components/chat/__tests__/chatUserMessageIngress.test.ts`（从 `frontend/` 的 Node 26 shell；这些文件不需要 transform-types） | `0`；`16 passed`；包含真实 SDK 1.30 initialize 失败后 aborted-signal→fresh-signal DELETE，以及延迟清理跨 Thread/revision lifecycle 时抑制旧错误的回归。 |
| Backend Phase 1—3 + regressions | `PYTHONPATH=backend uv run --native-tls --project backend --frozen --with pytest --with pytest-asyncio python -m pytest backend/tests/mcp_apps_phase1 backend/tests/mcp_apps_phase2 backend/tests/mcp_apps_phase3 backend/tests/test_claude_mcp_runtime_snapshot.py backend/tests/test_claude_mcp_service.py backend/tests/test_claude_mcp_router.py backend/tests/test_claude_agent_sse.py backend/tests/test_claude_agent_service.py backend/tests/test_claude_agent_thread_factory.py backend/tests/test_server_claude_agent.py -q` | `0`；`274 passed`、`8 subtests passed`；21 个既有 FastAPI lifecycle deprecation warnings。 |
| Chat/SSE/voice contracts | `pnpm --dir frontend exec playwright test app/_dream/lib/__tests__/apiBase.test.ts app/_dream/api/__tests__/voiceApi.writing-sse.test.ts app/_dream/components/chat/__tests__/ToolConfirmationRecovery.test.ts --reporter=line --workers=1` | `0`；`39 passed`。 |
| Chat 实时/历史过程合同 | `corepack pnpm --dir frontend exec playwright test app/_dream/components/chat/__tests__/ChatHistoryWindow.test.ts app/_dream/components/chat/__tests__/AssistantTurnHistory.test.ts app/_dream/components/chat/__tests__/ToolConfirmationRecovery.test.ts app/_dream/components/chat/__tests__/AssistantTurnGroup.browser.test.ts app/_dream/components/chat/__tests__/ChatHistoryProcessLazyLoad.browser.test.ts --reporter=line --workers=1` | `0`；`47 passed (11.4s)`；首次实时过程在精确匹配 final-only recovery 后保留；完成 turn 默认折叠过程，已验证 App 面板作为折叠区外单实例常驻。 |
| 折叠布局定向静态检查 | `corepack pnpm --dir frontend exec tsc --noEmit --pretty false` + `corepack pnpm --dir frontend exec eslint app/_dream/components/chat/AssistantTurnGroup.tsx app/_dream/components/chat/ChatMessageList.tsx app/_dream/components/chat/ChatPanel.tsx app/_dream/components/chat/ToolMessagePart.tsx app/_dream/components/chat/__tests__/AssistantTurnGroup.browser.test.ts app/_dream/components/chat/__tests__/ChatHistoryProcessLazyLoad.browser.test.ts` | 两条均 `0`；无诊断。 |
| Root shell | test-owned `pnpm exec next dev --hostname 127.0.0.1 --port 5173` + `pnpm exec playwright test e2e/root-next-shell.spec.ts --reporter=line --workers=1` | `0`；`1 passed (8.0s)`；login、canonical URL、refresh、direct load 无 diagnostics。 |
| Full frontend typecheck | `corepack pnpm --dir frontend exec tsc --noEmit --incremental false` | `0`。 |
| Lint | `corepack pnpm --dir frontend lint` | `0`；0 errors，17 个既有 `react-hooks/exhaustive-deps` warnings。 |
| Next build | `NODE_ENV=production corepack pnpm --dir frontend build` | `0`；TypeScript、pages、trace 完成。 |
| Standalone | `INK_NEXT_OUTPUT=standalone NODE_ENV=production corepack pnpm --dir frontend build:docker` | `0`；隔离端口 `43177` 的 `/api/health` 与 `/api/mcp-apps/phase1-status` 均 HTTP 200；默认 state=`unavailable`。 |

## 4. Browser 实际观察

当前 `1.7.5` 运行截图为 `frontend/output/playwright/mcp-apps/official-1.7.5-production-host.png`（run-owned、未纳入版本库，`1100×1026`、71,749 bytes，SHA-256 `86b1ff626509e5d8c5171c1f3a1bafa7b510a79603c98d3dac25b8a2e24be227`）。实际图像已人工查看：普通工具结果卡仍完整显示 Input/Output；其下方独立 Interactive tool result 面板显示官方 Server Time、Get Server Time、Send Message 和 Send Log 控件。

当前本机 Dream 真实页面另对已有 get-time turn 完成布局复核：展开时 `[data-turn-process] [data-testid="mcp-app-panel"]` 数量为 `0`，`[data-turn-outside-process] [data-testid="mcp-app-panel"]` 为 `1`；折叠后 process region 为 `0`，App panel 仍为 `1`，且仍在 outside-process 容器内。

同一 Browser run 证明：Browser 只访问 Host 与 sandbox origin；没有访问 relay/官方上游地址；Browser 配置、DOM、请求和 diagnostics 不含上游 secret。预期证据单列为 opaque-origin `localStorage` 拒绝、恶意 Phase 1 `tools/call` 的精确 method-not-found 响应，以及旧 session 在 lifecycle 切换时的 404/409 和禁用期标准 DELETE 的 fail-closed 503；除此之外 console/page/request diagnostics 为空。

## 5. 安全、状态与回滚

- Python 在解密前校验 Node 服务身份、actor、workspace、Server、config/credential/policy revision、enabled 和有限正数有效期；OAuth refresh 后重读权威 record 并返回同步推进的 credential revision，只投影单 Server 短时连接视图。
- Node 每次请求重验当前视图、manifest、policy 和 allowlist；connection profile 只以不可逆 canonical digest 参与同 revision 漂移判断。adapter session 与短时 view 同步到期，即使 Browser 崩溃或没有后续请求也会移除 secret-bearing view；revision/策略漂移、禁用、不兼容、到期与 provider 失败会使旧 session/connector 失效。catalog 分页有配置上限，携带凭据的上游请求拒绝 redirect。
- Browser identity 来自 server-owned `mcpAppResult`，包括由服务端校验 actor/Thread 所有权后的 workspace scope，不会从普通 output metadata 推断；`toolCallId` 不参与授权，error result 只保留普通输出。
- Phase 1 的页面 tool call 保持拒绝；AppBridge 不持有可自动转发的 SDK Client。Phase 2 只手动开放服务端 App-callable 正向列表明确分类的低风险工具；未列入、显式高风险或需确认的工具在解密/上游调用前拒绝。标准 MCP descriptor 的可选 risk hints 缺失不覆盖服务端显式分类。
- sandbox 使用隔离文档 origin、两层 `sandbox="allow-scripts"`、零设备权限和闭网 CSP。当前 asset URL 跟随前端入口，响应 CSP 另有 `sandbox allow-scripts`；外层 CSP 保留 inline script/style，因为它会继承到官方 App 的 `srcdoc`；网络、object、base、font、media 仍全部关闭，frame 仅允许内层。
- `ui/message`、composer、queued prompt 与 retry 共用同一 Chat-owned ingress，Editor 持久化和 turn generation 先于 transport dispatch；`window.im` 在认证 Host 的 `ui/initialize` capability 回执前保持不存在，并只声明 actor-effective 成员，自定义 response namespace 不泄漏到官方 App transport。
- 回滚顺序：关闭对应 Phase 2 capability → 禁用/回滚插件 revision → 关闭 preview effective；已有普通结果继续显示，Client/View/session 和无引用 connector 关闭。Next 可回滚至上一已验证 image。

## 6. 失败迭代与最终判定

- 第一轮独立审阅发现 AppBridge 自动转发、跨 scope invalidation、Browser policy/expiry 漂移、workspace 未透传、App 消息绕开 Chat coordinator、redirect/pagination、error-result 投影及 E2E 表述不精确等缺口。候选据此改为 manual handler、exact-scope teardown、双 revision + ping/expiry、按服务端 actor/thread 归属和路径检查的 workspace、统一 Chat ingress、no-redirect/有界分页、error ordinary-only。
- 第二轮独立审阅又发现 Browser close 未发标准 DELETE、OAuth refresh 后仍可能返回旧 credential revision、同 revision profile 漂移未比较，以及 `window.im.callTool` 可能与 actor-effective policy 失配。当前候选已增加 in-flight-connect 后的标准 DELETE、权威 revision 重读、secret-free canonical profile digest 和认证 Host capability handshake；真实 Chrome 明确验证 close/reopen/Thread switch/plugin disable 的 session/connector/lease 归零或归一。
- 最终失败路径审阅复现 SDK 1.30 initialize 校验失败会先 abort transport，并发现 tool-only runtime downgrade 可能产生矛盾的 `window.im` status。Browser cleanup 现在先尝试 SDK termination，失败时以同 scope header 和新 AbortSignal 执行有界 DELETE，finally 关闭本地 Client；清理完成后再次核对 effect lifecycle，旧 Thread/revision 不得向新连接写入错误。Node adapter 另以 view expiry 回收无后续请求的 session。status 的 `windowIm` 改由 effective method 可用性派生；真实 SDK 单测、延迟 lifecycle 单测、Runtime expiry 单测与独立 actual-Chrome tool-only 回归均通过。
- 同一独立审阅者在上述失败路径修复后完成最终 re-audit，结论为无 P1/P2 阻断；最终 actual-Chrome official run 也保持 `unexpectedDiagnostics=[]`。
- 两次 Python harness 命令先因不存在的根 `.venv`、随后因临时 pytest 缺少 `pytest-asyncio` 而失败；使用上表显式 `uv --with pytest --with pytest-asyncio` 后同一目标全部通过，不是产品失败。
- sandbox nonce-only CSP 曾阻止官方 App 的 inline bundle：`srcdoc` 继承外层 CSP，单独在内层 meta 放宽无效。最终合同显式允许 inline assets、继续关闭所有网络和设备能力，官方 lifecycle 与零意外 diagnostics 通过。
- root shell 首次重验在 Browser context setup 超时，且第一次 server 重试把 pnpm 参数转发给了 Next 项目目录；改用上表直接 `next dev` 的 test-owned server 后通过，并只清理本轮进程。

因此当前结论是：**Phase 0—3 provider-free 技术验收完成；production 发布保持 No-Go，直到真实账号、真实外部 MCP Server、真实 OAuth/权限和运维回滚验收另行通过。**
