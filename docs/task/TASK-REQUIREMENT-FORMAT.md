# TASK-REQUIREMENT-FORMAT

Status: Filled Template for SUO-202
Updated: 2026-08-01
Scope: Frontend task prompt template for the story-workspace task family

> [Input] `docs/issue/ISSUES_story-workspace.md`,
>      `docs/design/story-workspace/story-workspace-prd.md`,
>      `docs/design/story-workspace/story-workspace-layout-design.md`,
>      `docs/CLAUDE.md`,
>      `frontend/src/styles/tokens.css`,
>      `frontend/src/components/AppLayout.tsx`
> [Output] Generate:
>      `docs/task/task_202_frontend_story-workspace-overview.md`,
>      `docs/task/task_202a_frontend_three-column-layout.md`,
>      `docs/task/task_202b_frontend_sidebar-navigation.md`,
>      `docs/task/task_202c_frontend_data-table-components.md`,
>      `docs/task/task_202d_frontend_review-panel.md`,
>      `docs/task/task_202e_frontend_dashboard.md`,
>      `docs/task/task_202f_frontend_state-components.md`,
>      `docs/task/task_202g_frontend_e2e-integration.md`,
>      `docs/task/task_202h_frontend_user-documentation.md`
> [Pos] task-requirement-template in `docs/task`

## Issue Snapshot

| Field | Value |
|---|---|
| Issue ID | `SUO-202` |
| Title | `[task][story-workspace][frontend] 形成前端任务文档与验证边界` |
| Type | `frontend` |
| Priority | `medium` |
| Status | `in_progress` |
| Work mode | `standard` |
| Pending comments | `0` |
| Parent | `SUO-198` |
| Parent title | `参考调研Dreem_创作者平台设计Ink-Dream的workspace` |
| Parent status | `in_progress` |
| Blocks | `SUO-203` (stage) |
| Blocked by | `SUO-201` (issue dispatch) |
| Blocker status | `done` |
| Labels | `frontend`, `task-planning` |
| Runtime note | `checkout claimed by harness for FrontendTaskAgent` |

## Task Framing

Use the source design docs above to generate a frontend task document family for the story-workspace module.

Hard constraints:

- Keep the task family focused on the frontend chain: layout skeleton → sidebar navigation → data tables → review panel → dashboard → state components → E2E integration → user documentation.
- Do not expand scope into backend schema changes, API implementation, Agent service internals, or database migrations.
- Treat `SUO-201-SH-002` (naming/types shared package) as a cross-functional dependency; frontend docs may describe the type contract consumed, but should not define backend type implementation.
- Reuse the existing frontend app shell (AppLayout, TopNavBar, tokens.css); do not invent a second layout system.
- All business identifiers MUST use `story-workspace` prefix (DEC-004).
- Desktop-only (≥1280px); no mobile/tablet responsive code.
- No user manual creation flows; all content is Agent-generated, user only reviews.
- The generated docs must tell downstream implementation exactly what to verify, what minimal fixes are allowed, and what evidence to attach before stage execution.

## Required Output Shape

The generated task family must include:

1. One overview / manifest doc for the whole story-workspace frontend bundle
2. A layout skeleton task doc (FE-001)
3. A sidebar navigation & routing task doc (FE-002)
4. A data table components task doc (FE-003)
5. A review panel & review operations task doc (FE-004)
6. A dashboard page task doc (FE-005)
7. A state components task doc (FE-006)
8. An E2E integration task doc (SH-001, frontend-led)
9. A user documentation task doc (DO-001)

Each task document must include:

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

- Layout components under `frontend/src/components/story-workspace/layout/`
- Table components under `frontend/src/components/story-workspace/table/`
- Review components under `frontend/src/components/story-workspace/review/`
- State components under `frontend/src/components/story-workspace/state/`
- Page components under `frontend/src/pages/story-workspace/`
- Hooks under `frontend/src/hooks/story-workspace/`
- Router config in `frontend/src/router/story-workspace.tsx` (new file)
- Types under `frontend/src/types/story-workspace/` (consuming shared types)
- Reuse existing: `AppLayout.tsx`, `tokens.css`, global Toast, Modal, Button, Input components

## Generation Notes

- Keep the file naming convention `task_<序号>_frontend_<slug>.md`.
- Keep the documents concise enough for execution, but explicit enough that downstream implementation does not need to infer the E2E boundary.
- All task docs must reference source Issue ID, design decision IDs (DEC-001~DEC-008), and clarify what is in-scope vs out-of-scope.
- Make the parent/child relationship explicit in the overview doc so the downstream implementation understands how the frontend task family feeds stage execution.
- Explicitly exclude: complex canvas editor, video generation, mobile responsive, user manual creation, real-time collaboration, four-view character portraits, billing system.
