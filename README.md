<!-- [Sync] 2026-09-15: route user and Thread SystemConfig persistence through exact Admin contracts. -->
<!-- [Sync] 2026-09-15: route public Reflections custom configuration through registered83 Admin operations. -->
<!-- [Sync] 2026-09-15: public complete/partial assistant persistence uses the bound Admin turn owner and original receipt recovery. -->
<!-- [Sync] 2026-09-15: three public default resolvers share registered Admin ensure; Deck Plugin role reuses current profile. -->
<!-- [Sync] 2026-09-15: prepare registered fail/envelope consumers while retaining background ownership gaps. -->
<!-- [Sync] 2026-09-15: consume registered Run cancel with original reason/full result and bounded receipts; other lifecycle gaps remain. -->
<!-- [Sync] 2026-09-15: consume registered76 OAuth-write default Workspace; original text ID/receipt and independent read scope stay explicit. -->
<!-- [Sync] 2026-09-15: document Admin Thread ownership for shared file reads and remaining settings data. -->
<!-- [Sync] 2026-09-15: document the independent Admin Preflight GET and remaining workflow domains. -->
<!-- [Sync] 2026-09-15: consume Preflight execute and explicit original receipts; default Workspace remains pending. -->
<!-- [Sync] 2026-09-15: consume full Run read/create/retry domains with scoped original receipts. -->
<!-- [Sync] 2026-09-15: prepare launch metadata types/source seam and retain production wiring gaps. -->
<!-- [Sync] 2026-09-15: record complete Admin Deck list modes and remaining SQL source candidates. -->
<!-- [Sync] 2026-09-15: record Admin-owned Deck detail and unchanged legacy Memory projection. -->
<!-- [Sync] 2026-09-15: index five Admin Deck writes, shared schema gate and closed deletion feedback. -->
<!-- [Sync] 2026-09-15: public Voice mutations consume four Admin commands with raw Memory JSON. -->
<!-- [Sync] 2026-09-15: public friendship/invitation operations use the sole Admin data authority. -->
<!-- [Sync] 2026-09-15: synchronize Admin catalog refresh and retain concurrent domain HTTP. -->
<!-- [Sync] 2026-09-15: public Deck Claude Plugin refs use Admin plus unchanged local artifact/CLI checks. -->
<!-- [Sync] 2026-09-15: discard stale Browser session results and retain success-only logout. -->
<!-- [Sync] 2026-09-15: serialize resource HTTP shutdown after producers and Factory drain. -->
<!-- [Input] Current Dream/Admin/Gateway topology, supported versions, and user-visible MCP Apps workflow. -->
<!-- [Output] Plain-language user and local-operator guide with deeper engineering details linked out. -->
<!-- [Pos] Canonical English repository entry guide; README.zh.md is the same-structure Chinese mirror. -->
<!-- [Sync] 2026-09-15: public user preferences use two OAuth-bound Admin operations with original partial merge and raw JSON projection. -->
<!-- [Sync] 2026-09-15: describe Admin-owned Deck content version transactions and remaining Deck/runtime consumers. -->
<!-- [Sync] 2026-09-15: document bound Agent Thread resume and SDK Session writes plus remaining background domains. -->
<!-- [Sync] 2026-09-15: document public Session Admin consumers and their separate background authorization dependency. -->
<!-- [Sync] 2026-09-15: document atomic user reservations and the factory-owned server persistence grant lifecycle. -->
<!-- [Sync] 2026-09-15: document retired standalone authority and explicit Admin OAuth/account checks in named scripts. -->
<!-- [Sync] 2026-09-13: update MCP Apps design references after relocation to docs/design/claude-mcp; preserve implementation and historical evidence. -->
<!-- [Sync] 2026-09-06: reorganize around getting started and using MCP Apps; retain exact setup, ownership, security, and validation facts in layered sections. -->
<!-- [Sync] 2026-09-06: add sanitized real-component screenshots for the MCP connection, App settings, and Chat interaction steps. -->
<!-- [Sync] 2026-09-06: align connection creation and App controls with the accessible Server modal and unified MCP usage-policy form. -->
<!-- [Sync] 2026-09-12: add the recoverable explicit-origin NATAPP edge-relay operator path. -->
<!-- [Sync] 2026-09-13: adopt SDK 0.2.145 and the published Runtime 0.1.9 package-root selector contract. -->
<!-- [Sync] 2026-09-13: document historical-thread resume storage boundaries. -->

