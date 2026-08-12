# Dream Agent interaction design

> Status: **current interaction seams implemented and locally accepted**. R41
> passed S01–S10 sequentially in headless and visible headed Chromium with
> semantic waits and one worker; S11–S14 remain covered by backend/source
> acceptance. This is not staging, canary, immutable rollback or production-load
> evidence.

This document is the canonical **Agent runtime interaction** view. The complete
Dream product/workflow/file/Episode business view is intentionally separated
into [Business interaction design](./business-interaction-design.md), where
every B01–B21 business capability has its own sequence diagram. Neither document
may use the other plane's state as truth.

## Interaction contract

Dream and Chat are two views of the same owned Chat thread. Switching surfaces
must not create a second thread, second stream, copied history or translated
message schema.

The Dream surface keeps Dream-specific layout, workflow actions, unread markers,
focus behavior and business projection. It directly composes the existing
`ChatPanel`; `ChatPanel` remains the sole `useChat` and live reducer owner.

| Data/operation | Identifier sent by Dream browser | Boundary |
|---|---|---|
| History/status/stream/send/confirm/stop | `threadId` only | Canonical Chat routes |
| Run/files/review/episode actions | `workflowRunId` | Actor-scoped Story Workspace REST |
| Trusted Dream context | None | Server reverse-lookup by authenticated actor + owned thread |

During `ClaudeAgentService.assemble_context`, zero authorized Dream attempts
means generic Chat. One valid retry chain means the server selects its single
unsuperseded leaf and derives internal Dream context. Multiple independent
leaves, a broken/cyclic retry chain or frozen-source mismatch means `409` plus a
data-integrity alert. The browser and Chat request never select a run.

## ChatPanel-first composition and hydration

`ChatView` and the Dream wrapper share
`frontend/src/components/chat/threadSessionHydration.ts` for history → status
ordering, terminal-history stabilization, visibility filtering and
pending/settled tool IDs. `chatRuntimeState.ts` carries small main-turn
Stop/reconnect helpers. Generation protection, reconnect nonce and post-EOF
recovery remain in the two shells and `ChatPanel`; neither helper owns `useChat`,
live messages, send/confirm/stop or event parsing.

The current `ChatPanel` owns:

- ordered persisted and transient `UIMessage` parts;
- AI SDK live status plus authoritative runtime/reconnect/Stop state;
- active/pending tool confirmations for the owned thread; the server supplies
  the active `turnId` authority;
- reconnect/stop/error state;
- send, confirm, stop, refresh and mark-read commands;
- authoritative post-terminal history recovery.

Dream mounts the same `ChatPanel`, canonical transport/parser/reducer, composer,
confirmation dock and Stop behavior as Chat. This migration must not introduce
an app-wide `ClaudeThreadSessionProvider`, a second `useChat` wrapper or a copied
Dream controller.

Dream-specific `settledRevision` is gone. The current Dream/Execution pages use
`StoryWorkspaceDreamThreadChat.onSettled` to refresh their authoritative
business/file projections, and workflow polling remains the fallback. The
Observer's default latest-hint sink has no push/UI invalidation or durable owner
wiring. The already-authorized Dream-files response may attach a matching safe
`agentActivity` for informational copy only; it is absent when no hint exists
and never controls lifecycle, confirmation, input or Stop. The page view-model
renders only content-generation/workflow-operation activity and reconcile copy;
turn-terminal, waiting-confirmation, subagent and generic-tool hints render only
through canonical `ChatPanel` when applicable.

Current reusable seams are `frontend/src/lib/claude-agent-transport.ts`,
`frontend/src/lib/claude-agent-sse-utils.ts`,
`frontend/src/components/chat/threadSessionHydration.ts`,
`frontend/src/components/chat/chatRuntimeState.ts`, `ChatPanel.tsx`, and
`StoryWorkspaceDreamThreadChat.tsx`.

## Scenario 1 — Dream sends a normal message and receives incremental output

