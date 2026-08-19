<!-- [Input] Writing UI, session APIs, reflections APIs, and memory workspace configuration. -->
<!-- [Output] Current Writing, Timeline, Reflections, and Memory behavior. -->
<!-- [Pos] Canonical writing-memory module design. -->

# Writing 与 Memory

## 业务目标

用户可以持续记录正文，将内容保存为 Session，在时间线中回看，并按明确配置发起 Reflections 分析。
Memory 为 Agent 提供程序化工作区，不是独立的复杂编辑工作台。

## 当前需求与结果

- Writing 编辑器保存单条或批量 Session，并支持范围、聚合、详情和删除查询。
- 编辑器写入由 Session 事件通知页面刷新；自动保存按内容签名去重，避免无变化写入。
- Timeline、Analysis、图片和好友时间线复用同一用户数据边界。
- Reflections 先初始化 Memory 工作区，再创建和启动分析任务；任务状态和结果可查询，并通过 SSE 更新。
- Reflections 配置按 section 读取、更新和删除；服务端校验权限与配置结构。
- 当前深度分析以现有 Memory/Reflections 配置为准，尚未形成完整的用户 Profile 定制产品。

## 页面与接口

| 能力 | 生产入口 |
|---|---|
| Session | `/api/sessions`、`/api/sessions/range`、`/api/sessions/aggregate` |
| Reflections | `/api/reflections/memory-init`、`/api/reflections/tasks`、`/api/reflections/latest` |
| Reflections 事件 | `/api/reflections/tasks/{task_id}/events` |
| Memory 配置 | `/api/reflections/config/{section}` |
| 图片与好友 | `/api/pictures`、`/api/friends` |

## 代码所有权

- 前端：`frontend/src/components/Editor/`、`frontend/src/components/AnalysisView.tsx`、`frontend/src/App.tsx`
- 后端：`backend/routers/sessions.py`、`backend/routers/reflections.py`、`backend/routers/pictures.py`、`backend/routers/friends.py`
- Memory 工作区：`backend/libs/claude_agent_kit/server/memory_workspace.py`