Historical Dream threads keep their note links and messages when their Claude
session is unavailable in the current Runtime project: the server starts a new
Claude session in the same thread. Database and storage-access errors remain
visible failures. See the [resume contract and sequence diagram](docs/design/claude-agent/claude-session-resume-resolution.md).
<!-- [Sync] 2026-09-13: serve the opaque MCP Apps sandbox through the current frontend entry without a fixed second port. -->

<!-- [Sync] 2026-09-13: document bound Notion missing-relative-PATH compatibility and config-read diagnostics. -->
<!-- [Sync] 2026-09-13: document reported Server metadata on MCP connection details. -->

# Ink & Memory

<!-- [Sync] 2026-09-14: record the implemented Admin BFF/Browser boundary and remaining baseline migration gates. -->

Admin authentication/data-service migration is in progress on this implementation branch. The current startup commands below still describe the baseline direct-PostgreSQL path; they are not migration acceptance evidence. See the [consumer design](docs/architecture/admin-auth-data-interaction.md) and [execution/dependency gates](docs/exec/dream-admin-auth-data-plan.md). New Admin DTOs are strictly validated, and unpublished operations remain unavailable. The private BFF foundation requires explicit `INK_DREAM_PUBLIC_ORIGIN`, registered `INK_DREAM_BFF_REDIRECT_URI`, and server-only `INK_DREAM_BFF_COOKIE_SECRET` (at least 32 bytes); `INK_DREAM_BFF_LOGIN_TTL_SECONDS` defaults to 600. The actual start/callback/session/logout Route Handlers and Browser session requests now use this boundary. Login, registration and Google authentication run in Admin; Browser state receives only public user fields and in-memory CSRF. REST/SSE/file requests use the Next origin; explicit speech WebSocket selection is retained while the backend speech feature remains disabled.

The server consumer also requires explicit `INK_ADMIN_DREAM_BASE_URL`, its exact `INK_ADMIN_AUTH_ISSUER`, `INK_DREAM_API_RESOURCE`, and independent `INK_ADMIN_DREAM_SERVICE_CLIENT_ID`/`INK_ADMIN_DREAM_SERVICE_SECRET`. Configure the same registered public origin/callback and resource in Admin. Service credentials stay in the BFF/backend; public Runtime renewal receives only its purpose delegation.

<!-- [Sync] 2026-09-14: document file-relative Next compilation roots and stopped-cache backup recovery. -->

<p align="center">
  <img src="assets/banner.png" alt="Ink & Memory" width="700" />
</p>

<p align="center">
  English · <a href="README.zh.md">中文</a>
</p>

Ink & Memory is a workspace for writing with AI. You can keep long-running conversations, organize reusable Decks and Agents, connect external tools such as Notion or MCP Servers, and turn ideas into structured Dream workflows and creative assets.

This repository contains the Dream Web application and its FastAPI backend. Admin, PostgreSQL, the model Gateway, the public Python SDK, and the native Claude Runtime are maintained separately.

Resource reads/observer writes, shared request identity/profile, Chat CRUD/history/ownership, initial user-message reservation, Editor persistence, and user/Thread SystemConfig now consume Admin APIs. Runtime purpose creation/public renewal/receipt consumers have passed focused technical checks. The server user-turn grant follows the existing Factory lifecycle; Gateway CLI credentials, internal dispatch wiring, and other database domains still require migration. Old password/Google/Device/token/local-cookie HTTP paths return explicit 410 with configured Admin standard endpoints. Standalone auth helpers refuse local authority; importer Agent labels and the named Gateway verifier require explicit Admin OAuth and a matching production profile before business writes/model calls. Authlib/bcrypt have been removed without changing remaining dependency versions. Admin/Auth server secrets are cleared from child environment overlays. These source and build checks do not establish real-account business acceptance.

Browser session checks discard cancelled or superseded results. Logout invalidates pending reads while keeping the last validated session on failure; the auth context commits only the current public snapshot.

