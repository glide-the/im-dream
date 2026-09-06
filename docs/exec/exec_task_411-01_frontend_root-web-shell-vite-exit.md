<!-- [Input] SUO-419 execute wake, task_411-01 filled requirement, Stage 1, the SUO-420 through SUO-424 unblock receipts, and the rechecked dirty-tree baseline. -->
<!-- [Output] Completed Root Web Shell/Vite-exit implementation report, including the verified immutable rollback image and restored Chat regression gates. -->
<!-- [Pos] Canonical ExecTaskAgent report for task_411-01; it grants no Runtime, lock, P0, standalone-release, or production approval. -->
<!-- [Sync] 2026-09-05: completed all N1 gates after Docker recovery, isolated Vite rollback smoke, selector URL/network separation, and Chat SSE/resume fixture repair. -->
<!-- [Sync] 2026-09-06: rebased current Dream source references from the retired frontend/src tree to frontend/app/_dream. -->
<!-- [Sync] 2026-09-06: mark missing-lock and later-stage No-Go statements as dated execution facts superseded by current-candidate evidence. -->

# Exec Report: task_411-01 - Root Web Shell and Vite Exit

> **适用边界。** 本报告如实保留 411-01 执行时 pnpm lock 尚未落地、后续阶段尚未验证以及 Paperclip/checkout 的状态；这些是历史窗口，不是当前候选状态。411-03 和后续 Phase 0—3 已在唯一 pnpm lock 上完成 provider-free 技术验收，见 [当前候选统一回执](mcp-apps/current-candidate-validation.md)。生产仍为 `No-Go`，`productionAppsEffective=false`。

## 1. 任务标题与唯一 Execute Issue

- Task ID: `task_411-01`
- Execute Issue: `SUO-419` — `[execute][task_411-01] 根 workspace/Web Shell/Vite 退出`
- Final disposition: `completed`; work mode `standard`; priority `high`
- Assignee: `ExecTaskAgent` (`2a7a15fe-2ebb-4dc5-91a8-48ae2bcc5471`); user assignee: none
- Checkout: the Paperclip harness pre-claimed this Issue for the current run; no second checkout was attempted
- Parent/readiness: `SUO-416`; canonical Issue: `SUO-411`; Task source: `SUO-412`; Stage source: `SUO-414`
- Resolved authorization/unblock Issues: `SUO-420`, `SUO-421`, `SUO-423`, and `SUO-424`; all are `done` and no first-class blocker remains.
- Repository baseline: branch `codex/mcp-apps-design`, HEAD `cfd75b38fa699b92152fe2a23ba99ceb8fba0ae2`
- Execute date: 2026-09-05 (Asia/Shanghai)

## 2. Task / Requirement / Stage 绑定

| Binding | Current single source |
|---|---|
| General template | `docs/task/TASK-REQUIREMENT-FORMAT.md` |
| Task | `docs/task/task_411-01_frontend_root-web-shell-vite-exit.md` |
| Independent requirement | `docs/task/TASK-REQUIREMENT-task_411-01_frontend_root-web-shell-vite-exit.md` |
| Stage | `docs/stage/stage_mcp-apps-system-architecture.md`, Stage 1 |
| Canonical module | `docs/issue/ISSUES_mcp_apps_system_architecture.md`, `MCPAPPS-411-01` |
| Direct design | `docs/design/claude-agent/dream-frontend-node-framework-migration-assessment.md` §3.2, §4–§6, §9–§11, §13–§15 and DEC-005; `docs/design/claude-agent/mcp-apps-system-architecture-execution-checklist.md` §5.1, §10–§12 |

The execute input binds exactly one Issue, one Task, one independent requirement, and Stage 1. `MCPAPPS-411-02`, `MCPAPPS-411-03`, Phase 2/3, Runtime/P0, final standalone release, and production Apps remain excluded.

## 3. 任务目标与责任边界

### 3.1 TASK-REQUIREMENT-FORMAT.md filled input

