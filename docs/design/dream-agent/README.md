# Dream Agent conversation convergence design

> Status: **R41 corrected integration and business design ACCEPT**.
> The current candidate passed full backend/frontend/Admin checks, disposable
> and configured PostgreSQL checks, one real `hy3-preview` proof, and S01–S10
> in both headless and visible Chromium with one worker. The B01–B21 business
> interaction catalog and all 58 Mermaid blocks parse successfully. Production rollout remains separate because
> staging/canary, immutable rollback and production load were not run.
> [Diagnosis](./diagnosis.md) is intentionally pinned to the historical
> `platform@a506c83d5fa9a07d37afa10b2fb947c05c9c7408` baseline. All other current
> implementation claims refer to the 2026-08-12 migration worktree. R17–R41
> executable evidence is recorded in
> [Testing and acceptance](./testing-and-acceptance.md). It is not staging,
> canary, immutable-build rollback or production-load evidence.

## Decision

Dream is a product surface over one Chat thread, not a second public
conversation protocol.

1. Dream conversation history, live output, reconnect, tool confirmation and
   stop must use the canonical Chat thread contracts.
   Dream composes the existing `ChatPanel`; `ChatPanel` remains the sole
   `useChat` and live reducer owner.
2. The Dream browser must not connect to an independently filtered
   `/dream-agent/events` stream after migration.
3. A Dream Observer may consume server-side facts and derive Workflow Run or
   business projections. It must not proxy, redact, fork, reorder or terminate
   Chat conversation events. The current implementation consumes only normalized
   runtime events and stores process-local latest hints; the existing
   actor-scoped Dream-files REST response may expose a matching content-free
   hint as optional display-only `agentActivity`, but it has no durable owner
   wiring or push channel. The Dream page renders only
   `content_generation`/`workflow_operation` activity and
   `reconcile_requested` copy from that field. Terminal, runtime confirmation,
   subagent and generic-tool presentation remains canonical `ChatPanel` state.
4. Conversation lifecycle and Workflow Run lifecycle are related by immutable
   run/thread provenance, but neither is inferred from the other.

This decision deliberately supersedes the independent Dream public SSE
architecture introduced by Git commit `61f70fc52ee6c557bd7294d65969a7f672851e4d`
and later isolated behind `DreamStreamAdapter` in commit
`b5b986c6f1cb89b73b139b07eef18a2ec80937e6`.

## Status vocabulary

Every document in this directory uses the following labels:

| Label | Meaning |
|---|---|
| **Pinned baseline** | Directly supported by `platform@a506c83`; historical, not the current worktree. |
| **Verified worktree** | Directly supported by source or tests present in the 2026-08-11 migration worktree. |
| **Local acceptance PASS** | Executed against the current worktree or an owned disposable clone; not deployment evidence. |
| **Decision** | Normative target accepted by this design set. |
| **Proposed** | Required implementation that does not yet exist. |
| **Pending acceptance** | Implementation exists, but the required release evidence has not been recorded. |
| **Migration-only** | Temporary compatibility behavior with an explicit removal gate. |
| **Open** | A choice or risk that still requires owner approval. |

Passing acceptance evidence, not document publication or file existence,
changes a pending release item to PASS.

## Document map

| Document | Purpose | Authority |
|---|---|---|
| [Diagnosis](./diagnosis.md) | Pinned pre-migration call chains, Git split evidence, callers and failure modes | Historical evidence baseline |
| [Architecture](./architecture.md) | Target components, contracts, ownership and permission boundaries | Normative architecture |
| [Business interaction design](./business-interaction-design.md) | B01–B21 complete Dream business catalog, authoritative owners, side effects, open product decisions and one Mermaid sequence per capability | Normative business behavior |
| [Project / Episode Artifact contract](./project-episode-artifact-contract.md) | Stable identity, sealed snapshot, revision, read/write, reconcile and Admin review contract | Normative cross-system concept |
| [Dreamflow tool boundaries](./dreamflow-tool-boundaries.md) | Complete Dreamflow action/tool/confirmation/Agent boundary and sequences | Normative workflow interaction |
| [Interaction design](./interaction-design.md) | Canonical thread send, reconnect, tool confirm, Stop, Observer and migration scenarios | Normative Agent/browser runtime behavior |
| [Lifecycle](./lifecycle.md) | Independent Chat-turn and Workflow Run state machines | Normative state semantics |
| [Observer design](./observer-design.md) | Failure-isolated runtime hints, bounds and current sink limitations | Normative Observer boundary |
| [Migration plan](./migration-plan.md) | Sequenced implementation, compatibility, rollback and deletions | Delivery plan |
| [Testing and acceptance](./testing-and-acceptance.md) | Required tests, evidence and go/no-go gates | Release contract |
| [Design review](./design-review.md) | Formal findings, closure evidence and sign-off | Review record |
| [Prompt rounds](./prompt-rounds.md) | Reproducible artifact-level questions and decisions | Design trace |

## Pinned baseline and current worktree at a glance

