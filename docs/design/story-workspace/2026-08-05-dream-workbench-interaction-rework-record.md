# Dream 工作台交互返工实施记录

> 日期：2026-08-05
> 范围：Dream 入口降噪、Dream Agent surface 分流、Story Workspace 导航/Decks/订阅/主题
> 前置设计：`design_008_dream-reentry-and-agent-workbench.md`

## 1. 结论

本轮已在工作区完成以下返工：

1. Dream 发起页删除过大的四步生命周期说明，只保留一句 stage 渐进写入说明。
2. 从进行中/最近 Dream 清单打开 `?run=` 后，工作台左上角提供返回 canonical Dream 工作台的入口。
3. Dream masthead 与 rail 显示同一安全 Dream Agent assistant/streaming 预览；Dream route 在右栏内打开唯一 inline panel，execution route 打开悬浮 dialog。
4. inline panel 和 execution dialog 都有稳定 `aria-controls` 目标，收起后归还焦点；dialog 的执行中/已完成状态使用图标+文本。
5. Story Workspace 主导航改为 Dream / Decks / 订阅。Decks 在内部 `/story-workspace/decks` route 中直接显示 App 注入的既有 `DeckManager`，StoryWorkspaceLayout/sidebar 不卸载。
6. 订阅页为 Free / Dream / is Dreaming 三列静态说明；未虚构计费 API 或权限改动。
7. Story Workspace footer 在设置上方增加主题切换，复用 `utils/theme.ts` 的唯一 owner，没有新建 localStorage key。

## 2. 实现边界

| 区域 | 主要文件 | 边界 |
|---|---|---|
| Dream 入口/工作台 | `frontend/src/pages/story-workspace/StoryWorkspaceDreamLaunch.tsx`、`StoryWorkspaceDreamPage.tsx`、`.css` | 不挂 ChatView；Agent 消息不修改 stage/local draft |
| Dream inline Agent | `frontend/src/components/story-workspace/dream/StoryWorkspaceDreamAgentPanel.tsx`、`StoryWorkspaceDreamAgentRail.tsx` | 唯一 panel DOM；同 run view model；稳定 controls ID |
| Execution Agent | `frontend/src/pages/story-workspace/StoryWorkspaceExecutionPage.tsx`、`.css`、`StoryWorkspaceDreamAgentDialog.tsx` | 不替换 execution 内容；悬浮 dialog/Escape/焦点归还 |
| 侧栏/内部 Decks | `StoryWorkspaceSidebar.tsx`、`StoryWorkspaceLayout.css`、`router/story-workspace.tsx`、`storyWorkspacePath.ts`、`App.tsx` | `/story-workspace/decks` 内组合同一份已配置 DeckManager；Router 不接管 Deck owner |
| 订阅 | `StoryWorkspaceSubscriptionPage.tsx`、`.css`、`pages/story-workspace/index.ts` | 静态产品说明，无 billing transport |
| 设计 | `docs/design/story-workspace/design_008_dream-reentry-and-agent-workbench.md` | 已修订 surface 分流、导航、Decks 组合与 theme owner |

## 3. Red / Green 与评审

| 轮次 | Red | Green / 结果 |
|---|---|---|
| R1 Dream/Execution | 14 项中 5 项失败；追加 masthead 预览后仍 1 项失败 | 实现入口降噪、返回、inline panel、execution dialog、状态图标；聚焦 15 passed |
| R2 导航/订阅 | 新 sidebar/route/subscription 合同失败 | Dream/Decks/订阅与静态三列页 Green |
| R1a 无障碍复审返工 | 12 项中 2 项失败：Dream panel 与 execution dialog 缺少稳定 controls 合同 | 12 passed；唯一 panel ID、hidden lifecycle、焦点归还 Green |
| R2a 主题 | 侧栏缺少 `getTheme/onThemeChange/toggleTheme` 时失败 | 主题按钮位于设置上方，4 passed |
| R2b 工作台内 Decks | 17 项中 2 项失败：缺内部 decks route/组合合同 | `/story-workspace/decks` + `decksContent` ReactNode 组合 Green，17 passed |
| R2c 过时测试返工 | 独立复审实测 33 项中 1 项失败：旧测试错误禁止任意 ReactNode | 改为禁止 `dreamContent/ChatView/ChatWidgetUI`，允许 route-scoped `decksContent`；最终全部本仓前端 Node seam 120 passed |

独立评审历经两次 `NEEDS_REVISION`：第一次发现 `aria-controls` 目标断裂与运行时证据缺位；第二次发现 R2b 后过时 ReactNode 测试失败。两个生产/测试问题均已返工。真实浏览器仍受第 5 节环境限制，不列为运行时 PASS。

## 4. 最终自动化门禁

| 命令 | 结果 |
|---|---|
| `find src -path '*/__tests__/*.test.ts' ... playwright test --workers=1` | `120 passed (1.8s)` |
| `npx tsc -b` | PASS |
| `npx vite build` | PASS；仅既有 dynamic-import/chunk-size 警告 |
| 本轮改动 TS/TSX 定向 ESLint | 0 error；`App.tsx` 17 条既有 hooks warning |
| `git diff --check` | PASS |
| `git diff -- backend/database.py` | 无输出 |
| Dream/Execution/component `ChatView/ChatWidgetUI/dreamContent` 扫描 | 无生产挂载命中 |

一次将 CSS 路径传入 ESLint 产生“File ignored because no matching configuration” warning；它不是代码失败，不计入 TS/TSX 定向门禁。

## 5. 真实浏览器边界

按 `playwright` 技能先执行 prerequisite 和 wrapper：

1. `npx` 存在；
2. `/Users/dmeck/.codex/skills/playwright/scripts/playwright_cli.sh --help` 请求 `registry.npmjs.org/@playwright/mcp` 时两次 `ENOTFOUND`；
3. 改用仓库已安装 Playwright/Chromium 发起最小 browser launch，Chromium PID 创建后报 `FATAL ... mach_port_rendezvous_mac.cc:159 ... Permission denied (1100)`；
4. 15 秒后主动终止，exit 124，临时目录清理完成。

因此本轮没有生成新 screenshot/trace，下列行为仍是 **未验证**：真实 DOM 下 Dream 窄屏唯一 panel、execution Escape 归焦、Decks 内部路由后退/前进、订阅窄屏单列与主题按钮的真实点击。源码 seam 和 TypeScript/build 通过不代表真实浏览器验收。

## 6. Git、工作区与边界声明

- `.git` 在当前托管权限中为只读；本轮无法形成 R1/R2 独立 commit，改动保留为未暂存工作区文件。
- 本轮没有修改 `backend/database.py`，没有 DDL，没有归档操作。
- 没有关闭用户原有服务；浏览器启动超时后已执行 kill/临时目录清理，无本轮遗留 browser PID。
- 本轮没有修改、回滚或暂存 Claude 子代理与 Chat sidebar 等其他工作线文件。
