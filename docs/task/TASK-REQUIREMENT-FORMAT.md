# TASK-REQUIREMENT-FORMAT

Status: Filled Template
Updated: 2026-07-05
Scope: Frontend task prompt template for issue-to-task conversion

> [Input] `docs/design/notion-session/overview.md`,
>      `docs/design/notion-session/connector-interaction.md`,
>      `docs/design/claude-agent/notion-point/interaction-snapshot-lifecycle.md`,
>      `docs/prd/notion-session/resource-connector.md`,
>      `docs/prd/notion-session/resource-connector-ui-design.md`,
>      `docs/stage/stage_notion-resource-connector.md`,
>      `frontend/src/App.tsx`,
>      `frontend/src/api/resourceConnectorApi.ts`,
>      `frontend/src/components/dashboard/ResourceConnectorPage.tsx`,
>      `frontend/src/constants/storageKeys.ts`,
>      `frontend/src/components/dashboard/Sidebar.tsx`,
>      `frontend/src/components/dashboard/VerticalNav.tsx`
> [Output] Generate `docs/task/task_187_frontend_notion-resource-connector-e2e-regression.md`
> [Pos] task-requirement-template in `docs/task`

## Issue Snapshot

| Field | Value |
|---|---|
| Issue ID | `SUO-187` |
| Title | `验证 Notion 资源连接器前端链路 E2E 回归` |
| Type | `frontend` |
| Priority | `medium` |
| Status | `done` |
| Work mode | `standard` |
| Pending comments | `0` |
| Parent | `SUO-185` |
| Parent title | `补齐 Notion 资源连接器完整业务链 E2E 验收与缺口拆解` |
| Parent status | `done` |
| Blocks | `SUO-185` |
| Blocked by | `none` |
| Labels | `none` |
| Runtime note | `parentBlockerAdded=true` in the live issue payload |

## Task Framing

Use the source design docs above to generate one task document for the frontend-side Notion resource connector E2E regression verification work.

Hard constraints:

- Keep the task focused on the current frontend chain: `App.tsx` entry -> `ResourceConnectorPage` -> `resourceConnectorApi` -> selection/source refresh.
- Do not expand scope into backend route changes, Notion CLI internals, write-back, Deck/file-upload, or broader navigation redesign.
- Preserve the issue priority as `medium` and explicitly note that this child issue is the evidence gate under `SUO-185`.
- Reuse the existing frontend app shell and connector client; if response-shape mismatch or local fallback behavior hides a contract drift, call it out as a compatibility risk instead of widening scope.
- The generated task document must tell downstream implementation exactly what to verify, what minimal fixes are allowed, and what evidence to attach before the parent issue can close.

## Required Output Shape

The generated task document must include:

1. 任务标题
2. 关联 Issue
3. 任务目标
4. 实现步骤
5. 涉及文件路径
6. 输入 / 输出说明
7. 依赖项
8. 测试策略
9. 完成标志
10. 风险提示

## Suggested Implementation Surface

- Frontend shell entry and view switching in `frontend/src/App.tsx`
- Connector workbench and responsive layout in `frontend/src/components/dashboard/ResourceConnectorPage.tsx`
- Connector CRUD / auth polling / resource selection / refresh client in `frontend/src/api/resourceConnectorApi.ts`
- Local fallback storage isolation in `frontend/src/constants/storageKeys.ts`
- Existing dashboard chrome surfaces if they affect connector reachability in `frontend/src/components/dashboard/Sidebar.tsx` and `frontend/src/components/dashboard/VerticalNav.tsx`
- A minimal browser-e2e harness under `frontend/tests/**` only if the repo introduces one during this task

## Generation Notes

- Reuse the current connector page and client contract; do not invent a second connector surface.
- Keep the file naming convention `task_<序号>_frontend_<slug>.md`.
- Keep the document concise enough for execution, but explicit enough that downstream implementation does not need to infer the E2E boundary.
- If a response-shape mismatch exists, call it out as a compatibility risk instead of silently widening scope.
- Make the parent/child relationship explicit in the task doc so the downstream implementation understands that closing this regression is what lets `SUO-185` move toward closure and, transitively, the broader `SUO-172` umbrella.
