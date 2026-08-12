# Dream Agent testing and acceptance

> Status: **R17–R32 local execution evidence recorded; R35 business-design review
> ACCEPT**. The production-shaped fake-provider chain,
> backend/frontend/Admin regressions, S01–S10 headless Chromium,
> S11–S14 backend/source acceptance, PG16 clone safety
> gates and one bounded real Gateway request passed their recorded scopes. R32
> also passed the current S01–S10 candidate in visible headed Chromium with one
> worker. R33–R35 add documentation coverage and parser/source audits, not new
> product test claims. This is not staging, canary, immutable rollback or
> production-load evidence.

## Release decision

The current source architecture and all required local functional gates,
including the R28 verifier implementation (128 tests + 37 subtests) and its
independent ACCEPT re-review (19 directed tests), are formally accepted.
Production rollout remains a separate
no-go until the explicitly unexecuted deployment gates are satisfied or owned by
release engineering: immutable artifact/rollback, staging or canary, and
production load/performance. A waiver cannot weaken permissions,
trusted Dream context, exactly-one terminal, server confirmation policy,
Observer isolation or hard deletion of the old protocol.

## Test layers

| Layer | Purpose | Current locations / remaining scope |
|---|---|---|
| Pure contract/reducer | Event conversion, replay, hydration, visibility, Stop | `ToolConfirmationRecovery.test.ts`, `ThreadSessionHydration.test.ts`, `ChatRuntimeState.test.ts` |
| Backend unit | Binding resolver, pending policy, Observer/Coordinator sequencing and cleanup | `test_claude_agent_dream_binding_resolver.py`, `test_claude_agent_confirmation_policy.py`, `test_story_workspace_dream_lifecycle_observer.py` |
| Backend API | Ownership, Dream-files thread binding and canonical endpoints | `test_server_claude_agent.py`, Story Workspace Dream files/launch/confirmation tests |
| Integration | Factory/EventBus/service/persistence and independent workflow owners | `test_claude_agent_thread_factory.py`, `test_event_bus.py`, opt-in `test_event_bus_redis_runtime.py`, service/workflow tests; no durable Observer sink exists |
| Browser component | Chat/Dream wrapper convergence, settlement, focus/layout | Current component specs listed in the commands below |
| Browser E2E | User-visible canonical Dream-thread scenarios | R19/R30 S01–S10 headless Chromium PASS; R32 current-candidate S01–S10 headed Chromium PASS with `--workers=1` |
| Cross-layer acceptance | Observer, single-terminal and migration scenarios | S11–S14 backend/source/OpenAPI acceptance PASS; these are not browser tests |
| Business-design coverage | Every in-scope Dream product/workflow/file/Episode capability has actors, owner, side effects, failure path, evidence and Mermaid sequence | `business-interaction-design.md` B01–B21 plus its coverage matrix and open-decision list |
| Migration/operations | Single-protocol artifact, source/route/bundle deletion, immutable-build rollback | Local source/OpenAPI/bundle PASS; immutable artifact, staging/canary and rollback pending |

## Four hard acceptance gates

### Gate A — One conversation protocol

- Dream production bundles contain no call to `/dream-agent/messages`,
  `/dream-agent/events` or `/dream-agent/tool-confirm` after cutover.
- Dream and Chat compose the same `ChatPanel` and canonical reducer; `ChatPanel`
  remains the sole `useChat`/live-message owner.
- Shared frontend extraction is limited to history/status/reconnect nonce,
  pending IDs, generation guard and post-EOF hydration. No app-wide
  `ClaudeThreadSessionProvider` or second `useChat` abstraction exists.
- One view opens at most one conversation SSE connection.
- `workflowRunId` appears only in Story Workspace business requests, never Chat
  send/history/status/stream/confirm/stop.
- Switching surfaces preserves the exact `threadId`, message IDs, tool-call IDs
  and active turn.
- Dream re-entry obtains the existing `threadId` from actor-scoped
  `/workflow-runs/{runId}/dream-files`; this migration adds no binding endpoint
  or binding identifier. Optional `agentActivity` is display metadata, not a
  re-entry selector.

### Gate B — Trusted context and confirmation policy

- Chat route authenticates thread ownership before Dream lookup.
- Zero matching attempts is ordinary generic Chat.
- One valid retry chain selects its unique unsuperseded leaf.
- Multiple independent leaves, missing parent, cycle or frozen-source mismatch
  returns 409 and starts no turn.
- Browser-authored run/context/actor/Deck fields cannot affect trusted context.
- Before approval publication, `ClaudeAgentService._make_tool_confirm_cb` and
  the per-turn `ToolConfirmationStore` atomically register a bounded policy and
  Future keyed by `(threadId, turnId, toolCallId)`.
- AskUser IDs/bounds, network policy and `reject_only` are validated against that
  immutable record, then one atomic resolver wins; timeout/reject/cancel/
  terminal/close cleans policy and Future together.

### Gate C — Lifecycle and Observer correctness

- Every started turn reaches exactly one completed/failed/cancelled terminal.
- Pre-output and partial-output failure persist/render correctly.
- `message-final` is not terminal until persistence and `finish` ordering
  complete.
- `DreamLifecycleObserver` consumes `NormalizedAgentEvent` directly, derives
  event IDs from `(threadId, turnId, sequence)`, enforces per-Observer bounded
  dedup/high-water behavior, and ignores late events after terminal.
- Tool/subagent/content-generation/workflow-operation hints expose only bounded
  enums, outcome/state and a SHA-256 correlation value; raw tool name/call ID,
  input and output never enter the projection or response.
- The existing actor-scoped Dream-files GET may attach a matching process-local
  `agentActivity` for display only. When no matching hint exists, or any
  projection lookup/validation fails, the field is omitted; it cannot affect
  workflow/confirmation fields, Chat lifecycle, composer state or Stop
  eligibility.
- The latest-hint key includes actor identity and generation ordering; a
  cross-actor or older-generation value cannot overwrite/expose the current
  hint. Actor/generation are never serialized.
- The Dream business-page view model renders only `content_generation`,
  `workflow_operation` and `reconcile_requested` copy. Turn-terminal,
  waiting-confirmation, subagent and generic-tool hints produce no business
  copy; canonical `ChatPanel` exclusively renders those Agent concerns.
- Observer absence, delay, exception and overflow do not change Chat SSE event
  order/content or turn lock cleanup.
