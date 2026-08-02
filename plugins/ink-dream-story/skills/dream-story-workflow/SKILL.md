---
name: dream-story-workflow
description: Create or revise Dream stories, characters, and scenes as one structured proposal that must be reviewed by the user before downstream execution.
---

# Dream Story Workflow

Use this workflow when the user asks to create or revise a story, outline, script,
character set, or scene plan in Dream.

## Contract

Return exactly one JSON object without a Markdown fence or surrounding prose:

```json
{
  "title": "string",
  "description": "string or null",
  "type": "short | long | script | outline",
  "content": "string or null",
  "characters": [
    {
      "name": "string",
      "identity": "string or null",
      "personality": "string or null",
      "background": "string or null",
      "catchphrase": "string or null",
      "tags": ["string"]
    }
  ],
  "scenes": [
    {
      "name": "string",
      "description": "string or null",
      "order_index": 0
    }
  ]
}
```

The object is a proposal, not an approved result. Never claim that the user
confirmed it or that downstream creation executed. Preserve the Deck voice and
constraints supplied in `<deck_context>`. Use unique character names and unique
scene `order_index` values.

For ordinary questions that do not create or revise Dream assets, answer normally.
