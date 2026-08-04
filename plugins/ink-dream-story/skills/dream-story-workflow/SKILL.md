---
name: dream-story-workflow
description: Drive Dream from canonical workspace files through Agent output, page rendering, one confirmation, and same-Agent continuation.
---

# Dream Story Workflow

Use this workflow when the user asks to create or revise a story, outline,
character set, scene plan, or storyboard in Dream.

The only product lifecycle is:

```text
Agent output -> page rendering -> one confirmation -> same Chat Agent continues
```

Before creating Dream assets, read `references/dream-file-sync.md` completely
and follow its canonical-file and controlled-tool sequence.

## Rules

- Preserve the locked Deck voice and constraints supplied in `<deck_context>`.
- Write durable story assets in the current Chat workspace; do not return a
  standalone proposal JSON as a substitute for workspace files.
- Synchronize Dream page metadata only after the corresponding canonical files
  are complete and readable.
- Treat the hidden Dream confirmation command as the creator's one confirmation:
  apply its edits, update affected stage revisions, then continue this workflow
  in the same Chat thread.
- Never invent a WorkflowRun, actor, thread, source provenance, revision, or path.
- Do not introduce item-by-item approval, rejection, retry, archive, or another
  confirmation step.

For ordinary questions that do not create or revise Dream assets, answer normally.
