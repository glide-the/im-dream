<!-- [Input] A real Admin Better Auth 1.7.4 OAuth access-token claim shape and Dream Resource Server verification code. -->
<!-- [Output] One-phase optimized execution prompt, implementation boundary and verifiable acceptance commands. -->
<!-- [Pos] Real-login defect execution record; no token, subject, email, secret or database credential is recorded. -->
<!-- [Sync] 2026-09-16: define the bounded Better Auth audience-array compatibility repair before code mutation. -->

# Better Auth OAuth audience 兼容修复执行稿

## Optimized Prompt

You are an Expert Prompt Architect.

Implement and verify a bounded Dream Resource Server compatibility repair for the real OAuth access token issued by Admin Better Auth 1.7.4. Evidence from the completed Google login shows a signed ES256 `at+jwt` access token with the configured Admin issuer, the Dream browser client, a five-minute lifetime, and an `aud` JSON array containing exactly the configured Dream API resource plus the issuer's `/oauth2/userinfo` endpoint. Dream currently enables PyJWT `strict_aud`, which accepts only a scalar audience and incorrectly returns `INVALID_TOKEN_RESOURCE`.

Project and owner: Dream `/Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory`; the Dream authentication/data-client task owns the verifier and tests. It depends on the already-running Admin Better Auth 1.7.4 issuer and the existing server-owned `AdminDataConfig`. Do not change Admin token issuance, client registration, Google OAuth, user mapping or management roles.

Read and update the actual verifier, its provider-free contract tests, affected folder documentation, and this real-business acceptance record. Preserve signature verification, ES256-only enforcement, `at+jwt`, fixed JWKS URL and cache/rate limit, issuer, required claims, lifetime, subject, client, token ID and scope checks. Continue accepting the existing scalar audience only when it exactly equals the configured Dream resource. Accept an audience array only when it is nonempty, contains unique nonempty strings, includes the configured Dream resource, and every entry is either that resource or the exact issuer-derived `/oauth2/userinfo` endpoint. Reject missing Dream resource, arbitrary extra audience, duplicate value, empty value or non-string member as `INVALID_TOKEN_RESOURCE` without leaking token data.

Do not add a database path, fallback authentication authority, network lookup, deployment-environment branch or caller-controlled allowlist. The Admin issuer, Dream resource and userinfo audience remain derived from validated server configuration. Keep browser login, Device Flow, Admin RBAC separation, Runtime/SSE behavior and shared-filesystem behavior unchanged.

Acceptance requires focused tests for scalar success, the real Better Auth two-audience array, wrong resource, userinfo-only, arbitrary extra, duplicate, empty and non-string audiences; the existing wrong-signature, wrong-issuer, expiry, unknown-kid and insufficient-scope tests must remain green. Run the focused provider-free suite, `git diff --check`, restart only the task-owned Dream backend, then use the authenticated Dream browser to prove the visible `INVALID_TOKEN_RESOURCE` error is gone. Record exact commands, exit codes and the real-browser result without recording credentials or tokens.

## Optional Enhancers

- After the focused repair is green, run the broader authentication/data-boundary tests and continue the already-authorized Device Flow, Run/Thread/SSE, model and shared-file real-business acceptance.
- If the real browser still fails, capture only redacted error codes and non-sensitive claim shape; do not log access or refresh tokens.

## USER REQUIREMENT

Continue after the user completed Google and Admin authorization, repair the resulting real Dream OAuth resource-validation defect, and proceed with the full cross-project task. Database access remains DTO → domain service → typed ORM repository → Admin-managed PostgreSQL; Dream must not regain a database path.

## Planned files and impact

| File | Change | Preserved behavior |
| --- | --- | --- |
| `backend/services/admin_data/jwt_verifier.py` | Replace scalar-only PyJWT audience mode with explicit closed audience-shape validation after signature and issuer verification | ES256/JWKS/issuer/time/type/scope checks and redacted failures |
| `backend/tests/test_admin_data_boundary.py` | Add exact scalar/array success and malformed/extra audience failures | Provider-free public verifier contract |
| `backend/services/admin_data/.folder.md` | Record the fixed audience rule | DTO/HTTP boundary ownership |
| `backend/.folder.md` | Record the Resource Server compatibility boundary | No PostgreSQL credential or fallback |
| Real-acceptance documents | Append actual Google/adoption/session/browser and repair evidence | Historical evidence remains append-only |

Risk is limited to accepting the documented Better Auth multi-audience token. The closed allowlist prevents an access token for an unrelated resource from becoming valid in Dream.
