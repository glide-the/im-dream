# drama-forge 第一集流程指导模板返工记录

> 日期：2026-08-06  
> 性质：用户追加问题判定、设计裁决与后续实现证据 owner  
> 上游：`design_009_drama-forge-first-episode-storyline-storyboard-workbench.md`  
> 约束：模板指导 Dream Agent，但不拥有 artifact/nextAction truth，不自动串行，不绕过工具确认

## 0. 本轮规划前置器

### 0.1 Optimized Prompt

调查恢复按钮的服务端指令构造、canonical project guidance、Episode nextAction resolver 与 vendor drama-forge 的真实第一集工作流。把已验证的 `/drama-plan → /drama-script (EP01) → script-reviewer → /drama-asset → /drama-storyboard (EP01) → /drama-prompt (EP01)` 顺序沉淀为单一 Dream Agent workflow guidance 模板；恢复指令和每次继续指令复用该模板。模板必须明确当前轮只执行服务端授权 action，恢复轮只恢复 canonical project/EP01 binding，未来步骤只用于依赖校验和方向提示；不得无条件串行、不得从 Agent 消息推导完成、不得绕过 Story Workspace Tool Confirmation。

### 0.2 Optional Enhancers

- 区分 public action label、vendor display command 与 server-private workflow guidance。
- 对 `script-reviewer` 明确其是 `drama-script` Skill 的 blocking required review，不虚构 `/script-reviewer` slash command。
- 让 README 顺序测试同时验证 guidance 模板顺序，避免 evidence table 与 Agent instruction 漂移。

### 0.3 计划与验收

1. 取得 README、Skill/Agent、现有 action resolver 和 instruction builder 行号证据。
2. 修订 `design_009`，固定模板 owner、单步授权与工具确认边界。
3. 独立评审后先写 Red，再实现 Green 并独立 commit。
4. 与 Dream Tool Confirmation 修复合并跑后端/前端/浏览器门禁。

验收要求：模板步骤与 vendor 顺序一致；`script-reviewer` 语义准确；恢复轮不执行下游；continue 轮只执行 current action；不存在 raw MCP/CAS/路径/凭证；工具请求仍经 Dream 专属确认面。

## 1. 问题判定

### 1.1 问题

→ “恢复第一集关联”按钮生成了一段 server-authored Agent 指令，但当前内容只解释 canonical project 与 binding 恢复，没有把后续第一集 workflow 作为统一流程约束；各 continue 指令也只说明本轮入口，Agent 缺少完整依赖方向。

### 1.2 现状证据

- `_recover_text()` 只拼接 canonical/recovery guidance 与“恢复 EP01 关联”（`backend/services/story_workspace/episode_action_service.py:1227-1235`）。
- `_continue_text()` 只有目标能力、执行入口、EP 标识、manifest revision 与上游核对提示（同文件 `:1237-1254`）。
- server 已有完整 12 步 vendor evidence table，并将 2—10 映射为 Episode action（同文件 `:117-157`）；`actionOptions` 只从当前 nextAction 返回有序后缀，只有当前项可派发（同文件 `:654-679`）。
- vendor README 的第一集顺序为 `/drama-plan`、`/drama-script (EP01)`、`script-reviewer`、`/drama-asset`、`/drama-storyboard (EP01)`、`/drama-prompt (EP01)`（`vendor/drama-forge/drama-forge/README.md:353-370`）。
- `script-reviewer` 不是 slash command；它是 Agent（`vendor/drama-forge/drama-forge/.claude/agents/script-reviewer.md:1-13`），同时是 `drama-script` Skill 的 blocking required review。该 Skill 的 inputs/outputs 明确包含 `episode-outline.md → script.md + review-report.md`（`vendor/drama-forge/drama-forge/.claude/skills/drama-script/SKILL.md:1-25`），Step 4 由 `script-reviewer` 与 `continuity-keeper` 审查（同文件 `:120-137`）。
- resolver 对当前 script revision 已有 APPROVED script/full-chain report 时直接跳过 `review_script`；只有报告缺失、陈旧或未批准才补齐审查（`backend/services/story_workspace/episode_action_service.py:771-795`）。
- assets、storyboard、prompts、full-chain review、validation 与 render guide 的推进不仅看文件，还要求 current input revision 的 workflow completion fact（同文件 `:795-824,850-877`）；专用 completion 工具验证 server-owned action/message/revisions 后 CAS 回写技术事实（`backend/libs/claude_agent_kit/server/story_workspace_tool.py:104-115,519-620`）。

### 1.3 根因

→ vendor workflow evidence、nextAction resolver 和 Agent task envelope 虽已分别存在，但 instruction builder 没有复用同一个审定 workflow guidance；Agent 只能看到局部操作，恢复轮尤其容易把“恢复绑定”和“后续创作”理解成孤立任务。

### 1.4 可选方案

1. 在每个按钮里手写全部命令并要求自动跑完；
2. 只保留当前局部入口；
3. 从 server-owned vendor flow 生成统一 guidance，同时以 nextAction/current capability 约束每轮唯一执行范围。

### 1.5 最终决策

→ 采用方案 3。