- `DreamObserver`, registered through `SessionObserverRegistry`, owns the
  subscriber, bounded queue, reader and sink tasks. Close paths revoke/
  unsubscribe and perform bounded cancellation/await.
  A cancellation-swallowing injected sink may be detached/tracked; acceptance
  must expose that risk rather than assert unconditional zero residual tasks.
- Restart reads Workflow Run/business projection from existing owning services/
  DB without an Observer checkpoint. The current default Observer sink is not
  wired to those owners; its optional Dream-files field is not durable truth.
- Final diff does not modify
  `backend/libs/claude_agent_kit/server/agent_runner.py`; focused runner/service
  regressions preserve SDK classification, policy, cancellation, persistence and
  normalized terminal semantics.

### Gate D — Legacy removal

- Every production caller is replaced in the release candidate.
- Routes, adapter, old hook/contracts/bridges and obsolete protocol tests are
  absent from source and generated inventories before deployment.
- The built frontend has no old endpoint string or runtime transport selector.
- Rollback uses the recorded prior immutable build; it does not add the old
protocol back into the new artifact.

### Deployment-control boundary

- Redis EventBus is accepted only for callers that already know
  `(session_id, turn_id)`: shared writer/replay, TTL and exactly-one terminal.
- Active-turn registry, thread status, Stop, confirmation Future and HTTP stream
  routing remain process-local.
- Current production topology is one uvicorn worker and backend
  `--max-instances=1`. A multi-worker/pod claim requires a separate distributed
  registry/routing/control test plan; the Redis suite below cannot satisfy it.

### Current evidence checkpoint — R17 through R32

These are measured local or owned-clone facts from the current candidate line.
They are scoped PASS results, not an immutable production artifact or deployment
sign-off.

| Round/check | Measured result | Evidence boundary |
|---|---|---|
| R17 production-shaped fake-provider chain | Full owned PostgreSQL/Admin/Dream/headless chain PASS: producer 1/1, Admin generated-story 1/1, 32/32 correlated Gateway and fake-provider requests, balanced ledger, zero external provider calls, exact cleanup | Local isolated PASS; no real provider or headed browser |
| R19 backend broad | 1,927 passed, 17 skipped, 655 subtests | Local PASS; the 17 skipped cases are reported as skips, not promoted to PASS |
| R19 backend focused | 687 passed | Binding, confirmation, EventBus, Observer, lifecycle, persistence and Gateway-focused local PASS |
| R19 Redis and Gateway loopback | Isolated Redis and Gateway loopback gates PASS with owned resources and cleanup | Known-turn/loopback contract only; no multi-worker HTTP-control claim |
| R19 frontend | 340 unit/contract tests, TypeScript, ESLint and production build PASS | Local artifact PASS; immutable bundle not retained |
| R19 cross-layer interaction matrix | S01–S10 PASS in headless Chromium with semantic waits; S11–S14 PASS in backend/source/OpenAPI acceptance | No current-candidate headed S01–S10 result; deployment portion of S14 remains unexercised |
| R20 Admin canonical artifact contract | 28/28 scoped generated-story contracts and Admin TypeScript PASS after one stale test-only SQL expectation was synchronized | Sibling production query unchanged |
| R24 strict verifier | 24 focused/adjacent tests PASS; read-only PostgreSQL SQL probe parsed the receipt query | Provider-free hardening; the later review found two assertion gaps now assigned to R28 |
| R25 clone isolation/interruption | Provider-free PG16 clone preflight PASS; injected SIGINT exited 130 and all source/container/port/Git/private-runtime cleanup checks were true | Zero provider calls; source and original checkouts unchanged |
| R26 one bounded real request | One request, no retry: `hy-preview` → resolved/provider `hy3-preview`, HTTP 200 settled/succeeded, `entitlementBound=true`, reserve = capture + release, zero reserved remainder; canonical terminal/session/persistence observations, source integrity and cleanup PASS | Fresh generic clone thread; not terminal Dream workspace binding; post-run verifier gaps tracked in R28 |
| R28 post-proof verifier closure | 128 tests + 37 subtests PASS; success now requires nonblank `message-final`, exactly one start, at least one meaningful delta, exactly one end, strict final tail, visibility/dispatch private-denylist enforcement and exact two-row visible projected history | No provider call and no product runtime or `agent_runner.py` edit; independent re-review ACCEPT |
| R28 independent re-review | ACCEPT; 19 directed tests PASS | No new false-positive path, privacy leak or blocker; no provider call |
| R30 current-worktree completion audit | Backend binding/confirmation/Observer/migration acceptance: 71 tests + 37 subtests PASS; S01–S10 headless Chromium: 10/10 PASS with one worker; TypeScript, ESLint (0 errors, 21 unrelated existing warnings) and production build PASS; source/OpenAPI/built-bundle legacy scans, protected-runner hash and `git diff --check` PASS | No provider or headed browser; current-candidate headed remains user-deferred. The R30 runner left no controller/listener, but 58 pre-existing PID-1 Playwright processes in macOS `UEs` state resisted exact SIGTERM and SIGKILL, so global process-cleanliness is not claimed |
| R32 final visible-browser gate | S01–S10 `10 passed (14.4s)` using Chromium `--headed --workers=1`; semantic-wait scan found no fixed sleep. Fresh S11–S14 subset: 9 passed / 2 deselected. Legacy source gate, one production `useChat`, protected-runner SHA-256 and diff checks PASS | No provider request. After the user reboot removed the earlier kernel-stuck processes, the R32 browser exited cleanly, ports 5173/8765 were free and no new report artifact remained |

R26 emitted no prompt, response body, session identifier, token, URL,
credential or private source data into this evidence set. The clone-only user had
zero eligible terminal Dream threads, so the privacy-safe fallback proves the
shared Chat runtime and Gateway path only. A pre-existing Admin entitlement-
enforcement gap remains a residual risk; this proof did not exploit it because
success required a non-null subscription entitlement binding.

### R32 persistent-goal completion matrix

This matrix audits the current worktree against the eight persistent objectives;
it does not redefine completion around already-green tests.