The resource Admin HTTP owner serializes background reads, observer writes and final close. Shutdown stops its producers and drains the Factory before closing it off the Agent turn; a closed owner cannot reopen or dispatch new requests.

Public Chat also reads Admin's complete Workflow context before message reservation/SSE and passes an immutable actor/thread snapshot to Service, including ordinary-Chat null. Internal confirmation/launch dispatch and the remaining purpose consumers still require migration.

Public user turns now reserve message/title through Admin's atomic confirmation guard command using raw Python JSON. A server-only Thread/Run persistence grant renews under Factory ownership and survives SSE disconnect; unknown writes keep their original receipt ID. Public Agent Thread reads, SDK-native session ID updates, and complete/cancelled/error assistant messages use that bound grant. User/session/assistant writes share original-receipt recovery, and only the latest confirmed Session update is reused. Internal dispatcher assistant writes, writing Session context/tools, Gateway/Editor credentials and other database domains remain migration work.

Public writing Session save/get/batch/list/range/aggregate/delete now use six typed Admin operations with explicit request OAuth. The original metadata/full-state responses, precise timestamps, timezone day keys and prose metrics remain; edit events publish only after confirmed writes. Shared closed Editor state DTOs omit absent optional fields. The current Session contract rejects Thread server-persistence grants, so background Session context/tools remain a separate migration dependency.

Public Deck content state/preview/commit/history/detail now use five typed Admin operations and exact schema capabilities. Admin executes snapshot/hash/CAS/version transactions; Dream restores the original raw snapshot response and preserves safe conflict details and unknown commit IDs without retrying. Other Deck/Voice operations, plugin filesystem verification and runtime consumers remain migration work.

Public Deck Claude Plugin refs now use Admin list/prepare/replace. Dream verifies the selected artifact and CLI compatibility with the existing checks before submitting source-bound evidence; other plugin installation/runtime data paths remain migration work.

Public user preference get/save now use two OAuth-bound Admin operations. Missing records still return `{}`; null preserves saved fields, empty objects and strings remain values, and raw Python config JSON keeps numeric types. Default voices, first-login writes and background preference context remain separate domains; SystemConfig is handled by the dedicated operations below.

Settings GET/PUT now use Admin's `user-system-config.get/patch`; PUT returns a fresh independent read after a confirmed patch. Public Chat reads one OAuth-bound snapshot and reuses it for model selection and attachments. Active turns use `thread-system-config.get` through the exact Thread persistence grant before prompt, Workspace or Runtime assembly. Corrupt or unavailable configuration fails closed without a Dream database fallback. Gateway model selection requires an explicit authorized snapshot, so ownerless internal dispatch remains a named migration dependency.

Public Reflections configuration GET/PUT/DELETE now uses three OAuth-bound Admin operations. A lost save/delete response is resolved only from the original request receipt and never sends a second write. `memory-init` confirms the Chat Thread owner through Admin, reads the user's custom section configuration, merges it with Dream's static prompt defaults, and only then writes the shared workspace. The ownerless background Reflections worker still reads its custom configuration and task/result state from the remaining Dream database path.

The shared Admin client serializes catalog refresh and capability checks. Failed refresh clears readiness for the next request to reload; domain HTTP remains concurrent and keeps each actor, DTO and request ID separate.

Public invitations, friend requests, relationships and friend picture reads now use nine typed Admin operations. Admin owns invitation policy and atomic transitions; Dream preserves integer IDs, labels, timestamps, errors and unknown write IDs. Other database domains and normal business acceptance remain open.

Public Deck owned/community lists now use one typed Admin operation, preserving original counts and author fields without filesystem or default-initialization steps.

Public Preflight GET uses an owner-scoped Admin read without initializing a Workspace. POST preserves its 202 response, all 17 fields and explicit original three-state receipts. Run read/create/retry preserve all 28 fields and original 200/201 responses. Default-dependent Workflow ingress now uses the registered Admin workspace-default.ensure operation before these domains; it returns the original text ID and requires OAuth dream:write for initialization, including Run GET when no server Workspace is present. Unknown writes retain their original request ID without retries. Remaining lifecycle/launch/internal agent-output persistence still needs migration. See the [Preflight rules](docs/design/workflow-preflight-read-current.md) and [Run rules](docs/design/workflow-run-admin-consumer-current.md).

