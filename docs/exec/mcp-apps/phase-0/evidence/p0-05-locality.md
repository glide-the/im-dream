<!-- [Input] One logical fixture exposed over stdio, localhost Streamable HTTP, and Node-reachable legacy SSE. -->
<!-- [Output] P0-05 locality matrix. -->
<!-- [Pos] Provider-free Node transport evidence. -->
<!-- [Sync] 2026-09-04: reran the isolated transport probe under SUO-385. -->
<!-- [Sync] 2026-09-06: rerun the locality probe on the current Node/pnpm dependency tree. -->

# P0-05 Node locality

- `p0Id`: `P0-05`
- Command: `python backend/tests/fixtures/mcp_apps_phase0/phase0_standard_apps_fixture.py --probe-all`
- Exit code: `0`
- Versions/lockfile: Python wrapper + Node `v24.13.0`; MCP SDK `1.30.0`; lock SHA-256 `68d3c30f35eef1eec745d8c814475615eb7eceaf8866f0f721c4743394c1afd0`
- Redacted evidence: deterministic JSON stdout asserted by `test_protocol_locality.py`
- Locality matrix:

| Transport | Result | Boundary |
|---|---|---|
| Same-host/container stdio | supported | Node must be able to start the server process. |
| Localhost Streamable HTTP | supported | Node and server share a reachable loopback topology. |
| Node-reachable HTTP/SSE | supported protocol boundary | The proof uses an isolated reachable endpoint; deployment routing remains a later capability concern. |
| User-device local stdio | excluded | A server-side Node process cannot start a process on the user's device. |

- Conclusion: `pass`
- Rollback: the wrapper starts no persistent service; each probe closes its owned transport/server.