| Concern | Pinned `a506c83` baseline | Current migration worktree |
|---|---|---|
| Browser conversation stream | Dream uses run-scoped `/dream-agent/events`; Chat uses thread `/stream` | Dream and Chat both use canonical Chat SSE; the run-scoped conversation routes are removed |
| Conversation history | Dream receives a filtered run snapshot | `threadSessionHydration.ts` reads canonical thread history/status for both surfaces |
| Event projection | `DreamStreamAdapter` redacts and remaps normalized events | The adapter is deleted; no replacement Dream conversation protocol exists |
| Tool confirmation | Dream has a run-scoped endpoint; canonical store holds only a Future | `tool_confirmation_store.py` atomically registers bounded policy + Future and resolves exact active identity |
| Follow-up dispatch | Dream message service derives run/thread context and dispatches out of band | Standard Thread dispatch; `assemble_context` resolves trusted Dream context from actor + thread |
| Re-entry thread binding | Actor-scoped Dream-files already includes `threadId` | The wrapper reuses that field; no new re-entry endpoint or binding identifier was added (`agentActivity` is optional display metadata) |
| Browser live state | ChatPanel owns `useChat`; Dream owns a separate hook/parser/reducer | `StoryWorkspaceDreamThreadChat.tsx` composes `ChatPanel`; hydration/runtime helpers are shared without a Provider |
| Workflow status | Five-second REST polling is authoritative | Durable REST and explicit post-settlement refresh remain authoritative; optional `agentActivity` is informational and no Observer-to-owner transition sink is wired |
| Observer | No run-bound Dream lifecycle Observer | `dream_lifecycle_observer.py` provides an off-path per-turn classifier, safe operation/hash projection, coordinator and bounded 256-entry `(run, thread, actor)` latest-hint sink with generation ordering |
| Visibility | Chat can synthesize empty text for zero parts | Shared hydration filters private rows and drops zero-visible-part rows |

## Authority order

For this migration, conflicts are resolved in this order:

1. Executable source and tests in the current worktree establish implemented
   behavior.
2. The pinned revision establishes only the historical diagnosis and rollback
   baseline.
3. This directory establishes remaining normative requirements and release
   acceptance criteria.
4. `docs/design/story-workspace/workflow-execution.md`
   remains authoritative for durable Workflow Run truth and retry behavior where
   it does not prescribe an independent Dream conversation stream.
5. Deleted Story Workspace execution/review records remain recoverable in Git
   history but are not target-design dependencies.
6. Git baseline `a506c83` preserves the deleted legacy two-protocol documents
   (`docs/chat-dream-agent-interaction-design.md` and
   `docs/design/sse-streaming-interaction-design.md`) as migration evidence;
   neither deleted file is a target-design dependency.

## Non-negotiable invariants

- The browser never authors a trusted Dream run context.
- A server-derived `(actor_id, workspace_id, workflow_run_id, thread_id,
  deck binding revision)` must agree before a Dream-bound Chat turn starts.
- Multiple rows on one actor/thread may form one legal retry chain. The server
  follows `retry_of_run_id` and selects the single unsuperseded leaf attempt;
  multiple independent leaves, a broken/cyclic chain or frozen-source mismatch
  fails closed with 409.
- Chat thread ownership is checked on every history, status, stream, stop and
  confirmation request.
- Dream re-entry uses the existing actor-scoped `/dream-files` `threadId`; this
  migration adds no binding endpoint or binding identifier. Optional
  `agentActivity` cannot select a thread or run.
- `ChatPanel` is the only `useChat`/live reducer owner. No app-wide
  `ClaudeThreadSessionProvider`, second runtime controller or Dream parser is
  introduced; only minimal hydration is shared.
- Before any approval frame, the per-turn confirmation store atomically owns a
  bounded server policy and Future keyed by `(threadId, turnId, toolCallId)`;
  resolve and cleanup are atomic and browser fields cannot create policy.
- Private guidance, Dream business-confirmation and server episode-envelope rows
  never render/export. Zero-visible-part rows create no blank bubble.
- Observer output contains no raw prompt, reasoning, tool input, credentials or
  filesystem paths.
- Observer operations expose only safe tool/subagent/content/workflow classes,
  bounded state and an optional SHA-256 correlation value. Dream-files attaches
  a hint only after existing actor/run/thread authorization and an exact
  internal actor match; highest generation/sequence wins and neither guard is
  serialized. No match or lookup error leaves `agentActivity` absent. The business-page view model ignores
  tool/subagent/waiting/turn-terminal hints so the field cannot shadow
  `ChatPanel`.
- Observer failure cannot fail, delay or mutate the Chat stream. The Observer
  does not create a second durable event log; existing owning services and their
  database writes remain the durable truth.
- `DreamObserver`, registered through `SessionObserverRegistry`, revokes the
  lease, unsubscribes and performs
  bounded cancellation/await on context failure, terminal/sentinel, Stop, task
  exception, session eviction and factory close. A sink that swallows
  cancellation can be detached and tracked after the bound; the current default
  sink is process-local and performs no durable owner write.
- `backend/libs/claude_agent_kit/server/agent_runner.py` is protected. SDK
  classification/tool policy/cancellation stay there; `ClaudeAgentService`
  keeps normalized events, persistence and terminal ordering.
