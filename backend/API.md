# Ink & Memory API Documentation
<!--
[Input] Backend FastAPI routes and deployment public URL configuration.
[Output] Human-readable API reference for authenticated app APIs and public utility endpoints.
[Sync] 2026-06-14: document public SEO endpoints generated from INK_PUBLIC_BASE_URL and INK_BACKEND_PUBLIC_BASE_URL.
[Sync] 2026-06-15: remove /ink-and-memory frontend path prefix from public SEO endpoint notes.
[Sync] 2026-08-31: document curated latest-first Blog and Knowledge Base references in llms.txt.
[Sync] 2026-06-21: document system-config sandbox network policy fields.
[Sync] 2026-06-23: document Google OAuth, auth cookie aliases, and OAuth Device Flow endpoints.
[Sync] 2026-08-14: document transactional default Free provisioning and Admin-default model resolution for email and Google registration.
[Sync] 2026-08-14: document screenplay-only Deck visibility and atomic drama-forge v1.0.1 binding on Deck creation.
[Sync] 2026-08-14: document explicit zero-ref default screenplay Deck reconciliation.
[Sync] 2026-08-15: document missing default creation for legacy actors through the same reconciliation route.
[Sync] 2026-08-16: document transactional Deck deletion and preserved-dependency conflicts.
[Sync] 2026-08-16: document exact runtime binding history used by the folded Deck version panel.
[Sync] 2026-08-16: document capability-gated Deck draft/preview/explicit content commit/history.
[Sync] 2026-08-17: document Deck-filtered Chat history and corrected related-thread/binding deletion semantics.
[Sync] 2026-08-22: document per-thread CLAUDE_CODE_TMPDIR and the Workspace Mode disabled runtime-only boundary.
[Sync] 2026-08-22: restore authenticated Claude MCP Resources configuration, OAuth lifecycle, inventory, and removal contracts.
[Sync] 2026-08-25: replace the stale Claude CLI MCP contract with managed-PostgreSQL CRUD, standard-SDK discovery, encrypted OAuth, and automatic browser callback semantics.
[Sync] 2026-08-22: document retryable Claude Agent capacity and memory-pressure SSE errors.
[Sync] 2026-08-29: document the authenticated Notion connector capability catalog, parsed Skill detail, and revision-aware stable-ID Markdown file reads.
[Sync] 2026-08-29: capability schema v2 derives Skill metadata/files from the installed package and operations from the real Read hook/workspace materializer entrypoints.
[Sync] 2026-08-31: remove daily-picture mutation/generation and legacy voice-analysis APIs; historical picture reads remain.
[Sync] 2026-09-02: document stable Chat message pages, latest-ID stabilization, and legacy full-history compatibility.
[Sync] 2026-09-02: document final-only assistant pages and owned exact-id process detail.
-->

**Version:** 2.0.0
**Base URL:** `http://localhost:8765` (dev backend) | `https://ink-backend.suoxya.com` (prod backend). Public app URLs in crawler files come from `INK_PUBLIC_BASE_URL`; backend API links come from `INK_BACKEND_PUBLIC_BASE_URL`.

## Authentication

All endpoints except `/api/register`, `/api/login`, Google OAuth entry/callback, Device Flow code issuance, and `/api/default-voices` require authentication.

**Header:** `Authorization: Bearer <JWT_TOKEN>`

Browser clients may also authenticate with the backend-issued `access_token`
HttpOnly cookie. Google `id_token` / `access_token` values are never accepted
as business API credentials.

JWT access token lifetime is configured by `JWT_EXPIRES_IN` and defaults to 1 hour in this project. Expiration is sliding: any authenticated request made while less than half of the lifetime remains receives a freshly signed token in the `X-New-Access-Token` response header (and a refreshed `access_token` cookie for cookie-based clients), so active sessions stay signed in indefinitely.

---

## Public SEO Endpoints

These endpoints do not require authentication. The frontend nginx service proxies root-level requests for these files to the backend so crawler content stays environment-driven.

### GET `/robots.txt`

Returns crawler policy for the public app. Search visibility crawlers such as `GPTBot`, `OAI-SearchBot`, `ChatGPT-User`, `ClaudeBot`, and `PerplexityBot` can access the public app path, while private API and websocket paths are excluded.

