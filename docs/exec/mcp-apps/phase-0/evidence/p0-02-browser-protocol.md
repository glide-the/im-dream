<!-- [Input] Standard Browser MCP Client, IM endpoint, and phase0-standard-apps-fixture counters. -->
<!-- [Output] P0-02 protocol/network evidence. -->
<!-- [Pos] Redacted provider-free Browser trace. -->
<!-- [Sync] 2026-09-04: revalidated the exact SUO-385 one-worker Chrome command. -->
<!-- [Sync] 2026-09-06: rerun the current pnpm Browser entry with installed Chrome. -->

# P0-02 Browser protocol

- `p0Id`: `P0-02`
- Command: `pnpm --dir frontend run e2e:mcp-apps-phase0`
- Exit code: `0` (`4 passed in 10.5s`, one worker, installed Chrome channel)
- Versions/lockfile: Node `v24.13.0`; Chrome `152.0.7977.77`; lock SHA-256 `68d3c30f35eef1eec745d8c814475615eb7eceaf8866f0f721c4743394c1afd0`
- Redacted evidence: `p0-02-p0-04-browser-trace.json`
- Key observation: Browser methods include `initialize`, `notifications/initialized`, `tools/list`, and `resources/read`; every Browser MCP request path is `/phase0/im/mcp`. The Browser sees neither an upstream endpoint nor credentials/command/env material.
- Conclusion: `pass`
- Rollback: stop only the ephemeral `phase0-standard-apps-fixture` and Vite harness instances; the test closes both in `finally`.
