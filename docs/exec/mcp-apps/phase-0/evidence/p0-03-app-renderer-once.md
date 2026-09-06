<!-- [Input] One completed CallToolResult and its ui resource descriptor. -->
<!-- [Output] P0-03 AppRenderer no-replay evidence and local-Chrome screenshot. -->
<!-- [Pos] Redacted provider-free Browser evidence. -->
<!-- [Sync] 2026-09-04: revalidated one originating call and the rendered screenshot under SUO-385. -->
<!-- [Sync] 2026-09-06: revalidate no-replay and refresh behavior on the current pnpm Browser entry. -->

# P0-03 AppRenderer first-call count

- `p0Id`: `P0-03`
- Command: `pnpm --dir frontend run e2e:mcp-apps-phase0`
- Exit code: `0` (`4 passed in 10.5s`)
- Versions/lockfile: `@mcp-ui/client@7.1.1`; Chrome `152.0.7977.77`; lock SHA-256 `68d3c30f35eef1eec745d8c814475615eb7eceaf8866f0f721c4743394c1afd0`
- Redacted evidence: `p0-02-p0-04-browser-trace.json`; no screenshot is required for this current run.
- Key observation: the Node-side simulator creates the completed result once; AppRenderer reads `_meta.ui.resourceUri`, fetches the resource through the IM endpoint, and renders `shared-state-v1`. `originatingToolCalls=1`, `proxyForwardedToolCalls=0`, and no Browser navigation targets `ui://`.
- Conclusion: `pass`
- Rollback: delete only this task's run-owned output and stop its isolated renderer harness.