### GET `/sitemap.xml`

Returns an XML sitemap for the public SPA surface using `INK_PUBLIC_BASE_URL` as the canonical app URL.

### GET `/llms.txt`

Returns a structured AI-search summary describing Ink & Memory, primary public pages, a latest-first Blog and Knowledge Base list, product facts, keywords, backend API origin, and authenticated API boundaries. The newest bilingual connector essay points only to its published Medium and WeChat originals; no unpublished site URL is synthesized.

---

## Auth Endpoints

### POST `/api/register`

Register a new user.

The successful response is emitted only after the Admin-owned PostgreSQL
registration triggers have created the canonical user's billing projection,
active Free subscription, current-period Token allowance, and activation
event in the same transaction. Dream does not write or reconstruct billing
state. Google OAuth signup has the same postcondition because it uses the same
canonical user creation path.

The Free plan's Admin-owned default entitlement supplies the effective model
when the user has not saved an explicit model preference. Dream does not copy
that alias into a second registration-time default; Settings and Claude Agent
resolve the live callable `defaultModelAlias` from the Gateway catalog.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "display_name": "Optional Name"
}
```

**Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "display_name": "Optional Name"
  }
}
```

**Errors:**
- `400` - Email/password missing or password < 6 chars
- `400` - Email already exists
- `503` - Canonical user/default Free provisioning transaction could not
  commit; retry after the registration dependency is restored

---

### POST `/api/login`

Login with email and password.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "display_name": "Optional Name"
  }
}
```

**Errors:**
- `401` - Invalid email or password

---

### GET `/api/me`

Get current user info from token.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "display_name": "Optional Name",
  "created_at": "2025-11-02 05:20:53"
}
```

**Errors:**
- `401` - Missing or invalid token
- `404` - User not found

---

### GET `/auth/me`

Alias of `/api/me` for OAuth-oriented clients. Accepts either
`Authorization: Bearer <token>` or the backend-issued `access_token` cookie.

---

### POST `/auth/logout`

Revokes the current refresh token when present and clears auth cookies.

**Headers:** `Authorization: Bearer <token>` or auth cookie

**Response:**
```json
{
  "success": true
}
```

---

### GET `/oauth/google/login`

Starts Google OAuth/OIDC login through the Python backend Authlib client.

**Query:**
- `return_to` - Optional frontend-relative path to return to after login, for example `/` or `/oauth/device/verify?user_code=ABCD-1234`.

**Response:** `302` redirect to Google.

---

### GET `/oauth/google/callback`

OAuth callback registered in Google Cloud Console. The backend validates OAuth
state through the session cookie, exchanges the Google code, binds or creates
the local user (including transactional default Free provisioning for a new
canonical user), then issues this system's own access/refresh tokens.

**Response:** `302` redirect to frontend with auth cookies set.

**Errors:** redirects to the frontend with `auth_error`.

---

## OAuth Device Flow Endpoints

### POST `/oauth/device/code`

Create a Device Authorization request for CLI/Desktop/Agent/MCP clients.

**Request:**
```json
{
  "client_id": "ink-cli",
  "scope": "profile"
}
```

**Response:**
```json
{
  "device_code": "opaque-device-code",
  "user_code": "ABCD-1234",
  "verification_uri": "http://localhost:5173/oauth/device/verify",
  "verification_uri_complete": "http://localhost:5173/oauth/device/verify?user_code=ABCD-1234",
  "expires_in": 600,
  "interval": 5
}
```

---

### GET `/oauth/device/verify`

Returns verification metadata for the browser confirmation page.

**Query:** `user_code=ABCD-1234`

---

### POST `/oauth/device/verify`

Approve or deny a pending user code. Requires the browser user to be logged in.

**Headers:** `Authorization: Bearer <token>` or auth cookie

**Request:**
```json
{
  "user_code": "ABCD-1234",
  "approve": true
}
```

---

### POST `/oauth/token`

Supports Device Code Grant and refresh-token rotation.

**Device Code Request:**
```json
{
  "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
  "device_code": "opaque-device-code",
  "client_id": "ink-cli"
}
```