Story Workflow, Deck binding and Deck Plugin current-user dependencies share the same Admin default Workspace resolver. Deck Plugin role lookup reuses the current Admin profile with OAuth read scope and canonical ID validation; existing permission checks remain. Remaining domain and background persistence still need migration.

Registered Run fail and launch failure-envelope consumers now preserve historical failed replies, raw error text and original receipt IDs. The production launch recorder still needs the Admin turn owner and must retain its two independent commits; these type checks do not establish normal model acceptance. See the [failure rules](docs/design/dream-launch-admin-metadata-current.md).

Public Workflow Run cancel now uses its registered Admin command, preserving the original reason, full 28-field response, business errors and bounded original receipt. Agent cancellation retains its existing behavior.

Launch source/claim/finish typed consumers and the original application source adapter are prepared against registered75. The production endpoint still needs OAuth actor wiring, and prepare/Voice/failure SQL remains. See the [metadata preparation rules](docs/design/dream-launch-admin-metadata-current.md).

All public Workspace file routes read the current user's SystemConfig through OAuth before filesystem access. Content/download keep Thread ownership checks first, then apply Workspace Mode, path and filesystem checks. Missing Threads retain 404; configuration or metadata failures return safe 503 responses. File, ZIP and no-create behavior remains; other file-management data dependencies are still pending.

Public Deck detail now reads one typed Admin aggregate and restores original owner IDs, timestamps and legacy Memory values. An Admin producer difference for empty Memory remains documented for correction.

Public Deck update/delete/publication/collection/parent-sync now use five Admin commands. Original results and dependency-conflict messages remain; Admin owns locks and transactions, and unknown writes retain their original request ID. [Current rules](docs/design/deck-mutations-current.md).

Public Voice create/update/delete/collect now use four Admin commands. Raw Memory JSON and omitted/null/empty fields retain their original behavior; Admin owns defaults, order, locks and draft changes. Other Deck and background data consumers still require migration.

## What you can do

- **Write and reflect** — keep writing sessions, browse your timeline, and review reflections.
- **Chat with persistent context** — continue a Thread with streaming replies, tools, plans, files, and TODOs.
- **Preview generated reports** — open Workspace Markdown reports and PNG/JPEG/GIF/WebP links in Chat, with Thread-bound images and separate download controls.
- **Build reusable Agents** — use Decks to organize prompts, resources, plugins, and Agent behavior.
- **Run Dreams** — develop scripts, storyboards, prompts, and generated assets through guided workflows.
- **Connect your tools** — authorize Notion or a managed MCP Server from Settings.
- **Use interactive MCP Apps** — when a compatible tool returns an App, use its controls directly below the collapsed assistant process.

MCP Apps are currently a technical preview. The ordinary tool result remains available if an App is disabled, unavailable, or fails to load. Production enablement still requires separate real-account, external-Server, OAuth, and operations acceptance.

## Start locally

### Requirements