| Objective | Direct current evidence | Status |
|---|---|---|
| One Chat thread/SSE interaction runtime | Dream wrapper directly composes `ChatPanel`; source has one production `useChat`; S01–S10 exercise send, incremental text, Dream↔Chat handoff, confirmation, subagent, Stop, failure, reconnect and reload | Direct PASS in both headless and current-candidate headed Chromium |
| Delete Dream conversation protocol | Deleted routes/adapter/service/hook/reducer; production source, OpenAPI and built bundle contain zero legacy conversation endpoints | Direct PASS |
| Build Dream above `ClaudeAgentService` | `ClaudeAgentThreadFactory.run_streaming` is the sole public turn entry, exposes canonical Chat SSE plus its same-turn completion handle, Dream context is server-resolved, and protected `agent_runner.py` matches HEAD | Direct PASS |
| Observer is idempotent and non-authoritative | S11–S13 plus focused Observer tests cover trusted identity, bounded dedup/order/gap handling, single terminal, safe operation scopes, sink failure isolation and cleanup | Direct PASS |
| Reuse thread/message/session/reconnect/confirm/Stop persistence | Canonical API/service tests plus S01–S10 prove the same thread IDs, message IDs, running status and post-EOF hydration without a second send | Direct local PASS |
| Dream Flow remains business-only and authorized | Actor-scoped Dream-files, strict binding resolver, workflow command owners and display-only `agentActivity` tests prove one-way projection and unchanged business authorization | Direct local PASS |
| New design system and historical migration | Eleven-document design set, including complete B01–B21 business sequences, synchronized indexes/history, two superseded documents deleted, relative-link/source/status reader audits PASS, Git recovery anchors recorded | Direct PASS |
| No copied/third runtime or durable Observer store | One `useChat`, no Dream EventSource/parser/reducer/provider, bounded process-local latest-value projection only, protected runner unchanged | Direct PASS |
| Final visible headed Chromium gate | R32 current-candidate S01–S10, semantic waits, `--headed --workers=1` | **DIRECT PASS: 10/10** |
| Global browser-process cleanup | User reboot cleared the earlier PID-1 `UEs` processes; R32 post-run inventory found no Playwright/Chromium process and no 5173/8765 listener | **DIRECT PASS** |

## Required 14-scenario matrix

| ID | Scenario | Required assertions | Priority | Release result |
|---|---|---|---|---|
| S01 | Dream normal send/incremental output | Chat POST only; server context resolved; ordered deltas; history matches final | P0 | R19/R30 headless + R32 headed PASS |
| S02 | Dream → Chat switch | Reader abort does not Stop; same running thread replays/continues | P0 | R19/R30 headless + R32 headed PASS |
| S03 | Chat → Dream switch | Existing actor-scoped Dream-files returns authorized thread; same ChatPanel history/turn resumes; no new API | P0 | R19/R30 headless + R32 headed PASS |
| S04 | Approve/reject/AskUser | One canonical confirm route; qN answers; reject-only blocked; idempotent settled result | P0 | R19/R30 headless + R32 headed PASS |
| S05 | Subagent start/run/complete | Same thread projection; historical subagent never creates main busy/Stop; terminal preserved across switch | P1 | R19/R30 headless + R32 headed PASS |
| S06 | Main Agent Stop | Eligible current main turn only; success cleans tasks; non-2xx/timeout/running retains input lock and reconnects | P0 | R19/R30 headless + R32 headed PASS |
| S07 | Failure before output | User row retained; no fabricated assistant; one failed terminal | P0 | R19/R30 headless + R32 headed PASS |
| S08 | Failure after partial output | Partial parts retained and marked interrupted; not business completion | P0 | R19/R30 headless + R32 headed PASS |
| S09 | Browser disconnect/reconnect | Producer continues; history/status/replay converge; approval input preserved | P0 | R19/R30 headless + R32 headed PASS |
| S10 | Page refresh/history recovery | Existing Dream-files threadId → hydration → ChatPanel; running/settled state reconstructed; no new API | P0 | R19/R30 headless + R32 headed PASS |
| S11 | Observer remains off-path | Safe optional Dream-files activity is display-only/bounded/process-local; actor/generation prevent stale exposure; page shows only content/workflow/reconcile copy; canonical terminal/confirmation/subagent/tool UI and durable owners remain unchanged | P0 | R19/R30/R32 backend acceptance PASS |
| S12 | Observer replay/duplicates | Same derived event ID calls sink once while handle is live; gap requests reconcile; late after terminal ignored | P0 | R19/R30/R32 backend acceptance PASS |
| S13 | Normal exactly-one terminal | `message-final` candidate then persisted `finish`; terminal count exactly one | P0 | R19/R30/R32 backend service acceptance PASS |
| S14 | Legacy migration | One release candidate contains Chat transport only; old code/routes absent; immutable-build rollback works | P0 | R19/R30/R32 backend/OpenAPI/source PASS; immutable rollback pending |

Each scenario is specified as a separate Mermaid sequence in
[Interaction design](./interaction-design.md). The Playwright suite executes
S01–S10; the backend/source acceptance suite executes S11–S14. Together they
establish the local cross-layer matrix, but only S01–S10 are Chromium evidence.
R32 supplies the current-candidate headed S01–S10 run. The local matrix still
does not substitute for the real immutable deployment/rollback action included
in S14's release requirement.

## Permission and binding matrix

| Actor/thread/run graph | Expected Chat POST result | Expected side effect |
|---|---|---|
| Actor owns thread; no Dream attempt | Generic Chat turn | No Dream context/Observer |
| Actor owns thread; one Dream attempt | Dream-bound Chat turn | Trusted context for that attempt |
| Actor owns thread; linear A→B→C retry chain | Dream-bound Chat turn for leaf C | A/B never selected |
| Actor owns thread; two independent leaves | 409 | No message, runtime, Observer or existence detail |
| Retry parent missing | 409 | Integrity metric/log only |
| Retry cycle | 409 | Integrity metric/log only |
| Chain frozen source/Deck mismatch | 409 | No runtime start |
| Actor does not own thread | 404-equivalent ownership response | No Dream lookup leak |
| Actor owns run but thread differs | Fail closed | No context |
| Browser adds run/actor/context fields | Rejected or ignored by strict schema | Cannot select authority |
| Owned thread already running | Existing busy/reconnect semantics | No second turn |

The linear retry case is mandatory because
`backend/services/workflow/run_service.py:171-209` intentionally reuses
`source_voice_thread_id` and sets `retry_of_run_id`.

### Existing Dream-files binding contract

| Request | Expected result |
|---|---|
| Actor owns run/workspace | Existing response contains its validated non-empty `threadId` |
| Cross-actor or hidden run | Existing fail-closed 403/404-class response; no thread leak |
| Returned thread not owned by actor | Fail closed before ChatPanel mounts |
| Source diff/API inventory | No new re-entry/binding endpoint or additive field introduced for this migration |

## Confirmation policy matrix