```mermaid
sequenceDiagram
    actor User
    participant Dream as "Dream page"
    participant Ctrl as "ChatPanel (sole live reducer)"
    participant ChatAPI as "POST /api/claude-agent"
    participant Resolver as "Dream binding reverse-lookup"
    participant Runtime as "ClaudeAgent runtime"
    participant Bus as "Normalized EventBus"

    User->>Dream: Send text
    Dream->>Ctrl: send(threadId, message)
    Ctrl->>ChatAPI: Owned threadId plus Chat message
    ChatAPI->>Resolver: Lookup by authenticated actor + owned thread
    Resolver->>Resolver: Validate retry graph and select one leaf attempt
    Resolver-->>ChatAPI: Trusted Dream context for the leaf
    ChatAPI->>Runtime: Start turn with server-authored context
    Runtime->>Bus: text-start / text-delta...
    Bus-->>ChatAPI: ChatStreamAdapter frames
    ChatAPI-->>Ctrl: Canonical Chat SSE increments
    Ctrl-->>Dream: Render canonical UIMessage reducer state
    Runtime->>Bus: message-final, finish(stop), sentinel
    Ctrl->>ChatAPI: Reload history/status after EOF
    ChatAPI-->>Ctrl: Persisted authoritative turn
```

Dream must not call `/dream-agent/messages` or `/dream-agent/events`. The
deleted baseline calls are recoverable at `git show
a506c83:frontend/src/hooks/story-workspace/useStoryWorkspaceDreamAgent.ts`
(former lines 220-417).

## Scenario 2 — Switch Dream → Chat and continue the same thread

```mermaid
sequenceDiagram
    actor User
    participant Dream as "Dream page"
    participant CtrlD as "Dream-mounted ChatPanel"
    participant Runtime as "Server thread runtime"
    participant Chat as "Chat page"
    participant CtrlC as "Chat-mounted ChatPanel"
    participant API as "Chat thread API"

    User->>Dream: Navigate to Chat
    Dream->>CtrlD: Unmount/abort browser reader
    Note over CtrlD,Runtime: Abort disconnects this reader, it does not call Stop
    User->>Chat: Open identical threadId
    Chat->>CtrlC: mount(threadId)
    CtrlC->>API: GET messages
    CtrlC->>API: GET status
    alt Turn still running
        CtrlC->>API: GET threads/{threadId}/stream
        API-->>CtrlC: Replay buffer then live events
    else Turn settled
        API-->>CtrlC: Persisted history is final
    end
    CtrlC-->>Chat: Continue/render same conversation
```

No Dream-to-Chat message export or ID translation is allowed.

## Scenario 3 — Switch Chat → Dream and restore the same thread

```mermaid
sequenceDiagram
    actor User
    participant Chat as "Chat page"
    participant CtrlC as "Chat-mounted ChatPanel"
    participant Dream as "Dream page"
    participant Biz as "Story Workspace REST"
    participant CtrlD as "Dream-mounted ChatPanel"
    participant API as "Chat thread API"

    User->>Chat: Navigate to Dream run
    Chat->>CtrlC: Unmount/abort reader only
    Dream->>Biz: GET /workflow-runs/{workflowRunId}/dream-files
    Biz-->>Dream: Existing authorized response with threadId and files
    Dream->>CtrlD: mount(threadId)
    CtrlD->>API: GET messages then GET status
    alt Running
        CtrlD->>API: GET thread stream
        API-->>CtrlD: Replay plus live Chat events
    else Settled
        API-->>CtrlD: Final history/status
    end
    Biz-->>Dream: Run/files/review projection remains separate
```

`workflowRunId` is used only for the existing Dream-files business REST call;
the hydration primitive and `ChatPanel` receive only `threadId`. No re-entry API
or binding identifier is added by this migration. Optional `agentActivity` is
display-only and is not passed to `ChatPanel`.

## Scenario 4 — Tool approval, rejection and AskUserQuestion

