# Dream Agent migration plan

## Final state

- One canonical Chat Thread protocol and frontend runtime.
- Dream context resolved internally during `ClaudeAgentService.assemble_context`.
- No Dream field in Chat request/message/SSE contracts.
- One class-based `DreamObserver` registered in `SessionObserverRegistry`.
- Workflow business writes remain actor/revision/idempotency authorized.
- No unsupported post-confirmation Workflow state.
- Project/Episode Artifact and PostgreSQL DDL contracts owned as documented.

## Phase 1 — Documentation authority

1. Treat Admin's Story-business interaction design as the cross-system
   Project/Episode Artifact authority.
2. Maintain the Dream-facing concept in
   `project-episode-artifact-contract.md`.
3. Replace Story Workspace task/audit/test records with module-oriented current
   design only.
4. Define Dreamflow actions and Agent interaction separately from Chat runtime.

Exit: all live links resolve to the module documents and no deleted execution
record is presented as a business authority.

## Phase 2 — Context assembly without protocol changes

1. Remove `story_workspace_dream_context` from `ClaudeAgentRunRequest`.
2. Remove Dream lookup/projection from `backend/routers/claude_agent.py`; the
   route continues to build the same standard Chat request.
3. Add a named `DreamThreadContextMapper` service using the existing actor-owned
   thread/retry-leaf resolver.
4. Resolve the internal context at the start of
   `ClaudeAgentService.assemble_context`.
5. Pass the internal object only through `_TurnExecution` and server-only
   context builder/tool environment calls.
6. Update launch, confirmation and Episode dispatchers to dispatch only actor +
   canonical Thread; no dispatcher injects a Dream request field.

Exit: source scan finds no request/router/HTTP Dream context field; a generic
Chat Thread maps to none and one valid Dream Thread maps to exactly one leaf.

## Phase 3 — Runtime activation in Phase 1

1. Replace the SDK-message closure with a named runtime activation dependency.
2. Use verified workspace manifest, frozen plugin lock, context mapping and
   canonical session facts during assembly.
3. Use one server-owned `local_persistent` placement in every deployment;
   remove environment-name maps, activation gates and lifecycle short-circuits
   from production modules.
4. Record the runtime receipt and queued→running transition before Phase 3.
5. Leave `AgentStreamingCallbacks` and the existing Phase 3 call to
   `runner.run_streaming(run_options, callbacks)` free of Dream initialization.
6. Do not modify `agent_runner.py`.

Admin/Drizzle owns the forward-only placement normalization: migration 0034
converts historical receipt/session labels to `local`, constrains future rows
to that one value and publishes `dream.runtime.local-placement.v1`. Harness
configuration remains in tests/scripts and never creates a second business
path.

Exit: no `_make_dream_runtime_init_cb`, no Dream `on_message` callback, no
protected runner diff, no deployment-label business branch, and activation
failure closes the canonical turn once.

## Phase 4 — SessionObserverRegistry ownership

1. Define `DreamObserver(SessionLifecycleObserver)` as a standard class.
2. Register it once beside `LoggingObserver`.
3. Pass internal assembled execution/bus metadata in the existing after-context
   hook; ordinary Chat is a no-op.
4. Move EventBus attach, dedupe/order/terminal fence, bounded sink and cleanup
   under that Observer.
5. Delete ThreadFactory's direct Dream coordinator fields, branches and close
   calls.

Exit: ThreadFactory contains no direct `DreamLifecycleCoordinator` dependency;
Observer exceptions do not alter SSE; every close path releases handles/tasks.

## Phase 5 — Typed router DTO projection

1. Create named enums/models/projectors for public Thread, message, metadata and
   tool choice.
2. Preserve the current response shape and private-row filtering.
3. Remove module-level field tuples/sets used as pseudo DTOs.

Exit: contract tests prove identical public JSON and no private Dream metadata,
path or blank message leak.

## Phase 6 — Remove invalid Workflow state

Dream application changes:

1. Remove the enum value and transition edges.
2. Business confirmation persists `confirmed`; post-confirmation dispatch does
   not create another Workflow transition.
3. Domain completion moves `confirmed -> completed`; domain failure/cancel may
   move from confirmed to its terminal.
4. Guidance eligibility uses explicit confirmed/failed policy.
5. Frontend status unions, routing, polling, copy and tests use `confirmed` plus
   canonical Thread `running` rather than a duplicate state.

Admin/Drizzle changes:

1. Add a new forward migration; never modify published `0032` or its receipt.
2. Preflight the existing rows/history shape.
3. Correct current rows and invalid transition history transactionally while
   preserving audit correlation and contiguous sequence/version invariants.
4. Replace check constraints/guard functions and the Drizzle enum/schema.
5. Update catalog/snapshot/capability contract and adoption tests.

Exit: live source/schema scan has no invalid state value, legacy rows adopt
atomically, unknown history shapes fail before partial mutation, and Dream only
checks the Admin-owned capability.

## Phase 7 — Legacy conversation deletion

The current worktree already removes the old public Dream message/event routes,
adapter, hook and reducer. Before merge, verify:

```bash
rg -n 'DreamStreamAdapter|iter_dream_run_events|/dream-agent/events|useStoryWorkspaceDreamAgent' \
  backend frontend/src
```

Expected production result is empty except explicit migration/source-scan tests.
No feature flag or long-lived dual writer is introduced. Rollback deploys the
prior immutable build; it does not restore both protocols in one build.

## Documentation removal record

| Removed source | Reason | Replacement | Git recovery |
|---|---|---|---|
| `docs/design/story-workspace/2026-*` | execution, audit, review and test records are not business design | module documents in `docs/design/story-workspace/` | current branch parent via `git show` |
| `docs/design/story-workspace/design_003`–`design_012` | mixed current requirements with implementation history and competing protocols | Story Workspace module docs + Dream Agent contracts | current branch parent via `git show` |
| old PRD/layout/settings documents | accumulated decision/change/test sections and duplicated module ownership | product/navigation, workbench and settings modules | current branch parent via `git show` |
| Story Workspace evidence directory and research PDF | test/research artifacts, not normative design | no design replacement; requirements retained in module docs | current branch parent via `git show` |
| legacy Dream SSE design docs | preserve a protocol explicitly being deleted | current Dream Agent architecture/lifecycle | pinned baseline `a506c83` |

No unique business requirement source is deleted until its current behavior is
represented in one module document. Links outside the directory are migrated to
the owning module.

## Release and rollback

Recommended release units:

1. Dream docs + protocol-neutral context/Observer/DTO code and tests.
2. Admin forward lifecycle migration + Dream compatible application release.
3. Dream final state-only application/frontend cleanup.

Run the Admin migration with the dedicated `MIGRATION_DATABASE_URL`, advisory
lock and atomic receipt. Deploy a Dream version that can read corrected data
before removing application compatibility. Database rollback is forward-fix or
PITR; do not publish a destructive downgrade.

## Acceptance gates

- No diff in protected Agent runner or public Claude Agent wire snapshot.
- Same Thread behaves identically in Chat and Dream for send, incremental text,
  tool confirmation, AskUserQuestion, subagent, Stop, failure and reconnect.
- Observer duplicate/replay/order/error/late-terminal tests pass.
- Dreamflow authorization and Artifact revision/CAS tests pass.
- Old Dream endpoints and frontend runtime have no production callers.
- Focused backend/frontend tests, typecheck, lint, build and `git diff --check`
  pass; headed E2E is run only when explicitly permitted for the validation
  round.
