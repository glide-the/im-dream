# Dream Deck Chat Context SQL Resolver Retirement

## Optimized Prompt

You are the Dream/Admin cross-project Chat architecture engineer. Remove Dream's unused SQL-backed `DeckChatContextService` while preserving the active `DeckChatContextAssembler`, which consumes one strict Admin Registry105 `DeckChatContextOutputDTO` snapshot and applies Dream-owned enabled/ready, voice selection, prompt and Runtime rules.

Refactor `backend/services/deck/chat_context.py` so prompt construction is a module-level pure function. Delete all database reads and the `load_deck_plugin_refs` dependency. Update the assembler to call the pure function. Keep `DeckChatContext`, `DeckChatContextError`, prompt bytes, truncation length, plugin provenance shape, selected voice behavior and Dream-mode instructions unchanged.

Replace the mixed SQLite/DTO test file with provider-free Admin snapshot tests. Retain coverage for normal prompt/provenance, non-ready failure, disabled Deck/Voice/plugin filtering, selected voice denial, exact character truncation and Dream workspace-file mode. Existing `AdminDeckChatContextData`, public Chat and confirmation tests must continue to verify actor/Deck/Voice binding and Runtime integration.

Do not add SQL, database credentials, fallback lookup, a second DTO or a Runtime query. Update file headers, folder contracts, current architecture terminology and the stage index. Preserve historical documents as history.

Validate repository-wide absence of `DeckChatContextService`, absence of `load_deck_plugin_refs` from the Chat context module, focused assembler/Admin/public Chat/confirmation tests, Python compilation/imports, Markdown references and the production database inventory. The separate workspace packer still owns its current plugin-byte packing path until that active boundary is migrated.

## Optional Enhancers

- Record the next active SQL boundary separately; do not combine it with this zero-caller retirement.
- Keep the extracted prompt function private unless another active module needs it.

## USER REQUIREMENT

Continue the Admin-auth/database-access refactor. Database interfaces must follow strict DTO and ORM repository design; Dream production paths must not retain PostgreSQL credentials or database fallbacks.

## Execution Plan

| Item | Decision |
|---|---|
| Owner | Dream consumer; Admin Registry105 owns data read and access filtering |
| Evidence | Production imports only `DeckChatContextAssembler`/error/context; `DeckChatContextService` appears only in its module and legacy SQLite tests |
| Dependencies | `AdminDeckChatContextData`, Registry105 strict DTO, public request owner and immutable turn snapshot |
| Code scope | Delete SQL resolver/import; extract pure prompt builder; rewrite tests to provider-free DTO snapshots |
| Contract changes | None to Registry105, public routes, prompts, errors or Runtime options |
| Preserved behavior | enabled/ready rules, selected voice, plugin provenance, prompt truncation and Dream mode |
| Failure handling | Missing/mismatched Admin data and disabled/non-ready facts fail before Runtime; no database fallback |
| Acceptance | Old service absent; Chat context has no plugin-ref database loader; focused tests pass; inventory drops `chat_context.py` |
| Remaining risk | The active workspace packer plugin-ref read and other Deck runtime/context SQL modules remain separate migration work |

## Design Review Result

- The active public router and `ClaudeAgentService` already consume `DeckChatContextOutputDTO` through `DeckChatContextAssembler`; no production caller uses the SQL-backed service.
- Removing the duplicate resolver does not move Runtime, SSE, workspace packing or shared-filesystem work into Admin. Admin remains responsible for DTO validation, actor filtering and ORM reads; Dream remains responsible for prompt and Runtime policy.
- The implementation therefore removes only the unreachable database authority and its SQLite tests. No API field, database schema, capability hash, prompt text, state transition or retry rule changes.

## Verification Result

| Check | Command / Evidence | Result |
|---|---|---|
| Focused business regression | `cd backend && PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_deck_chat_context.py tests/test_admin_deck_chat_context_data.py tests/test_claude_agent_service.py tests/test_server_claude_agent.py tests/test_admin_story_workspace_confirmation_data.py tests/test_story_workspace_dream_confirmation.py` | Exit 0; 155 passed, 13 subtests passed |
| Import/compile | `python -m py_compile` for implementation/test plus direct imports of assembler/error/context/DTO | Exit 0 |
| Retired boundary | repository search for `DeckChatContextService`; scoped search for `load_deck_plugin_refs` in `services/deck/chat_context.py` | Retired service absent; Chat context loader dependency absent |
| Production DB inventory | AST scan for production `database` imports and literal SQL calls | 25 remaining modules; `services/deck/chat_context.py` absent |
| Formatting/docs | `git diff --check` for code, folder contracts, terminology and stage plan | Exit 0 |

The remaining 25 production database candidates stay in the cross-project closure inventory. They include the active workspace packer's plugin-ref read, are not fallback paths for Registry105, and require their own DTO/Service/ORM migration or zero-caller retirement evidence.
