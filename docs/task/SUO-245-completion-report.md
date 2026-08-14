# SUO-245 Task 设计交付报告

## 1. 交付范围

- Paperclip Issue：`SUO-245`
- 输入设计：`docs/design/story-workspace/project-and-episode-workbench.md`
- 增量 Issue：`docs/issue/ISSUES_story-workspace-suo241-delta.md`
- 稳定映射基线：`docs/issue/ISSUES_story-workspace.md`
- 写入范围：仅 `docs/task/`

## 2. Requirement Gate

已先将 10 条 Issue 的标题、domain、优先级、标签、依赖、设计决策、验收输入和路径填入 `docs/task/TASK-REQUIREMENT-FORMAT.md`，模板状态为 `Filled Prompt Template for SUO-245`；随后才生成任务文档。

## 3. Issue 与 Task 一一映射

| Issue | Domain | Task 文档 |
|---|---|---|
| `SUO-241-BE-001` | backend | `docs/task/task_241_backend_episode-adapter-projection.md` |
| `SUO-241-BE-002` | backend | `docs/task/task_241_backend_run-record-audit.md` |
| `SUO-241-BE-003` | backend | `docs/task/task_241_backend_review-gate-conflict.md` |
| `SUO-241-FE-001` | frontend | `docs/task/task_241_frontend_episode-workspace.md` |
| `SUO-241-FE-002` | frontend | `docs/task/task_241_frontend_episode-list-table.md` |
| `SUO-241-FE-003` | frontend | `docs/task/task_241_frontend_episode-detail-tabs.md` |
| `SUO-241-FE-004` | frontend | `docs/task/task_241_frontend_episode-review-panel.md` |
| `SUO-241-FE-005` | frontend | `docs/task/task_241_frontend_episode-states.md` |
| `SUO-241-SH-001` | shared | `docs/task/task_241_shared_episode-projection-e2e.md` |
| `SUO-241-SH-002` | shared | `docs/task/task_241_shared_review-gate-conflict-e2e.md` |

## 4. 非阻塞澄清项保留

| 澄清项 | 默认假设 | 主要落点 |
|---|---|---|
| `[CLARIFICATION_NEEDED] requiredArtifactKinds` | 默认 script/storyboard/prompts/review-report，最终以锁定 Deck workflow snapshot 为准 | Prompt Template、两份 shared E2E、相关 backend/frontend 风险 |
| `[CLARIFICATION_NEEDED] 时长差异阈值` | 默认按百分比，warning/block 阈值由 workflow 规则决定 | Prompt Template、两份 shared E2E、列表/Gate 风险 |
| `[CLARIFICATION_NEEDED] 手工结构化编辑范围` | 默认仅基线批准字段；保存创建新 artifact version | Prompt Template、run audit、EpisodeReviewPanel |

## 5. 校验结果

- 任务数量：10。
- primary Issue 映射：10 个唯一目标，无遗漏或重复。
- 命名：全部符合 `task_<序号>_<domain>_<slug>.md`，domain 仅为 backend/frontend/shared。
- 章节：每份均包含任务标题、关联 Issue、任务目标、实现步骤、涉及路径、I/O、依赖、测试、完成标志、风险提示。
- 依赖：逐项核对增量清单中 17 条直接依赖引用。
- shared 边界：两份 shared 文档均显式列出前端、后端、联调、验收责任。
- 设计范围：保留 DEC-020～DEC-025 与相关稳定基线，排除复杂画布、视频能力、移动端、Deck 内部流程及实现代码。
- Markdown：`git diff --check` 通过。
- 工作区保护：未改写 `docs/design/`、`docs/issue/`、`docs/stage/` 或实现代码；这些目录中的既有变更保持原样。

## 6. Prompt 迁移记录

- `SUO-245` 生成任务文档时使用的已填充 prompt 已原样迁移到 `docs/task/TASK-REQUIREMENT-SUO-245.md`，作为该次 Requirement Gate 的审计快照。
- `docs/task/TASK-REQUIREMENT-FORMAT.md` 后续恢复为可复用模板；本报告与 10 份 `task_241_*` 交付物保持不变。
