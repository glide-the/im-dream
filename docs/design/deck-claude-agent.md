# Deck × Claude-Agent Integration Design

## Overview

Each **Voice** inside a Deck can be associated with a persistent **Claude-agent thread**
(`thread_id`).  When a user selects a voice from the `@`-agent picker in the Writing
view, or presses **Chat** on a voice card in the Deck Manager, the app creates (or reuses)
a Claude-agent thread for that voice and opens it in the Chat view.

This replaces the previous inline `ChatWidgetUI` that was powered by the stateless
`/api/analyze` (`chatWithVoice`) endpoint.

---

## Data Model

### `voices` table (backend)

A new nullable column is added:

```sql
ALTER TABLE voices ADD COLUMN thread_id TEXT;
```

| Column      | Type   | Notes                                           |
|-------------|--------|-------------------------------------------------|
| `thread_id` | TEXT   | UUID of the linked `chat_thread` row, or NULL   |

The `thread_id` column is populated the first time a user starts a chat session with that
voice (lazy creation).  Multiple voices in the same deck each have their own independent
thread.

---

## API Changes

### `PUT /api/voices/{voice_id}`

`VoiceUpdateRequest` gains an optional `thread_id` field so the frontend can persist the
thread association after creation:

```json
{ "thread_id": "<uuid>" }
```

### `POST /api/claude-agent/threads` (existing)

Unchanged – the frontend calls this to create a new thread and receives `{ thread_id }`.

---

## Frontend Flow

### 1. `@`-Agent Picker in the Writing View

```
User types "@" → AgentDropdown opens (list of enabled voices from Deck system)
   ↓
User selects a voice
   ↓
handleAgentSelect():
  1. Call POST /api/claude-agent/threads → get thread_id
  2. Save thread_id on the voice (PUT /api/voices/{voice_id}) [optional, lazy]
  3. Insert a lightweight AgentLinkWidget into the editor
     { voiceName, voiceConfig, thread_id }
  4. Navigate to Chat view with requestedThreadId = thread_id
```

### 2. AgentLinkWidget (replaces ChatWidgetUI)

The old full-featured inline chat widget is replaced by a compact card:

```
┌────────────────────────────────────────┐
│  🧠  Mirror                  [Chat →]  │
│  "Thread started 2026-05-30"           │
└────────────────────────────────────────┘
```

Clicking **Chat →** fires `onOpenChat(thread_id)` in App.tsx, which:
- Sets `requestedChatThreadId` state
- Switches `currentView` to `'chat'`

### 3. ChatView – External Thread Navigation

`ChatView` accepts a new optional prop:

```ts
requestedThreadId?: string;
```

A `useEffect` watches it.  When it changes to a non-null value that differs from
`activeThreadId`, the view switches to that thread (same as `handleSelectThread`).

### 4. Deck Manager – Voice Chat Button

Each voice card inside `DeckEditorModal` gets a **Chat** button.  When clicked:

1. If `voice.thread_id` exists → call `onOpenChat(voice.thread_id)` directly.
2. Otherwise → `POST /api/claude-agent/threads`, then `PUT /api/voices/{id}`
   to persist the association, then call `onOpenChat(newThreadId)`.

`DeckManager` exposes `onOpenChat?: (threadId: string) => void` to its parent (`App.tsx`).

---

## Sequence Diagram

```
User (Writing View)           App.tsx           ChatView
       │                        │                  │
       │  types "@Mirror"       │                  │
       │──────────────────────► │                  │
       │  voice selected        │                  │
       │                        │                  │
       │               POST /claude-agent/threads  │
       │                        │──────────────────X (Claude Agent API)
       │                        │◄─── thread_id ───│
       │                        │                  │
       │         insert AgentLinkWidget(thread_id) │
       │                        │                  │
       │      [Chat →] clicked  │                  │
       │──────────────────────► │                  │
       │                        │ requestedThreadId=id
       │                        │─────────────────►│
       │                        │ currentView='chat'│
       │                        │─────────────────►│ (switch to thread)
```

---

## Removed Components

| Old Component / API           | Replacement                                     |
|-------------------------------|-------------------------------------------------|
| `ChatWidgetUI`                | `AgentLinkUI` (compact link card)               |
| `handleChatSend` in App.tsx   | Removed (no inline chat)                        |
| `chatWithVoice` API call      | Removed from agent-select flow                  |
| `chatProcessing` state        | Removed                                         |

The `chatWithVoice` function itself remains in `voiceApi.ts` as it may still be used by
the Comments chat feature (`handleCommentChatSend`).
