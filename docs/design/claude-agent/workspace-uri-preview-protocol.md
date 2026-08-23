> [Input] Claude Agent context assembly, Chat SSE/history hydration, shared ChatMarkdown rendering, Workspace file router/core, and authenticated Thread ownership records.
> [Output] Define the evidence-backed `workspace://` Markdown reference protocol, its minimal implementation boundary, security policy, interaction states, sequence, tests, and rollback.
> [Pos] workspace URI preview protocol design in `docs/design/claude-agent`
> [Sync] 2026-08-22: initial protocol and implementation decision for Thread-owned `files/` image previews and file downloads in Chat Markdown.
> [Sync] 2026-08-22: align Workspace image thumbnails and full-size modal behavior with the v2.1 light-paper visual contract.
> [Sync] 2026-08-23: fix Chat long-image export by resolving protected Workspace images through the same Thread-bound access path before capture.
> [Sync] 2026-08-23: replace divergent image card/modal chrome with Mermaid's exact inline frame and the shared reference-style immersive viewer.
> [Sync] 2026-08-23: add shared wheel-up/down zoom over the immersive media stage with scroll suppression and existing clamp reuse.
> [Sync] 2026-08-23: correct zoom ownership so only image/diagram content scales while the fitted Paper sheet remains geometrically stable.

# `workspace://` Workspace File Preview Protocol

## 1. Background and problem

Claude Agent can create an image under the current Thread workspace, for example
`files/fashion_flux2.png`, but a reply such as
`![fashion_flux2](files/fashion_flux2.png)` is only an ordinary relative browser URL.
The browser resolves it against the page URL, not against the server-owned Thread
workspace. The Chat Markdown chain therefore has no authenticated or Thread-bound way
to preview the generated file.

The root cause is a missing cross-layer contract, not a missing file system:

- the Agent is not told how to refer to a file for Chat rendering;
- the shared Markdown renderer does not recognize a Workspace URI;
- the existing Workspace download route is a management/download route, not a safe
  Markdown content boundary: it authenticates a bearer token but does not bind
  `sessionId` to `chat_thread.user_id`, and it creates a missing workspace while reading;
- the Chat message already carries the Thread identity needed to resolve the reference,
  but that identity is not passed into Markdown file rendering.

## 2. Evidence table

| Finding | Status | Evidence | Consequence |
|---|---|---|---|
| System prompt assembly has one owner. | Confirmed | `backend/claude_agent/service.py::assemble_context` calls `ClaudeAgentContextBuilder.build_system_prompt`; `backend/claude_agent/context_builder.py::_SYSTEM_PROMPT_TEMPLATE` is the engine template. | Add the Agent-facing contract there; do not create a second prompt entry. |
| Workspace Mode binds the product workspace to the Thread. | Confirmed | `service.py::assemble_context` resolves `get_or_create_workspace(state.session_id)` only when `workspace_enabled=true`, passes the resulting `cwd`, and clears it when disabled. | A URI is meaningful only when `<workspace_context>` exists. |
| `AGENT_CWD` is the root and each Thread uses `{AGENT_CWD}/{thread_id}`. | Confirmed | `backend/libs/claude_agent_kit/server/workspace.py::get_or_create_workspace` and `get_or_create_thread_runtime_workspace`. | The URI path is relative to the current Thread workspace, never to `AGENT_CWD` itself. |
| Agent-produced/user-uploaded public files have an existing `files/` namespace. | Confirmed | `WORKSPACE_SUBDIRS`, `workspace_file_sync.py`, `FileSidebar.tsx`, and the Workspace context template. | Protocol v1 exposes only `files/<path>`; internal `.claude*`, `.notion`, logs, skills, memory, and Dream control files are not addressable. |
| Chat uses one shared Markdown rendering seam. | Confirmed | `ChatMessageList` routes assistant/user text through `AssistMessagePart` / `UserMessagePart`; both use `ChatMarkdown`, which owns `ReactMarkdown + remark-gfm`. | Extend `ChatMarkdown`; do not add a parallel renderer. |
| The actual Markdown library is ReactMarkdown 10.1.0. | Confirmed | `frontend/package.json` and `ChatMarkdown.tsx`. ReactMarkdown's default URL transform removes unknown schemes. | Preserve only validated `workspace://` candidates before component routing; delegate every other URL to `defaultUrlTransform`. |
| SSE preserves model Markdown text. | Confirmed | `claude-agent-transport.ts` maps `text-delta` to AI SDK text chunks; `service.py` persists normalized text parts. | No SSE event or DB schema change is required. |
| History recovery still knows the Thread. | Confirmed | `hydrateClaudeThreadSession(threadId)` reloads persisted parts; `ChatPanel` passes the same `threadId` into `ChatMessageList`. | Historical messages can resolve the same URI after refresh without persisting credentials or disk paths. |
| Existing Workspace file core has resolve-based containment. | Confirmed | `workspace.py::_resolve_workspace_safe_path` and `read_workspace_file_content`. | Reuse the core, adding a strict no-symlink read option for untrusted Markdown content. |
| Existing `/api/workspace/files/download` proves Thread ownership. | Excluded | `backend/routers/workspace.py::download_workspace_file` validates JWT and `sessionId` syntax only. | Do not map untrusted Markdown directly to this route. |
| Existing download is read-only with respect to workspace lifecycle. | Excluded | It calls `_get_or_create_workspace_for_user`. | Add a narrow content read that never creates/repairs a workspace. |
| Browser `<img>` can use the bearer-protected endpoint directly. | Excluded | `<img>` cannot attach the existing Authorization header; query-token URLs would expose credentials in DOM/logs/history. | Fetch with bearer, validate MIME, then render an ephemeral blob URL. |
| A database or new file service is needed. | Excluded | Thread ownership and file content primitives already exist. | No schema, migration, runtime DDL, alternate storage service, or alternate Markdown renderer. |
| Exported long-chat images can preserve unknown Workspace URLs unchanged. | Excluded after reproduction | The export-only `ThreadImageCard` used ReactMarkdown's default transform, producing `src=""`; `html-to-image` then rejected the empty image node with an Event error. | Preserve only the exact scheme in the export renderer, authenticate and embed supported bytes before capture, and render failures as inert text. |