- Task content: non-empty. Make `frontend/` the sole Node workspace/Web package/Next root; make root `frontend/app/**` the sole App Router/client compatibility shell; retire legacy Vite from default source/build/deploy ownership after regression.
- Objective: preserve URL/refresh, JWT auth, OAuth callback, Python API, SSE cancel/resume, voice WebSocket, startup runtime config, dynamic public resources, and ordinary Chat behavior.
- Safety invariants: keep `production_apps_effective=false`; do not change backend/schema/Gateway/Agent/Thread/EventBus/SSE/voice semantics; Browser credentials and external Server/Cloud remain excluded.
- Lock ownership: `frontend/pnpm-lock.yaml` is missing and read-only; all create/relock/digest/acceptance work belongs to 411-03. `frontend/package-lock.json` remains untouched for 411-03 retirement.
- Maintenance-doc amendment: resolved `SUO-420` adds only `README.md`, `README.zh.md`, and `frontend/.folder.md` for minimal effective runtime/architecture documentation.
- Collision amendment: resolved `SUO-421` adds exactly the current 32-file `frontend/app/_dream/pages/**` non-router UI tree as a move/delete source, `frontend/app/_dream/views/**` as the relative-tree-preserving destination, the current inbound import/path references, `frontend/app/_dream/.folder.md`, the relocated test folder contract, and path-ownership file headers. The move is complete: source/destination counts are `32/32`, all files are byte-identical to the pre-move source except the intentionally updated relocated `.folder.md`, and old-path imports are zero. A root `frontend/pages/**` sentinel, alias, symlink, dual write, temporary rename, unrelated refactor, and business-semantic change remain forbidden.
- Pre-move source inventory: 32 files; path-list SHA-256 `21416c7a19003dafd42791380e6eec02e363b268c36e039d19820a0427a1ed98`; content-manifest SHA-256 `ef5077d776a46bb9ba5285c316e8c7b51b9b64ef61d05300856c06b2190bd2c6`.
- Pre-move inbound-reference scan: 14 current consumer files / 23 matching occurrences. The authorization comment's 13/20 parenthetical is treated as an informational baseline; all 14 files are pre-existing current inbound consumers and none was dirty except the already-authorized `frontend/app/_dream/App.tsx` WIP.
- Evidence location: this report and the current Issue thread. No old Task/Stage/Exec/evidence is used as a pass result.
- Resume delta: the current heartbeat re-read the template/Task/requirement/Stage, confirmed the harness-held checkout and sole assignee, consumed the completed `SUO-423`/`SUO-424` receipts, and generated fresh rollback and Chat evidence before changing disposition.
- Rollback artifact: `ink-dream/frontend-vite-rollback:task-411-01-d002d4a220a7`, content-addressed locally as `ink-dream/frontend-vite-rollback@sha256:289bd32e5fae92b47e8f4cd17e1940e5d164748cce0cf7a471b56ff86f45de1f`; source bundle manifest SHA-256 `d002d4a220a714906e7ddb16520e865408e08c1ac14905a25177da2bb33ee817`.

### 3.2 Dirty-tree, checkout, and single-assignee evidence

