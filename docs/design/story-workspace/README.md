# Story Workspace business design

This directory contains only current, normative product and interaction design.
It is organized by functional module; implementation diaries, task records,
review notes, evidence files and change histories are intentionally excluded.

## Modules

| Document | Business scope |
|---|---|
| [Product scope and navigation](./product-scope-and-navigation.md) | roles, information architecture, routes and responsive shell |
| [Dream workspace and re-entry](./dream-workspace-and-reentry.md) | run discovery, selection, canonical Thread recovery and Agent workbench |
| [Workflow execution](./workflow-execution.md) | Workflow Run states, confirmation, cancel/retry and authority |
| [Project and Episode workbench](./project-and-episode-workbench.md) | Episode/storyline/scene/shot reading and editing interactions |
| [Artifact reading and degradation](./artifact-reading-and-degradation.md) | file projection, revision, invalid/missing/degraded behavior |
| [Workflow actions](./workflow-actions.md) | Dreamflow actions, dependencies, multi-Episode progression and confirmation |
| [Settings](./settings.md) | Story Workspace settings navigation and accessibility |

Agent conversation and Project/Episode cross-system contracts are owned by:

- [Dream Agent design](../dream-agent/README.md)
- [Project / Episode Artifact contract](../dream-agent/project-episode-artifact-contract.md)
- [Dreamflow tool boundaries](../dream-agent/dreamflow-tool-boundaries.md)

## Authority rules

1. Chat history, streaming, runtime tool confirmation, Stop and reconnect use
   the canonical Thread runtime and are not redefined here.
2. Workflow, Artifact, Story Index and review are distinct business state
   domains. UI may compose them but cannot make one authoritative for another.
3. Every write rechecks actor identity, Thread ownership, Workflow permission,
   expected revision and data integrity on the server.
4. A design fact belongs in exactly one module document; other modules link to
   it instead of copying a competing lifecycle or protocol.