| Pending kind | Input | Expected |
|---|---|---|
| Any first callback | Trusted identity/policy | Future and policy atomically registered before approval event |
| Duplicate callback | Same identity and policy fingerprint | Join same waiter; no second record/event |
| Duplicate callback | Same identity, different policy | Fail closed; do not replace policy |
| Generic approval | approve | Resolve once |
| Generic approval | reject + bounded reason | Resolve rejection once |
| AskUser | answers keyed by known qN IDs | Accept typed/bounded answers |
| AskUser | missing/unknown/oversized answer | 4xx; future remains pending |
| Network | approved host/policy shape | Apply server policy |
| `reject_only` | approve=true | 4xx; never resolve as approval |
| Any | wrong thread/actor/turn/tool ID | 404/409 without leak |
| Any | exact replay after settlement | Idempotent not-pending/settled result |
| Any | concurrent double submit | One resolution; second settled result |
| Any valid decision, including reject | Exact record settles | Future/policy leave pending state; bounded replay tombstone may remain up to five minutes/256 entries or turn cleanup |
| Any pending decision | timeout/Stop/cancel/terminal/context failure/factory close | Pending Future/policy are cancelled; turn teardown clears replay tombstones |

The deleted baseline policy tests are historical migration input only and must
be read with:

```bash
git show a506c83:backend/tests/test_story_workspace_dream_agent_messages.py
```

There is no current
`backend/tests/test_story_workspace_dream_agent_messages.py`. Canonical policy
coverage now lives in `backend/tests/test_claude_agent_confirmation_policy.py`,
`backend/tests/test_claude_agent_service.py` and
`backend/tests/test_server_claude_agent.py`.

The browser does not submit `turnId`; the route snapshots the current server
turn and matches `(threadId, turnId, toolCallId)`. Tests must prove an old-turn
tool ID cannot resolve a new turn and a cross-loop resolution is awaited through
the atomic state change rather than treated as successful when merely queued.

## Event and terminal matrix

| Ordered normalized events | ChatPanel terminal | Observer terminal | Persisted result |
|---|---|---|---|
| `message-final`, `finish(stop)`, sentinel | completed once | completed once | Final assistant |
| `error`, `finish(error)`, sentinel | failed once | failed once | User plus valid partial if any |
| text delta, `error`, `finish(error)`, sentinel | failed once with partial visible | failed once | Partial assistant |
| `finish(stop)`, sentinel with no `message-final` | cancelled once | cancelled once | User/partial |
| duplicate `finish` | First terminal only | First eventId only | No duplicate write |
| event after terminal | Ignore/count late | Ignore/count late | No mutation |
| sentinel without `finish` | Protocol failure + history/status recovery | Reconcile hint, no invented success | Existing DB truth |

Tests must assert ordering from verified service behavior at
`backend/claude_agent/service.py:1715-1757`.

## Observer tests

### Pure sequencing

- Same derived `(eventId, threadId, turnId)` replay is ignored while the handle
  is live.
- Event IDs are derived from `(threadId, turnId, sequence)`, so another
  turn/thread is namespaced distinctly.
- Sequence `n+1` is accepted; `<n+1` is duplicate/replay; `>n+1` records a gap
  and emits `reconcile_requested`.
- Keepalive does not increment sequence.
- First terminal closes the turn; all later events are ignored.
- Each Observer retains at most 4,096 IDs; the default sink retains at most 256
  latest `(run, thread, actor)` hints and rejects older generations. There is no
  Observer terminal TTL or 256-turn cache.

### Failure isolation

- Sink absent: Chat stream unchanged.
- Sink raises synchronously/asynchronously: Chat stream unchanged; in-process
  `sink_errors` diagnostic rises.
- Sink sleeps beyond turn: Chat terminal and lock cleanup are unchanged.
- Queue full: activity/waiting hints drop; a terminal/reconcile hint may displace
  one queued item. Owner facts remain independent in DB.
- Process restart: Observer/default-sink memory is empty; actor-scoped REST reads
  current owner truth and may omit `agentActivity`.
- Reader exception: project reconcile to clear stale activity, resubscribe and
  replay once; stable IDs suppress the prefix. A second failure closes the
  handle and never restarts the Agent producer.
- No Observer table, migration, outbox or checkpoint artifact exists.
- Subscription/queue/worker is ready before context assembly can emit failure;
  assembly failure then reaches the common close path.
- Normal terminal+sentinel, sentinel without terminal, Stop, producer exception,
  explicit close, session eviction and factory `aclose` each exercise lease
  revoke, unsubscribe and bounded task close.
- The current default sink performs no owning-service write. Before any durable
  sink is wired, it must recheck the lease at its side-effect boundary and prove
  late-write safety.
- Tool start/approval/result fixtures prove `tool`, `subagent`,
  `content_generation` and `workflow_operation` classification, stable
  same-call correlation, success/error reduction and absence of raw names, IDs,
  inputs and outputs.
- Dream-files API/gateway fixtures prove that only the already-authorized,
  matching `(runId, threadId, actorId)` highest-generation entry receives
  optional `agentActivity`; actor/generation are not serialized. When no match
  exists or factory/snapshot/validation raises, the response is preserved with
  the field absent.
- A present hint is asserted not to change `canConfirm`, confirmation facts,
  file/run revisions, Workflow Run status, Chat status, input lock or Stop.
- Frontend view-model fixtures assert that content-generation,
  workflow-operation and reconcile hints produce informational copy, while
  turn-terminal, waiting-confirmation, subagent and generic-tool hints produce
  no Dream business-page copy.
- Ordinary teardown leaves no handle/subscriber. A test sink that swallows
  cancellation may remain temporarily in `live_detached_tasks`; that bounded,
  observable risk must not be reported as zero residual tasks.

### Equivalence oracle

For the same normalized event fixture, capture Chat frames with Observer disabled
and enabled. Assert byte-for-byte equality and identical sentinel timing within
test scheduling tolerance. The Observer may change only in-process diagnostics
and latest-hint memory.

## Frontend reducer/reconnect tests

- Initial and reconnect paths call the same reducer.
- Split/merge SSE frames across every byte boundary, LF/CRLF, UTF-8 multibyte
  Chinese, embedded newline and JSON-special-character variants; parser
  converges without replacement characters or dropped data.
- Approval without `input` retains prior tool input on initial and replay paths.
- Full EventBus replay does not duplicate text/tool parts.
- Switching/unmount aborts the reader but never sends Stop.
- `ChatPanel` is the only `useChat`/live reducer owner; Dream composes it and no
  Provider/second runtime abstraction exists.
