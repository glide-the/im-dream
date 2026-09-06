<!-- [Input] Complete safe CallToolResult and existing Chat persistence/public-history/hydration functions. -->
<!-- [Output] P0-07 five-field refresh round-trip and no-schema evidence. -->
<!-- [Pos] Provider-free fake-DB/Browser contract evidence; no production rows are written. -->
<!-- [Sync] 2026-09-04: revalidated backend and Browser round trips under SUO-385. -->
<!-- [Sync] 2026-09-06: revalidate backend persistence plus current live/reconnect result projection. -->

# P0-07 Chat save/restore

- `p0Id`: `P0-07`
- Backend command: `uv run --native-tls --project backend --frozen --with pytest python -m pytest backend/tests/mcp_apps_phase0 -q`
- Backend exit code: `0` (`3 passed in 1.43s`).
- Browser command: `pnpm --dir frontend run e2e:mcp-apps-phase0`
- Browser exit code: `0` (`4 passed in 10.5s`, one worker, installed Chrome channel)
- Additional projection/reconnect suites: Backend current Phase 1—3 regression (`262 passed`, 8 subtests), frontend Chat/SSE contract (`39 passed`), and result/Chat-ingress/session-cleanup contracts (`15 passed`).
- Versions/lockfile: Python project harness; Node `v24.13.0`; Chrome `152.0.7977.77`; lock SHA-256 `68d3c30f35eef1eec745d8c814475615eb7eceaf8866f0f721c4743394c1afd0`
- Redacted evidence: `test_chat_apps_projection.py`; `test_result_identity_projection.py`; `phase0-app-renderer-harness.spec.ts`; `ToolConfirmationRecovery.test.ts`
- Key observation: the fake DB boundary calls existing `database.save_chat_message` and `database.list_chat_messages`, then the existing `claude_agent_thread_messages` projection. The Browser test calls existing `hydrateClaudeThreadSession` and observes the history → status → latest-ID stabilization order. `serverRef`, raw `toolName`, `toolCallId`, input, and complete `CallToolResult` remain equal.
- Schema/privacy observation: captured SQL contains no DDL/Alembic operations; sensitive connection keys are rejected before persistence; Browser MCP trace contains no credential/header/command/env markers.
- Conclusion: `pass`
- Rollback: no database rollback is needed because only a fake connection was used; delete only the test projection/fixtures.
