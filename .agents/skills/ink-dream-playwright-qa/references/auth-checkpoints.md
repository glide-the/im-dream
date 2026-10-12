<!-- [Input] Prior successful browser login evidence and current production authentication boundaries. -->
<!-- [Output] Secret-free login checkpoints and bounded recovery decisions. -->
<!-- [Pos] Read for normal-account authentication and session recovery; technical fixtures have separate prerequisites. -->
<!-- [Sync] 2026-10-12: preserve the actual successful login source across long tasks and context changes. -->

# Authentication checkpoints

Before trying a login again, search the current execution record for the last successful login. Distinguish a fresh form submission from merely observing a previously authenticated page. Reuse the recorded browser/profile and entry when authorized and available; do not assume two accounts with the same email share credentials.

For Ink & Memory, Admin `/api/admin/auth/login` reads `admin_users` through `AUTH_DATABASE_URL`; Dream credential login uses the Better Auth product flow. Check the current implementations before relying on this mapping. `pnpm local:stable` builds and starts the existing supervised Admin application; it does not reset or synchronize these passwords.

Record a checkpoint after successful login and update its state after session loss. Use the task's existing durable execution record, with only these non-secret facts:

| Field | Meaning |
| --- | --- |
| Recorded time and state | authenticated, expired, rejected, or not yet attempted |
| Entry and resulting page | Public route and origin; omit OAuth codes, state and token parameters |
| Authentication domain and account | Product user or independent management account; approved account identifier |
| Credential/session source | User-provided for this domain, browser-saved credential, or pre-existing session; never the credential itself |
| Browser and recovery operation | Selected connector/profile, current tab reference as a hint, and the visible actions that succeeded |
| Success evidence | Resulting identity/role and actual authorized page content; a browser action's exit code is insufficient |
| Service identity | Actual repository, listener, startup entry and redacted database target when relevant |
| Evidence and remaining gaps | Safe receipt paths and the next necessary verification |

Tab IDs are discovery hints, not permanent identities. Re-list current tabs and match origin/title before claiming the page. A screenshot of cached content is insufficient after session loss; confirm a protected navigation before reporting recovery.

When a recorded login used browser-saved credentials, try that normal website autofill flow rather than repeatedly submitting an unrelated product password. Do not export the saved secret or copy it into scripts, docs, tool output or auth fixtures. If the flow cannot be operated or the browser blocks access, record that precise limitation; do not change browser channels or use raw commands to route around the rejection.

Before declaring an authentication blocker, check the actual failure branch. A page's generic invalid-credentials message alone cannot distinguish a missing member, inactive member, unsupported hash or password mismatch. Read-only production-domain diagnostics can classify those branches, but cannot substitute for visible business acceptance. Use the same database role/target as the authentication service, not merely the application's general database connection.

Credential failure does not authorize a password reset, account creation, session injection or broader role grants. Never persist password values, hashes, cookies, session tokens, OAuth codes or full unredacted credential-form snapshots. Record that a password is present only when necessary; do not read its contents to recover a session.

Current task checkpoints are linked from the repository execution index. When resuming, read their latest state rather than treating this reference as evidence that any session is currently valid.
