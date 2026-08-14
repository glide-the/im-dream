# Product scope and navigation

## Product goal

Story Workspace lets a creator start or resume a Dream production, collaborate
with the Agent in one canonical Thread, inspect Project/Episode outputs, edit
bounded business data, confirm a reviewed result and continue with authorized
Dreamflow actions without losing identity or revision context.

Authenticated root entry is Chat-first: `/` is replaced with
`/story-workspace/chat`, while explicit authorized deep links keep their target.
The current primary sidebar exposes Chat, Dream and Decks in that order. Legacy
Writing, Timeline and Analysis routes remain implemented but their sidebar
entries are temporarily hidden.

## Roles

- Creator: owns Workspaces, Threads and Dream Workflow Runs; reads/writes the
  authorized business surface.
- Dream Agent: operates through shared Claude Agent runtime and installed
  Dreamflow tools.
- Operator: uses Admin for PostgreSQL search and read-only Artifact preview; not
  part of the creator navigation.

## Information architecture

```text
Story Workspace
├── Dream
│   ├── New production
│   ├── Active and waiting runs
│   └── Recent runs
├── Execution
│   ├── Project / Episode context
│   ├── Artifact workbench
│   └── Dream Agent thread panel
├── Review
│   ├── draft modules
│   └── one business confirmation
└── Settings
```

Canonical routes use public Workspace/Run identifiers only where the business
API authorizes them. The Agent panel uses `threadId`; Artifact APIs do not
accept Thread paths or filesystem paths.

## Surface selection

| Business fact | Default surface |
|---|---|
| no eligible Run | Dream launch |
| queued/running Agent turn | Dream with shared thread panel |
| pending review | Dream review modules and confirmation bar |
| confirmed with active Agent turn | Execution with shared thread panel |
| completed/failed/cancelled | Execution summary and available recovery actions |

Navigation never starts or resumes a model turn. GET requests hydrate current
state only. A new turn requires an explicit user/business command.

## Layout

Desktop uses three cooperative regions:

1. Module rail: Project/Episode navigation and availability badges.
2. Content workspace: selected Artifact or business module.
3. Detail/Agent region: inspector or the shared Thread panel.

On narrow screens these become ordered views rather than compressed columns.
The active module, Episode and detail target remain stable through resize.
Agent expansion is a presentation choice and does not reconnect under a new
Thread or start the initial prompt again.

## Accessibility

- Navigation is keyboard reachable with visible focus.
- State and errors are conveyed by text and ARIA announcements, not color alone.
- Focus returns to the invoking control when a dialog closes.
- Streaming output does not steal focus or force scroll when the user is
  reading earlier content.
- Reduced-motion preference disables non-essential transitions.