**Success:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1...",
  "refresh_token": "opaque-refresh-token",
  "token_type": "Bearer",
  "expires_in": 900
}
```

**OAuth errors:**
```json
{
  "error": "authorization_pending",
  "error_description": "Authorization has not completed yet."
}
```

Known Device Flow errors include `authorization_pending`, `slow_down`,
`expired_token`, `access_denied`, `invalid_grant`, and `invalid_client`.

---

## Migration Endpoint

### POST `/api/import-local-data`

One-time import of localStorage data to database on first login.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "currentSession": "{\"cells\": [...]}",
  "calendarEntries": "{\"2025-11-01\": [...]}",
  "dailyPictures": "[{\"date\": \"2025-11-01\", \"base64\": \"...\"}]",
  "voiceCustomizations": "{\"Logic\": {...}}",
  "metaPrompt": "Be helpful",
  "stateConfig": "{\"states\": {...}}",
  "selectedState": "happy",
  "analysisReports": "[{\"type\": \"echoes\", \"data\": {...}}]",
  "oldDocument": "{\"document\": \"...\"}"
}
```

All fields are optional. Strings should be JSON-stringified.

**Response:**
```json
{
  "success": true,
  "imported": {
    "sessions": 6,
    "pictures": 2,
    "preferences": 4,
    "reports": 3
  }
}
```

**Errors:**
- `401` - Missing or invalid token

---

## System Config

### GET `/api/system-config`

Returns the current user's Settings configuration as a JSON object.

Known fields include:

```json
{
  "provider": "anthropic",
  "model": "claude-sonnet-4-20250514",
  "system_prompt": "You are...",
  "workspace_enabled": true,
  "sandbox_network_mode": "allowlist",
  "sandbox_network_allowed_domains": ["raw.githubusercontent.com", "github.com"],
  "sandbox_fs_allowed_write_paths": ["/data/out"],
  "im_full_access_enabled": false,
  "theme": "system",
  "env_vars": {
    "ANTHROPIC_MODEL": "claude-sonnet-4-20250514"
  }
}
```

### PUT `/api/system-config`

Merges accepted fields into the current user's Settings configuration.
Unknown keys are ignored. `sandbox_network_mode` accepts `disabled`,
`allowlist`, or `open`. `sandbox_network_allowed_domains` is sanitized to a
flat domain-pattern list; use `open` mode instead of sending a bare `*`.
`sandbox_fs_allowed_write_paths` is sanitized to absolute paths only
(trailing slashes stripped, deduped, capped).

The sandbox network fields are consumed on the next Claude Agent workspace
initialization and written to the thread-local `.claude/settings.json`
`sandbox.network` block; `sandbox_fs_allowed_write_paths` is appended to the
`sandbox.filesystem.allowWrite` list after the thread workspace and the exact
server-owned Claude Code temp root (`CLAUDE_CODE_TMPDIR`, default
`{AGENT_CWD}/{thread_id}/.claude-tmp`, canonicalized, created as `0700` before
the subprocess starts, and always allowed when the sandbox is enabled). The
application does not broadly allow `/tmp` or guess per-UID/dynamic `cwd-*` paths.
This runtime-only directory is prepared even when Workspace Mode is disabled;
that does not initialize the full workspace, pass `cwd`, inject workspace
context, or expose file surfaces.

---

## Session Storage

### POST `/api/sessions`

Save or update a session.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "session_id": "my-session-123",
  "name": "My Session Name",
  "editor_state": {
    "cells": [
      {"type": "text", "content": "Hello world"}
    ],
    "commentors": []
  }
}
```

**Response:**
```json
{
  "success": true
}
```

---

### GET `/api/sessions`

List all sessions for current user (metadata only, no editor_state).

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "sessions": [
    {
      "id": "session-123",
      "name": "My Session",
      "created_at": "2025-11-02 05:22:41",
      "updated_at": "2025-11-02 05:22:41"
    }
  ]
}
```

---

### GET `/api/sessions/events`

Stream Edit Session update/delete events for the authenticated user.

**Headers:** `Authorization: Bearer <token>`, `Accept: text/event-stream`

**Response:** `text/event-stream`

```text
event: session_updated
data: {"type":"session_updated","sessionId":"session-123","source":"agent","toolCallId":"tool-call-1","toolName":"mcp__editor__write_segment","timestamp":"2026-06-14T00:00:00Z"}
```