- Baseline command: `git status --porcelain=v1 --untracked-files=all`
- Prior artifact count/SHA-256: `116` paths / `65e18753c09546057ee6761fe17d374d6ed188a78515c7f46d8affd30609b44d`
- Resume comparison: removed the prior report line from the current status, then compared byte-for-byte with the uploaded baseline.
- Resume result: `116` paths / the same SHA-256 / `diff` exit `0`.
- Post-WIP resume inventory before the final verification run: 125 status entries / raw status SHA-256 `5eb0c46112ed053c56abcc099e00a716002c0a6c4ae2b976632efc52793dd280`. Compared with the 116-path Stage ledger, the only source additions/removals are the reported root owner moves, exact Vite/nested deletions, four compatibility-entry changes, the authorized `src/pages/**` move and inbound references, `app/_dream/lib/apiBase.ts`, maintenance docs, and this report. Root `.next/**` and focused Playwright `test-results/**` are generated verification artifacts, not source owners or pass evidence.
- Final inventory before this report update: full status has `1125` entries / SHA-256 `8c4d98e9e24afc62cb8ae7b54bd3610819dd494718778624fddee64e27cc85f8`; excluding untracked root `.next/**` and Playwright `test-results/**` leaves `219` source/evidence entries / SHA-256 `403915bfbc4b25aed953bd5356a6f2c7acabb8c30a9e91b6e66bac62bad0ffdc`. The delta from the prior blocked candidate is explained by the completed child-owned Chat fixture/folder evidence and the rollback-selector/docs completion; no lock or forbidden source owner disappeared.
- Existing in-scope WIP was merged minimally; all other dirty paths were preserved. No reset, restore, broad format, lock write, backend write, or concurrent-owner overwrite occurred.

## 4. 实现步骤与模型生成的执行任务

The filled prompt produced this bounded sequence:

1. Reconfirm checkout, assignee, both authorization amendments, complete dirty-tree, and baseline hashes.
2. Move the current 32-file non-router UI tree from `frontend/app/_dream/pages/**` to `frontend/app/_dream/views/**` with byte-preserving relative paths; then update only its current inbound references, path-ownership headers, and folder contracts.
3. Prove source/destination inventory parity, zero old-path references, no root `frontend/pages/**`, and no alias/symlink/dual-write owner.
4. Continue the previously bounded root workspace/App Router/client shell/Vite/Docker changes without altering business behavior.
5. Run focused moved-module/import tests, root build/dev/start, lint, route/owner/SSR scans, browser regression, and rollback smoke.
6. Package the retained pre-exit bundle into one content-addressed Vite image, exercise it through the local selector with separate internal/browser URLs and an isolated Docker network, then update maintenance docs and complete the 411-02/03 handoff.

The fresh filled input passes the model-call gate for the exact move and current inbound references. It does not authorize unrelated cleanup or treating an unavailable Docker daemon as rollback success.

### 4.1 Browser QA business concept and impact brief

| Concept/fact | Source/write owner | Visible consumer | Expected impact in this technical mocked-browser run |
|---|---|---|---|
| Project identity/title | Canonical Project files; Agent + successful Hook | Story/Execution headings | Unchanged; no Project data or model turn is exercised. |
| Episode identity/title/content | Canonical Episode artifacts; Agent + successful Hook | Episode API/workbench | Unchanged; no Episode mutation or projection is exercised. |
| Run-private publication | Host-owned successful after-turn Hook | Server readers/materializer | Out of scope; no backend, database, Hook, or real business data is used. |
| Shared conversation | ClaudeAgentService Thread/session | Chat and Dream composers/history | Mocked read-only UI bootstrap only; verifies URL/refresh/client shell and does not create or resume a real turn. |

This is provider-free technical regression, not real-business acceptance. The browser must report zero Ink-Dream console/page/request failures after routes are mocked; screenshots are supporting evidence only.

## 5. 涉及文件路径（允许、禁止、删除集合）

### 5.1 Actual source/config/deploy changes