- macOS or glibc Linux on arm64/x64
- Python `>=3.12` and [uv](https://docs.astral.sh/uv/)
- Node.js `>=22 <25`, Corepack, and npm
- The Admin repository, which provides PostgreSQL and the model Gateway

Windows and musl targets are not supported by the qualified native Runtime.

### 1. Get Dream and Admin

```bash
git clone https://github.com/glide-the/im-dream.git ink-dream-memory
git clone https://github.com/glide-the/dream-im-platform.git ink-admin-memory
```

Use Dream's `develop` branch and Admin's `main` branch unless a reviewed release tells you otherwise.

### 2. Prepare Admin, PostgreSQL, and Gateway

```bash
cd ink-admin-memory
pnpm install
pnpm env:setup
pnpm env:check
pnpm db:migrate
pnpm db:migrate:check
```

For a first local installation, follow the Admin README to configure `.env.local`, then provision the default subscription and Dream service identities:

```bash
pnpm db:data:subscriptions -- --apply
pnpm product:provision-local-dream
pnpm gateway:provision-local-dream
```

These commands write Admin-owned data. Use them only with the intended local database unless a separate deployment review says otherwise.

### 3. Install Dream and its Runtime

The `develop` source contract requires the published Runtime `0.1.9`. On 2026-09-13, all five public npm archives were verified byte-for-byte against the same-SHA four-platform CI release, and registry `latest` is `0.1.9`. Do not mix current Dream source with Runtime `0.1.4`; the resolver intentionally fails closed. See the [release and local adoption receipt](docs/deploy/runtime-0.1.9-release-and-local-dream-adoption.md).

```bash
cd ../ink-dream-memory/backend
uv sync --frozen

npm install --global @glide-the/ink-claude-code-dream@0.1.9
export PATH="$(npm prefix --global)/bin:$PATH"
ink-claude-code-dream --version

npm install --global ntn@0.15.1
ntn --version

cd ../frontend
corepack enable
corepack pnpm install --frozen-lockfile
```

The Runtime must print `2.1.241 (Claude Code)`. Both npm command aliases must resolve to package-root `cli.js`, whose adjacent `release-manifest.json` must declare Runtime `0.1.9`; Notion CLI must print `ntn 0.15.1`, and Corepack must resolve `pnpm@10.28.1`.

### 4. Configure Dream

Create `backend/.env` from the example and point it at the Admin environment and your workspace root:

```bash
cd ../backend
test -f .env || cp .env.example .env
```

```dotenv
DATABASE_URL=
INK_LOAD_DATABASE_URL_FROM_ENV_FILE=1
INK_DATABASE_ENV_FILE=/absolute/path/to/ink-admin-memory/.env.local

INK_GATEWAY_ENABLED=1
INK_GATEWAY_BASE_URL=http://127.0.0.1:3000

AGENT_CWD=/absolute/path/to/agentdata/agent-workspace
INK_AGENT_SANDBOX_ENABLED=true
INK_NOTION_RUNTIME_ROOT=/absolute/path/to/agentdata/notion-runtime
```

Provider keys stay in Admin; do not copy them into Dream.

### 5. Run the three services

Terminal A — Admin and Gateway:

```bash
cd ink-admin-memory
pnpm dev
```

Terminal B — Dream backend:

```bash
cd ink-dream-memory/backend
.venv/bin/python server.py
```

Terminal C — Dream Web:

```bash
cd ink-dream-memory/frontend
INK_BACKEND_INTERNAL_URL=http://127.0.0.1:8765 \
NEXT_PUBLIC_WS_BASE_URL=ws://127.0.0.1:8765 \
corepack pnpm run dev --hostname 127.0.0.1 --port 5173
```

Open:

- Dream: <http://127.0.0.1:5173>
- Admin: <http://127.0.0.1:3000/admin>
- Dream API: <http://127.0.0.1:8765>

## Use MCP Apps

### Local preview services

Keep the existing Admin, backend and Next.js services. Start the external MCP
Server before opening its connection detail; Next.js already includes the Host.
With the existing preview/plugin policy configured, Next.js also serves
`/mcp-apps-sandbox`. Its URL follows the browser's current frontend scheme,
hostname and port; no separate sandbox process or port is required. Legacy
`INK_MCP_APPS_SANDBOX_URL` and `INK_MCP_APPS_PARENT_ORIGINS` are no longer used.
Both iframe layers and the sandbox response CSP enforce opaque document origins
without `allow-same-origin`; sharing the frontend URL does not grant App content
access to the frontend DOM or storage. Authentication and permissions are unchanged.
If discovery ran before the MCP Server started, re-enter or refresh the detail
page after starting it; valid cached failures may remain until their TTL expires.
If an App has already fallen back, use **Try interactive view again** after
the frontend and external MCP Server are available.
See the [local recovery design and evidence](docs/exec/mcp-apps/local-startup-recovery.md).

### Add a connection and enable its App

1. Sign in to Dream and open **Settings → Resource Links**.
2. Click **Add MCP Service**, enter the managed endpoint in the dialog, or open an existing connection, then complete its authentication.
3. On the connection detail page, find **Usage policy**.
4. Turn on **Use App in Chat**. If needed, also allow **Low-risk tool calls** and **Send messages to this chat**.
5. Changes save automatically. A save failure retains your choice and retries; do not look for a save button.

Connection details display the Server's reported name and version when supplied. Missing Server metadata does not hide its tools, resources, or prompts. See the [current connector design](docs/design/claude-mcp/claude-mcp-resource-connector-current-design.md#7-api-合同).

These screenshots use safe example data and the real production UI components; they contain no account details or secrets.

![Add a managed MCP connection by entering its name, transport, and URL](assets/mcp-apps-guide/01-add-mcp-connection.png)

*Open the Add MCP Service dialog from Resource Links and enter the managed endpoint. Authentication requirements are detected after Dream connects to the Server.*

![Enable the MCP App and choose its permitted interactions](assets/mcp-apps-guide/02-configure-mcp-app.png)

*One usage-policy group contains the App switch and interaction choices. The current UI saves automatically and no longer displays the historical screenshot's status or save footer.*

Default policy, your saved choice, and actual server status remain separate. A switch may be on while the App remains unavailable if the connection is offline, the Server does not advertise an App, or the server-side preview policy does not allow it.

### Call and use the App in Chat

1. Open Chat and select a Deck/Agent that can use the connection.
2. Ask the Agent to use the relevant MCP tool, for example: “Check the server time.”
3. The model calls the tool normally and writes its answer.
4. The assistant's reasoning and ordinary tool details remain under the **View process / Took…** disclosure.
5. A verified interactive App appears outside that disclosure, so collapsing the process does not hide the App.
6. Use the App's buttons or fields directly. A permitted in-App tool action updates the App without starting another model turn. If the App sends a message to Chat, it becomes a normal user message and starts one new Agent turn.

![A collapsed MCP tool result with its interactive App still visible below it](assets/mcp-apps-guide/03-use-mcp-app-in-chat.png)

*The tool details are collapsed at the top; the official example App remains available below for direct interaction.*

You can close and reopen the interactive view. Refreshing, switching Threads, changing permissions, or changing the connection revision creates a fresh governed session; the original tool is not replayed.

Dream adapts the original Runtime's SDK MCP text, content-array and metadata-envelope
results into App-compatible content without parsing text or changing permissions.
After updating Python code, restart your owned backend before testing a new normal
Chat tool call. Older rows that lost the SDK envelope retain their ordinary result;
Dream does not fabricate missing metadata or replay those tools.

The complete engineering flow—connection discovery, model tool call, call-ID association and result DTO validation, live/history recovery, Browser Host, Node proxy, sandbox, permissions, and Chat-message re-entry—is documented in [MCP Apps and IM Agent UI design](docs/design/claude-mcp/mcp-apps-integration-strategy.md#32-端到端调用链).

## Supported versions and ownership

| Component | Supported version / owner |
| --- | --- |
| Dream integration branch | `develop` |
| Dream project metadata | backend `0.1.3`, frontend `0.0.3`; API schema remains `2.0.0` |
| Python | `>=3.12` |
| Node.js | `>=22 <25`; deployment images use Node 22 |
| Frontend package manager | `pnpm@10.28.1` through Corepack |
| Next.js / React | `next@16.1.6`, `react@19.1.0`, `react-dom@19.1.0` |
| Python SDK | `ink-claude-dream-agent-sdk==0.2.145` |
| Native Runtime | Published `@glide-the/ink-claude-code-dream@0.1.9`; registry `latest` is `0.1.9` as of 2026-09-13 |
| Runtime compatibility output | `2.1.241 (Claude Code)` |
| Notion CLI | `ntn@0.15.1` |
| Shared PostgreSQL schema, Admin, Gateway, billing | `dream-im-platform` / Admin repository |
| Dream Web, Thread/Run/Workspace integration | This repository |

Package ownership is intentional: `uv` manages Dream's Python environment, npm distributes the native Runtime and Notion CLI, and pnpm manages `frontend/`. `uv sync` does not install or upgrade the native Runtime.

For Notion `Failed to read config.json`, distinguish file-read failure from malformed JSON and inspect the final Agent Bash binding. Runtime 0.1.9 rejects relative PATH entries before its native `ntn` candidate. Dream omits only relative directories proven absent at the current thread cwd from that bound launch's SDK environment, preserving valid command order and all strict shadow checks. It does not change shell profiles, parent PATH, credentials, or non-Notion turns. `ntn doctor` exit 0 alone is insufficient: inspect warnings and verify a read-only request through normal Chat.

Runtime `0.1.9` keeps the original modules as its single `src` implementation (1,902 unchanged files, 35 original module directories) and removes the duplicate `restored-src` directory. The default build reads `src/entrypoints/cli.tsx`; no second Runtime implementation is maintained. Source-bound headless, MCP and Dream compatibility transforms stay in the build layer. Original copyright and the user-attested redistribution boundary are preserved in the artifact. Dream's exact Runtime pin and project metadata move together; local adoption requires verified public archives and the owned backend's startup identity, not merely source edits. See the [release and local Dream adoption plan](docs/deploy/runtime-0.1.9-release-and-local-dream-adoption.md).

Admin Drizzle is the only owner of shared PostgreSQL migrations. Dream consumes exact published capabilities and fails closed when a required capability is missing. MCP App connection settings require Admin migration `0053_rare_lenny_balinger` and capability `dream.mcp-app-connection-settings.v1` before the matching Dream code is released.

## Build and test

Common provider-free checks:

```bash
# Backend
PYTHONPATH=backend uv run --native-tls --project backend --frozen \
  --with pytest==9.1.1 --with pytest-asyncio \
  python -m pytest backend/tests -q

# Frontend
corepack pnpm --dir frontend exec tsc --noEmit --incremental false
corepack pnpm --dir frontend lint
NODE_ENV=production corepack pnpm --dir frontend build

# MCP Apps Browser/Node contracts
corepack pnpm --dir frontend test:mcp-apps-runtime
corepack pnpm --dir frontend typecheck:mcp-apps
```

Post-publication SDK/Runtime registry acceptance:

```bash
python3 scripts/verify_claude_registry_release.py \
  --sdk-version 0.2.145 \
  --runtime-version 0.1.9 \
  --expected-cli-version '2.1.241 (Claude Code)'
```

Build the standalone Web image only from the pnpm/Next workspace:

```bash
INK_NEXT_OUTPUT=standalone NODE_ENV=production \
  corepack pnpm --dir frontend run build:docker
test -f frontend/.next/standalone/server.js
```

Focused MCP Apps commands and the current provider-free evidence are listed in [the MCP Apps validation receipt](docs/exec/mcp-apps/current-candidate-validation.md). Provider-free tests are technical checks, not proof of production availability.

## Safety and release boundaries

- Secrets, Provider keys, MCP credentials, transcripts, and Workspace content must not enter Git or Browser-visible configuration.
- Dream never creates or migrates the shared schema at runtime. Apply reviewed Admin Drizzle migrations first.
- Missing capabilities, mismatched Runtime/SDK versions, stale revisions, unavailable credentials, or invalid policy fail closed; ordinary MCP results remain the fallback where possible.
- Browser MCP Apps connect only to the authenticated same-origin Node endpoint. The real Server address and credential stay server-side, and App content runs in a restricted iframe sandbox.
- Tests and local launchers may stop or delete only resources they created.
- Roll back only to an explicitly reviewed immutable image or release; do not restore retired npm/Vite build paths.
- MCP Apps remain production-off (`productionAppsEffective=false`) until a separate real-business acceptance changes that contract.

For deployment profiles, see [deploy/README.md](deploy/README.md). AutoDL now builds the same canonical Next.js workspace with the frozen pnpm lock and includes the server-only MCP Apps runtime; legacy Vite/npm/dist release paths are unsupported. An Alibaba edge that relays the existing public domains to explicit NATAPP Dream/Admin origins uses the recoverable [edge-relay procedure](docs/deploy/natapp-edge-relay.md), not an inferred Compose upstream.

## Troubleshooting

If Next reports `Could not find the module ... in the React Client Manifest`, check its compilation root and cache before changing application modules. `frontend/next.config.js` derives `turbopack.root` from its own file location, not the launch working directory or ancestor lockfiles. Stop the frontend, confirm `.next/dev/lock` has no active owner, move only `frontend/.next` to an independent backup, then restart to rebuild. Do not delete parent lockfiles, reinstall unrelated dependencies, move environment/database files, or weaken the client boundary. Configuration regression: `corepack pnpm --dir frontend exec playwright test e2e/next-config.test.ts --workers=1 --reporter=line` (no browser or service required).

### The App does not appear

- Confirm the MCP connection is connected and the tool advertises an App.
- Open **Settings → Resource Links → connection → Usage policy** and compare the default policy, your saved choice, and the actual status.
- Confirm Admin migration `0053_rare_lenny_balinger` is applied and `dream.mcp-app-connection-settings.v1` is published.
- Retry the Chat call after the connection inventory refreshes. For compact historical rows, expand the process once to load the saved detail; after loading, the App stays visible when the process is collapsed.
- If policy, authentication, or the sandbox is unavailable, the ordinary result is the expected fallback.

### `Dream Claude Runtime is not production-qualified`

```bash
command -v ink-claude-code-dream
readlink "$(command -v ink-claude-code-dream)"
ink-claude-code-dream --version
cd backend
.venv/bin/python -c 'from libs.claude_agent_kit.server.sdk_env import resolve_claude_cli_path; print(resolve_claude_cli_path())'
```

The current source requires Runtime `0.1.9` and output `2.1.241 (Claude Code)`. The default npm target must resolve to package-root `cli.js`; Dream reads `release-manifest.json` beside it and verifies the exact version, `runtime.entrypoint`, stream protocol, 14 required capabilities, production flags, and selector digest. The separately qualified, non-redistributable AutoDL local-core artifact retains its exact `bin/ink-claude-code-dream` entrypoint, release-root manifest, and 13-capability baseline. Dream distinguishes these layouts rather than treating one as the other; an older registry package, a mismatched layout claim, or fixture-only candidate evidence is rejected. Install the exact release on normal `PATH`, then restart only the service you own. `CLAUDE_CODE_CLI_PATH` is reserved for an explicitly reviewed absolute-path rollback.

### `uv sync` removed pytest

`uv sync` removes undeclared packages. Use the temporary `uv run --with pytest...` command from [Build and test](#build-and-test), or add a development dependency in a separate reviewed change.

### The Web page cannot reach an API or Voice

On this migration branch, REST/SSE/files stay on the Next origin and use authenticated Route Handlers. Configure the backend origin with server-only `INK_BACKEND_INTERNAL_URL` (or `BACKEND_URL`), and verify the Admin service configuration and BFF cookies. Generic API/auth rewrites are removed. Explicit speech WebSocket configuration is retained; speech recognition remains disabled in the backend.

### A build still asks for npm/Vite files

The active Web workspace uses Corepack/pnpm, Next, `.next`, and `frontend/pnpm-lock.yaml`. A workflow looking for `frontend/package-lock.json`, `vite.config.ts`, or production `dist/index.html` is obsolete.

### PostgreSQL capability or model is unavailable

Run the Admin migration check, verify the Admin-owned environment file, and configure an enabled/priced model alias plus Provider credential in Admin. Dream accepts platform model aliases, not Browser-supplied Provider IDs or keys.

## More documentation

- [MCP Apps end-to-end design](docs/design/claude-mcp/mcp-apps-integration-strategy.md#32-端到端调用链)
- [MCP Apps current technical evidence](docs/exec/mcp-apps/current-candidate-validation.md)
- [Repository maintenance rules](Agent.md)
- [Agent product behavior](docs/Agent.md)
- [Rules index](docs/rules/README.md)
- [Deployment guide](deploy/README.md)
- [SDK/Runtime packaging](docs/deploy/claude-sdk-runtime-packaging-and-integration.md)
- [Registry acceptance](docs/deploy/claude-registry-release-acceptance.md)

Keep `README.md` and `README.zh.md` structurally aligned. Preserve unrelated working-tree changes, update affected file headers and folder contracts, and report exact validation commands and any remaining release action.

For multi-file exports, the Agent may run `zip` from the workspace root with an explicit `.zip` output and explicit ordinary inputs (e.g. `zip -r files/export-bundle.zip files/scene`) and link the resulting binary archive, or link a dedicated workspace directory whose download packages a real ZIP. Dot-prefixed runtime paths, workspace escapes, symlinks, broad `.`/glob inputs, and shell-composed archive commands stay denied. The production backend image and the AutoDL direct-host release install Info-ZIP for this path.
