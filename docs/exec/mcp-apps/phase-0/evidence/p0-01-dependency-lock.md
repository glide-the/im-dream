<!-- [Input] Exact package manifest/lockfile plus the admitted local Node/npm/Chrome toolchain. -->
<!-- [Output] Reproducible dependency-freeze evidence for P0-01. -->
<!-- [Pos] Redacted Phase 0 evidence; it does not authorize production usage. -->
<!-- [Sync] 2026-09-04: revalidated exact roots and dry-run lock reproducibility under SUO-385. -->
<!-- [Sync] 2026-09-06: replace the npm receipt with the current canonical pnpm lock evidence. -->

# P0-01 Dependency lock

- `p0Id`: `P0-01`
- Command: `pnpm --dir frontend list @modelcontextprotocol/ext-apps @modelcontextprotocol/sdk @mcp-ui/client @playwright/test --depth 0`
- Exit code: `0`
- Reproducibility command: `pnpm --dir frontend install --frozen-lockfile --ignore-scripts`
- Reproducibility exit code: `0`
- Versions: Node `v24.13.0`; pnpm `10.28.1`; Chrome `152.0.7977.77`; `@modelcontextprotocol/ext-apps@1.7.5`; `@modelcontextprotocol/sdk@1.30.0`; `@mcp-ui/client@7.1.1`; `@playwright/test@1.62.1`
- Lockfile SHA-256: `68d3c30f35eef1eec745d8c814475615eb7eceaf8866f0f721c4743394c1afd0`
- Redacted evidence: `frontend/package.json`, `frontend/pnpm-lock.yaml`, `frontend/pnpm-workspace.yaml`
- Key observation: all MCP Apps root dependencies are exact versions; pnpm reports one resolved root set and the frozen install makes no lock change. No `latest` selector is present.
- Transitive-manifest note: lockfile package metadata retains upstream-compatible ranges such as `^1.2.0` and `^1.29.0`; the selected root and resolved package versions remain exact and are the values reported above.
- Conclusion: `pass`
- Rollback: revert only the current MCP Apps dependency/script additions with the previous validated image/lock; do not create an npm lock or rewrite unrelated dependencies.