```mermaid
sequenceDiagram
    actor User
    participant UI as "Dream or Chat confirmation UI"
    participant Ctrl as "ChatPanel (sole live reducer)"
    participant API as "POST /api/claude-agent/tool-confirm"
    participant Service as "ClaudeAgentService callback"
    participant Store as "Bounded ToolConfirmationStore policy+Future"

    Service->>Store: Atomically register (thread, turn, toolCall) policy + Future
    Service-->>Ctrl: Publish tool-approval-request only after registration
    Ctrl-->>UI: Render typed confirmation
    alt Approve
        User->>UI: Approve
        UI->>Ctrl: confirm(toolCallId, approved=true)
    else Reject
        User->>UI: Reject with reason
        UI->>Ctrl: confirm(toolCallId, approved=false, reason)
    else AskUserQuestion
        User->>UI: Submit answers keyed by stable qN IDs
        UI->>Ctrl: confirm(toolCallId, approved=true, answers)
    end
    Ctrl->>API: threadId + toolCallId + untrusted decision
    API->>Store: Owner + active turn + exact tool identity + untrusted decision
    Store->>Store: Validate AskUser/network/reject_only and compare-and-set pending
    alt Allowed and pending
        Store-->>Service: Resolve exactly one pending future
        Service-->>Ctrl: Tool output / continued Chat SSE
    else Already settled
        API-->>Ctrl: Idempotent not-pending result
    else Forbidden or invalid
        API-->>Ctrl: Stable 4xx, do not resolve future
    end
```

The old Dream endpoint branch is removed. `ToolConfirmationDock.tsx` submits only
the canonical Chat decision, while
`backend/claude_agent/tool_confirmation_store.py` owns typed AskUser,
network/reject-only validation, atomic settlement and bounded replay tombstones.
A `reject_only` confirmation cannot be approved regardless of browser payload.

## Scenario 5 — Subagent starts, runs and completes

```mermaid
sequenceDiagram
    participant Main as "Main Agent"
    participant Bus as "Canonical Chat EventBus"
    participant Ctrl as "ChatPanel (sole live reducer)"
    participant Sub as "Subagent runtime/transcript"
    participant SubAPI as "GET thread subagents"
    participant UI as "Dream or Chat subagent panel"

    Main->>Bus: Agent/Task tool-input-start and available
    Bus-->>Ctrl: Canonical tool events
    Ctrl-->>UI: Show launched/running task row
    Main->>Sub: Start child task under same thread workspace
    loop While main runtime is running
        UI->>SubAPI: Read safe thread-scoped subagent projection
        SubAPI->>Sub: Project transcript/meta
        Sub-->>SubAPI: running timeline
        SubAPI-->>UI: running
    end
    Sub-->>Main: Result
    Main->>Bus: tool-output-available
    UI->>SubAPI: Refresh
    SubAPI-->>UI: completed or failed terminal
```

The existing owned subagent REST route is in
`backend/routers/claude_agent.py`; the current hook is
`frontend/src/hooks/useThreadSubagents.ts`. Dream reuses this thread-scoped
projection and must not create a run-scoped subagent protocol.
Historical subagent rows or a completed subagent projection never make the main
thread busy and never make Stop visible.

## Scenario 6 — Main Agent Stop and cancellation propagation

```mermaid
sequenceDiagram
    actor User
    participant UI as "Dream or Chat surface"
    participant Ctrl as "ChatPanel (sole live reducer)"
    participant Stop as "POST thread stop"
    participant Factory as "ClaudeAgentThreadFactory"
    participant Main as "Main Agent task"
    participant Child as "Child/subagent/tool work"
    participant Bus as "EventBus"

    Note over UI,Ctrl: Show Stop only for local submitted/streaming main turn or authoritative main-turn running
    User->>UI: Stop current main turn
    UI->>Ctrl: stop(threadId)
    Ctrl->>Stop: Owned threadId
    Stop->>Factory: stop_thread
    alt HTTP 2xx and running=false
        Factory->>Main: Cancel running task
        Main-xChild: Propagate cancellation/cleanup
        Main->>Main: Persist any partial assistant state
        Main->>Bus: finish(stop) exactly once
        Bus-->>Ctrl: Canonical terminal then EOF
        Ctrl->>Stop: GET history/status
        Stop-->>Ctrl: Authoritative idle/terminal plus persisted partial
        Ctrl-->>UI: cancelled, unlock composer
    else Non-2xx, timeout, malformed result, or running=true
        Ctrl-->>UI: Keep input locked, do not claim cancelled
        Ctrl->>Stop: GET status then reconnect main-turn stream
        Stop-->>Ctrl: Reconcile until authoritative terminal/idle
    end
```

