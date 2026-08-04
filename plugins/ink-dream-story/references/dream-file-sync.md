# Dream workspace file synchronization

This reference defines when the current Chat Agent makes Dream pages visible.
The Deck plugin describes the workflow; the host owns identity, authorization,
fixed routes, schemas, and `.dream` durability.

## Non-forgeable context

Use only the `workflowRunId` supplied by the host-started flow or by the hidden
Dream confirmation command. Do not guess a recent run, use a Chat thread ID as
a run ID, or supply actor, thread, plugin binding, snapshot, or lock fields.

Do not write `.dream` with Write, Edit, or Bash. Those paths are protected.
Only use:

- `mcp__story_workspace__write_dream_run`
- `mcp__story_workspace__write_dream_stage`

Both tools use compare-and-swap. Pass the current `expectedRevision`: `0` only
when the corresponding run or stage file does not yet exist. On a later update,
use the revision returned by the latest tool call or the hidden confirmation's
base revisions. Never overwrite after a revision mismatch.

## 1. Establish the Dream run

At the start of a host-bound Dream turn, call
`mcp__story_workspace__write_dream_run` with:

```json
{
  "workflowRunId": "run_<32 lowercase hex>",
  "expectedRevision": 0
}
```

The host writes `runtime/runs/<workflowRunId>/run.json` with the authoritative
thread, source provenance, fixed projection route, and the three required stages.
This call does not advance the WorkflowRun state machine.

## 2. Characters

1. Write complete canonical character files under `assets/characters/`.
2. Verify that every file named in `sourceFiles` exists in this workspace.
3. Call `mcp__story_workspace__write_dream_stage` with `stage: "characters"`,
   the `sourceFiles`, normalized page `items`, and the current
   `expectedRevision`.

Only after step 3 does the characters page become available. Each item contains
`entityId`, `displayName`, nullable `summary`, one declared `sourceFile`, and
string `relations`.

## 3. Scenes

1. Write complete canonical scene files under `assets/scenes/`.
2. Call the same stage tool with `stage: "scenes"`, existing `sourceFiles`,
   normalized items, and the current `expectedRevision`.

Characters and scenes may be prepared in parallel, but each stage appears only
after all of its canonical files are complete.

## 4. Storyboards

1. Write the canonical storyboard first, normally
   `stories/<project>/episodes/EP??/storyboard.yaml`.
2. If drama-forge reports or artifacts already exist, they may be additional
   source references; they never replace `storyboard.yaml` as the canonical
   storyboard.
3. Call the stage tool with `stage: "storyboards"`, the existing
   `sourceFiles`, normalized shot/beat items, and the current
   `expectedRevision`.

The upstream drama-forge package writes its own YAML and Markdown files; it does
not write `.dream`. This adapter step is required after its canonical output.

## 5. Hidden confirmation command

The command with `metadata.kind="story-workspace-dream-confirmation"` contains
the complete camelCase edits and base revisions. It is already the creator's
one confirmation.

1. Apply each allowed edit (`displayName`, `summary`, or `relations`) to the
   referenced canonical workspace file.
2. For every affected stage, call the stage tool with the command's base
   revision as `expectedRevision` and the complete updated stage projection.
3. Continue the locked Deck workflow in this same Chat thread.
4. Do not ask for another confirmation.

Later canonical changes follow the same rule: finish the workspace files first,
then CAS-update the affected Dream stage so the page can re-read the latest
revision.
