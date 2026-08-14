# Dream Agent design prompt rounds

> Status: historical prompt and evidence trace through R35. This records inputs,
> questions, measured results and artifact changes. It is not a transcript of
> hidden reasoning; current implementation and acceptance claims still require
> the source and executable evidence linked by the canonical design documents.

## Purpose

Future implementers and reviewers should be able to reproduce why the design
changed, challenge an assumption with code evidence, and know which documents
must change. Each round below has an observable question, evidence set, decision
and exit condition.

## Execution rounds

This table records the actual requested rounds. “Complete” means the round's
artifact was produced, not that proposed code was implemented.

| Round | Goal | Scope | Completion standard | Actual result | Unverified inference |
|---|---|---|---|---|---|
| R1 — diagnosis | Locate the real Chat/Dream split and document cleanup boundary | Read-only Git, code, docs and sibling proxy evidence | Exact commits, paths/lines, callers, conflict/keep/archive/delete and recoverability | Complete; captured in `diagnosis.md` | Production traffic and stakeholder intent were not measured |
| R2 — design | Replace independent Dream public SSE with Chat thread SSE and define Observer/business projection | Only `docs/design/dream-agent/**` | Ten requested files, 14 Mermaid scenarios, complete states, permissions, migration/deletion and acceptance | Complete as proposed design; no implementation claimed | Visibility approval, SLO baselines and future component behavior remain unverified |
| R3 — formal review | Independently challenge R2 against code, security, lifecycle and removability | This design set plus pinned repository evidence | Reviewer fills findings, decision and sign-off in `design-review.md` | Complete: **CHANGES REQUIRED / 修改后接受** with DR-001–DR-009 | Implementation permission remains withheld until all findings are closed and re-reviewed |
| R4 — review-blocker closure | Revise normative design to close DR-001–DR-009 without production-code edits | Every file here except reviewer-owned `design-review.md` | Each DR has a precise target contract/location; R4 static checks pass; status awaits independent re-review | **已修订待复审** | No target code/test/operational result is verified; reviewer closure remains pending |
| R5 — independent re-review | Recheck every R3 blocker against the revised normative design | Design set and cited source evidence | Every DR is CLOSED before implementation permission | Complete: **接受，并授权生产实现** | Runtime feasibility and release validation were not yet proven |
| R6 — implementation | Replace the Dream public conversation protocol with canonical Chat runtime composition | Scoped backend/frontend production seams and focused tests | One public protocol, Observer off-path, old callers removed, protected runner untouched | Implemented; integration review remains active | Broad regression/build/browser evidence is reserved for R9 |
| R7 — documentation migration | Remove misleading two-protocol guidance without deleting unique business requirements | Dream/Claude-agent docs, indexes and inbound links | Recoverable deletions, redirected normative links and complete migration table | Complete | External bookmarks and deployed copies are not observable locally |
| R8 — integration race closure | Independently review the assembled migration and close lifecycle races before release validation | Changed production seams plus focused deterministic regressions | No pre-mount settlement loss, cross-thread reconnect bleed, mechanical duplicates or restored Dream runtime | Complete: independent frontend and backend reviews **ACCEPT** | Broad regression/build/browser and real PostgreSQL/Redis evidence remain reserved for R9 |
| R9 — release validation and evidence sync | Validate the assembled candidate without a real model, close deterministic test gaps, and make docs match only measured facts | Backend/frontend/Admin/static/browser suites, focused E2E additions, artifact/source scans and final docs | Required checks pass or every environment-bound gap has an explicit reason, substitute evidence and residual risk; browser tests use semantic waits and leave no owned residue | **Local validation complete; immutable release gates remain open** | Real PostgreSQL/Redis, staging, performance, rollback and a complete 14-ID release matrix remain unverified |
| R10 — requirement-by-requirement completion audit | Re-open the persistent objective, prove every named requirement from current source and executable evidence, and close every locally actionable gap | Current worktree, S01–S14 coverage, backend/frontend/Admin contracts, infrastructure probes, docs and cleanup | Every objective item has direct evidence or an explicit external blocker; S01–S14 are independently discoverable; no second runtime or weakened permission boundary; no new headed run while deferred | In progress; prompt recorded before audit | Headed rerun is deferred by the user; live PostgreSQL/Redis and deployment facilities must be discovered rather than assumed |
| R11 — final candidate validation | Re-run the complete locally executable release gate after the R10 fixes and reconcile the evidence to the exact candidate | Isolated PostgreSQL/Redis, backend/frontend/Admin suites, type/lint/build, named headless Chromium scenarios, source/link/diff/cleanup audits and final design evidence | Every command is reproducible and passes or is reported with an exact external blocker; no real model, no existing database, no fixed sleep, no owned residue and no new headed run | **Failed:** isolated PostgreSQL harness reached the local Admin gateway but `/v1/messages?beta=true` returned 401 before the fake provider; cleanup passed | Root cause and smallest production-faithful fix move to R12; immutable/staging/rollback and current-candidate headed remain external/deferred |
| R12 — local gateway authentication repair | Diagnose and repair the isolated Dream producer chain's Admin gateway 401 without weakening production authentication | Dream backend subject/service-key construction, Admin gateway auth middleware, fake-provider harness and focused cross-repository contracts | The exact 401 is explained by source and executable evidence; the smallest fix preserves issuer/audience/client/scope/user binding; focused and full isolated headless harness pass with zero external provider calls/residue | **Failed after first repair:** the isolated rerun still reached `/v1/models` but `/v1/messages?beta=true` returned 401 before request accounting or the fake provider; all owned resources were cleaned | Removing a resurrected direct token was necessary in focused evidence but not sufficient in the full CLI process; exact outbound Messages authorization remains unproven and moves to R14 |
| R13 — one-way workflow boundary closure | Remove the last path where Dream Workflow status can control the canonical thread runtime | Trusted binding resolution, SDK-init activation replay, terminal/fresh-session contracts and focused review | Terminal workflows no longer inject business activation authority into ordinary Chat turns; active business commands retain authorization; regressions cover four terminal states and fresh-session recovery | In progress; prompt recorded before design/implementation | Exact active-run replay policy must be proven from current activation/session persistence before editing |
| R14 — full CLI gateway authorization trace | Explain the remaining full-harness Messages 401 from the actual subprocess environment and repair only the proven request-construction defect | AgentRunner/Simple client/Claude CLI environment and helper invocation, bounded local capture proxy, Admin canonical-subject authentication and isolated fake-provider harness | A no-secret capture proves which authorization form reaches `/v1/messages`; the smallest fix preserves strict Admin authentication; focused regression and the full isolated headless harness pass with fake-provider requests, gateway accounting, zero external calls and exact cleanup | **Auth defect closed:** real-CLI ambient-credential regression passes; isolated chain produced 32/32 settled HTTP 200 Gateway requests and 32 fake-provider calls, but the producer spec still failed on an earlier transient Dream-files 422 diagnostic | Full harness completion moves to R16; the 401 inference is now executable proof, not an open question |
| R15 — real-data and real-model validation | Validate the converged Dream/Chat path with an actual configured model and representative existing data while preserving isolation and privacy | Local configured data-source discovery, recoverable clone or bounded non-sensitive fixture selection, strict Gateway route, one budget-capped model turn, persistence/business output and cleanup evidence | The real provider is reached exactly through the configured Gateway; one bounded turn completes on representative real data; thread/message/workflow artifacts correlate; secrets and raw private content are not logged; original data is not mutated; owned resources are cleaned; no headed browser | In progress; user explicitly authorized real data/model after R14 began | Exact locally available real-data source and provider budget remain to be discovered; absence of a safe cloneable source must be reported rather than bypassed |
| R16 — transient Dream-files readiness contract | Remove the last headless producer failure without hiding genuine output corruption | Initial Dream page hydration/polling, Dream-files GET readiness semantics, frontend diagnostics, terminal validation and Admin generated-story continuation | “Output not produced yet” is represented as a non-error pending/empty state; malformed output after it should exist remains 422; no retry sleep masks the race; the full isolated fake-provider harness including Admin generated-story passes and cleans up | **Complete:** missing pre-materialization `.dream` is a read-only waiting projection; output-ready/review descendants remain strict; backend 67 + 37 subtests and frontend 6 passed; full-chain proof completed in R18 | Failed/cancelled intentionally allow absent output because they may terminate before first output; this is a verified domain distinction, not a permissive terminal fallback |
| R17 — post-readiness isolated release proof | Prove the R16 contract on a fresh production-shaped local stack before any real-provider request | Owned PostgreSQL, Admin Gateway, Dream API/UI, local fake Provider, producer/Admin headless Chromium, Gateway ledger and exact cleanup | The complete script exits zero; initial hydration emits no application error; producer and generated-story Admin checks pass; all Gateway requests settle one-to-one with fake-provider requests; external calls and owned residue are zero | First attempt exposed an R18 barrel-export startup defect before launch; after R18, the same full script passed producer 1/1, Admin 1/1, 32/32 settled Gateway/fake-provider requests, balanced ledger, zero external calls and exact cleanup | No remaining fake-provider full-chain defect is inferred; broad same-candidate regression moves to R19 |
| R18 — Dream launch first-render diagnosis | Explain and close the new isolated producer failure without masking a real launch-page defect | Producer spec initial navigation, auth bootstrap/local storage, router/React render, Vite readiness, console/HTTP diagnostics and semantic wait | Failure evidence identifies the rendered route/state; a product or test-harness fix is minimal and deterministic; no fixed sleep or weakened assertion; focused launch and full R17 chain pass | **Complete:** safe diagnostics proved an empty React root caused by a stale barrel re-export; one export was removed, TypeScript and 12 focused tests passed, then the complete R17 chain passed | The implicit five-second wait was not the cause and was not increased |
| R19 — exact-candidate broad local regression | Re-run every locally executable non-headed release gate after R13–R18 | Backend broad/focused suites, frontend unit/type/lint/build, Admin contracts/build, named S01–S10 headless browser plus S11–S14 backend/source scenarios, source/docs/diff/protected-file/cleanup audits | All tests and static/build gates pass on the same worktree or have an exact non-product external blocker; no old Dream protocol production caller, no runner edit, no owned residue and no headed run | Complete: backend 1,927 passed / 17 skipped / 655 subtests, focused 687 passed, Redis/Gateway loopback PASS; frontend 340 plus type/lint/build; S01–S10 headless Chromium and S11–S14 backend/source acceptance PASS | Current-candidate headed S01–S10, staging/canary, immutable rollback and production load remain outside R19 |
| R20 — Admin canonical artifact-status assertion sync | Close the sole deterministic R19 red test without changing the correct production query | Clean sibling Admin `repository.test.ts` assertion plus its generated-story contract selector and TypeScript | Test expects the canonical derived compatibility SQL, all 28 generated-story contracts and typecheck pass, and no unrelated sibling file changes | Complete: one assertion changed; 28/28 contracts and Admin TypeScript passed; production source stayed clean | No production behavior change was required; schema and repository source already agreed |
| R21 — isolated real-data real-model Gateway proof | Prove the canonical Chat thread path works against a privacy-preserving clone of real data through the existing Admin Gateway with exact model `hy3-preview` | Read-only source preflight, disposable PostgreSQL/workspace clone, Admin Gateway and Dream API, one bounded canonical thread turn, SSE/persistence/model/ledger/original-integrity assertions, exact cleanup | One request reaches and resolves exact `hy3-preview`, emits exactly one terminal event, persists canonical thread messages, settles Gateway accounting, preserves the original data byte/logical identity, and leaves no owned resources; otherwise stop with exact blocker and no fallback | In progress; optimized validation prompt recorded before discovery or execution | Provider entitlement and exact upstream catalog resolution remain unverified until the preflight; no private prompt/history/model output may enter logs or docs |
| R22 — distinguish public alias from selected upstream model | Preserve the production catalog while proving the user's exact `hy3-preview` selection without fabricating an alias or falling back | Source/clone catalog, saved selection, canonical request alias, Gateway request resolution and upstream provider identity | Submit only the configured callable alias `hy-preview`; prove its unique enabled upstream, every correlated `resolved_model`, and provider request model are exactly `hy3-preview`; reject every other mapping | In progress; revised prompt recorded after read-only discovery and before any provider call | Source has no public alias named `hy3-preview`; renaming the clone alias would make the proof less production-shaped and is therefore rejected |
| R23 — source-compatible PostgreSQL clone tooling | Repair the provider-free clone preflight after PG18 client output proved incompatible with the required PG16 target | Dump/restore client version selection, binary-safe owned dump, PG16 source/target parity, unchanged R22 safety gates | Use PG16 `pg_dump` and `pg_restore`, restore byte/logical source data into the owned PG16 clone, then reach catalog/subscription preflight with no provider call; retain exact cleanup | Complete: source/dump/target/restore majors all 16; logical fingerprint matched and the complete provider-free preflight passed | Provider behavior remains intentionally untested until the separately planned one-call round |
| R24 — harden the real-proof evidence contract | Close independent review findings before the first provider call | Legacy TEXT JSON casts, strict SSE parsing/order/terminal checks, durable metadata/session equality, sanitized subprocess failures | Provider-free regression remains green; a later real success can pass only with valid ordered SSE, exact persisted session/model/visibility facts, and no raw diagnostic disclosure | Complete: 24 focused/adjacent tests passed, read-only PostgreSQL parsed the receipt SQL, and provider-free preflight remained green | Real JSON/session semantics require the isolated real turn; no provider was called in R24 |
| R25 — fail-safe clone isolation and interruption cleanup | Close the runner safety findings discovered during R24 review before any provider call | Credential transport, isolated Admin checkout, clone-user fixture eligibility, signal races, unconditional owned-resource cleanup and sanitized failure reporting | No source credential appears in argv; original checkouts/data stay unchanged; only the clone user is considered for fallback; SIGINT/SIGTERM cannot strand the uniquely named container, volume, processes or private runtime; provider-free regression passes | Complete and independently ACCEPTED: injected SIGINT exited 130 with every cleanup assertion true; full provider-free clone passed with zero eligible clone-user terminal threads, zero provider calls and exact cleanup; reviewer tests/probes passed | Turbopack rejects the external dependency link, so the disposable Admin checkout uses its supported webpack dev mode; malformed future source-URL initialization is a non-blocking hardening suggestion |
| R26 — one bounded real `hy3-preview` proof | Execute the user-authorized real model once through the production Gateway contract after every provider-free gate and review is green | Read-only real-data clone, clone-only entitled subject, one canonical thread turn, strict SSE/persistence/Gateway/ledger/model receipts and unconditional cleanup; no browser | Exactly one Gateway request uses alias `hy-preview`, resolves and is provider-reported as `hy3-preview`, settles successfully, persists one user and one assistant with matching SDK session, emits one terminal finish, prints no content/secrets, leaves source/resources unchanged; no retry or fallback on failure | Complete in one request: exact model/entitlement/ledger/source/cleanup passed and the receipt observed incremental text, one terminal, matching session and non-empty persisted assistant; post-run review assigned two future verifier predicates to R28 | Headed remains deferred; generic fixture is not terminal Dream binding; the removed clone cannot supply a retroactive final-text boolean and no second call is permitted |
| R27 — evidence reconciliation and reader-tested final review | Make every Dream design/migration/acceptance document match the exact implemented candidate and measured R17–R28 evidence | `docs/design/dream-agent/**`, formal review, dead-link/source/status audits and fresh-reader testing; no provider/browser | No stale dual-protocol or pending local-validation claim remains; final review separates measured pass, deferred deployment gates and residual risks; fresh readers can recover architecture, security and evidence boundaries | Complete: documentation/source/link/status/diff reconciliation PASS, formal review ACCEPT, and a no-context reader recovered all ten requested facts with no privacy leak or broken link | Headed/staging/canary/immutable rollback/load remain explicitly unrun; Admin entitlement enforcement remains a disclosed residual risk |
| R28 — close post-proof verifier false-positive gaps | Strengthen the evidence predicate found incomplete by the final independent review without issuing a second provider request | Real-turn verifier and focused contract tests only: incremental text/final text, private discriminators and client-visible REST history; then independent re-review | Success requires non-empty `message-final.text`, ordered text start/delta/end, no private visibility/dispatch metadata, and two non-empty canonical projected history rows; sanitized output remains content-free | Complete and independently ACCEPTED: 128 tests + 37 subtests, then 19 directed review tests; no provider/runtime/runner change and no new false positive, leak or blocker | The completed R26 receipt measured one start/delta/end and non-empty DB assistant, but the removed clone prevents retroactively adding a final-text boolean; no second call was made or needed for verifier closure |
| R29 — final no-provider/no-browser audit | Execute the last reproducible audit without another model call or browser | Document links/status, legacy-protocol production references, shared Chat runtime, protected-runner hash, repository/Admin diff checks, resource and Python 3.12 cache cleanup | Every check has explicit evidence, every unrun item remains labelled, generated caches are moved recoverably, and no provider/browser/protected-runtime/user-resource boundary is crossed | Complete: relative-link/status and fresh-reader review passed; production legacy-protocol scan was empty; Dream owns no second `useChat`; protected runner matched HEAD; both diff checks and owned-resource cleanup passed; four exact generated caches moved recoverably | No provider or browser was invoked; headed/deployment/load gates remain explicitly deferred |
| R30 — persistent-goal completion audit | Audit every objective against the authoritative current worktree and close all non-headed gaps without narrowing completion | Runtime/protocol/Observer/persistence/Flow/docs/complexity source evidence; focused backend, headless Chromium, type/lint/build, OpenAPI/bundle/protected-runner/cleanup checks | Each objective is directly evidenced or explicitly incomplete; no real model or headed run; the goal remains active while its required headed gate is user-deferred | Authorized non-headed product checks pass: 71 tests + 37 subtests, S01–S10 10/10 headless, type/lint/build, zero legacy OpenAPI/bundle routes, runner hash and diff checks; R30-owned artifacts/controllers/listeners cleaned | Persistent goal remains **not complete** at the required headed gate; 58 older macOS `UEs` Playwright processes resisted exact TERM/KILL, and deployment/Admin entitlement risks remain separately disclosed |
| R31 — browser evidence-scope correction | Reconcile every S01–S14 headless/Chromium claim with actual Playwright and pytest discovery | Design/acceptance/history documents, Playwright `--list`, pytest collection; no product code or headed execution | S01–S10 are labelled browser evidence; S11–S14 are labelled backend/source/OpenAPI evidence; the cross-layer 14-ID matrix remains intact without overstating browser coverage | Complete: Playwright lists exactly 10 S01–S10 tests; pytest collects the S11–S14 acceptance classes; all current design claims and commands are layer-accurate | Current-candidate headed scope is explicitly S01–S10 and remains user-deferred |
| R32 — final visible-browser acceptance | After the user reboot and explicit authorization, execute the exact current-candidate S01–S10 suite visibly and close the persistent local gate | Playwright preflight/discovery, headed Chromium with one worker and semantic waits, post-run process/port/report cleanup, fresh S11–S14 and legacy/runtime checks, synchronized acceptance evidence | S01–S10 pass 10/10 with `--headed --workers=1`; S11–S14 and hard-deletion/runner gates remain green; no browser/service residue or second provider request; docs distinguish local completion from deployment gates | Complete: visible Chromium 10/10 in 14.4s; S11–S14 subset 9 passed / 2 deselected; no fixed sleep/process/listener/report residue; one production `useChat`, legacy source gate and protected-runner hash pass | Staging/canary, immutable artifact/rollback, production load and the disclosed Admin entitlement risk remain release concerns, not blockers to the completed repository refactor |
| R33 — complete business interaction specification | Replace the state-machine-only reading experience with a code-grounded catalog of every Dream business interaction | Current Story Workspace/Dream/Chat production code, tests, existing design set and historical PRD | Every in-scope capability has an owner, permissions, side effects, failure behavior, evidence and an independent Mermaid sequence; assumptions are marked | Complete: created `business-interaction-design.md` with one master chain and B01–B21, including eight explicit product decisions | Stakeholder intent for the eight open decisions is not inferred from source |
| R34 — business-design structural validation | Repair notation/coverage/link issues and prove every business sequence is renderable and reviewable | The new business document plus its inbound/outbound design links; no product code | All 22 Mermaid sequences parse with project Mermaid; B01–B21 each have intent, rule/boundary and evidence; no dead relative link or state diagram masquerading as an interaction | Complete: 22/22 parse, 21/21 capability coverage, 55 relative links and no `stateDiagram` passed | Visual rendering was parser-validated but not manually reviewed in every Markdown renderer |
| R35 — formal business-understanding review | Challenge the full catalog against current source and separate delivered behavior from open product choices | B01–B21, canonical design set and production source counter-scans | Accept only if there is no second runtime, no invented UI/recovery/coupling, and every open business choice is visible to the owner | Complete: initial formatting/parser findings were corrected; final conclusion **ACCEPT**, with eight non-inferred product decisions retained for owner review | The owner has not yet decided the eight items in §26; those decisions may require later design/code changes |

### R1 optimized prompt — diagnosis

```text
Act as a read-only architecture diagnostician for ink-dream-memory. Inspect the
platform, story-workspace and develop refs and prove whether the Chat/Dream split
is a Git branch divergence, runtime divergence or public-protocol divergence.
Trace the current backend and frontend call chains for Chat thread SSE, Dream
run-scoped SSE, tool confirmation, reconnect, workflow status and file status.
Inventory normative versus historical documents that mention Dream Agent,
Dream events, run-scoped SSE, safe projection or allowlists. Identify exact
conflicts, unique business/UX/safety requirements that must survive cleanup,
inbound index links, update/archive/delete candidates and Git recovery commits.
Inspect the sibling admin gateway only to decide whether it owns schema or merely
transports SSE. Cite exact commit SHAs and source/document path:line evidence.
Do not edit code or docs. Report verified facts separately from inference.
```

**R1 actual result**

- Proved `story-workspace@eedde94` is the exact merge base/ancestor of
  `platform@a506c83`.
- Identified `61f70fc` as the public Dream protocol split and `b5b986c` as
  normalized internal reconvergence with separate adapters.
- Distinguished conversation, workflow/business and legacy audit event planes.
- Produced the current caller/difference/document migration inventory now in
  [Diagnosis](./diagnosis.md).

**R1 unverified inference**

No live traffic, logs, stakeholder interviews or production permission model
were inspected. Document cleanup recommendations remain proposed until owners
approve and extraction is verified.

### R2 optimized prompt — design

```text
Create a new design set only under docs/design/dream-agent/ with README.md,
architecture.md, interaction-design.md, lifecycle.md, observer-design.md,
migration-plan.md, testing-and-acceptance.md, diagnosis.md, design-review.md and
prompt-rounds.md. Explicitly overturn the old independent Dream public SSE
design: Dream conversation must use canonical Chat thread history, status, send,
SSE reconnect, tool confirmation and Stop. workflowRunId remains only in Story
Workspace business REST and must never enter Chat send/confirm/stream/stop.

At Chat ingress, resolve Dream authority from authenticated actor plus owned
thread. Validate retry_of_run_id because legal retries reuse source_voice_thread_id;
select the unique unsuperseded leaf of one valid acyclic chain. Zero attempt is
generic Chat; independent multiple leaves, a broken/cyclic chain or frozen
source/Deck mismatch is 409. The browser cannot select or author run context.

Define DreamLifecycleObserver as a dedicated NormalizedAgentEvent/EventBus
subscriber. It may keep only bounded process-local eventId/turnId/threadId
dedup and strict sequence, project activity/waiting/exactly-one terminal hints,
ignore all late events after terminal, and call an injectable business sink.
Do not add an Observer event store, outbox or checkpoint; existing owning
services/DB remain durable workflow truth.

Include exact Git/path/line evidence, current and target diagrams, public
difference/caller matrices, permission boundary, migration/deletion table and a
formal review template. Include separate Mermaid sequences for all 14 required
scenarios: normal Dream send; Dream→Chat; Chat→Dream; approve/reject/AskUser;
subagent lifecycle; main Stop; failure before output; failure after partial
output; disconnect/reconnect; refresh/history; Observer projection; Observer
duplicates; exactly-one normal terminal; old-protocol migration. Include the
complete conversation, reconnect, exactly-one terminal and Workflow Run state
machines with one-way business derivation. Distinguish verified current from
proposed behavior; do not claim implementation or review approval.

The repository-round target is direct replacement of production Dream callers
and hard deletion of the old protocol. A cohort/canary may be documented only as
an optional deployment technique between immutable builds, not as a long-lived
repository feature flag or dual-protocol implementation.
```

**R2 actual result**

The ten requested files were created. The normative set specifies one Chat
conversation protocol, thread-only authority lookup with retry-leaf validation,
process-local `DreamLifecycleObserver`, 14 interaction sequences, full lifecycle
states, direct migration/deletion and test/review contracts. All target code is
labelled proposed.

**R2 unverified inference**

- The binding resolver, minimal hydration primitive, bounded canonical
  confirmation policy record and Coordinator/Observer do not yet exist;
  `ChatPanel` itself is verified current.
- Product/security acceptance of richer Chat visibility is unknown.
- Baseline-relative latency and projection SLOs require measurement.
- Exact module names may change during implementation if responsibilities and
  acceptance contracts remain intact.

### R3 optimized prompt — independent formal review

```text
Act as an independent architecture reviewer with no reliance on prior hidden
reasoning. Read every file under docs/design/dream-agent/ at one pinned Git SHA
and verify cited source paths/lines against the repository. Check that the target
has exactly one public Chat conversation protocol, no browser run selector, a
correct retry-chain leaf algorithm, server-owned confirmation policy, exactly-one
terminal behavior, all 14 separate Mermaid scenarios, complete conversation and
Workflow Run state machines, and one-way business projection.

Challenge DreamLifecycleObserver for EventBus subscription, stable
eventId/threadId/turnId identity, strict sequence, bounded memory, replay/late
event handling, failure isolation and absence of new persistence. Challenge
direct replacement/hard deletion for complete caller inventory, rollback by
immutable build, no long-lived flag or dual protocol, and objective acceptance.
Review the richer Chat visibility boundary, cross-actor behavior, retry graph,
tool confirmation and proxy/reconnect failure modes.

Record every actionable issue in design-review.md with severity, exact evidence,
required change and owner. Do not silently edit normative decisions. Use the
decision rubric and sign-off table; leave status PENDING while evidence or any
blocking finding remains. Do not claim tests or implementation were run unless
the artifact includes the exact command/result.
```

**R3 actual result**

The independent reviewer recorded **修改后接受 / CHANGES REQUIRED** with one P0
and eight P1 findings, DR-001 through DR-009. The review accepts the core
single-protocol/immutable-build direction but withholds implementation permission
until those findings are closed and re-reviewed.

**R3 unverified inference**

Final closure, implementation permission and all production risk acceptances
remain unknown until the independent reviewer rechecks R4.

### R4 optimized prompt — close DR-001 through DR-009

```text
Revise only docs/design/dream-agent/** except reviewer-owned design-review.md;
change no production code. Close DR-001–DR-009 exactly. Reuse the existing
actor-scoped Dream-files response and its existing threadId; add no re-entry API.
Make the frontend ChatPanel-first: ChatPanel remains the sole useChat/live
reducer owner and Dream composes it directly. Share only the smallest
history→status→reconnect nonce/pending IDs/post-EOF hydration primitive; prohibit
a large Provider or second runtime.

At ClaudeAgentService._make_tool_confirm_cb/ToolConfirmationStore, specify
register-before-publish of a bounded server-owned policy+Future keyed by
thread/turn/toolCall. Cover typed AskUser, network and reject_only validation,
atomic single resolve, stable settled replay and timeout/reject/Stop/cancel/
terminal/context/session/factory-close cleanup. Do not modify agent_runner.py.

List and migrate dream_launch_infrastructure.py:813,
dream_confirmation_service.py:889 and dream_agent_message_service.py:1891 from
iter_dream_run_events to canonical normalized run_events or one minimal
Coordinator drain while preserving their distinct claim/ack semantics. Define
DreamLifecycleCoordinator ownership for pre-producer subscription, bounded
queue, sink worker, lease fencing, terminal/sentinel/context-failure/Stop/task-
exception/eviction/aclose unsubscribe-cancel-await cleanup. Preserve
ClaudeAgentService normalized-event/persistence/terminal ownership.

Apply one field-level visibility contract at history/live/reconnect/export:
private Story Workspace control rows never appear, zero visible parts produce no
blank bubble, and owner-visible reasoning/tool input/output/provider error
snapshots match Chat. Define Stop only for a real current main turn; non-2xx,
timeout or running=true keeps input locked and status/reconnects; unmount never
Stops.

Make validation mandatory and exact: backend focused/regression, frontend
contracts, standalone TypeScript, ESLint, build, git diff --check, byte-split/
merge/CRLF/Unicode/Chinese/newline/special-character/Admin no-buffer, headless
then headed Chromium --workers=1 with semantic waits, deterministic fake
provider, isolated temporary DB/workspace and zero residual ports/processes/
browser/server/Observer tasks/Futures. Mark R4 actual result 已修订待复审 and do
not claim implementation or reviewer closure.
```

**R4 actual result**

**已修订待复审。** The normative documents now contain the requested target
contracts and DR-to-location mapping. `design-review.md` remains reviewer-owned
and has not been edited by the design author in R4.

**R4 unverified inference**

No production implementation, test command, security approval, performance
baseline, cleanup trace or reviewer closure is claimed. Proposed names, bounds
and test paths remain subject to implementation plus independent re-review.

### R5 optimized prompt — independent blocker-closure review

```text
Re-review the complete docs/design/dream-agent/ design set as the independent
implementation gate. Compare every R4 normative change against the original
DR-001 through DR-009 required changes in design-review.md and against the cited
current repository code. For each DR, record CLOSED or OPEN with exact document
and code evidence. Do not accept a named concept unless identity, ordering,
ownership, cleanup, authorization and acceptance tests are executable.

Specifically prove: Dream reuses the existing actor-scoped dream-files threadId
without a new endpoint; Dream directly composes ChatPanel and ChatPanel stays the
only useChat/live reducer owner; canonical confirmation registers a bounded
server-owned policy+Future before publish and validates one atomic resolve; all
three iter_dream_run_events consumers have explicit canonical replacements and
task ownership; the minimal Coordinator owns subscriber/queue/worker cleanup on
every exit; agent_runner.py remains protected; history/live/reconnect/export use
one private-row/zero-visible-parts contract; Stop remains locked on non-2xx,
timeout or running=true and ignores historical subagents; and the validation
gate includes focused/regression tests, typecheck, lint, build, diff check,
headless plus headed Chromium with semantic waits, fake provider, isolated data
and zero resource leaks.

Update only design-review.md. The result must be 接受 only if every blocker is
closed and there is no remaining P0/P1 ambiguity; otherwise keep 修改后接受 or
拒绝 and withhold production implementation permission. Do not claim that any
proposed code or test already exists.
```

**R5 scope and completion standard**

- Goal: independently decide whether R4 is safe and precise enough to authorize
  implementation.
- Scope: all files in this design set plus read-only cited source; only
  `design-review.md` may be changed.
- Completion standard: DR-001–DR-009 each have a disposition and evidence; the
  final verdict unambiguously grants or withholds production-code work.
- Actual result: DR-001 through DR-009 are CLOSED; verdict **接受，并授权生产实现**.
- Unverified inference: implementation feasibility, test behavior, performance
  and production compatibility remain unverified regardless of design verdict.

**R5 actual result**

The independent reviewer marked DR-001 through DR-009 **CLOSED** and changed the
formal verdict to **接受，并授权生产实现**. Release permission remains withheld
until the implementation and all P0/P1 validation gates pass.

### R6 optimized prompt — implement the accepted convergence design

```text
Implement the accepted DREAM-CONVERGENCE-2026-01 design in three coordinated,
non-overlapping work packages. First, extend the canonical per-turn
ToolConfirmationStore and ClaudeAgentService boundary with server-derived,
register-before-publish policy, exact active identity, typed AskUser/network/
reject-only validation, atomic one-winner settlement and complete cleanup; make
canonical Chat ingress resolve Dream context only from authenticated actor plus
owned thread and a validated retry graph. Second, add the minimal factory-owned
DreamLifecycleCoordinator/Observer over NormalizedAgentEvent/EventBus, migrate
all three internal adapter drains to canonical run_events while preserving each
claim/ack owner, remove Dream public conversation routes/adapter/projection and
close every task/subscription/queue on all exits. Third, make Dream surfaces
compose ChatPanel directly with the existing dream-files threadId and the same
history/status/stream/confirm/Stop semantics; extract only minimal hydration,
fix shared Stop uncertainty and visibility/zero-part behavior, and delete the
Dream EventSource/parser/reducer/hook and reverse confirmation/history bridges.

Do not modify backend/libs/claude_agent_kit/server/agent_runner.py. Do not add a
browser run/turn selector, second useChat/live reducer, app-wide runtime Provider,
Observer persistence, new public Dream conversation schema, feature flag or
dual protocol. Preserve actor/thread/run/Deck/revision/idempotency authorization
for workflow business commands. Treat finish as the sole terminal; message-final
is persistence evidence only. Preserve user changes and limit edits to this
migration. Add focused backend/frontend contract tests with deterministic fakes;
do not call a real model. Each work package must report exact files, tests run,
known failures and unverified assumptions for integration review.
```

**R6 scope and completion standard**

- Goal: produce the accepted single-runtime implementation and remove all
  production callers of the old Dream conversation protocol.
- Scope: Dream/Chat backend and frontend seams, their focused tests, and no
  unrelated global refactor; `agent_runner.py` is protected.
- Completion standard: canonical context/confirmation and Observer contracts
  exist, both surfaces use one Chat runtime, legacy production routes/adapters/
  reducers/callers are absent, focused tests pass, and all changes are ready for
  the separate validation round.
- Actual result: implemented. Dream directly composes the canonical ChatPanel;
  the old public Dream routes, adapters, hook/parser/reducer and their production
  callers are removed; the factory-owned Observer/coordinator, binding resolver,
  confirmation policy and internal workflow command drain are present; the
  protected runner has no diff. Focused implementation evidence is consolidated
  in R8; release validation remains separate.
- Unverified inference: full regression, build, Admin transport and real headed
  browser behavior remain unverified until the later validation round.

### R7 optimized prompt — migrate and clean historical Dream design docs

```text
Audit every repository document and index that mentions DreamAgent, Dream Event,
run-scoped messages/SSE, safe projection, allowlist reducer or Dream confirmation
transport. Before changing or deleting a document, use rg to inventory inbound
links from code, README, tests and docs. Separate unique business requirements,
UX acceptance and authorization rules from historical implementation choices.
Move or link still-valid requirements into docs/design/dream-agent/, update every
surviving normative document and index to the canonical Chat thread/SSE plus
one-way Dream Observer architecture, and remove only documents whose misleading
protocol design is fully superseded. Do not delete the only source of a business
requirement.

Maintain in migration-plan.md a table with original document, current status,
conflict, replacement and action. For every deletion record the reason and Git
recovery baseline/commit. Run relative-link, source-reference and stale-term
scans after edits; leave no dead links or index entry that recommends the old
Dream public protocol. Do not change production code in this round and do not
claim runtime migration or tests are complete.
```

**R7 scope and completion standard**

- Goal: make the design corpus point unambiguously to the accepted architecture
  while retaining unique business and safety requirements.
- Scope: Dream/Claude-agent design documents and their indexes/links only.
- Completion standard: migration table matches actual files, every deleted file
  has inbound-reference and recovery evidence, surviving links resolve, and no
  normative doc recommends run-scoped Dream conversation SSE.
- Actual result: complete. Two fully superseded two-protocol documents were
  deleted after inbound-reference scans; design005/007/008/012 retain unique
  business/UX evidence with explicit transport supersession; Claude API,
  EventBus, glossary and design indexes now point to the shared contract. The
  migration table records exact `a506c83` recovery commands.
- Unverified inference: external bookmarks, stakeholder ownership and deployed
  copies outside the repository cannot be observed locally.

### R8 optimized prompt — close integration lifecycle races

```text
Act as the integration owner for the accepted Dream/Chat single-runtime
migration. Review the assembled backend and frontend diff rather than trusting
work-package reports. Keep ChatPanel as the only useChat/live reducer and keep
canonical thread history, status, SSE, confirmation and Stop as the only
conversation contract.

Close every concrete integration defect before broad validation. In particular,
prove that a server-authorized workflow command which completes or fails before
the Dream conversation wrapper mounts is recognized from canonical persisted
thread history plus authoritative idle status, releases its business
idempotency latch exactly once, and never treats an unproven initial idle sample
as completion. Prove that a reconnect signal is scoped to its hydrated thread,
so switching from a formerly running thread to an idle thread cannot open a
spurious stream or display Stop. Preserve hidden business envelopes and
human-visible Dream messages under the shared Chat visibility contract.

Inspect backend thread binding, confirmation policy, Observer queue/lease/task
cleanup, internal command claims and single-terminal behavior for cross-package
mistakes. Remove mechanical duplicate parameters/JSX props and stale imports.
Do not restore a Dream EventSource/parser/reducer/API, do not add a browser run
selector or Observer persistence, and do not modify agent_runner.py. Add only
focused deterministic regressions needed to prove each fixed race. Report exact
evidence and leave broad backend/frontend/build/headless/headed validation to a
separate Prompt-Architect round.
```

**R8 scope and completion standard**

- Goal: make the integrated implementation internally coherent before broad
  release testing.
- Scope: changed backend/frontend lifecycle seams and focused deterministic
  regressions; no unrelated refactor.
- Completion standard: independent review findings are closed; pre-mount
  terminal/failure settlement and running→idle thread switching have tests;
  source scans show one `useChat`, no legacy public Dream transport, no
  mechanical duplicates, and no protected runner diff.
- Actual result: complete. Independent frontend and backend reviews both
  returned **ACCEPT** after closing pre-mount settlement, reconnect generation,
  confirmation replay, history projection, malformed metadata, atomic terminal,
  rolling Redis finish/sentinel, factory admission/teardown and
  message-final/cancellation races. The final backend five-file suite reports
  `177 passed`, `25 subtests passed`, with 23 pre-existing FastAPI deprecation
  warnings; focused frontend runtime/confirmation contracts report `27 passed`.
  Source scans find one production `useChat(`, no production legacy Dream
  EventSource/parser/reducer/API caller, no mechanical duplicate prop, and no
  protected runner diff. `git diff --check` is clean.
- Unverified inference: reasonable-scope regression, standalone typecheck,
  ESLint, production build, Admin no-buffer, headless and headed Chromium,
  cleanup residue and real PostgreSQL/Redis remain unverified until R9.

### R9 optimized prompt — validate the release candidate and synchronize evidence

