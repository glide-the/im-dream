<!-- [Input] frontend/app/_dream voice, Deck, preference, storage, and Claude Agent Thread implementations. -->
<!-- [Output] Current ownership, precedence, data-flow, and validation boundaries for Voice configuration. -->
<!-- [Pos] Current Voice configuration design note; supersedes the retired analyze_text/trigger customization proposal. -->
<!-- [Sync] 2026-09-06: replace the pre-Next proposal with the implemented Next private-source and Deck-owned flow. -->

# Voice configuration

## Background and problem

The former design described a dedicated Settings panel, a `voice-customizations`
browser key, and `/api/sessions/analyze_text` plus `/api/trigger` as the active
Voice path. Those interfaces are not the current implementation. Automatic
`analyze_text` transport has been retired, the Dream Web source now lives below
the private Next.js App Router tree, and authenticated Voice identities come
from Deck data.

This document records the checked-in implementation. It does not promise a new
customization panel, import or export workflow, public template library, or
deployment status.

## Goals and boundaries

- Identify the current source owners and API owners.
- State the actual startup precedence for Voice configuration.
- Separate authenticated Deck data, authenticated preferences, browser migration
  data, and backend defaults.
- Preserve the ordinary Claude Agent Thread and server-owned Deck Plugin
  boundaries.

The following are outside the current contract:

- `/api/sessions/analyze_text` as an automatic Editor request;
- `/api/trigger` as the Voice execution entry;
- a `voice-customizations` browser-storage key;
- the former Save, Use Default, Import, and Export Settings panel;
- any claim that a proposed Voice marketplace or analytics feature is available.

## Concepts and rules

### Source ownership

| Concern | Current owner |
|---|---|
| Browser application and Voice state | `frontend/app/_dream/App.tsx` |
| Voice and preference API client | `frontend/app/_dream/api/voiceApi.ts` |
| Legacy browser migration helpers | `frontend/app/_dream/utils/voiceStorage.ts` and `frontend/app/_dream/constants/storageKeys.ts` |
| Authenticated session preference hydration | `frontend/app/_dream/hooks/useSessionLifecycle.ts` |
| Deck and Voice REST endpoints | `backend/routers/voices.py` |
| Preferences and backend defaults | `backend/routers/preferences.py` |
| Writing Voice execution | the existing Claude Agent Thread Server-Sent Events path exposed by `streamClaudeAgentTurn` |

All browser-owned modules above are under `frontend/app/_dream/**`. They are
loaded through `frontend/app/client-shell.tsx`; they are not a second App Router,
an independent Vite application, or a server-side Runtime package.

### Configuration precedence

The initial browser load follows the implemented order below:

1. Fetch backend fallback values from `GET /api/default-voices`.
2. For an authenticated actor, load enabled Voices from enabled Decks through
   `GET /api/decks` and `GET /api/decks/{deck_id}`.
3. If authenticated Deck Voices exist, use them.
4. Otherwise, use the legacy `voice-configs` browser value when it exists.
5. Otherwise, use backend default Voices.
6. During authenticated session hydration, a persisted `voice_configs`
   preference can replace the earlier in-memory value.

This is precedence, not merging. A selected source supplies the complete
in-memory Voice map for that step. The application does not merge individual
fields from Deck, browser, and default records.

### Persistence boundaries

- `voice-configs`, `meta-prompt`, and `state-config` are legacy browser keys
  centralized in `STORAGE_KEYS`; no code should invent alternate key names.
- Authenticated preferences are read through `GET /api/preferences` and written
  through `POST /api/preferences`.
- Deck and Voice records are server-owned business data. Browser storage is not
  authoritative for an authenticated Deck.
- First-login migration is a separate workflow. Existing browser data may cause
  the migration prompt; after server preferences report completion, non-auth
  browser application keys are cleared by the current application logic.

### Execution boundary

Writing Voice interactions use the same Claude Agent Thread transport as other
current Writing interactions. The browser sends the selected Voice system prompt
and current Editor snapshot to the existing `/api/claude-agent` Server-Sent
Events request. Voice configuration does not create a parallel Agent runtime,
Gateway, persistence protocol, or deployment-specific behavior.

### Client and server boundary

- The browser may render names, icons, colors, and enabled state from the
  selected Voice map.
- The backend owns authentication, Deck access, preference persistence, and the
  Claude Agent Thread request boundary.
- The browser must not infer Deck Plugin readiness or server capabilities from a
  model identifier or local configuration.
- The server must not treat browser-storage values as authority for another
  actor's Deck or preference data.

## Validation entry points

Use commands that match the current package and source layout:

```bash
cd frontend
pnpm run lint
pnpm run build
```

Focused transport coverage lives at
`frontend/app/_dream/api/__tests__/voiceApi.writing-sse.test.ts`; Editor removal
of the automatic analysis request is covered by
`frontend/app/_dream/engine/__tests__/EditorEngineWritingNetwork.test.ts`.
These are technical checks. They do not by themselves prove that a public
deployment, a real model call, or a production Voice workflow is available.

## Known gaps

- The legacy `voiceStorage.ts` fallback and first-login migration remain in the
  application; their removal requires a separate compatibility decision.
- `voiceApi.ts` still contains a historical comment referring to a Vite type
  workaround even though the source now belongs to the Next.js private tree.
- The former customization panel, import and export behavior, and template or
  analytics proposals are not implemented by the files cited in this document.