| File | Action | Current WIP change |
|---|---|---|
| `frontend/package.json` | modify | Root `next dev`, `next build --webpack`, `next start`; Docker build selects standalone; removed Vite source scripts and positional `app`. |
| `frontend/pnpm-workspace.yaml` | create | Declares only `.` and `packages/*`. |
| `frontend/next.config.js` | create | Sole root Next config; conditional standalone, runtime-config no-cache headers, optional server-owned Python fallbacks. |
| `frontend/tsconfig.json` | modify | Sole root Next/TypeScript config and root `@/*` mapping; removes Vite client types. |
| `frontend/next-env.d.ts` | create | Sole root Next type entry. |
| `frontend/app/layout.tsx` | move/modify | Root Server Component layout; preserved metadata/structured data and loads runtime config before hydration. |
| `frontend/app/client-shell.tsx` | move/modify | Root Client Component with `dynamic(..., { ssr:false })`; browser-only App stays out of SSR. |
| `frontend/app/[[...path]]/page.tsx` | move/modify | Root compatibility catch-all. |
| `frontend/app/api/health/route.ts` | move/modify | Root production-off health receipt. |
| `frontend/app/api/mcp-apps/[serverRef]/route.ts` | move/modify | Root thin MCP Apps Route Handler; legacy Runtime import remains explicit 411-02 handoff, not a pass claim. |
| `frontend/app/api/mcp-apps/phase1-status/route.ts` | move/modify | Root preview receipt with `productionAppsEffective: false`. |
| `frontend/app/mcp-apps-sandbox/route.ts` | move/modify | Root zero-permission sandbox Route Handler. |
| `frontend/app/_public-resource-proxy.ts`, `frontend/app/{robots.txt,sitemap.xml,llms.txt}/route.ts` | create | Keep Python-owned crawler resources out of the catch-all and fail closed with plain text when the backend origin is unavailable. |
| `frontend/app/_dream/pages/story-workspace/**` → `frontend/app/_dream/views/story-workspace/**` | move | Move the 32-file non-router UI tree byte-for-byte, except the required relocated folder-contract path update. |
| Current inbound `frontend/app/_dream/**` references | modify | Replace only `pages/story-workspace` imports with `views/story-workspace`; no business logic change. |
| `frontend/app/_dream/lib/apiBase.ts` | modify | Startup runtime config remains authoritative; Vite-only `import.meta.env` fallbacks become optional `NEXT_PUBLIC_*` fallbacks. |
| `frontend/e2e/root-next-shell.spec.ts` | create | Provider-free system-Chrome login, URL, direct-load, refresh, and zero-diagnostic regression. |
| `frontend/Dockerfile` | modify | Default image now builds root standalone Next and serves Node on the existing port; retained npm lock is a read-only transition input until 411-03. |
| `frontend/docker-entrypoint.sh` | modify | Renders `/app/public/runtime-config.js`, then starts `node server.js`; no default Nginx/Vite process. |
| `frontend/nginx.conf.template` | modify | Marked historical immutable Vite-image input; default Docker/local source execution no longer references it. |
| `deploy/local/deploy.sh` | modify | Next/pnpm default; Vite rollback accepts only an explicitly named immutable image, separates container-internal backend and browser runtime URLs, and optionally joins one explicit pre-existing isolated Docker network. |
| `README.md`, `README.zh.md`, `frontend/.folder.md`, `frontend/app/_dream/.folder.md`, `frontend/e2e/.folder.md` | modify | Authorized maintenance parity for the root Next workspace, `app/_dream/views/**`, commands, tests, and rollback boundary. |
| `docs/exec/exec_task_411-01_frontend_root-web-shell-vite-exit.md` | modify | This fresh execution/blocker report. |

### 5.2 Exact delete-set actions

All five Vite owners are deleted in the WIP:

1. `frontend/vite.config.ts`
2. `frontend/index.html`
3. `frontend/app/_dream/main.tsx`
4. `frontend/tsconfig.app.json`
5. `frontend/tsconfig.node.json`

All twelve nested owners were removed from their old paths; seven route/shell files were moved to the root locations listed above:

1. `frontend/app/.folder.md`
2. `frontend/app/.gitignore`
3. `frontend/app/next-env.d.ts`
4. `frontend/app/next.config.mjs`
5. `frontend/app/tsconfig.json`
6. `frontend/app/app/layout.tsx`
7. `frontend/app/app/client-shell.tsx`
8. `frontend/app/app/[[...path]]/page.tsx`
9. `frontend/app/app/api/health/route.ts`
10. `frontend/app/app/api/mcp-apps/[serverRef]/route.ts`
11. `frontend/app/app/api/mcp-apps/phase1-status/route.ts`
12. `frontend/app/app/mcp-apps-sandbox/route.ts`