## 3. Goals and non-goals

### Goals

- Let Agent replies render generated PNG/JPEG/GIF/WebP files from the current
  authenticated Thread workspace.
- Let an explicit Markdown link download any regular file under the same public
  `files/` namespace.
- Preserve Markdown, SSE, history, Workspace sidebar, sandbox, and SDK behavior.
- Fail closed before file access for malformed, disabled, missing, foreign, traversing,
  repeatedly encoded, absolute, backslash, or symlink paths.
- Keep bearer tokens and real disk paths out of persisted Markdown.
- Let the existing Chat long-image exporter include supported Workspace images without
  exposing credentials or making one unavailable asset fail the whole export.

### Non-goals

- Interpreting ordinary relative Markdown URLs as Workspace files.
- Exposing directories, directory ZIPs, `.claude*`, `.notion`, `logs/`, `skills/`,
  `memory/`, `.dream/`, `assets/`, or `stories/` through this protocol.
- Inline preview of SVG, HTML, PDF, video, audio, or text in v1.
- Changing upload, list, move, delete, or existing manual download behavior.
- Adding a database capability, signed URL store, service worker, or long-lived blob URL.

## 4. Protocol contract

### 4.1 Canonical syntax

```text
workspace://files/<segment>[/<segment>...]
```

Example:

```markdown
![Flux.2 Dev](workspace://files/fashion_flux2.png)
[Download notes](workspace://files/%E5%88%86%E9%95%9C%20notes.md)
```

`workspace://` is an application-owned opaque prefix. The text after the prefix is
treated as a Thread-workspace-relative path; `files` is the public mount name, not a
DNS host. The canonical scheme is lowercase and exact.

### 4.2 Identity binding

The resolver receives the `threadId` from the rendered message surface. It never takes
a user ID, Thread ID, workspace root, bearer token, or disk path from Markdown.

The backend binds the request in this order:

1. verify the bearer token;
2. validate the `sessionId` syntax;
3. load `chat_thread(sessionId, authenticated_user_id)`; use one public 404 for an
   absent or foreign Thread;
4. require `system_config.workspace_enabled=true`;
5. resolve an already existing non-symlink Thread workspace under `AGENT_CWD`;
6. validate and read only the requested regular file under `files/`.

This binding is reproducible after refresh because persisted Markdown stores only the
opaque URI while the recovered Chat surface supplies its authenticated `threadId` again.

### 4.3 Decode and normalization order

The Markdown parser may provide raw Unicode or percent-encoded UTF-8. The frontend:

