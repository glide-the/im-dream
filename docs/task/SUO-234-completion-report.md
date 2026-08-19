# SUO-234 完成报告 — Dream 导航与审阅 Gate 任务合同

> **状态**: 已完成  
> **完成时间**: 2026-08-01  
> **执行 Agent**: TaskDesignAgent  
> **关联 Issue**: [SUO-234](/SUO/issues/SUO-234)

---

## 产物清单

### 新建 task 文档（4 份）

| 文件 | Issue | Domain | 说明 |
|------|-------|--------|------|
| `docs/task/task_230_frontend_dream-nav-item.md` | SUO-230-FE-001 | frontend | TopNavBar Dream 导航项、canonical 路由 `/story-workspace/dream`、兼容重定向、选中态 |
| `docs/task/task_230_frontend_dream-page-review-gate.md` | SUO-230-FE-002 | frontend | Dream 页面组合、ReviewGate 四步进度、gate 状态映射、确认版本校验 |
| `docs/task/task_230_backend_review-gate-aggregation.md` | SUO-230-BE-001 | backend | 服务端聚合查询、确认版本校验、继续/结束幂等、防绕过验证 |
| `docs/task/task_230_shared_idempotency-e2e.md` | SUO-230-SH-001 | shared | 8 个 E2E 场景：正常确认、幂等、过期拒绝、防绕过、部分确认、驳回锁定、重新生成、切换工作流 |

### 同步更新既有 task 文档（4 份）

| 文件 | 更新内容 |
|------|----------|
| `task_202b_frontend_sidebar-navigation.md` | 路由重定向 `/story-workspace` → `/dream`；`/dashboard` → `/dream`；Sidebar 首页指向 `/dream`；新增增量差异说明 |
| `task_202e_frontend_dashboard.md` | Dashboard 降级为可复用组件；空态引导指向 Dream；新增与 Dream 页面协同说明 |
| `task_202d_frontend_review-panel.md` | 确认操作追加 `workflow_run_id` + `review_version`；ReviewGate 联动；过期版本处理 |
| `task_202_backend_story-workspace-rest-api.md` | confirm 端点增强版本校验；为 `task_230` 端点预留路由扩展点；新增增量边界说明 |

---

## 差异摘要

### 路由变更

- **Canonical**: `/story-workspace/dream`（新增）
- **重定向**: `/story-workspace` → `/dream`；`/story-workspace/dashboard` → `/dream`
- Dashboard 保留组件但不再拥有独立路由状态

### 审阅 Gate 核心规则

- Gate 聚合当前 `workflow_run_id` 的全部必审 story/character/scene
- 任一项 `pending` 或 `rejected` → 锁定；全部 `confirmed` → 解锁
- 确认必须携带 `workflow_run_id` + `review_version`，服务端拒绝过期版本
- 继续/结束必须幂等：首次合法请求后只执行一次
- 客户端直接调用 continue API 必须被服务端以聚合状态拒绝

### 状态映射（`StoryWorkspaceReviewGateState`）

```
story-workspace-agent-running → story-workspace-rendering → story-workspace-pending-review → story-workspace-confirmed → story-workspace-dream-running/story-workspace-completed
```

---

## 未决依赖

| 依赖 | 状态 | 影响 |
|------|------|------|
| [SUO-226](/SUO/issues/SUO-226) 传播单 | Issue 阶段已完成；其下游实现未完成 | `task_230_backend_review-gate-aggregation` 仍依赖 `SUO-226-BE-001` / `SUO-226-BE-004` 对应的 `workflow_run` 数据模型与 API；不得把传播单 `done` 误判为实现完成 |
| `SUO-226-SH-001`（Deck 运行配置技术传输合同） | [CLARIFICATION_NEEDED] | 合同冻结前下游使用 mock/适配层；不影响 task 文档产出 |
| `task_213_frontend_story_workspace_status` | Task 合同已产出、实现状态待 Stage/Exec 核验 | Dream 页面可按该合同复用工作流上下文条；实现未就绪时使用同字段的占位组件 |
| E2E harness | 未发现 Playwright / Cypress 配置 | StagePlanner 需先安排独立 bootstrap，或明确采用 agent-browser 可追溯验证；task 合同不假定框架已存在 |

---

## 最小校验结果

- ✅ 4 份增量 task 文档已创建并遵循 `TASK-REQUIREMENT-FORMAT.md` 结构
- ✅ 4 份既有 task 已增量同步，无破坏性修改
- ✅ 每份 task 明确标注允许/禁止修改范围、验收条件、测试策略
- ✅ `/story-workspace/dream` canonical 路由、兼容重定向、运行级 ReviewGate、服务端防绕过、`workflow_run_id + review_version` 校验与幂等要求均已明确
- ✅ 对尚未完成的 SUO-226 依赖已识别并记录，未擅自假定已实现
- ✅ Backend 涉及路径已按仓库 Python/FastAPI 结构归一到 `backend/routers/`、`backend/services/` 与 `backend/tests/`，未保留 TypeScript `backend/src/*.ts` 假设
- ✅ 未修改 `docs/design/`、`docs/issue/`、`docs/stage/`、`docs/exec/`、应用代码或 `TASK-REQUIREMENT-FORMAT.md`
- ✅ 所有业务标识使用 `story-workspace` 前缀（DEC-004）

---

## 后续 StagePlanner 可消费路径

StagePlanner 应按以下依赖顺序排期：

1. `task_230_frontend_dream-nav-item`（可并行于基线）
2. `task_230_frontend_dream-page-review-gate` + `task_230_backend_review-gate-aggregation`（前后端并行，均依赖基线完成）
3. `task_230_shared_idempotency-e2e`（依赖前两者完成后联调）

---

## 设计决策引用

- `DEC-017`: 全局 Dream 导航以 `/story-workspace/dream` 为 canonical 入口
- `DEC-018`: 运行级审阅 gate 在全部必审项确认前禁止继续或结束
- `DEC-010`: 单次运行锁定 Deck 插件版本、`deck_runtime_snapshot_id` 与 `runtime_plugin_lock_id`
- `DEC-014`: 重试默认沿用固定版本