```text
Act as the release-validation owner for the accepted Dream/Chat single-runtime
migration. Validate the actual uncommitted candidate without calling a real
model. First inventory and terminate only task-owned stale Vite/Chromium
processes and ports; never use broad process kills. Run Python compile checks,
the focused backend suites and a reasonable regression set, schema/migration
verification, frontend contract tests, standalone TypeScript, ESLint and the
production build. Run the sibling Admin gateway SSE tests and prove it neither
buffers nor aggregates canonical thread SSE. Repeat source, import, route,
OpenAPI and built-artifact scans for exactly one Chat runtime, zero legacy Dream
conversation API/adapter/parser/reducer callers and zero protected runner diff.

Add only the smallest deterministic fake-server browser scenarios needed to
cover gaps not already proven by contract tests: an active same-thread
Dream→Chat→Dream surface handoff without a duplicate POST or implicit Stop;
confirmation/AskUser/reject-only handoff; true Stop success and uncertain
failure locking; disconnect/reload recovery; and pre-output/partial-output
failure with exactly one terminal. Reuse existing contract tests for exhaustive
chunk splitting, Unicode and typed confirmation variants. Use strict fake API
method/auth/catch-all assertions, OS-assigned ports, semantic waits only, no
fixed sleeps and no real credentials/model. Run the focused Chromium suite
headless first, then at least once visibly with `--headed --workers=1`, retaining
trace evidence on failure. Close pages before servers and prove zero owned
listener/process/task residue on every exit.

Update docs/design/dream-agent only from measured implementation and validation
facts. Preserve the R5 design review as historical, append the R8 implementation
review, correct nonexistent test paths/commands, distinguish implemented from
release-verified, and keep unavailable real PostgreSQL/Redis/cross-process
checks explicitly pending with substitute evidence and risk. Do not weaken a
gate to obtain green results, do not add a second runtime, do not modify
agent_runner.py, and do not claim release completion until every executable
check and the final documentation/link/diff audit has been rerun.
```

**R9 scope and completion standard**

- Goal: produce reproducible release evidence for the single-runtime migration
  and make every current design/status statement match the implementation.
- Scope: reasonable backend/frontend/Admin/static/browser validation, minimal
  deterministic E2E gap coverage, cleanup proof and Dream design evidence sync.
- Completion standard: executable checks pass; one headless and one visible
  headed Chromium run pass with semantic waits; source/OpenAPI/bundle scans and
  cleanup checks are clean; unavailable infrastructure checks are recorded as
  unverified rather than guessed; docs contain no nonexistent command/path or
  stale claim that implemented behavior is merely proposed.
- Actual result: after R8 acceptance, Python compile passed for 340 files; the
  final backend broad run passed `1887` tests plus `615` subtests with `13`
  skips; 62 focused frontend tests, TypeScript, ESLint (0 errors/21 existing
  warnings), the production build and 18 focused Admin gateway tests passed.
  Source/OpenAPI/bundle scans found no legacy Dream conversation contract.
  Chromium convergence passed 4/4 headless and 4/4 headed before the user
  deferred further headed runs; the test contains no fixed sleep and left no
  owned browser/server residue.
- Unverified inference: no local PostgreSQL or Redis service/DSN was available,
  so live database concurrency/migration and Redis Lua/cross-process rolling
  upgrade remain pending. Staging, performance baseline, immutable rollback and
  14 independently named release scenarios are also not claimed by local R9.

### R10 optimized prompt — prove full objective completion from current state

```text
Act as the final completion-audit and implementation owner for the persistent
DreamAgent convergence objective in /Users/dmeck/project/ink-dream-memory.
Treat the current worktree—not earlier summaries—as authoritative. Derive an
explicit evidence matrix for every requirement: one Chat thread runtime on both
surfaces; canonical send/SSE/history/reconnect/confirmation/AskUser/network/
reject-only/subagent/Stop/completion/failure/cancellation semantics; trusted
Dream workflow authorization; Observer idempotency/order/single-terminal and
failure isolation; session persistence; GET side-effect removal; legacy route,
adapter, reducer and caller deletion; documentation migration; async cleanup;
and S01–S14 acceptance.

Inspect implementation and tests before accepting any prior claim. Close every
locally actionable gap with the smallest production-faithful change. Make all
fourteen scenarios independently discoverable and assert behavior rather than
merely mapping names to unrelated tests. Use deterministic fake providers and
isolated OS-assigned ports; never call a real model. Probe for disposable
PostgreSQL and Redis facilities and use them only if safely isolated; otherwise
retain precise environment-bound gaps and strengthen static/fake substitutes
without weakening release criteria. Preserve workflow, actor, thread, run,
Deck and provenance authorization, and never modify
backend/libs/claude_agent_kit/server/agent_runner.py.

Run proportional backend, frontend, Admin, schema, type, lint, build and
headless Chromium checks with semantic waits and exact process cleanup. The
user has temporarily deferred --headed, so do not launch a new headed browser
in this round; preserve earlier evidence but do not treat it as authorization
for another run. Repeat source/OpenAPI/bundle/link/diff audits and update the
design evidence only from measured facts. Mark the objective complete only if
every requirement is directly proven and no required work remains; otherwise
continue implementing or report only the exact external gate.
```

**R10 scope and completion standard**

- Goal: convert the remaining mixed/indirect evidence into a direct
  requirement-by-requirement completion proof.
- Scope: current implementation, independently named S01–S14 tests, safe local
  infrastructure discovery, deterministic validation, cleanup and final docs.
- Completion standard: all locally executable requirements pass with direct
  evidence; remaining external requirements, if any, are demonstrated to be
  unavailable rather than inferred; no headed browser is launched while the
  user's temporary deferral remains active.
- Actual result: pending audit execution.
- Unverified inference: availability of a safe disposable PostgreSQL/Redis
  runtime, immutable deployment artifacts and staging/rollback control.

### R11 optimized prompt — validate the exact final candidate without headed Chromium

```text
Act as the final local release validator and evidence reconciler for the exact
DreamAgent convergence candidate in /Users/dmeck/project/ink-dream-memory.
Validate only the current worktree after all R10 implementation and review
fixes; do not reuse an earlier green result for code that has since changed.

First run the repository's isolated Dream business harness against a new,
randomly named disposable PostgreSQL container and OS-assigned ports. Require
Alembic head, a live catalog assertion for the trusted thread-lookup index, the
PostgreSQL rollback/concurrency contract, fake-provider backend/Admin/Vite
services, and the named headless Chromium convergence scenarios. Never read or
mutate the developer database, never call a real model, and prove exact cleanup
of containers, processes and temporary artifacts even after failure.

Then run the broad reasonable backend suite; focused frontend unit and contract
tests; Admin proxy contracts; TypeScript; ESLint; production builds; all
independently named S01-S14 acceptance tests; and the live isolated Redis RESP2,
RESP3, replay, terminal-arbitration, TTL and cleanup contract. Use semantic
waits and one worker for browser tests. The user has explicitly deferred
--headed, so run no new headed browser and report the current-candidate headed
gate as deferred rather than passed.

Finally re-audit production source, OpenAPI and built bundles for the deleted
Dream conversation protocol; verify GET is read-only with respect to Agent
turn scheduling; verify agent_runner.py is untouched; check documentation
links and migration records; run git diff --check; and prove no owned service,
browser, Redis or PostgreSQL residue. Reconcile prompt-rounds.md and all Dream
design acceptance claims to measured command output. Do not claim distributed
multi-worker HTTP routing from the Redis stream adapter: active-turn ownership,
Stop, confirmation and subscriber routing remain process-local unless a real
shared control plane is implemented. Do not claim immutable artifact, staging
or rollback proof without release-system evidence.
```

**R11 scope and completion standard**

- Goal: validate the exact post-R10 candidate and leave one reproducible,
  requirement-linked local evidence set.
- Scope: isolated infrastructure, local suites, headless browser, static and
  documentation audits, and owned-resource cleanup.
- Completion standard: every locally executable gate is green and accurately
  documented; deferred or external gates stay explicit; no `--headed` or real
  model invocation occurs.
- Actual result: pending validation execution.
- Unverified inference: immutable release artifact identity, staging behavior,
  deployment rollback and a current-candidate headed browser run.

**R11 actual result**

- Passed before the blocking chain: Alembic head, live PostgreSQL catalog proof
  for the non-unique valid/ready Dream thread index, PostgreSQL runtime 4/4 and
  2/2 suites, artifact PostgreSQL 61/61, one headless model/mobile browser test,
  backend broad `1913 passed, 17 skipped, 626 subtests`, and isolated Redis
  `4 passed` plus 2 RESP2/RESP3 subtests.
- Failed at the headless producer-chain prerequisite: Admin
  `/v1/messages?beta=true` returned 401, the local fake provider observed zero
  requests, the canonical thread stayed running with only its user row, and no
  external provider was called. The harness removed its container, listeners,
  processes and temporary artifacts and restored the Admin tsconfig hash.
- This is an actionable local integration failure, not a release PASS or an
  external-environment waiver. R12 owns diagnosis and repair.

### R12 optimized prompt — repair the local gateway authentication boundary

```text
Act as a cross-repository gateway authentication diagnostician and minimal-fix
owner for the Dream producer chain. The exact reproducible symptom is that the
isolated PostgreSQL/fake-provider harness reaches ink-admin-memory
`/v1/messages?beta=true`, receives HTTP 401 repeatedly, records zero
gateway/provider requests, and leaves the canonical Dream thread running with
only its user message. Earlier migration, live index, PostgreSQL contract and
model-selection checks pass. No real provider was contacted and cleanup passed.

Trace the credential end to end from ink-dream-memory's Gateway client and
subject-token construction through request headers, service API-key lookup,
issuer/audience/client/scope validation and ink-admin-memory middleware. Compare
the harness bootstrap values with the exact production validators and existing
cross-repository tests. Capture the bounded 401 reason without logging secrets.
Do not guess that the environment is at fault and do not weaken authentication,
scope, canonical-subject, actor, subscription, model or provider checks.

Implement only the smallest production-faithful correction in the owning
repository or harness. Add a regression that fails for the observed mismatch
and passes for the corrected issuer/audience/client/service-key/subject
contract. Preserve all user worktree changes, do not modify agent_runner.py,
and do not introduce a compatibility bypass or second Agent runtime.

Validate first with a focused auth/gateway test, then rerun the complete isolated
PostgreSQL business harness against a new random test database/container and
local fake provider. Require provider observations greater than zero,
gateway/token settlement, producer-chain and Admin story browser checks, zero
external provider calls, and exact cleanup on pass/failure. The user has
deferred --headed: run headless Chromium only. Record verified facts and keep
immutable artifact, staging and deployment rollback outside local claims.
```

**R12 scope and completion standard**

- Goal: explain and close the local Admin gateway 401 without reducing any
  production authorization boundary.
- Scope: service-key and subject-token creation/validation plus the isolated
  fake-provider integration and its focused contracts.
- Completion standard: focused regression and the entire fresh isolated harness
  pass; the fake provider is called, the external-provider count stays zero,
  accounting settles, and no owned resource remains.
- Actual result: pending diagnosis and repair.
- Unverified inference: the precise failed validation branch until bounded
  middleware/client evidence is captured.

### R13 optimized prompt — close workflow-to-thread reverse control

```text
Act as the final one-way-lifecycle boundary reviewer and implementation owner.
One P1 finding must be proved and closed without creating a second runtime.
The trusted Dream binding resolver currently injects Dream activation
context even when the unique retry leaf is completed, failed, cancelled or
rejected. The canonical composer remains available, but SDK-init activation
rejects those workflow states, so a derived business status can block an
otherwise valid Chat thread turn. The same replay path may reject a canonical
fresh SDK session after local transcript loss because it compares the new
session ID to an old Dream runtime session record.

Trace the retry-leaf status, resolver return value, canonical message metadata,
activation callback installation, existing activation/session rows and
fresh-session recovery. Distinguish initial/active Dream business execution
from ordinary conversation after a terminal workflow. Select the smallest
one-way design: fully validate actor/thread/retry/Deck provenance, but do not
attach Dream business activation authority to an ordinary turn when the trusted
leaf is in a terminal business state. Unknown/corrupt state must still fail
closed. Workflow retry/cancel/confirm/internal commands retain their own actor,
run, thread, ownership and CAS authorization; terminal detachment must not make
those commands generic or mutable.

For active workflows, prove whether repeat SDK-init activation is required. If
an already activated run can safely treat later canonical session init as
idempotent, preserve the durable initial activation evidence while allowing the
thread's existing transcript-missing fresh-session recovery; do not silently
rewrite frozen plugin/runtime authority. If that cannot be proven, constrain
the change to terminal detachment and report the active fresh-session gap
rather than guessing.

Add executable contracts for completed/failed/cancelled/rejected workflow
leaves continuing through the canonical Chat path with no Dream activation,
active leaves retaining trusted context, malformed/unknown state failing
closed, and—only if proven safe—already-activated transcript-loss recovery.
Preserve agent_runner.py, canonical Chat persistence and all workflow command
permissions. Run focused backend tests, the isolated fake-provider PostgreSQL
headless harness, broad regression and final architecture re-review. The user
has deferred --headed, so run no headed browser.
```

**R13 scope and completion standard**

- Goal: make Workflow state strictly one-way business derivation.
- Scope: binding/activation/session seams and their deterministic tests; no UI
  or protocol fork.
- Completion standard: four terminal states allow ordinary canonical messages
  without activation; active state and business commands retain authorization;
  unknown state rejects; fresh-session behavior is either proven/fixed or
  explicitly bounded.
- Actual result: pending source proof and implementation.
- Unverified inference: whether an already activated active run may safely
  accept a changed SDK session ID without updating frozen runtime authority.

### R14 optimized prompt — trace the real CLI Messages authorization

```text
Act as a Python/Claude Agent SDK subprocess and HTTP authentication diagnostician.
The first R12 repair removed a direct ANTHROPIC_AUTH_TOKEN that could be
resurrected by the Simple client’s second project-env merge, and focused local
captures showed a valid canonical-subject JWT. A fresh production-shaped,
isolated PostgreSQL/fake-provider/headless harness nevertheless still produced
HTTP 200 for Admin /v1/models but repeated HTTP 401 for /v1/messages?beta=true,
with no gateway request row, ledger reservation or fake-provider request. Treat
that rerun as disproof that the first cause was sufficient.

Trace the exact environment and Claude CLI invocation used by the full harness,
from harness variables through uvicorn, AgentRunner, gateway option application,
SimpleClaudeAgentSDKClient and the spawned CLI. Use a bounded local capture
endpoint or equivalent no-model executable probe to record only safe derived
facts: request path, presence and scheme of Authorization, presence of x-api-key,
whether the subject token parses as a three-segment JWT, and non-secret claim
names/issuer/audience/client/sub/scope. Never print plaintext service keys,
tokens, helper commands containing secrets, or inherited credentials. Compare
the capture with Admin’s canonical-subject contract and determine whether the
header is absent, stale, malformed, overridden, attached to a different header,
or rejected for a claim mismatch.

Inspect every relevant Claude credential variable and precedence rule that is
actually present in this repository/installed SDK/CLI runtime. Do not weaken
Admin authentication, accept a direct provider token as a subject identity, or
change agent_runner.py. Make only the smallest source fix supported by the
capture and add regressions that reproduce the full subprocess merge/launch
boundary, including both dotenv and process-environment credential sources.

Then run focused backend tests and one fresh isolated PostgreSQL/fake-provider
headless harness. Success requires /v1/messages to reach the fake provider,
gateway request and ledger settlement evidence to exist, all three headless
specs to pass, external provider calls to remain zero, and every owned container,
process, port, temporary workspace and generated Admin build directory to be
cleaned. The user has deferred --headed, so do not run a headed browser.
```

**R14 scope and completion standard**

- Goal: replace the remaining 401 inference with executable, non-secret outbound
  request evidence and close only the proven credential-construction defect.
- Scope: harness-to-CLI environment, helper/header construction and strict Admin
  subject authentication; no provider-auth relaxation or unrelated refactor.
- Completion standard: safe capture explains the exact 401, a focused subprocess
  regression passes, and the full isolated headless chain reaches and settles the
  fake provider with zero external calls and residue.
- Actual result: pending capture and implementation.
- Unverified inference: the subject Bearer may be absent or overridden in the
  full CLI process even though a smaller Simple-client capture emitted one.

### R15 optimized prompt — bounded real-data `hy3-preview` validation

```text
Act as the release validation owner for a privacy-sensitive Agent system. The
user has explicitly authorized a real-data, real-model validation and selected
the exact model alias `hy3-preview`; do not silently substitute another model.
This round extends, but does not weaken, the R14 Gateway authentication repair.

First discover the locally configured canonical model catalog and prove that
`hy3-preview` resolves to an enabled model for the authenticated test subject
through the existing Admin Gateway. Verify the alias, subscription/allowance,
service-key scope and provider route without printing credentials. If the alias
is unavailable, stop the real invocation and report the exact configuration
gate instead of falling back.

Discover available existing application data using read-only queries and file
metadata. Prefer a recoverable clone/snapshot of the locally configured data
source; otherwise select the smallest representative, non-sensitive existing
Story Workspace/Deck/thread record whose owner and permissions can be exercised
legitimately. Never mutate the original database. Do not print prompts, story
content, personal records, tokens or provider secrets; evidence should contain
only hashed/counted/categorical facts and generated test identifiers.

After the R14 subprocess credential boundary is fixed and focused tests pass,
run exactly one bounded real-model workflow through the production-shaped path:
canonical Chat thread SSE -> ClaudeAgentService -> Admin Gateway ->
`hy3-preview`. Apply the repository's existing max-turns and timeout controls,
set an explicit conservative token/budget ceiling where supported, and prevent
fallback models. The result must prove provider reachability, one correlated
Gateway request/ledger settlement, canonical thread/message persistence,
single terminal behavior and any expected Dream business artifact/projection.
Do not call the provider directly around the Gateway.

Use an isolated cloned database and temporary workspace/build directories, keep
the browser headless because the user still defers `--headed`, and perform exact
cleanup of owned processes, ports, containers, temporary files and generated
build artifacts. Report model alias, request counts, status classes, hashes and
cleanup facts only. Distinguish a model answer from a full Dream business-chain
success; do not claim the latter unless workflow output and persistence are both
verified.
```

**R15 scope and completion standard**

- Goal: add one production-shaped, budget-bounded real `hy3-preview` proof on
  representative existing data without exposing or mutating the source.
- Scope: read-only data discovery, isolated clone, canonical Gateway model path,
  one real turn, persistence/business correlation and cleanup; no headed run.
- Completion standard: exact alias accepted, real provider reached through the
  Gateway, correlated canonical and business evidence exists, original data is
  unchanged and no owned residue or sensitive output remains.
- Actual result: pending R14 repair and safe data/model discovery.
- Unverified inference: `hy3-preview` is configured and entitled in the local
  catalog; this must be measured before any provider request.

### R16 optimized prompt — distinguish pending output from invalid output

```text
Act as the Dream business-readiness contract owner. The R14 isolated chain now
authenticates correctly: all 32 Admin Gateway Messages requests reached the
local fake provider and settled cleanly, the workflow completed all seven
business actions, terminal files/run/story-index checks succeeded, and cleanup
passed. The remaining producer-spec failure is an earlier Dream-page hydration
request to the authorized Dream-files GET that returned HTTP 422
OUTPUT_CONTRACT_INVALID before initial model output existed. The UI diagnostic
collector retained that transient response even though later output was valid.

Trace the initial Dream page load, Dream-files GET, file/output parser, polling
or refresh trigger, error normalization and E2E diagnostic assertion. Prove the
domain distinction between (a) a queued/running workflow whose first required
output has not been produced, (b) an output that exists but is malformed, and
(c) a terminal workflow missing required output. Select the smallest contract
fix: “not produced yet” must be represented as an ordinary pending/empty business
projection and must not surface as an application error, while malformed or
terminally missing output must remain fail-closed. Do not make every 422
fail-soft, swallow permission failures, weaken output validation, add fixed
sleeps, or make GET start/resume an SDK turn.

Prefer an explicit backend readiness result if the existing GET contract owns
this distinction; prefer a narrow frontend status mapping only if the backend
already emits an unambiguous pending code. Preserve actor/thread/workspace/run
authorization and the optional Observer hint. Add deterministic tests for all
three states and prove that polling uses semantic lifecycle/file readiness, not
time-based masking.

Then rerun the full fresh PostgreSQL/Admin/fake-provider headless harness. It
must pass model selection, producer chain and Admin generated-story review;
Gateway request/ledger counts must settle; external provider calls remain zero;
all owned resources are cleaned. Do not run `--headed`. Only after this fake
baseline passes may the separately authorized `hy3-preview` real-data/model
round proceed.
```

**R16 scope and completion standard**

- Goal: make initial Dream business hydration race-free without weakening real
  output corruption or authorization errors.
- Scope: Dream-files readiness contract, its UI adapter/diagnostics and focused
  tests; no Agent protocol or lifecycle fork.
- Completion standard: pending is non-error, malformed/terminal missing remains
  fail-closed, the complete isolated fake-provider headless harness passes and
  cleans up.
- Actual result: a red reproduction proved missing `.dream` was incorrectly
  mapped to 422. Read-only missing-root handling plus a status-aware strict gate
  now distinguishes running absence, malformed existing output and output-ready
  missing output. Backend Dream file/API coverage passed 67 tests with 37
  subtests; frontend parsing/fetch coverage passed 6 tests. The complete owned
  harness subsequently passed in R18.
- Unverified inference: none for the readiness distinction. Failed/cancelled
  absence is intentionally legal because those states may precede first output.

### R17 optimized prompt — fresh fake-provider release proof

```text
Act as the release validator for the exact post-R16 Dream Agent candidate.
Start from fresh, owned infrastructure only: a temporary PostgreSQL database,
temporary thread workspaces and build outputs, the existing Admin Gateway, the
Dream FastAPI/Vite applications and the repository's local deterministic
Anthropic-compatible fake provider. Do not read or mutate an existing user
database, do not contact an external model provider, and do not run headed
Chromium.

Execute the supported schema/migration order and its rollback/index checks,
then run the complete repository-owned Dream business harness with Chromium
`--workers=1`. Prove all of the following on the same generated run: model
selection, launch 201, initial Dream page hydration without a 4xx diagnostic,
canonical Chat thread settlement, three required Dream file stages, one
confirmation, all seven Episode actions, completed workflow, story index,
re-entry, Admin generated-story read/review and cross-service persistence.

Treat any earlier 4xx captured by the browser diagnostic collector as a real
failure even if a later retry succeeds. Require every Gateway request to have
one local fake-provider request, a succeeded/settled HTTP 200 outcome and a
closed reserve = capture + release ledger with zero reserved balance. Preserve
strict authorization and output validation; do not add sleeps, retry away a
contract error, weaken assertions or modify the harness merely to obtain a
green result.

On failure, report the earliest phase, allowlisted error code, request/provider
counts, safe server tail and cleanup result without printing credentials or
generated private content. In all cases terminate owned processes, remove the
owned container, temporary workspaces, test output and Admin build directory,
restore any generated config byte-for-byte and prove that unrelated existing
PostgreSQL/MinIO containers and standard ports were untouched.
```

**Optional enhancers**

- Capture only aggregate request, token-ledger and status evidence; omit model
  prompts and generated story bodies.
- Re-run the focused R16 boundary tests immediately before the full harness if
  the candidate changes while validation is running.

**R17 scope and completion standard**

- Goal: convert the focused R16 proof into a complete isolated release-chain
  result before any paid or external model call.
- Scope: the existing full fake-provider script and its owned resources; no
  production data, no real provider and no headed browser.
- Completion standard: all script phases pass in one invocation and cleanup is
  exact, or the earliest remaining product defect is isolated with executable
  evidence.
- Actual result: the first run stopped before launch because R18 exposed a stale
  frontend barrel export. After that one-line correction, the complete script
  passed: producer 1/1, Admin generated-story 1/1, 32/32 Gateway requests and
  fake-provider requests, balanced token ledger, zero external calls and exact
  cleanup.
- Unverified inference: broad suites outside this owned full-chain script remain
  for R19.

### R18 optimized prompt — diagnose the missing Dream launch surface

```text
Act as a browser-startup and authentication diagnostician for the isolated
Dream producer E2E. The fresh R17 stack passed schema/index checks, 4 + 2
rollback tests, 61 artifact tests and the model-selection Chromium test. In the
next independent Chromium invocation, `page.goto(/story-workspace/dream)`
completed but the semantic heading “发起一次 Dream” was not found within the
default five-second assertion. No launch request, Gateway Messages request or
provider request occurred, so do not attribute this failure to Dream-files,
Claude SDK, Gateway authentication or model output.

Reproduce on owned infrastructure and capture only safe first-render evidence:
final URL/path, document title, root child count, visible headings/status/alert
text, login-shell presence, HTTP failures, console errors and page errors. Do
not dump localStorage tokens, cookies, HTML containing user content or secrets.
Trace the router, auth initialization and Vite/application readiness contracts,
including whether `page.goto` can resolve before the React route is mounted.

Choose the smallest evidence-based correction. If the product renders an
incorrect/blank/error surface, fix that product defect and add a deterministic
regression. If the expected surface renders correctly but later than the
default assertion under a fresh dev-server compile, replace the implicit
five-second limit with a bounded semantic readiness wait and keep the exact
heading/selection assertions. Never add `sleep`, retry navigation blindly,
ignore console/HTTP errors or merely increase timeouts without captured proof.

After the focused launch check passes, rerun the complete R17 owned-stack
script unchanged in business assertions. It must proceed through the R16
initial hydration path, producer chain, Admin review, Gateway/ledger settlement
and exact cleanup. Do not run headed Chromium and do not contact a real model.
```

**Optional enhancers**

- Include the current diagnostic phase in every captured failure so a later
  4xx cannot be mistaken for first-render failure.
- Keep the failure evidence helper reusable for launch-form failures only;
  avoid adding a parallel application state machine to the spec.

**R18 scope and completion standard**

- Goal: turn the missing-heading timeout into an explained, reproducible
  browser readiness contract.
- Scope: initial producer navigation/auth/render and its diagnostics, followed
  by the complete isolated fake-provider rerun.
- Completion standard: evidence distinguishes product render failure from a
  delayed valid render; the selected fix is deterministic and the full chain
  passes or exposes the next earliest product failure.
- Actual result: safe evidence showed `/story-workspace/dream`, the expected
  document title, an empty React root and a page error naming the missing
  `storyWorkspaceShouldReadDreamFilesForAgent` export. Removing its stale barrel
  re-export fixed the product bundle; TypeScript and 12 focused frontend tests
  passed, followed by the complete R17 chain. No timeout was increased.
- Unverified inference: none for this first-render failure.

### R19 optimized prompt — exact-candidate broad non-headed regression

```text
Act as the final local release-gate owner for the exact Dream Agent worktree
that passed the owned PostgreSQL/Admin/fake-provider chain. Do not make design
or production changes unless a deterministic failure proves a candidate defect.
Do not contact a real model in this round and do not run headed Chromium.

Run the repository's broad backend suite plus all focused Dream/Chat/EventBus,
confirmation, reconnect, cancellation, session-persistence, Observer,
authorization, PostgreSQL boundary and Gateway CLI regressions. Run the
frontend's complete node/Playwright unit-contract set, TypeScript project check,
ESLint and production build. In the sibling Admin repository, run only the
Gateway/proxy/streaming/generated-story contracts and type/build checks required
by this cross-repository change; preserve unrelated dirty work and do not edit
the sibling unless a scoped defect is proven.

Run the browser-applicable S01–S10 Dream/Chat scenarios in headless Chromium
with `--workers=1`, semantic waits, no fixed sleeps and exact process cleanup;
run S11–S14 as backend/source/OpenAPI acceptance. Cover
ordinary streaming, same-thread page switches, refresh/reconnect, tool approve
and reject, AskUserQuestion, sandbox/network/reject-only, subagents, Stop,
pre-output and partial-output failures, cancellation, one terminal, Unicode and
SSE chunk split/merge, and Admin no-buffer streaming. Record discovered test
counts and command exit codes rather than copying earlier totals.

Finish with source and route scans proving the deleted Dream public SSE/Event
API, parser, reducer and production callers do not remain; confirm workflow
business commands still enforce actor/thread/run permission; check Markdown
links and design indexes; run `git diff --check`; prove
`backend/libs/claude_agent_kit/server/agent_runner.py` is untouched; inspect
owned processes, ports, containers and generated outputs. Treat skipped tests
as evidence only when the skip reason is explicit and provide the nearest
executable substitute. Preserve all user changes and do not stage or commit.
```

**Optional enhancers**

- Parallelize independent backend, frontend and Admin checks while keeping each
  command's output and exit status separately attributable.
- If a broad suite fails, rerun only the smallest focused selector needed to
  prove root cause before changing source.

**R19 scope and completion standard**

- Goal: prove no same-candidate regression remains outside the already-passed
  production-shaped fake-provider chain.
- Scope: locally executable backend/frontend/Admin/static/headless gates and
  cleanup; no real provider and no headed browser.
- Completion standard: every required local gate passes, or an exact external
  blocker and substitute proof are recorded without overclaiming.
- Actual result: complete. Backend broad finished with 1,927 passed, 17 skipped
  and 655 subtests; the focused backend selection passed 687. Isolated Redis and
  Gateway loopback gates passed. Frontend passed 340 unit/contract tests,
  TypeScript, ESLint and production build; S01–S10 passed in headless Chromium
  with semantic waits, while S11–S14 passed in backend/source acceptance.
- Unverified inference: none for the executed R19 scope. Current-candidate
  headed, staging/canary, immutable rollback and production load were not run.

### R20 optimized prompt — synchronize the stale Admin SQL assertion

```text
Act as the narrow cross-repository contract-test maintainer. R19 proved all
S01–S14 acceptance IDs, 104 Admin Gateway/proxy/SSE tests, Admin TypeScript and
the isolated production build. The only deterministic failure is
ink-admin-memory `app/lib/story-source/repository.test.ts`, whose assertion
still expects the removed physical predicate `s.artifact_available::text = $2`.
The clean production repository and schema already establish
`artifact_status` as canonical and expose the compatibility filter as
`(s.artifact_status = 'available')::text`.

Verify the two sibling files are unmodified, then change only the stale test
expectation to the exact canonical derived SQL fragment. Do not modify the
production query, reintroduce `artifact_available`, relax the assertion, alter
test fixtures or touch unrelated Admin code. Re-run the six generated-story
contract files (28 tests expected) and Admin TypeScript. Confirm the sibling
diff contains only that assertion and leave generated build/test residue
clean. No browser, provider or model call is needed.
```

**Optional enhancers**

- Retain the exact SQL fragment in the assertion so a future regression back
  to the legacy physical column fails loudly.

**R20 scope and completion standard**

- Goal: make the generated-story test express the already-implemented
  canonical artifact-status migration.
- Scope: one clean test assertion in the sibling Admin repository.
- Completion standard: 28/28 contracts and TypeScript pass; sibling diff is one
  line and production source is unchanged.
- Actual result: complete. Only the stale `repository.test.ts` expectation was
  changed; the six generated-story files passed 28/28 and Admin TypeScript
  emitted no diagnostics. The sibling diff contains exactly that one-line test
  update and the production repository remains unmodified.
- Unverified inference: none; the mismatch reproduced twice in R19.

### R21 optimized prompt — isolated real-data and exact `hy3-preview` proof

```text
Act as the release validation owner for DreamAgent's canonical Chat thread
runtime. Perform one privacy-preserving, real-provider validation using real
application data only through an isolated clone and the existing Admin Gateway.
The requested model is exactly `hy3-preview`; model substitution, provider
fallback and direct provider invocation are forbidden.

Begin with read-only discovery. Resolve the current database/workspace topology,
Admin Gateway authentication path, provider catalog/entitlement, canonical
`POST /api/claude-agent` request contract, SSE terminal contract and durable
message/ledger tables without printing secret values or private content. Prove
that the source database and workspace will remain read-only. If the exact model
is absent, disabled or not entitled, stop with the precise sanitized blocker.

Create uniquely named, disposable PostgreSQL and workspace clones from the real
source. Preserve the real provider/model configuration and encrypted credential
relationships inside the clone, while routing every mutable application write
to owned resources. Select a cloned, owned thread whose Dream workflow binding
is terminal (or create the minimum isolated canonical thread if no safe terminal
candidate exists). Start isolated Admin Gateway and Dream API processes against
the clone. Do not touch pre-existing PostgreSQL, MinIO, browser or server
processes.

Send one benign, bounded canonical Chat turn through `POST /api/claude-agent`
with model exactly `hy3-preview`, `max_turns=1`, and tools disabled. Consume the
actual SSE stream with a chunk-safe parser. Record only generated test IDs,
counts, hashes, status classes, timings and sanitized model-resolution metadata;
never record source history, prompt text, assistant output, API keys, bearer
tokens or decrypted provider credentials.

Assert: the request traverses the Admin Gateway; requested, resolved and
upstream model identity are all exactly `hy3-preview`; the same thread receives
one user and one non-empty assistant result under the canonical visibility
contract; streaming yields exactly one completed/failed/cancelled terminal and
no duplicate confirmation or terminal; durable session/message state survives a
read-back; Gateway reservation settles to capture plus release with no reserved
balance; no old Dream Event/API path is called. A model/provider error is valid
evidence only as an explicit failed proof, never a reason to fall back.

Before and after execution, compare sanitized logical fingerprints/counts for
the original source database and content hashes for any sampled source workspace
files. Clean every owned process, port, temporary directory, database/container,
build artifact and credential file even on failure. Re-check that pre-existing
services are untouched. Report measured evidence and remaining uncertainty; do
not claim headed browser coverage, because it is intentionally deferred.
```

**Optional enhancers**

- Use a generated run identifier in every owned resource name so cleanup can be
  exact and independently audited.
- Store the sanitized evidence manifest outside the source-data clone, then
  delete all transient cloned private data after assertions complete.

**R21 scope and completion standard**

- Goal: obtain one real-model proof for the shared canonical thread runtime with
  exact `hy3-preview` and real cloned application data.
- Scope: read-only original data; owned clones and processes; existing Admin
  Gateway; one no-tool, single-turn canonical request; sanitized evidence only.
- Completion standard: exact model identity, canonical SSE/persistence and
  Gateway accounting pass together; original integrity and exact cleanup pass.
- Actual result: pending read-only discovery and execution.
- Unverified inference: the cloned account is entitled to `hy3-preview`, the
  alias resolves without substitution, and a safe terminal Dream thread exists.

### R22 optimized prompt — prove exact upstream identity through the real alias

```text
Act as the model-routing contract owner. Read-only discovery corrected one
historical assumption: the production-shaped catalog does not expose a public
alias named `hy3-preview`. It exposes one enabled alias, `hy-preview`, whose
configured upstream model is exactly `hy3-preview`. The canonical Chat API is
required to submit a callable catalog alias and treats the browser value only as
confirmation of the server-saved selection.

Do not rename the cloned model, add an artificial alias, bypass catalog
selection, call the provider directly, or choose another model. Preserve the
real cloned catalog and set/confirm the cloned user's saved selection through
the canonical system-config API as `hy-preview`. Before a provider call, require
the isolated Admin `/v1/models` and Dream `/api/gateway/models` catalogs to show
that alias as callable; require the cloned database model row to have enabled
provider, usable encrypted credential, active pricing, and unique upstream
`hy3-preview`. Stop safely if any check fails.

Run the one bounded no-tool Agent turn using request alias `hy-preview`, because
that is the only production-valid identifier for the selected model. Prove from
the correlated Gateway request that `requested_model` is `hy-preview` and
`resolved_model` is exactly `hy3-preview`; where a sanitized provider-side model
field is available, require it to be exactly `hy3-preview` as well. This alias
translation is canonical model resolution, not fallback. Any other resolved or
upstream identity is a hard failure.

Retain every R21 isolation, privacy, single-terminal, persistence, accounting,
original-integrity and cleanup requirement. Report the alias/upstream
distinction explicitly so the result cannot be mistaken for a direct alias
match or a substituted model.
```

**Optional enhancers**

- Include a one-to-one alias-to-upstream cardinality assertion before and after
  the request so a concurrent catalog ambiguity cannot pass.

**R22 scope and completion standard**

- Goal: verify the user's exact upstream model through the production catalog
  contract without modifying catalog identity.
- Scope: `hy-preview` request alias and its sole `hy3-preview` upstream mapping;
  all R21 safety and evidence boundaries remain in force.
- Completion standard: both catalogs accept the alias, the correlated Gateway
  request resolves only to `hy3-preview`, the turn succeeds, and no fallback or
  clone-only alias rewrite occurs.
- Actual result: pending isolated catalog callability preflight and invocation.
- Unverified inference: the cloned subject's current subscription allowance
  makes `hy-preview` callable despite the source plan's entitlement layout.

### R23 optimized prompt — use source-compatible PG16 dump and restore tools

```text
Act as the isolated PostgreSQL validation-harness maintainer. The first R22
provider-free preflight stopped before Admin/Dream startup and before every
provider call. The owned PG16 target rejected a custom dump made by Homebrew
pg_dump 18 because it contained the PG18-only statement
`SET transaction_timeout = 0`. All source-integrity and cleanup assertions
passed.

Keep source and target on PostgreSQL 16. Select pg_dump and pg_restore clients
whose major version is exactly 16, preferably the binaries already present in
the running source PG16 container or an owned transient `postgres:16-alpine`
tool container. Never install into, restart, write files inside, or change the
configuration of the source container. Stream a binary-safe custom dump only
to the 0700 owned temporary directory; do not capture it as text, rewrite SQL,
strip unknown settings, switch the target to PG18, or weaken restore
`--exit-on-error`.

Record sanitized source-server, dump-client, restore-client and target-server
major versions and require all to be 16 before restore. Retain forced read-only
source sessions, source/clone logical fingerprints, uniquely labelled owned
container and volume, current migrations on the clone only, Product entitlement
preflight, no-provider early exit and every R22 cleanup assertion.

Re-run the provider-free preflight. Completion requires the PG16 clone to
restore exactly, the clone-only user to receive an authorized published plan,
both catalogs to accept `hy-preview`, model selection to persist, provider call
count to remain zero, and cleanup/source integrity to pass. Do not begin the
real model request in this repair run.
```

**Optional enhancers**

- Fail immediately if `pg_dump --version` and `pg_restore --version` do not
  report the same PG16 major as both source and target servers.

**R23 scope and completion standard**

- Goal: close only the dump/restore major-version incompatibility.
- Scope: validation harness tooling; no application, schema, catalog or model
  behavior change.
- Completion standard: provider-free R22 preflight passes end to end on PG16
  and all owned resources are removed.
