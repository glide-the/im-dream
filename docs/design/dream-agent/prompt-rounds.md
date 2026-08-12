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
| R13 — one-way workflow boundary closure | Remove the last paths where Dream Workflow status or environment coercion can control or weaken the canonical thread runtime | Trusted binding resolution, SDK-init activation replay, deployment-tier mapping, terminal/fresh-session contracts and focused review | Terminal workflows no longer inject business activation authority into ordinary Chat turns; active business commands retain authorization; environment mapping fails closed; regressions cover four terminal states and fresh-session recovery | In progress; prompt recorded before design/implementation | Exact active-run replay policy must be proven from current activation/session persistence before editing |
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

### R13 optimized prompt — close workflow-to-thread reverse control and fail-open tier mapping

```text
Act as the final one-way-lifecycle boundary reviewer and implementation owner.
Two P1 findings must be proved and closed without creating a second runtime.
First, the trusted Dream binding resolver currently injects Dream activation
context even when the unique retry leaf is completed, failed, cancelled or
rejected. The canonical composer remains available, but SDK-init activation
rejects those workflow states, so a derived business status can block an
otherwise valid Chat thread turn. The same replay path may reject a canonical
fresh SDK session after local transcript loss because it compares the new
session ID to an old Dream runtime session record. Second, the activation
caller maps every non-test environment, including production, unknown, blank
and typos, to development, bypassing the activation service's fail-closed tier
contract.

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

Replace deployment-tier coercion with an explicit map: dev/development to
development, test/testing to test, and every production/unknown/blank/invalid
value to the existing fail-closed rejection. Never label production as
development. Add parameterized regressions for the accepted and rejected
environment values.

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

- Goal: make Workflow state strictly one-way business derivation and restore
  fail-closed deployment-tier behavior.
- Scope: binding/activation/session seams and their deterministic tests; no UI
  or protocol fork.
- Completion standard: four terminal states allow ordinary canonical messages
  without activation; active state and business commands retain authorization;
  unknown state and non-dev/test environment reject; fresh-session behavior is
  either proven/fixed or explicitly bounded.
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