Stop is an explicit action, unlike merely unmounting or losing the network. The
verified endpoint is in `backend/routers/claude_agent.py`. Unmount,
navigation and network abort close only the reader and never call Stop.

## Scenario 7 — Failure before any output

```mermaid
sequenceDiagram
    actor User
    participant Ctrl as "ChatPanel (sole live reducer)"
    participant Runtime as "ClaudeAgent runtime"
    participant Bus as "EventBus"
    participant Obs as "DreamLifecycleObserver"
    participant Biz as "Default latest-hint sink"

    User->>Ctrl: Send
    Runtime->>Bus: error(errorText)
    Bus-->>Ctrl: Show stable failed state, no fabricated assistant text
    Bus-->>Obs: Failure candidate with eventId/sequence
    Runtime->>Bus: finish(error) exactly once
    Bus-->>Ctrl: Terminal failed then EOF
    Bus-->>Obs: Terminal failure hint
    Ctrl->>Runtime: Reload history/status
    Runtime-->>Ctrl: User row, no assistant output or only valid persisted parts
    Obs-->>Biz: Store one failed terminal hint in bounded process memory
```

Provider diagnostics may be shown only according to the canonical Chat error
policy; the Observer records no provider text or diagnostics.

## Scenario 8 — Failure after partial output

```mermaid
sequenceDiagram
    participant Runtime as "ClaudeAgent runtime"
    participant Bus as "EventBus"
    participant Ctrl as "ChatPanel (sole live reducer)"
    participant DB as "Chat persistence"
    participant Obs as "DreamLifecycleObserver"

    Runtime->>Bus: text-delta / tool parts
    Bus-->>Ctrl: Render partial output
    Runtime->>Bus: error
    Runtime->>Bus: finish(error) exactly once
    Runtime->>DB: Persist partial assistant state
    Bus-->>Ctrl: EOF
    Ctrl->>DB: Reload authoritative history
    DB-->>Ctrl: Persisted partial parts marked interrupted/failed
    Bus-->>Obs: Ordered failure terminal
    Obs->>Obs: Close turn, ignore late events
```

Partial conversation output remains visible, but it cannot prove Dream required
files or Workflow Run completion.

## Scenario 9 — Browser disconnect and SSE reconnect

```mermaid
sequenceDiagram
    participant Browser as "Dream or Chat browser"
    participant Ctrl as "ChatPanel (sole live reducer)"
    participant API as "Chat thread API"
    participant Bus as "Active EventBus replay"
    participant Runtime as "Background turn"

    Runtime->>Bus: Events continue
    API--xBrowser: Network disconnect
    Note over Runtime,Bus: Producer continues, disconnect is not Stop
    Ctrl->>API: GET messages
    Ctrl->>API: GET status
    API-->>Ctrl: running + pending tool IDs
    Ctrl->>API: GET threads/{threadId}/stream
    API->>Bus: New subscription
    Bus-->>Ctrl: Full buffered replay then live events
    Ctrl->>Ctrl: Deduplicate/reduce canonical parts
    Runtime->>Bus: finish and sentinel
    Ctrl->>API: Reload history/status after EOF
```

Reconnect preserves cached tool input when approval events omit it through the
shared SSE merge path; current coverage lives in
`frontend/src/components/chat/__tests__/ToolConfirmationRecovery.test.ts`.