**Event sources:**
- `api` - regular `/api/sessions` save/delete calls
- `agent` - successful Agent MCP editor write tool results

**Errors:**
- `401` - Missing or invalid token

---

### GET `/api/sessions/{session_id}`

Get a specific session including full editor_state.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "id": "session-123",
  "name": "My Session",
  "created_at": "2025-11-02 05:22:41",
  "updated_at": "2025-11-02 05:22:41",
  "editor_state": {
    "cells": [...],
    "commentors": []
  }
}
```

**Errors:**
- `404` - Session not found

---

### DELETE `/api/sessions/{session_id}`

Delete a session.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "success": true
}
```

---

## Claude Agent Chat Threads

### POST `/api/claude-agent`

Start or resume the current user's Claude Agent turn through the existing
`text/event-stream` contract. Before creating a Claude Code CLI process tree,
the backend enforces its configured active-turn cap and checks host/cgroup
memory headroom.

When capacity is unavailable the HTTP connection remains protocol-compatible:
it receives one `error` event followed by the existing `finish` event. New
fields are additive; clients that only read `errorText` remain compatible.

```text
data: {"type":"error","data":{"errorText":"[CLAUDE_AGENT_CAPACITY_EXHAUSTED] ...","errorCode":"CLAUDE_AGENT_CAPACITY_EXHAUSTED","retryable":true,"retryAfterSeconds":60}}
data: {"type":"finish","data":{"finishReason":"error"}}
```

Retryable resource codes:

- `CLAUDE_AGENT_CAPACITY_EXHAUSTED`: this backend already owns the configured
  number of active Agent turns; no second CLI process tree was created.
- `CLAUDE_AGENT_MEMORY_PRESSURE`: host `MemAvailable` or cgroup v2 headroom is
  below the configured run budget plus reserve; no CLI process was created.

### GET `/api/claude-agent/threads`

List Chat threads for the current user. Without search params, returns newest
threads first and supports `limit`/`offset` pagination for scroll-loaded
history panes. With `query`, searches thread titles and persisted conversation
text through the configured Chat history retriever. `deck_id` constrains either
path to conversations owned by the current actor and bound to that Deck; it is
the authoritative source for Settings / Work related-conversation previews.

**Headers:** `Authorization: Bearer <token>`

**Query params:**
- `deck_id` (optional) - return only owned conversations bound to this Deck
- `query` (optional) - fuzzy title/message query
- `search_scope` (optional, default `all`) - `all`, `title`, or `messages`
- `retrieval_mode` (optional, default `fuzzy`) - `fuzzy`, `auto`, or `vector`
- `vector_query` (optional) - JSON object string; reserved interface only
- `min_score` (optional) - fuzzy threshold, `0` to `1`
- `limit` (optional) - max result count
- `offset` (optional, default `0`) - default-list page offset; ignored by search retrieval

### GET `/api/claude-agent/threads/{thread_id}/messages`

Read an owned Thread's messages. With no query parameters, the legacy contract
returns the complete chronological history. Chat and Dream use stable keyset
pages by sending `limit`. A completed assistant row with projection v1 returns
only its final text part plus `projection_version: 1` and
`process_available`; user, partial, diagnostic, and unprojected legacy rows
retain their complete public `parts`. The canonical message is never truncated
or rewritten.

**Query params:**

- `limit` (optional, `1..100`) - enable newest-to-older keyset pagination; the response page is chronological
- `cursor` (optional) - opaque, versioned and Thread-bound boundary for the next older page
- `known_latest_message_id` (optional) - ID-only idle stabilization probe; mutually exclusive with `cursor`

Paged responses add `next_cursor`, `has_more`, `latest_message_id`, and
`unchanged`. An unchanged probe returns no messages and does not read
`parts`/`metadata`; a changed probe returns a replacement latest page. Invalid,
expired-version, or cross-Thread cursors return HTTP 400. Ownership remains 404.

### GET `/api/claude-agent/threads/{thread_id}/messages/{message_id}/process`

Read the complete canonical parts for one assistant message whose paged row
advertised `process_available: true`. The Thread is ownership-checked before the
exact `(thread_id, message_id)` assistant lookup. Unknown Threads/messages,
user messages, final-only messages, and unprojected rows all return the same
HTTP 404 response. This endpoint is intended for explicit process expansion;
it does not change SSE, turn, resume, cancel, or the legacy full-history API.