1. checks the exact lowercase `workspace://` prefix;
2. rejects an empty suffix, a leading slash, query, or fragment;
3. rejects percent-encoded `/` or `\\` before decoding;
4. calls `decodeURIComponent` exactly once;
5. rejects a remaining `%HH` triplet as repeated encoding;
6. rejects control characters, `\\`, `?`, `#`, an absolute path, a Windows drive
   prefix, empty segments, `.` segments, and `..` segments;
7. requires at least one child under the first segment `files`;
8. preserves decoded Unicode and spaces exactly and joins segments with `/`.

The backend receives the transport-decoded query value and repeats the structural
validation without decoding it again. Both layers are required: frontend validation
prevents accidental network access; backend validation is the trust boundary.

### 4.4 Encoding policy

- Raw Unicode is accepted.
- UTF-8 percent encoding is accepted and decoded once.
- Spaces are accepted; percent-encoding as `%20` is the canonical Markdown form when
  a Markdown destination would otherwise require angle brackets.
- Query parameters and fragments are not part of v1 and are rejected, including their
  encoded forms.
- Literal percent characters must be encoded as `%25`; a decoded `%HH` sequence is
  rejected to make repeated encoding unambiguous.
- Duplicate slashes are rejected rather than normalized.
- Unicode normalization forms are not rewritten; file names remain byte/name exact.

### 4.5 File types

| Markdown form | v1 behavior |
|---|---|
| `![alt](workspace://files/x.png)` | Fetch with bearer; require response MIME in `image/png`, `image/jpeg`, `image/gif`, `image/webp`; render bounded image content inside Mermaid's exact media frame and open the shared immersive zoom/download viewer from one ephemeral blob URL. |
| `[label](workspace://files/x.ext)` | Fetch only after user activation and download the regular-file blob using the final path segment. |
| Workspace image URI with unsupported extension/MIME | Do not render inline; show a stable unsupported-type fallback and a safe download action. |
| Directory | Reject; the content endpoint is regular-file only and uses descriptor-backed `O_NOFOLLOW` reads. |

SVG is deliberately not inline-previewed in v1. This avoids active-content and external
resource ambiguity while preserving a download path.

## 5. Candidate solutions and decision

| Candidate | Result | Reason |
|---|---|---|
| Rewrite every relative Markdown URL to the Thread workspace. | Rejected | Ambiguous and breaks ordinary Markdown/link compatibility. |
| Convert URI to `/api/workspace/files/download?...&token=...` in `src`/`href`. | Rejected | Persists/exposes credentials and maps model content to a route without Thread ownership. |
| Add a second file proxy/storage service. | Rejected | Duplicates existing Workspace primitives and expands architecture. |
| Use a remark AST plugin plus a new renderer. | Rejected | `ChatMarkdown` already has the exact component seam; an AST plugin adds no security value. |
| Extend `ChatMarkdown` URL/component overrides and add one narrow route to the existing Workspace Router. | Selected | Smallest boundary that preserves all non-Workspace URLs, keeps auth in fetch headers, reuses existing Thread/file primitives, and fails closed without workspace creation. |

The route is a backend supplement, not a second service:

```text
GET /api/workspace/files/content?sessionId=<owned-thread>&path=<validated-files-path>
Authorization: Bearer <token>
```

## 6. Agent context initialization contract

The engine system template contains one short normative section:

- use `workspace://files/...` when a `<workspace_context>` is present and the reply
  references a generated or existing Workspace file;
- the suffix is relative to the current Thread workspace root;
- do not emit local absolute paths, `file://`, container paths, or plain relative paths
  for files the user must open from Chat;
- do not emit `workspace://` when no `<workspace_context>` exists.

This is assembled through the existing `ClaudeAgentContextBuilder`; it does not add a
client system-prompt field or a second initialization lifecycle.

## 7. Frontend design

`ChatMarkdown` remains the only live Chat Markdown renderer.

- Its `urlTransform` returns exact `workspace://` candidates unchanged so ReactMarkdown
  can route them, while delegating every other URL to ReactMarkdown's secure
  `defaultUrlTransform`.
- Its `img` and `a` component overrides intercept only the exact scheme.
- A pure parser returns either a canonical `files/...` path or a reasoned invalid state.
- Workspace fetches use the current `threadId`, `apiUrl`, and bearer token. Markdown
  contains none of those values.
