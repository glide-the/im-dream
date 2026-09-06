# No Hardcoding Rule

<!-- [Sync] 2026-09-06: resolve all Dream frontend configuration owners from frontend/app/_dream. -->

## Mandatory

- Do not hardcode business IDs, API bases, local machine paths, model names, credentials, JWT settings, storage keys, prompt bodies, feature flags, retries, timeouts, language defaults, or UI state identifiers inside feature code.
- Before adding a new constant, search for an existing source of truth in frontend constants, backend config, environment variables, the Admin Gateway catalog, prompt files, API docs, or shared helpers.
- If no shared definition exists, add one in the narrowest central owner and document its purpose.

## Global-First Search Order

1. Environment variables, deployment config, and the Admin-owned model catalog.
2. Backend central modules: `backend/config.py`, `backend/auth.py`, `backend/database.py`, and the focused service owner.
3. Frontend central modules: `frontend/app/_dream/constants/storageKeys.ts`, `frontend/app/_dream/i18n.ts`, `frontend/app/_dream/api/voiceApi.ts`, and shared utils under `frontend/app/_dream/utils/`.
4. Prompt assets under `backend/prompts/`.
5. API contract documentation in `backend/API.md` and behavioral notes under `docs/`.
6. Local module constants only as the last resort, and only for values whose ownership is truly local.

## Current Examples

- localStorage keys belong in `frontend/app/_dream/constants/storageKeys.ts`; do not repeat raw key strings across components or hooks.
- UI language storage and normalization belong in `frontend/app/_dream/i18n.ts` or a shared helper that imports it.
- Frontend API URL construction belongs in `frontend/app/_dream/api/voiceApi.ts` or a central frontend config helper; do not scatter `/ink-and-memory` or endpoint paths across components.
- Auth token handling belongs in `frontend/app/_dream/contexts/AuthContext.tsx`, `frontend/app/_dream/api/voiceApi.ts`, and `backend/auth.py`.
- Model aliases and callability belong in the Admin catalog; Dream-owned credentials and endpoint overrides belong in their focused environment/config owner.
- Voice persona prompt text belongs in `backend/prompts/*.md`; route handlers and Claude Agent services should load or reference prompt definitions instead of embedding long prompt strings.
- Database schema and persistence behavior belong in `backend/database.py`; avoid duplicating SQL table names or storage serialization rules in unrelated modules.
- API request/response shapes should match `backend/API.md` and the route/Pydantic contracts in `backend/server.py`; update docs when the contract changes.