- Workflow transitions require owning-service facts; `finish`, EOF or assistant
  text alone is never proof that a Dream workflow completed.
- The worktree removes old endpoints; that artifact may be deployed only after
  the traffic, contract and rollback gates in [Migration plan](./migration-plan.md)
  pass.

## Implementation status

| Capability | Status |
|---|---|
| Shared normalized server EventBus and canonical Chat thread endpoints | Verified worktree |
| Dream wrapper composing `ChatPanel` plus `threadSessionHydration.ts` | Verified worktree |
| Server-side Dream retry-leaf resolver during context assembly | Verified worktree in `dream_thread_binding.py` + `ClaudeAgentService.assemble_context` |
| Canonical bounded confirmation policy/Future store | Verified worktree in `tool_confirmation_store.py` |
| Registry-owned `DreamObserver` and bounded latest-hint sink | Verified worktree through `SessionObserverRegistry`; failures remain outside the Agent stream |
| Optional shared Redis EventBus runtime dependency | `redis>=5,<8` declared; isolated Redis and Gateway loopback checks PASS for known-turn stream/replay/terminal semantics |
| Direct caller replacement and hard deletion of the old protocol | Local source, OpenAPI and built-bundle inventories PASS; immutable release artifact and rollback exercise pending |
| Backend and frontend regression | R41: backend 1,952 passed / 22 skipped / 654 subtests; frontend 338 unit/contract tests plus TypeScript, lint and production build PASS |
| Named cross-layer interaction matrix | R41: S01–S10 PASS headless and visible headed Chromium with semantic waits and one worker; S11–S14 remain covered by backend/source/OpenAPI acceptance |
| Production-shaped fake-provider chain | R17 full owned PostgreSQL/Admin/fake-provider chain PASS with balanced ledger, zero external calls and exact cleanup |
| Admin canonical artifact contract | R20: 28 tests and Admin TypeScript PASS after the scoped stale assertion correction |
| Real-proof verifier and isolation | R24: 24 tests plus read-only SQL probe PASS; R25 provider-free clone and injected-SIGINT cleanup PASS |
| One bounded real Gateway request | R26: exact `hy-preview` → resolved/provider `hy3-preview`, entitlement-bound HTTP 200, terminal/SSE/persistence observations, balanced ledger, source integrity and cleanup PASS; R28 hardens two future success predicates |
| Post-proof verifier closure | R28: 128 tests + 37 subtests PASS; nonblank `message-final`, one start / one-or-more meaningful deltas / one end with strict tail, private visibility/dispatch denial and exact visible projected history are mandatory; no provider/runtime/runner change |
| Independent R28 re-review | ACCEPT; 19 directed tests PASS with no new false-positive path, privacy leak or blocker and no provider call |
| R41 database/model/browser gate | Admin cutover and configured capability PASS; one exact `hy-preview` → `hy3-preview` request PASS; S01–S10 headed `10 passed (15.8s)` and sequential headless PASS |
| Staging, canary, immutable rollback, production load | Not run; deployment acceptance remains pending |

Redis does not change the deployment-control boundary: active turn/status/Stop/
confirmation/HTTP stream routing remain process-local. The current backend runs
one uvicorn worker and is deployed with `max-instances=1`; the isolated Redis
PASS must not be cited as multi-worker/pod HTTP reconnect support.

## R27 evidence boundary

The R26 real request used a fresh generic canonical Chat thread owned by a
clone-only entitled user. That user had **zero eligible terminal Dream threads**,
so the result proves the shared Chat runtime, Admin Gateway, exact model routing,
observed terminal/persistence behavior and accounting path. It does **not** prove
terminal Dream workspace binding. No prompt, provider response, session ID,
token, URL, credential or private source data is part of this design record.

The pre-existing Admin entitlement-enforcement gap remains a residual risk. The
R26 proof did not exploit it: the verifier required the settled request receipt
to report a non-null subscription entitlement binding (`entitlementBound=true`).
Formal source review still found one canonical runtime/protocol/reducer,
off-path non-authoritative observation, preserved actor/thread/run/Deck
authorization and no change to
`backend/libs/claude_agent_kit/server/agent_runner.py`.

Independent review after R26 found two verifier false-positive seams: future
success must explicitly require non-empty ordered incremental/final text and a
fully projected two-row public history with additional private discriminators
denied. The completed call did observe one text start/delta/end and a non-empty
persisted assistant, but its disposed clone cannot supply a retroactive final-
text boolean. R28 is therefore test/verifier-only and must not issue a second
provider request.

R28 has implemented those requirements and passed 128 tests plus 37 subtests
without contacting a provider or changing product runtime/`agent_runner.py`.
Its independent read-only re-review returned ACCEPT after 19 directed tests,
with no new false-positive path, privacy leak or blocker and no provider call.

## Updating this design set

When acceptance evidence lands, update the evidence table in
[Testing and acceptance](./testing-and-acceptance.md) with a commit, exact test
command and artifact. Then update status labels surgically. Do not rewrite the
diagnosis to make the old architecture disappear; it is needed to audit the
migration and execute rollback.