- Images use abortable fetch, MIME allowlisting, `URL.createObjectURL`, and cleanup.
- Successful Workspace images render as responsive 4:3 `object-fit: contain` content in
  Mermaid's exact shared media frame; the toolbar and image both expose the same blob in
  the shared `Modal media-preview` viewer.
- File links fetch only on click, create a temporary blob URL, trigger download, and
  revoke the URL.
- Normal HTTP(S), `data`, `blob`, anchors, relative links, code, GFM, and Mermaid keep
  their current ReactMarkdown behavior.

`ChatMessageList` passes its existing `threadId` to assistant and user Markdown. Other
Chat-owned surfaces may use the active Thread fallback, but persisted message rendering
does not depend on it.

### 7.1 Image interaction and visual contract

The source is [Ink & Memory UI Design v2.1](<../../prd/Ink & Memory UI Design v2.pdf>)
plus the approved existing `MermaidBlock` Chat UI and supplied immersive-viewer reference.
There is one media chrome contract:

- the outer frame, header height, solid Border Paper boundary, radius, label typography,
  action dimensions, hover and focus states are the exact shared `MarkdownMedia.css`
  classes used by Mermaid; no Workspace-specific approximation is allowed;
- image content remains bounded to `420×315px` with 4:3 `object-fit: contain`, centered
  inside the shared frame so generated assets do not dominate the conversation;
- the header shows the accessible file label plus enlarge and download actions; the
  image itself remains an accessible enlarge trigger;
- below `640px`, the thumbnail uses the message column width and never creates page
  horizontal overflow;
- the shared portal-backed media viewer follows the supplied skeleton: full-viewport
  black overlay, large centered Paper canvas, round download/close controls at top right,
  and a bottom-centered `− / percentage / +` zoom control;
- previews open at 100%, zoom from 50% to 200% in 10% steps through either bottom
  buttons or wheel-up/down over the media stage, preserve original ratio, suppress
  background scrolling, close by close button/backdrop/Escape, contain focus, and
  restore focus to the opener.
- 100% is the media's fitted viewport baseline; percentage changes apply only to the
  actual image or Mermaid diagram, never to the Paper sheet, toolbar, or modal surface;
  a separate invisible layout sizer may reserve overflow space but must not scale visually.

This styling is scoped to `WorkspaceImage`. Ordinary HTTP(S), `data`, `blob`, and
relative Markdown images retain `.prose img` behavior.

### 7.2 Long-image export

`ThreadImageCard` is the existing export-only projection and remains the sole input to
`html-to-image`. It must not render a raw or empty `workspace://` image source:

1. its ReactMarkdown URL transform preserves only the explicit `workspace://` prefix;
2. the first off-screen render emits inert markers instead of `<img src="">`;
3. `renderThreadImage` collects those exact marker URIs and uses the shared
   `workspaceFileAccess` helper with the current Thread ID and bearer header;
4. the same MIME allowlist used by live Chat accepts PNG/JPEG/GIF/WebP;
5. accepted blobs become transient `data:` URLs inside the off-screen export tree so
   SVG/canvas capture is self-contained and cannot be cross-origin tainted;
6. missing, disabled, foreign, invalid, unsupported, or corrupt/undecodable files remain
   a localized inert placeholder, allowing the rest of the conversation to export;
7. the export host and embedded data are removed after capture. No credential, endpoint,
   blob/data URL, or file bytes are written back to Markdown, history, or the database.

This is not a second exporter or file service: it is input resolution immediately before
the existing tiled `ThreadImageCard → html-to-image → PNG` pipeline.

## 8. Interaction states

| State | Image UI | File-link UI | Network behavior |
|---|---|---|---|
| Loading | Accessible loading text, then image | Label remains; loading state after click | One abortable authenticated request |
| Success | Bounded blob thumbnail with model alt; activate for original-ratio modal | Browser download starts | One blob URL shared by thumbnail/modal; revoked on cleanup / after click |
| File missing or inaccessible | “File not found or unavailable” | Same status after click | 404; does not distinguish foreign Thread existence |
| No permission/token | “You do not have access” | Same status after click | No token means no request; 401/403 map to access error |
| Invalid URI/path | “Invalid Workspace file reference” | Inert text with invalid state | No request |
| Workspace disabled | “Workspace is disabled” | Inert text | No file request |
| Unsupported image type | Unsupported preview + safe download action | Normal safe download | Image is not fetched merely for preview |
| Retryable server/network failure | Error + Retry button | Error; activate again to retry | 5xx/network only |

