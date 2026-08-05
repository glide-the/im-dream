# Dream Agent 信息层级与安全过程展示返工实施记录

日期：2026-08-05

设计 owner：`design_008_dream-reentry-and-agent-workbench.md`

范围：Dream rail、Dream inline panel / execution dialog 的共享消息渲染、Dream run 重进标题与窄屏可用性。

## 1. 本轮结论

本轮按“重复信息消除 → Deck 元信息 disclosure → 安全过程投影 → 独立复审返工 → 真实浏览器验收”完成：

1. masthead 继续拥有折叠态实时回复预览；rail 不再重复最新回复或“回复会显示在这里”的空态说明，只保留 Deck 元信息、Dream Agent 状态和 stage revisions。
2. rail 中的 Deck 名称改为 Dream 专属 button/popover，交互参考 `PluginReceiptBadge`，但不复用 Chat thread/plugin polling。
3. inline panel 移除重复 header；返回 Dream 内容成为独立控制。Panel 与 execution dialog 共用 Dream 专属消息列表。
4. 消息列表按原始 part 顺序显示安全 assistant/user 文本与可折叠 activity。activity 仅有固定 category、label、status 和不透明 ID，不暴露 tool name、参数、输出、错误、命令、路径或内部任务 envelope。
5. 最近/进行中列表标题继续使用服务端持久化的创作目标前缀，不从浏览器本地状态推导。
6. 窄屏侧栏固定收敛为 72px；Dream Agent section 打开时隐藏属于内容 section 的确认栏，确保消息输入和发送操作不被覆盖。

## 2. 文件与合同证据

| 结论 | 证据 |
|---|---|
| rail 不重复消息预览/空态，只显示 Deck metadata、status、stage | `frontend/src/components/story-workspace/dream/StoryWorkspaceDreamAgentRail.tsx:26-45` |
| Deck metadata 是 Dream 专属 disclosure，打开后聚焦 dialog，Escape 关闭并归还焦点 | `frontend/src/components/story-workspace/dream/StoryWorkspaceDreamDeckMetadata.tsx:23-90` |
| Panel 无重复 header，并保留返回、消息、前往最新、工具确认和留言 | `frontend/src/components/story-workspace/dream/StoryWorkspaceDreamAgentPanel.tsx:83-139` |
| 安全文本与 activity 按序渲染，activity 默认折叠 | `frontend/src/components/story-workspace/dream/StoryWorkspaceDreamAgentMessageList.tsx:24-95` |
| activity 状态变化参与自动跟随 revision，并经 500ms `aria-live` 聚合播报 | `frontend/src/components/story-workspace/dream/useStoryWorkspaceDreamAgentScroll.ts:34-118,150-220` |
| Panel 打开后内容确认栏不渲染 | `frontend/src/pages/story-workspace/StoryWorkspaceDreamPage.tsx:589-617` |
| 767px 以下全局侧栏为 72px 可访问图标轨道 | `frontend/src/components/story-workspace/layout/StoryWorkspaceLayout.css:926-970` |
| 最近/进行中标题使用 `goalPrefix` | `frontend/src/pages/story-workspace/StoryWorkspaceDreamLaunch.tsx:35-49` |
| 服务端 snapshot 文本脱敏和 activity 固定投影 | `backend/services/story_workspace/dream_agent_message_service.py:371-407,424-543` |
| confirmation resolved 与 activity finished 使用稳定子游标 | `backend/services/story_workspace/dream_agent_message_service.py:1430-1468` |
| SSE 文本采用跨帧 guard，敏感内容只输出固定替代文案 | `backend/services/story_workspace/dream_agent_message_service.py:1470-1535` |

## 3. 实现单元、Red / Green、评审与提交

| 单元 | Red | Green | 独立评审 | commit |
|---|---|---|---|---|
| U1 Dream Deck 元信息 disclosure | 结构测试先要求 rail 不再拥有消息文案，并要求 `aria-haspopup/expanded/controls` | 新增 Dream 专属 metadata button/popover 与样式 | 首轮发现打开后焦点未进入 dialog；返工补齐 focus/Escape return 后通过 | `fec641f`, `3d2dcf8` |
| U2 信息层级设计 owner | 设计核对发现 masthead、rail、panel 存在重复 owner | design_008 明确 masthead/rail/panel 各自职责 | 设计评审确认不挂载 ChatView/ChatPanel | `013632b` |
| U3 安全 activity 后端与 adapter | 后端/Node seam 先要求 ordered content、固定分类、严格解析和 SSE 去重 | snapshot + SSE 投影 activity，前端 adapter 严格消费 | 首轮发现公开文本可跨帧泄漏、confirmation activity 停留 running；返工后动态探针通过 | `4794311`, `c67b3c3` |
| U4 Dream 专属折叠过程 UI | 页面结构测试先要求 Panel 无 header、过程默认折叠、不得挂 ChatPanel/ChatView | 新增共享 Dream message list，Panel/Dialog 共用；固定 icon/status | 独立评审确认 DOM 不含 raw tool fields | `a167af0` |
| U5 activity 更新后的跟随与播报 | seam 测试先覆盖同 ID 状态变更和 activity-only 更新 | content revision 纳入 activity status；500ms 聚合播报 | 首轮发现 activity-only 更新不滚动/不播报；返工后通过 | `ee7b4c3` |
| U6 窄屏工作面 | 响应式测试与 390/320 浏览器断言先暴露固定桌面侧栏挤压和确认栏遮挡 | 72px 图标侧栏；Agent section 打开时不渲染内容确认栏 | 390px 与 320px 均无文档级横向溢出，发送按钮可见 | `b59fc85`, `1e6e157` |

