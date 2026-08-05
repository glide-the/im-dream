# Dream 可恢复入口与 Dream Agent 工作台：任务二设计实施记录

> 日期：2026-08-05  
> 任务：基于任务一裁决完成独立交互设计稿与独立评审  
> 设计稿：`docs/design/story-workspace/design_008_dream-reentry-and-agent-workbench.md`

## 1. 输入

本轮直接采用任务一的七项固定裁决，不重新建立平行 owner：

1. `/story-workspace/dream` 是唯一 canonical re-entry；`?run=` 只定位同页 run。
2. actor-scoped Dream run 聚合承担持久发现，多 run 由用户明确选择。
3. Dream route 移除顶部完整 WorkflowContextBar，右侧 rail 成为上下文/status owner。
4. Dream 消息使用服务端 allowlist 的 snapshot + filtered increment + terminal reconciliation。
5. 悬浮层使用 Dream 专属 adapter/view model/component，不挂载 ChatView。
6. `.dream` stage、持久消息、EventBus、隐藏 thread 与 local draft 各有唯一 truth owner。
7. 不扩展驳回、业务失败、人工重试或归档状态。

输入裁决及其完整证据见 `docs/design/story-workspace/2026-08-05-dream-reentry-agent-workbench-task1-problem-decision-record.md:1-347`。

## 2. 交付内容

### 2.1 设计稿

新增 `design_008_dream-reentry-and-agent-workbench.md`，包含：

- 背景、目标、非目标与 canonical re-entry IA（`:9-74`）；
- Dream 首页、多 run、模块关系与右侧区域（`:75-157`）；
- WorkflowContextBar 迁移、收起/展开交互（`:158-230`）；
- Agent snapshot、filtered SSE、重连去重与恢复时序（`:231-357`）；
- 所有权/Deck binding、可信发送与同 thread 对话（`:358-452`）；
- truth ownership、页面文案、响应式与无障碍（`:453-532`）；
- 桌面/窄屏线框（`:533-592`）；
- API/组件边界、异常边界、非目标与验收（`:593-698`）；
- DEC-034～041、证据索引与变更历史（`:699-725`）。

图示共七类：

1. 业务模块关系图（`design_008:105-132`）；
2. 消息 snapshot + increment 时序图（`:280-310`）；
3. 退出并重新进入时序图（`:322-357`）；
4. 打开悬浮层并继续对话时序图（`:425-451`）；
5. truth ownership 图（`:453-484`）；
6. 桌面端线框（`:533-561`）；
7. 窄屏线框（`:563-591`）。

### 2.2 术语表

更新 canonical 术语表：

- “Dream 可恢复入口”（`docs/architecture/术语表.md:65`）；
- “Dream Agent 工作台交互层”（同文件 `:78`）；
- 登记 design_008 的唯一 owner 范围（同文件 `:112`）。

术语继续使用“物理映射”；用户可见主体统一称为 Dream Agent。隐藏 Agent thread 只出现在可信绑定与技术时序中，不成为 Chat 产品入口。

## 3. UI Design v2 对齐

设计稿明确使用 Warm Canvas `#F6EFE5`、Paper Cream `#FFFAF2`，以排版、留白和细分隔线建立层级；静态 rail 不使用重卡片阴影，dialog 只以一层克制边界/阴影表达悬浮（`design_008:507-592`）。依据是既有 design_007 对 PDF 第 4～5 页的视觉记录（`docs/design/story-workspace/design_007_dream-business-module-interaction.md:340-348`）。

## 4. 合同可实现性

- 后端 DTO 继续唯一归 `backend/story_workspace/contracts.py`，前端 DTO 继续唯一归 `frontend/src/hooks/story-workspace/contracts.ts`（`design_008:593-637`）。
- 不修改 `backend/database.py`，消息幂等复用确定性 message ID/既有持久 metadata 与 run/thread 级 claim，不新增 DDL（`design_008:411-423,605`）。
- 通用 Claude Agent message/stream 只作底层来源；Dream adapter 在服务端过滤 reasoning/tool/debug 内容（`design_008:231-320`）。
- `.dream` stage 更新继续由既有 Dream files REST polling 驱动（`design_008:486-492`）。

## 5. 独立设计评审

评审者：独立子代理 `/root/task2_design_review`  
评审方式：只读对照任务一、术语表、design_006、design_007、layout design 与用户验收要求。  
评审状态：**PASS**。

首轮评审为 `NEEDS_REVISION`，发现：initial live turn 可能错投影为 continuing；自由输入可能绕过一次确认；持久 claim 未闭合；cursor 前后不一致；truth 图把 EventBus 错画为 writer 调用者。修订见 `design_008:81-86,219-229,258-320,411-423,453-484`。

第一次复审继续发现两项中等问题：任务一残留 snapshot cursor 表述；不同 idempotency key 可能在 live status 建立前并发。最终修订为“首次无 cursor 的 active-turn replay”以及同一 `BEGIN IMMEDIATE` 中的 run/thread pending/fresh-dispatch guard（Task 1 `:171-191`；`design_008:411-423`）。

第二次复审结论为 PASS：确认原五项与追加两项均已闭合，且没有引入新矛盾。评审同时确认 Dream 独立模块、一次确认门禁、安全消息过滤、`.dream` truth、UI Design v2、七类图示、响应式/无障碍和非目标边界保持完整。

## 6. 本轮文件边界

本轮只改设计文档：

- `docs/design/story-workspace/design_008_dream-reentry-and-agent-workbench.md`；
- `docs/design/story-workspace/2026-08-05-dream-reentry-agent-workbench-task2-design-record.md`；
- `docs/design/story-workspace/2026-08-05-dream-reentry-agent-workbench-task1-problem-decision-record.md`（仅同步修正评审发现的 lifecycle、首次 replay 与发送门禁合同）；
- `docs/architecture/术语表.md`。

任务一记录仍作为前置交付存在。本轮没有修改生产代码、数据库 schema 或插件制品，没有执行归档操作。
