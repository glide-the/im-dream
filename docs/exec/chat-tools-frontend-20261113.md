<!-- [Input] 用户工作台导航修正、Chat组件实现需求与独立设计归属要求。 -->
<!-- [Output] 范围、选型、交付物、实施状态及本轮验证回执。 -->
<!-- [Pos] Chat前端组件与资源入口本轮执行记录。 -->
<!-- [Sync] 2026-11-13: 独立登记Chat设计与资源页面职责；保留既有工作区改动。 -->

# Chat工具前端与工作台资源入口

## 优化后的任务定义

依据Notion最新前端需求和用户纠正，单独编写Chat模块的Agent选择、工具菜单和输入栏交互稿，补开发接口及正常／恢复时序；更新Web与App组件，工作台“远程资源链接”入口放在“设置”下方。复用原Thread、草稿、队列、认证、MCP配置与权限，保留现有未提交修改。音频工具为Low-Sensitivity，通过AskUserQuestion询问播放；播放器接线与真机播放验收独立。用户要求按源码核定范围：当前Chat缺少工作流选择与工具预设数据链路，菜单不展示这两项。多Agent控制、Web Bridge、IDENTITY／USER／HEARTBEAT退出本轮。

## 发现、定义与方案收敛

- 发现：读取最新Notion要求、现有输入栏、Agent选择、MCP列表／API及两端导航；外部参考核对至PromptInput和tool-select源码。
- 定义：Chat负责输入、选择与反馈；资源页负责连接生命周期；播放器负责用户回答后的媒体执行。
- 比较：完整移植外部ChatBot涉及会话和认证替换；选定保留当前业务边界的组件重构。
- 交付：Chat独立产品交互与开发稿；资源管理从音频稿拆出；历史正文、图示与改前文件保留。

## 交付物与状态

| 工作项 | 交付物 | 状态 |
| --- | --- | --- |
| Chat专项产品交互 | [agent-tool-composer](../prd/chat/agent-tool-composer.md) | 已编写，文档验证通过 |
| Chat开发合同 | [chat-agent-tool-composer](../design/claude-agent/chat-agent-tool-composer.md) | 已编写，文档与类型验证通过 |
| 资源管理归属 | [资源管理产品稿](../prd/resource-connections/mcp-tool-management.md)与独立前端接线 | 已拆分，历史完整保留 |
| 双端组件与导航 | 原AIInputDock、DeckChatSelector、MCP列表及工作台导航 | 源码已接线，定向隔离技术验证通过 |
| 验证 | 文档／类型／隔离真实组件验证 | 定向通过，真机／真实业务验收分列 |

证据目录：`frontend/output/chat-tools-20261113/`。preimage-manifest记录本轮改前文件；此前Nov12设计验证保留为历史证据。

## 实施明细

- 新增Chat双端工具菜单，服务搜索、原工具模式与版本化启停；本机音频能力未接通，保持不可选择。
- AIInputDock沿原发送和草稿状态接线；DeckChatSelector显示所选Agent图标。
- MCP资源列表改为卡片与实际计数，复用同一启停hook；Native资源页重新激活时读取当前配置。
- Web侧栏、窄屏与Native导航按设置／远程资源链接排列，兼容原资源路由。
- 原资源测试的标题与连接按钮选择器随新文案同步；真实账户／连接类spec本轮未执行。
- 浏览器夹具曾遗漏source路径排除、原Skill目录请求及storage配置请求；首次导航回归的回调预期漏列新资源路径。各次失败日志保留，修正后的定向验证通过。

## 源码范围核定

用户回复“你看源码”后核对参考WorkflowToolSelector／ToolPresets、当前buildClaudeChatRequest、useComposerDraft与Story Workspace WorkflowRun。Chat菜单采用当前已接入能力；兼容空字段保持，Dream工作流沿原业务入口。开发稿登记核对表，原临时假设已替换为源码依据。

## 本轮验证回执

| 命令／阶段 | 退出码 | 已观察结果 |
| --- | --- | --- |
| `pnpm exec tsc --noEmit --incremental false --pretty false` | 0 | Web类型检查通过，原tsbuildinfo保持 |
| `pnpm native:typecheck` | 0 | Native类型检查通过 |
| `pnpm exec playwright test --config=e2e/chat-tools.config.ts e2e/chat-tools.spec.ts more-navigation.spec.ts native-more-navigation.spec.ts native-mcp-resources.spec.ts --output=output/chat-tools-20261113/final-browser`，`INK_MORE_EVIDENCE_DIR=output/chat-tools-20261113/more` | 0 | 23项定向用例通过，包含原发送／停止、服务启停／409／503、资源卡片、Web与Native导航及原生资源管理的隔离呈现 |
| `node frontend/output/chat-tools-20261113/checks/check-docs.mjs` | 0 | Markdown清单、引用、历史原文与12幅Mermaid渲染通过 |

主代理复核了窄屏工具菜单与桌面资源卡片截图。主题夹具补齐原页面的背景token后，视觉截图另存，最终截图回执单列。上述检查采用生产组件与模拟HTTP，未连接真实服务。

完整命令与输出见[定向验证回执](../../frontend/output/chat-tools-20261113/checks/final-receipt.md)，此前停止阶段见[既有回归回执](../../frontend/output/chat-tools-20261113/checks/affected-regressions-receipt.md)。Playwright输出目录按本轮命名，Vite／Chrome自有进程已关闭；用户已有服务保持。

## 验收边界

Web组件交互、原Native资源／导航的隔离呈现和双端类型检查已取得技术回执。Native新工具面板的系统键盘、触摸与无障碍，iOS／Android真机、真实账户／MCP／模型、音频媒体预览与原生播放、后台计算、安装构建和部署均未执行。本轮源码修改限定前端，先前后端音频MCP改动与其他并行修改保持。

## 视觉复核与清单收敛

补齐测试页面主题背景后，390px／1200px的明暗4项视觉用例通过（exit 0），8张截图保留于本轮visual-final目录。主代理复核了实际窄屏工具菜单和深色资源卡片。

先前回归执行发现iOS构建源码副本被宽泛testMatch收录，历史102项通过计数包含生成副本。当前harness已排除ios／android／.next／output／node_modules，原输入栏使用canonical源码用例重新核对；生成副本计数不纳入当前功能验证数量。

视觉命令与截图见[视觉回执](../../frontend/output/chat-tools-20261113/checks/visual-final-receipt.md)。Native新工具面板的真机验证继续单列。