- Stop is visible only for local submitted/streaming main turn or authoritative
  main-turn `running`; historical subagent data never enables it.
- Stop success unlocks only after authoritative idle/terminal recovery. Non-2xx,
  timeout, malformed body or `running=true` keeps input locked and performs
  status + stream reconnect.
- Post-EOF history replaces transient parts only for the same thread/generation.
- Stale async recovery from a prior thread cannot overwrite the active thread.
- History, live render, reconnect and export share
  `filterStoryWorkspaceControlMessages`; private guidance/Dream-confirmation/
  episode-envelope rows are absent, zero-visible-part rows create no blank
  bubble, and visible owner parts match across Dream and Chat.
- Dream `markRead`, scroll-follow, focus return and polite announcement behavior
  survives ChatPanel composition.

Current seams to protect are
`frontend/src/components/chat/threadSessionHydration.ts`,
`frontend/src/components/chat/chatRuntimeState.ts`,
`frontend/src/components/chat/toolConfirmation.ts`,
`frontend/src/lib/claude-agent-sse-utils.ts`,
`frontend/src/lib/claude-agent-transport.ts`, `ChatPanel.tsx`, `ChatView.tsx`,
and
`frontend/src/components/story-workspace/dream/StoryWorkspaceDreamThreadChat.tsx`.

## Workflow/business tests

- Conversation `completed` alone does not transition Workflow Run to completed.
- Required-output-ready fact traverses running → output_validating →
  pending_review through the existing lifecycle owner.
- One business confirmation traverses pending_review → confirmed exactly once.
- Post-confirmation dispatch leaves the Workflow Run at confirmed while the
  shared Thread independently reports active execution.
- Episode complete fact traverses confirmed → completed.
- Illegal/stale/out-of-order facts do not regress status.
- Runtime tool rejection may continue/fail the turn but is not the one Dream
  business rejection.
- REST polling/re-entry sees current DB truth after Observer restart/failure.

Executable transition evidence is
`backend/services/workflow/run_service.py:95-122` and
`backend/services/story_workspace/dream_workflow_lifecycle_service.py:40-141`.

## Security and privacy tests

- Cross-actor thread, run, confirmation and subagent requests fail without
  existence disclosure.
- A forged message metadata/context/run field never enters MCP environment.
- Deck/binding mismatch fails before runner creation.
- The same fixtures on Dream and Chat produce identical visible rows/parts for
  text, reasoning state/text, tool identity/name/state/input/output/error and
  canonical client-safe provider/turn errors.
- `story-workspace-guidance`, `story-workspace-dream-confirmation` and
  server-attested episode-action envelope rows never render or export. A row with
  zero visible parts produces no empty text/bubble.
- Export consumes the filtered visible model and cannot re-read raw persistence;
  private rows never enter export artifacts.
- Observer observations, diagnostics and logs contain no prompt, response,
  answers, tool input, token, credential or filesystem path.
- `agentActivity.operationId` is either absent/null or exactly a lowercase
  64-character SHA-256 value; raw tool/subagent IDs and names are not serialized.
- Cross-run/thread activity entries are not exposed through an authorized
  Dream-files response; cross-actor/older-generation entries are also rejected,
  actor/generation never enter the wire, and Observer lookup failure does not
  weaken the endpoint's existing ownership checks.
- No Observer metrics exporter exists. If release instrumentation is added,
  labels must be bounded and omit run/thread/turn IDs.
- Admin proxy preserves `text/event-stream`, `no-cache`, `no-transform`, flush
  behavior and split/merged Unicode/Chinese/newline/special-character chunks.

## Performance and capacity acceptance

Use the Phase 0 baseline rather than an invented absolute production target:

- Chat p95 time-to-first-event regresses by no more than 5% and 50 ms absolute.
- Enabling Observer changes Chat event/frame count by exactly zero.
- Observer enqueue is non-blocking and its memory never exceeds configured
  bounds under a ten-times expected event burst.
- Existing REST/business-owner visible projection convergence is ≤6 s with the
  current five-second poll when no request failure occurs. A future durable
  Observer sink needs a separately measured budget; the current default sink
  performs no durable work.
- Reconnect converges without duplicated parts for the largest supported replay
  buffer.
- One slow browser subscriber does not block another subscriber or Observer.

Any threshold change requires reviewer approval and a recorded baseline.

## Migration and deletion tests

- Final source scan has no production `/dream-agent/events`, Dream message hook,
  Dream adapter, confirmation bridge or runtime transport selector.
- The guarded production-only `rg` command below finds no
  `iter_dream_run_events|DreamStreamAdapter` match after `dream_launch_infrastructure.py`,
  `dream_confirmation_service.py` and `dream_internal_command_service.py` use
  the canonical `run_streaming`/same-turn completion drain.
- Launch failure handling, business-confirmation dispatch claim/heartbeat/
  ack, and message/episode dispatch claim/release focused tests still pass.
- Final route/OpenAPI snapshot has no legacy conversation endpoints.
- Built frontend bundles contain no legacy conversation endpoint strings.
- S01–S10 browser and S11–S14 backend/source acceptance execute against the same
  single-protocol release candidate that is eligible for deployment.
- An optional infrastructure canary routes only between complete immutable old
  and new builds; the new build itself never exposes both transports.
- Git recovery commit and rollback deployment procedure are exercised in
  staging.
- `git diff --quiet a506c83 --
  backend/libs/claude_agent_kit/server/agent_runner.py` exits zero; runner,
  service and factory focused regressions pass.

## Mandatory verification commands

These are reproducibility templates for the gates whose aggregate R17–R26
results are recorded above. Run them from the repository root unless a block
explicitly changes directory. A future immutable candidate must still record its
commit, output and artifact; file existence alone is never evidence.

### Backend focused and reasonable-scope regression

```bash
cd backend
python3 -m pytest -q \
  tests/test_event_bus.py \
  tests/test_dream_agent_acceptance_scenarios.py \
  tests/test_claude_agent_thread_factory.py \
  tests/test_claude_agent_service.py \
  tests/test_claude_agent_runner.py \
  tests/test_claude_agent_dream_binding_resolver.py \
  tests/test_claude_agent_confirmation_policy.py \
  tests/test_story_workspace_dream_lifecycle_observer.py \
  tests/test_story_workspace_dream_api.py \
  tests/test_server_claude_agent.py \
  tests/test_dream_thread_lookup_migration.py \
  tests/test_story_workspace_dream_files.py \
  tests/test_story_workspace_dream_launch.py \
  tests/test_story_workspace_dream_launch_api.py \
  tests/test_story_workspace_dream_confirmation.py \
  tests/test_story_workspace_dream_internal_commands.py \
  tests/test_story_workspace_dream_internal_recovery.py \
  tests/test_story_workspace_episode_actions.py
```