This sequence assumes the HTTP request reaches the process that owns the active
turn. That is true for the current single-uvicorn-worker,
backend-`max-instances=1` deployment. Redis EventBus can replay a stream to a
caller that already knows `(session_id, turn_id)`, but does not provide
active-turn discovery, HTTP routing, `/status`, Stop or confirmation ownership;
it must not be used to claim this sequence works across arbitrary workers/pods.

## Scenario 10 — Page refresh and history recovery

```mermaid
sequenceDiagram
    actor User
    participant Page as "Refreshed Dream page"
    participant Biz as "Story Workspace REST"
    participant Ctrl as "New Dream-mounted ChatPanel"
    participant ChatAPI as "Chat thread API"

    User->>Page: Refresh / deep-link to workflowRunId
    Page->>Biz: GET /workflow-runs/{workflowRunId}/dream-files
    Biz-->>Page: Existing authorized response with threadId and files
    Page->>Ctrl: mount(threadId)
    Ctrl->>ChatAPI: GET messages
    Ctrl->>ChatAPI: GET status
    alt running
        Ctrl->>ChatAPI: GET thread stream
        ChatAPI-->>Ctrl: replay/live
    else idle/not_found
        Ctrl-->>Page: Render persisted history, no live stream
    end
    Page->>Biz: Continue run/files polling as needed
```

No local Dream cursor, transient text buffer or `settledRevision` is required to
recover the conversation. No new re-entry endpoint is introduced.

## Scenario 11 — Observer receives events without owning workflow projection

```mermaid
sequenceDiagram
    participant Bus as "Normalized EventBus"
    participant Registry as "SessionObserverRegistry"
    participant Obs as "DreamObserver"
    participant Sink as "Default bounded latest-hint sink"
    participant REST as "Existing actor-scoped Dream-files REST"
    participant Owner as "Existing Dream domain owner"
    participant DB as "Workflow Run DB"
    participant VM as "Dream business-copy whitelist"
    participant UI as "Dream page"
    participant Chat as "Canonical ChatPanel"

    Registry->>Obs: after context assembly with internal Dream context
    Obs->>Bus: Subscribe before Session Execution
    Bus-->>Obs: Ordered normalized events through bounded handoff
    Obs->>Obs: Validate context, derived eventId and sequence
    Obs-->>Sink: project latest hint or mark reconcile-needed
    Owner->>DB: Persist/transition through existing owner path
    UI->>REST: Actor-scoped poll/read
    REST->>DB: Read authorized durable workflow/file projection
    REST->>Sink: Read matching run/thread/actor highest-generation hint if available
    REST-->>UI: Durable projection plus optional safe agentActivity
    UI->>VM: Reduce optional hint for page copy
    alt content_generation, workflow_operation, or reconcile_requested
        VM-->>UI: Informational Dream business copy
    else terminal, confirmation, subagent, or generic tool
        VM-->>UI: No business copy
        Chat-->>UI: Canonical lifecycle/confirmation/subagent/tool presentation
    end
```

Subscriber/sink execution is off the Chat response path. On terminal/sentinel,
context failure, Stop, task exception, eviction or factory close, the Coordinator
revokes the lease, unsubscribes and applies bounded task cancellation/await. The
default sink stores at most 256 latest `(run, thread, actor)` hints in memory,
rejects an older generation, and calls no lifecycle owner. Actor/generation are
selection guards and never enter the wire. Tool, subagent, content-generation
and workflow-operation hints expose only safe enums and an optional SHA-256
correlation value. The REST
field is display-only, absent on no match/error and cannot alter the durable
projection. Its page view-model only renders content-generation,
workflow-operation and reconcile copy; terminal, waiting-confirmation, subagent
and generic-tool hints are ignored there. Existing transition guards and
`ChatPanel` remain authoritative. A complete Observer-to-durable-owner
integration is not claimed.

## Scenario 12 — Observer replay, duplicates and idempotency