### 5.3 Forbidden/read-only paths preserved

- No `frontend/pnpm-lock.yaml` was created or changed; no install/relock/digest command ran.
- `frontend/package-lock.json`, `frontend/packages/mcp-apps-runtime/**`, and `frontend/app/_dream/server/mcp-apps/**` were not modified by this run.
- No backend, schema, migration, Admin, Gateway, workflow, forbidden deploy, design, issue, task, or stage path was touched.
- No alias, symlink, second manifest, nested `.next`, Browser credential, external Server/Cloud, or production flag was added.
- `README.md`, `README.zh.md`, `frontend/.folder.md`, `frontend/app/_dream/.folder.md`, `frontend/e2e/.folder.md`, and the relocated test folder contract contain the authorized maintenance parity for the effective Next root, `app/_dream/views/**`, root commands, dynamic crawler owner, and Vite-image-only rollback boundary.

## 6. 输入 / 输出说明

- Input: the single binding above, the stable 116-path shared worktree, and the `SUO-420` minimal maintenance-doc amendment.
- Intended and actual output: a buildable root Next Web Shell/App Router, behavior evidence, one verified immutable Vite rollback image, and explicit 411-02/03 handoff. All five `N1-*` acceptance items now have fresh evidence.
- Generated build input: `frontend/dist/**` is the ignored pre-exit Vite bundle used to create the content-addressed rollback image. It is not a source owner or an accepted rollback target; only the report-named image digest is accepted.

## 7. 依赖项、阻断和 owner/action

### 7.1 Resolved source blocker

`SUO-421` is done. Its canonical amendment authorized the 32-file non-router `frontend/app/_dream/pages/**` to `frontend/app/_dream/views/**` move and current inbound-reference updates. The move parity/negative scans pass, and standard `NODE_ENV=production pnpm run build` now exits `0` with one root App Router manifest.

### 7.2 Resolved first-class blockers

- `SUO-423` restored Docker Desktop; fresh `docker info --format ...` returned server `28.2.2`.
- `SUO-424` attributed both Chat failures to fixture drift without production changes. This heartbeat reran the original commands: Dream reconnect `1 passed (5.9s)` and queued-send `1 passed (6.5s)`.
- The rollback selector initially exposed that one URL could not simultaneously represent an isolated container-internal backend and a browser-visible API origin. The authorized local deploy entry now separates those values and accepts an explicit existing Docker network. Its final isolated smoke passed; no blocker or clarification remains.

## 8. 验收矩阵与测试策略

| Acceptance | Current result | Evidence / next owner action |
|---|---|---|
| `N1-01-root` | Pass for 411-01 | Exact owner/delete/import scans pass; the 32-file move is content-preserving; production build exits `0`; route manifest is root-only; pnpm lock remains missing/untouched and belongs to 411-03. |
| `N1-02-client` | Pass | Server layout imports the `ssr:false` Client shell only; production build prerender succeeds; dev and production Chrome journeys render without SSR/browser-global failures. |
| `N1-03-regression` | Pass for 411-01 | Root URL/login/refresh/direct Dream/OAuth/runtime-config/voice URL, six Voice/Writing SSE contracts, Thread binding, Dream reconnect, and queued-send/resume gates pass. The two repaired Chat fixtures were rerun fresh; no production behavior changed. No real backend/business/model lane was authorized. |
| `N1-04-route-owner` | Pass for 411-01 | Build manifest contains one health, one MCP dynamic route, one phase1 status, one sandbox route, and one each for robots/sitemap/llms; Runtime/P0 remain 411-02/03 handoffs. |
| `N1-rollback` | Pass for 411-01 | The selector started exactly `ink-dream/frontend-vite-rollback@sha256:289bd32e5fae92b47e8f4cd17e1940e5d164748cce0cf7a471b56ff86f45de1f`; root/API/data/OAuth proxy and two Chrome journeys passed, then the exact task container/network/port resources were removed. |

