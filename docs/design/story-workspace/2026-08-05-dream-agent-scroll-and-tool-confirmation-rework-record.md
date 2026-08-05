# Dream Agent 自动跟随与工具确认返工实施记录

> 日期：2026-08-05  
> 设计输入：`design_008_dream-reentry-and-agent-workbench.md`  
> 范围：Dream Agent 消息自动跟随、“前往最新消息”、Dream 专属工具确认、重连与确认安全边界。

## 1. 实施结论

Dream 页面内嵌 Agent panel 与 execution 页面悬浮 dialog 已共享同一套 Dream 专属消息滚动规则：首次打开和 near-bottom 阅读时跟随增量；用户普通上滚后保留阅读位置并显示“前往最新消息”；用户成功发送属于显式继续对话，必须保持跟随直到新消息真正抵达底部。

Dream Agent 的 allowlist 工具确认在原输入区内显示为编辑校样条，不挂载 ChatView 或 Chat 的确认 dock。连续确认按 `toolCallId` FIFO 排队；AskUser 只把服务端生成的不透明 `qN` 暴露给浏览器，提交后由服务端映射回 runner 问题文本。敏感文本和危险命令 fail closed；规范 `run_<32hex>` 业务标识不会被高熵启发式误杀。

同一 turn 的重叠 SSE 订阅使用 actor/run/thread/turn 租约计数，单个标签页或旧重连连接关闭不会提前删除另一订阅仍在展示的确认；最后一个订阅释放或真实 terminal 时清理。

## 2. 组件与合同边界

| 边界 | 实现 | 约束 |
|---|---|---|
| 滚动 owner | `useStoryWorkspaceDreamAgentScroll.ts` | 只滚动 Dream history element；不调用页面级滚动或 `scrollIntoView` |
| Dream surfaces | `StoryWorkspaceDreamAgentPanel.tsx`、`StoryWorkspaceDreamAgentDialog.tsx` | panel/dialog 复用 Dream hook，不复用 ChatView；dialog 支持 Escape 与焦点归还 |
| 确认 UI | `StoryWorkspaceDreamToolConfirmation.tsx` | 内嵌 `region`；替换 composer；只渲染公开 projection |
| 前端 adapter | `useStoryWorkspaceDreamAgent.ts` | snapshot + SSE；FIFO；稳定连接 10 秒后重置退避；发送/确认只带 run-scoped 公开 payload |
| 后端安全 adapter | `dream_agent_message_service.py` | actor/run/thread/turn/toolCall 可信绑定、敏感投影、`qN` 映射、订阅租约 |
| `.dream` truth | Dream files REST adapter | 本轮未改变；Agent message/confirmation 不写 stage revision 或 local draft |

## 3. Red / Green / 复审记录

| 单元 | Red | Green | 独立复审 |
|---|---|---|---|
| S1 自动跟随 | 缺少 history-only/reduced-motion seam；浏览器发送后因平滑滚动中间事件丢失 follow，30 秒超时 | 聚焦 `18 passed`；浏览器发送后距底部 `3px` | history-only、120px 阈值、普通上滚保留、发送强制 follow 已闭合 |
| S2 工具确认 UI/adapter | 缺 allowlist confirmation、FIFO、错误可见性、窄屏 inert、UTF-8 字节限制与稳定退避 | 前端全量 Node seam `152 passed`；TypeScript/ESLint 通过 | 两轮 NEEDS_REVISION 后闭合 FIFO、region、焦点、重连和 payload 边界 |
| S3 后端安全投影 | 最终攻击样本 Red `7 failed`：五类危险命令漏放、规范 run ID 误杀、双订阅误清 registry | 聚焦 `27 passed, 33 subtests passed`；相关全量 `57 passed, 48 subtests passed` | PASS：独立实测 PUBLIC/BLOCKED、租约 `2→1→0`、terminal 清理与额外 release 不产生负计数 |

## 4. Commit 记录

| Commit | 内容 |
|---|---|
| `10aeb37`、`90cebba`、`6e94617` | 自动跟随、history-only 滚动、发送期间保持 follow |
| `a6746c2`、`b730013` | Dream surfaces 接入工具确认与 FIFO |
| `842e512`、`c629aea`、`af9df6b` | answers 校验、`qN` 映射、敏感投影与 registry 安全加固 |
| `b25bcc5` | 连接稳定 10 秒后重置指数退避 |
| `09b1f1d` | 危险命令/run ID 边界与重叠 SSE 订阅租约 |

过程说明：`8c34d48` 曾一次吸收 39 个文件，包含本功能的初始确认实现及同一工作区已有的其他交互改动；`ea9984b` 因此成为空提交。本轮未改写历史，后续返工均使用窄范围独立提交，最终交付如实保留该记录。

## 5. 最终自动化与浏览器证据

| 门禁 | 结果 |
|---|---|
| Dream/re-entry/backend 组合 pytest | `173 passed, 88 subtests passed in 8.53s` |
| 全部前端 Playwright Node seam | `152 passed (3.5s)` |
| `npx tsc -b` | PASS |
| 改动前端文件 ESLint | PASS |
| Chromium 真实 DOM 交互脚本 | PASS；run `run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`，thread `thread-qa-safe-binding` |
| 自动跟随 | 首次距底部 `1px`；点击最新后 `4px`；发送并恢复回复后 `3px` |
| 工具确认 | AskUser + Write 共 2 次提交，各一次；payload 不含 thread/Deck/raw input |
| 390px 窄屏 | dialog `left=8`、`right=382`、document `scrollWidth=390` |

浏览器产物：

- `output/playwright/dream-agent-interaction-20260805/evidence.json`
- `01-scroll-to-latest.png`
- `02-send-followed-latest.png`
- `03-tool-confirmation-wide.png`
- `04-tool-confirmation-narrow.png`
- `dream-agent-interaction-trace.zip`

## 6. 诚实边界

本次 Chromium 脚本运行的是仓库真实 App、真实路由、真实 Dream panel/dialog DOM 与真实浏览器布局，但在浏览器网络层 mock 了 API/SSE。因此它证明滚动、点击、焦点、FIFO、payload 形状和宽窄屏行为，不证明真实 Claude 模型或真实后端授权。后端安全投影、可信绑定、并发确认和 registry 生命周期由 pytest 独立证明；两类证据不可相互替代。

本轮没有修改 `backend/database.py`，没有 DDL，没有让 Agent message 取得 `.dream` stage truth ownership，没有挂载 ChatView，也没有增加业务驳回、失败、人工重试或归档状态。

## 7. 工作区与终端

其他工作线的设置、订阅、侧栏、Dream launch/re-entry 测试和截图改动保持未提交或原状；本轮没有回滚、覆盖或夹带这些文件。测试完成后只关闭本轮启动的 Vite/浏览器进程，用户原有 `127.0.0.1:8765` 后端保持运行。

明确声明：**未执行归档操作。**