## 9. Workspace access and security

- The content endpoint performs no workspace initialization, repair, upload, move,
  delete, directory archive, or mutation.
- Thread ownership is checked before any workspace root or path probe.
- The public namespace is exactly `files/`.
- Absolute paths, Windows paths, backslashes, empty/dot/dot-dot segments, encoded
  traversal, repeated encoding, query, fragment, directories, and any symlink component
  are rejected.
- The response returns bytes, MIME, length, `private, no-store`, and `nosniff`; it never
  returns `AGENT_CWD`, the resolved workspace, or another server path.
- Unknown/foreign Thread and missing workspace use a non-enumerating 404 boundary.
- MIME allowlisting is repeated by the frontend before rendering a blob as an image.
- Authentication stays in the request header and is never persisted in a message URL.

## 10. Business sequence

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend Chat
    participant MR as Markdown Renderer
    participant EX as Long-image Export
    participant WP as Workspace URI Plugin
    participant API as Dream API
    participant CB as Claude Agent Context Builder
    participant SDK as Claude Agent SDK
    participant WS as Workspace Service
    participant FS as File Storage

    API->>CB: assemble_context(owned thread, Workspace Mode)
    CB-->>SDK: system prompt + workspace:// contract
    User->>FE: Ask Agent to generate an image
    FE->>API: POST /api/claude-agent (owned thread)
    API->>SDK: Run in current Thread workspace
    SDK->>FS: Write files/fashion_flux2.png
    SDK-->>API: Markdown with workspace://files/fashion_flux2.png
    API-->>FE: SSE text-* frames
    FE->>MR: Render message text with threadId
    MR->>WP: Parse explicit workspace:// URI
    WP->>API: GET /api/workspace/files/content + bearer + threadId + path
    API->>API: Verify user, Thread ownership, Workspace Mode, path
    API->>WS: Resolve existing Thread workspace without creation
    WS->>FS: Reject symlinks; read regular files/ file
    FS-->>WS: Bytes + metadata
    WS-->>API: Safe file content
    API-->>WP: private/no-store + nosniff response
    WP-->>MR: MIME-checked ephemeral blob URL
    MR-->>User: Render bounded image thumbnail
    User->>WP: Activate “view full size”
    WP-->>User: Open accessible original-ratio modal from same blob

    User->>FE: Export conversation image
    FE->>EX: Render persisted Markdown with current threadId
    EX->>WP: Collect explicit workspace:// image markers
    WP->>API: GET the same owner-bound content + bearer
    API-->>WP: MIME-checked image bytes
    WP-->>EX: Transient in-memory data URL
    EX-->>User: Preview and download existing tiled PNG export

    alt Missing, foreign, invalid, disabled, or unsupported
        API-->>WP: 400 / 404 / 409, or WP rejects before request
        WP-->>User: Stable inert/download/retry fallback
    end

    User->>FE: Refresh or reopen history
    FE->>API: GET owned Thread messages/status
    API-->>FE: Persisted Markdown parts
    FE->>MR: Render same Markdown with recovered threadId
    MR->>WP: Resolve URI again through the same authenticated flow
    WP-->>User: Render historical image