### 8.1 Commands and concrete results

| Command / method | Exit | Key output |
|---|---:|---|
| Baseline artifact vs current pre-write status comparison | `0` | `116` paths and SHA-256 `65e187…09b44d` matched exactly. |
| `cd frontend && pnpm exec vite build` before Vite-owner deletion | `0` | Vite 8.1.5 transformed 3,092 modules and wrote the fresh ignored `dist/` baseline. |
| Initial `pnpm run build` with inherited `NODE_ENV=development` | `1` | Compiled, then `_global-error` prerender failed under the non-standard ambient environment; Next emitted the explicit non-standard `NODE_ENV` warning. |
| `cd frontend && NODE_ENV=production pnpm run build` | `0` | Next 16.1.6 compiled, prerendered four static pages, finalized traces, and emitted the unique route table. |
| `cd frontend && NODE_ENV=development PORT=5173 pnpm run dev` | `0` on owned Ctrl-C | Root `next dev` reached ready in 722 ms with no project location argument; health, `/`, Chat, Dream, and crawler-handler requests were served. |
| `cd frontend && NODE_ENV=production PORT=5173 pnpm run start` | `0` on owned Ctrl-C | Root `next start` reached ready in 244 ms with no project location argument; health and four direct page paths returned `200`. |
| `pnpm exec eslint app app/_dream/App.tsx app/_dream/router/story-workspace.tsx app/_dream/lib/apiBase.ts app/_dream/views/story-workspace e2e/root-next-shell.spec.ts` | `0` | Zero errors; 14 pre-existing `App.tsx` exhaustive-deps warnings were reported. |
| `pnpm exec playwright test app/_dream/views/story-workspace/__tests__ --reporter=line --workers=1` | `0` | 90/90 moved-module contract tests passed. |
| `pnpm exec playwright test e2e/root-next-shell.spec.ts --reporter=line --workers=1` against dev and start | `0`, `0` | Installed system Chrome 152: 1/1 passed in both lanes; visible login, canonical Chat, refresh, direct Dream, and zero diagnostics. |
| Focused OAuth callback test from `e2e/claude-mcp-resources.spec.ts` | `0` | 1/1 passed; callback auto-submit retained code/state only in the request and removed it from page/storage. |
| `pnpm exec playwright test app/_dream/lib/__tests__/apiBase.test.ts --reporter=line --workers=1` | `0` | 2/2 passed; startup runtime config remains authoritative for REST and voice WebSocket URLs. |
| Voice/Writing SSE plus Chat resume focused batch | `1` | 7/9 passed: all six Voice/Writing SSE contracts and Thread binding conflict passed; Chat reconnect timed out and queued-send found an unmocked current `/api/claude-agent/skill-commands` request. |
| `pnpm exec playwright test app/_dream/components/chat/__tests__/ChatDreamReconnect.test.ts --reporter=line --workers=1` | `0` | Fresh parent-task rerun: `1 passed (5.9s)`; paged history stabilization, reconnect SSE, and ordinary Chat resume succeeded. |
| `pnpm exec playwright test app/_dream/components/chat/__tests__/ChatQueuedSend.test.ts --reporter=line --workers=1` | `0` | Fresh parent-task rerun: `1 passed (6.5s)`; lazy first-turn send remained exactly once with the current common Skill boot fixture. |
| Root config ESM load/assertion | `0` | `root-next-config=ok`; regular build does not force standalone. |
| Exact five-Vite/twelve-nested/root-route/script/import/symlink scan | `0` | `closed-set-scan=ok`; `frontend/app/app`, root/src Pages owners, old imports, symlinks, positional Next arguments, and Vite scripts are absent. |
| Source/destination move comparison | `0` | 32/32; only the relocated `__tests__/.folder.md` intentionally differs for path ownership. |
| `test ! -e frontend/pnpm-lock.yaml && git diff --exit-code -- frontend/pnpm-lock.yaml` | `0` | `pnpm-lock=missing-untouched`. |
| `bash -n deploy/local/deploy.sh && sh -n frontend/docker-entrypoint.sh` | `0` | Both authorized entrypoints are syntactically valid. |
| Authorized-path `git diff --check` | `0` | No whitespace errors. |
| `docker info` after `open -a Docker` and 20 two-second probes | `1` | Docker CLI 28.2.2 exists, but Desktop daemon remained unavailable; no image/container mutation occurred and no alternative runtime is installed. |
| `docker info --format 'client={{.ClientInfo.Context}} server={{.ServerVersion}}'` | `0` | Current daemon receipt: `client=desktop-linux server=28.2.2`; this supersedes the earlier harness prerequisite failure. |
| Content-addressed rollback image build + inspect | `0` | Vite bundle manifest `d002d4…ee817`; tag `ink-dream/frontend-vite-rollback:task-411-01-d002d4a220a7`; image ID/repo digest `sha256:289bd3…45de1f`; base `nginx:1.27.5-alpine@sha256:65645c…2f2a10`. |
| `LOCAL_FRONTEND_RUNTIME=vite-image ... deploy/local/deploy.sh --check/start` with exact digest and isolated network | `0` | Selector joined only `ink-task411-01-rollback-<run>`, started only `ink-frontend-vite-task411-01-rollback-<run>`, served `/` `200`, same-origin runtime config, and proxied API/data/OAuth probes with `200`. |
| Rollback-image `e2e/root-next-shell.spec.ts` / OAuth callback focused test | `0`, `0` | System Chrome root journey `1 passed (5.0s)`; OAuth callback secrecy/state journey `1 passed (3.3s)`. |
| Rollback cleanup receipt | `0` | Exact task container and network absent; ports `45173` and `48765` have zero listeners. The verified image digest is intentionally retained as the rollback artifact. |
| Targeted image cardinality inspect | `0` | Accepted image reports exactly one repo tag and one repo digest, both named above. A global unfiltered `docker image ls` still hits an unrelated pre-existing Desktop content-store missing blob; owner is Docker Desktop maintenance, but exact inspect/start/run remain healthy and the task rollback is not blocked. |
| Markdown parity/path inventory plus `git diff --check` | `0` | README H2 counts are `10/10`; every directly referenced Task/Stage/Issue/design/source path exists; changed Markdown has no whitespace errors. |
| Post-run listener check | `0` | Ports 5173 and 8765 are free; only the two frontend processes started by this run were stopped. |