### Live Redis EventBus (opt-in, isolated)

The source dependency is `redis>=5,<8`; package declaration alone is not live
evidence. Point the opt-in suite only at a disposable Redis database/container:

```bash
cd backend
INK_AGENT_REDIS_RUNTIME_URL='redis://127.0.0.1:<isolated-port>/0' \
  .venv/bin/python -m pytest -q tests/test_event_bus_redis_runtime.py
```

The test uses random session/turn keys, deletes only those exact stream and
terminal keys, and must close both event-bus and Redis clients. It must prove
cross-process replay, Unicode/newline preservation, one winning `finish`, one
sentinel and rejection of late writers. Do not use `FLUSHDB`, a developer Redis
database or a shared production DSN.

**R10 local result (2026-08-11), retained and followed by the R19 Redis/Gateway
loopback rerun: PASS.** The suite ran against a disposable,
isolated Redis container and completed 4 test methods; the live-read method ran
2 passing subtests for RESP2 and RESP3. Covered behavior was live `XREAD`,
cross-process writer/replay with Chinese/newline payloads, concurrent
exactly-one `finish` plus one sentinel, legacy finish without sentinel,
positive stream/marker TTL and exact-key cleanup. The container and test keys
were removed afterward; no `FLUSHDB`, developer DSN or real model was used.

This result validates only the Redis EventBus contract for a known
`(session_id, turn_id)`. It does not validate cross-worker active-turn discovery,
HTTP request routing, `/status`, Stop or confirmation, all of which remain
process-local. It is therefore a local adapter PASS, not release/staging or
multi-worker/pod HTTP reconnect evidence.

The removed `test_story_workspace_dream_agent_messages.py` is baseline-only;
inspect it with the `git show a506c83:...` command above, never add its deleted
path to a current pytest invocation.

### Frontend contract, type, lint and build

```bash
cd frontend
npx playwright test \
  src/components/chat/__tests__/ToolConfirmationRecovery.test.ts \
  src/components/chat/__tests__/ThreadSessionHydration.test.ts \
  src/components/chat/__tests__/ChatRuntimeState.test.ts \
  src/components/chat/__tests__/ChatDreamReconnect.test.ts \
  src/components/chat/__tests__/ChatSubagentStatus.test.ts \
  src/components/chat/__tests__/AskUserQuestionMultiSelect.test.ts \
  src/components/story-workspace/dream/__tests__/StoryWorkspaceDreamThreadSettlement.test.ts \
  src/pages/story-workspace/__tests__/StoryWorkspaceDreamAgentLayout.test.ts \
  src/pages/story-workspace/__tests__/StoryWorkspaceDreamViewModel.test.ts \
  src/hooks/story-workspace/__tests__/useStoryWorkspaceDreamFiles.test.ts \
  --reporter=line --workers=1
npx tsc -b --pretty false
npm run lint
npm run build
```

The focused component files cover current ChatPanel composition, hydration,
visibility/zero-part rows, confirmation/replay, Stop helpers, subagent status and
Dream settlement, plus the Observer business-copy whitelist and strict optional
activity parser. They do not by themselves satisfy S01-S14 or the build gate.

### SSE chunking and Admin gateway

```bash
cd frontend
npx playwright test \
  src/components/chat/__tests__/ToolConfirmationRecovery.test.ts \
  --reporter=line --workers=1

cd ../../ink-admin-memory
pnpm exec vitest run \
  app/lib/gateway/sse.test.ts \
  app/lib/gateway/proxy-handler.test.ts \
  --exclude "**/*.integration.test.ts"
```

Fixtures must cover every-byte split and multi-frame merge, LF/CRLF,
Unicode/Chinese split inside a multibyte code point, embedded newlines and JSON
quotes/backslashes. Admin assertions include `text/event-stream`, `no-cache,
no-transform`, `x-accel-buffering: no` and incremental—not buffered—delivery.

### Browser E2E: headless and visible headed Chromium complete

```bash
cd frontend
npx playwright test e2e/dream-agent-thread-convergence.spec.ts \
  --browser=chromium --reporter=line --workers=1
npx playwright test e2e/dream-agent-thread-convergence.spec.ts \
  --browser=chromium --headed --reporter=line --workers=1
rg -n 'waitForTimeout|sleep\(' e2e/dream-agent-thread-convergence.spec.ts
```

The final `rg` must return no match. E2E waits use locator assertions,
`expect.poll`, response predicates or explicit app state; fixed sleeps may not
hide races. R19 and R30 completed S01–S10 headless Chromium; S11–S14 are
backend/source acceptance IDs and are not passed to Playwright. R32 executed the
same current-candidate S01–S10 suite visibly with `--headed --workers=1` and
passed 10/10. Failure-only trace, screenshot/video and console/network capture
were not triggered because the run passed; no failure artifact was produced.

### Diff and deletion gates

```bash
git status --short
git diff --check a506c83 --
git diff --quiet a506c83 -- backend/libs/claude_agent_kit/server/agent_runner.py
test ! -e backend/services/story_workspace/dream_stream_adapter.py
test ! -e backend/services/story_workspace/dream_agent_message_service.py
test ! -e frontend/src/hooks/story-workspace/useStoryWorkspaceDreamAgent.ts
if rg -n 'iter_dream_run_events|DreamStreamAdapter' \
  backend frontend/src -g '!backend/tests/**' -g '!**/__tests__/**'; then exit 1; fi
if rg -n '/dream-agent/(messages|events|tool-confirm)' \
  backend frontend/src -g '!backend/tests/**' -g '!**/__tests__/**'; then exit 1; fi
if rg -n 'ClaudeThreadSessionProvider|useStoryWorkspaceDreamAgent' \
  frontend/src -g '!**/__tests__/**'; then exit 1; fi
```

`git status --short` is inventory, not a cleanliness assertion, while the change
is still being assembled. `git diff --check a506c83 --` covers tracked worktree
content; after every new file is tracked in the candidate commit, also run
`git diff --check a506c83..HEAD`. The quiet protected-runtime check and `test`
commands must exit zero. Each guarded `rg` must find no production match.

