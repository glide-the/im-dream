<!-- [Input] Two new MCP sessions plus shared deterministic fixture state. -->
<!-- [Output] P0-06 connection-state portability evidence. -->
<!-- [Pos] Provider-free Node session evidence. -->
<!-- [Sync] 2026-09-04: revalidated the suite through the frozen uv project after the system Python lacked pytest. -->
<!-- [Sync] 2026-09-06: rerun fresh-session portability on the current candidate. -->

# P0-06 Fresh-session portability

- `p0Id`: `P0-06`
- Command: `uv run --native-tls --project backend --frozen --with pytest python -m pytest backend/tests/mcp_apps_phase0 -q`
- Exit code: `0` (`3 passed in 1.43s`)
- Versions/lockfile: Node `v24.13.0`; MCP SDK `1.30.0`; lock SHA-256 `68d3c30f35eef1eec745d8c814475615eb7eceaf8866f0f721c4743394c1afd0`
- Redacted evidence: `test_protocol_locality.py`; fixture probe reports `sharedStateVisibleAcrossSessions=true`
- Key observation: a fresh Streamable HTTP session and a fresh Node-upstream session independently list/read the same deterministic business state. No Agent worker socket or in-memory client object is transferred to the Browser-facing proxy.
- Conclusion: `pass`
- Rollback: close the two isolated sessions and their owned loopback servers; the fixture does so before process exit.