Harness mistakes are not hidden: the repository QA preflight still requires the intentionally deleted `frontend/vite.config.ts`; one initial move comparison treated the authorized relocated `.folder.md` edit as byte drift; one syntax command used the wrong working directory; and two scans assigned zsh's special `path` variable before corrected reruns. The first generated rollback wrapper encoded an invalid nested shell CMD and was superseded before acceptance; the next smoke exposed the internal/browser URL collision that the final selector change fixes. None of those failed attempts is used as pass evidence; their named resources were cleaned and only the digest above remains accepted.

### 8.2 Unrun verification

- The full 38-spec browser suite was not run. Proportional focused route/auth/OAuth/SSE/cancel/resume/voice/Chat tests cover the migrated boundary, including both formerly failing Chat gates.
- No real backend, database, user, model, Gateway, or deployment mutation ran; this is provider-free technical verification only.
- No additional Markdown inventory script exists under `scripts/`; the explicit parity/path/diff check above is the repository-local evidence used.

These are declared scope limits, not remaining blockers and not real-business claims.

## 9. dirty-tree、checkout 和 single-assignee 证据

- Scoped wake and heartbeat context confirm this Agent as sole assignee with no user assignee.
- Harness checkout was already active; the required no-duplicate-checkout rule was respected.
- The prior 116-path snapshot and SHA-256 were byte-identical at resume.
- All pre-existing out-of-scope dirty paths remain present and untouched.
- `SUO-421`, `SUO-423`, and `SUO-424` are done. New/changed source paths remain confined to the amended closure, child-owned Chat fixture repair, maintenance-doc/rollback-selector completion, generated verification outputs, and this report. No pnpm lock, package-lock, Runtime package, backend, schema, forbidden deploy, or production flag was written by this execution.