### OpenAPI and built-bundle inventories

```bash
cd backend
python3 -c 'from server import app; paths=app.openapi()["paths"]; legacy=sorted(path for path in paths if "/dream-agent/" in path); print("\n".join(legacy) if legacy else "legacy Dream conversation OpenAPI paths: 0"); raise SystemExit(1 if legacy else 0)'
cd ..
if rg -n '/dream-agent/(messages|events|tool-confirm)' frontend/dist; then exit 1; fi
```

The OpenAPI command inventories the actual registered FastAPI application, not
only router source text. The bundle scan is valid only after `npm run build` has
created `frontend/dist`. The local inventories passed again on the current
candidate line; an immutable release artifact is still required for deployment
PASS.

### Historical R9/R10 reproducibility notes

These results explain the earlier checkpoint and are superseded for current
counts by the R17–R26 table above. They must not be combined with the current
candidate to manufacture a headed or immutable-artifact result.

- The final broad backend command was:

  ```bash
  cd backend
  env -u DATABASE_URL -u TEST_DATABASE_URL \
    -u ANTHROPIC_API_KEY -u ANTHROPIC_AUTH_TOKEN \
    -u OPENAI_API_KEY -u DASHSCOPE_API_KEY \
    PYTHONDONTWRITEBYTECODE=1 PYTHONASYNCIODEBUG=1 \
    INK_LOAD_DATABASE_URL_FROM_ENV_FILE=0 \
    INK_RUN_DATABASE_RUNTIME_PG_TEST=0 \
    .venv/bin/python -m pytest -q -ra -p no:cacheprovider tests \
    --ignore=tests/test_api_endpoints.py \
    --ignore=tests/test_database_postgres_runtime.py \
    --ignore=tests/test_postgres_runtime_services_integration.py \
    --ignore=tests/test_real_cli_drama_forge.py \
    --ignore=tests/test_real_cli_plugin_install.py \
    --ignore=tests/test_gateway_claude_agent_adapter.py
  ```

- Backend broad command used the repository `backend/.venv`, unset provider and
  database credentials, enabled `PYTHONASYNCIODEBUG=1`, and excluded real-model,
  unavailable PostgreSQL-runtime and unrelated gateway-adapter suites. It
  completed in 128.45 seconds with `1887 passed, 13 skipped, 615 subtests
  passed`; the 93 warnings were existing FastAPI lifecycle and UTC-datetime
  deprecations.
- Static schema verification recorded manifest SHA
  `6116654affbcb143247851f08a1a32c0191ae54e995d17fd62f56b49d7183399`:
  source 48 tables/567 columns/78 indexes/25 triggers and PostgreSQL target 48
  tables/569 columns/82 indexes/25 triggers. Cross-interpreter gzip output is
  deterministic.
- The four browser tests cover active Dream↔Chat handoff, failed/unknown Stop,
  pre-output disconnect/failure, partial-output failure, reload, history
  de-duplication and exactly-one terminal. Exhaustive confirmation, subagent,
  chunk-splitting and Observer variants remain in focused contract/backend
  suites; this is why the 14-ID release matrix remains open.
- No real model or external provider was called. No local PostgreSQL server,
  Redis server or corresponding DSN was available, so live migration ownership,
  concurrent CAS and Redis Lua/cross-process rolling-upgrade behavior remain
  environment-bound gaps. Deterministic SQL/static/fake-client tests are the
  substitute evidence, not a claim of live-infrastructure equivalence.
- That sentence records the R9 environment only. The R10 worktree now declares
  `redis>=5,<8`, and the isolated live Redis run described above passed 4 test
  methods plus 2 RESP2/RESP3 subtests. Real PostgreSQL remains open. Redis
  rolling deployment and arbitrary-worker HTTP routing also remain open because
  the adapter does not own active-turn/status/Stop/confirmation routing.
- The old R9 worktree recorded 4/4 headed convergence tests. That historical
  result is superseded by the current R41 record below.

## R41 corrected-integration verification (2026-08-12)

| Gate | Current result |
|---|---|
| Dream backend | `1952 passed, 22 skipped, 654 subtests passed` |
| Frontend source/unit contracts | `338 passed`, one worker |
| Frontend static/build | TypeScript + Vite production build PASS; ESLint zero errors and 21 pre-existing Hook warnings |
| Admin | `378 passed`; ESLint and Next production build PASS |
| Configured PostgreSQL | Drizzle `34/34` current; zero legacy lifecycle rows in run/transition data; one `dream.workflow.no-continuing.v1` capability |
| Disposable PostgreSQL cutover | fresh, legacy 06/07, legacy-row normalization, drift rejection, idempotency and concurrent migrator PASS |
| Real provider | one `hy-preview` request resolved/provider-reported as `hy3-preview`; HTTP 200, settled, one finish, two visible history rows, ledger conservation PASS |
| Browser | S01-S10 headless `10/10`; visible `--headed --workers=1` `10/10` |
| Cleanup | real-data source fingerprint unchanged; owned database/container/volume/ports/private clone removed |

The real-provider proof uses a read-only logical snapshot of the configured
PostgreSQL data and creates its actor/thread only inside the private clone. It
therefore validates real schema/data shape, gateway entitlement/accounting and
the real model without modifying the source business rows. The headed browser
lane uses the strict deterministic API harness to exhaustively exercise
Dream/Chat switching and lifecycle races; it is intentionally separate from the
single paid/provider request. Neither result is presented as production load,
staging or canary evidence.

## R42 application-service and turn-entry verification (2026-08-12)

| Gate | Current result |
|---|---|
| Complete backend repository tests | `1954 passed, 22 skipped, 651 subtests passed` from explicit `backend/tests` collection |
| Application ownership | Launch, Run, Artifact, Episode and Confirmation routes inject separate services; former broad gateway symbols have zero production matches |
| Agent turn entry | `run_streaming()` is the only public start; same-turn completion contract and AST guard pass |
| Dream launch structure | Four launch modules contain zero nested function/lambda definitions; dispatch and runtime preparation are named classes |
| Protected SDK runner | `git diff -- backend/libs/claude_agent_kit/server/agent_runner.py` is empty |
| Static integrity | Changed Python compiles; production legacy-symbol scans and `git diff --check` pass |