**Response:**
```json
{
  "threads": [
    {
      "id": "thread-123",
      "title": "论文初筛流程",
      "created_at": "2026-06-26 10:00:00",
      "updated_at": "2026-06-27 09:00:00",
      "match": {
        "strategy": "fuzzy",
        "retriever": "fuzzy",
        "score": 1,
        "fields": ["messages"],
        "excerpt": "之前讨论过向量库先不接入，只保留接口。"
      }
    }
  ],
  "retrieval": {
    "mode": "fuzzy",
    "query": "向量库 接口",
    "search_scope": "all",
    "min_score": 0.35,
    "limit": null,
    "vector": "interface_only",
    "retriever": "fuzzy"
  }
}
```

`retrieval_mode=vector` currently returns `ok=false`,
`error="vector_retrieval_unavailable"`, and does not access a vector database.

---

### GET `/api/claude-agent/threads/{thread_id}/subagents`

Return the current user's projected Claude Code subagent tasks for one Chat
thread. The server reads bounded transcript metadata from the server-owned
workspace. Projection v2 includes the assigned task, assistant Markdown,
credential-redacted tool summaries, lifecycle status, and final reply; thinking
blocks are excluded and oversized records are explicitly marked as truncated.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "thread_id": "thread-123",
  "exists": true,
  "tasks": [
    {
      "task_id": "a1b2c3",
      "agent_id": "a1b2c3",
      "agent_type": "quality-reviewer",
      "description": "Task3 quality review",
      "summary": "PASS. No new regressions.",
      "status": "completed",
      "tool_call_id": "toolu_123",
      "spawn_depth": 1,
      "started_at": "2026-08-04T09:00:00Z",
      "finished_at": "2026-08-04T09:00:10Z",
      "duration_ms": 10000,
      "error": null,
      "messages": [
        {"id": "message-1", "sequence": 1, "kind": "task", "text": "Review the change", "timestamp": null, "status": null, "tool_name": null, "tool_call_id": null, "input": null, "output": null, "redacted": false, "truncated": false},
        {"id": "message-2", "sequence": 2, "kind": "final", "text": "PASS. No new regressions.", "timestamp": "2026-08-04T09:00:10Z", "status": null, "tool_name": null, "tool_call_id": null, "input": null, "output": null, "redacted": false, "truncated": false},
        {"id": "message-3", "sequence": 3, "kind": "status", "text": null, "timestamp": "2026-08-04T09:00:10Z", "status": "completed", "tool_name": null, "tool_call_id": null, "input": null, "output": null, "redacted": false, "truncated": false}
      ],
      "message_count": 3,
      "messages_truncated": false,
      "projection_version": 2
    }
  ],
  "counts": {"running": 0, "completed": 1, "ended": 0, "total": 1},
  "updated_at": "2026-08-04T09:00:10Z"
}
```

`status` is one of `running`, `completed`, `failed`, or `cancelled`.
`messages[].kind` is one of `task`, `assistant`, `tool_call`, `tool_result`,
`status`, `final`, or `system`. Clients must use `sequence` then `timestamp` and
`id` for stable ordering. `summary` and `activity` remain available for legacy
clients; when v2 messages exist the final summary must not be rendered twice.
`ended` counts failed and cancelled tasks; it does not inflate the completed count.
The endpoint returns `404` when the thread does not belong to the current user.

---

## Pictures

### GET `/api/pictures`

Get recent daily pictures.

**Headers:** `Authorization: Bearer <token>`

**Query params:**
- `limit` (optional, default 30) - Max number of pictures

**Response:**
```json
{
  "pictures": [
    {
      "date": "2025-11-02",
      "image_base64": "iVBORw0KGgoAAAANSUhEUg...",
      "prompt": "A serene landscape...",
      "created_at": "2025-11-02 05:22:41"
    }
  ]
}
```

---

### GET `/api/pictures/range`

Get historical picture thumbnails within an optional date range.

**Headers:** `Authorization: Bearer <token>`

**Query params:** `start_date`, `end_date`, `limit`.

### GET `/api/pictures/{date}/full`

Get the historical full-resolution image for one `YYYY-MM-DD` date. Returns `404`
when that date has no retained picture.

---

## Preferences

### GET `/api/preferences`

Get user preferences.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "voice_configs": {
    "Logic": {
      "name": "Logic",
      "tagline": "...",
      "icon": "brain",
      "color": "blue",
      "enabled": true
    }
  },
  "meta_prompt": "Be helpful",
  "state_config": {
    "states": {
      "happy": {"name": "Happy", "prompt": "..."}
    }
  },
  "selected_state": "happy",
  "updated_at": "2025-11-02 05:22:41"
}
```