```mermaid
sequenceDiagram
    participant Bus as "EventBus replay"
    participant Coord as "Coordinator bounded queue"
    participant Obs as "DreamLifecycleObserver"
    participant Dedup as "Per-Observer 4,096 eventId bound"
    participant Sink as "Business sink"

    Bus-->>Coord: normalized event at reader sequence 7
    Coord-->>Obs: accepted queue item
    Obs->>Dedup: derive sha256(thread, turn, 7), unseen and next sequence
    Dedup-->>Obs: accept
    Obs->>Sink: project once
    Bus-->>Coord: test/replay supplies the same event at sequence 7
    Coord-->>Obs: replay queue item
    Obs->>Dedup: duplicate key
    Dedup-->>Obs: ignore and count duplicate
    Bus-->>Coord: finish at sequence 8
    Coord-->>Obs: terminal queue item
    Obs->>Sink: one terminal hint
    Bus-->>Coord: late E9 after terminal
    Coord-->>Obs: late item rejected by closed lease
    Obs->>Dedup: turn already closed
    Dedup-->>Obs: ignore and count late event
```

On handle close or process restart the Observer dedup set is gone; no terminal
TTL/checkpoint is loaded. The independent owner/REST paths remain the source of
durable convergence.

If the EventBus reader itself raises, the Coordinator first projects reconcile
to clear stale activity, then resubscribes/replays once. Stable sequence-derived
IDs make the replay idempotent. A second failure follows bounded close and never
restarts the main Agent producer.

## Scenario 13 — Normal completion produces one terminal

```mermaid
sequenceDiagram
    participant Service as "ClaudeAgentService"
    participant DB as "Chat persistence"
    participant Bus as "EventBus"
    participant Ctrl as "ChatPanel (sole live reducer)"
    participant Obs as "DreamLifecycleObserver"

    Service->>Bus: message-final
    Bus-->>Ctrl: Success candidate, keep stream open
    Bus-->>Obs: Success candidate, not terminal
    Service->>DB: Persist assistant and structured output
    Service->>Bus: finish(stop)
    Bus-->>Ctrl: completed terminal
    Bus-->>Obs: completed terminal eventId
    Service->>Bus: sentinel
    Ctrl->>DB: Reload authoritative history
    Note over Ctrl,Obs: Any duplicate finish/late event is ignored, terminal count remains one
```

`message-final` must never independently emit a second terminal. Acceptance
asserts exactly one terminal in `ChatPanel` and Observer for each turn.

## Scenario 14 — Migrate old Dream protocol to Chat thread SSE

```mermaid
sequenceDiagram
    participant OldBuild as "Prior immutable build"
    participant NewBuild as "Single-protocol release candidate"
    participant Dream as "Dream page"
    participant Old as "Old Dream snapshot/SSE endpoints"
    participant Chat as "Canonical Chat thread API"
    participant Gate as "Source, route, bundle and scenario gates"
    participant Deploy as "Immutable-build deployment"

    OldBuild->>Old: Deployed behavior before replacement
    NewBuild->>Dream: Replace Dream protocol hook with existing ChatPanel composition
    NewBuild-xOld: Delete routes, adapter, hook, contracts and bridges
    NewBuild->>Gate: Prove old symbols/routes absent and run S01-S14
    Gate-->>Deploy: Approve single-protocol artifact
    Deploy-->>Dream: Serve new immutable build
    Dream->>Chat: History/status/thread SSE/send/confirm/stop only
    Dream-xOld: No old endpoint exists in this artifact
    Note over Deploy: Optional canary routes between complete immutable builds, never between protocols in one build
```

The repository change directly replaces production callers and hard-deletes the
old protocol. A deployment canary is optional infrastructure routing between
complete immutable builds; there is no repository feature flag or releasable
dual-protocol artifact. The hard removal and rollback gates are in
[Migration plan](./migration-plan.md).

## Permission behavior

- Dream re-entry obtains `threadId` only from the actor/run/workspace-authorized,
  already-existing Dream-files response, which is the sole re-entry
  binding seam and this migration adds no endpoint.