## 4. 双阶段独立评审

### 4.1 第一阶段：不通过

独立评审识别五项阻断：

- assistant 文本的 snapshot / SSE 缺少统一敏感内容策略；跨 frame 的 secret、绝对用户路径、system/hidden marker 可能在完整匹配前泄漏；
- confirmation resolved 后对应 activity 可能停留 `running`；
- 仅 activity 状态变化时不会触发滚动与 `aria-live`；
- metadata dialog 打开时没有明确初始焦点；
- 窄屏仍受 240px 桌面侧栏和 sticky confirmation footer 挤压。

原实现单元完成返工，没有新增业务失败、人工重试、驳回或归档状态。

### 4.2 第二阶段：通过

复审结论：无 P1/P2 阻断项。动态安全探针确认 hidden/system/key/path 输入均为 `raw=False, redacted=True`；普通中文文本仍能在 committed 前产生安全 delta。confirmation 的 `:0` resolved 与 `:1` activity finished 可稳定 replay，activity-only follow/a11y、metadata focus、窄屏布局与 Dream 内容确认栏边界均通过。

## 5. 测试结果

| 验证 | 结果 |
|---|---|
| 后端 Dream Agent / re-entry 聚焦 pytest | `32 passed, 33 subtests passed in 1.28s` |
| 前端 Dream Agent/activity/layout Node seam | 聚焦套件通过；独立复审合计 `50 passed` |
| 窄屏响应式 seam | `4 passed` |
| TypeScript | `npx tsc -b`，exit 0 |
| ESLint | 覆盖本轮全部前端改动文件，exit 0；最终命令曾误写一个测试文件名，修正为 `StoryWorkspaceResponsiveLayout.test.ts` 后通过 |
| 源码边界 | Dream UI 未挂载 `ChatView`、`ChatPanel`、`ChatMessageList` 或通用 tool renderer |

## 6. 真实浏览器验收

使用真实 Chromium 验证实际 React DOM、样式、焦点和 viewport；API 使用确定性 mock，因此本项只证明 UI 合同，不冒充真实 drama-forge Agent/run/database 链路。

命令：

```text
npx playwright test e2e/.tmp-dream-agent-activity-ui.spec.ts --reporter=line --workers=1 --trace=on --output=../output/playwright/dream-agent-activity-20260805/pw-results
```

结果：`1 passed (3.8s)`。

证据：

- re-entry 创作目标前缀：`output/playwright/dream-agent-activity-20260805/reentry.png`
- 桌面 rail / Panel / activity disclosure：`output/playwright/dream-agent-activity-20260805/desktop.png`
- 390px 窄屏侧栏、输入与无溢出：`output/playwright/dream-agent-activity-20260805/narrow.png`
- trace：`output/playwright/dream-agent-activity-20260805/trace.zip`
- mock run：`run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`
- mock thread：`thread-dream-activity`

浏览器断言覆盖：re-entry 标题为创作目标前缀；Panel 无重复 header；metadata dialog 打开/关闭和焦点归还；activity 默认折叠且可展开；DOM 不出现隐藏内容；390px/320px 无文档级横向溢出；Agent section 中留言和发送可见，内容确认栏不出现。

## 7. 按设计实现与诚实遗留

| 项目 | 状态 |
|---|---|
| Rail / Panel 去重、Deck metadata、折叠 activity、安全文本、自动跟随、窄屏 | 已按 design_008 实现并验证 |
| 最近/进行中使用创作目标前缀 | 已存在并重新验证，没有为本轮重复改写 owner |
| Chat 相同的 raw tool card / 推理过程 | 明确不实现；只借鉴 disclosure 与滚动交互，Dream 只消费安全投影 |
| 真实 drama-forge Deck 的离开/恢复、同 thread 回答、数据库计数 | 本轮未重跑；不能由 mock 浏览器证据替代，沿用上一轮实施记录中的真实链路状态 |

## 8. 工作区与资源清理

- 本轮提交均只包含对应实现单元文件；未 stage、未提交其他工作线的脏文件。
- `backend/database.py` 的既有 diff 未触碰，本轮没有增加 DDL。
- 本轮启动的 Vite 5175 服务在验收后关闭；用户原有 5173/8765 服务不处理。
- 未执行任何归档操作。