Returns empty object `{}` if no preferences set.

---

### POST `/api/preferences`

Save user preferences (partial updates supported).

**Headers:** `Authorization: Bearer <token>`

**Request (any combination of fields):**
```json
{
  "voice_configs": {...},
  "meta_prompt": "Be creative",
  "state_config": {...},
  "selected_state": "happy"
}
```

**Response:**
```json
{
  "success": true
}
```

---

## Analysis Reports

### GET `/api/reports`

Get recent analysis reports.

**Headers:** `Authorization: Bearer <token>`

**Query params:**
- `limit` (optional, default 10) - Max number of reports

**Response:**
```json
{
  "reports": [
    {
      "id": 1,
      "report_type": "echoes",
      "report_data": {
        "echoes": [...]
      },
      "created_at": "2025-11-02 05:22:41"
    }
  ]
}
```

---

### POST `/api/reports`

Save an analysis report.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "report_type": "echoes",
  "report_data": {
    "echoes": [
      {"title": "...", "description": "...", "examples": [...]}
    ]
  },
  "all_notes_text": "All the user's notes combined..."
}
```

**Response:**
```json
{
  "success": true
}
```

**Errors:**
- `400` - report_type or report_data missing

---

### GET `/api/default-voices`

Get default voice configurations (no auth required).

**Response:**
```json
{
  "Logic": {
    "tagline": "Wield raw intellectual power...",
    "icon": "brain",
    "color": "blue"
  },
  "Rhetoric": {...},
  ...
}
```

---

## Deck Endpoints

### GET `/api/decks`

Returns the authenticated user's Decks and Voices. The active product default is
the five-role screenplay-creation Deck. Untouched forks of the retired
introspection, scholar, and philosophy system defaults are omitted; user-created
Decks and retired forks with Deck- or Voice-level local changes remain visible.

### POST `/api/decks`

Creates a user Deck and binds the configured default Claude plugin in one
PostgreSQL transaction. The browser submits only Deck display fields; the server
resolves the exact configured package/version (default `drama-forge` `1.0.1`),
requires a ready installation, and verifies artifact digest and Claude CLI
compatibility before committing the Deck and plugin reference.

**Response:**
```json
{
  "deck_id": "c6654ae3-3de5-4ab9-b882-c9034a0d8fa6"
}
```

**Errors:**
- `409` - The configured default plugin is missing, not ready, digest-invalid,
  incompatible, or changes before the transaction commits. No Deck is created.

### POST `/api/decks/defaults/reconcile`

Idempotently ensures the actor owns the configured screenplay default Deck. If
it is missing, the route creates the complete five-role team and verified
`drama-forge` `1.0.1` reference in one transaction under the actor row lock. If
the Deck exists with no refs, only the verified ref is added. Any existing
plugin ref preserves the user's selection and prevents repair.

**Response:**
```json
{
  "deck_id": "c1b3ecf1-5fca-4a51-8806-202f19bef348",
  "reconciled": true,
  "reason": "missing_ref"
}
```

`reason` is one of `default_created`, `missing_ref`, or `refs_preserved`. During a
rolling restart, an older server may still return the legacy `default_not_found`
reason; clients should tolerate it and refresh after reconciliation.
Returns `409` when the configured installation cannot be verified; Deck and
existing refs remain unchanged.

### DELETE `/api/decks/{deck_id}`

Deletes an owned Deck in one PostgreSQL transaction. Mutable
`deck_claude_plugin_refs` and plugin bindings that were never captured by an
immutable runtime snapshot are removed before the Deck; owned Voices continue
to follow the database cascade contract. The route returns `404` for a missing
or non-owned Deck. Related Chat conversations return `409` with
`Deck cannot be deleted while related Chat conversations still exist.` so the
client can direct the user to the ordinary Chat deletion flow. Derived Decks or
immutable runtime snapshots also return `409` without changing the Deck or its
references. A plugin binding alone is version configuration, not proof of Chat
history, and no longer permanently blocks deletion.

### GET `/api/decks/{deck_id}/version-state`

Returns the owned Deck's aggregate `draft_revision`, latest immutable content
version, clean/dirty status, and next vN. Returns structured `503
DECK_VERSION_CAPABILITY_MISSING` until Admin Drizzle publishes
`dream.deck-content-versions.v1`; ordinary Deck editing remains available.

### POST `/api/decks/{deck_id}/versions/preview`

Accepts `expected_draft_revision` and `expected_base_version`. Revalidates
ownership/CAS, normalizes the complete Deck/Agent/plugin/binding snapshot, and
returns the target vN plus categorized changes. Preview never writes a version.

### POST `/api/decks/{deck_id}/versions`

Accepts the same expected values plus an optional 200-character description.
Locks the Deck, repeats validation/diff/hash, appends an immutable `deck_versions`
snapshot, and advances latest/published revision in one transaction. Stale facts
or no changes return `409`; failures preserve the draft and previous vN.

### GET `/api/decks/{deck_id}/versions`

Returns owner-scoped immutable Deck content versions newest-first. Runtime plugin
SemVer and binding revision are secondary snapshot/configuration facts and are
not substituted for content vN.

### GET `/api/voice-decks/{deck_id}/plugin-binding/history`

Returns owner-checked append-only runtime-configuration revisions newest first.
The optional `limit` query parameter defaults to `50` and is constrained to
`1..100`. This history describes exact Deck Plugin bindings only; it is not a
Deck content snapshot, draft, or publication history.

**Response:**

```json
{
  "deck_id": "c6654ae3-3de5-4ab9-b882-c9034a0d8fa6",
  "current_binding_revision": 2,
  "entries": [
    {
      "deck_plugin_binding_id": "dpb_33333333333333333333333333333333",
      "deck_plugin_id": "ink.deck.drama-forge",
      "deck_plugin_version": "1.1.0",
      "binding_revision": 2,
      "status": "active",
      "applied_to": "next_run",
      "created_at": "2026-08-16T10:10:00Z",
      "updated_at": "2026-08-16T10:10:00Z"
    }
  ]
}
```

`404` preserves the existing missing-or-not-owned boundary. Version changes
continue through `PUT /api/voice-decks/{deck_id}/plugin-binding` with an exact
SemVer, `expected_binding_revision`, and `apply_to: "next_run"`.

---

## Notion Resource Connector

所有 `/api/connectors*` 路由都要求正常 Dream 登录。连接、资源范围、轻量
索引与策略继续由现有 actor-scoped Notion facade 管理；以下三个 Settings 读取
路由只投影服务器发布包，不执行 `ntn`、Notion API、Runtime `Read` 或 MCP：

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/api/connectors/notion/capabilities` | 返回当前 actor 的 `notion-session` / `notion-cli` 安装包、真实 `apply_notion_page_read_redirect` / `materialize_workspace_snapshot` 阶段能力、聚合 package revision 和 Hosted MCP `not_integrated` 事实；没有连接时仍可审阅。 |
| `GET` | `/api/connectors/notion/skills/{skill_id}` | 从安装包返回解析掉 frontmatter 的 `SKILL.md` 标题/摘要/body，以及服务器 `references/*.md` 的 stable ID、相对路径、`text/markdown` MIME 和大小。 |
| `GET` | `/api/connectors/notion/skills/{skill_id}/files/{file_id}` | 按 stable file ID 返回一个服务器发布的 reference Markdown；可传 `package_revision`，陈旧 revision 返回 `409`。 |