- Actual result: complete. Source server, dump client, target server and restore
  client all reported major 16; the restored table fingerprint matched the
  read-only source snapshot and the provider-free catalog/subscription preflight
  reached success with exact cleanup.
- Unverified inference: none for dump/restore compatibility; provider behavior
  remains outside this deliberately provider-free round.

### R24 optimized prompt — make the real-model proof fail closed

```text
Act as the release-evidence contract reviewer. The PG16 provider-free preflight
now passes end to end with zero provider calls and exact cleanup, but independent
review found post-inference assertions that could fail late or accept incomplete
evidence.

Patch the verifier before any real call. Cast legacy `chat_message.parts` and
nullable `metadata` TEXT columns explicitly to JSONB. Assert the generated user
message identity and exact public text-part shape without emitting the text;
assert one non-partial, non-empty assistant text result, zero tool parts, no
Dream authority metadata on the fresh generic thread, stored Chat model alias
`hy-preview`, and a non-empty persisted SDK session equal to the
`message-final.sessionId` observed in SSE.

Treat the SSE response as a strict protocol. Require the base media type
`text/event-stream`; incrementally parse blank-line-delimited events across
arbitrary network chunks, accept comments, join multiple data lines, and fail on
malformed JSON or non-object frames. Require exactly one `message-final`, then
exactly one final `finish` as the last data event before EOF, with no frames
after finish, no error/tool/business-output frames, `finishReason=stop`, and no
cancellation.

Do not include raw subprocess stderr, request/response bodies, prompts, model
text, tokens or credentials in thrown errors or final output. Preserve only an
allowlisted phase, command label, exit class/status and the existing sanitized
receipts; transient raw diagnostics must not escape the 0700 owned area and may
be discarded.

Keep the intentional R22 boundaries: request the real catalog alias
`hy-preview` and require upstream/provider model `hy3-preview`; use a fresh
clone-only properly entitled subject because no terminal Dream workflow exists
and sending private historical context is unnecessary. Do not manufacture a
catalog alias or weaken authorization to satisfy a literal three-name equality.

Run syntax/static checks and the provider-free preflight again. Do not make a
provider request in this hardening round.
```

**Optional enhancers**

- Return only booleans/counts for text and metadata assertions so the verifier
  cannot accidentally serialize model or user content.

**R24 scope and completion standard**

- Goal: ensure the eventual real proof is both privacy-safe and semantically
  conclusive.
- Scope: validation harness and verifier assertions only; no runtime behavior
  or product catalog changes.
- Completion standard: static checks and provider-free clone preflight pass,
  while focused negative checks demonstrate malformed/order-invalid SSE and
  invalid persistence cannot pass.
- Actual result: complete. The verifier now fails closed on missing model
  contract, MIME/framing/order, malformed SSE, persistence/session/model/
  visibility mismatch and unsafe top-level errors. Twenty-four focused and
  adjacent tests passed; read-only PostgreSQL parsed the receipt SQL; the full
  provider-free clone preflight remained green.
- Unverified inference: the real SSE and persisted values satisfy these strict
  checks only after the separately planned real turn executes.

### R25 optimized prompt — make the real-data clone runner interruption-safe

```text
Act as a destructive-test safety engineer reviewing the isolated real-data,
real-model release harness before it is allowed to contact a provider.

Keep the selected production contract exact: the Dream request uses the
configured public alias `hy-preview`, while Gateway resolution and the provider
must report upstream `hy3-preview`; do not create an alias, retry another model,
or call a provider in this round.

Eliminate secret-bearing process arguments. Pass the source and clone database
URLs only through child environments or another non-argv channel, discard raw
child stderr, and ensure the verifier's top-level failure output contains only
an allowlisted phase and error class. Never emit provider text, prompt text,
session IDs, database URLs, credentials or private row content.

Run Admin from a disposable source checkout under the 0700 runtime directory,
reusing dependencies read-only, so Next build output and tsconfig rewrites never
touch the original Admin checkout. Preserve byte/logical fingerprints of the
source database and Git status of both original repositories.

Before creating a fresh generic thread, prove in the restored clone that the
newly generated clone-only canonical user has zero owned, safely eligible
terminal Dream threads. Scope the query to that user; terminal threads owned by
real users are private and must neither be selected nor block the privacy-safe
fallback. Report only the zero count and fallback classification.

Make SIGINT and SIGTERM fail-safe across every race window. Keep handlers active
through cleanup, stop tracked children whose exitCode/signalCode are both null,
and unconditionally attempt removal by the unique owned container and volume
names even if a signal arrives between Docker creation and the corresponding
flag assignment. Then verify ports, container, volume, private runtime, original
containers, source fingerprint, port 3000 listener and Git statuses. A cleanup
verification failure must fail the run with sanitized evidence.

Run syntax/static checks, focused negative checks where practical, an
independent source review, and the complete provider-free clone preflight. The
round is complete only if zero provider requests occur and every isolation and
cleanup assertion is true.
```

**Optional enhancers**

- Inject a deterministic interruption immediately after owned Docker resource
  creation to exercise the narrow flag-assignment race without a provider call.

**R25 scope and completion standard**

- Goal: make real-data isolation recoverable even under user interruption.
- Scope: the validation runner and verifier only; no product runtime/catalog
  behavior and no source-data mutation.
- Completion standard: review plus provider-free execution prove scoped fallback,
  no argv credential exposure, original-checkout zero-write and exact cleanup.
- Actual result: executable gates complete. A deterministic SIGINT immediately
  after owned-volume creation exited 130 and reported source/container/port/Git/
  private-runtime cleanup all true. The full provider-free clone then passed:
  the clone-only user had zero owned terminal Dream candidates, Admin ran from a
  disposable checkout, `hy-preview` uniquely mapped to `hy3-preview`, no
  provider was called, and every cleanup assertion was true.
- Unverified inference: none for the current provider-free isolation contract;
  independent review returned ACCEPT. Turbopack's external-symlink rejection
  was measured; the disposable Admin checkout uses Next's supported webpack dev
  mode without changing product source. Malformed future source-URL initialization
  remains a non-blocking hardening suggestion.

### R26 optimized prompt — execute one exact real `hy3-preview` turn

```text
Act as the release operator for the final, user-authorized real-model proof.
Every provider-free clone, interruption-cleanup, SQL, strict-SSE, persistence,
authorization and independent-review gate is green. Execute exactly one bounded
canonical Claude Agent turn against a disposable logical clone of the configured
real database; never mutate the source database or reuse a private real user's
thread/history.

Keep the production model contract intact. Submit the only configured callable
public alias `hy-preview` through Dream's canonical Chat thread endpoint and the
existing Admin Gateway. Require the cloned catalog to prove that alias uniquely
maps to enabled upstream `hy3-preview`, and after the call require the correlated
Gateway row's requested model to be `hy-preview`, resolved model to be
`hy3-preview`, and provider-reported response model to be exactly `hy3-preview`.
Do not fabricate an alias, call a provider directly, substitute another model,
fall back, or retry if this call fails or is rate-limited.

Use the generated clone-only canonical user with a real published plan
entitlement and positive allowance. Assert the settled Gateway request is bound
to a subscription entitlement. Send one fixed non-private instruction requesting
a minimal answer, with `resume=false`, `toolChoice=none` and `max_turns=1` in an
empty owned workspace. Do not print the instruction, provider response,
assistant text, session IDs, tokens, URLs, credentials, raw SSE or raw stderr.

Accept success only when the strict incremental SSE parser observes base MIME
`text/event-stream`, exactly one non-empty `message-final`, then exactly one
`finish` with `finishReason=stop` and `cancelled=false`, followed by EOF; reject
errors, tools, Dream business-output frames, malformed frames, duplicates or
late data. Require thread status not running after finish and REST history to
contain exactly one user and one assistant.

Verify durable facts without exposing content: exact user message ID and single
text part, one non-partial/non-empty/no-tool assistant, stored Chat model
provider/alias, no Dream authority metadata on the generic fixture, persisted
SDK session exactly equal to the SSE final session, and exact runtime contract
version. Require one and only one correlated Gateway request, settled succeeded
HTTP 200 with upstream request ID, reserve equal to capture plus release, and
zero remaining reserved tokens.

Always stop owned Admin/Dream processes, force-remove the unique clone container
and volume, delete the 0700 dump/workspace/runtime checkout, and prove source
fingerprint, existing Postgres/MinIO identities, port 3000 listener, owned ports
and both original Git statuses are unchanged. Emit only the sanitized boolean,
count, status, alias/upstream and cleanup receipt. Do not run a browser or
`--headed` in this round.
```

**Optional enhancers**

- None. A second request would violate this round's bounded-call contract.

**R26 scope and completion standard**

- Goal: prove the selected real upstream model on the converged canonical thread
  path with real catalog, credential, entitlement, pricing and accounting data.
- Scope: one provider request in an isolated clone; no browser and no product
  source change.
- Completion standard: every strict SSE/persistence/Gateway/ledger/model and
  cleanup assertion passes from that one call; otherwise stop without retry.
- Actual result: complete in one request with no retry. The Gateway receipt was
  `hy-preview` → `hy3-preview` → provider-reported `hy3-preview`, HTTP 200,
  settled/succeeded and entitlement-bound; reserve equalled capture plus release
  with zero reserved remainder. Strict SSE, exact Chat persistence/session,
  source integrity and every cleanup assertion passed. No prompt, response,
  session, token, URL or credential was printed.
- Post-run review boundary: the sanitized receipt did measure one text start,
  one non-empty delta, one text end and a non-empty DB assistant, but the verifier
  did not make non-empty ordered incremental/final text and fully projected
  public history hard success predicates. R28 closes those future false-positive
  paths without a second provider request; the disposed clone cannot provide a
  retroactive final-text boolean.
- Unverified inference: the exact `message-final.text` value for the removed R26
  clone is not retrospectively available. A terminal Dream-bound fixture was
  unavailable for the generated clone user; headed remains deferred.

### R27 optimized prompt — reconcile final evidence and reader-test the design

