# TASK-REQUIREMENT-FORMAT

Status: Filled Template for SUO-203
Updated: 2026-08-01
Scope: Backend task prompt template for the story-workspace task family

> [Input] `docs/issue/ISSUES_story-workspace.md`,
>      `docs/design/story-workspace/story-workspace-prd.md`,
>      `docs/design/story-workspace/story-workspace-layout-design.md`,
>      `docs/CLAUDE.md`
> [Output] Generate / update:
>      `docs/task/task_201_backend_story-workspace-schema.md`,
>      `docs/task/task_202_backend_story-workspace-rest-api.md`,
>      `docs/task/task_203_backend_story-workspace-review-workflow.md`,
>      `docs/task/task_204_backend_story-workspace-agent-integration.md`,
>      `docs/task/task_205_backend_story-workspace-shared-types.md`
> [Pos] task-requirement-template in `docs/task`

## Issue Snapshot

| Field | Value |
|---|---|
| Issue ID | `SUO-203` |
| Title | `[task][story-workspace][backend] 形成后端任务文档与数据合同` |
| Type | `backend` |
| Priority | `medium` |
| Status | `in_progress` |
| Work mode | `standard` |
| Pending comments | `0` |
| Parent | `SUO-198` |
| Parent title | `参考调研Dreem_创作者平台设计Ink-Dream的workspace` |
| Parent status | `in_progress` |
| Blocked by | `SUO-201` (issue dispatch) |
| Blocker status | `done` |
| Labels | `backend`, `task-planning` |

## Task Framing

Use the source design docs above to generate / verify the backend task document family for the story-workspace module.

Backend responsibility scope:
- `SUO-201-BE-001` 数据库 Schema 与数据表初始化
- `SUO-201-BE-002` Story Workspace REST API 实现
- `SUO-201-BE-003` 审阅状态流转与批量操作 API
- `SUO-201-BE-004` Agent 产出数据接收与存储集成
- `SUO-201-SH-002` 命名规范与类型定义共享包（BackendTaskAgent 主责，FrontendTaskAgent 协作）

Hard constraints:

- Only add or incrementally update backend task artifacts under `docs/task/`.
- Do not modify `docs/design/`, `docs/issue/`, `docs/stage/`, `docs/exec/`, or any implementation code.
- Do not treat task documents as execute authorization; do not implement directly.
- All business identifiers MUST use the `story-workspace` prefix (DEC-004).
- Desktop-only (≥1280px); backend APIs must not assume mobile-specific consumers.
- No user manual creation flows; all content is Agent-generated, user only reviews.
- The project backend uses SQLite (not PostgreSQL); do not assume `pg_trgm` / `gin_trgm_ops` availability.
- Every task document must reference its source Issue ID, design decision IDs (DEC-001~DEC-008), dependencies, acceptance criteria, test/validation strategy, migration rollback requirements, and shared-type contract ownership.

## Required Output Shape

The generated task family must include:

1. `task_201_backend_story-workspace-schema.md` — `SUO-201-BE-001`
2. `task_202_backend_story-workspace-rest-api.md` — `SUO-201-BE-002`
3. `task_203_backend_story-workspace-review-workflow.md` — `SUO-201-BE-003`
4. `task_204_backend_story-workspace-agent-integration.md` — `SUO-201-BE-004`
5. `task_205_backend_story-workspace-shared-types.md` — `SUO-201-SH-002`

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

- Database schema / migrations in `backend/database.py` (project convention)
- REST routes in `backend/routers/story-workspace.py`
- Agent integration service in `backend/services/story-workspace/agent_integration.py`
- Shared types: define a single source-of-truth contract; recommend `shared/types/story-workspace/` if a monorepo shared package exists, otherwise document identical contracts in `backend/src/types/story-workspace/` and `frontend/src/types/story-workspace/` with a synchronization checklist.
- Reuse existing: global auth middleware, `chat_thread` table, claude-agent SSE service, SQLite `database.py` patterns.

## Generation Notes

- Keep the file naming convention `task_<序号>_backend_<slug>.md`.
- Keep the documents concise enough for execution, but explicit enough that downstream implementation does not need to infer the E2E boundary.
- All task docs must reference source Issue ID, design decision IDs (DEC-001~DEC-008), and clarify what is in-scope vs out-of-scope.
- Make the parent/child relationship and dependency chain explicit in each doc so StagePlanner can sequence work.
- Explicitly exclude: complex canvas editor, video generation, mobile responsive, user manual creation, real-time collaboration, four-view character portraits, billing system.
- For `SUO-201-SH-002`, specify the BackendTaskAgent as the sole owner of the canonical type contract; FrontendTaskAgent only consumes it.