Skill 文件读取不接受相对/绝对路径输入，拒绝未知 ID、越界、符号链接、不支持
MIME 和超限文件；公开响应不包含服务器路径、凭证或 Notion 正文。`write`
operation 仅表示把 connector-owned 轻量索引 materialize 到当前 thread workspace，
不写回远程 Notion。详情与文件响应使用对应 Skill 自己的 package revision；目录响应使用
两个包的聚合 revision。`notion-cli` 随内置 Skill 同步并可审阅，但 Dream 不把 actor-owned
`NOTION_HOME` 合并进 Agent/Bash 环境，因此 Settings 将其执行可用性标为 `unavailable`。
当前 Hosted Notion MCP OAuth/inventory/执行仍未接入，也没有工具执行端点。

---

## Claude MCP Resources

所有路由都要求正常 Dream 登录。PostgreSQL `dream_mcp_*` 是 Server 配置、
作用域、启用状态、credential ref 与 discovery snapshot 的唯一事实来源；
正常请求链不会执行 `claude --version`、`claude mcp help/list/get/login/logout`
或其他 MCP 管理 CLI。Token、Authorization Header、callback code/state 不会
出现在公开 DTO、普通配置字段或 access log；OAuth 文档只以 actor/server AAD
绑定的 AES-GCM envelope 保存。

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/api/claude-mcp/capability` | 返回精确 schema capability、支持的 transport 与 DB 管理模式；不探测 CLI。 |
| `GET` | `/api/claude-mcp/servers` | 只查询 actor/workspace 范围内的数据库 Server；不连接远端 MCP。 |
| `GET` | `/api/claude-mcp/servers/{identifier}` | 读取一个 actor-owned Server 的安全配置摘要；不自动 discovery。 |
| `POST` | `/api/claude-mcp/servers` | 新增经过 URL/transport/profile 策略校验的 Server；认证类型由后端 discovery 判断。 |
| `PATCH` | `/api/claude-mcp/servers/{identifier}` | 用 `expected_revision` CAS 修改配置；endpoint/transport 变化会清除旧 credential/snapshot。 |
| `DELETE` | `/api/claude-mcp/servers/{identifier}` | 用可选 `expected_revision` 删除 actor-owned Server。 |
| `POST` | `/api/claude-mcp/servers/{identifier}/discoveries` | 通过标准 Python MCP SDK 显式发现 tools/resources/prompts。 |
| `DELETE` | `/api/claude-mcp/servers/{identifier}/discoveries` | 取消该 Server 当前 actor-owned discovery。 |
| `POST` | `/api/claude-mcp/discoveries` | 在配置化并发上限内批量发现，单 Server 失败不阻塞其他结果。 |
| `POST` | `/api/claude-mcp/servers/{identifier}/auth-operations` | 启动/恢复进程内标准 SDK OAuth operation；前端只在后端判定 `needs_auth` 后展示。 |
| `GET` | `/api/claude-mcp/auth-operations/{operation_id}` | Poll an actor-owned in-process OAuth operation. |
| `POST` | `/api/claude-mcp/auth-operations/{operation_id}/redirect` | 同源 SPA 自动提交完整 callback URL 给该 operation；不需要用户复制。 |
| `POST` | `/api/claude-mcp/auth-operations/{operation_id}/cancel` | 取消并关闭该 SDK session/transport。 |
| `DELETE` | `/api/claude-mcp/servers/{identifier}/credential` | 删除 encrypted credential 并精准失效相关 snapshot。 |

Chat 的 new/resume 每一轮从同一数据库事实源生成 detached `mcp_servers`
snapshot，通过公开 Agent SDK `Path` 接口和 `strict_mcp_config=true` 注入；
不会自动批准工具。Dream 不创建 migration/runtime DDL，缺少 Admin 发布的
`dream.managed-mcp-resources.v1` capability 时 fail closed。

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message"
}
```

Common status codes:
- `400` - Bad request (missing/invalid params)
- `401` - Unauthorized (missing/invalid token)
- `404` - Not found
- `500` - Internal server error

---

## Development

**Start server:**
```bash
cd backend
source .venv/bin/activate
python server.py
```

**Run tests:**
```bash
python test_migration.py           # Test migration logic
python test_real_migration.py      # Test with real data
```

**API Docs:**
- Interactive docs: http://localhost:8765/docs

---

## Database

SQLite database at `backend/data/ink-and-memory.db`

**Initialize/reset:**
```python
from database import init_db
init_db()
```

**Tables:**
- `users` - User accounts
- `user_sessions` - Editor sessions
- `daily_pictures` - Historical timeline images retained for read-only viewing
- `user_preferences` - User settings
- `analysis_reports` - Analysis results
- `auth_sessions` - Session tokens (optional)
- `schema_version` - Migration tracking