- instruction template 是 Dream Agent 的流程/依赖 guidance，不是 artifact truth，也不是新的业务状态机。
- 恢复轮模板先列出第一集核心顺序，再明确“本轮只恢复 canonical project 与 EP01 binding；成功后停止，由服务端重新读取 artifact facts 决定 `/drama-plan` 或更后步骤”。
- continue 轮复用同一顺序，并明确“本轮唯一授权入口”和当前 artifact/manifest revision；不得执行后续项。
- `script-reviewer` 写成“`/drama-script` 内置的 blocking 五维度审查”，不得生成不存在的 `/script-reviewer` 命令；当 resolver 的 `review_script` 为当前项时，指令要求补齐/刷新 `review-report.md`，仍由 Dream Agent 在 vendor Skill 边界内调度 reviewer。
- 若 `/drama-script` 已为当前 `script.md` revision 产出 APPROVED script/full-chain report，resolver 跳过 `review_script`；它不是每次 `/drama-script` 后必然发生的第二次派发。
- guidance 分为同一 owner 下的“核心创作序列 2—7”和“本期完成序列 8—10”：全链路审查、完整产物校验、render guide/voice 也必须有 action-specific 当前轮说明；11—12 仍明确为本期外。
- Agent 只能根据 server envelope 与工作区文件核对依赖；完成事实仍来自 Episode artifacts/workflow facts，下一步仍由 resolver 计算。
- 对 Episode continue，公开 workflow template 只含产品步骤、当前 action、canonical 前置/输出与 current-only/stop 约束；server 在可信 Dream context 内根据 `story_workspace_episode_action` provenance 另注入 private completion guidance。Agent 写入并重新核验 canonical 输出后必须调用 Story Workspace 受控 completion 能力，成功或 fail-closed 后停止，不得继续下一产品步骤。
- exact completion MCP 名称、message/input/facts/manifest/workflow revision 和 CAS 参数只存在于 server-private context/tool runtime；不得写入 public user message、actionOptions、Dream snapshot/SSE 或 DOM。
- 任一 Write/Bash/网络等工具许可继续走 run/actor/turn 绑定的 Dream 专属 confirmation snapshot/SSE；模板文本不能视为预授权。

### 1.6 影响范围

→ 新增或收敛 Episode workflow instruction owner；`episode_action_service` 的 recovery/continue public task envelope；Claude Agent trusted Dream context 的 private action-completion guidance；Episode action/MCP/context/message 安全测试。不得修改 artifact reader/writer owner、resolver 规则、公共 actionOptions schema 或 `backend/database.py`。

### 1.7 风险与验收

风险：把完整顺序误写成“连续执行清单”会绕过分阶段确认；把 reviewer 写成 slash command 会虚构 vendor surface；把模板作为 owner 会与 artifact facts 冲突。

验收：README 步骤 2—10 与 template/action entries 逐项机器校验；恢复/continue 文本分别断言 stop/current-only；script-reviewer 类型与跳过语义断言；canonical 文件已写但 completion 未回写时 nextAction 不前进，private guidance 要求 exact completion；public message/API/DOM 不出现内部 tool/CAS/revision 参数；安全 payload 与工具确认回归。

## 2. 实现与评审台账

### 2.1 设计独立评审

- 首轮：FAIL（P0=0 / P1=3 / P2=1）。缺口为 completion handshake、步骤 8—10、reviewer 跳过语义，以及完整证据路径/影响范围。
- 返工：按本轮 Prompt Architect 增加 public/private instruction 分层、trusted completion provenance、2—10 action entries、review_script 条件语义与公共安全边界。
- 复评：PASS（P0=0 / P1=0 / P2=0），允许进入实现。

### 2.2 实现台账

| 轮次 | Red / 问题 | Green / 裁决 | 评审 |
|---|---|---|---|
| 初始实现 | 新 owner 尚不存在，2 个测试 collection error | 单一 `episode_workflow_instruction.py` 生成 README steps 2—10、入口、前置、产物、边界与完成要求；初始聚焦组 `153 passed` | 首轮代码评审 FAIL（P0=0 / P1=2 / P2=1） |
| 安全返工 | 恶意 guidance、server seal 与 persisted claim 组首跑 `20 failed, 16 passed`：复现 13 类私有协议/越权续跑文本、seal 缺失及 6 类伪造/过期 claim | user guidance 增加私有协议、MCP、CAS、完整 revision、claim 字段与越权续跑 denylist；文本 JSON 编码为“仅当前 action 创作偏好”，末尾重新施加 current-only/stop；private context 重新读取持久 user message，严格核对 message/run/thread/actor/dispatching/claim/未过期 lease/exact provenance | 返工复评 PASS（P0=0 / P1=0 / P2=0） |

最终验证：

- workflow/context/service：`172 passed, 17 subtests passed`。
- completion tool/runner：实现者全组 `115 passed, 1 skipped, 115 subtests passed`；独立评审聚焦 `22 passed, 94 deselected, 21 subtests passed`。
- 两条工作线合并后端回归：`382 passed, 1 skipped, 210 subtests passed in 2.18s`。
- `compileall`、public-guidance safety/seal 探针、`git diff --check`：PASS。
- 未修改 `backend/database.py`；不新增 DDL；guidance 不改变 Write/Bash/网络工具许可，仍由 Dream 专属确认链路处理。
- 本单元因执行环境 `.git` 目录只读而未提交；没有绕过权限，也没有执行归档。
