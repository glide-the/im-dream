# Settings

## Information architecture

Story Workspace settings are a section of the product settings center, not a
second application shell. Entries are grouped by user intent:

- Workspace defaults and display preferences.
- Dream production defaults that do not weaken server policy.
- Deck/plugin selection through the existing authorized Deck model.
- Privacy, data retention and integration visibility.

Runtime model entitlement, sandbox/network policy and trusted plugin paths
remain server-owned and are not represented as arbitrary free-form settings.

## Interaction

- Deep links select a known settings section; unknown sections fall back to the
  section index without writing state.
- Notion and Claude MCP details belong only to Work / Resources. Choosing any
  Settings category clears transient Notion detail state and reconciles Claude
  MCP detail state from the destination URL, so a detail cannot mask another
  category's content.
- Dirty forms prompt before navigation.
- Save uses field-level validation and version/CAS where concurrent changes are
  possible.
- Success is announced without clearing unrelated unsaved sections.
- Authorization or validation errors retain entered safe values and identify
  the owning field.

## Responsive and accessible layout

Desktop uses section navigation and a bounded form pane. At the shared 767px
boundary, narrow screens switch the entire Settings surface to one column: the
search and horizontally scrollable category rail occupy full width above a
full-width content pane. Because Settings hides the global Story Workspace
sidebar, the outer layout must not reserve the compact rail's 72px width.
Labels, descriptions, errors and destructive effects are programmatically
associated. Keyboard focus moves to the first invalid field on submit and back
to the invoking section on exit.