## 10. 完成标志、报告字段与 Stage handoff

- [x] Fresh execute template and authorization re-read
- [x] Checkout/single-assignee and dirty baseline reconfirmed
- [x] Root owner and authorized `app/_dream/views/**` migration implemented inside the amended closed set
- [x] Root dev/build/start and unique route manifest accepted
- [x] Focused root route/auth/refresh/OAuth/runtime-config/voice URL regression accepted
- [x] Exact remaining failed commands and owner/actions recorded
- [x] Both repaired Chat SSE/resume focused gates accepted
- [x] Immutable Vite rollback image smoke accepted
- [x] README/folder documentation parity completed
- [x] All `N1-*` acceptance conditions satisfied
- [x] Ready for review/audit and Stage 2 readiness consideration

Stage 1 `N1-*` is complete, so 411-02 may enter a new, independently checked-out CEO readiness decision. This does not authorize 411-02 or 411-03 execution. The pnpm lock remains missing/untouched and exclusively owned by 411-03. Runtime, P0, standalone release, and production Apps remain unvalidated; `production_apps_effective=false` remains mandatory.

## 11. 风险提示、回滚条件与回滚步骤

### 11.1 Accepted rollback object

- Human-readable tag: `ink-dream/frontend-vite-rollback:task-411-01-d002d4a220a7`
- Required immutable selector: `ink-dream/frontend-vite-rollback@sha256:289bd32e5fae92b47e8f4cd17e1940e5d164748cce0cf7a471b56ff86f45de1f`
- Bundle manifest SHA-256: `d002d4a220a714906e7ddb16520e865408e08c1ac14905a25177da2bb33ee817`
- Storage boundary: local Docker Desktop image store in this execution workspace; no registry push was authorized or claimed.

### 11.2 Intended operational rollback after acceptance

1. Keep `production_apps_effective=false`.
2. Stop only the frontend process or exact isolated rollback container started by this task.
3. Select the digest above through `LOCAL_FRONTEND_RUNTIME=vite-image` and `LOCAL_VITE_ROLLBACK_IMAGE=<verified-digest>`. Set `LOCAL_VITE_ROLLBACK_BACKEND_URL` to the container-internal backend origin, set the browser-facing `LOCAL_VITE_ROLLBACK_API_BASE_URL` / `LOCAL_VITE_ROLLBACK_WS_BASE_URL` explicitly, and use `LOCAL_VITE_ROLLBACK_NETWORK` only when that exact isolated network already exists.
4. Verify Python API reachability, data preservation, OAuth state, and public crawler resources.
5. Retain redacted receipts; do not restore nested Next, source-built Vite default owners, `frontend/app/_dream/server/mcp-apps/**`, old locks/evidence, or production Apps.

The smoke used provider-free stable data/OAuth markers rather than real user data. It verified that switching the Web image does not require schema/data migration and that the callback state remains browser-only; production rollback still follows the normal operator account/service checks without changing persisted data.

## 12. 执行完成报告

Disposition: **completed**. The root migration builds and runs from `frontend/`, exposes one root App Router, keeps browser-only code outside SSR, preserves focused route/auth/OAuth/SSE/resume/voice/runtime-config/Chat behavior, exits the five Vite source owners, and retains exactly one verified immutable Vite rollback image. All task-owned test resources were cleaned except that intentional image artifact; no first-class blocker remains. This completion makes Stage 2 eligible only for a fresh CEO readiness/checkout and does not grant Runtime, pnpm lock, standalone, P0, Phase 1, or production Apps approval.
