# Story Workspace 阶段推荐按钮矩阵实施记录

> 日期：2026-08-07
> 结论：已按产品更新将当前 Episode 的工作流操作改为阶段精确集合；前端继续只消费服务端 action projection。未派发真实动作，未执行归档。

## 本轮 Optimized Prompt

将产品提供的剧本创作、剧本审阅、资产定稿、详细分镜、Prompt、全链路审阅、原子校验与制作指引阶段按钮矩阵落实为服务端拥有的 action projection。区分唯一推荐动作、受控可执行返工和 disabled preview；为完整审阅与原子校验阶段的每个返工动作计算独立 canonical input revision 和不可复用 action ID。不得由前端根据进度 DOM、数组位置或 label 推导动作。采用 TDD，并验证多 Episode 身份、刷新恢复、确认合同和现有 UI 折叠逻辑。

## Optional Enhancers

- 非空 projection 仍只有一个 `recommendedActionId`；同阶段的第二个可执行按钮是返工入口，不是第二推荐。
- 详细分镜阶段的 Prompt、完整审阅阶段的校验和制作指引只作为不可执行预览，显示真实前置原因。
- validation current 前不展示下一 Episode，防止当前 Episode 与下一 Episode 操作混淆；validation current 后继续使用既有 next plan/script horizon。
- 同一个 capability 的 advance 与 rework 使用不同 action ID intent，避免早期缓存 action ID 在后期阶段重新变成有效操作。

## 产品裁决

### 精确阶段矩阵

| 当前阶段 | 服务端有序 action options | 可执行性 |
| --- | --- | --- |
| 剧本创作 | `write_script` | 当前项可执行 |
| 剧本审阅 | `review_script` | 当前项可执行 |
| 资产定稿 | `refresh_assets` | 当前项可执行 |
| 详细分镜 | `regenerate_storyboard`, `generate_prompts` | 分镜可执行；Prompt preview |
| Prompt | `generate_prompts` | 当前项可执行 |
| 全链路审阅 | `review_full_chain`, `write_script`, `validate_episode`, `prepare_render_guide` | 前两项可执行；后两项 preview |
| 原子校验 | `validate_episode`, `write_script`, `review_script`, `refresh_assets`, `regenerate_storyboard`, `generate_prompts` | 六项均可执行 |
| 制作指引 | `prepare_render_guide`，以及 validation current 后的 next Episode horizon | 依各自服务端事实 |

实现 owner 位于 `backend/services/story_workspace/multi_episode_action_service.py:43-87`；投影时严格使用该矩阵，不再为这些阶段自动附加完整 vendor suffix（同文件 `825-888`、`955-962`）。

### 推荐、返工与预览

- 每行第一项是唯一推荐动作。
- `write_script` 在完整审阅和原子校验阶段是明确返工；原子校验阶段的 review/assets/storyboard/prompts 也是返工。
- 返工项使用 `availability=executable` 与 `canDispatch=true`；preview 使用 `canDispatch=false` 和公开 disabled reason。
- 返工完成后不直接篡改其他按钮状态；canonical files 和 workflow facts 的 revision 变化使下游 completion stale，再由 resolver 重投影。

### Revision 与 action ID

旧 snapshot 只有当前推荐动作的一个 `currentInputRevision`，不能安全支持多可执行返工。现在 snapshot 由服务端为所有 allowlisted current actions 计算独立 revision（`backend/services/story_workspace/multi_episode_action_service.py:431-460`），option/action ID/canonical inputs 都选择目标 action 自身 revision（同文件 `478-520`）。

action ID payload 同时包含 `intent=advance|rework|update`；即使同一动作的上游 revision 未变化，早期 advance action ID 也不能在后期返工阶段重放。对应测试位于 `backend/tests/test_story_workspace_multi_episode_actions.py:217-233`。

### 文案

`refresh_assets` 用户可见名称统一为“刷新 EPxx 角色与场景资产”；V2 label 由可信 Episode descriptor 生成（`backend/services/story_workspace/multi_episode_action_service.py:523-537`），legacy EP01 fallback 同步更新。前端没有拼接 EP 编号或 slash command。

## TDD 证据

### Red

- 新阶段矩阵、每动作 revision 和资产文案测试：`9 failed, 6 deselected`。
- 失败事实：旧 projector 输出完整 vendor suffix；完整审阅第二项仍是 storyboard；snapshot 拒绝 `current_action_input_revisions`；资产 label 仍为“核对 EP01 资产引用”。
- action ID intent 测试单独 Red：advance 与 rework 得到完全相同的 action ID。

### Green

- 新矩阵 Red 集合：`9 passed, 6 deselected`。
- action ID intent 与相关后端回归：`142 passed in 1.91s`。
- 正式后端测试集：`1566 passed, 1 skipped, 19 warnings, 632 subtests passed in 68.97s`。
- Episode artifact 前端 Node seam：`36 passed`。
- Dream Agent workflow action Playwright seam：首次并行运行遇到页面模块尚未初始化的瞬时 `split is not a function`；同一命令独立重跑 `1 passed (1.8s)`，未修改产品代码掩盖该事实。
- `npx tsc -b`：exit 0。
- ESLint 覆盖本轮及工作区全部改动 TS/TSX：exit 0。

## 真实 Run 只读证据

对 `run_fdd7012110c74d1db96c1ff396dd6491` 使用当前源码直接读取 durable surface/facts/registry：

| 事实 | 值 |
| --- | --- |
| Episode | `EP01` / `93c0656c179b483b885a51e3bf64ea1b` |
| Facts revision | `2` |
| Manifest revision | `sha256:cacdb95d67f2a8e43c4dfbb995e282445ca6c4b1fc9350618088c56a89c92795` |
| 推荐动作 | `review_script` |
| Label | `审阅 EP01 剧本` |
| 状态 | `executable`, `canDispatch=true`, `isRecommended=true` |
| Action options 数量 | `1` |
| Input revision | `sha256:b250e11bc7110aae6306483fe812e5a466464100a7b782bad7cf35634192a72a` |

本轮没有修改该 Run 的 artifact 或 facts，没有触发 reviewer、模型、Prompt、渲染或付费调用。

## 工作区与服务安全

- 开始时分支为 `story-workspace`，HEAD `2753d52`；已有未跟踪 `.claude/worktrees/`，未读取其业务内容、未删除、未提交。
- 5173（PID 48097）和 8765（PID 44201）是开始前已有用户服务，未停止、未重启。
- 本轮工作期间出现另一工作线的 Dream Agent Page/Panel/Dialog/CSS/composer 改动；本轮不覆盖、不格式化、不纳入阶段矩阵提交。
- 未修改 `backend/database.py`，未使用 localStorage 作为 workflow truth，未执行归档。
