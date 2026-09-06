<!-- [Input] DEC-002 Host adapter, resource permission metadata, server-owned policy, and adversarial messages. -->
<!-- [Output] Passing P0-04 evidence for revision-bound two-iframe permission enforcement. -->
<!-- [Pos] Decision-driving Phase 0 security evidence; production Apps remains disabled. -->
<!-- [Sync] 2026-09-04: SUO-387 bounded rerun passes P0-04 on the frozen dependency/Chrome combination. -->
<!-- [Sync] 2026-09-06: current pnpm/Chrome rerun passes the full DEC-002 security contract. -->

# P0-04 Security isolation

- `p0Id`: `P0-04`
- Final command: `pnpm --dir frontend run e2e:mcp-apps-phase0`
- Final exit code: `0` (`4 passed in 10.5s`; one worker; installed Chrome channel)
- Versions/lockfile: `@mcp-ui/client@7.1.1` using only `AppBridge` / `PostMessageTransport`; `@modelcontextprotocol/ext-apps@1.7.5`; `@modelcontextprotocol/sdk@1.30.0`; `@playwright/test@1.62.1`; Chrome `152.0.7977.77`; lock SHA-256 `68d3c30f35eef1eec745d8c814475615eb7eceaf8866f0f721c4743394c1afd0`.
- Redacted evidence: `p0-02-p0-04-browser-trace.json`.

## Runtime observations

- `ImMcpAppHostAdapter` is the only permission-bearing iframe owner. `AppRenderer` / `AppFrame` are absent from the running PoC source path.
- `requestedPermissions=[geolocation]` came from the actual `contents[0]._meta.ui.permissions`; test-owned desired and Host-supported permissions produced `effectivePermissions=[geolocation]` at revision `phase0-policy-revision-2`.
- Before outer iframe navigation/insertion, the adapter wrote the immutable sandbox tokens and allow policy. The proxy applied the same tokens and effective permission to the inner iframe.
- Outer/inner allow: `camera 'none'; microphone 'none'; geolocation; clipboard-write 'none'`.
- Proxy `Permissions-Policy`: `camera=(), microphone=(), geolocation=(self), clipboard-write=()`; no directive contains `*`.
- `hostCapabilities.sandbox.permissions` exposed only `geolocation`; the isolated Chrome geolocation call succeeded. Camera remained denied/unavailable.
- Missing permissions and ungranted camera produced an empty effective set and deny-all outer/inner policy. Invalid resource metadata, an unknown permission key, and invalid desired policy degraded before a usable iframe existed.
- A same-parent forged resource-ready message with different permissions/tokens was rejected by the revision-bound proxy decision. Invalid schema and foreign-window source messages were rejected without changing the inner iframe policy.
- Separate origin, restrictive CSP, parent-DOM denial, external-network blocking, schema/source validation, and ordered teardown all passed.
- Counters remained `originatingToolCalls=1`, `proxyForwardedToolCalls=0`, `resourceReads=1`.
- Trace records requested/effective permissions, revision, outer/inner allow, response policy, positive/negative probes, `appPermissionsPropagated=true`, and `appSandboxOverridePropagated=true`; it contains no HTML, credential, header value other than the policy under test, or user content.

## Iteration receipts

| Attempt | Exit | Observation / correction |
|---|---:|---|
| Current pnpm rerun | 0 | `4 passed in 10.5s`; positive/negative capabilities, forged inputs, diagnostics, refresh and ordered teardown all pass. |

## Conclusion

- Conclusion: `pass`
- Rollback: `phase0-isolated-poc-cleanup`; remove only the bounded adapter/fixture/test/evidence changes and stop only named run-owned processes. Keep production Apps disabled.
