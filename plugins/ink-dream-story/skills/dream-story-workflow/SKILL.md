---
name: dream-story-workflow
description: Drive Dream from canonical workspace files through Agent output, page rendering, one confirmation, and same-Agent continuation.
---

# Dream Story Workflow

Use this workflow when the user asks to create or revise a story, outline,
character set, scene plan, or storyboard in Dream.

唯一产品生命周期是：

```text
Agent 构建 canonical 产物 -> 宿主自动同步产物并渲染页面 -> 一次确认 -> 同一 Chat Agent 构建首集产物工作台
```

Before creating Dream assets, read `references/dream-file-sync.md` completely
and follow its canonical-file and controlled-tool sequence.

## Rules

- Preserve the locked Deck voice and constraints supplied in `<deck_context>`.
- Write durable story assets in the current Chat workspace; do not return a
  standalone proposal JSON as a substitute for workspace files.
- canonical 文件完整可读后直接结束 turn；宿主 Hook 负责稳定同步页面和 `.dream`，MCP 写工具只做即时预览或显式修复。
- Dream confirmation 是创作者的一次确认且正文对用户可见：应用修改后在同一 thread 写入 EP01 的 `episode-outline.md`、`script.md`、`storyboard.yaml`、`review-report.md`，不能只回复正文。
- 收到 Dream confirmation 后第一动作必须是内建 Write/Edit；不先规划、解释或研究 schema，不调用 Dream MCP 更新 stage。即使上一次失败已留下文件，也必须覆盖四项 Episode 文件；`storyboard.yaml` 的 `shot_id` 必须是带引号的 ASCII 字符串（如 `"shot-001"`），数字 `shot_id: 1` 无效。四项文件写完即结束，stage、`.dream` 发布和 Episode 关联由宿主成功 Hook 处理。
- Never invent a WorkflowRun, actor, thread, source provenance, revision, or path.
- Do not introduce item-by-item approval, rejection, retry, archive, or another
  confirmation step.

For ordinary questions that do not create or revise Dream assets, answer normally.
