# Dream 工作台文件同步

本参考定义 Dream Agent 与故事工作台之间的文件合同。Deck 插件负责构建创作产物，宿主负责身份、权限、固定路由、Schema、workflow 生命周期和 `.dream` 产物同步。

## 权威边界

- 只使用宿主消息提供的 `workflowRunId`、thread 和 project identity；不得猜测最近 Run，也不得把 thread ID 当作 Run ID。
- Agent 只写当前 Chat workspace 的 canonical 文件，禁止用 Write、Edit 或 Bash 写 `.dream/**`。
- 主 Agent turn 成功结束后，宿主 Hook 会读取并校验 canonical 产物、更新 Dream 页面 stage，并把允许的 Project/Episode 产物同步到该 Run 的 `.dream/runtime/runs/<run-id>/artifact/`。
- `mcp__story_workspace__write_dream_run` 与 `mcp__story_workspace__write_dream_stage` 只用于需要立即预览或显式修复的场景，不是正常同步的完成条件；不得用 MCP 返回值代替 canonical 文件。

## 初次 Dream 输出

先按宿主分配的 `project_id/project_slug` 构建以下工作台产物：

```text
assets/characters/*.md
assets/scenes/*.md
stories/<project-id>/project.yaml
stories/<project-id>/episodes/EP01/storyboard.yaml
```

文件必须完整、可读且使用合法 UTF-8。完成后直接结束本轮；宿主自动投影人物、场景和分镜三类 stage，页面据此提供一次“确认并继续”。

## 确认并继续

`metadata.kind="story-workspace-dream-confirmation"` 的用户消息就是创作者的一次确认，正文中的 JSON 可以直接读取和展示。

收到确认后按顺序完成：

1. 第一动作直接使用内建 Write/Edit；不要先规划、解释、读取 schema 或调用 Dream MCP。
2. 即使失败重试已留下旧文件，也要覆盖四项 Episode 文件；`storyboard.yaml` 每个 `shot_id` 都必须是带引号的 ASCII 字符串，例如 `"shot-001"`，不能写成数字 `shot_id: 1`。
3. `edits` 非空时，将 `displayName`、`summary`、`relations` 修改写回当前 session 已知的对应 canonical 文件。
4. 不再次询问确认，在同一 canonical Project 下完成首集协作包：

```text
stories/<project-id>/episodes/EP01/
  episode-outline.md
  script.md
  storyboard.yaml
  review-report.md
```

5. 必须真实写入四个文件，不能只在 Assistant 回复中粘贴内容；分镜 shot 使用唯一 `shot_id` 和 `shot_type/visual/camera.movement/timing.duration_sec` 最小形状。
6. 文件完成后只回复一句并结束本轮。宿主校验四项产物、更新 stage、同步 `.dream` 私有副本并构建 EP01 产物关联；`episode-workflow.json` 在第一次真实 Episode action completion 时按需创建。

任何必需文件缺失、路径不安全、Project identity 不一致、产物同步失败或产物关联未构建，都不算确认后业务完成，确认消息保持可恢复状态。