An unscoped backend-root pytest attempt is not a product failure: it recursively
collected 629 duplicate `test_basic.py`/`test_exec.py` copies inside real
`backend/data/agent-workspace` plugin workspaces and stopped at import-file
mismatch. Those user/runtime data directories were not deleted or modified. The
repository-owned suite is the explicit `backend/tests` boundary recorded above.
No frontend, provider, database migration or browser behavior changed in R42,
so the R41 real-model/UI evidence remains the applicable wire-level evidence.

## Fake-provider, isolation and cleanup contract

- Backend and E2E tests inject a deterministic fake provider/runner; any attempt
  to reach a real model or external provider fails the test. No credential is
  required or read.
- Every test run creates a unique temporary database and workspace root using
  pytest `tmp_path`/temporary-directory fixtures or the Playwright harness's
  per-run output directory. It never reads or writes the developer database,
  normal workspace or another worker's directory.
- Servers bind an OS-assigned port, publish it through the test harness and
  register every server/browser/child PID. Teardown runs in `finally`/fixture
  finalizers on pass, failure and Ctrl-C: close browser/context, stop HTTP
  servers, close factory, cancel and gather producer/dispatch/Observer tasks,
  close DB connections, then remove the temporary root.
- The test process asserts zero registered live PID, open listener, EventBus
  subscriber, confirmation Future/policy and Coordinator turn handle before
  exit. Ordinary sinks must also leave zero live tasks. The explicit
  cancellation-swallowing sink test instead must prove bounded return, lease
  revocation and non-zero detached diagnostics until the fixture releases the
  task; the test then releases it and verifies final cleanup.

## Evidence record

For every P0/P1 row, append or link a record with this schema:

| Field | Required value |
|---|---|
| Requirement/test ID | Stable ID such as `S09` or `SEC-BIND-07` |
| Commit | Full Git SHA |
| Environment | Local/CI/staging/production and immutable build ID |
| Command/action | Exact reproducible command or browser steps |
| Result | PASS/FAIL, counts and relevant bounded metrics |
| Artifact | CI URL, report, trace, screenshot or log query |
| Reviewer | Named owner and date |
| Notes | Known limitations; no secrets or personal IDs |

## Final go/no-go checklist

- [x] Final R27 architecture/security review ACCEPT after R28 verifier closure.
- [x] S01–S10 browser scenarios pass in R19 and R30 headless Chromium.
- [x] S11–S14 Observer/single-terminal/migration scenarios pass in backend,
      OpenAPI and source acceptance; they are not browser tests.
- [x] Permission, retry-leaf and confirmation matrices pass locally.
- [x] Existing Dream-files authorization/threadId contract passes and no new
      re-entry endpoint/field appears.
- [x] Exactly-one terminal and partial failure tests pass.
- [x] Confirmation register-before-publish, atomic resolve and all-path cleanup
      tests pass.
- [x] Observer/Coordinator equivalence, isolation and ordinary-sink cleanup tests
      pass without new persistence; the cancellation-swallowing fixture proves
      bounded detach diagnostics and is released before test teardown.
- [x] Observer operation classification/hash privacy and authorized optional
      Dream-files `agentActivity` tests pass; the field never controls lifecycle,
      and page copy rejects terminal/confirmation/subagent/tool hints.
- [x] Workflow owner transition tests pass.
- [x] Accessibility and cross-surface switch tests pass headlessly.
- [x] Shared visibility/private-row/zero-part/export snapshots pass on both
      surfaces.
- [x] Stop eligibility, failure/timeout/`running=true`, subagent-history and
      unmount/navigation input-lock tests pass.
- [x] TypeScript, ESLint, build and frontend contracts pass; final documentation
      `git diff --check` is an R27 closeout action.
- [x] Every-byte/merge/CRLF/Unicode/Chinese/newline/special-character and Admin
      no-buffer gates pass.
- [x] Headless Chromium passes with semantic waits only.
- [x] Current-candidate headed Chromium S01–S10 passes 10/10 with
      `--headed --workers=1` and semantic waits only (R32).
- [x] Fake provider, isolated temporary DB/workspace and zero-residual-process/
      task/Future/subscriber cleanup gates pass.
- [x] Protected runner diff is empty and runner/service focused regressions pass.
- [x] R42 sole public `run_streaming` entry, same-turn completion, explicit
      application services and closure-free Dream launch structure pass.
- [x] Dream launch without a deployment label executes the same production
      path; production-source scan contains no deployment-name business gate;
      Admin 0034 normalizes receipt/session placement to `local` and publishes
      `dream.runtime.local-placement.v1`.
- [x] Shared SDK option assembly pins Claude Code native request retries to
      three; a real local Claude CLI contract survives three transient 429
      responses on the same request boundary without adding an Agent turn loop.
- [ ] The latest full headed real-model launch is blocked after its first
      settled `hy3-preview` request by the configured principal's hard
      `DAILY_TOKEN_LIMIT_EXCEEDED` Gateway policy. Source data and owned
      resources remain unchanged; no permission/limit override is accepted as
      a substitute for this external quota prerequisite.
- [x] Proxy/reconnect functional gates pass.
- [ ] Production performance/load baseline and threshold gates remain unrun.
- [x] Redis isolated adapter and Gateway loopback suites pass; this does not claim
      multi-worker/pod HTTP support without a separate distributed active-turn/
      status/Stop/confirmation/routing design.
- [x] R28 implementation closes incremental-text/final-text and projected-history/
      private-discriminator false-positive paths: 128 tests + 37 subtests pass,
      with no second provider request or runtime/runner edit.
- [x] Independent R28 re-review ACCEPT; 19 directed tests passed with no new
      false-positive path, privacy leak, blocker or provider call.
- [ ] Staging/canary and immutable artifact retention are unrun.
- [ ] Rollback exercised against recorded immutable builds.
- [x] Local source/OpenAPI/bundle scans prove old protocol absent.
- [x] Legacy code/routes/contracts/bridges and obsolete tests are hard-deleted.
- [x] R27 documentation source/link/status/diff scans and independent fresh-
      reader test complete; the reader recovered all ten architecture, security,
      evidence and residual-gate questions with no privacy leak or broken link.
- [x] R30 current-worktree focused backend, headless Chromium, TypeScript, ESLint,
      build, source/OpenAPI/bundle, protected-runner and cleanup re-audit PASS.
- [x] R41-owned Playwright/controllers/browser/backend listeners are gone after
      headed execution; port 8765 is free. The pre-existing user-owned Vite PID
      on 5173 was identified, reused only as a repository fact and left running.
- [ ] Admin entitlement-enforcement residual risk is accepted or separately
      remediated; R26 itself required `entitlementBound=true` and did not exploit
      the gap.
