# Chat 工具确认重连恢复实施记录

日期：2026-08-06

## 1. 问题与裁决

现象是已同意的 Chat Agent 工具确认在重连后再次出现；重复点击时后端返回
`No pending confirmation for tool_call_id=...`。根因不是后端仍在等待确认，而是
EventBus 重放旧 `tool-approval-request` 后，前端缺少“该 call 已处理”的精确终态，
同时缺少以 SSE EOF 和本地 turn 代次保护的持久化历史恢复。

最终裁决：

- 前端在当前 thread 内保存精确 `tool_call_id` tombstone；
- 后端以所有权校验保护确认入口；
- owned-but-settled 返回类型化 409，供前端安全地执行幂等收敛；
- 仅在 SSE EOF 或 Stop 完成后请求权威快照，并以 thread、reconnect nonce、
  turn generation checkpoint 拒绝迟到响应；
- 普通 404、权限、网络或畸形响应均不得被当作“已确认”。

## 2. Prompt Architect 校准

### Optimized Prompt

诊断并修复通用 Chat 页面中已完成 Agent 工具确认被 SSE 重连历史帧重新展示的
问题。以 `tool_call_id` 为幂等键，建立前后端一致的终态合同：校验 thread 所有权，
区分越权、仍待确认与已处理，保证重复确认只关闭精确的过期 UI，不制造工具输出，
并让持久化历史在 SSE EOF 后安全覆盖重放产生的临时状态。采用 Red/Green 测试覆盖
所有权、类型化冲突、精确 ID、重连快照与单次 dispatch，最后以真实 Chromium
验证确认面板消失、输入框恢复且无重复请求。

### Optional Enhancers

- 在未来的真实长时工具执行回归中保留服务端事件游标与消息快照计数证据。
- 为 EventBus 引入持久化事件 ID 后，可进一步把 replay 截止点作为传输层优化；
  但不能取代本次 UI 幂等与权限合同。

## 3. Red / Green 记录

### Red

- 后端新增三条路由测试后，原实现分别暴露：未校验 thread 所有权、settled 与
  missing 都返回 404、成功路径没有读取 thread。
- 前端首次引入响应解释器、精确 ID 与历史快照判定测试时，分别因接口缺失、
  mismatch ID 被误判终态、恢复 helper 缺失而失败。
- 首轮独立评审发现迟到快照可覆盖新 turn、editor-write 合同不一致、Dock 身份与
  快速双触发问题；第二轮发现 finish 早于持久化、Stop 未应用快照、折叠徽标仍显示。
  两轮均先补失败断言或可复现检查，再进入修复。

### Green

- `backend/tests/test_server_claude_agent.py`：`48 passed`。
- `frontend/src/components/chat/__tests__/ToolConfirmationRecovery.test.ts`：
  `4 passed`，包含 finish 到达后流仍未 EOF 的时序测试。
- 改动前端文件 ESLint：通过。
- 改动前端文件定向 TypeScript：通过。
- `npx tsc -b`：通过。

## 4. 浏览器验收

使用现有用户 Vite 服务与真实 Chromium，针对确定性 API mock 注入一个历史重放的
`tool-approval-request`，确认接口返回精确
`409 TOOL_CONFIRMATION_NOT_PENDING`。验证结果：

- 确认面板最初显示 `Compute sha256 project slug`；
- 快速双击同意只发送一次、且携带精确 thread/tool ID；
- 类型化 409 后确认面板消失；
- Chat 输入框恢复；
- Playwright：`1 passed`。

证据：

- 截图：`output/playwright/chat-tool-confirmation-recovery-20260806.png`
- trace：`output/playwright/chat-tool-confirmation-recovery-20260806-trace.zip`

限制说明：本次浏览器验收使用确定性 API mock 复现服务端 settled 合同，不声称重新
执行了用户报告的生产 run。后端路由与 runtime 边界由 pytest 独立覆盖。

## 5. 独立评审与边界

独立评审检查并发、权限、错误分类与回归风险。初评和第一次复审均返回 FAIL，
问题修正后最终复审为 **PASS（P0/P1/P2 清零）**。
本轮没有修改 Agent confirmation store 的生命周期，也没有把 404 或权限错误降级为
成功；没有覆盖、回滚或夹带 Story Workspace 其他工作线修改。

本轮未启动后端或 Vite 服务，因此不关闭用户原有的 5173/8765 进程；仅启动了短期
Playwright Chromium，测试结束后已自动退出。未执行任何归档操作。