```text
Act as the final technical-doc owner and release design reviewer for the
implemented DreamAgent convergence. The runtime refactor and all locally
executable non-headed gates have completed, including one user-authorized real
Gateway request whose public alias `hy-preview` resolved to and was reported by
the provider as exact upstream `hy3-preview`.

Update `docs/design/dream-agent/**` and every surviving inbound Dream/Claude
Agent design link so documents describe the current source, not the original
proposal or an obsolete run-scoped public protocol. Reconcile the README,
architecture, interaction, lifecycle, Observer, migration, testing/acceptance,
diagnosis, formal review and prompt-round record. Preserve historical decisions
only when clearly labelled historical/recoverable; do not rewrite evidence as
if it had existed before implementation.

Record measured gates precisely: R17 isolated fake-provider production-shaped
chain; R19 backend broad/focused, Redis, frontend unit/type/lint/build and S01–
S14 headless evidence; R20 Admin canonical artifact assertion and TypeScript;
R24/R25 strict verifier, PG16 clone, provider-free and interruption cleanup;
R26 exactly one real request with strict SSE, one user/assistant, matching SDK
session, entitlement binding, balanced ledger, exact model identity and source/
resource cleanup. Do not include private content, response text, session IDs,
tokens, credentials or raw database details.

State limitations without weakening the result: no new headed run by explicit
user direction; no staging/canary/immutable rollback or production load test;
the real fixture was a fresh generic canonical thread for a clone-only entitled
user because that user had zero eligible terminal Dream runs, so R26 proves the
shared Chat runtime and Gateway path rather than a terminal Dream workspace
binding. Report the pre-existing Admin entitlement-enforcement concern as a
residual risk; the real proof did not exploit it because the receipt required a
non-null entitlement binding.

Perform a formal design review against current code: confirm no second Dream
Agent runtime/public SSE/transport/parser/reducer, Dream UI composes the shared
Chat thread contract, Observer is off-path and non-authoritative, workflow
permissions remain, ClaudeAgentService/EventBus/session ownership is unchanged,
single terminal and cleanup contracts hold, and `agent_runner.py` is untouched.
Give ACCEPT only if source and executable evidence support every item; otherwise
fix documentation or report a blocker, not an aspirational pass.

Run documentation source/dead-link/status scans and `git diff --check`. Then use
a fresh context reader to answer realistic architecture, security, migration,
model-evidence and reproduction questions from the design set alone and to find
ambiguity or contradictions. Repair any documentation-only gaps and repeat the
reader test until it can recover the intended facts. Do not call the provider,
run a browser, stage, commit or modify unrelated code.
```

**Optional enhancers**

- Keep command counts and residual gates in one acceptance table so later
  release operators cannot confuse local proof with deployment proof.

**R27 scope and completion standard**

- Goal: leave a truthful, reader-usable, final design/evidence system.
- Scope: Dream design docs, inbound links, formal review and read-only audits.
- Completion standard: source and reader tests agree on architecture, measured
  evidence, migration/security boundaries, reproduction and residual risks.
- Actual result: documentation reconciliation and source/link/status/diff scans
  passed; formal current-code review returns ACCEPT after the R28 independent
  verifier review. A no-context reader correctly recovered the one-runtime/live-
  owner model, Observer and permission boundaries, all requested R17–R28 counts,
  R26 model/entitlement/ledger facts and non-proof boundary, remaining deployment
  gates and formal verdict. It found no privacy leak or broken local link; its two
  stale-status observations were corrected in this closeout.
- Unverified inference: none for R27's documentation/readability scope. Headed,
  staging/canary, immutable rollback and production load remain deliberately
  unexecuted rather than inferred.

### R28 optimized prompt — close verifier false-positive seams without a retry

```text
Act as a release-evidence verifier maintainer. A single authorized real
`hy3-preview` request has already succeeded and must not be repeated. Its
sanitized receipt measured one `text-start`, one `text-delta`, one `text-end`,
one `message-final`, one `finish(stop)`, one visible persisted user and assistant,
matching SDK session, exact model routing, entitlement-bound settlement and
complete cleanup. A later independent review found two places where the generic
success predicate could have accepted weaker future evidence.

Strengthen `backend/script/verify_gateway_e2e.py` so a successful real proof
requires `message-final.text` to be a non-empty string without ever serializing
that string, exactly one text-start, at least one non-empty text-delta, exactly
one text-end, and ordering text-start → all text deltas → text-end →
message-final → finish → EOF. Continue requiring one terminal, no tool/error/
Dream business frame and exact MIME/chunk-safe parsing.

Extend the persisted-message private discriminator denylist with `visibility`,
`dispatch_status` and `dispatchStatus`. Validate the REST history projection,
not only role counts: require exactly one user and one assistant, the generated
user row to remain one exact text part, and the assistant projection to contain
one non-empty text part with no hidden/zero-visible row. Compare values in
memory, return only booleans/counts, and never print text, session IDs, metadata,
tokens, URLs, credentials or raw payloads.

Add focused positive and negative tests for empty final text, missing/empty or
misordered deltas, hidden visibility/dispatch metadata, and empty projected
history. Run the verifier contract tests, adjacent system-config/SSE tests,
syntax and diff checks, then obtain an independent read-only re-review. Do not
run the clone harness in real mode, contact a provider, run a browser or mutate
product runtime code. Preserve the already measured R26 result honestly: the
receipt proves actual incremental frame counts and DB non-empty content; the
removed clone means a new final-text boolean cannot be retroactively measured,
so rely only on the service's same-result construction plus tests and state that
boundary explicitly rather than issuing a second call.
```

**Optional enhancers**

- Make projected-history checking a pure helper so malformed fixtures can be
  tested without HTTP or a database.

**R28 scope and completion standard**

- Goal: eliminate two false-positive paths in future real-model evidence.
- Scope: verifier plus focused no-provider tests and independent review.
- Completion standard: all negative fixtures fail closed, positive fixtures
  pass, output remains sanitized and review returns ACCEPT.
- Actual result: verifier/test implementation complete. Success now requires a
  nonblank `message-final`, exactly one text start, at least one meaningful text
  delta, exactly one text end and the strict terminal tail; whitespace-only
  deltas may coexist but cannot satisfy the meaningful-delta requirement.
  Visibility/dispatch private discriminators are denied and REST history must
  equal the exact visible canonical projection. The focused/adjacent run passed
  128 tests plus 37 subtests, with no provider call and no product runtime or
  `agent_runner.py` edit. Independent re-review then passed 19 directed tests and
  returned ACCEPT with no new false-positive path, privacy leak or blocker and
  no provider call.
- Unverified inference: `message-final.text` for the removed R26 clone follows
  the same non-empty result used by the verified DB assistant; no second real
  call is permitted to manufacture stronger retroactive evidence.

### R29 optimized prompt — final no-provider/no-browser audit

```text
在不调用供应商、不启动浏览器、不运行 `--headed`、不改动受保护
`agent_runner.py`、不触碰既有容器/端口/用户数据的前提下，对 DreamAgent 重构执行
最终可复现审计：验证新设计文档相对链接与当前状态一致；确认生产代码已无旧
Dream Event/run-scoped SSE/parser/reducer 调用；确认 Dream 仅组合共享 Chat runtime；
复核受保护文件哈希、主仓库与 Admin 的 `git diff --check`、临时资源完全清理；
仅以可恢复方式移走本轮生成的 Python 3.12 缓存。完成标准是所有检查有明确证据，
任何未执行项如实标注，不进行第二次真实模型调用。
```

**Optional enhancers**

- 将审计命令与结果摘要写入 `prompt-rounds.md`，并用独立 fresh-reader
  问答验证文档能单独解释协议、权限、生命周期、迁移与验证边界。

**R29 scope and completion standard**

- Goal: 在无供应商、无浏览器的前提下完成最终可复现审计。
- Scope: 文档链接/状态、旧协议生产引用、共享 Chat runtime、
  `agent_runner.py` 哈希、主仓库/Admin diff-check、资源与 Python 3.12
  缓存清理。
- Completion standard: 证据齐全，未执行项如实标注，可恢复地处理本轮缓存，
  不第二次调用模型，不越过受保护 runtime 或用户资源边界。
- Actual result: complete. Markdown relative-link/status review passed and the
  context-free reader recovered all 10 requested architecture, authorization,
  evidence and limitation facts. Production scans found no old Dream event,
  run-scoped SSE, adapter, hook or reducer consumer; the Dream feature owns no
  `useChat` and composes canonical `ChatPanel`. `agent_runner.py` matched HEAD at
  SHA-256 `cef92a1fe030338e09ebecab91436f0e5bdb9bcfdccdd2c5aa7420a9a2f904b1`.
  Main and Admin `git diff --check` both exited zero. No `ink.r22.run` container
  or volume, `ink-r22-real-model-*` temporary directory, or owned process
  remained; the existing Admin listener stayed PID 96344. Four exact ignored
  Python 3.12 caches generated by R28 were moved recoverably to
  `/Users/dmeck/.Trash/ink-r28-pyc.0gX1Cz/`. No provider or browser was invoked.
- Unverified inference: none. Current-candidate headed Chromium,
  staging/canary, immutable rollback and production load remain explicit
  unexecuted gates rather than inferred passes.

### R30 optimized prompt — persistent-goal completion audit

```text
以当前工作树和可执行证据为准，对 DreamAgent 重构逐条映射完整目标：检查唯一
thread/SSE runtime、旧协议删除、Observer 非权威性、会话持久化、跨页面恢复、
Dream Flow 权限、文档体系、代码复杂度和所有验收门禁。对每条要求区分“直接
证明、间接证明、缺失或被用户暂缓”；不得把搜索无结果当成完整证明，不调用
真实模型，不运行新的 `--headed`。对可在当前范围补强的缺口立即实现并验证；
仅把确实受 headed 暂缓约束的门禁保留为未完成。
```

**Optional enhancers**

- 形成可追踪的 requirement→source→test→status 矩阵，并让最终 headed 恢复时
  只需执行一个语义等待、`workers=1` 的收口场景。

**R30 scope and completion standard**

- Goal: 对持久目标执行逐条、当前态、不可降级的完成性审计。
- Scope: canonical runtime、legacy deletion、Observer、persistence、Dream Flow、
  documents、complexity、focused backend/browser/static/build and cleanup evidence.
- Completion standard: 每项要求有直接证据或明确标为未完成；不调用 provider、
  不运行 headed、不把历史 PASS 或搜索无结果单独提升为整体完成。
- Actual result: authorized non-headed scope complete. Backend focused acceptance
  passed 71 tests plus 37 subtests; S01–S10 passed 10/10 in headless Chromium with
  one worker; TypeScript, ESLint (zero errors), production build, legacy source/
  OpenAPI/bundle inventories, protected runner hash and diff checks passed.
  Ports 5173/8765 were free after the run, and the exact Playwright result folder
  plus one generated test bytecode file were moved recoverably to
  `/Users/dmeck/.Trash/ink-r30-qa.SbIeo1/`. The run left no Playwright controller
  or listener. A system inventory found 58 older PID-1 Playwright browser
  processes in macOS `UEs` state; exact SIGTERM and SIGKILL did not remove them,
  so R30 does not claim global process cleanliness. No provider or headed browser
  ran.
- Unverified/incomplete: the persistent objective still requires a current-
  candidate visible headed Chromium run. The user has temporarily deferred it,
  so the goal remains active. The kernel-stuck pre-existing browser processes,
  staging/canary, immutable rollback, production load and the disclosed Admin
  entitlement-enforcement gap are separate environment/release risks.

### R31 optimized prompt — correct browser evidence scope

```text
审计 DreamAgent 验收文档中所有 “S01–S14 headless/Chromium” 声明，并与
可执行测试发现结果逐项核对。将 S01–S10 明确标为真实 Chromium 浏览器场景，
将 S11–S14 明确标为后端/源码/OpenAPI 契约；不得用非浏览器测试冒充
headed/headless 证据，也不得为纯 Observer 顺序或路由删除机械增加 UI 测试。
更新测试命令、证据矩阵、最终 checklist 和历史轮次说明，同时保留跨层
S01–S14 总矩阵。完成标准是每个 ID 的执行层、命令、结果和未运行门禁都准确一致。
```

**Optional enhancers**

- 用 Playwright `--list` 和 pytest collection 证明发现数量；扫描整个新设计体系，
  确保不再出现未经限定的 “S01–S14 headless Chromium PASS”。

**R31 scope and completion standard**

- Goal: make browser evidence claims match executable discovery exactly.
- Scope: the Dream design set, Playwright S01–S10 spec, backend S11–S14
  acceptance classes and headed command boundary; no product implementation.
- Completion standard: retain the 14-ID cross-layer matrix while labelling each
  ID's real execution layer; no non-browser contract may be presented as
  Chromium evidence.
- Actual result: complete. `npx playwright test ... --list --browser=chromium`
  discovered exactly 10 S01–S10 tests. Pytest collection found the S11–S14
  Observer, replay, terminal and migration acceptance classes (11 tests total
  including the two S04 server-confirmation contracts). Current status tables,
  commands, matrix rows and historical R19 evidence now distinguish those
  layers. No product code, provider request or headed browser execution occurred.
- Unverified/incomplete: current-candidate headed Chromium still applies to the
  user-visible S01–S10 suite and remains explicitly deferred.

### R32 optimized prompt — final visible-browser acceptance after reboot

```text
在用户重启机器并明确允许 `--headed --workers=1` 后，以当前 DreamAgent
候选工作树完成最后的可见 Chromium 验收。先确认 Playwright/Chromium 可用、
5173/8765 无冲突、S01–S10 正好发现 10 个用例且测试源码没有固定 sleep；然后
使用确定性测试 API、语义等待和单 worker 可见运行完整 S01–S10。失败时保留
failure-only trace、截图/视频及安全的 console/network 诊断；成功后确认浏览器、
驱动、服务监听和报告临时文件全部释放。随后复跑 S11–S14 后端/源码契约，复核
旧 Dream 协议硬删除、唯一 production `useChat`、受保护 `agent_runner.py` 哈希、
diff 与文档链接。不得发出第二次真实模型请求；既有一次 `hy-preview` →
`hy3-preview` 成功证据继续有效。只有所有本地目标门禁具备直接证据时，才把
持久目标标记完成；部署、回滚、负载与已披露 Admin 风险仍要单独标注。
```

**Optional enhancers**

- 记录 Playwright 的精确发现数、总耗时、命令退出码和跑后进程/端口空清单；
  历史轮次中的“headed deferred”保持为当时事实，仅更新当前权威状态。

**R32 scope and completion standard**

- Goal: close the final user-visible Chromium gate for the exact current
  DreamAgent candidate after reboot.
- Scope: S01–S10 headed Playwright, S11–S14 backend/source acceptance,
  legacy/runtime/diff/link evidence and owned-resource cleanup; no product
  change and no provider request.
- Completion standard: 10/10 visible browser PASS with semantic waits and one
  worker; fresh S11–S14 PASS; no legacy runtime, runner edit, browser/driver,
  listener or generated-report residue; current docs accurately record the
  result and keep deployment-only gates separate.
- Actual result: complete. Playwright discovered exactly S01–S10 and the visible
  Chromium command passed `10 passed (14.4s)`. A fresh S11–S14 subset passed
  `9 passed, 2 deselected` with only existing FastAPI deprecation warnings.
  The fixed-wait scan was empty; legacy source checks, the sole production
  `useChat` owner and protected-runner SHA-256
  `cef92a1fe030338e09ebecab91436f0e5bdb9bcfdccdd2c5aa7420a9a2f904b1`
  passed. Post-run process and port inventories were empty, and the tracked
  Playwright status file matched Git with no new report artifact.
- Unverified/incomplete: no staging/canary, retained immutable artifact/rollback
  exercise or production load run is claimed. The pre-existing Admin
  entitlement-enforcement risk remains disclosed. These do not change the R32
  repository/local acceptance result.

### R33 optimized prompt — complete Dream business interaction design

```text
基于当前生产代码、测试、DreamAgent 收敛设计和 Story Workspace 历史 PRD，建立一份
可作为业务真值入口的 DreamAgent 全业务交互设计。不要只复述 lifecycle 状态图；枚举
用户入口、launch、runtime 激活、内容产出/读取/编辑/确认、共享对话、工具确认、
Observer、私有命令恢复、Guidance、Stop/Cancel、Retry、Execution、Episode、artifact、
Story Index、最终完成、权限并发和通用输出边界。每项必须给出独立 Mermaid
sequenceDiagram、参与者、权威 owner、读写副作用、权限、失败/重放行为和源码/测试
证据。未接 UI、未自动恢复或仍需产品判断的能力必须明确标注，不得画成已交付事实；
不得恢复第二套 Dream SSE/runtime/reducer，也不得让 workflow/Observer 反向控制 thread。
```

**Optional enhancers**

- 增加 B01–B21 覆盖矩阵、API 副作用表、业务方待确认清单和读者验收提问。

**R33 scope and completion standard**

- Goal: make the full Dream product behavior reviewable independently of the
  lower-level thread lifecycle diagrams.
- Scope: current code/test evidence and design documentation only; no product
  implementation or provider/browser run.
- Completion standard: every in-scope business capability has an independent
  sequence and evidence; historical implementation assumptions are separated
  from business requirements.
- Actual result: complete. `business-interaction-design.md` catalogs B01–B21
  and includes 22 sequences (one master plus one per capability), an API side-
  effect table, eight product decisions and ten reader questions. It also
  corrected two tempting overclaims: generic Guidance has no durable startup
  reconciler, and Execution access uses accepted rather than dispatched.
- Unverified/incomplete: the eight product choices in §26 require business-owner
  confirmation; the completed real `hy3-preview` generic-thread proof is not
  represented as a terminal Dream workspace-binding proof.

### R34 optimized prompt — validate every business diagram and evidence seam

```text
修复 DreamAgent 全业务设计的 Mermaid 语法、能力覆盖标记和相对链接校验问题，并对
全部图执行项目内真实 Mermaid parser。要求主链和 B01–B21 共 22 张图全部解析；每个
能力恰有一张 sequenceDiagram，并有业务意图、规则/权限/边界和证据；不得使用
stateDiagram 冒充交互。链接校验要 URL-decode 合法路径，不能把既有带编码 PDF 链接
误报为死链。随后以源码反证确认唯一 production useChat、旧 Dream runtime 零调用，
以及 Guidance/Retry/Cancel 未接页面的事实，不得通过减少覆盖或忽略 parser 错误过关。
```

**Optional enhancers**

- 输出每张图的 capability ID；对所有新旧设计入口执行相对链接检查。

**R34 scope and completion standard**

- Goal: turn the business catalog into an executable documentation contract.
- Scope: business document notation/labels and linked design indexes only.
- Completion standard: 22/22 real parser PASS, B01–B21 structural coverage,
  no state-diagram substitution, no broken relative link and source boundary
  counter-checks.
- Actual result: complete. English semicolons in Mermaid messages were replaced;
  missing rule/evidence labels were made explicit. The project Mermaid 11.16
  parser passed MASTER + B01–B21, the coverage audit passed all 21 IDs, and 55
  relative links passed after correct URL decoding. Production source still has
  one `useChat` in `ChatPanel`, no legacy Dream runtime caller, no Dream page
  Guidance/Retry/Cancel caller, a Dream-context generic-projection early return,
  and Guidance `dispatched: false` behavior.
- Unverified/incomplete: no product test was rerun because R34 changed only
  documentation; visual differences between Markdown renderers remain possible.

### R35 optimized prompt — formally review business understanding

```text
对 business-interaction-design.md 做正式业务理解审查。逐项核对 B01–B21 是否覆盖
Dream 用户任务、owner、允许/禁止副作用、权限、失败和证据；拒绝旧 Dream 协议换名、
未接 UI/未恢复能力伪装为已交付、thread/workflow 自动互控三类误判。确认每项时序图
可解析且能独立审查，将开放产品决策与实现缺陷分开，并同步 README、测试契约、
设计审查和 prompt 轮次记录。结论必须是接受、修改后接受或拒绝。
```

**Optional enhancers**

- 用源码反证和一个业务方可逐项回复的决策清单支撑最终结论。

**R35 scope and completion standard**

- Goal: decide whether the documented behavior is an accurate, complete and
  non-duplicative representation of the current Dream business.
- Scope: B01–B21 and canonical documentation/source seams; documentation only.
- Completion standard: no second runtime or invented behavior, all decisions
  visible, all diagrams/links/coverage gates green.
- Actual result: **修改后接受 → 接受**. The initial parser punctuation and
  inconsistent review labels were corrected in R34. Final review found no
  second conversation transport/reducer, no Observer reverse control and no
  invented Guidance/Retry/Cancel delivery. Eight product-owner choices remain
  explicitly open rather than silently resolved.
- Unverified/incomplete: business-owner decisions have not yet been supplied;
  changing one may reopen its capability design and implementation.

### R36 optimized prompt — complete the Admin/Drizzle authority cutover

```text
作为跨仓库 PostgreSQL Schema 权威切换验证负责人，验证当前 Dream/Admin 工作树已
实现 capability-only 切换：Dream 不存在 Alembic 配置、revision、依赖、迁移/adoption
模块或 PostgreSQL DDL 生成器；所有新库与旧 06/07 接管只由 Admin Drizzle 0032
完成；20260811_07 原需求在 Admin 中既有可执行索引/capability 合同，也有不可执行
原文归档。运行 Dream 聚焦与合理范围后端测试、Admin migration/unit/type/lint、Admin
PostgreSQL cutover E2E、真实 43+5 数据 E2E、静态调用方扫描和 git diff --check。只使用
明确命名的一次性 PostgreSQL，不修改用户真实业务数据，并确认容器/进程清理。
```

**Optional enhancers**

- 在 Admin cutover E2E 中由 0032 自身的已审查 DDL 构造旧 06/07 夹具，证明测试不再
  反向依赖 Dream 仓库。

**R36 scope and completion standard**

- Goal: make Admin/Drizzle the sole executable DDL/version authority and retain
  the `20260811_07` business requirement without a Dream revision runner.
- Scope: both repositories' migration callers, Dream capability gate,
  dependencies, legacy data validation, docs and disposable PostgreSQL E2E.
- Completion standard: Dream has no executable Alembic/PG DDL artifacts;
  Admin independently passes fresh/06/07/partial/concurrent/idempotent/check;
  real 43+5 import remains exact; no user database is mutated.
- Actual result: complete for repository/local scope. Dream migrations,
  Alembic/adoption modules, PG DDL renderer/static SQL and dependencies were
  removed; runtime/importer are capability-only. The original seven revision
  texts are frozen as non-executable `.py.txt` files under Admin. Admin cutover
  E2E passed fresh, 06 with/without the lookup index, 07, partial/unknown atomic
  failure, two concurrent migrators, idempotency and `--check`, with 33 receipts
  and three capabilities. Real data E2E passed 48 tables/4,930 rows, idempotency,
  conflict blocking and append-only SQLSTATE `55000`. Admin unit 378/378,
  TypeScript and ESLint passed. Dream affected suites passed 82/82 plus 53
  subtests; after isolating Gateway environment variables in the affected
  tests, the complete project suite passed 1,955/1,955 with 22 skipped and 655
  subtests passed.
  The full disposable Dream business harness then passed the Admin-only
  `0029→0032` artifact backfill, thread index proof, PostgreSQL runtime 4/4,
  helpers 2/2, artifact contracts 61/61, and three real Chromium scenarios
  (Dream model/mobile, producer chain, Admin review), with zero external
  Provider calls and owned-resource cleanup.
- Unverified/incomplete: staging/production 06/07 inventory, PITR, migrator
  role/ACL and rollout receipts remain environment-owned checks. No real model
  was repeated because this round changes only schema authority; the business
  harness used its deterministic local provider.

## Round 0 — Establish the repository baseline

**Prompt/question**

> Determine whether Chat and Dream are separate runtimes, separate Git branches,
> or separate public protocols. Cite exact commits, paths and lines.

**Evidence**

- `git merge-base platform story-workspace` returns `eedde94`, the
  `story-workspace` tip.
- `backend/agent_stream_events.py:23-69` and
  `backend/claude_agent/event_bus.py:62-169` show one normalized runtime bus.
- `backend/claude_agent/chat_stream_adapter.py:10-27` and
  `backend/services/story_workspace/dream_stream_adapter.py:37-208` show two
  browser encoders.
- `61f70fc` introduced `/dream-agent/events`; `b5b986c` separated normalized
  internals from public adapters.

**Decision/artifact effect**

Record “linear history, one runtime, two public conversation protocols” in
[Diagnosis](./diagnosis.md). Do not call this a branch fork.

**Exit condition**

Current call chains, public differences and callers are independently locatable
from the diagnosis.

## Round 1 — Challenge the current two-adapter architecture

**Prompt/question**

> If Dream already persists and runs on a Chat thread, what user/business
> requirement requires a second public conversation SSE contract?

**Evidence**

- Dream launch/follow-up reuse `ClaudeAgentRunRequest` and the same factory.
- Chat calls Dream snapshot/confirmation as a reverse bridge at
  `frontend/src/components/chat/ChatView.tsx:355-388` and
  `ToolConfirmationDock.tsx:68-108`.
- Dream independently implements parser, cursor, reducer, polling and reconnect
  at `useStoryWorkspaceDreamAgent.ts:760-1205`.

**Decision/artifact effect**

Supersede independent Dream public SSE. Dream conversation uses Chat thread
history/SSE/send/confirm/stop; Dream-specific business projection remains
separate.

**Exit condition**

[Architecture](./architecture.md) has one browser conversation plane and no
Dream event encoder in the target graph.

## Round 2 — Protect trusted Dream context

**Prompt/question**

> Can Dream simply call generic Chat POST after changing its SSE URL?

**Evidence**

- Generic Chat POST does not currently attach `StoryWorkspaceDreamRunContext`.
- Context changes plugin packing, MCP environment, runtime activation and source
  provenance in `backend/claude_agent/service.py:935-970,1203-1226,1295-1304,
  1495-1600`.
- Existing gateway derives exact actor/run/thread/Deck authority at
  `story_workflow_application.py:1266-1329`.

**Decision/artifact effect**

Add a proposed server-side binding resolver before Chat request construction.
The browser supplies no run/context authority.

**Exit condition**

Migration and testing mark resolver/context tests as hard pre-cutover gates.

## Round 3 — Remove the browser run selector

**Prompt/question**

> Does adding `storyWorkspaceRunId` to Chat POST merely recreate run-scoped
> identity in the conversation protocol?

**Decision/artifact effect**

Yes; remove it. Chat send/history/status/stream/confirm/stop carry `threadId`
only. The authenticated server reverse-lookups Dream binding by actor + owned
thread. Dream uses `workflowRunId` only for business REST.

**Exit condition**

No target Chat request in this directory contains a run selector.

## Round 4 — Correct unique-row lookup for retries

**Prompt/question**

> Is more than one Workflow Run row for an actor/thread always corruption?

**Evidence**

`WorkflowRunService.retry_run` permits a terminated unsuccessful attempt to be
retried and preserves `source_voice_thread_id` while setting `retry_of_run_id`:
`backend/services/workflow/run_service.py:171-209`.

**Decision/artifact effect**

Validate the retry graph and choose its unique unsuperseded leaf. Zero attempts
is generic Chat. Multiple independent leaves, a missing parent, cycle or frozen
source/binding mismatch is 409. Creation time/status is never a selector.

**Exit condition**

Architecture, interaction, lifecycle, migration and acceptance matrices all
include legal linear retry and invalid graph cases.

## Round 5 — Bound the Observer

**Prompt/question**

> Does conversation convergence require a new durable Observer event store or
> checkpoint subsystem?

**Decision/artifact effect**

No. `DreamLifecycleObserver` subscribes to `NormalizedAgentEvent` on the
existing EventBus, applies strict process-local sequence and bounded
`(eventId,threadId,turnId)` dedup, projects activity/waiting/exactly-one terminal
hints, and calls an injectable business sink. Existing owning services/DB remain
durable truth. Restart reconciles a requested run from those facts.

**Exit condition**

[Observer design](./observer-design.md) forbids an Observer table, outbox,
checkpoint or public SSE and contains failure-isolation acceptance.

## Round 6 — Exercise the complete interaction surface

**Prompt/question**

> Does the target work for every required navigation, confirmation, subagent,
> stop, failure, reconnect, Observer and migration path?

**Decision/artifact effect**

[Interaction design](./interaction-design.md) contains 14 independent Mermaid
sequences:

1. Dream normal send/incremental output.
2. Dream → Chat switch.
3. Chat → Dream switch.
4. Approve/reject/AskUser.
5. Subagent start/run/complete.
6. Main Agent Stop/cancellation.
7. Failure before output.
8. Failure after partial output.
9. Disconnect/reconnect.
10. Refresh/history recovery.
11. Observer projection.
12. Observer replay/duplicates.
13. Normal exactly-one terminal.
14. Legacy protocol migration.

**Exit condition**

[Testing and acceptance](./testing-and-acceptance.md) maps S01–S14 to explicit
assertions and priority.

## Round 7 — Make replacement direct and old protocol deletable

**Prompt/question**

> What prevents migration scaffolding and the old Dream protocol from becoming
> permanent in the repository?

**Decision/artifact effect**

Replace production Dream call sites and hard-delete old routes, adapter, hook,
contracts, bridges and tests in the repository change. Roll back by deploying
the prior immutable build. An infrastructure canary is optional, but must not
add a repository feature flag or make both protocols supported at once.

**Exit condition**

[Migration plan](./migration-plan.md) has path-level deletion ownership, source
scans and immutable-build rollback.

## Implementation prompt templates

These prompts are reusable work packages. They intentionally ask for evidence
rather than assuming completion.

### I1 — ChatPanel-first frontend convergence

> Keep `ChatPanel` as the only `useChat`/live reducer owner and make the Dream
> wrapper compose it directly. Extract only history→status→reconnect nonce,
> pending/settled IDs, generation guard and post-EOF hydration needed unchanged
> by ChatView and Dream. Add no app-wide Provider or second controller. Apply the
> same private-control-row/zero-part/export visibility contract. Cover Stop
> success, non-2xx, timeout, `running=true`, historical subagent and unmount.

Expected evidence: imports proving both surfaces use `ChatPanel`, no second
`useChat`/Dream parser, visibility fixtures, type/lint/build, headless then headed
cross-surface trace, semantic waits and zero leaked browser/server process.

### I2 — Binding resolver and canonical policy

> Implement actor + owned-thread Dream attempt lookup with retry graph validation
> and one unsuperseded leaf. Reuse existing actor-scoped Dream-files `threadId`;
> add no re-entry API. At the service callback/per-turn store, atomically register
> bounded server policy+Future before approval publish, then validate/atomically
> resolve exact active identity for AskUser/network/reject-only. Clean all state
> on timeout/reject/cancel/terminal/context/session/factory close. Accept no run
> or turn selector from the browser and do not modify `agent_runner.py`.

Expected evidence: query/graph and Dream-files authorization tests, generic Chat
zero-attempt regression, register-before-publish/atomic concurrency/cleanup tests,
no new endpoint/field and empty protected-runner diff.

### I3 — Coordinator-owned `DreamLifecycleObserver`

> Make the thread factory own a minimal `DreamLifecycleCoordinator` per trusted
> turn: attach the EventBus subscriber before context assembly/producer publish,
> hand off through a bounded non-blocking queue to a sink worker, assign stable
> identity/order and exactly-one terminal, and fence late sink writes. In one
> finally path unsubscribe, cancel and await on context failure, terminal/
> sentinel, Stop, task exception, eviction and factory aclose. Add no persistence
> and preserve `ClaudeAgentService` normalized-event/persistence ownership.

Expected evidence: S11/S12/S13, enabled/disabled frame equivalence, queue/memory
bounds, slow/raising/late sink, every close path, zero residual subscriber/task/
Future/cache and no schema migration.

### I4 — Direct call-site replacement and hard deletion

> Replace every production Dream conversation caller with Dream wrapper +
> existing ChatPanel + minimal hydration. Migrate the launch, business-
> confirmation and message/episode internal drains at the three reviewed call
> sites to canonical normalized run_events/Coordinator while preserving their
> claim/ack semantics. Remove old routes, adapter, hook, contracts, bridges and
> obsolete tests. Add source/route scans proving no old protocol or adapter
> consumer and test rollback by deploying the prior immutable build.

Expected evidence: caller inventory diff, final route/source scans, acceptance
suite, immutable-build rollback exercise and Git recovery SHA.

Optional deployment note: release engineering may canary the new immutable build
against the prior build. That is a deployment option outside this repository
round; it must not introduce a code-level cohort flag or retain both protocols in
the final source tree.

## Reader-review questions

A context-free reviewer should be able to answer all of these using only this
design set:

1. Which protocol does Dream use after migration?
2. Why is no run ID sent to Chat?
3. How is a legal retry chain distinguished from conflicting bindings?
4. Who owns durable Workflow Run truth?
5. What may `DreamLifecycleObserver` store?
6. Why is `message-final` not a terminal?
7. How do Dream → Chat and Chat → Dream preserve a running turn?
8. What replaces the Dream confirmation endpoint without weakening policy?
9. Which exact gates force legacy deletion?
10. What evidence changes a proposed capability to verified?

If a reviewer cannot answer one unambiguously, fix the owning normative document
instead of adding an explanation only here.

## Round 38 — Correct the Dream business contract and integration boundary

**Current-round objective**

Correct the DreamAgent design and implementation after business review: make the
Admin Project/Episode Artifact contract explicit in Dream, replace Story Workspace
execution diaries with functional design documents, move Dream runtime assembly
into `ClaudeAgentService.assemble_context`, use a class-based `DreamObserver`
registered with `SessionObserverRegistry`, preserve the Claude Agent entry point
and wire contract, model frontend DTO projection with standard classes, define the
complete Dreamflow tool boundary, and remove the unsupported `continuing` stage.

**Optimized Prompt**

> Work directly in `/Users/dmeck/project/ink-dream-memory` and, where the shared
> database or authoritative Story contract requires it, in
> `/Users/dmeck/project/ink-admin-memory`. Treat Admin's
> `docs/design/modules/story-business/admin-dream-interaction-design.md` as the
> authoritative Project/Episode Artifact contract. First convert the Dream and
> Story Workspace documentation into normative, module-oriented business design:
> define stable Project/Episode/Story identity, sealed artifact files, revisions,
> writer/read boundaries, authorization, reconciliation and degradation; retain
> requirements and final behavior only and delete execution records, review logs,
> change histories and test diaries from `docs/design/story-workspace`. Add complete
> Dreamflow tool/Agent interaction sequences and boundaries.
>
> Then refactor without changing Claude Agent HTTP/SSE messages or the protected
> Agent entry/runner. Resolve the owned Dream context from the canonical thread ID
> inside `ClaudeAgentService.assemble_context`; do not pass Dream fields through
> `ClaudeAgentRunRequest`, the router or the browser. Replace closure-based runtime
> initialization with named classes/services. Register a Dream-specific
> `DreamObserver` in `SessionObserverRegistry`; let it own Dream post-processing,
> idempotent business projection and cleanup while remaining unable to control the
> main Agent lifecycle or interrupt SSE. Replace router field allowlists with typed
> DTO/projector classes. Remove `continuing` from documentation, backend/frontend
> enums, transitions, copy, tests and the Admin-owned PostgreSQL schema using a new
> forward Drizzle migration that safely adopts existing rows. Preserve workflow
> authorization, thread ownership and exactly-one terminal behavior. Do not touch
> `backend/libs/claude_agent_kit/server/agent_runner.py` and do not discard existing
> worktree changes.
>
> Before implementation, conduct a formal design review and require “accepted” or
> “accepted after modification”. Verify with focused backend/frontend contract
> tests, source scans, type/lint/build checks, database migration replay/adoption
> checks where available, and `git diff --check`. Record facts separately from
> unverified assumptions.

**Optional Enhancers**

- Produce a before/after ownership table for every lifecycle and artifact field.
- Add contract tests proving generic Chat threads never receive Dream context and
  Dream/Chat switching needs only the canonical thread ID.
- Add migration fixtures for an existing `continuing` row and history sequence.

**Scope checked or modified**

- Dream Agent design, Story Workspace functional design and Admin Story contract.
- `ClaudeAgentService` assembly, `SessionObserverRegistry`, Dream observers and
  runtime activation; router DTO projection; Dreamflow boundaries.
- Workflow lifecycle in Dream code/frontend and Admin-owned Drizzle DDL.
- Relevant tests and references; no unrelated global refactor.

**Completion standard**

The Project/Episode Artifact contract is unambiguous; Story Workspace contains
only module business design; no public Claude Agent field or entry function is
changed; Dream context comes exclusively from server-side thread mapping during
assembly; Dream post-processing is observer-owned; no closure callback initializes
Dream runtime; `continuing` is absent from live design/code/schema; focused tests
and source scans pass without altering the protected runner.

**Actual result and unverified inferences**

Completed. Added the normative Project/Episode Artifact contract and Dreamflow
tool boundary; rebuilt `docs/design/story-workspace` as eight module-oriented
business documents and removed execution/review/test-history records. Source and
Admin DDL inspection confirmed each originally reported integration defect. The
only historical-state mentions retained outside live contracts are the mandatory
Prompt Architect audit and one-way migration record.

## Round 39 — Formal review of the corrected design

**Current-round objective**

Review the corrected Artifact, Story Workspace, Dreamflow, context-assembly and
Observer design before changing runtime code.

**Optimized Prompt**

> Review the Round 38 design as an independent architecture gate. Verify that
> Project/Episode/Story identity matches the Admin authority; Story Workspace
> documents contain only current module requirements; Dreamflow tools own
> revision-bound business writes but not conversation lifecycle; the browser and
> `ClaudeAgentRunRequest` carry no Dream context; context lookup and activation
> happen in `ClaudeAgentService.assemble_context` without a closure; the Claude
> Agent route, SSE contract, protected runner and Phase 3 entry call remain
> unchanged; a class-based `DreamObserver` registered in
> `SessionObserverRegistry` owns only failure-isolated business observation and
> cleanup; router output projection uses typed DTO classes; and removal of the
> `continuing` state has an explicit forward-data migration. Return ACCEPT,
> ACCEPT AFTER MODIFICATION or REJECT with blocking findings. Do not begin code
> changes until blocking design findings are incorporated.

**Optional Enhancers**

- Trace one generic Chat turn and prove the Dream resolver is a no-op.
- Trace one Dream-bound turn and identify every authority check and cleanup owner.

**Scope checked or modified**

- New Dream Artifact/Dreamflow documents and module-only Story Workspace set.
- Target `ClaudeAgentService`, Observer registry, DTO and Workflow-state seams.
- Admin-owned lifecycle DDL adoption requirement.

**Completion standard**

The review has a formal verdict, every blocking finding has an owning design
change, and implementation can proceed without changing public Agent protocol or
creating a second lifecycle truth source.

**Actual result and unverified inferences**

Completed with verdict **ACCEPT AFTER MODIFICATION -> ACCEPT**. Eight blocking
findings were closed in the design: Artifact identity/ownership, module-only Story
Workspace documentation, assembly-time named activation, registered
`DreamObserver`, typed router projection, complete Dreamflow boundaries,
server-side Thread mapping and forward-only lifecycle-data adoption. The accepted
design did not authorize any Claude Agent wire or runner-entry change.

## Round 40 — Implement the accepted integration correction

**Current-round objective**

Implement the R39 accepted design in backend, frontend and Admin-owned DDL while
preserving the canonical Agent entry and wire contract.

**Optimized Prompt**

> Refactor the current Dream migration worktree in the smallest coherent units.
> First remove request/router/dispatcher Dream context injection and resolve a
> named internal Dream context from actor + canonical Thread inside
> `ClaudeAgentService.assemble_context`. Move runtime activation into that phase
> through a named class/service using verified server facts; delete the SDK-init
> callback closure but leave Phase 3 `run_streaming` and `agent_runner.py`
> unchanged. Next define `DreamObserver` as a class registered in
> `SessionObserverRegistry`, move coordinator attach/close ownership out of
> ThreadFactory, and preserve bounded failure-isolated projection. Replace
> router pseudo-DTO field constants with standard DTO/projector classes without
> changing public JSON. Finally remove the invalid post-confirmation Workflow
> state from Dream backend/frontend and add a new forward Admin/Drizzle migration
> for existing data, constraints and guards. Update tests to assert the new
> ownership and state semantics; never revert unrelated worktree changes.

**Optional Enhancers**

- Add explicit generic-Chat no-op and Observer attach-failure tests.
- Preserve immutable migration receipts and fail closed on unknown history.

**Scope checked or modified**

- `backend/claude_agent`, Dream thread mapping/runtime/observer/dispatchers,
  router DTO projection and their focused tests.
- Workflow models/services/contracts, frontend states/copy/tests.
- Admin Drizzle schema, forward migration, journal/snapshot/contracts/tests.

**Completion standard**

All R39 executable acceptance conditions pass, public Agent wire fixtures and
protected runner remain unchanged, existing data has a safe forward adoption
path, and focused tests prove no second runtime or lifecycle truth source.

**Actual result and unverified inferences**

Completed. Dream context is resolved from actor + canonical Thread inside
`assemble_context`; the closure callback and request-level Dream field are gone;
`DreamObserver` is registered through `SessionObserverRegistry`; router output is
projected by typed DTO classes; and frontend Dream conversation is a thin
`ChatPanel` composition. Admin migration 0033 normalizes historical rows,
rewrites the guard/check contract and publishes
`dream.workflow.no-continuing.v1`. Phase 3 still calls the same
`runner.run_streaming(...)`, and `agent_runner.py` has no diff.

## Round 41 — Contract and end-to-end verification

**Current-round objective**

Verify the corrected Dream business/runtime design against source, tests,
PostgreSQL migration replay, the real `hy3-preview` model and Chromium without
reintroducing a Dream wire protocol or the removed lifecycle stage.

**Optimized Prompt**

> Validate both repositories from the accepted Round 39 contracts. Start with
> source scans proving: no Dream context field exists in HTTP/request DTOs or
> internal dispatch requests; no Dream-specific browser EventSource/parser/
> reducer remains; no new Claude Agent SSE event was introduced; Phase 3 still
> calls the unchanged Agent runner entry; Dream runtime activation occurs in
> `assemble_context`; Dream business observation is registered through
> `SessionObserverRegistry`; and the obsolete lifecycle state is absent from
> live code, schema and normative docs except its one-way migration fixture.
>
> Run focused and reasonably broad backend tests, frontend unit/contract tests,
> TypeScript, ESLint, production build and `git diff --check`. Replay Admin
> Drizzle on disposable PostgreSQL across fresh, Alembic 06/07, partial drift,
> concurrency, idempotency and a real legacy-state data fixture; verify the new
> capability and generated catalog. Then use the user's configured real data
> and real `hy3-preview` model for the Dream business chain. Finally run
> Chromium Playwright with semantic waits and `--workers=1`, including headed
> mode as now authorized. Never print DSNs, secrets, model prompts containing
> private content or full business artifacts. Clean all test processes and
> disposable databases/containers.

**Optional Enhancers**

- Compare a Dream→Chat→Dream navigation trace using one canonical thread ID.
- Capture only redacted IDs, terminal counts and contract hashes as evidence.

**Scope checked or modified**

- Dream backend/frontend contracts and focused regression suites.
- Admin migration 0033, catalog, capability and migration E2E.
- Real local Dream/Chat runtime and `hy3-preview` browser flow.

**Completion standard**

All feasible checks pass; one canonical thread provides message/history/status/
stream/confirmation/Stop behavior on both pages; migration 0033 is proven on
disposable and configured data; exactly one terminal is observed; headed
Chromium runs with one worker; all processes and disposable resources are
cleaned; any unexecuted check is named with an evidence-backed reason.

**Actual result and unverified inferences**

Completed. Dream backend: 1952 passed, 22 skipped and 654 subtests passed.
Frontend: 338 source/unit contract tests passed after correcting one stale sort
expectation; TypeScript/production build and ESLint passed (21 pre-existing Hook
warnings, zero errors). Admin: 378 tests, lint and production build passed. The
configured database reports 34/34 migrations, zero obsolete workflow/transition
rows and one required capability. Disposable PostgreSQL cutover passed fresh,
legacy-06/07, legacy-state adoption, partial-drift rejection, idempotency and two
concurrent migrators; catalog SHA-256 is
`97208671d7519979982ed819e2397bba12403a500e14a938165254a64132f0cb`.

The read-only logical-clone real-provider proof issued exactly one request:
`hy-preview` resolved to provider-reported `hy3-preview`, returned one canonical
SSE terminal and two visible history rows, and left the source fingerprint
unchanged; all owned containers, volumes, ports and clone data were removed.
Current-candidate Chromium passed S01-S10 both headless and visibly headed with
one worker. No fixed sleep exists in the convergence spec. Final diff/link/source
and process cleanup gates are recorded in the acceptance document. No production
load/canary inference is made from these local results.

## Round 42 — Application-service simplification and single turn entry

**Current-round objective**

Remove the opaque Dream launch/workflow gateway shells and make
`ClaudeAgentThreadFactory.run_streaming()` the only public Agent turn-start
entry without modifying Phase 3 or the protected SDK runner.

**Optimized Prompt**

> Refactor the accepted Dream design into explicit application services. Replace
> the launch service/gateway pair with one `DreamLaunchApplicationService`, a
> request-scoped endpoint service and named repository/workflow/provisioning/
> dispatch adapters. Split the monolithic Story workflow gateway into Run,
> Artifact, Episode and Confirmation application services, and inject each only
> into the routes it owns. Keep authorization, preflight, idempotency, run
> creation and commands out of `DreamObserver`. Remove public `run_events` and
> start every Chat/Dream/internal turn through `run_streaming`; retain private
> turn supervision, EventBus, Stop and reconnect behavior, and expose a
> completion handle for the same stream instead of a second execution API.
> Replace Dream launch closures with named classes. Do not change
> `agent_runner.py`, SDK message handling or the Claude Agent Phase 3 call.

**Optional Enhancers**

- Add AST guards for the single public entry and closure-free launch modules.
- Keep shared Chat decoding only where a durable launch needs one safe error.

**Scope checked or modified**

- ThreadFactory Chat stream/completion implementation and Dream drains.
- Dream launch endpoint/application/infrastructure and preflight builder.
- Story Run/Artifact/Episode/Confirmation application services, router and
  Server lifecycle wiring.
- Focused architecture contracts, business sequences and acceptance docs.

**Completion standard**

Production source contains no former launch/workflow gateway, public
`run_events` or launch nested callable; all turn producers call
`run_streaming`; the protected runner has no diff; focused and complete
`backend/tests` pass; Python compile and `git diff --check` pass.

**Actual result and unverified inferences**

Completed. Launch uses `DreamLaunchEndpointService` →
`DreamLaunchApplicationService` with named infrastructure classes. Story APIs
inject `StoryWorkflowRunApplicationService`, `DreamArtifactApplicationService`,
`EpisodeApplicationService` or `DreamConfirmationApplicationService`; the broad
gateway symbols and file are gone. `run_streaming()` returns canonical Chat SSE
and its same-turn completion handle; `_run_streaming_frames`, `_run_turn_task`
and `_subscribe_events` remain private. Production legacy-symbol and nested-
callable scans are empty, `agent_runner.py` has no diff, and complete repository
tests passed: 1,954 passed, 22 skipped and 651 subtests. An unscoped `pytest`
attempt also collected real `backend/data/agent-workspace` plugin test copies
and stopped with 629 duplicate-module collection errors; no real data was
deleted, and the authoritative `backend/tests` boundary passed. Frontend,
Admin, real-provider and browser tests were not rerun because this round changes
only backend application wiring and preserves the already-tested public wire/UI
contracts.

## Round 43 — Atomic architecture commit

**Current-round objective**

Commit only the reviewed Dream application-service and single-turn-entry change
set as one recoverable Git unit.

**Optimized Prompt**

> Audit the current Dream repository worktree and stage only files directly
> related to the R42 application-service split, sole `run_streaming()` entry,
> Observer/router/Server wiring, contract tests and synchronized design docs.
> Exclude environment files, real Agent workspace data, dependencies and Admin
> repository state. Verify the protected runner is unchanged and
> `git diff --check` passes, then create one descriptive architecture commit.

**Scope checked or modified**

- R42 backend implementation, tests and directly synchronized design documents.
- No `backend/data`, environment, dependency or Admin files.

**Completion standard**

The staged diff exactly matches the R42 change set, passes whitespace review,
contains no protected-runner diff and is committed as one atomic unit.

**Actual result and unverified inferences**

Completed as the commit containing this record. Pre-commit inventory found no
environment or real-data path, `agent_runner.py` remained unchanged and
`git diff --check` passed. No tests were rerun in this commit-only round; R42's
complete and focused test results remain the verification evidence.

## Round 44 — Remove deployment-name runtime behavior

**Current-round objective**

Repair the real Dream launch failure by deleting deployment-tier gates from the
business runtime, adopting one explicit local placement and proving the full
launch path without a deployment label.

**Optimized Prompt**

> Diagnose the observed Dream launch failure from the production call chain.
> Delete `_DREAM_RUNTIME_DEPLOYMENT_TIERS` and every design or production branch
> that selects Dream behavior from development/test/production/unknown labels.
> Represent the currently owned topology as one named `local_persistent`
> placement shared by provisioning, activation, tool lifecycle and persistence.
> Keep secret, capability, plugin, actor/thread and workflow authorization
> checks at their actual boundaries. Put all fake/real provider and isolation
> differences in test harnesses only. Add a forward Admin/Drizzle migration for
> historical receipt/session placement, update both repositories' `AGENTS.md`,
> and validate focused backend contracts, migration replay, the deterministic
> complete Dream chain and a private real-data/real-model headed launch. Do not
> change Claude Agent messages, Phase 3 or `agent_runner.py`.

**Optional Enhancers**

- Diagnose the initial Dream-files readiness race without fixed sleeps.
- Record only redacted model, lifecycle, placement and cleanup evidence.

**Scope checked or modified**

- Dream activation/provisioning/session/tool lifecycle and their tests.
- Admin Drizzle placement constraints, capability, catalog and cutover harness.
- Dream-files readiness, real-model headed browser harness and design contracts.

**Completion standard**

No production Dream behavior reads a deployment name; all runtime rows use the
single placement; deterministic business and migration suites pass; the real
launch either completes or reports the exact external policy blocker with
source/resource cleanup proof.

**Actual result and unverified inferences**

Implementation and deterministic verification are complete: the focused Dream
set passed 184 tests plus 107 subtests, the full fake-provider business chain
passed, and Admin migration 0034 passed configured migration/check plus fresh,
legacy, drift, idempotency and concurrency cutover cases. The private headed
real-model run reached `hy-preview` → `hy3-preview` and settled its first request,
then the configured Gateway principal rejected the next request with
`DAILY_TOKEN_LIMIT_EXCEEDED`; the Workflow correctly failed once. Source
fingerprint, repositories, containers, volumes, ports and processes were
unchanged/cleaned. No inference is made that a hard daily quota is transient.

## Round 45 — Configure Claude Code native 429 retries

**Current-round objective**

Set the Claude Code default HTTP retry policy to three without changing Admin
limits, user permissions, Agent turn ownership or the protected runner entry.

**Optimized Prompt**

> Configure the locally installed Claude Code-supported
> `CLAUDE_CODE_MAX_RETRIES` runtime option to `3` through the existing shared
> SDK option assembly called by every canonical Agent turn and direct SDK
> client. Treat it as a server-owned default with explicit caller options
> preserved; do not expose it as a frontend DTO, user model permission, Admin
> quota mutation or new whole-turn retry loop. Remove the temporary private-
> clone RPM experiment. Add a deterministic option contract and a real local
> Claude CLI loopback test in which three transient 429 responses are followed
> by success. Verify the protected `agent_runner.py` has no diff, focused and
> reasonably broad tests pass, no secrets are printed and all local servers are
> released.

**Optional Enhancers**

- Document that hard daily/monthly quota failures remain non-recoverable.
- Assert an explicit direct-caller retry option is not overwritten.

**Scope checked or modified**

- Shared Claude SDK environment assembly and Gateway/CLI contracts.
- Private real-model harness diagnostics and Dream architecture/acceptance docs.
- No Admin limit/permission schema or production Gateway mutation.

**Completion standard**

Every canonical SDK subprocess gets default `CLAUDE_CODE_MAX_RETRIES=3`; a real
CLI proves three 429 retries can recover on the fourth request; explicit options
remain intact; no second Agent turn/terminal is introduced; focused/full checks
and cleanup pass.

**Actual result and unverified inferences**

Complete. The option/default and explicit-override contracts pass, and the real
Claude Code 2.1.220 loopback recovered after three transient 429 responses. The
private-clone permission override is deleted. The final focused Dream set passed
134 tests, one skip and 69 subtests; frontend TypeScript/production build,
Playwright collection and targeted ESLint passed; Admin passed 378 tests,
targeted ESLint and configured migration check at 35/35. A fresh provider-free
logical-clone preflight confirmed the exact `hy-preview` → `hy3-preview` model,
the real principal limit of 100,000 daily Tokens, no Provider call, unchanged
source fingerprint and complete container/volume/port/process cleanup. The
protected runner diff and production environment-gate scans are empty. The hard
daily quota remains an external policy blocker rather than a retry-configuration
failure; no additional real Provider call was made in this verification round.

## Round 46 — Existing-account real Dream verification

**Current-round objective**

Run the real-data, real-`hy3-preview`, headed Dream launch with the explicitly
selected existing account while preserving source data and account policy.

**Optimized Prompt**

> Validate the Dream launch as the existing account supplied through
> `INK_REAL_DREAM_ACCOUNT_EMAIL`; for this round the operator supplies
> `dmeck123@suoxya.com`. Resolve that account, its `ink-dream` platform
> projection, subscription, entitlement and principal limits from a read-only
> PostgreSQL source snapshot. Never create a replacement identity, change the
> account's model permission or quota, or print its token, database URL,
> credential, private history or full business artifact. Restore the snapshot
> into an owned private PostgreSQL clone, apply current Admin migrations, add
> only a clone-local Dream workspace/Deck/Agent owned by the resolved account,
> and select that Deck explicitly in the browser URL. Run the production Dream
> route with the real `hy-preview` alias resolving to `hy3-preview`, headed
> Chromium and `--workers=1`; install diagnostics before navigation and use only
> semantic waits. Verify Dream-files readiness, canonical Thread history and
> Dream→Chat→Dream recovery when the account policy permits completion. If the
> Gateway rejects the run, report the exact redacted policy code and persisted
> single-terminal evidence instead of changing limits. In every outcome prove
> source fingerprint stability and remove owned browser, processes, ports,
> container, volume and temporary clone.

**Optional Enhancers**

- Run a provider-free account preflight before the paid headed request.
- Keep the account email out of emitted evidence after resolution.

**Scope checked or modified**

- Private logical-clone real-model harness and its headed Playwright spec.
- Existing account resolution, exact Deck selection and redacted evidence.
- No Dream/Admin production business behavior or Gateway policy mutation.

**Completion standard**

The harness proves it used the requested existing account and unmodified policy,
then either completes the full headed Dream/Chat flow or produces the exact
external policy blocker; provider use is bounded and all source/resources remain
unchanged.

**Actual result and unverified inferences**

The existing canonical account and active `ink-dream` projection resolved from
the read-only source, with one active `free v2` subscription and 50,000,000
daily/monthly principal Token limits. Provider-free preflight then failed closed
because that plan has exactly one entitlement, `deepseek-v4-flash`, and no
`hy-preview`/`hy3-preview` entitlement. No Provider call occurred; source
fingerprint and all owned container/volume/port/process resources were cleaned.
Headed execution is blocked pending explicit authority to change the real
subscription; no clone-only permission fiction was introduced.

## Round 47 — Inject the Run-isolated layout into Dream context assembly

**Current-round objective**

Make every server-resolved Dream turn understand the normative run-isolated
Project/Episode Artifact tree before the existing-account real-model test.

**Optimized Prompt**

> Add the exact `# Run-isolated layout` tree supplied by the business owner to
> the Dream context built during `ClaudeAgentService.assemble_context`. Keep the
> layout in a named Story Workspace instruction constant and append it inside
> the existing `<story_workspace_dream_context>` only when the server-side
> actor+Thread mapper resolves a trusted Dream binding. State that `<run-id>` is
> the trusted `workflow_run_id`, shared root and Thread key are server-derived,
> sealed Run snapshots are isolated/immutable, and only Story Workspace MCP
> tools may write `.dream/**`. Do not add a request DTO field, frontend payload,
> SSE event, alternate Agent entry or generic Chat instruction. Add context
> builder contracts for every required path and for generic-Chat absence;
> preserve the protected runner and Phase 3 entry. Then restart the selected
> account's provider-free and headed real-model verification against the updated
> prompt.

**Optional Enhancers**

- Keep the exact Markdown heading and code tree for prompt inspection.
- Assert layout guidance precedes the user's text in the same Dream turn.

**Scope checked or modified**

- Story Workspace canonical instruction, Dream context builder and focused
  contracts.
- Architecture description and the pending existing-account real-model harness.
- No public Chat/Dream wire or Agent execution entry.

**Completion standard**

Focused tests prove the exact layout exists only in trusted Dream context and
the protected runner remains unchanged; the updated prompt is then exercised by
the account-specific real-model browser run.

**Actual result and unverified inferences**

Complete in code and focused verification: 77 tests and 22 subtests pass. The
exact heading/tree is injected only in server-resolved Dream context, generic
Chat absence is asserted, and no protected runner or public wire changed. The
account-specific Provider proof cannot exercise the updated prompt until the
separate model-entitlement blocker from R46 is resolved.

## Round 48 — Confirm the public request alias and upstream model identity

**Current-round objective**

Confirm the existing-account real-model harness uses `hy-preview` as the public
request name and resolves that server-owned alias to the `hy3-preview` display
and upstream model identity.

**Optimized Prompt**

> Treat the Admin model form as the authoritative naming contract:
> `hy-preview` is the public request name (`ai_models.code`) and
> `hy3-preview` is the display/upstream model identity. Keep Dream and Gateway
> requests on `hy-preview`; let the server resolve the corresponding model row
> and forward `hy3-preview` upstream. Bind authorization to that model row ID,
> not to display text. Preserve the existing private-clone account test and its
> provider-free preflight without changing the real account, subscription,
> quota or model permissions.

**Optional Enhancers**

- Record requested alias, resolved upstream and provider-reported model as
  separate evidence fields.

**Scope checked or modified**

- Dream model DTO/UI selection, Admin model resolver and subscription binding.
- Existing-account real-model harness and redacted validation evidence.
- No production account or Gateway policy mutation.

**Completion standard**

The harness submits the public request alias, verifies the resolved upstream
model separately, and either completes or reports a genuine model-row
entitlement blocker.

**Actual result and unverified inferences**

Confirmed from the authoritative Admin form and current contracts:
`hy-preview` is the request name while `hy3-preview` is the display/upstream
identity. The existing harness already uses exactly that pair, so no production
or test code change is required. The earlier attempt to reinterpret
`hy3-preview` as the public request value was incorrect and was not implemented.

## Round 49 — Continue the existing-account real Dream business verification

**Current-round objective**

Exercise the complete Dream launch business flow with the requested existing
account, real cloned data and the real `hy3-preview` Provider model, including a
final Chromium headed run with one worker.

**Optimized Prompt**

> Run the durable private-clone Dream real-model harness for the existing
> account selected by `INK_REAL_DREAM_ACCOUNT_EMAIL`. Use `hy-preview` as the
> public request alias and prove that Admin Gateway resolves it to
> `hy3-preview`. First run repository/port/browser and provider-free policy
> preflight. If it passes, execute the focused Playwright spec with Chromium
> headed and `--workers=1`, using semantic waits and the real public production
> endpoints for Dream launch, shared Thread SSE/history, workflow projection
> and artifact access. Capture redacted evidence for the request alias,
> upstream model, terminal Thread/workflow state, Project/Episode artifacts,
> browser diagnostics and source-data immutability. Do not mutate the source
> account, plan, permission, quota or content; do not call the Provider after a
> failed preflight. Always stop owned processes, release ports and delete the
> exact isolated database/container/runtime resources.

**Optional Enhancers**

- Preserve a minimal failure artifact only when it materially helps diagnosis.
- If the product path fails, repair the smallest production defect and rerun
  focused contracts before restarting the real-model lane.

**Scope checked or modified**

- Existing-account private clone, Admin Gateway and Dream API/UI business path.
- Focused headed Chromium spec and run-isolated artifact assertions.
- No source-account writes or alternate Agent runtime.

**Completion standard**

Provider-free preflight passes, the headed one-worker browser flow reaches one
terminal state with correct shared Thread/workflow/artifact evidence, zero
Ink-Dream browser diagnostics, and cleanup proves source and owned resources are
unchanged; otherwise the exact genuine blocker is isolated with no Provider or
source mutation beyond authorized scope.

**Actual result and unverified inferences**

Pending preflight and headed execution.

## Round 50 — Preserve safe business failure evidence in the real-model harness

**Current-round objective**

Make the provider-free preflight identify its exact non-sensitive business
blocker instead of collapsing every explicit subscription failure into the
generic Python class `RuntimeError`.

**Optimized Prompt**

> Introduce a narrow structured preflight exception in the real Gateway E2E
> verification script. Give every subscription eligibility failure a stable,
> non-sensitive phase and error code, and make the safe entrypoint emit only
> that code plus the existing privacy assertions. Never emit response bodies,
> account identifiers, tokens, secrets, Provider content or exception text.
> Add focused contracts for structured output and retain generic redaction for
> unexpected exceptions. Update the script/test folder contracts, run the
> focused backend test, then repeat the private-clone provider-free preflight.
> Do not change Product/Gateway production policy merely to make the test pass.

**Optional Enhancers**

- Use a closed set of literal codes instead of deriving output from exception
  messages.

**Scope checked or modified**

- `backend/script/verify_gateway_e2e.py`, its focused contract tests and folder
  documentation.
- No production request, model, subscription or Agent behavior.

**Completion standard**

Focused tests prove expected preflight failures expose a stable safe code while
unexpected errors remain redacted; the rerun reports an actionable phase/code
without calling the Provider or leaking private data.

**Actual result and unverified inferences**

Pending harness diagnostic change and provider-free rerun.

## Round 51 — Close the Gateway model-entitlement authorization gap

**Current-round objective**

Resolve the observed production contradiction where Gateway/Dream model catalogs
mark `hy-preview` callable for the existing account while Product subscription
context reports no exact model entitlement.

**Optimized Prompt**

> Trace Admin Gateway model callability and message preparation from
> `listAvailableGatewayModels` through billable-model resolution, allowance
> reservation and Provider dispatch. Prove whether the selected current plan has
> an enabled `messages:create` entitlement for the resolved model row before any
> Provider request. Treat a missing entitlement as `upgrade_required` in the
> public catalog when an eligible plan exists, otherwise fail closed with a
> stable authorization error. Apply the smallest Admin production fix at the
> shared server-owned boundary and add contracts proving catalog and inference
> cannot disagree. Do not grant or synthesize an entitlement, alter the existing
> account, or weaken quota/user-permission checks. After focused Admin tests,
> rerun the Dream provider-free clone preflight; enter the paid headed lane only
> if the real subscription genuinely authorizes `hy-preview`.

**Optional Enhancers**

- Assert missing entitlement is rejected before request reservation and
  Provider transport.

**Scope checked or modified**

- Admin Gateway catalog, resolver/request-preparation authorization and focused
  contracts.
- Dream private-clone preflight as cross-repository acceptance evidence.
- No subscription or account mutation.

**Completion standard**

Catalog callability and Provider dispatch enforce the same exact model-row
entitlement, focused tests pass, and the rerun either proceeds legitimately or
stops before Provider use with one accurate business blocker.

**Actual result and unverified inferences**

Provider-free evidence shows `hy-preview` passed both Admin and Dream catalog
callability checks but failed Product exact-entitlement preflight. Source review
initially suggested a missing `entitlement_id` condition in catalog evaluation.
Deeper review rejected that inference: Admin's existing catalog and
subscription-Gateway contracts explicitly support `allowance-only` access to an
enabled model without a per-plan model entitlement, while still enforcing
subscription state/period, user-model denial and Token reservation before
Provider dispatch. No Admin production change was made; the contradiction is in
the real-model harness's stricter assumption.

## Round 52 — Align real-model preflight with allowance-only Gateway policy

**Current-round objective**

Remove the harness-only exact-entitlement requirement that contradicts the
production Token allowance contract, without weakening any production or test
authorization boundary.

**Optimized Prompt**

> Keep Admin `/v1/models` and Dream `/api/gateway/models` as the server-owned
> source of exact model callability. In the existing-account real-model harness,
> accept the current subscription when its period Token allowance is positive
> even if Product context does not list a plan-specific `hy-preview`
> entitlement; record this as `allowance-only`. Continue to fail closed when the
> catalog model is not callable, the subscription/allowance is absent or
> exhausted, an explicit user-model permission denies access, or Gateway
> preauthorization rejects the request. Add focused contracts for exact
> entitlement and allowance-only modes. Validate the existing Admin allowance
> policy tests, rerun provider-free preflight, then execute the real headed
> Dream browser flow with one worker. Do not create/change a subscription or
> bypass Gateway request preparation.

**Optional Enhancers**

- Emit the access mode in redacted evidence so entitlement-backed and
  allowance-only runs cannot be confused.

**Scope checked or modified**

- Dream real-model verification harness and its focused contracts.
- Read-only execution of existing Admin Gateway/subscription tests.
- No Admin production code or real account mutation.

**Completion standard**

Tests prove the harness mirrors the production allowance-only policy, the
provider-free preflight succeeds for the existing account without provisioning,
and the headed run reaches a real terminal business outcome with cleanup.

**Actual result and unverified inferences**

Pending harness alignment, focused tests and real execution.

## Round 53 — Diagnose the real Dream launch Artifact timeout by lifecycle layer

**Current-round objective**

Identify why the headed real-model Dream launch accepted a Run but failed to
reach settled `dream-files` within 360 seconds, instead of increasing timeouts or
replaying an unobservable paid request.

**Optimized Prompt**

> Improve the private-clone failure receipt so a headed Dream launch records the
> accepted workflow Run and Thread IDs outside private browser content, then on
> failure queries the owned clone read-only for: workflow Run status/version and
> error code, source Thread/runtime binding, Agent session state, Thread running
> status and terminal messages, Gateway requested/resolved model plus safe
> outcome/error code, Observer projection receipt, and Project/Episode Artifact
> row/file counts. Use opaque presence/count/state evidence only. Diagnose before
> clone cleanup and never print prompts, assistant text, paths containing user
> content, account identifiers, Provider bodies or secrets. Add focused harness
> contracts where practical. Rerun provider-free checks after any change, then
> one headed real-model flow only when the new receipt can distinguish launch,
> Agent, workflow and Artifact failures. Do not extend the 360-second semantic
> wait to hide the defect.

**Optional Enhancers**

- Persist only the final redacted diagnostic JSON when the run fails.

**Scope checked or modified**

- Headed Dream E2E accepted-run handoff, private-clone failure diagnostics and
  the business endpoints polled by the spec.
- No production lifecycle change until evidence identifies the failing owner.

**Completion standard**

A failed rerun produces a non-null, content-free lifecycle receipt that assigns
the fault to one state owner, or the corrected run passes the full Artifact and
same-Thread Chat/Dream acceptance path; cleanup remains complete.

**Actual result and unverified inferences**

The first headed run passed both model catalogs and allowance-only preflight,
started one Chromium worker, then timed out at the 360-second settled
`dream-files` predicate. Existing failure evidence returned `run:null`, so the
failing lifecycle layer is still unverified. All source and owned resources were
cleaned.

## Round 54 — Handle a completed Agent turn with incomplete Dream output

**Current-round objective**

Fix the observed lifecycle split where the shared Agent turn ends normally
after only `write_dream_run`, while the Dream workflow remains waiting forever
for characters, scenes and storyboards.

**Optimized Prompt**

> Use the headed browser evidence as authoritative: the Agent produced a
> `write_dream_run` result with `changedStages: []`, emitted prose promising the
> next initialization step, then the shared Thread turn stopped and no Stop
> control remained. Trace the Dream launch request's `max_turns` and tool budget
> through the single public `ClaudeAgentThreadFactory.run_streaming()` entry,
> without changing the Claude SDK runner entrypoint. Determine whether a
> one-turn limit prematurely stops the required multi-tool flow. Ensure one
> Dream launch permits enough SDK agentic turns to complete the documented
> `write_dream_run` plus characters/scenes/storyboards sequence in the same main
> turn. Independently, make `DreamObserver`/launch completion validation project
> a stable `DREAM_OUTPUT_INCOMPLETE` failure when a normal shared turn ends
> without all required persisted stages; never leave workflow `running` after
> Thread idle, never create a `continuing` state, and never auto-start a second
> Agent turn. Add lifecycle contracts for success, incomplete normal finish,
> error and single terminal transition. Then rerun focused tests and the headed
> real-model flow.

**Optional Enhancers**

- Surface the incomplete-output error immediately in Dream instead of waiting
  for polling timeout.

**Scope checked or modified**

- Dream launch turn options, the single `run_streaming()` caller, DreamObserver
  or post-turn output validation, workflow transition projection and focused
  UI/API contracts.
- Protected Claude Agent runner and shared Chat wire remain unchanged.

**Completion standard**

The required multi-tool flow is not truncated by a one-turn SDK budget; a
normal incomplete finish transitions once to failed and becomes immediately
visible; a complete run reaches pending review; no workflow remains running
after Thread idle and no `continuing` state appears.

**Actual result and unverified inferences**

Headed evidence confirms the shared turn ended after `write_dream_run` with
zero changed stages and only prose announcing future work. The filesystem held
`run.json` but no stage files. Whether a `max_turns=1` launch option caused this
premature normal finish is not yet verified.

Source inspection verified Dream launch inherits the shared `max_turns=100`;
the turn was not truncated by a one-turn SDK budget. The business owner
classified the premature finish as a model-capability issue and explicitly
selected `deepseek-v4-pro` for the next run. No lifecycle/prompt production
change from this round was implemented; incomplete-turn fail-closed handling
remains a separate hardening item rather than a prerequisite for the requested
model comparison.

## Round 55 — Restart the real Dream flow with DeepSeek V4 Pro

**Current-round objective**

Repeat the full existing-account Dream business test from a fresh isolated
clone using the real `deepseek-v4-pro` model instead of `hy3-preview`.

**Optimized Prompt**

> Parameterize the durable private-clone real-model harness with an explicit
> public request alias and expected upstream model, and select
> `deepseek-v4-pro` for both values after verifying the current Admin model row.
> Preserve every existing safety boundary: the requested account is resolved
> read-only from source, allowance/catalog/model checks run Provider-free first,
> source data and subscriptions are never modified, and the headed run uses
> Chromium `--headed --workers=1`. Start from a new clone and new Dream Run.
> Assert the Agent completes `write_dream_run`, characters, scenes and
> storyboards, reaches pending review, exposes editable Dream files, restores
> the same Thread in Chat and Dream, emits no duplicate terminal, and leaves no
> owned process/container/volume/port. If the turn stops after partial output,
> report the last content-free stage receipt immediately rather than waiting on
> backend process liveness. Write the scenario as a normal human journey:
> navigate the Dream page, select the visible Deck, enter a natural creation
> goal, click the launch control, observe the visible Agent session, and treat
> the Agent's visible stop as terminal. Use API reads only to verify persisted
> facts behind that UI journey. Never keep polling artifacts after the shared
> Thread has stopped with at least one turn and incomplete stages.

**Optional Enhancers**

- Keep alias and upstream independently required so an accidental routing
  mismatch fails before Provider use.

**Scope checked or modified**

- Real-model harness configuration and focused source/contract checks.
- Fresh Provider-free and headed Dream business execution.
- No production Agent, workflow, SSE or account policy change.

**Completion standard**

The exact DeepSeek model contract passes preflight and one fresh headed flow
either completes all Dream/Thread/Artifact acceptance assertions or yields a
precise model/business failure with complete cleanup.

**Actual result and unverified inferences**

The read-only Admin row proves public alias, upstream model and display name are
all `deepseek-v4-pro`; the model and Anthropic-protocol Provider are enabled and
active. The harness is now explicitly parameterized, and the browser scenario
fails immediately when a human-visible Agent stop leaves required stages
incomplete instead of waiting for the Artifact timeout. Fresh execution is
pending.

## Round 56 — Make human business journeys mandatory in the Playwright QA skill

**Current-round objective**

Persist the business owner's testing rule in the repository QA skill so future
browser tests do not confuse process/API liveness with a user's visible
business flow.

**Optimized Prompt**

> Update `ink-dream-playwright-qa/SKILL.md` and its project workflow reference
> with a mandatory human-journey rule. Browser E2E scenarios must perform the
> meaningful actions a normal user performs through visible UI, observe visible
> progress and terminal controls, and judge completion at the same point a user
> would. API calls may create isolated prerequisites or verify persistence, but
> may not replace the business interaction under test. Service/process health
> proves only infrastructure liveness. When the visible Agent/Thread has
> stopped, the test must immediately validate the visible/persisted business
> result and fail if required output is incomplete; it must not continue long
> polling because backend processes remain alive. Require semantic waits and
> prohibit fixed sleeps or inflated timeouts that mask a stopped business flow.
> Include a concise Dream example and preserve all existing isolation,
> diagnostics and cleanup rules.

**Optional Enhancers**

- Require each E2E name to read as a user outcome rather than an implementation
  endpoint sequence.

**Scope checked or modified**

- Repository-local `ink-dream-playwright-qa` skill and its project workflow
  reference.
- No production or test execution behavior in this documentation-only round.

**Completion standard**

The skill unambiguously directs future agents to test visible human business
journeys, stop on the visible terminal, use APIs only as supporting evidence,
and distinguish infrastructure health from business progress.

**Actual result and unverified inferences**

Complete. The core skill now requires visible human business journeys, treats
visible Agent/Thread stop as terminal, separates infrastructure liveness from
business progress, and limits API reads to fixture setup or persisted-fact
corroboration. The project workflow includes the exact Dream stopped-turn
example. Frontmatter and `git diff --check` passed; the skill remains a compact
143 lines.

## Round 57 — Remove the last entitlement-only assumption from model preflight

**Current-round objective**

Allow the verified `deepseek-v4-pro` model to reach the production catalog
preflight under the same allowance-only policy already accepted elsewhere, and
prevent pre-launch failures from reporting unrelated historical Runs.

**Optimized Prompt**

> Update only the private-clone harness. In model-row verification require the
> exact public alias/upstream pair, enabled model, active Provider, usable
> credential and active pricing; record published entitlement count as evidence
> but do not require it, because final account callability is decided by the
> authenticated Admin/Dream catalogs plus subscription allowance policy. When
> no accepted browser Run receipt exists, failure diagnostics must report
> `receiptPresent=false` and `runPresent=false` rather than selecting the newest
> historical Run from the cloned account. Keep provider-free execution and full
> cleanup, then restart the DeepSeek preflight and headed human journey.

**Optional Enhancers**

- Assert pre-launch phases can never emit historical workflow evidence.

**Scope checked or modified**

- Private real-model clone model-row and failure-diagnostic checks only.
- No production model authorization, account, workflow or Agent behavior.

**Completion standard**

DeepSeek reaches authenticated catalog/account preflight without a fake
entitlement requirement; any pre-launch failure contains no unrelated Run; no
Provider call occurs before the headed lane.

**Actual result and unverified inferences**

The first DeepSeek provider-free attempt stopped at `clone-model-contract`
because the harness still asserted `publishedEntitlements > 0`. No current Run
or Provider request existed. The old fallback diagnosis incorrectly displayed
an unrelated historical failed Run from the clone.

## Round 58 — Restore the isolated Product dependency before Provider use

**Current-round objective**

Resolve the repeatable `503 PRODUCT_DEPENDENCY_UNAVAILABLE` returned by the
Dream Product plans BFF during DeepSeek provider-free preflight.

**Optimized Prompt**

> Trace the private-clone Product call from Dream's
> `/api/story-workspace/subscription/plans` through its Admin Product client to
> the exact isolated Admin route, JWT/service credentials and Origin policy.
> Compare the harness environment with the production DTO/config contract and
> the previously passing HY preflight. Add a readiness check for the actual
> Product dependency rather than treating an unauthenticated `/v1/models`
> response as sufficient Admin readiness. Preserve redaction: report only route
> status and stable error codes, not JWTs, service keys, account IDs, DSNs or
> response bodies. Fix the smallest harness/config defect, run focused Product
> client contracts, and repeat Provider-free DeepSeek preflight. Do not create a
> Dream Run or call the Provider until Product plans succeeds.

**Optional Enhancers**

- Distinguish Admin process readiness from Product route authorization in the
  final preflight evidence.

**Scope checked or modified**

- Dream Admin Product client configuration and private-clone readiness/config.
- Focused read-only HTTP/config diagnostics; no Provider or account mutation.

**Completion standard**

The isolated Product plans route returns its valid authenticated contract in
provider-free preflight, with repeatable startup readiness and full cleanup.

**Actual result and unverified inferences**

Two fresh DeepSeek preflights passed model/account catalog checks but returned
the same `503 PRODUCT_DEPENDENCY_UNAVAILABLE` before Run creation. Both cleaned
all resources. A mere Admin cold-start transient is therefore rejected.

## Round 59 — Align Dream ProductPlan with the Admin authority contract

**Current-round objective**

Repair the verified Admin/Dream Product plans DTO drift without weakening the
Dream BFF response firewall.

**Optimized Prompt**

> Treat the Admin Product projection as the authoritative business contract.
> Preserve Dream's strict Pydantic parsing, extra-field rejection, safe
> identifiers, Token-only firewall and commercial-value invariants. Update only
> the availability relationship that contradicts Admin: a published plan may be
> unavailable when its runtime/commercial configuration is incomplete, with
> null commercial values, a non-null `configuration_incomplete` reason and no
> available actions. Keep draft plans tied to
> `commercial_parameters_pending`. Add a focused client contract test using the
> exact shape, run Product unit tests, then repeat the isolated DeepSeek
> Provider-free preflight. Do not call the Provider until both the direct Admin
> contract and Dream BFF contract pass.

**Optional Enhancers**

- Retain the authenticated Admin Product readiness receipt as future harness
  evidence so HTTP process readiness cannot mask DTO drift again.

**Scope checked or modified**

- Dream Product plans DTO availability validator and focused client test.
- Real-model clone harness Product readiness evidence.

**Completion standard**

Both authoritative Admin unavailable-plan variants validate through Dream,
invalid commercial/action combinations still fail closed, and the full
Provider-free DeepSeek preflight passes with no Run or Provider call.

**Actual result and unverified inferences**

Complete. The Dream validator now accepts an Admin-authoritative published plan
that is unavailable solely because configuration is incomplete, while still
requiring null commercial values and no available actions. The direct Product
probe validates with three plans, 46 focused Product/BFF/harness tests pass, and
the complete DeepSeek Provider-free private-clone preflight passes. It resolves
the existing account in allowance-only mode, makes no Provider call, preserves
the source fingerprint and removes every owned resource.

## Round 60 — Headed DeepSeek Dream business journey

**Current-round objective**

Execute one fresh, visible Dream launch with the existing account and exact
`deepseek-v4-pro` model after every Provider-free gate passed.

**Optimized Prompt**

> Run the focused Dream Playwright scenario in visible Chromium with exactly
> one worker against the private logical PostgreSQL clone and isolated Admin,
> Dream API, Vite and workspace roots. Behave as a normal user: open the Dream
> page, choose the visible Deck, enter a realistic Chinese story-production
> goal, submit through the visible launch action, observe the shared Chat thread
> streaming state and inspect the resulting Dream business panels/artifacts.
> Use APIs only for authenticated supporting evidence. Poll Thread lifecycle and
> Artifact projection together; once the Agent turn is no longer running, stop
> waiting and fail immediately if characters, scenes or storyboard output is
> incomplete. Verify the accepted Run/thread receipt, exact requested/resolved
> model, settled Gateway accounting, single workflow terminal semantics and
> full cleanup. Never log prompts, model output, JWTs, DSNs or source history.

**Optional Enhancers**

- Preserve a content-free lifecycle receipt for a failed stopped turn so model
  capability can be distinguished from infrastructure liveness.

**Scope checked or modified**

- One headed `--workers=1` Dream launch using the focused human-journey spec.
- Read-only post-run lifecycle, message-role, Gateway and cleanup receipts.

**Completion standard**

The visible user journey reaches complete Dream business output and the
expected review-ready state through one shared Thread turn, with exact
DeepSeek/Gateway evidence and no source or resource residue; otherwise report
the first true business terminal and its content-free evidence.

**Actual result and unverified inferences**

Rejected and interrupted by the owner. The headed user journey reached a live
running Dream turn and seven successfully settled exact-DeepSeek Gateway
requests, but the harness wrote all Gateway receipts to a private clone. The
owner's normal Admin console therefore could not observe them. The run was
stopped immediately; source data remained unchanged and every owned process,
port, container, volume and temporary clone was removed. This execution is not
accepted as business evidence.

## Round 61 — Observable live Admin Dream journey

**Current-round objective**

Replace the invisible clone-only headed proof with a real local business test
whose Gateway receipts are visible in the owner's normal Admin console.

**Optimized Prompt**

> Use the existing account `dmeck123@suoxya.com`, the normal Admin/Gateway
> service and its actual PostgreSQL data, and exact model alias
> `deepseek-v4-pro`. First verify the normal Admin service, Dream API and web
> endpoints and identify an existing enabled Dream Deck without creating a fake
> clone-only Deck. Adapt the focused Playwright case so it behaves like a human
> through visible UI and does not assert clone fixture labels. Create one fresh
> Dream Run through the visible launch action, observe shared Thread streaming,
> require characters/scenes/storyboards and review readiness, then verify the
> corresponding requested/resolved model and settlement receipts through the
> same database/API used by the Admin console. Keep the resulting business Run
> and receipts observable for owner review; stop owned service/browser
> processes without deleting the accepted business evidence. Do not print
> prompts, model output, JWTs, credentials or DSNs.

**Optional Enhancers**

- Record a content-free Run/thread identifier and creation time so the owner can
  locate the exact entry in Admin without exposing conversation content.

**Scope checked or modified**

- Standard local Admin/Dream/Vite service readiness and live-data focused E2E.
- Existing-account Deck discovery and content-free post-run receipt checks.

**Completion standard**

The headed one-worker Dream journey is visible in the normal Admin Gateway log
view and reaches the required business output, or fails at the true Agent/Run
terminal with an exact content-free diagnosis; no unrelated service is killed.

**Actual result and unverified inferences**

Pending live-service readiness and observable test execution. This round will
write a real Run and Gateway receipts to the account's normal database by
explicit owner request.

## Round 63 — Load normal backend identity config in the headed harness

**Current-round objective**

Unblock the live-data Playwright login preparation without introducing a test
database or test-only authentication path.

**Optimized Prompt**

> Keep authentication against the existing active account and the normal
> backend JWT implementation. In the Playwright-only helper process, explicitly
> load `backend/.env` with non-overriding dotenv semantics before opening the
> production PostgreSQL pool, matching normal FastAPI startup. Do not copy
> credentials into test source, print the token/DSN, create a shadow account or
> bypass `auth.create_access_token`. Prove the focused spec still passes ESLint
> and discovery, then rerun headed Chromium against ports 5173/8765 and the
> existing Admin on 3000. Confirm no Run or Provider request was created by the
> failed pre-browser attempt.

**Optional Enhancers**

- Keep API-issued auth as test setup only; every business action remains a
  visible browser interaction.

**Scope checked or modified**

- Playwright login preparation and the next live headed execution only.

**Completion standard**

The existing account authenticates without exposing secrets, the browser
reaches the visible Dream launch form, and all subsequent writes use the normal
local business database.

**Actual result and unverified inferences**

Complete. The helper now loads normal backend configuration without overriding
the process environment, preserves the real auth implementation and reaches
the visible Dream launch form. ESLint and Playwright discovery pass. The next
live attempt created a normal observable Run, proving authentication and the
local real-data route are working.

## Round 64 — Handle Dream tool confirmation as a visible human action

**Current-round objective**

Correct the human-journey E2E after the live Run waited six minutes for an
unanswered built-in `Write` confirmation.

**Optimized Prompt**

> Keep production confirmation policy unchanged. Extend the headed Dream test
> to observe the shared Chat confirmation dock on the visible page while the
> Run is streaming. Approve only an explicitly allowlisted built-in `Write`
> confirmation needed to create the run-isolated Dream artifacts, by clicking
> the visible localized Approve button and waiting for that exact dialog to
> settle. Never approve Bash, network access, an unknown tool or arbitrary
> confirmation content; fail immediately with a content-free error instead.
> Count approvals in the private receipt without recording tool input. Continue
> polling Thread lifecycle and Artifact output after approval. Update the
> Playwright QA skill so every business journey must respond to required visible
> confirmations like a human rather than waiting behind them. Rerun lint,
> focused confirmation contracts and headed real-data Chromium. Preserve the
> cancelled failed Run and its normal Admin receipts as evidence.

**Optional Enhancers**

- If AskUserQuestion appears in a future scenario, answer it through its visible
  form using case-specific business input; never invent a generic silent answer.

**Scope checked or modified**

- Focused real-model Dream Playwright case and Playwright QA skill.
- No production confirmation, Claude runner or Agent lifecycle changes.

**Completion standard**

The test cannot remain blocked behind an unanswered visible confirmation,
approves only reviewed Dream Write operations, and reaches either complete
artifacts or the next true business terminal.

**Actual result and unverified inferences**

Partially complete. The first normal local-data Run produced eight successful
settled DeepSeek requests, then waited on `Write`; the old test timed out. The
updated browser visibly approved one `Write` in the next real Run and Provider
traffic resumed, proving the interaction works. It then failed closed on a
second confirmation whose content-free accessible name identified the built-in
`Agent` tool with the safe summary `Compute project slug hash`. Both incomplete
Runs were stopped and persisted as `cancelled`; normal Admin receipts remain.

## Round 65 — Approve the expected Dream subagent through visible UI

**Current-round objective**

Permit the case-specific built-in `Agent` subagent confirmation required by the
Dream workflow while keeping the headed test fail-closed for all other tools.

**Optimized Prompt**

> Extend the visible confirmation helper from one exact tool to the closed set
> `{Write, Agent}`. Parse only the confirmation dialog's accessible title, never
> its parameters. Click the localized Approve button for a single visible
> built-in `Write` or `Agent` dialog, wait for that exact dialog to close and
> count each tool type separately in the content-free receipt. `Agent` is
> allowed because this scenario explicitly covers Dream subagent delegation;
> Bash, network, AskUserQuestion without scenario answers, reject-only and every
> unknown tool must still fail immediately. Run ESLint/discovery and restart a
> new normal local-data headed journey. Preserve prior cancelled Runs and Admin
> receipts.

**Optional Enhancers**

- Corroborate subagent start/completion from the shared Thread projection after
  the main turn settles without reading its transcript.

**Scope checked or modified**

- Focused Playwright confirmation allowlist and content-free receipt only.

**Completion standard**

Expected Write and Agent dialogs are handled like explicit human approvals,
unexpected confirmations remain blocked, and the Dream turn advances to
business artifacts or a new exact terminal.

**Actual result and unverified inferences**

Implemented and statically validated. The headed test recognizes only one
visible exact `Write` or `Agent` dialog at a time, requires its Approve control
to be inside the viewport, and records separate content-free counts. The latest
real Run visibly approved one Write and two Agent operations; no unknown,
Bash/network or AskUserQuestion operation was approved. The Run later failed
the Artifact completion deadline for the separate orchestration reason recorded
in Round 68.

## Round 62 — Make local real data mandatory for real business QA

**Current-round objective**

Codify the owner's rule that every real business/model acceptance test uses the
normal local services and local real PostgreSQL data, never a clone substitute.

**Optimized Prompt**

> Update both Dream and Admin root `AGENTS.md` files with one unambiguous
> cross-repository rule: anything described as real business testing, real-data
> testing or real-model acceptance must execute against this machine's normal
> Admin, Dream, Gateway and current local PostgreSQL data. It must use the
> requested existing account and existing business entities; do not create a
> cloned database, shadow account, clone-only Deck, synthetic subscription,
> isolated ledger or alternate Admin runtime to stand in for the business
> system. Runs, Gateway receipts and failures must be visible through the normal
> Admin console. Keep migration, backfill, destructive and repeatable
> persistence tests isolated, and explicitly prohibit reporting those technical
> tests as real business acceptance. Reconcile existing broad isolation wording
> so the two classes do not contradict each other.

**Optional Enhancers**

- Preserve owner-requested real Run and Gateway receipts for review unless the
  owner explicitly asks to remove them.

**Scope checked or modified**

- Dream and Admin root Agent instructions only, plus this round record.

**Completion standard**

Both repositories state the same enforceable rule and no existing sentence
still requires a database clone for an owner-authorized real business test.

**Actual result and unverified inferences**

Complete. Both root `AGENTS.md` files require owner-authorized real business,
real-data and real-model acceptance to use the normal local Admin, Dream,
Gateway and current local PostgreSQL data. They prohibit clone/shadow business
substitutes and require evidence to remain visible in normal Admin, while
retaining isolation for destructive migration/backfill and provider-free
technical tests.

## Round 66 — Fit the headed Dream journey inside the visible window

**Current-round objective**

Keep the full Dream business page and its shared Chat controls usable inside a
normal headed Chromium window while continuing the local real-data journey.

**Optimized Prompt**

> Replace the test's oversized 1440×1000 runtime viewport with an explicit,
> bounded headed Chromium outer window and a smaller deterministic content
> viewport that fit the current desktop. Do not use browser zoom, CSS scaling,
> hidden panels or maximization to mask layout defects. Assert that the document
> has no horizontal overflow, the Dream launch heading and primary action are
> inside the viewport, and every visible confirmation dialog is brought into
> view and remains operable before approval. Record the same rule in the
> Playwright QA skill. Run lint and test discovery first, then resume the normal
> local Admin/Dream/Gateway journey with the existing real account and data.

**Optional Enhancers**

- Capture a failure screenshot only if a real responsive-layout assertion
  fails, without recording private model output in logs.

**Scope checked or modified**

- The focused Dream real-model Playwright case and its QA skill guidance.
- Product layout code only if the bounded-window assertions expose a genuine
  application overflow.

**Completion standard**

The headed browser fits the desktop, the launch action and confirmation UI are
usable without clipping or zoom, and the business test can continue through
the normal visible page.

**Actual result and unverified inferences**

Complete. The headed Chromium outer window was bounded to 1280×800 with a
1200×720 content viewport. The launch heading and primary action were inside
the viewport, every handled confirmation dialog and Approve button was inside
the viewport, and the Dream, Chat and back-to-Dream routes passed the
document-level horizontal-overflow assertion wherever reached. No browser zoom,
maximization, hidden panel or product CSS workaround was used.

## Round 67 — Enforce the run-isolated Artifact boundary found by real QA

**Current-round objective**

Diagnose and correct the normal local-data Run that wrote Project/character/
scene files outside its server-derived `.dream/runtime/runs/<run-id>/artifact`
root and therefore did not finish the storyboard projection in time.

**Optimized Prompt**

> Use the cancelled real Run's content-free lifecycle facts and current code to
> trace `ClaudeAgentService.assemble_context`, Dream context construction,
> permission/tool exposure and Dream Artifact projection. Prove whether the
> server-derived run root and canonical Project/Episode Artifact contract are
> present in the actual Dream system context. Prove whether generic `Write` or
> shell tools can bypass that boundary by writing to the Thread workspace root.
> Enforce the boundary in server-owned runtime/tool policy rather than merely
> adding another advisory prompt. Preserve the single public
> `ClaudeAgentThreadFactory.run_streaming()` entry and the existing Claude
> runner entry. Add focused contracts for exact run-root injection and rejection
> of non-run-isolated Dream artifact mutation. Do not expose model transcript or
> business contents in test output. After focused tests, repeat one bounded
> visible local-data journey only if the boundary is proven.

**Optional Enhancers**

- Make the test receipt record only canonical Artifact counts and a boolean
  proving no legacy workspace-root artifact path was used.

**Scope checked or modified**

- Dream context assembly, Dream-specific tool/runtime policy, Artifact path
  resolution and focused contracts.
- No Claude SDK runner entry, external Dream SSE protocol or unrelated global
  filesystem policy changes.

**Completion standard**

The actual Dream context contains one exact server-derived run layout, generic
tools cannot create Project/Episode artifacts outside it, and the focused
contracts plus a visible real Run prove canonical characters, scenes and
storyboard projection.

**Actual result and unverified inferences**

The bounded headed window and all viewport assertions passed. The real Run
projected three characters and two scenes within six minutes and had also
created the canonical storyboard source file, while the shared Thread remained
a cancellable main turn. It was stopped through the Thread endpoint and then
persisted as `cancelled`. Code inspection disproved the initial bypass
inference: `assets/` and `stories/` are the editable source workspace, generic
tools are hard-denied from `.dream/**`, and `bind_first_episode` publishes the
server-owned Artifact snapshot only after the source contract is complete. The
actual Dream message includes the exact Run-isolated layout. No runtime boundary
change is warranted from this evidence.

## Round 68 — Use a human-sized active-turn deadline for real Dream generation

**Current-round objective**

Allow the full real-model Project/Episode workflow to finish while preserving
the rule that a stopped Agent with incomplete output fails immediately.

**Optimized Prompt**

> Keep the bounded 1280×800 headed window and all viewport assertions. Increase
> only the focused real-model case's total timeout and semantic Artifact poll so
> a genuinely running `deepseek-v4-pro` turn has up to twelve minutes to create
> canonical source files, publish all three Dream stages and bind the first
> Episode. Continue checking visible confirmations, WorkflowRun failure and the
> shared Thread status on every poll. If the Thread stops with missing output,
> fail immediately; never use a fixed sleep, service liveness or a reconnect
> loop as progress. Run static checks first, then execute one normal local-data
> headed journey with one worker. On failure, use standard Thread Stop and
> workflow cancel and keep Admin receipts.

**Optional Enhancers**

- Record source/project and published Artifact presence only as booleans or
  counts, without storing model content in Playwright failure snapshots.

**Scope checked or modified**

- Focused Dream real-model Playwright timing contract only.
- No production lifecycle, model, prompt, runner, SSE or workflow change.

**Completion standard**

The test finishes the visible same-Thread Dream→Chat→Dream journey within the
bounded active-turn window, or reports the first genuine business terminal
without leaving a running Agent.

**Actual result and unverified inferences**

The timing contract and static checks passed, but the real business acceptance
did not complete. Run `run_1d6380cea6fc4a91b0586c1e79856ec4` remained a real
cancellable main turn for twelve minutes, with one visible Write confirmation
and two visible Agent confirmations approved inside the bounded window. Admin
showed the latest `deepseek-v4-pro` requests settled successfully, but no
canonical source files or stages were produced before the semantic deadline.
At the deadline the Thread projection showed two running subagents and no
completed main turn. Standard Thread Stop returned `stop_requested=true`, the
WorkflowRun was persisted as `cancelled`, and both subagent projections were
then released as completed. This is a model/subagent orchestration performance
failure, not a window, Provider availability, model alias, SSE or Run-isolated
layout failure. A full successful Artifact and Dream→Chat→Dream business result
remains unverified.

## Round 69 — Prove and enforce Dream Claude Session continuity

**Current-round objective**

Diagnose why a user message such as “继续” on an existing Dream Thread can be
handled without the prior Claude Code context, and make every non-initial Dream
turn resume the authoritative persisted Claude Session.

**Optimized Prompt**

> Trace Dream launch, shared Dream Chat composer, confirmation, guidance and
> internal-command dispatch into `ClaudeAgentThreadFactory.run_streaming()` and
> `ClaudeAgentService.assemble_context`. For each path, prove the value of
> `request.resume`, the authoritative `chat_thread.claude_session_id`, the local
> transcript probe and the resulting SDK `thread_id`. Inspect the affected real
> Thread using content-minimal database evidence. Preserve `resume=false` only
> for the first turn that has no Claude Session. For every later Dream turn,
> require a usable persisted Session and fail closed with a stable lifecycle
> error if its Session identity or transcript is unavailable; do not silently
> start a fresh Claude Session and pretend history was resumed. Keep ordinary
> Chat's existing recovery semantics unless a shared invariant is demonstrably
> required. Do not pass Dream context in the public Claude message, modify the
> Claude runner entry, or create a second runtime. Add focused contracts for
> initial launch, shared-composer continuation, internal commands and missing
> transcript/session behavior, then run proportional backend/frontend tests.

**Optional Enhancers**

- Emit content-free logs containing only Thread ID, resume decision and a stable
  reason code so future continuity failures are diagnosable without transcripts.

**Scope checked or modified**

- Dream dispatch request construction, Session resolution in context assembly,
  persistence/continuity contracts and focused tests.
- No Claude SDK entry, public Chat/Dream wire format, Dream SSE or unrelated
  workflow lifecycle changes.

**Completion standard**

The initial Dream turn starts exactly once without resume; every subsequent
Dream turn uses the same persisted Claude Session and its history, while a
missing/unusable Session fails explicitly instead of silently starting over.

**Actual result and unverified inferences**

Real Thread evidence proved the defect: the initial Dream turn created Claude
Session `14ab0bb4-30c8-4982-a4b1-e7d96b9415d6`, but Stop persisted only the
partial Chat assistant message and not that Session pointer. The later “继续”
request did carry `resume=true`; because `chat_thread.claude_session_id` was
empty, the service silently created Session
`6cffe7cd-1c59-4916-ae3e-08bab6b79d2c`. This was a Session lifecycle defect,
not proof of weak model context handling.

The historical-Dream classification proposed during this round was rejected by
business review because Dream and Chat already share the same Thread and Agent
runtime. It would have changed terminal Thread behavior and has been completely
removed. The transcript-scanning compensation proposed afterwards was also
removed because it inferred Session identity outside the existing SDK contract.
Round 71 replaces both with the shared SDK-native `on_message` persistence fix.
The affected cancelled real Thread was repaired to point back to its original
Session without deleting either transcript or any message. A new real-model
“继续” turn was not submitted during this round.

## Round 70 — Remove historical Dream classification from Agent runtime

**Current-round objective**

Correct the Session continuity fix so it does not reinterpret terminal Dream
workflow provenance as a second Claude Agent runtime category.

**Optimized Prompt**

> Remove `dream_thread_has_history`, `has_dream_history()` and every test or
> document claim that gives a terminal/historical Dream Thread special Agent
> execution semantics. Preserve the original boundary: only a currently
> resolved internal `dream_context` activates Dream business assembly; after a
> WorkflowRun is terminal, the same durable Thread follows the ordinary shared
> Chat lifecycle. Fix the observed continuity defect solely by persisting the
> Claude Session pointer when a first Dream turn is stopped or fails, recovering
> a unique missing pointer while the active Dream context is still authoritative,
> and honoring the existing public `resume=true` Chat request thereafter. Do
> not change the Claude runner entry, public message, mapper business meaning,
> workflow permissions or ordinary Chat transcript fallback.

**Optional Enhancers**

- Retain a regression proving a cancelled first Dream turn persists the new
  Claude Session ID before the next shared Chat message.

**Scope checked or modified**

- ClaudeAgentService Session persistence/resume logic, Dream binding mapper,
  focused tests and affected folder/design documentation.

**Completion standard**

The historical Dream classifier no longer exists; active Dream can never
silently restart when resume was requested; a stopped first Dream turn saves
its Session pointer; terminal Threads retain unchanged standard Chat behavior.

**Actual result and unverified inferences**

**Rejected and superseded by Round 71.** Historical Dream classification was
removed as required. The intermediate proposal to recover Session identity by
scanning transcript filenames was also rejected because the existing runner
already exposes the SDK-native Session ID through `on_message`; introducing a
second recovery definition was unnecessary.

## Round 71 — Re-audit shared Chat/Dream Claude Session management

**Current-round objective**

Re-check the reported “继续” context loss using the authoritative business
boundary that Dream and Chat share one Thread, one `chat_thread` row and one
ClaudeAgentService Session lifecycle.

**Optimized Prompt**

> Re-audit every production turn dispatcher and the full
> `ClaudeAgentService.assemble_context → ClaudeAgentRunner.run_streaming →
> persistence` path. Treat Dream and Chat as the same Agent runtime over the
> same durable `thread_id` and `chat_thread.claude_session_id`. Do not introduce
> a historical-Dream classifier, Dream-only resume state, new Session ID
> meaning, transcript-derived business identity, or changes to
> `existing_claude_session_id`, `should_resume`, `thread_id_for_agent` and the
> protected runner entry. Prove which callers send `resume=true`, when the SDK
> first emits its native Session ID, and which success/error/Stop paths persist
> it. Fix only the demonstrated missing persistence point through the existing
> shared callback/lifecycle contract, so every later standard `resume=true`
> request finds the original Session. Add focused shared Chat/Dream tests and
> verify the affected real Thread using IDs/status only.

**Optional Enhancers**

- Persist the SDK-native Session ID at first observation and keep the existing
  successful-turn write as an idempotent terminal safeguard.

**Scope checked or modified**

- Production Dream/Chat dispatchers, shared context assembly, runner callback
  contract, Session persistence, focused tests and affected documentation.

**Completion standard**

Every non-initial Dream path is proven to request resume; the original resume
resolution code is unchanged; the SDK-native Session ID is persisted before a
Stop can discard it; no Dream-only Session state or ID definition remains.

**Actual result and unverified inferences**

Fresh audit confirmed that `ChatPanel`, guidance, confirmation and internal
commands all send `resume=true`; only the first Dream launch sends the required
`resume=false`. `assemble_context` already loads the same
`chat_thread.claude_session_id`, validates the existing contract/transcript and
sets the original `resume_existing_session`, `existing_claude_session_id`,
`should_resume` and SDK `thread_id` values. Those lines are unchanged.

The actual missing write was after context assembly: the runner receives the
SDK-native Session ID in `SystemMessage(init)` and forwards that message through
its pre-existing `on_message` callback, but ClaudeAgentService did not register
the callback. It only persisted `result.session_id` after a successful turn, so
Stop skipped the write. The shared service now registers `on_message` and writes
that exact SDK-native ID to the same `chat_thread` immediately; resumed turns
are recognized and not redundantly rewritten, while the successful terminal
write remains unchanged and idempotent. No Dream-only state, transcript scan,
historical classifier, new ID definition, public DTO or runner-entry change
remains.

Verification passed 151 focused backend tests with 38 subtests; two unrelated
tests were skipped by their existing conditions. Coverage includes standard
Thread resume from the persisted ID, SDK-init ID persistence before cancellation,
Dream confirmation/internal recovery, ThreadFactory and Dream acceptance. The
dispatcher-focused launch/guidance/confirmation/internal-command/service set
also passed 148 tests with 60 subtests (three existing conditional skips), and
the shared Dream/Chat frontend reconnect/layout contracts passed 7 tests with
one worker. The affected real Thread still points to its original Session and
the restarted local backend is healthy. A new real-provider continuation
response remains unverified.

## Round 72 — Review and commit the shared Session persistence fix

**Current-round objective**

Review the completed shared Chat/Dream Claude Session continuity change and
commit only the files belonging to that fix.

**Optimized Prompt**

> Inspect the working tree and confirm that the pending change preserves the
> original `claude_session_id`, `existing_claude_session_id`, `should_resume`
> and `thread_id_for_agent` business definitions. Verify that the only runtime
> behavior change is early persistence of the SDK-native Session ID through the
> existing shared `on_message` callback, with focused cancellation and resume
> tests plus synchronized folder documentation. Exclude unrelated user work,
> run the proportional regression and whitespace checks, then create one
> descriptive Git commit without amending or rewriting history.

**Optional Enhancers**

- Include the test counts and commit hash in the final handoff.

**Scope checked or modified**

- Shared ClaudeAgentService Session persistence, focused tests, folder
  contracts and this execution record only.

**Completion standard**

The reviewed diff contains no Dream-only Session semantics or unrelated files;
the focused tests and `git diff --check` pass; one normal Git commit is created.

**Actual result and unverified inferences**

The reviewed diff contains exactly the shared service implementation, its
focused tests, the two affected folder contracts and this execution record. The
two critical Session resume/cancellation tests passed and `git diff --check`
reported no whitespace errors. No new real-model request is part of this commit
round; provider-level semantic continuation remains outside this Git operation.

## Round 73 — Design server-detected Deck output synchronization

**Current-round objective**

Design how a Dream Agent learns that a Deck plugin has produced valid output
and can synchronize it into the private Run surface without generic `.dream`
writes or a second lifecycle owner.

**Optimized Prompt**

> Reconstruct the initial Dream generation contract from Codex task
> `019fcb01-c61c-7f22-9d56-fb38660f042a` and the multi-Episode action contract
> from `019fd74e-e06f-7073-a714-fe86cdada2ce`. Design one explicit Story
> Workspace MCP checkpoint triggered by the main Agent after a Deck workflow
> step returns. The server must derive the current actor, Thread, Run, message,
> Deck output contract, Project, Episode, action and revisions; stably observe
> allowlisted canonical files; return structured not-ready/invalid/synced/
> sealed/conflict results; synchronize through private staging; and record
> completion or final immutable publication with CAS. Reject filesystem
> watchers, PostToolUse inference, Observer ownership, browser paths, Agent-
> supplied revisions and generic `.dream` mutation. Cover initialization,
> Episode actions, idempotency, cancellation, concurrency, recovery, security,
> diagrams, migration and tests without changing the shared Chat runtime.

**Optional Enhancers**

- Make the Deck manifest advertise only a reviewed output-contract identifier;
  keep path/parser definitions in a server registry frozen by the Deck lock.

**Scope checked or modified**

- Initial Dream run/stage production, Project/EP01 binding, Episode workflow
  checkpoints, private staging/sealing, Observer boundary and design docs.
- No production code, Claude runner, public Chat DTO/SSE or database DDL change.

**Completion standard**

The design explains exactly when the Agent calls which MCP tool, how readiness
is proven, how the Agent reacts to each structured result, how duplicate/racing
calls remain safe and how mutable authoring differs from immutable publication.

**Actual result and unverified inferences**

The accepted design uses an explicit Agent checkpoint with server-side stable
observation; it rejects watcher/Observer/hook inference. It separates initial
stage synchronization, per-action staging synchronization and final atomic
Artifact sealing, while preserving the existing `.dream` write guard and shared
Thread runtime. A final source review found that current `bind_first_episode`
correctly permits only `plan_episode` or recovery provenance, so initialization
now has a distinct one-use private launch claim and a path/revision-free
`bind_initial_project_episode` checkpoint instead of weakening that guard.
Production implementation and real Deck/model validation have not been
performed. The current sealed four-file Artifact layout also omits Prompt/render
outputs required by the workflow; that versioned allowlist must be reconciled
before publisher implementation.

## 第 74 轮——补全 Deck 产物同步业务时序并中文化设计文档

**当前轮次目标**

将 Deck 产物检测与 `.dream` 私有发布设计从技术检查点说明，重写为可供业务审核的中文设计；补全首次初始化、Episode 动作、产物未就绪修复、最终发布、重复/并发、取消恢复和 Observer 刷新的独立业务交互时序图。

**优化后的执行提示词**

> 以当前生产代码、首次 Dream 初始化需求和多 Episode 工作流为事实基础，完整重写 Deck 产物检测与 `.dream` 私有同步设计。文档必须使用中文，明确区分规范创作工作区、Run 私有暂存区和不可变发布 Artifact；说明谁发起同步、谁检测完成、谁拥有业务 claim、谁写 workflow 完成事实以及 Agent 如何根据结构化结果继续或停止。至少分别提供首次初始化、普通 Episode 动作成功、未就绪修复重试、最终校验与原子发布、重复/并发幂等、Stop/取消后恢复、Observer 失败隔离的 Mermaid 业务时序图。不得使用文件监听器、PostToolUse 推断、Agent 自报完成、浏览器路径、Agent 提交 revision、Observer 控制流程或通用工具写 `.dream/**`。保留共享 Chat thread runtime，明确当前实现与目标设计的差异、迁移步骤和验收条件。

**可选增强项**

- 为每张时序图补充业务前置条件、成功事实、失败后的用户可见结果。
- 使用同步规则矩阵说明不同状态下 Agent、服务端和页面分别执行什么动作。

**本轮检查或修改范围**

- `docs/design/dream-agent/deck-output-sync-design.md`。
- DreamAgent 文档目录、Dreamflow 工具边界说明和文档目录合同。
- 不修改生产代码、Claude Agent 入口、Chat SSE、数据库 DDL 或真实业务数据。

**本轮完成标准**

- 同步规则可从业务泳道直接审核，不依赖技术实现猜测。
- 所有新增同步场景都有独立 Mermaid 图。
- 本轮新增/更新的同步设计正文使用中文，术语和状态含义一致。
- Markdown 围栏、相对链接和差异检查通过。

**本轮实际结果和未验证推断**

- 已将同步设计全文重写为中文，新增首次初始化、普通 Episode 动作、未就绪修复、最终发布、重复/并发、Stop/取消恢复、Observer 失败隔离七张独立业务时序图，并保留一张 Artifact 协调状态图。目录、Dreamflow 边界说明和文档目录合同已同步更新。
- 本轮只修改设计文档；生产 checkpoint、private staging、publisher 和真实 Deck/模型验收仍未执行，不能把本文档状态解释为代码已交付。

## 第 75 轮——同步设计文档验证

**当前轮次目标**

验证中文同步设计的结构、图表、链接和差异质量，确保新增业务时序可以被文档工具解析且没有把待实现能力写成已交付事实。

**优化后的执行提示词**

> 对 Deck 产物同步设计执行只读文档验收：统计并逐一解析所有 Mermaid 图；检查 Markdown 围栏成对、相对链接目标存在、标题和说明已中文化、README 与 folder contract 已建立入口；运行 `git diff --check`；反向搜索 watcher、PostToolUse、Observer、通用 `.dream` 写入、已实现 publisher 等禁止或误导性表述，确认它们只以“拒绝方案/待实现差异”出现。输出实际通过项和仍未验证的生产实现，不运行真实模型或修改业务数据。

**可选增强项**

- 如果本地 Mermaid 渲染器缺少 DOM 环境，至少分别提取图块并使用项目已有解析入口验证，明确工具限制。

**本轮检查或修改范围**

- 本轮更新的四份设计文档和 `docs/design/.folder.md`。
- 只读验证；发现文档缺陷时才做最小修正。

**本轮完成标准**

- 七张业务时序图和一张状态图数量正确、围栏完整。
- 相对链接无死链，差异无空白错误。
- 文档明确区分“设计已接受”和“生产实现待完成”。

**本轮实际结果和未验证推断**

- `git diff --check` 通过；同步设计共有七张业务 `sequenceDiagram` 和一张 Artifact 状态图，Markdown 围栏共 40 个且成对。
- 项目现有 Mermaid 11.16.0 在纯 Node 入口中逐张解析：七张业务时序图全部 PASS；状态图已完成语法解析，但在 DB 语义抽取阶段遇到 Mermaid Node 环境自身的 `DOMPurify.addHook is not a function`，因此未把状态图记为完整渲染通过。该错误发生在 sanitize 阶段，不是 parser 返回的 Mermaid 语法错误。
- README 和 Dreamflow 的新增相对链接目标存在；英文业务标题反查完成，保留的英文只属于 Deck、Dream、Artifact、MCP、Observer 类名、状态/工具标识等固定技术词。
- 未运行浏览器渲染、生产代码测试、真实 Deck 或真实模型；这些仍属于实现后的验收范围。

## 第 76 轮——将同步设计改为主 Agent 生命周期自动同步

**当前轮次目标**

纠正将 Drama 命令建模为固定顺序工作流、并依赖 Agent 主动调用 MCP 才能同步的设计错误；基于真实 Claude Agent 生命周期 hook 和 Deck 命令合同，设计首次初始化默认执行、其余命令随机按需执行时的自动产物检测与同步。

**优化后的执行提示词**

> 重新审查 DreamAgent、ClaudeAgentService、Claude Agent runner、SessionObserverRegistry、SDK hook 和 Deck 命令实现。业务事实是：首次空间初始化默认执行 `/drama-init`；之后 `/drama-plan`、`/drama-script`、`/drama-asset`、`/drama-storyboard`、`/drama-prompt`、`/drama-render`、`/drama-voice`、`/drama-edit`、`/drama-promote`、`/drama-query`、`/drama-doctor`、`/drama-payoff` 均由用户按需、重复、无固定顺序执行。设计主 Agent turn 前后的确定性 hook：turn 前记录受控工作区基线与授权上下文，turn 后在主 Agent 单终态结算前或结算协调阶段比较产物、按输出合同校验并自动同步 `.dream` 私有投影；必须区分主 Agent 与子 Agent、成功/失败/取消/确认等待、无文件变化、部分写入、重复执行和并发 turn。MCP 只作为 Agent 主动检查、修复反馈和显式重同步的辅助入口，不能成为自动同步正确性的必要条件。不得修改 Claude SDK 入口，不新增第二套 Agent runtime/SSE，不让 Observer 成为同步 owner，不把命令强制串成 workflow DAG。用中文更新业务规则、时序图、状态和迁移清单，并明确哪些旧设计被否决。

**可选增强项**

- 使用 command-output registry 表达每条命令可能产生的文件集合和校验策略，而不是固定 predecessor。
- 将自动同步设计成 ClaudeAgentService 生命周期中的命名类，不使用闭包或测试环境分支。

**本轮检查或修改范围**

- ClaudeAgentService assemble/session execution、runner hooks、SessionObserverRegistry、Story Workspace MCP 和 Deck 命令合同的只读检查。
- `docs/design/dream-agent/deck-output-sync-design.md`、相关业务/工具边界和文档索引。
- 不修改生产代码、Claude Agent 入口、数据库或真实业务数据。

**本轮完成标准**

- 首次 init 与后续随机命令的业务规则准确。
- 自动同步不依赖模型记得调用 MCP。
- hook 在失败、取消、子 Agent、重复和并发场景中不会误同步或重复终态。
- MCP、Observer、ClaudeAgentService 和同步协调器职责无重叠。

**本轮实际结果和未验证推断**

- 源码确认现有 SDK `PreToolUse/PostToolUse` 只覆盖单工具，`SessionObserverRegistry.on_after_session_started` 没有根 turn outcome 且异常会被隔离，二者都不能承担自动同步正确性。目标 Hook 因此放在 `ClaudeAgentService`：assembly 后记录 Ticket，根 runner settlement 后自动 diff、校验和同步；原 runner 入口保持不变。
- 已将同步设计、Dreamflow 边界、B04/B16/B19 业务交互、Project/Episode workflow v2 概念、目录和正式设计审查改为“init 默认、其余命令随机可重复、Hook 自动同步、MCP 辅助”。
- 当前 `episode_workflow_instruction.py`、next-action resolver、前端 action projection 和测试仍是固定流程；本轮未修改生产代码。DramaForge skill 输出路径也存在多套布局，canonical registry 尚未冻结，真实 Hook/Deck/模型验证未执行。

## 第 77 轮——随机命令自动同步设计验证

**当前轮次目标**

验证修订后的文档没有残留固定命令 DAG、Agent 必须调用 MCP、Observer 同步 owner 或 no-next-action 完成 Workflow 的规范性表述，并确认业务时序图可解析。

**优化后的执行提示词**

> 对 R76 变更执行文档验收：逐个解析受影响 Markdown 中的 Mermaid；检查围栏、相对链接和 `git diff --check`；搜索 next_action、no_next_action、固定顺序、stage checkpoint、MCP 必做、action 只能完成一次等旧语义，确认剩余命中只作为“当前实现差异/待删除”存在；核对十三条命令、首次 init、根 turn before/after hook、子 Agent 单次结算、success/error/cancel、no-change、重复 revision 和辅助 MCP 均有明确合同。不得运行生产写测试或真实模型。

**可选增强项**

- 将生产源码中的固定流程命中单列为实施差异，避免误报为文档遗漏。

**本轮检查或修改范围**

- R76 修改的 DreamAgent 设计文档和目录合同。
- 只读验证；只在发现矛盾时进行最小文档修正。

**本轮完成标准**

- Mermaid、Markdown、链接和 diff 检查通过。
- 规范正文只有随机命令和自动 Hook 一套同步真相。
- 当前代码未实现的部分被明确标记，不能误读为已交付。

**本轮实际结果和未验证推断**

- `git diff --check` 通过。十三条 Drama 命令在新同步设计中全部存在，before/after 根 turn、子 Agent 单次结算、success/failed/cancelled、confirmation wait、no-change、重复 revision 和辅助 MCP 合同均有直接文本或时序覆盖。
- 使用项目 Mermaid 11.16.0 解析四份受影响文档的 30 张图：同步设计 4 张、Dreamflow 1 张、B01–B21 业务图 22 张、Project/Episode 合同 3 张；29 张 PASS。Project/Episode 第一张既有 flowchart 在语法解析后的 sanitize 阶段触发纯 Node 环境 `DOMPurify.addHook is not a function`，未记为完整渲染通过。
- 旧 `next_action/no_next_action`、固定 stage、Agent 必须调用 MCP 和 action 单次 completion 的剩余文档命中均位于“当前实现差异/待迁移删除”说明，没有作为目标规范继续使用。新增相对链接目标存在。
- 未修改生产代码；当前固定 action 实现、canonical output layout、Hook/synchronizer/MCP 和真实 Deck/模型仍未迁移或验证。

## 第 78 轮——最小工作台产物闭环实施

**当前轮次目标**

对比 Codex 任务 `019fd74e-e06f-7073-a714-fe86cdada2ce` 与 `019fcb01-c61c-7f22-9d56-fb38660f042a` 中实际生成和展示过的业务产物，放弃此前大部分固定 workflow、action、checkpoint 和命令编排方案，只完成“主 Agent 产出工作台文件 → 自动同步到当前 Run 的 `.dream` 私有路径 → Dream 页面正确显示”的最小业务闭环。

**优化后的执行提示词**

> 基于两个指定 Codex 历史任务、当前 Git 历史、现有 Story Workspace 文件合同和 Dream 页面代码，识别页面真正消费的初始化与 Episode 产物，不沿用历史任务中的固定阶段 DAG、next action、checkpoint 或命令顺序。保持 Chat/Dream 共用 thread、message、Claude session、SSE 和 `ClaudeAgentService`；不修改 Claude Agent runner 入口或原始 `claude_session_id` 语义。在主 Agent 根 turn 的既有服务生命周期中，以标准类实现一次确定性的产物收集与同步：只处理当前授权 workspace/run 下的受控工作台文件，按内容摘要幂等复制到 `.dream/runtime/runs/<run-id>/artifact/`，失败不得伪造 Agent 成功或产生第二终态，取消与未完成写入不得发布。Dream 页面和 `dream-files` API 直接读取该私有投影并正确呈现已有产物、空状态和刷新结果。添加契约与回归测试，随后使用本机真实数据、真实账号、真实模型和真实页面验证；不得克隆业务数据，不创建多环境实现，不改数据库 DDL。

**可选增强项**

- 若既有输出注册表足以覆盖页面所需文件，复用并缩减它；不要为了未来命令引入通用 DAG 或事件存储。
- 对不影响最小闭环的旧 action UI 仅隔离或停止依赖，避免无关的大范围删除。

**本轮检查或修改范围**

- 两个 Codex 历史任务的用户要求、助手交付摘要和相关 Git 提交。
- `ClaudeAgentService` 根 turn 生命周期、Story Workspace 工作台/Run 文件服务、`dream-files` API 与 Dream 页面。
- 对应中文设计、后端/前端契约测试和真实浏览器验收。
- 不修改 `backend/libs/claude_agent_kit/server/agent_runner.py`、Claude 报文、共享 thread/session 定义、Admin DDL 或无关模块。

**本轮完成标准**

- 页面所需工作台产物由历史事实和当前消费者共同确定，不由旧固定流程推断。
- 主 Agent 正常结束后自动同步，重复执行幂等，失败/取消不发布半成品。
- `.dream` 私有路径、API 和页面对同一 Run 的内容一致，刷新后仍可恢复。
- 聚焦后端/前端测试、类型/构建和真实业务页面验证通过，Admin 可观察到真实运行记录。

**本轮实际结果和未验证推断**

- 进行中。尚未修改生产代码；两个历史任务的最终产物集合、现有同步缺口和页面消费者仍在逐项核对。

## 第 79 轮——真实历史产物兼容性校验

**当前轮次目标**

使用本机历史真实工作台文件校验最小同步 Hook，修正源文件解析与现有真实产物之间的兼容问题，同时不放宽 `.dream` 私有发布路径和 canonical Project/Episode 身份约束。

**优化后的执行提示词**

> 对已有真实 Story Workspace 中的角色、场景、分镜和 Project/Episode 文件执行只读收集验证。源工作台允许正常 Unicode 文件名、无 frontmatter 的 YAML，以及以 Markdown 分隔线开头但没有 frontmatter 结束标记的普通正文；解析器应优先读取结构化 YAML，缺少结构化字段时使用安全的文件名或一级标题回退。目标 `.dream/runtime/runs/<run-id>/artifact/` 仍只接受服务端派生的 ASCII project slug、EPxx 和 allowlist 文件名，canonical project 身份不匹配必须拒绝发布，不能用兼容逻辑掩盖。增加回归测试并重新验证三个历史真实布局；不得改 Claude Agent 入口、session、SSE 或数据库。

**可选增强项**

- 仅在普通 Markdown 确实没有闭合 frontmatter 时回退为正文；已闭合但无效的 YAML 仍 fail closed。
- 页面投影和私有 artifact 发布分别报告，便于定位历史不合规项目而不混淆页面产物。

**本轮检查或修改范围**

- `backend/services/story_workspace/dream_artifact_turn_hook.py` 的源文件路径和内容解析。
- 对应聚焦回归测试及本机历史工作台只读探测。
- 不修改页面协议、Claude 报文或工作流状态。

**本轮完成标准**

- Unicode 资产文件、plain YAML 和普通 Markdown 均能形成稳定页面投影。
- 非法 canonical project 不进入 `.dream` 私有 artifact。
- 新规范产物重复同步仍无 revision 增长，manifest 仍为最后提交点。

**本轮实际结果和未验证推断**

- 进行中。已确认历史布局存在 Unicode 资产名、plain YAML 和以分隔线开头的 Markdown；修正和真实只读复测尚未完成。

## 第 80 轮——最小闭环文档收敛

**当前轮次目标**

将此前偏复杂的同步、随机命令、revision 和 checkpoint 方案收敛为已经实现的最小业务事实：工作台文件、根 turn 自动同步、`.dream` 页面投影和页面刷新。

**优化后的执行提示词**

> 以当前实现和两个指定历史任务的真实产物为准，重写 Dream 工作台同步设计。正文只保留：canonical 工作台允许路径；`ClaudeAgentService` 根 turn 成功后的命名 Hook；角色/场景/分镜页面 stage 投影；Project/Episode allowlist 私有 artifact 与 manifest；Dream 页面通过既有 `dream-files` GET 恢复；权限、幂等、失败隔离和不修改 Chat/Claude session 的边界。删除 command-output registry、固定或随机命令编排、通用 Artifact revision 状态机、next action、checkpoint、Agent 感知上一轮同步结果和未来 MCP resync 等未实现且当前不需要的方案。所有正文使用中文，并提供一张普通成功时序、一张重复/失败时序和一张页面恢复时序。同步 README、业务清单、工具边界、Project/Episode 合同和设计审查的实现状态。

**可选增强项**

- 将历史任务差异只保留为一张产物对照表，不复述执行过程。

**本轮检查或修改范围**

- `deck-output-sync-design.md` 及直接引用其合同的 DreamAgent 文档。
- 不修改生产代码或执行真实模型。

**本轮完成标准**

- 文档没有把未来命令编排、MCP 或 checkpoint 写成目标组成部分。
- 图和文字与当前代码的成功后同步、manifest 原子提交、页面 stage 读取一致。
- 不误称 Claude runner、Observer 或前端为同步 owner。

**本轮实际结果和未验证推断**

- 进行中。生产 Hook 与三套历史文件的只读投影已验证；文档尚未完成收敛。

## 第 81 轮——实现与静态验证

**当前轮次目标**

验证根 turn 自动同步实现没有破坏共享 Chat runtime、Dream 页面合同或受保护 Claude runner，并完成进入真实模型测试前的全部本地门禁。

**优化后的执行提示词**

> 对最小工作台闭环执行分层验证：先运行 Hook、ContextBuilder、ClaudeAgentService、Dream launch/runtime 和 dream-files 页面合同聚焦测试；再运行合理范围后端全量、前端 Dream/Chat 契约、TypeScript、ESLint 和 production build。检查 `agent_runner.py` 无 diff、Claude session/resume 定义无改动、没有新增 Dream SSE/DTO/环境分支。解析新增 Mermaid，检查 Markdown 相对链接、Python 编译和 `git diff --check`。失败必须定位并修正真实根因，不用固定 sleep、伪造业务数据、放宽权限或删除断言绕过。

**可选增强项**

- 用历史真实工作台执行只读 parser probe，作为格式兼容证据，不写历史 Run。

**本轮检查或修改范围**

- 当前变更的生产代码、测试和 DreamAgent 文档。
- 不启动真实模型，不修改本机业务数据。

**本轮完成标准**

- 聚焦和合理全量测试、类型、lint、build、文档门禁全部通过。
- `agent_runner.py`、session identity、Chat payload 和前端 transport 无本轮 diff。
- 进入真实业务验证前无已知代码阻断。

**本轮实际结果和未验证推断**

- 进行中。聚焦后端测试已达 118 passed、1 skipped；其余门禁尚未执行。

## 第 82 轮——真实 Run 的共享 SSE 重放恢复

**当前轮次目标**

修复真实 Dream Run 在页面晚挂载后无法及时显示标准 `Agent` 工具确认的问题；修复必须位于共享 Chat 重连 reducer，不新增 Dream 专用协议、状态或确认入口。

**优化后的执行提示词**

> 使用真实账号、真实 `deepseek-v4-pro` Run 和标准 thread SSE 诊断晚挂载恢复。后端运行时确认存储已持有 pending ID，EventBus 也能完整重放 `tool-input-*` 与 `tool-approval-request`；若浏览器因为数万个细粒度 reasoning/text delta 逐事件执行 React 状态更新而无法及时抵达确认事件，应在共享 `ChatPanel` 重连消费层实现有界批处理，并只归并相邻、同 ID 的 reasoning/text delta。必须保持非 delta 事件顺序、工具输入、确认、Stop、finish 和历史恢复语义；Chat 与 Dream 同时复用，不改 Claude 报文、runner、session ID 或 Dream API。添加共享 reducer/页面契约测试，再继续同一个真实 Run 的可见 UI 确认；测试不得通过后端接口代替用户点击。

**可选增强项**

- 将批处理归并提取为纯函数，以可重复单元测试证明跨工具边界不重排事件。
- 记录真实 replay 的事件数量和类型，不记录 reasoning 正文或工具输入正文。

**本轮检查或修改范围**

- `frontend/src/components/chat/ChatPanel.tsx` 及共享 Chat 重连测试。
- 当前真实 Run `run_5feb30d84d7e4b3fbfac6efd66bca3aa` 的只读状态、SSE 类型和可见页面确认。
- 不修改 Dream transport、Claude Agent runner、Claude session 定义、数据库或真实 Run 内容。

**本轮完成标准**

- 晚挂载页面能从同一 thread SSE replay 显示标准 `Agent` 确认卡。
- 浏览器通过可见按钮完成确认，Agent 继续运行；不调用隐藏确认 API。
- 大量 delta 被有界归并，工具和终态事件不丢失、不乱序、不重复。

**本轮实际结果和未验证推断**

- 诊断已确认 pending 工具为标准 `Agent`，后端 status 返回该 call ID，EventBus 重连可重放完整流；一次两秒只读采样已收到约 1.6 MB、1.7 万余个细粒度事件。
- 页面尚未显示确认卡；共享批处理修复和真实 UI 复测尚未完成。

## 第 83 轮——真实模型幂等重试阻断诊断

**当前轮次目标**

诊断真实 `deepseek-v4-pro` Run 在工具返回后的续接请求被 Gateway 以 409 拒绝的问题，核对 Claude Code 默认三次重试与 Admin 请求幂等账本，解除真实模型验证阻断；不把模型/Gateway 故障误归因于 Dream 同步。

**优化后的执行提示词**

> 以 Run `run_99a9ac79ed3e4c408e07795b26e38d99`、thread `636d77d5-09ac-5f75-8607-dab55c83e7a8` 和 Admin Gateway 正常业务账本为证据，追踪 `409 A request with this Idempotency-Key is still in progress` 的请求状态、耗时、重试次数和终态。检查当前 Claude Code/SDK 默认重试配置是否确为三次，以及 Gateway 对同一幂等键的 in-progress join/reject 合同；不得修改 `agent_runner.py`、Claude session ID、Dream SSE 或通过更换模型绕过。若问题来自本机残留未结算请求，等待或按现有安全恢复语义处理；若存在配置/代码缺口，只做最小共享 Gateway/Claude Code 配置修复并添加契约测试。随后重新运行真实有头人类旅程，确认工作台文件、`.dream` manifest 与页面展示。

**可选增强项**

- 只输出请求 ID、模型、状态、耗时和错误码等内容无关回执，不打印提示词、reasoning、Token 或 Secret。

**本轮检查或修改范围**

- Dream 侧 Claude SDK 启动配置、Admin Gateway 幂等/请求账本和当前真实 Run 日志。
- 不修改 Dream Artifact Hook、Claude 报文或数据库数据。

**本轮完成标准**

- 409 的真实来源和责任边界有 Admin/运行日志证据。
- 默认三次重试配置正确，且不会制造并发重复模型请求。
- 新真实 Run 不再因同类 409 失败，最终业务闭环通过。

**本轮实际结果和未验证推断**

- 已确认第二个真实 Run 在约十分钟后失败，后端 runner 报告 Gateway 409：同一 `Idempotency-Key` 的请求仍在处理中；Run 未生成工作台文件，Hook 未发布半成品。
- Admin 账本、默认重试配置和修复路径尚未完成核对。

## 第 84 轮——首次 Dream 最小工作台指令收敛

**当前轮次目标**

将首次 Dream 从完整 Drama 插件探索收敛为最新业务要求的最小初始化产出：直接写人物、场景和分镜工作台文件，成功后由宿主同步 `.dream` 并在页面显示。

**优化后的执行提示词**

> 修改首次 Dream 的服务端可信指令：后端从原始 goal 确定性派生并明确给出唯一 ASCII `project_id/project_slug`，模型必须原样使用，不得自行计算哈希。明确本轮不需要读取或搜索插件源码、CLAUDE.md、模板，不调用 `Agent`、`WebFetch`、`WebSearch`、AskUserQuestion 或 Dream MCP，不执行完整 `/drama-init` 命令编排；只使用内建 `Write` 直接创建至少两个人物卡、一个场景卡、规范 `project.yaml` 和 `EP01/storyboard.yaml`，写成简洁可编辑草稿后结束 root turn。保留共享 Chat 工具确认、Claude session 和成功后 Artifact Hook；不得自动批准 Write。更新指令契约测试，并使用真实 `deepseek-v4-pro` 重跑。

**可选增强项**

- 在指令中给出精确目标路径和最小字段，而不是让模型从插件文档推断布局。

**本轮检查或修改范围**

- `canonical_project_instruction.py` 的已分配 ID 优先规则。
- `dream_launch_infrastructure.py` 的首次 launch 指令及对应测试。
- 不修改 Claude Agent runner、Gateway 幂等实现、模型设置或页面协议。

**本轮完成标准**

- 首次 Run 不再调用 Agent/WebFetch 或自行计算 project hash。
- 页面可见 Write 确认后，目标五类文件在较少工具回合内完成。
- 宿主 Hook 同步三个 stage 和私有 manifest，页面刷新可恢复。

**本轮实际结果和未验证推断**

- Admin 账本显示失败 turn 在大量成功工具请求后出现两次 120 秒 `UPSTREAM_CONNECTION_ERROR`；失败请求体约 607KB、41 条 message、43 个 tools。`CLAUDE_CODE_MAX_RETRIES` 默认值与测试均为 3，不需要改 runner。
- 已由服务端从原始 goal 分配唯一 project slug，并把首轮指令限制为内建 `Write` 创建两个人物、一个场景、一个项目文件和一个 EP01 分镜；明确禁止插件扫描、联网、子 Agent、AskUserQuestion 和 Dream MCP。
- 指令与共享生命周期聚焦测试通过：109 passed、1 skipped、40 subtests。真实页面复测进入下一轮。

## 第 85 轮——真实最小闭环最终验收

**当前轮次目标**

使用本机真实账号、真实数据、真实 `deepseek-v4-pro` 和可见 Chromium，完成“工作台文件生成 → 宿主同步 `.dream` → Dream 页面展示”的最小业务闭环。

**优化后的执行提示词**

> 重启当前 Dream 后端以加载已验证的最小首轮指令；保留现有 Admin 与 Vite 服务。使用用户指定的本机真实账号、真实 Deck 和 `deepseek-v4-pro` 启动一个全新 Dream Run。像正常用户一样在可见浏览器中操作，语义等待标准 Write 确认并通过页面按钮批准，禁止调用隐藏确认接口、固定 sleep、克隆数据或伪造模型结果。主 Agent 应只创建两个人物文件、一个场景文件、`project.yaml` 和 `EP01/storyboard.yaml` 后结束。随后核对 authoritative workflow run、canonical 工作台文件、`.dream/runtime/runs/<run-id>/stages/*.json`、`artifact/manifest.json`、页面人物/场景/分镜展示，以及刷新和同 thread Chat 切换恢复。失败时保留真实 Run、请求 ID 和页面证据并修复根因；不修改 Claude runner、session ID、Chat SSE 协议或 Gateway 默认重试。

**可选增强项**

- 在 Admin 可见日志中确认本次真实模型请求，但不输出正文、Token、DSN 或 Secret。
- 保存不含敏感内容的验收回执与页面截图。

**本轮检查或修改范围**

- 当前后端服务、真实 Dream 页面、标准 Chat confirmation、工作区与该 Run 的 `.dream` 私有发布目录。
- 只在真实失败暴露根因时做最小修复；不恢复此前固定命令 workflow 或 MCP 主同步方案。

**本轮完成标准**

- 真实 root turn 成功且只产生一个完成终态。
- 五类 canonical 工作台文件存在，Hook 写出 stages 与 manifest，内容摘要匹配。
- Dream 页面在当前视窗正常显示人物、场景和分镜；刷新及 Chat 切换保持同一 thread。
- 真实模型请求可在 Admin 账本中追踪，所有测试进程和异步资源状态明确。

**本轮实际结果和未验证推断**

- 真实 Run `run_33f42331b5ab46ac81d38f42398c3901` 已由 `deepseek-v4-pro` 生成两个人物、一个场景、规范 `project.yaml` 与 `EP01/storyboard.yaml`；宿主成功写出三个 stage 和 `artifact/manifest.json`，页面刷新及切换 Chat 后返回均持续读取 200。
- 业务闭环已成立，但有头脚本在浏览器已经返回 Dream 后仍挂在 `page.goBack()` 的页面加载完成信号，未输出 Playwright 成功终态；进入第 86 轮修复测试导航等待并重跑。

## 第 86 轮——有头验收返回导航收口

**当前轮次目标**

修复仅存在于真实验收脚本的浏览器返回等待挂起，获得完整 `--headed --workers=1` 成功结果；不改变已经通过的业务实现。

**优化后的执行提示词**

> 保留第 85 轮真实 Run、工作台和 `.dream` 证据。当前浏览器已从 Chat 返回 Dream，后端持续收到 run 与 dream-files 200，但 Playwright 的无界 `page.goBack()` 仍等待页面 load 信号。终止仅挂起的 E2E 浏览器；将返回动作设为有界、以 navigation commit 为完成点，随后继续使用 Dream URL、视窗适配和“确认并继续”可用性作语义等待。不得使用固定 sleep、隐藏 API 代替页面验证或修改生产路由。重新执行同一完整真实人类旅程并保存内容无关回执。

**可选增强项**

- 在关键页面切换点输出不含正文的测试进度，便于区分业务等待与导航等待。

**本轮检查或修改范围**

- 仅 `frontend/e2e/dream-launch-real-model.spec.ts` 的返回导航等待和最终真实 E2E。
- 不修改生产业务代码、真实 Run、Claude session 或模型配置。

**本轮完成标准**

- 新真实 Run 再次生成并同步最小文件。
- 页面刷新、Dream→Chat→Dream 均通过有界语义等待。
- Playwright 进程明确以 1 passed 退出，无残留测试浏览器。

**本轮实际结果和未验证推断**

- `page.goBack({ waitUntil: 'commit', timeout: 30_000 })` 已实施；第二个真实 Run `run_45b66fb3dfe04e86a164d43e19aff670` 再次产出 2 人物、1 场景、1 分镜并同步 `.dream`。
- 页面已切换 Chat 并返回 Dream，仍持续读取 200；脚本继续停在测试尾部，排除返回导航，定位到诊断器等待错误响应完整 body 的无界 Promise。

## 第 87 轮——真实验收诊断器非阻塞收尾

**当前轮次目标**

移除 E2E 诊断器读取 API 错误正文造成的潜在无界等待，同时减少业务正文泄漏风险，获得明确的有头成功终态。

**优化后的执行提示词**

> 修改真实 Dream E2E 的只读诊断器：HTTP API 错误在 response 事件到达时立即记录状态码与 URL，不读取或缓存 response body，不维护需要在测试尾部等待的 Promise。保留 console、pageerror、requestfailed 与 dream-files 状态断言。此修改只影响测试证据采集，不改变页面、后端或真实业务。终止当前只剩诊断收尾挂起的浏览器，重新以 `--headed --workers=1` 执行；最终必须明确 1 passed，并确认无 Playwright 测试进程残留。

**可选增强项**

- 保留 `settle()` 空实现以减少调用面改动，后续可单独清理接口。

**本轮检查或修改范围**

- `frontend/e2e/dream-launch-real-model.spec.ts` 的 `installDiagnostics`。
- 不修改生产代码、模型、Gateway、session 或工作区数据。

**本轮完成标准**

- 诊断器不读取 API 错误正文，不存在尾部 Promise 挂起。
- 完整真实有头旅程以 1 passed 退出。
- 第三个真实 Run 的文件、`.dream`、页面与 Admin 请求证据完整。

**本轮实际结果和未验证推断**

- 诊断器已改为只记录 API 状态码与 URL，不读取正文；第三个真实 Run `run_0917bd9a7c97462793582d04486da890` 再次完成 2 人物、1 场景、1 分镜及 `.dream` 发布。
- 可见窗口确认 Dream 内容与“确认并继续”均正常，但页面底部存在横向滚动条；验收实际停在页面适应窗口断言，诊断器不是剩余阻断。

## 第 88 轮——Story Workspace 窗口适配修复

**当前轮次目标**

消除 Dream 页面在 1200×720 真实视窗中的根级横向溢出，使页面正常适应窗口并完成最终有头验收。

**优化后的执行提示词**

> 基于第三个真实 Run 的可见页面证据诊断 Story Workspace 外层横向滚动条。保持 Dream 双栏内部滚动与移动端响应式设计，只让共享主内容容器在水平方向裁剪根级布局溢出、纵向继续按现有规则滚动；不得用放大测试视窗、降低断言阈值或隐藏具体业务内容规避。添加/更新布局契约测试，确认 1200×720、侧栏展开、Dream 人物编辑页的 `max(documentElement.scrollWidth, body.scrollWidth) <= clientWidth + 1`。随后重跑真实 `--headed --workers=1`，由同一语义断言证明修复。

**可选增强项**

- 验证侧栏收起与小屏断点没有回归。

**本轮检查或修改范围**

- `StoryWorkspaceLayout.css` 的主内容 overflow 边界、相关前端测试和真实 E2E。
- 不修改 Dream 后端、Artifact Hook、Claude Agent 或真实业务数据。

**本轮完成标准**

- 页面根级无横向滚动条，Dream 内容与编辑面板仍可用。
- 前端布局测试、类型/构建通过。
- 完整真实有头旅程明确 1 passed 退出。

**本轮实际结果和未验证推断**

- 共享 Story Workspace 主内容已改为 `overflow-x: hidden; overflow-y: auto`，静态布局与共享 Chat 恢复测试 24 passed。
- 对真实 Run 页的独立 Chromium 测量为 `documentElement/body scrollWidth = clientWidth = 1200`，无越界元素；窗口适配修复成立。
- 完整脚本仍停在已发生的 SPA 返回动作：URL 与页面已切回 Dream，但 `page.goBack()` 等待不存在的新文档 commit。进入第 89 轮修正同文档历史等待。

## 第 89 轮——SPA 同文档返回语义等待

**当前轮次目标**

让真实 E2E 按 SPA 实际行为完成 Dream→Chat→Dream 返回，不等待不存在的 document commit。

**优化后的执行提示词**

> Dream 与 Chat 是同一前端应用中的客户端路由。返回时在页面上下文触发标准 `window.history.back()`，随后以目标 Dream Run URL、页面无横向溢出和“确认并继续”可用为唯一完成条件；不要让 Playwright `page.goBack()` 等待新文档 commit，也不使用固定 sleep 或直接跳转 URL。先用现有真实 Run 做无模型导航验证，再执行最终完整真实有头旅程。

**可选增强项**

- 将同文档返回封装为小型测试 helper，明确 30 秒 URL 上限。

**本轮检查或修改范围**

- `frontend/e2e/dream-launch-real-model.spec.ts` 的 SPA 返回动作。
- 不修改生产路由或业务实现。

**本轮完成标准**

- 现有真实 Run 的 Dream→Chat→history back 导航验证通过。
- 完整真实有头 E2E 以 1 passed 退出。

**本轮实际结果和未验证推断**

- 已将返回动作改为 `window.history.back()` 后等待精确 Dream URL。
- 使用现有真实 Run 逐步诊断发现脚本实际先停在侧栏“对话”的 `click()`：业务已完成 SPA 切页，但 Playwright 自动等待不存在的新文档导航，尚未执行显式 Chat URL 等待。

## 第 90 轮——SPA 侧栏点击导航收口

**当前轮次目标**

关闭“对话”真实按钮点击自带的 document navigation 等待，改由明确 Chat URL 语义等待接管，彻底消除 E2E 挂起。

**优化后的执行提示词**

> 继续点击用户可见、可交互的侧栏“对话”按钮，但为 Playwright click 设置 `noWaitAfter`，因为生产路由是 SPA 同文档切换；紧接着以精确 `/story-workspace/chat` URL 和 Chat 输入框可见作为完成条件。返回仍用浏览器 history，并等待精确 Dream Run URL、视窗适配与业务按钮。不使用直接 URL 跳转替代用户点击，不使用 sleep。先在现有真实 Run 上逐步通过，再运行最终完整有头 E2E。

**可选增强项**

- 给所有 SPA 切换动作设置显式 30 秒语义超时。

**本轮检查或修改范围**

- 真实 E2E 的“对话”按钮点击选项和导航验证。
- 不修改生产路由、页面或后端。

**本轮完成标准**

- 现有 Run 导航脚本输出完整 passed。
- 完整真实 E2E 输出 1 passed 并退出。

**本轮实际结果和未验证推断**

- 真实侧栏标签按当前语言为 `Chat`，标准 composer 是 Tiptap `role=textbox`、accessible name 为 `Chat input`，不是带 placeholder 的 textarea；E2E 已改为中英文可访问名称契约。
- 现有真实 Run 的 Dream→可见 Chat 按钮→同 thread composer→history back→Dream 页面、按钮与 1200px 窗口适配逐步验证通过。
- 最终完整真实 `deepseek-v4-pro` 有头旅程通过：`1 passed (1.2m)`，命令为 `--headed --workers=1`。

## 第 91 轮——最终证据与回归收口

**当前轮次目标**

在真实闭环通过后完成产物、Admin 请求、回归测试、构建和受保护入口检查，确认可交付且无残留测试进程。

**优化后的执行提示词**

> 读取第 90 轮内容无关验收回执，核对该 Run 的 canonical 文件、三个 stage、manifest 路径和摘要；在 Admin 真实 Gateway 账本中以账号、模型和时间范围确认本次请求可追踪，只报告请求 ID、状态、模型和耗时，不输出提示词、reasoning、Token、DSN 或 Secret。运行 Dream Hook/launch/context/service 聚焦后端测试、共享 Chat recovery 与 Story Workspace layout 测试、TypeScript、ESLint、生产构建、`git diff --check` 和受保护文件 diff。检查 Playwright/Chromium 测试进程与异步资源；保留用户原有服务和真实数据，不做清理性删除。

**可选增强项**

- 对 manifest 文件逐项重算 SHA-256，验证私有副本与 canonical 源一致。

**本轮检查或修改范围**

- 只读真实 Run/Admin 证据、当前工作树静态/测试验证及文档结果更新。
- 不再改变已通过的业务架构，除非回归暴露真实缺陷。

**本轮完成标准**

- 真实 Run 证据完整且 Admin 可追踪。
- 聚焦回归、类型、lint、build、diff check 全部通过或明确列出既存非本轮阻断。
- `agent_runner.py`、`thread_factory.py`、`routers/claude_agent.py` 未被本轮改动。
- 无残留 Playwright 测试浏览器；后端服务状态明确。

**本轮实际结果和未验证推断**

- 最终 Run `run_604125a31ad9478990622b675a996863` 的 canonical 五类文件、三个 stage、preview manifest 和两个私有 Project/Episode 副本均存在；源与副本 SHA-256 完全一致。
- Admin Gateway 账本能按真实账号和 `deepseek-v4-pro` 追踪本轮成功请求；最近两条为 `req_aaf1562063a54ab88fc9e5d6b8782c60`（53,294ms）和 `req_a8992e384f3d4249b5b61cc54a78b998`（5,618ms），均 settled/succeeded/HTTP 200。
- 后端聚焦回归 131 passed、2 skipped、59 subtests；共享 Chat/layout 24 passed；TypeScript 生产构建通过；ESLint 0 error、21 个既存 warning；`git diff --check`、py_compile 和受保护文件 diff 通过。
- 最终有头 E2E 测试进程已退出；一个由临时独立诊断脚本遗留的 headless Chromium 已终止。当前后端 8765、Vite 5173、Admin 3000 保持运行。

## 第 92 轮——当前业务文档去历史化

**当前轮次目标**

将 Dream Agent 设计入口收敛为已经实现并验证的最小业务，删除当前文档中的过期英文状态、旧 B01–B21 目录和未采用方案，保留 Git 可恢复的 Prompt 执行记录。

**优化后的执行提示词**

> 重写 `README.md`、`business-interaction-design.md`、`project-episode-artifact-contract.md` 和 `design-review.md` 的当前正文为中文最小设计。只描述：真实 Dream 发起、共享 thread/Claude session、主 Agent canonical 文件、成功后 Hook 自动同步、actor-scoped dream-files 页面显示、刷新与 Chat 切换、失败/取消不发布，以及 preview 与 Admin 权威 sealed Artifact 的明确区别。为每个当前业务交互提供 Mermaid 时序。删除当前入口里的命令 DAG、next action、checkpoint、B01–B21 全目录、旧轮次发布状态和英文 Pending 文案；历史依据保留在 Git 和 `prompt-rounds.md`，不能继续误导实现。

**可选增强项**

- 在 README 中列出本轮真实 Run 与测试数字，但不包含业务正文或密钥。

**本轮检查或修改范围**

- 仅四份当前设计入口文档；不改生产代码。

**本轮完成标准**

- 文档全部中文、当前状态为已实现/已验收。
- 当前业务范围、权威边界和时序与代码/真实证据一致。
- 无旧方案被描述为当前必须实现。

**本轮实际结果和未验证推断**

- `README.md`、全业务交互、Project/Episode 合同和设计审查已重写为中文当前态；当前入口不再携带旧 B01–B21 目录、英文 Pending 状态、命令 DAG、next action 或 checkpoint。
- 当前文档只保留已实现的最小闭环、逐业务时序、Admin sealed Artifact 权威边界和真实验收证据；历史执行过程仅保留在本文件和 Git 中。

## 第 93 轮——验收改动原子提交

**当前轮次目标**

将已经完成真实业务验证的 Dream 工作台最小闭环，以一个可审计的原子 Git commit 纳入版本历史。

**优化后的执行提示词**

> 复核当前工作树，只提交与 Dream 主 Agent 生成 canonical 工作台文件、成功终态后服务端同步到 `.dream`、页面业务投影、共享 Chat SSE 稳定性、视窗适配、测试和中文设计文档直接相关的改动。提交前检查仓库协议、未跟踪文件、敏感信息、生成产物、受保护 Claude Agent 入口和 `git diff --check`；不得提交日志、环境变量、DSN、Secret、模型正文或 Playwright 产物，不得顺带修改其他用户改动。确认暂存内容后创建单一语义化 commit，并报告 commit ID。

**可选增强项**

- 在提交后重新读取 commit 文件清单和工作树状态，确认没有漏提交本闭环文件，也没有纳入运行产物。

**本轮检查或修改范围**

- 当前 Dream 工作台闭环的后端、前端、E2E、单元测试、目录说明和设计文档。
- Git 暂存区与提交历史；不修改生产业务逻辑。

**本轮完成标准**

- 敏感信息和生成产物扫描无异常。
- `git diff --check` 与受保护入口检查通过。
- 暂存内容与已验收范围一致。
- Git commit 成功，提交后工作树无本轮遗留改动。

**本轮实际结果和未验证推断**

- 提交前检查确认当前改动均属于已验收的最小闭环；未发现环境变量、凭证、业务正文或测试生成目录。
- 最终 commit ID 和提交后工作树状态在本轮 Git 操作完成后确认。

## 第 94 轮——确认后工作台生成与 Dream 消息原文可见

**当前轮次目标**

修复 Dream“确认并继续”后只输出文字、不生成 Episode 工作台产物且重复执行确认的问题；确认成功后进入并默认重返故事协作工作台。同时取消 Dream 业务消息正文的后端脱敏和前端过滤。

**优化后的执行提示词**

> 基于真实 Run `run_ba96a80d55a04d0f8a2799ecd8a824cf` 的 workflow、thread、确认消息和 canonical 文件证据，修复 Dream 确认提交、Agent 执行、成功 Hook、Episode 绑定、工作台路由之间的业务断点。确认前的成功主 turn 必须把 Run 推进到待确认；确认命令必须明确要求插件写入首集工作台 canonical 文件；确认 turn 成功后自动同步 `.dream`、建立权威 Episode 绑定并进入执行页。同一确认只能消费一次，失败可恢复但不得重复产生 Agent turn。Dream 的 launch、guidance、confirmation、episode action 和普通用户消息正文必须通过共享 Chat history/SSE 原文显示，不得在后端置空或在前端筛除；只保留元数据字段最小公开边界。不得修改 Claude SDK 入口、Claude session ID 语义或标准 SSE 报文，不得克隆真实数据。

**可选增强项**

- 对旧的 `running + 已持久化确认` 状态提供一次事实驱动的幂等修复，使已发生故障的真实 Run 能停止重复调度。

**本轮检查或修改范围**

- Dream workflow 生命周期、确认协调器、成功 turn Hook、Episode 绑定、确认指令、重入链接和执行页导航。
- Chat history 的 Dream 正文投影与前端消息消费过滤。
- 对应中文设计、后端/前端契约测试和真实浏览器业务验收。

**本轮完成标准**

- 确认后产生首集工作台文件和 Episode 绑定，执行页可读取并显示。
- 确认只触发一个 Agent turn，Run 生命周期可幂等恢复。
- Dream 用户消息和内部 JSON 控制正文在 Chat/Dream 两侧都可见。
- 身份、权限、thread/run 绑定与内部元数据边界未削弱。
- 聚焦测试、类型检查、构建及真实 UI 流程通过；未执行项明确记录。

**本轮实际结果和未验证推断**

- 实现和验证进行中。当前已确认：真实 Run 的确认消息处于 `dispatching`，workflow 仍为 `running`，ACK 前生命周期转换因此失败并重复调度；后端 `PublicChatMessageDto` 与前端 `filterStoryWorkspaceControlMessages` 同时隐藏了 Dream 业务正文。

## 第 95 轮——三条业务合同并行审查

**当前轮次目标**

按用户要求用并行对话分别审查确认调度、Episode 产物绑定、消息可见性与页面导航，再由主线完成无冲突集成。

**优化后的执行提示词**

> 将 Dream 确认后故障拆为三个独立合同并行处理：一，确认状态必须在 Agent 调度前依据已持久化、已授权、stage 完整的确认事实幂等收敛，不能在完成 ACK 时才发现非法状态并重复运行；二，成功确认 turn 必须写入首集 canonical 文件、由宿主 Hook 同步 `.dream` 并建立 EP01 权威绑定，执行页只读这些事实；三，Dream launch、guidance、confirmation、episode action、普通用户消息和内部 JSON 控制正文必须经共享 Chat history/SSE 原样展示，确认后进入且重返 execution route。每条对话只检查自己的文件和测试边界，禁止修改 Claude SDK 入口、thread/session 语义和标准报文；主线负责合并结论、冲突检查及真实业务验证。

**本轮检查或修改范围**

- 并行对话仅做指定边界的代码审查或测试补充；生产实现和最终集成由主线负责。

**本轮完成标准**

- 三条对话都有独立证据和结论，且不存在重复实现或互相冲突的状态源。
- 主线根据审查修正代码并统一运行聚焦与真实业务测试。

**本轮实际结果和未验证推断**

- 并行审查已启动，结果待合并。

## 第 96 轮——确认工作台与消息原文验证

**当前轮次目标**

验证并行审查修正后的确认调度、四文件后置条件、Episode binding、execution 导航和 Dream 正文可见合同，并完成本机真实业务验收。

**优化后的执行提示词**

> 先以聚焦后端合同证明 claim/lease/ACK 的并发所有权、确认前 lifecycle 收敛、确认 turn 四文件后置条件、EP01 authority/binding 和 Dream 正文原样投影；再执行前端消息/导航合同、TypeScript、ESLint、生产构建与 `git diff --check`。然后只重启本会话拥有的后端，使用本机真实账号、真实 Run、真实模型，从可见 UI 走完“确认并继续 → execution 页面 → EP01 四产物显示 → 用户/内部 JSON 消息可见”的正常人类路径。禁止克隆业务数据、影子账号、直接数据库造数、固定 sleep、停止用户服务或隐藏失败证据。

**本轮检查或修改范围**

- 当前未提交业务改动、相关后端/前端测试、真实本机服务和真实 Run。
- 不再扩大到无关 Story Workspace 功能或 Claude SDK 入口。

**本轮完成标准**

- 聚焦测试、类型、lint、build、diff check 通过。
- 真实 UI 中确认只运行一次，execution 能显示 EP01 产物，重入继续进入 execution。
- Dream/Chat 能看到用户消息与确认 JSON 正文，Admin 能追踪真实模型请求。
- 所有本轮自有异步任务/浏览器退出，用户服务和数据保持。

**本轮实际结果和未验证推断**

- 验证进行中。并行审查已促成 claim/lease/ACK CAS、lease 丢失取消 turn、服务端 project slug authority、四文件 postcondition 与确认后 Hook 失败传播等修正。

## 第 97 轮——产物构建术语修正

**当前轮次目标**

按用户要求区分“产物构建过程”和“安全信任边界”，删除用“可信”替代第一集产物构建/关联的业务文案。

**优化后的执行提示词**

> 扫描全部 Dream/Story Workspace 当前设计稿、页面文案、测试和插件说明。凡描述用户尚未完成的 Project/Episode 工作台、文件、产物绑定或页面准备过程，统一使用“尚未构建第一集产物关联”“第一集产物关联待构建”等业务表达，不得使用“可信/权威”代替“构建”。仅在 actor/thread/run 身份、server-derived provenance、权限、CAS 和安全校验的技术边界中保留“可信/权威”。同步更新 Mermaid、验收条件和 UI 断言，不改变 thread/session、SSE 或 Episode identity 安全实现。

**本轮检查或修改范围**

- `docs/design/dream-agent/**`、`docs/design/story-workspace/**`、Story Workspace 页面文案、对应测试和插件当前说明。
- 历史 Prompt 执行记录只保留原始证据，不回写已经发生的历史引用；当前业务结论必须采用新术语。

**本轮完成标准**

- 页面统一显示“尚未构建第一集产物关联”。
- 当前设计中构建过程使用“产物构建/产物关联”，安全术语只用于真实信任边界。
- 相关文案测试和 Markdown 引用检查通过后继续真实业务验证。

**本轮实际结果和未验证推断**

- 已扫描 `docs/design/dream-agent/**`、`docs/design/story-workspace/**`、相关前后端、插件文案和测试；执行页将未绑定状态改为“尚未构建第一集产物关联”，关联动作、等待和失败文案统一使用构建/同步/校验产物语义。
- 当前设计时序、Artifact 合同与插件说明已同步；`actor/thread/run/project` 服务端派生身份、来源证明、权限、CAS、manifest 提交标记和 Admin 跨系统合同仍保留“可信/权威”。
- 聚焦验证通过：执行页 Playwright `16 passed`；插件合同 `3 passed, 20 subtests passed`；两个前端文件 ESLint 通过；Markdown 清单/引用路径和 `git diff --check` 通过。
- 未运行真实模型或真实业务数据验收；本轮仅改文案、设计与对应静态/聚焦合同，不改变 thread/session、SSE 或 Episode identity 实现。

## 第 98 轮——旧确认恢复与真实业务续测

**当前轮次目标**

不中断原任务；修复旧版本已持久化确认仍携带过时指令、因而重复调用真实模型却不生成首集工作台的问题，并继续真实页面验收。

**优化后的执行提示词**

> 在不修改 Claude Agent 入口、thread/session 定义、Claude session ID 和标准报文的前提下，为已持久化的 Dream 确认提供原子、可见的当前合同升级：保留用户已确认且已指纹校验的 command，只更新服务器所有的 instructions，并在 Agent turn 开始前将更新后的完整 JSON 写回同一条 Chat 消息，保证页面所见与 Agent 输入一致。随后使用同一本机真实账号、真实数据和真实模型走完“确认并继续 → 写出 EP01 四项 canonical 文件 → 成功 Hook 同步 `.dream` → 构建第一集产物关联 → execution 页面显示”的正常人类路径。失败不得 ACK，不得隐藏消息，不得克隆业务数据。

**本轮检查或修改范围**

- Dream 确认 claim 的旧消息兼容、可见控制正文、对应聚焦测试。
- 当前任务拥有的 8765 后端、既有 5173/3000 用户服务、真实 Run 恢复及后续有头 E2E。
- 并行 Codex 新任务只负责术语/设计稿，不暂停当前业务实现。

**本轮完成标准**

- 旧确认在调度前升级为当前四文件输出合同，数据库可见正文与 Agent 输入完全一致。
- 同一确认不再使用旧指令反复产生无效真实模型调用。
- 真实执行页可读取 EP01 四项产物并显示；Chat/Dream 保留完整用户及内部 JSON 消息。
- 聚焦测试、静态检查、构建、真实有头单 worker E2E 均有明确结果。

**本轮实际结果和未验证推断**

- 已确认旧真实 Run 的失败不是 session 丢失，而是确认消息在新合同发布前已经持久化；恢复协调器忠实重放了旧正文，模型只回复文本，成功 Hook 因缺少 EP01 四项文件正确拒绝 ACK。兼容升级和续测进行中。

## 第 99 轮——全新 Run 真实有头验收

**当前轮次目标**

在旧 Run 已真实恢复后，再用全新 Run 验证普通用户从 Dream 发起到首集执行工作台的完整生产路径，排除仅靠历史数据修复成功的可能。

**优化后的执行提示词**

> 使用本机真实账号 `dmeck123@suoxya.com`、当前真实 Deck/model 配置和正常 PostgreSQL，从可见 Dream 页面发起一个全新创作任务。主 Agent 完成人物、场景和分镜后，通过页面“确认并继续”提交同一 thread 的可见 JSON 确认；等待 Agent 写出 `episode-outline.md`、`script.md`、`storyboard.yaml`、`review-report.md`，由成功 Hook 同步到 Run-private `.dream` 并构建 EP01 产物关联。页面必须进入 execution、显示 EP01，Dream Agent 面板必须保留确认 JSON 正文；回到 Dream 后该 Run 默认重入 execution。只批准可见且预期的 Write/Agent 工具；Agent 终止而产物不完整时立即失败，禁止固定 sleep、数据克隆或 API 替代关键交互。

**本轮检查或修改范围**

- `frontend/e2e/dream-launch-real-model.spec.ts` 对应的人类路径。
- 本任务拥有的 8765 后端、用户已有的 5173 与 3000 服务、本机真实数据和真实 Gateway 模型。
- 测试生成的真实 Run、Thread 和 Admin 日志按协议保留供用户复核。

**本轮完成标准**

- 有头 Chromium、`--workers=1` 完成完整 UI 路径。
- 新 Run 的三阶段草稿、四项 EP01 产物、`.dream` 同步、Episode 关联和默认重入均有可见/持久化证据。
- 页面无横向溢出、关键控件位于窗口内、无 Ink-Dream console/page/request 错误。
- 失败时保留真实 Run 回执和后台日志，不伪报成功。

**本轮实际结果和未验证推断**

- 真实有头验证开始；preflight 已确认仓库依赖和 5173/8765 监听正常。

## 第 100 轮——可见 Agent 面板后的确认续测

**当前轮次目标**

修正真实人类路径中 Agent 消息面板展开后遮蔽 Dream 内容操作的问题，再从页面完成确认与首集工作台生成。

**优化后的执行提示词**

> 保持 Dream Agent 完整消息可见合同。主 Agent 完成后，如果页面当前展开“Dream Agent 完整消息”，测试必须像正常用户一样点击“返回 Dream 内容”，再查找并点击“确认并继续”；禁止用强制点击、隐藏面板、DOM 注入或直接 API 提交替代。随后继续验证同一 thread 的确认 turn、四文件产出、`.dream` 同步、EP01 产物关联、execution 显示和默认重入。

**本轮检查或修改范围**

- 仅修正真实 E2E 的面板状态处理；不改变生产 UI 的消息可见性或 Agent lifecycle。
- 保留已生成的真实 Run 作为失败证据，并用修正后的完整可见路径再次验收。

**本轮完成标准**

- E2E 通过语义按钮返回内容，确认按钮真实可见、在窗口内且可操作。
- 不因消息面板展开而误判业务按钮缺失。
- 后续四文件与 execution 验收继续按第 99 轮标准执行。

**本轮实际结果和未验证推断**

- 首次全新 Run `run_ca43dc1cb9ff40e48e59d3f00f5f36c4` 已真实完成三阶段产物，Run 为 `pending_review`、revision 1、三阶段 item 数为 2/1/1。失败快照证明页面停在已展开的 Dream Agent 完整消息面板，因此“确认并继续”不在当前可见内容面板；模型、Hook 和三阶段产出没有失败。

## 第 101 轮——四产物可读性后置条件

**当前轮次目标**

修复 Hook 只按路径存在就构建 Episode 关联、却允许 execution 页面把其中产物判为 invalid 的合同缺口。

**优化后的执行提示词**

> Dream 确认 turn 的成功后置条件必须与 execution 页面读取合同一致，而不是只判断四个文件路径存在。Hook 在 Run-private `.dream` 发布和 Episode 关联之前，分别使用现有 Episode outline、script、storyboard、review 解析器验证四项 canonical 文件；任一产物 invalid 时，同一 turn 失败、不 ACK、不发布、不构建产物关联。确认 JSON 明确要求 storyboard 每个 shots 项使用唯一 `shot_id`，并使用现有 canonical 字段形状，禁止另建简化 schema 或让前端容忍错误文件。

**本轮检查或修改范围**

- 确认指令、Dream 成功 Hook、现有 Episode 解析器复用、对应后端测试和真实有头 E2E。
- 不修改 Claude Agent 入口、SSE、thread/session 或 execution 页面解析器。

**本轮完成标准**

- invalid storyboard 在发布/绑定前被 Hook 拒绝，确认保持可恢复。
- 四项均能被现有页面解析器读取后才允许 `.dream` 发布和 EP01 产物关联。
- 新确认正文能让模型生成含 `shot_id` 的 canonical storyboard。
- 聚焦测试与全新真实有头流程通过。

**本轮实际结果和未验证推断**

- 真实 Run `run_bdda2d39eec244ed955e88201f53d70b` 暴露根因：确认 turn 写出了四个路径并被旧 Hook 绑定，但 storyboard 使用 `shot/type/description/duration_sec`，缺少页面权威解析器要求的 `shot_id`，因此 API 显示 `storyboard.yaml=invalid`。修复与续测进行中。
- 确认指令已明确 `shot_id/shot_type/visual/camera.movement/timing.duration_sec` 合同；成功 Hook 在发布和绑定前复用现有 Episode outline、script、storyboard、review 解析器，invalid 文件会使 turn 失败且 publisher/binder 均不执行。
- 聚焦确认/Hook 验证通过：`57 passed, 2 skipped, 16 subtests passed`。第三次真实 Run `run_425f38e32e1649ccb206f0cc1b7ee076` 已生成包含 12 个唯一 `shot_id` 的 canonical storyboard，四项文件被发布到 Run-private `.dream` 且页面均显示为可阅读。

## 第 102 轮——执行页语义断言与故事索引验收

**当前轮次目标**

在四项真实 EP01 产物已经通过页面解析器并显示后，修正 E2E 对旧 `EP01` 文案的错误精确匹配，并把“Story Index 尚未建立”的可恢复合同与其他 HTTP 故障分开验收。

**优化后的执行提示词**

> 继续使用本机真实账号、真实数据、真实模型和可见浏览器完成 Dream 全链路。四项 Episode 产物均为 `available` 且绑定为 `bound` 后，按当前页面语义断言 `EP01 · Episode execution` 和四项可读入口；若 PostgreSQL Story Index 初始为 `missing`，像正常用户一样点击页面提供的“重试索引同步”，等待状态变为“已就绪”。诊断器可单独记录该契约允许的 Story Index `404 → 200` 过程，但不得忽略 Dream files、Episode artifacts 或其他 API 的 4xx/5xx。最后继续验证 Dream Agent 内可见确认 JSON、同一 thread 历史和默认重入 execution。

**本轮检查或修改范围**

- `frontend/e2e/dream-launch-real-model.spec.ts` 的页面语义断言、Story Index 状态记录和正常用户同步动作。
- 第三次全新真实 Run 的页面快照、Run-private 文件和 API 事实；不修改生产 Agent lifecycle。

**本轮完成标准**

- E2E 不再因已删除的独立 `EP01` 文案误报失败。
- Story Index 缺失状态有明确、可见、幂等的恢复动作，最终必须为 `200/已就绪`。
- 其他 API 错误仍使测试失败；四项产物、消息原文、同 thread 和默认重入继续完整验证。

**本轮实际结果和未验证推断**

- 第三次真实 Run `run_425f38e32e1649ccb206f0cc1b7ee076` 已达到 `bound`，四项 Episode 产物均为 `available`，页面可阅读分集大纲、剧本、分镜和审阅报告。
- 失败快照中的唯一业务断言失败是测试精确查找独立 `EP01`，而页面当前输出为 `EP01 · Episode execution`；Story Index 随后从 `404/missing` 经幂等同步变为 `200`。测试修正与最终续测进行中。

## 第 103 轮——隐藏手动关联入口后的最终集成验证

**当前轮次目标**

集成独立 Codex 对话完成的“隐藏手动构建第一集产物关联”改动，验证普通用户只需一次“确认并继续”即可自动生成、发布、绑定并进入可读 Episode 页面，然后完成最终真实有头验收。

**优化后的执行提示词**

> 审核共享工作树中的执行页改动：未关联时只读显示等待确认后的自动发布与绑定，execution 页面及 Dream Agent 操作区都不得暴露“构建第一集产物关联”按钮；不得删除后端成功 Hook、产物解析、Run-private `.dream` 发布或 `bind_first_episode`。依次运行聚焦前后端合同、TypeScript、目标 ESLint、生产构建、Python 编译、`git diff --check` 和受保护入口零差异检查。最后使用 `dmeck123@suoxya.com`、真实 Deck/model、本机真实 PostgreSQL 和可见 Chromium `--headed --workers=1`，从 Dream 发起全新任务，完成 Chat 往返、确认并继续、四项 EP01 文件、Story Index 同步、消息原文、同 thread 历史和默认 execution 重入；禁止克隆数据、固定 sleep、直接 API 替代关键点击或停止用户服务。

**本轮检查或修改范围**

- 当前全部 Dream 重构改动、按钮隐藏对话的前端/文档改动和真实 E2E。
- 受保护的 `agent_runner.py` 与 `thread_factory.py` 只做零差异检查；5173/3000 用户服务保持运行。

**本轮完成标准**

- 页面没有手动关联入口，自动链路仍能真实构建四项可读产物和 Episode 关联。
- 后端聚焦、前端合同、类型、lint、build、diff check 均通过。
- 最终真实有头单 worker 流程通过；失败则保留 Run/thread 回执并继续按事实修复，不伪报成功。

**本轮实际结果和未验证推断**

- 独立 Codex 对话 `019ffa6d-ffe7-7e43-b8e3-ff4e9f98e83b` 已移除 execution 未关联页和 Dream Agent 操作区的手动构建入口；聚焦源级合同 `16 passed`、mocked Chromium `2 passed`、TypeScript、目标 ESLint、Markdown 链接和 `git diff --check` 均通过。
- 主线最终集成和全新真实有头验收进行中。

## 第 104 轮——真实轮询瞬时连接恢复

**当前轮次目标**

修正真实 E2E 在后端仍健康且相邻请求持续为 200 时，因单次 `ECONNRESET` 立即终止整个长时确认流程的问题；保持业务失败快速暴露。

**优化后的执行提示词**

> 保留真实浏览器、真实账号、真实模型和真实数据路径。Episode 产物的 `expect.poll` 读取允许有限、连续的瞬时网络失败：读取成功即清零计数，连续达到 5 次才抛出原始错误；Run 进入失败/取消、主 Agent 已停止但四项产物不完整、API 返回非 200 合同错误等业务失败仍立即失败。禁止固定 sleep、无限重试、隐藏业务错误或重启/克隆数据替代恢复。先检查已接受 Run 的同一 confirmation turn 是否继续完成，再重跑完整有头流程。

**本轮检查或修改范围**

- `frontend/e2e/dream-launch-real-model.spec.ts` 的 Episode 产物轮询错误边界。
- 真实 Run `run_bfcb11a1062d453095d57229d172c0c0` 的后台完成、四项文件和绑定事实。

**本轮完成标准**

- 单次连接重置不再中止长时真实流程，连续故障仍在有界次数后失败。
- 业务终态和产物不完整仍快速、明确失败。
- 同一真实 Run 不因浏览器测试退出而重复调度；最终有头完整路径通过。

**本轮实际结果和未验证推断**

- 8765 PID 77836 在失败前后保持监听，日志显示同一 Run 的 `episode-artifacts` 在一次客户端 `ECONNRESET` 前后持续返回 200；确认 turn 由服务端协调器继续拥有。修正与续测进行中。

## 第 105 轮——确认指令去歧义与首动作写入

**当前轮次目标**

修复确认指令同时要求“更新 stage revision”和“宿主自动同步”导致模型过度规划、误把可选 Dream MCP 当成前置步骤并在 Write 前耗尽输出的问题。

**优化后的执行提示词**

> Dream confirmation 的可见 JSON 必须给出单一、强顺序完成合同：第一动作必须是内建 Write/Edit；不在工具前解释或规划；若 command.edits 非空，只把它们写回本 session 已知的 canonical 文件；随后在当前已存在的 canonical Project/EP01 路径创建或覆盖 `episode-outline.md`、`script.md`、`storyboard.yaml`、`review-report.md`。禁止调用 Dream MCP、Agent、Read、Grep、Glob、Bash、Web 和 AskUserQuestion，禁止研究 schema/插件，禁止写 `.dream`。storyboard 每个 shot 使用唯一 `shot_id` 和最小 `shot_type/visual/camera.movement/timing.duration_sec` 形状。四次写入成功后只回复一句完成并结束。stage revision、解析、发布和绑定全部由宿主成功 Hook 负责。

**本轮检查或修改范围**

- Dream confirmation 可见指令构建、旧确认 claim 升级、对应单测和插件中文执行规则。
- 不改变 command 指纹、用户确认内容、Claude session ID、共享 SSE 或 Hook 的四产物后置条件。

**本轮完成标准**

- 指令中不再出现“Agent 更新 Dream stage revision”或把 MCP 作为正常完成步骤。
- 模型第一动作明确为 Write/Edit，四项路径和最小 storyboard 合同无歧义。
- 旧持久化确认在下一次 claim 时原子升级；同一用户 command/fingerprint 不变。
- 聚焦测试和真实恢复验证通过。

**本轮实际结果和未验证推断**

- 真实 Run `run_3e9ef2688feb4feca8fbca074b92e3a3` 的确认 turn 正确 resume 同一 Claude session，但模型生成约 35,000 字符 planning，反复讨论 Dream MCP、stage revision 和 schema，在任何工具调用前以 partial 结束；Hook 正确拒绝发布/绑定/ACK。指令收敛与恢复验证进行中。

## 第 106 轮——分镜标识类型合同与失败产物覆盖

**当前轮次目标**

修复真实确认重试已写出四个文件、但 `storyboard.yaml` 把 `shot_id` 写成 YAML 数字，导致权威 Episode 解析器拒绝发布和绑定的问题。

**优化后的执行提示词**

> 保持同一 Run、thread、Claude session 和 confirmation command，不手工修改真实数据。确认指令必须明确：即使失败尝试留下旧文件，也要覆盖 `storyboard.yaml`；每个 `shot_id` 必须是带引号的非空 ASCII 字符串，例如 `"shot-001"`，数字 `shot_id: 1` 无效；值必须唯一并匹配 `^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$`。给出可直接照写的最小 shot 形状 `{shot_id: "shot-001", shot_type: "wide", visual: "...", camera: {movement: "static"}, timing: {duration_sec: 6}}`。由 Agent 使用 Write/Edit 覆盖 canonical 文件，宿主继续负责解析、发布、绑定和 ACK。

**本轮检查或修改范围**

- Dream confirmation 可见指令、旧确认 claim 指令升级、对应单测和 Dream 插件执行规则。
- 真实 Run `run_3e9ef2688feb4feca8fbca074b92e3a3` 的同 session 恢复验证。
- 不放宽 Episode 解析器，不修改真实文件、不改变 Claude session ID、thread 或 command 指纹。

**本轮完成标准**

- 指令明确区分字符串 `shot_id` 与无效数字值，并要求覆盖失败遗留文件。
- 聚焦测试通过；重启本任务后端后，持久化确认使用新指令恢复。
- Agent 自行写出可被现有解析器读取的四项产物，Hook 才发布 `.dream`、绑定 EP01 并 ACK 一次。

**本轮实际结果和未验证推断**

- 代码检查确认 `_required_identity_text` 只接受 ASCII `str`；修复前真实 `storyboard.yaml` 的 `shot_id: 1..12` 被 YAML 解析为整数，因此确定触发 `invalid_shot_id`。
- 聚焦确认、Hook 和插件合同测试通过：`60 passed, 2 skipped, 36 subtests passed`；TypeScript 和 `git diff --check` 通过。
- 重启本任务持有的 8765 后端后，同一 confirmation message 原子升级为新指令并继续 resume 同一 Claude session。Agent 自行把 12 个 `shot_id` 覆盖为带引号的 `shot-001..shot-012`；确认最终只 ACK 为 `dispatched`。
- Run-private `.dream` 已包含 `dream-episode/v1` 绑定、五文件 manifest、四项 EP01 产物；canonical 与 private 副本均通过现有 outline/script/storyboard/review 解析器，分镜为 12 个唯一标识。未手工修改真实产物。

## 第 107 轮——隐藏手动入口后的最终真实有头验收

**当前轮次目标**

以全新真实 Run 验证当前最终代码：用户不再看到手动“构建第一集产物关联”，一次“确认并继续”即可由 Agent 构建四项产物并由宿主自动发布、绑定和打开 execution。

**优化后的执行提示词**

> 使用本机真实账号 `dmeck123@suoxya.com`、本机真实 PostgreSQL、Admin 当前真实 Deck/model 配置和真实模型，从 `http://127.0.0.1:5173/story-workspace/dream` 运行可见 Chromium `--headed --workers=1`。像正常用户一样填写创作目标、发起 Dream、观察 Agent 输出、在 Dream 与 Chat 间切换、返回 Dream 内容并点击一次“确认并继续”。页面不得出现手动“构建第一集产物关联”；Agent 必须在同一 thread/session 写出四项 canonical EP01 文件，宿主校验后自动同步 Run-private `.dream`、绑定 EP01、显示四项可读产物和 Story Index，并默认重入 execution。保留用户消息和内部 JSON 正文；禁止克隆数据、固定 sleep、API 替代关键 UI 操作或停止 5173/3000 用户服务。

**本轮检查或修改范围**

- `frontend/e2e/dream-launch-real-model.spec.ts` 与当前真实 5173/8765/3000 服务。
- 当前全部 Dream 重构改动的最终用户路径；不再改动受保护 Agent 入口。

**本轮完成标准**

- 新 Run 完成三阶段草稿、一次确认、四项可读 Episode 产物、`.dream` 发布和 EP01 自动绑定。
- Dream↔Chat 使用同一 thread，确认 JSON 和用户消息可见，返回 Dream 默认进入 execution。
- 可见窗口无横向溢出；无非预期 console/page/request 错误；不存在手动关联按钮。
- 有头单 worker E2E 通过并留下不含正文的真实 Run 回执。

**本轮实际结果和未验证推断**

- 最终真实有头验证开始；旧 Run 恢复已证明新字符串 `shot_id` 合同和自动绑定 Hook 可执行，但尚需用全新 Run 排除只依赖重试历史的可能。

## 第 108 轮——Story Index 可见恢复动作

**当前轮次目标**

在全新 Run 的四项产物和自动绑定已经完成后，使真实 E2E 按页面现有状态机处理 Story Index 的短暂读取失败，不把成功的 Agent 业务误报为失败。

**优化后的执行提示词**

> 保持真实 Run 和生产页面行为。点击一次“重试索引同步”后，如果状态区域短暂显示“故事索引状态暂时无法读取”并提供“重新检查”，测试必须像正常用户一样点击可见且可用的“重新检查”；如果随后仍显示可重试的“未建立/版本过期”，可再次点击“重试索引同步”。最多执行 3 次可见恢复动作，并在 60 秒内等待 `data-index-status=indexed` 与“PostgreSQL 索引 已就绪”。不得固定 sleep、直接调用 reconcile API、无限重试或忽略其他 HTTP 错误。

**本轮检查或修改范围**

- 仅 `frontend/e2e/dream-launch-real-model.spec.ts` 的 Story Index 后置验收。
- 全新真实 Run `run_2cb9ffabc5114e86b993aa002c9bf3fc` 的已有产物、自动绑定和 Story Index 后端事实。

**本轮完成标准**

- 页面提供的“重试索引同步/重新检查”是唯一恢复入口，每次动作均可见、可用且位于窗口内。
- 后端最终 200 后页面进入 `indexed/已就绪`；超过 3 次或 60 秒仍未成功则保留失败。
- 随后继续验证消息原文、同 thread、默认 execution 重入和手动关联按钮不存在。

**本轮实际结果和未验证推断**

- 第 107 轮新 Run 已完成四项产物与自动绑定；首次 E2E 仅在 Story Index 后置断言超时。后台日志显示状态从 404 变为 200，而页面曾从 `missing` 短暂进入带“重新检查”的 error 状态；修正和重入验收进行中。

## 第 109 轮——预期 Story Index 404 的控制台归因

**当前轮次目标**

避免浏览器对允许的 Story Index `404/missing` 同时输出无 URL 的通用 console error，导致网络诊断已正确分类后又被重复判失败。

**优化后的执行提示词**

> 网络 response 仍是 HTTP 事实来源：只有 `GET .../story-index` 的 404 可作为未建立状态继续，其余 API 4xx/5xx 必须失败；Story Index 最终必须出现 200。把 Chromium 的通用 `Failed to load resource ... 404` 单独计数，最终数量不得超过 response 诊断实际记录的 Story Index 404 数量；其他 console error、pageerror 和 requestfailed 均保留为失败。不得按字符串无条件忽略所有 404。

**本轮检查或修改范围**

- 仅真实 E2E 的诊断归因和最终断言。
- 全新真实 Run `run_3a4a92661112424c8840a14383fa000d` 的已完成 Agent 产物、自动绑定、Story Index reconcile 与默认重入事实。

**本轮完成标准**

- 无 URL console 404 必须由相同数量的 Story Index response 404 覆盖；超出即失败。
- Story Index 200、所有 Dream files 200、其他诊断错误为空。
- 修正后最终有头单 worker 路径通过。

**本轮实际结果和未验证推断**

- 第 108 轮全新 Run 已完成业务路径和可见 Story Index 恢复，后台 `GET story-index 404 → 200`、`POST reconcile 200`；E2E 最后仅因两条预期 404 的重复 console 记录失败。归因修正与最终复测进行中。

## 第 110 轮——真实项目身份隔离

**当前轮次目标**

修正真实 E2E 反复使用完全相同项目名称造成的 PostgreSQL Story Index 身份冲突，使每次验收创建一个正常、可区分的真实项目，而不是复用同一 `project_id` 覆盖旧项目事实。

**优化后的执行提示词**

> 每次真实有头验收在用户可见的创作目标中使用一个人类可读、带北京时间的独立项目名，例如《雨夜末班车·2026-08-13-18-12-30》；其余人物关系、场景和结尾目标保持一致。由真实 Agent 按正常初始化规则生成新 canonical Project identity，禁止克隆现有数据、直接改数据库、手工改 `project.yaml` 或在服务端注入测试 ID。Story Index 仍必须经页面可见动作建立并达到 `indexed`。

**本轮检查或修改范围**

- 仅真实 E2E 填写的可见项目名称及最终验收。
- 已失败 Run `run_d67dc6eee51a47b89889d268729e05be` 保留为冲突证据，不做数据修补。

**本轮完成标准**

- 新 Run 的 Agent 创建与历史 Run 不同的 Project identity。
- 四项 EP01 产物、自动绑定、Story Index、消息可见性、同 thread 和默认重入全部通过。
- 不使用克隆数据或测试专用后端分支。

**本轮实际结果和未验证推断**

- 真实 200 响应证明第 109 轮页面没有进入 indexed 的原因是 `status=failed,errorCode=story_index_conflict,retryable=false`；observed revisions 与同一 `proj-575fa8bd` 的历史 indexed revisions 不一致。根因是多轮 E2E 都提交完全相同的项目名，使 Agent 按确定性 fallback 复用了相同 `project_id`，不是前端 reducer 丢状态。独立项目名修正与最终复测进行中。

## 第 111 轮——自动绑定后的页面轮询等待

**当前轮次目标**

使真实 E2E 在服务端 Episode 已 bound 后，等待生产 hook 既有的 5 秒 ETag 轮询把 execution 未关联占位替换为已关联工作台，而不是用默认 5 秒断言与同一轮询临界竞争。

**优化后的执行提示词**

> 服务端 `episode-artifacts` 返回 `bound` 且四项产物 `available` 后，不直接刷新页面、不调用隐藏命令，也不添加固定 sleep。使用语义 locator 等待 `EP01 · Episode execution` 最多 30 秒，让生产 `useStoryWorkspaceEpisodeArtifacts` 的现有 5 秒 ETag polling 自行获取新 revision 并更新页面。若 30 秒仍显示“尚未构建第一集产物关联”，保留失败，视为真实自动刷新缺陷。

**本轮检查或修改范围**

- 仅真实 E2E 中服务端完成事实到页面可见事实的等待上限。
- 新 Run `run_2ff110bde1a446ff89c68704ef4017a9` 的自动绑定与页面轮询证据。

**本轮完成标准**

- 不借助手工关联、reload 或 API mutation，页面在生产轮询周期内出现 EP01 execution。
- 随后完成 Story Index、消息正文、同 thread 和默认重入验收。
- TypeScript、ESLint、diff check 与最终有头流程通过。

**本轮实际结果和未验证推断**

- 第 110 轮独立项目 Run 已由 API 证明 bound 且四项 available；失败快照恰在服务端完成后的默认 5 秒 UI 断言处仍显示自动绑定等待占位。hook 最小轮询为 5 秒，后台随后返回新的 Episode 200，因此当前证据指向测试与轮询临界竞态；扩大语义等待后复测。

## 第 112 轮——最终回归与资源清理

**当前轮次目标**

在真实有头完整路径通过后，对当前 Dream 重构工作树运行最终聚焦回归、静态检查、构建、受保护入口检查和异步资源审计，并记录仍未验证的边界。

**优化后的执行提示词**

> 对当前所有 Dream 相关改动运行：修改过的后端测试集合、前端源级合同与 mocked Chromium、TypeScript、目标 ESLint、生产 build、Python compile、`git diff --check`、旧手动关联入口生产扫描、旧不当用词扫描和 `agent_runner.py/thread_factory.py` 工作树零差异检查。确认最终真实有头回执 `run_1ad5696aba324f8886f7074790d4bbdf` 为同一 thread、恰好一条 dispatched confirmation、四项 canonical/private 产物可解析、Episode 已 bound、Story Index indexed。清理 Playwright 进程；保留本任务 8765 后端供用户复测，不停止用户的 5173/3000。任何未通过项必须如实记录，不提交代码。

**本轮检查或修改范围**

- 当前 Dream 重构涉及的后端、前端、插件和 `docs/design/dream-agent`。
- 测试生成的真实 Run 只读核验，不删除或克隆。

**本轮完成标准**

- 聚焦回归、类型、lint、build、compile 和 diff check 全部通过。
- 最终真实 Run 的持久化事实与 `1 passed (2.1m)` 一致。
- 无残留 Playwright 进程；用户服务保持运行；无受保护入口工作树改动。

**本轮实际结果和未验证推断**

- 最终有头 Chromium `--workers=1` 已通过：`1 passed (2.1m)`；Run `run_1ad5696aba324f8886f7074790d4bbdf`。
- 后端聚焦回归通过：`270 passed, 2 skipped, 63 subtests passed`。测试进程退出时 psycopg pool 打印延迟关闭警告，但进程已经结束且没有残留测试 Python 进程；本任务 8765 服务保持运行。
- 前端源级合同通过 `45 passed`；两项 mocked Chromium 在正确的 `INK_E2E_WEB_BASE=http://127.0.0.1:5173` 下通过 `2 passed`。第一次误用 Node 原生 runner、以及第一次漏写该环境变量导致的失败均属于命令配置错误，未计为代码通过证据。
- TypeScript、目标 ESLint、生产 build、Python compile、`git diff --check` 均通过；build 仅保留既有大 chunk 和 ineffective dynamic import 警告。
- `agent_runner.py` 与 `thread_factory.py` 工作树零差异；生产源码不存在手动“构建第一集产物关联”按钮；Dream/story-workspace 设计文档不再使用“可信的第一集关联”措辞。
- 最终真实持久化核验：Run `confirmed`、error null、同一 source thread、有 Claude session、恰好一条 confirmation 且 `dispatched`；`.dream` 为 `dream-episode/v1` revision 1、manifest 5 文件，四项 Episode 产物均通过权威解析器，10 个分镜 ID 全部唯一；Story Index HTTP 200、status `indexed`、error null、episodeCount 1。
- 5173、3000 和本任务 8765 均继续监听；没有残留本轮 Playwright spec 进程。系统已有多个 Codex Playwright MCP 常驻进程，未归属本轮且未停止。

## 第 113 轮——恢复多 Episode 推荐按钮状态机

**当前轮次目标**

继续历史任务 `019fd74e-e06f-7073-a714-fe86cdada2ce`，在当前 Dream 单一 thread runtime 和自动产物发布重构之上，完成多 Episode 推荐按钮状态机从服务端事实到 Dream/Execution UI、确认、派发和刷新恢复的全链路实现。

**优化后的执行提示词**

> 在当前 `platform` 分支上恢复并完成历史任务的多 Episode 工作流能力。以服务端 Episode registry、artifact manifest 与 workflow facts 为唯一业务真相，完整实现 EP01→EP02→EP03 的推荐按钮状态机：每阶段仅一个 recommended action，其余动作明确为可执行返工或不可执行预览；所有 label、canonical input revision、idempotency、确认、刷新恢复均绑定正确 EP，前端不得推导命令或工作流状态。先对照旧提交 `489af74` 与当前重构差异，再更新中文设计时序图、补齐生产代码和契约测试，最后通过聚焦后端、前端 seam、TypeScript、ESLint 与浏览器验证。不得回退 ClaudeAgentService、thread/session 和 Dream 自动发布链路。

**本轮检查或修改范围**

- 历史任务与提交 `489af74` 的 Episode action projection、确认和 UI 合同。
- 当前 `backend/services/story_workspace`、Dream/Execution 页面、相关 API、测试和中文业务设计。
- 不修改 Claude SDK 入口、`thread_factory.py`、Claude session ID 定义或现有 EP01 自动发布/绑定 owner。

**本轮完成标准**

- EP01、EP02、EP03 均由服务端绑定生成不同且正确的动作 identity、label 和 canonical inputs。
- 每阶段只有一个推荐动作；返工动作、未来预览和不可执行原因不会混淆。
- 当前 Dream/Execution UI 可以展示、确认、派发并在刷新或重新进入后恢复这些动作。
- 中文设计包含状态机、业务时序和 truth ownership；聚焦后端/前端测试、TypeScript、ESLint 与浏览器验证通过。

**本轮实际结果和未验证推断**

- 历史任务读取确认旧提交 `489af74` 已实现一版阶段矩阵、每动作独立 revision 与 action ID intent，且该提交仍位于当前分支历史中。
- 当前代码尚有两个已确认缺口：Artifact GET 始终读取 launch metadata 中固定的 EP01 authority；下一 Episode 的完成 MCP 也要求 episode UID 等于 EP01 source authority，因此 EP02 虽能创建 binding 和派发，却无法成为 active Episode 或完成闭环。

## 第 114 轮——删除推荐状态机，收束为已安装 Skill 与成功 Hook

**当前轮次目标**

撤销第 113 轮的多 Episode 推荐按钮方向。除首次 `/drama-init` 外，十三个业务 Skill
允许用户在同一 Chat thread 中随机、重复执行；页面输入 `/` 时只推荐当前 Deck/thread
实际安装的 Skill。删除 next action、completion fact、action projection、专用确认/恢复
API 和前端阶段按钮。主 Agent before/after Hook 负责成功 turn 后确定性扫描 canonical
工作台、发布 `.dream` 和幂等构建已有 Episode 产物关联；Observer 与 MCP 都不是同步 owner。

**优化后的执行提示词**

> 在不修改 Claude runner、标准报文、thread/session/claude_session_id 的前提下，把
> Dream/Story Workspace 从代码级 Episode 状态机收束为“真实安装 Skill 的 Slash 建议 +
> 主 Agent 成功边界 Hook 自动同步”。完整移除推荐按钮、next-action/completion-fact DTO、
> action/recovery POST、内部派发器、专用 reducer 和冲突设计；保留首次 init、权限、
> Project/Episode Artifact 合同、原子发布、同 thread Chat、Stop/确认/历史恢复。Slash 选择
> 只插入普通文本。Hook 失败沿同一 Chat turn 唯一失败路径返回，Observer 仅作非控制型
> 投影。用聚焦后端、前端契约、类型、lint、构建和真实本机 Chromium 验证。

**本轮检查或修改范围**

- `backend/services/story_workspace`、Story Workspace router/contracts/MCP、
  `ClaudeAgentService` 的既有 Hook 调用点；
- Chat composer、Dream/Execution 页面、Episode artifact GET/parser/reducer；
- `docs/design/dream-agent` 和 `docs/design/story-workspace` 当前业务文档与测试。

**本轮完成标准**

- 生产代码不再提供 Episode action/recovery API、action DTO、状态机或推荐控件；
- Slash 建议来自 enabled/ready/digest 匹配及 thread 冻结加载事实；
- Hook 在任意成功 Dream 根 turn 后发布当前快照，MCP 未调用也成立；
- GET 保持只读，Observer 不控制同步，权限和原子性不削弱；
- 中文业务时序、设计审查、聚焦测试、类型、lint、构建和真实页面验证通过。

**本轮实际结果和未验证推断**

- 第 113 轮方向已明确被当前业务要求取代；旧 action/recovery 生产模块、API、前端控件、
  reducer 和专用测试已删除；MCP 不再推进 Workflow，未使用的 Episode 完成方法已删除。
- 首次 `/drama-init` 的三页面产物 readiness 仍由成功后 Hook 负责，以保留“确认并继续”；
  它不用于后续十三 Skill 的推荐、禁用、排序或完成判断。
- 后端全量：`1772 passed, 21 skipped, 584 subtests`；退出码 0。测试进程退出时仍有既有
  psycopg pool worker 关闭超时提示，未发现残留 pytest 进程。
- 前端全量：`298 passed`；TypeScript 与 production build 通过；ESLint 为 0 error、
  21 个既有 Hook dependency warning；`git diff --check` 通过。
- 真实有头 Chromium 使用账号 `dmeck123@suoxya.com`、Run
  `run_21d5990b83ea49f984e56ff068228188` 和本机冻结 receipt：完整展示 13 个 Drama Skill
  加 1 个实际安装平台 Skill，Slash 选择不发送、无推荐按钮、1280×800 无横向溢出。
- 同一真实 thread 发送只读 `/drama-query` 后成功恢复原 Claude session；持久化 assistant
  模型为 `gateway/deepseek-v4-pro`、正文 5818 字符；Artifact manifest revision 与 5 个
  文件保持不变。Playwright 最终回执为 `passed`，worker 已退出。

## 第 115 轮——Skill 重初始化后的文件事实对账与连续编辑上下文

**当前轮次目标**

修复两个真实缺口：`/drama-init` 删除 launch seed 后旧 stage 仍可能留在 `.dream` 页面；
同一 Dream thread 的后续自然语言“修改标题”缺少稳定的工作台定位，模型可能只返回故事
JSON 而不编辑 `project.yaml`。

**优化后的执行提示词**

> 以“Skill 任意执行、Hook 根据文件事实同步、Observer 只做非控制型投影”为前提，
> 在 `ClaudeAgentService.assemble_context` 既有生命周期内部署 Agent 只读的
> `.dream/WORKBENCH.md`，并为每个 Dream turn 注入服务端解析的 run/thread/唯一 Project
> 文件上下文。Hook 对人物、场景和分镜执行完整集合对账：源集合为空时删除旧 stage，
> 新源出现时重建；项目属性修改后覆盖私有 Project 副本并提交新 manifest。不得增加
> 命令顺序状态机、Observer 控制、Dream SSE、新 DTO 或新的 Agent 执行入口。

**本轮检查或修改范围**

- `ClaudeAgentService.assemble_context`、`ClaudeAgentContextBuilder`；
- `DreamArtifactTurnHook` 与安全 Dream stage writer/reader；
- `backend/story_workspace/dream_workbench_context.py`；
- 工作台同步中文设计、聚焦后端合同测试和真实模型 Dream 页面旅程。

**本轮完成标准**

- 删除某类全部 canonical 源文件后旧 stage 消失，新文件出现后只显示新事实；
- 每个 Dream turn 均能读取 WORKBENCH 合同并获知当前 run/thread/project；
- “修改标题”为文件编辑，`project.yaml.project_name` 与 `.dream` 私有副本一致；
- 不改变公开 Chat 报文、Claude session ID、runner 入口和 Observer 边界；
- 聚焦测试、构建、静态检查和本机真实模型自动化验收通过。

**本轮实际结果和未验证推断**

- 真实 run `run_8956be79389b4bd3aa40b5107a5bb233` 证明 canonical 文件与旧 stage
  均存在，历史“修改标题”消息随后得到脱离文件的结构化故事 JSON；根因合同已定位。
- 已新增服务端维护的 `.dream/WORKBENCH.md` 和每 turn 动态上下文；未修改公开 Chat
  报文、Claude session ID、runner 入口或 Observer。Hook 已按当前完整源集合删除旧 stage，
  并可在新源出现时重建页面投影。
- 后端全量为 `1775 passed, 21 skipped, 584 subtests`；聚焦合同测试为
  `135 passed, 52 subtests`。TypeScript、production build、目标 E2E ESLint、
  `git diff --check` 均通过。
- 真实有头 Chromium 使用本机账号 `dmeck123@suoxya.com`、原始 Run
  `run_8956be79389b4bd3aa40b5107a5bb233` 和真实 `deepseek-v4-pro`：自然语言标题修改
  已实际写入 canonical `project.yaml`，Hook 同步后的私有副本和 manifest SHA 一致，
  页面无横向溢出，Playwright `--headed --workers=1` 为 `1 passed`。
- 仍需产品层面继续观察开放式创作指令的模型质量；文件同步与连续编辑合同本轮已有自动化
  和真实模型证据，不再作为未验证推断。

## 第 116 轮——初始化部署与逐轮实际路径读取

**当前轮次目标**

纠正第 115 轮只在 `assemble_context` 生成文件、只注入相对路径的不足：Dream surface 初始化
时即部署 Agent 工作台合同；每个 Dream turn 刷新动态事实后，将服务端校验的实际文件路径
注入消息并要求 Agent 本轮先读取。

**优化后的执行提示词**

> 审计当前未提交实现和真实调用链，区分 Dream workspace 首次初始化与每个用户 turn 的
> context assembly。把稳定合同移到 `backend/story_workspace` 下的 Markdown 源文件，首次
> Dream surface 原子部署 `.dream/WORKBENCH.md`；`ClaudeAgentService.assemble_context`
> 每轮验证/刷新 run、thread、workspace、Project、Episode 事实，并在不修改公开 DTO、runner、
> session 或 Observer 的前提下，向同一 Agent message 注入同步后文件的实际路径，明确要求
> 先 Read 再处理用户请求。以合同测试、全量检查和真实模型持久化 tool parts 证明行为。

**本轮检查或修改范围**

- `backend/story_workspace` 的静态 Agent 合同和安全刷新类；
- Dream surface 的 workspace 初始化；
- `ClaudeAgentService.assemble_context` 与内部 context builder；
- 中文交互设计、时序、审查、合同测试和真实模型 E2E。

**本轮完成标准**

- 新 workspace 初始化即存在静态 WORKBENCH；
- 每个 Dream turn 的文件和注入内容都含服务端可信实际路径及动态事实；
- 真实模型持久化 parts 证明读取 WORKBENCH 后再操作 canonical 工作台；
- 普通 Chat、Claude session、runner、公开报文、Hook/Observer 边界保持不变；
- 聚焦测试、全量合理检查、构建和真实本机有头 Playwright 通过。

**本轮实际结果和未验证推断**

- 设计审计已证明旧实现未在 Dream surface 初始化时部署 WORKBENCH，且每轮指令只包含相对
  路径；设计已修改后接受。
- 静态合同已迁移到 `backend/story_workspace/dream_workbench_context.md`；新 Dream surface
  初始化原子部署该文件，已有 surface 缺失时只补文件而保留 runtime。每个 Dream turn 刷新
  run/thread/workspace/project/Episode 事实，并注入绝对、经校验的路径要求 Agent 先 Read。
- 合同测试为 `110 passed, 13 subtests`；后端项目全量为
  `1778 passed, 21 skipped, 584 subtests`。Python 编译、目标 ESLint、TypeScript、production
  build 和 `git diff --check` 通过。
- 真实有头 Chromium 使用账号 `dmeck123@suoxya.com`、原始 Run
  `run_8956be79389b4bd3aa40b5107a5bb233` 与真实 `deepseek-v4-pro`，结果 `1 passed (39.3s)`。
  assistant `fa525153-ece7-44d0-a6c7-616c3dff611b` 的持久化 tool parts 依次记录了绝对
  `WORKBENCH.md` 和 canonical `project.yaml` 的 Read；工作台含本轮 run/thread/实际路径，
  项目标题仍为“隔壁的病友”，canonical/private SHA 与 manifest SHA 一致。
- 开放式创作质量仍属于模型质量观察项；“每轮真实读取当前工作台上下文”本轮已有真实模型
  证据，不再是推断。

## 第 117 轮——Project 标题的完整消费链同步

**当前轮次目标**

修复真实 Run 的 canonical `project.yaml.project_name` 已修改、`.dream` 私有副本也正确，
但 `after_main_turn` 未刷新 PostgreSQL Story 投影，Execution 页面仍显示旧业务标题的问题；
同时把 Playwright Skill 从“问题点/文件检查”升级为逐轮完整业务旅程验证。

**优化后的执行提示词**

> 以真实 Run `run_8956be79389b4bd3aa40b5107a5bb233` 和账号
> `dmeck123@suoxya.com` 为唯一业务验收对象，追踪可见用户对话、同一 Claude session、
> canonical Project/Episode 文件、成功后 Hook、Run-private `.dream`、PostgreSQL Story、
> actor-scoped API 与 Execution 页面。复用现有 Artifact Story projector/repository，在
> `after_main_turn` 幂等物化 Project 投影；DTO增加 bounded Project title，页面明确分开
> Project 与 Episode 标题。不得新增状态机、Observer 控制、前端写回、数据克隆或替代服务。
> 为每轮正常人类对话先定义预期，再验证完整消费链。

**本轮检查或修改范围**

- `DreamArtifactTurnHook.after_main_turn` 与既有 Artifact Story Index；
- Story Index 后端/前端 DTO 和 Execution masthead；
- Project/Episode、同步、测试与设计审查文档；
- `ink-dream-playwright-qa` Skill 和真实 Run 两轮对话 E2E。

**本轮完成标准**

- 成功 Dream turn 对可索引 Episode 自动物化 Story Project，不需要页面手动 reconcile；
- `project.yaml.project_name` 通过 PostgreSQL/API 到达 Execution Project 标题；
- Episode 标题保持独立，不被 Project 重命名覆盖；
- 两轮真实对话保持同一 Claude session，第二轮只读且文件/revision 不变；
- 聚焦后端、前端合同、ESLint、构建、diff gate 和真实 Chromium 通过。

**本轮实际结果和未验证推断**

- 根因确认：旧 Hook 只负责 stage、private artifact/manifest 和 EP01 binding；Story Index
  materialize 仅存在于显式 reconcile POST，因此文件正确不代表页面消费闭环完成。
- Hook 已复用 `ArtifactStoryIndexService` 自动物化，Story Index wire 增加安全
  `projectTitle`；Execution 顶部显示 Project“隔壁的病友”，Episode 仍显示“凌晨五点的敲墙声”。
- QA Skill 已明确真实业务不得克隆数据，并要求每条对话验证 Thread→文件→Hook→DB/API→页面。
- 真实 `deepseek-v4-pro` 有头两轮 E2E 为 `1 passed (32.4s)`；同一 Claude session、逐轮
  WORKBENCH Read、第二轮无文件变化、PostgreSQL/API `indexed` 和页面双标题均通过。用户随后
  要求关闭有头模式，浏览器已退出，后续未再启动。
- 聚焦后端为 `159 passed, 3 skipped, 2 subtests passed`；前端合同 16 passed、mocked
  Execution 2 passed；目标 ESLint、TypeScript/production build 和 `git diff --check` 通过。
- 未执行 staging/生产环境或并发负载验证；本轮只声明本机真实业务闭环。

## 第 118 轮——先定义 Dream 业务影响范围，再执行无头真实验收

**当前轮次目标**

纠正“看到 Episode 仍是旧标题就判断 Project 同步失败”的测试概念混淆，并按用户要求
继续完成代码、Skill 和真实 Run 的完整闭环验证，不再只检查问题点。

**优化后的执行提示词**

> 在测试前先定义 Project、Episode、canonical Artifact、Run-private `.dream`、成功后
> Hook、PostgreSQL/API 投影和最终 UI 消费面；对每个事实标记应变化、必须保持不变或不在
> 范围。针对真实 Run `run_8956be79389b4bd3aa40b5107a5bb233`，验证 Project 标题
> `project.yaml.project_name=隔壁的病友` 经 `after_main_turn` 到达 `.dream`、Story row、
> Story Index API 和 Execution `<h1>`；同时验证 EP01 标题“凌晨五点的敲墙声”、同一
> thread/session 和未点名产物不被修改。使用真实账号、真实数据、`deepseek-v4-pro` 和
> 无头 Chromium，不克隆数据、不启动替代 runtime、不使用有头模式。

**本轮检查或修改范围**

- Dream Project/Episode 业务合同和测试验收文档；
- `ink-dream-playwright-qa` 的测试前概念/影响门禁；
- `DreamArtifactTurnHook`、Story Index DTO/页面的既有未提交实现；
- 真实 Run 两轮对话 E2E 的变化与不变断言。

**本轮完成标准**

- Skill 强制在浏览器/模型运行前输出业务概念与影响矩阵；
- Project 标题完整消费链正确，Episode 语义保持独立；
- 两轮对话使用同一 Claude session，每轮都验证文件、Hook、数据库、API 和页面；
- 聚焦测试、静态检查、构建、Markdown/diff gate 和无头真实 E2E 通过。

**本轮实际结果和未验证推断**

- 页面截图已确认 Project 一级标题为“隔壁的病友”，EP01 仍显示“凌晨五点的敲墙声”；
  这是 Project-only 修改的正确业务结果，不是 Hook 漏同步 Episode。
- Skill、参考流程和真实 E2E 已加入强制影响范围合同，明确应变化和必须保持不变的事实。
- 后端聚焦测试 `125 passed, 2 subtests passed`，前端合同 `16 passed`，目标 ESLint 通过。
- 真实 `deepseek-v4-pro` 无头 E2E 使用原始 Run、真实账号和同一 thread，两轮完整业务链
  验收为 `1 passed (29.4s)`；未启动有头 Chromium。
- staging/生产环境和并发负载仍未验证，本轮只声明本机真实业务闭环。

## 第 119 轮——统一 Dream 工作空间展示标题

**当前轮次目标**

重新定义 Dream 工作空间标题，使 Execution、Dream 回访列表和 Admin 列表在 Project
存在后统一显示 canonical Project 标题；只有尚未构建 Project 时才显示创作目标前缀。

**优化后的执行提示词**

> 追踪 Dream 标题从 canonical `project.yaml.project_name`、成功后 Hook、PostgreSQL
> Story 投影、Story Index、Dream Run 回访 API 到 Dream/Admin UI 的完整读取链。定义唯一
> 派生顺序为“Project/Story title 优先，launch goal 前 80 字符仅兜底”，不得新增数据库
> 标题字段、文件扫描、双写、第二状态源或 Episode/Deck/workflow summary 覆盖。更新权威
> 设计、DTO、查询、页面和契约测试，并使用现有本机真实数据做无头只读验证。

**本轮检查或修改范围**

- Dream Run 回访后端投影、DTO、前端解析与列表；
- Execution Project 一级标题解析；
- Admin Story/Dream Run 只读查询和列表；
- Project/Episode、同步、测试验收及目录合同；
- 聚焦单元/契约测试、静态检查、构建和无头真实页面。

**本轮完成标准**

- 已存在 Project 的 Run 在所有列表与 Execution 显示同一 Project 标题；
- 尚无 Project 的 Run 显示 launch goal 前 80 字符；
- Episode 标题不受影响，Admin 不写业务数据且不扫描 Artifact；
- 聚焦测试、类型检查、构建、`git diff --check` 和无头真实验证通过。

**本轮实际结果和未验证推断**

- Dream Run DTO增加服务端派生 `displayTitle`；回访列表和 Execution 统一以 Project 标题优先，
  尚无 Project 时使用 launch goal 前 80 字符。历史 Run 通过 Workspace + stable Project slug
  解析同一 Story，不受 current `source_run_id` 更新影响。
- Admin 恢复只读 `/admin/story/workflow-runs` 页面，首列使用同一标题顺序；查询只连接共享
  PostgreSQL，不扫描或写 Artifact，也不新增 DDL/Run title。
- 后端聚焦测试 `113 passed, 2 subtests passed`；前端合同 `19 passed`；Admin Repository
  `7 passed`。Dream/Admin 目标 ESLint、Python 编译、两端 production build 和两个仓库
  `git diff --check` 均通过。
- 无头真实 Playwright 使用账号 `dmeck123@suoxya.com` 和本机原始数据，验证
  `run_ddb53a9a261d497c98ad9a6c1ec3a1c2` 在 API、Dream 回访和 Execution 均显示
  “雾中黑海湖”；无 Project 的 `run_1d6380cea6fc4a91b0586c1e79856ec4` 显示 goal 前缀，
  最终结果 `1 passed (3.5s)`；关联 mocked Execution E2E `2 passed (4.7s)`。未发送消息、
  未调用模型、未执行有头测试。
- Admin SQL 已在相同真实 PostgreSQL 上只读验证 canonical 与 fallback 两种结果；Admin 登录
  UI 本轮未自动化，页面路由、Repository 契约与 production build 已覆盖。

## 第 120 轮——Dream Agent 自然语言资产协作

**当前轮次目标**

修复真实 Run 中用户要求新增/修改人物却只得到 JSON 文本、canonical 文件和页面均未变化的
问题；定义人物、场景、分镜的完整 Agent 协作合同，并验证成功后 Hook 文件事实同步。

**优化后的执行提示词**

> 诊断真实 Run `run_ddb53a9a261d497c98ad9a6c1ec3a1c2` 的持久化消息、Claude
> session、Deck prompt、canonical 文件与 `.dream` stage。新增唯一 Agent 可执行资产协作
> 合同，覆盖人物、场景、分镜 CRUD、稳定 ID、引用完整性和失败边界；随 Dream surface
> 初始化并在每个 `ClaudeAgentService.assemble_context` 注入实际路径。Dream turn 必须使用
> workspace-file 合同而非普通 Chat standalone JSON proposal。不得修改 runner、公开消息
> DTO、session/resume、SSE，不新增状态机、Observer 控制、Watcher 或 MCP 强依赖。编写中文
> 设计与时序，审查后实施，并用真实账号、原始 Run、真实模型和无头 Chromium 验证完整
> 新增→更新→引用删除→清理流程。

**本轮检查或修改范围**

- `DeckChatContextService` 的既有 Dream mode 与 `ClaudeAgentService.assemble_context`；
- `backend/story_workspace` 工作台/资产 Agent 合同及 Dream surface 初始化；
- `DreamArtifactTurnHook` 已有完整文件事实扫描与 stage 对账；
- 人物、场景、分镜 CRUD 合同测试和真实业务 E2E。

**本轮完成标准**

- 每个 Dream turn 先 Read WORKBENCH 和资产协作合同；
- Dream turn 不再收到 legacy standalone JSON proposal；普通 Chat 行为不变；
- 三类资产增删改与引用完整性经过 canonical、Hook、`.dream` API 和页面验证；
- 无头真实测试不克隆数据、不启动替代服务，并清理测试临时资产；
- 聚焦测试、静态检查、构建和 `git diff --check` 通过。

**本轮实际结果和未验证推断**

- 已确认目标 thread 有可用 `claude_session_id` 且连续历史完整；失败的两个 assistant turn
  没有任何文件工具调用，只返回同一 JSON proposal。
- 根因已定位到公共 Chat Deck prompt 的 legacy JSON 合同仍进入 Dream turn，以及现有
  WORKBENCH 未定义资产 CRUD；不是 session 丢失或 Hook 漏扫已写文件。
- 中文设计、五类业务时序和设计审查已完成，结论为“修改后接受”；人物、场景、道具、分镜
  合同随 Dream surface 部署，并在每个可信 Dream turn 的 `assemble_context` 中注入实际路径。
- Dream turn 已切换到既有 `dream_mode` 文件协作合同；成功主轮 Hook 按完整 canonical 文件
  事实同步 `.dream` stage。sandbox 以 thread workspace 覆盖全部 canonical `assets/**`，
  `.dream/**` denyWrite；PreToolUse 只开放确认式单资产删除，不改变 runner 公开执行入口。
- 后端聚焦回归 `380 passed, 1 skipped, 113 subtests passed`；前端业务合同 `35 passed`，
  mocked Execution E2E `2 passed`；TypeScript、目标 ESLint、production build 和
  `git diff --check` 均通过。
- 真实账号 `dmeck123@suoxya.com`、原始 Run、`deepseek-v4-pro`、同一 Claude session
  `9d94db3d-c0b2-4e81-a04b-4c2be8cb531d` 已实际完成无头四轮；新增、稳定 ID 更新、引用解除、
  删除及最终清理均经过 canonical、Hook、API 和页面核对，基线恢复为 2 人物、1 场景、0 道具、
  EP01 8 镜/48 秒。该次运行曾在临时诊断版本中通过，但其放宽的删除回执断言已随 `/tmp`
  实验一并回滚，不能作为最终 spec 通过记录。
- 三条删除 Bash receipt 仍因既有 Claude Code command-level 临时目录问题记录为
  `output-error`，但删除后的 canonical 文件事实及 Hook/API/UI 投影均已验证。用户已决定跳过
  该基础设施问题；最终 E2E 恢复要求 `output-available`，故该项保持未通过/未重跑，不以放宽
  断言规避。本轮没有修改临时目录策略，也不推断其已解决。未执行有头或生产环境验证。

## 第 121 轮——撤销 `/tmp` 兼容实验并冻结边界

**当前轮次目标**

撤销本轮为 Claude Code command-level 临时目录故障引入的全部实现、测试和设计变更；保留
原有临时目录策略，并增加明确 TODO，禁止 Dream 后续任务继续改动该边界。

**优化后的执行提示词**

> 精确审计本轮与 `/tmp`、`TMPDIR`、`CLAUDE_TMPDIR`、短路径、符号链接和 `.claude-tmp`
> 有关的差异。只撤销本轮实验，不回退原仓库既有 Claude Code 临时目录实现，也不影响
> `_workspace_sandbox_config` 对 canonical `assets/**` 可写和 `.dream/**` 只读的 Dream
> 业务边界。删除为临时目录故障新增的测试豁免和设计说明；在代码与根 Agent 规则中保留
> 一个冻结 TODO，规定除用户单独批准的专项任务外不得再修改。完成后运行聚焦测试和差异审计。

**本轮检查或修改范围**

- Claude Agent runner 环境变量组装；
- workspace sandbox 原有临时目录策略；
- 资产协作设计和真实 E2E 中与临时目录故障耦合的说明；
- 根 `AGENTS.md` 的持续约束。

**本轮完成标准**

- 不存在本轮新增的 TMPDIR 注入、短路径、符号链接或 `.claude-tmp`；
- 原有 `_sandbox_claude_tmp_write_paths()` 行为保持不变；
- Dream `assets/**`/`.dream/**` capability 边界不被误回滚；
- 只保留冻结 TODO，聚焦测试和 `git diff --check` 通过。

**本轮实际结果和未验证推断**

- 已撤销 runner 的临时目录环境注入、短目录/符号链接实现、相关测试豁免和设计故障方案；
  原有 Claude Code 临时目录函数与返回值未改变。
- 根规则和临时目录函数加入冻结 TODO；Dream sandbox 的 canonical workspace 写权限及
  `.dream` denyWrite 是独立业务改动，予以保留。
- workspace/runner 聚焦测试 `146 passed, 1 skipped, 98 subtests passed`；运行时代码残留
  扫描只命中本轮记录和唯一冻结 TODO，`git diff --check` 通过。
- Claude Code 自身的 command-level 临时目录问题明确不在本轮修复范围，不能推断其已解决；
  本轮未新增 TMPDIR 注入、短路径、符号链接、`.claude-tmp` 或 sandbox 放行。

## 第 122 轮——人类语言资产全流程与 Claude Code 删除回执修复

**当前轮次目标**

修复真实 Dream 用户用“删除阿酷”等页面术语删除资产时，Claude Code shell 回执因
`/tmp/claude-501/cwd-*` 被 sandbox 拒绝而失败的问题；完善 Agent 对模糊页面术语的资产协作
规则，并以真实 Run、账号、模型完成新增、更新、引用解除、删除、Hook 同步、API 与页面显示
及最终清理的完整无头业务验证。

**优化后的执行提示词**

> 基于真实 Run `run_ddb53a9a261d497c98ad9a6c1ec3a1c2`、同一 Chat/Dream thread、账号
> `dmeck123@suoxya.com` 与真实模型 `deepseek-v4-pro`，先评估人物、场景、道具、EP01 分镜、
> Project/Episode、Hook 投影、API、页面和 Claude session 的影响边界。诊断并修复 Claude Code
> 2.1.220 删除工具产生 `zsh: operation not permitted: /tmp/claude-501/cwd-*` 的共享运行时
> 根因：使用服务端权威 `CLAUDE_CODE_TMPDIR`，SDK 子进程与 workspace sandbox 必须共享同一
> 精确根，禁止放行整个 `/tmp`、猜测 per-UID 路径或记录动态 `cwd-*`。完善每轮部署的资产协作
> 合同，使 Agent 能以展示名称、“刚才那个”“第一集最后一个镜头”等自然语言定位唯一资产，
> 不要求用户理解 ID、路径、文件名、工具、Hook 或 `.dream`。重写真实 Playwright E2E，页面
> 消息只能使用正常人类表达；内部身份只能在首轮完成后由测试读取用于证据与确认安全检查。
> 完整验证新增→同身份更新→解除引用→精确删除→删除镜头→恢复基线，并逐轮核对 canonical
> 文件、成功 Bash receipt、after_main_turn Hook、`.dream`、actor-scoped API、页面、模型和同一
> Claude session。不得克隆数据、直接清库或绕过 Agent 清理；不改公开 Agent 入口、SSE/DTO、
> session/resume、Observer 控制边界，不增加状态机或 Dream 专用临时目录实现。

**本轮检查或修改范围**

- `sdk_env.py` 的共享 Claude SDK subprocess 环境；
- `workspace.py` 的 thread sandbox 精确写目录；
- Dream Agent 资产协作合同及其每 turn 部署/读取测试；
- 真实资产 E2E 的用户话术、动态身份发现、删除确认与完整消费者证据；
- 相关中文设计、API、Agent/测试技能和文件夹同步记录。

**本轮完成标准**

- SDK 与 sandbox 都使用服务端 `CLAUDE_CODE_TMPDIR` 的同一规范化根（配置默认
  `/tmp/claude`，本机为 `/private/tmp/claude`），调用方不能漂移；
- 不再放行整个 `/tmp`、旧 `/tmp/claude-$UID` 或动态 `cwd-*`；
- 用户话术不含内部 ID/路径/工具指令，仍能完成四类资产的增改删；
- 删除必须有用户可见确认、Bash `output-available` 且不存在 operation-not-permitted 回执；
- 每轮 canonical→Hook→`.dream`→API→页面一致，thread/session/model 不变，其他业务事实不变；
- 测试临时资产经同一 Agent 对话清理，最终恢复真实数据基线；
- 后端聚焦回归、前端类型/ESLint/build、无头 Chromium 和 `git diff --check` 通过。

**本轮实际结果和未验证推断**

- 已用本机 Claude 2.1.220 二进制字符串和真实失败 tool receipt 确认支持变量为
  `CLAUDE_CODE_TMPDIR`；旧代码使用了错误变量/推断路径，并把 `/tmp` 与一次性的 `cwd-*`
  加入 sandbox，造成命令事实与 Agent 回执不一致。
- 已完成共享运行时最小修复、模糊页面术语合同、QA 技能规则、中文设计与 E2E 重写；聚焦
  workspace/runner 单测已先通过 `148 passed, 1 skipped, 98 subtests passed`。
- 首次真实重跑已证明自然语言增改与 Hook/API/页面链路，但三条删除 receipt 仍为
  `operation not permitted: /tmp/claude/claude-501/cwd-*`；原因是 macOS 将实际访问规范化为
  `/private/tmp/...`，而 settings 中仍保存 `/tmp/...` 别名。测试正确失败并用同一可见 Agent
  对话恢复 2 人物、1 场景、0 道具、8 镜/48 秒。
- 追加共享路径规范化后，真实账号、原始 Run、`deepseek-v4-pro` 与同一 Claude session
  `9d94db3d-c0b2-4e81-a04b-4c2be8cb531d` 的第二次无头四轮 E2E 通过：`1 passed (4.6m)`。
  所有页面消息均为普通人类术语；三条精确 `rm --` receipt 均为 `output-available` 且无
  `operation not permitted`，人物/场景/道具/分镜的 canonical→Hook→API→页面证据通过。
- 最终真实数据恢复为 `lead-a`、`lead-b`、`terminal`、0 道具、EP01 `shot-001` 至
  `shot-008` 共 8 镜/48 秒；sandbox `allowWrite` 仅含 thread workspace 与
  `/private/tmp/claude`，`.dream` 继续 denyWrite。
- 聚焦回归为 `189 passed, 1 skipped, 109 subtests passed`；广覆盖 Story Workspace/Claude
  回归在正确 backend 工作目录为 `889 passed, 6 skipped, 260 subtests passed`。前端 ESLint
  0 errors（21 个既有 warnings），production build 通过。未执行有头或生产环境验证。