- Every Chat route independently rechecks thread ownership.
- Chat POST reverse-lookups Dream attempts by authenticated actor and owned
  thread. `workflowRunId` is not accepted by Chat conversation operations.
- Multiple rows are allowed only as one valid retry chain. The single
  unsuperseded leaf is selected; multiple leaves, graph corruption or frozen
  source mismatch fails closed with 409. No newest-run heuristic is allowed.
- Tool confirmation policy is server-owned. The UI cannot turn a `reject_only`
  request into an approval.
- Direct Chat adoption uses the same owner-visible row/part/export contract on
  both surfaces; server-private control rows and zero-visible-part rows remain
  hidden.

## Shared visibility and export behavior

History, live render, reconnect recovery and export all apply
`filterStoryWorkspaceControlMessages` before rendering parts. Rows marked
`story-workspace-guidance`, `story-workspace-dream-confirmation`, or a
server-attested `story-workspace-episode-action/v1` envelope are omitted
entirely. A remaining row with no visible parts is skipped; no empty text part or
blank bubble is synthesized.

For every remaining owner-visible row, Dream and Chat show/export the same
canonical fields: text; reasoning text/state under the existing collapsed UI;
tool call identity/name/state plus canonical input/output/error; and only the
client-safe provider/turn error emitted by `ClaudeAgentService`. Raw logs,
credentials, prompts and filesystem paths never become visible. Export consumes
this filtered non-empty view model and cannot re-read unfiltered persistence.

## UI and accessibility requirements

- Preserve the Dream rail/panel/dialog layouts and business actions, but render
  conversation rows by composing `ChatPanel` and its canonical `UIMessage` parts.
- Opening the conversation moves focus to the heading or composer according to
  the initiating action; closing returns focus to the trigger.
- Trap focus only in the mobile/modal dialog, not in the desktop inline panel.
- Stream announcements are polite and coalesced; token deltas are not announced
  individually.
- Confirmation focus remains stable through retry and cannot jump to a replayed
  settled card.
- Stop has an explicit accessible name and is never represented by closing the
  panel. It appears only for the current main turn, and its pending/failure state
  keeps the composer locked until authoritative recovery.
- “Jump to latest” appears when the user is not following the tail; replay must
  not force scroll away from their reading position.
- Failed partial output is labelled as interrupted without discarding readable
  content.

Unique source requirements are in
`docs/design/story-workspace/dream-workspace-and-reentry.md`;
transport-specific portions of that document are superseded, not its focus,
confirmation and re-entry behavior.

## Interaction acceptance summary

- The named S01–S10 browser suite passed in R19 headless Chromium with one worker
  and semantic waits. S11–S14 passed in the backend/source acceptance suite;
  they are not browser tests. The deployment-only immutable rollout/rollback
  action described in Scenario 14 remains unexercised.
- Both Dream → Chat and Chat → Dream switches preserve the same thread and live
  turn.
- Pre-output and partial-output failures are visibly different but share one
  terminal outcome.
- Runtime tool confirmation and one-time Dream business confirmation remain
  distinct.
- Subagents, Stop, reconnect and refresh use thread-scoped Chat capabilities.
- Existing Dream-files supplies the authorized `threadId`; no re-entry transport
  API is added.
- Observer duplicates/replay cannot duplicate a live-turn terminal hint; the
  current default sink does not project durable business state. Its optional
  Dream-files `agentActivity` is content-free display metadata; only the
  business-copy whitelist renders it, never canonical terminal/confirmation/
  subagent/tool state.
- R10 focused evidence for this Observer/UI boundary is 116 backend tests plus
  20 subtests and 6 frontend tests; R19 subsequently passed 687 focused backend
  tests, 1,927 broad backend tests with 17 skips and 655 subtests, 340 frontend
  unit/contract tests, S01–S10 headless Chromium and S11–S14 backend/source
  acceptance.
- The current worktree has no old conversation caller or endpoint; local source,
  OpenAPI and built-bundle deletion gates passed. An immutable artifact and
  deployment rollback proof remain mandatory before production promotion.
