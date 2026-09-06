# Component Reuse Rule

<!-- [Sync] 2026-09-06: resolve all Dream frontend reuse owners from the private frontend/app/_dream tree. -->

## Mandatory

- Search the active workspace before adding a React component, hook, API helper, backend endpoint, Claude Agent service, database helper, prompt file, or script.
- Prefer extending existing Ink & Memory ownership boundaries over creating parallel implementations.
- Do not import Pawkeyland-specific modules, pet-domain paths, Claude Agent services, or prompt policy assumptions into this app as a shortcut.

## Frontend Search Order

1. Nearest feature component under `frontend/app/_dream/components/`.
2. Shared stateful logic under `frontend/app/_dream/hooks/`.
3. Editor and chat behavior in `frontend/app/_dream/engine/`.
4. API integration in `frontend/app/_dream/api/voiceApi.ts`.
5. Shared constants and utilities in `frontend/app/_dream/constants/`, `frontend/app/_dream/utils/`, `frontend/app/_dream/i18n.ts`, and `frontend/app/_dream/contexts/`.
6. New component or hook only when reuse would create incorrect ownership, unclear props, or cross-feature coupling.

## Backend Search Order

1. Existing focused FastAPI router under `backend/routers/` and composition in `backend/server.py`.
2. Auth, persistence, and runtime helpers in `backend/auth.py`, `backend/database.py`, `backend/config.py`, `backend/claude_agent/`, and `backend/speech_recognition.py`.
3. Existing prompt assets in `backend/prompts/`.
4. Existing tooling and tests in `backend/tools/` and `backend/tests/`.
5. New module only when the behavior has a stable owner and would otherwise make `server.py` or `database.py` harder to maintain.

## Practical Examples

- Add editor UI by extending existing components such as `App.tsx`, `ChatWidgetUI.tsx`, `DeckManager.tsx`, or smaller components nearby before introducing a new screen.
- Add reusable client state through a hook in `frontend/app/_dream/hooks/` when multiple components need the same lifecycle, persistence, or API orchestration.
- Add backend voice/deck behavior by reusing the existing database access patterns and Claude Agent Thread/SSE contracts before adding another route shape.
- Add prompt behavior by creating or editing a file in `backend/prompts/` and loading it through `backend/config.py` patterns, not by embedding prompt bodies in request handlers.

## Documentation Requirement

- If a change alters ownership between frontend, backend, prompts, or persistence, update the nearest existing `.folder.md` and the relevant docs.
- When you choose not to reuse an existing unit, record the concrete reason in code review notes or nearby docs: wrong abstraction, wrong lifecycle, incompatible data contract, or unacceptable coupling.