```

## 11. Backward compatibility

- No SSE event, UIMessage part, persisted Markdown, DB schema, Agent SDK, workspace
  initialization, sandbox, sync, or session-resume format changes.
- Old messages with ordinary relative paths stay ordinary relative paths.
- HTTP(S), anchors, `data`, `blob`, and normal Markdown links remain delegated to
  ReactMarkdown's existing URL policy.
- Existing Workspace list/upload/download/delete/move routes and FileSidebar behavior
  are unchanged by the narrow content endpoint.

## 12. Logging and observability

v1 relies on existing HTTP access logs for status-level observability. Application logs
are emitted only for internal ownership/config lookup failures and never include the
requested file path. Bearer tokens, bytes, resolved disk paths, environment variables,
and model message bodies are never logged. Browser failures remain local accessible
state, not telemetry in v1.

Metrics for URI use/failure rates are deferred until a repository-owned metrics sink is
identified; adding an ad hoc collector would violate the minimal design.

## 13. Test plan

Backend route/core tests:

- owned Thread success with ASCII, spaces, Unicode, and percent-encoded transport;
- missing file/workspace, foreign Thread, Workspace Mode disabled;
- `../`, encoded traversal after transport decode, repeated encoding, absolute path,
  Windows drive/backslash, query/fragment, wrong public namespace, and directory;
- an in-workspace symlink and an escaping symlink are both rejected;
- response has no disk path and uses private/no-store + nosniff.

Frontend parser/component tests:

- canonical image, raw Unicode/space, encoded Unicode/space;
- malformed encoding, encoded separator, repeated encoding, traversal, absolute,
  backslash, query, fragment, and unsupported namespace/type;
- bearer header and current `threadId` are used only in the runtime request;
- loading/success/missing/disabled/retry/unsupported fallbacks;
- wide-screen thumbnail stays within `420×320px`, opens a materially larger
  original-ratio dialog, closes on Escape, and restores trigger focus;
- Mermaid and Workspace use the same computed outer-frame style; Mermaid enlarge is
  immediately after copy, and both dialogs expose the same download/close/zoom skeleton;
- wheel up/down changes the shared percentage in 10% steps, clamps at 50%/200%, and its
  cancelable event is default-prevented without moving the background page;
- real bounding boxes at 50%/100%/110%/200% prove the Paper sheet width/height stays
  stable while the Workspace image and Mermaid diagram follow the requested scale;
- `360px` dark/Chinese viewport has no horizontal overflow; the media dialog fills the
  viewport and keeps every control visible;
- three valid Workspace images plus missing/corrupt images produce one
  previewable/downloadable PNG through the production tiled exporter; requests keep the
  current Thread and bearer;
- normal HTTP(S) image/link behavior remains unchanged;
- remount/history rendering resolves the same URI again.

Repository validation:

- focused backend tests;
- focused Playwright component/browser test;
- frontend lint, typecheck/build;
- Markdown reference inventory;
- `git diff --check` and final status.

Real-model image generation is optional and must use the separately authorized local
real-business protocol. This implementation can be accepted technically without making
real-model or real-data claims.

## 14. Design self-review

| Check | Result |
|---|---|
| Directly fixes generated images not previewing | Pass: Agent emits a stable URI and Chat renders it. |
| Preserves existing Markdown | Pass: only exact `workspace://` is intercepted. |
| Matches approved Mermaid/reference interaction | Pass: exact shared inline frame plus one full-screen download/close/zoom viewer; image content stays within 420×315px. |
| Reuses existing Workspace access | Pass: same router, auth, workspace root, and file content primitives. |
| Adds a second service/renderer | No. |
| Leaks real paths or credentials | No: opaque persisted URI + authenticated runtime fetch + blob. |
| Can bypass Thread/user isolation | No: owned `chat_thread` is required before file probes. |
| Rejects traversal/repeated encoding/symlinks | Pass by dual-layer validation and strict file read. |
| Changes database | No. |
| Adds speculative abstractions | No: one parser, one rendering component, one narrow route. |
| Independently rollbackable | Yes: remove prompt block, Markdown overrides, component/parser, and content route. |
| Minimal for current requirement | Yes: live images, ordinary downloads, and compatibility with the existing long-image exporter; other media/metrics remain deferred. |

## 15. Rollback

Rollback is file-local and does not require data migration:

1. remove the Agent prompt protocol section;
2. restore `ChatMarkdown` to the existing GFM/Mermaid component map;
3. remove the Workspace URI parser/reference component and focused tests;
4. remove `GET /api/workspace/files/content` and its strict read helpers;
5. retain stored messages unchanged—unknown `workspace://` URLs fall back to inert/alt
   behavior under ReactMarkdown's default URL transform.

## 16. Acceptance criteria

- The Agent context contains the canonical rule and example only through the existing
  context builder.
- `workspace://files/fashion_flux2.png` renders in live and recovered Chat messages.
- Three supported images in one message render independently.
- Each Workspace image is bounded inside Mermaid's exact responsive media frame and opens
  the same accessible full-screen download/close/zoom preview; wide and `360px` layouts
  remain viewport-contained.
- Chat long-image export embeds supported Workspace images through the same authenticated
  Thread endpoint, previews and downloads successfully, and degrades unavailable images
  to inert text without failing the entire export.
- Only the authenticated owner of the current Thread can read its existing `files/`.
- Invalid, foreign, missing, disabled, directory, and symlink references reveal no bytes
  or disk paths and have stable UI fallbacks.
- Existing SSE, Chat history, Workspace sidebar, HTTP(S) Markdown, ordinary links, GFM,
  Mermaid, sandbox, and session resume contracts remain unchanged.
