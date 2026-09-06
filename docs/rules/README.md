<!-- [Input] Repository guardrails, source ownership, package-manager boundaries, and validation contracts. -->
<!-- [Output] Human-readable index of the active workspace rules. -->
<!-- [Pos] Rules reference; executable workspace rules remain in .cursor/rules/*.mdc. -->
# Rules Reference

<!-- [Sync] 2026-09-06: make frontend/app/_dream the sole Dream application source, preserve the independent MCP Apps Runtime package, and limit Vite to isolated harness/rollback evidence. -->

## Scope

These rule notes are the human-readable companion to the workspace guardrails in `.cursor/rules/`.
They are adapted for the current Ink & Memory app:

- `frontend/`: React 19 + Next.js 16 + TypeScript Web shell managed by the sole pnpm workspace/lock; `frontend/app/**` is the sole App Router and `frontend/app/_dream/**` is the sole Dream application source.
- `frontend/packages/mcp-apps-runtime/src/**`: legitimate independent server-only package for the MCP Apps Node Runtime. It is not a second Dream application tree and Browser modules must not move into it.
- `backend/`: FastAPI Python service for auth, session storage, Claude Agent/Reflections workflows, Decks, speech recognition, prompt loading, and model configuration.
- `docs/`: architecture, design, API, and rule notes. Keep docs aligned with source ownership when behavior changes.

## Rules Index

- `docs/rules/no-hardcoding.md`: config-first policy for envs, routes, model roles, storage keys, prompt files, thresholds, and API bases.
- `docs/rules/component-reuse.md`: reuse-first policy for React components/hooks, editor/engine modules, backend services, Claude Agent Threads, prompts, and database helpers.
- `.cursor/rules/vibe-engineering.mdc`: architecture, hardcoding, and overlap guardrails.
- `.cursor/rules/vibe-loading.mdc`: load only the docs needed for the task.
- `.cursor/rules/vibe-doc-sync.mdc`: update folder docs and file headers when source behavior changes.
- `.cursor/rules/vibe-component-reuse.mdc`: search before adding parallel implementations.

## Golden Rules

1. Keep source-of-truth values centralized: frontend storage keys in `frontend/app/_dream/constants/storageKeys.ts`, UI language key in `frontend/app/_dream/i18n.ts`, callable model roles in the Admin Gateway catalog, and Dream runtime settings in `backend/config.py` and environment variables.
2. Reuse existing React components, hooks, API helpers, backend auth/database/config modules, Claude Agent Thread contracts, prompt files, and tests before adding new code paths.
3. Preserve the frontend/backend boundary: React calls typed API helpers; backend route behavior is composed by `backend/server.py` from focused routers and services such as `auth.py`, `database.py`, `claude_agent/`, and `services/`.
4. Do not copy Pawkeyland-specific paths, pet-domain names, Claude Agent layers, or prompt-policy locations into this project unless an active Ink & Memory feature explicitly introduces them.
5. Update the nearest `**/.folder.md` and related docs when a changed folder already participates in the workspace documentation contract.
6. Use Corepack/pnpm and the root `frontend/package.json` for current frontend install, development, build and test commands. Do not restore `package-lock.json`, nested Next roots, `frontend/src/**`, or npm/Vite as production owners.
7. Vite remains valid only where a named isolated test harness or immutable rollback receipt explicitly owns it; its presence there is not evidence of a second production frontend.
8. Distinguish focused/provider-free technical validation from public application availability and production enablement. MCP Apps remains production-off until real external Server, account/OAuth, permission and operations evidence exists; the current effective value is `productionAppsEffective=false`.
