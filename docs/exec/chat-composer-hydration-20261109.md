<!-- [Input] Notion输入框等待记录、当前Chat组件、既有页面缓存与状态核对协议。 -->
<!-- [Output] 输入框挂载修复的范围、交付物、技术验证、构建44手机安装及剩余验收条件。 -->
<!-- [Sync] 2026-11-10: 当前工作区构建44完成iPhone覆盖安装与启动，原Application Support路径保留。 -->
<!-- [Pos] 2026-11-09已有对话输入框专项执行记录。 -->
# 已有对话输入框修复记录

## 需求与范围

来源：[重新进入对话后输入框等待记录](https://app.notion.com/p/40b30b7547c380f7ac22f85fdd2dbdd0#41130b7547c3804ba7c6c2df14744b00)。用户要求修复指定问题。

执行目标：核对当前源码和已有改动，定位输入框出现的等待条件，复用当前组件完成最小修复；同步产品规则、技术交互和目录说明，执行隔离浏览器及相邻合同验证。保留其他工作区改动和当前服务。真实账户、模型、数据库写入、原生打包安装与发布单独登记。

## 判断与交付物

`ChatViewContent` 原先以 `threadMessages === null` 分支替换整个 `ChatPanel`，输入框等待历史、运行状态及稳定复核完成。修复后目标 Thread 立即挂载 `ChatPanel`，阅读区域单独接收原加载、预览和失败反馈，原输入框贯穿读取与重试。读取期间沿原加载规则阻止发送，核对成功后开放原操作。

| 需求项 | 交付物 | 验收条件 |
| --- | --- | --- |
| 提前显示输入框 | `ChatView.tsx`、`ChatPanel.tsx` | messages与status分别未返回时均可编辑草稿。 |
| 保留编辑内容 | 原 `AIInputDock` 和 `useComposerDraft` | 加载、失败、重试及成功后保持输入节点与草稿。 |
| 沿用原对话行为 | 原发送、队列、确认和重连入口 | 核对期间零提交，成功后主动提交一次，Thread身份与resume保持。 |
| 产品与技术规则 | [消息阅读](../prd/chat/message-reading.md)、[历史分页与输入框挂载](../design/claude-agent/chat-history-keyset-pagination.md#已有对话的输入框挂载2026-11-09) | 桌面与窄屏骨架、正常/异常时序、状态和验证范围一致。 |

业务影响：共享 Thread 的读取期输入显示发生变化。Project、Episode、canonical Artifact、Run-private `.dream`、after-turn Hook、数据库/API投影和模型执行均处于本轮变更范围外。浏览器规格使用生产组件与显式合成HTTP响应，结论归技术验证。

## 验证记录

`python3 .agents/skills/ink-dream-playwright-qa/scripts/preflight.py` 退出0；安装的Playwright为1.62.1，5173空闲，8765已有监听。验证使用系统Chrome与规格自有临时Vite端口，现有后端保持。

当前回执目录：`frontend/output/chat-composer-hydration-20261109/`。验证工作目录为 `frontend/`。

| 命令 | 退出码 | 结果 |
| --- | --- | --- |
| `corepack pnpm exec playwright test --config=output/chat-composer-hydration-20261109/route.config.ts` | 0 | 精确4项通过，桌面1200px与窄屏390px分别覆盖正常及状态失败恢复。输入框在messages与status分别阻塞时可编辑，回车零提交，读取成功后原Thread主动发送一次。 |
| `corepack pnpm exec tsc --noEmit --pretty false --incremental --tsBuildInfoFile output/chat-composer-hydration-20261109/web.tsbuildinfo` | 0 | 完整Web类型检查通过，使用本轮独立增量文件。 |
| `corepack pnpm exec eslint app/_dream/components/chat/ChatView.tsx app/_dream/components/chat/ChatPanel.tsx e2e/chat-route-cache.spec.ts` | 0 | 0错误，保留ChatView原有1条Effect依赖警告。 |

首轮浏览器规格使用错误的按钮可访问名称 `Send`，当前名称为 `Send message`；原失败及中止回执保留在 `r1/`。验证配置曾递归匹配iOS构建目录的测试副本，修订为精确源码测试目录；副本结果退出产品统计。最终配置显式使用系统Chrome。

相邻重连和首次发送测试原先将导航或StrictMode触发的具名GET取消计入失败。恢复集合仅包含列表与首次发送Thread的inputs、scheduled-tasks路径。trace显示取消后存在更晚的同URL200读取。两个测试现对集合中的每个取消要求后续同URL、更高请求序号的200回执，其他网络错误继续失败。首次发送规格以读取恢复条件替换原250毫秒固定等待。

r3相邻批次中5项输入规格通过；重连规格在虚拟页面模块请求处超时，应用API请求为0，11项未执行。两个虚拟入口规格已分别配置独立Vite optimizer缓存，并关闭默认HTML入口扫描。r4重连1项通过；首次发送的页面、草稿和单次POST断言通过，inputs及scheduled-tasks的StrictMode取消进入原diagnostics。两项取消各有更晚的同URL200回执，现纳入上述严格恢复集合，后续定向回执待补充。前述失败归测试前置与诊断问题，原截图和trace保留。

文档检查覆盖9份本轮文档与目录合同、32个本地引用；3个新增Mermaid图在Chrome/Vite中实际解析通过，命令 `node output/chat-composer-hydration-20261109/mermaid-browser-check.mjs` 退出0。Node直接解析状态图遇到 `DOMPurify.addHook` 接口限制，原回执保留，图示语法结论采用浏览器结果。文档检查归技术验证。

## 最终技术验证结论

唯一规格合计21项通过：输入框及路由4项（r2）、原输入操作5项（r3）、重连1项（r4）、首次发送/停止/历史读取11项（r5）。失败、中止和未执行批次保留，重复执行退出唯一计数。

| 最终命令（工作目录为frontend） | 退出码 | 结果 |
| --- | --- | --- |
| `corepack pnpm exec playwright test --config=output/chat-composer-hydration-20261109/adjacent-r5.config.ts --max-failures=1` | 0 | ChatQueuedSend、ChatStopControl、ThreadSessionHydration合计11项通过；首次创建对话仅发送一次，原Stop及历史状态合同通过。 |
| `corepack pnpm exec eslint app/_dream/components/chat/__tests__/ChatQueuedSend.test.ts app/_dream/components/chat/__tests__/ThreadSessionHydration.test.ts app/_dream/components/chat/__tests__/ChatStopControl.test.ts` | 0 | 0错误、0警告；ChatDreamReconnect沿r4定向ESLint通过回执。 |

源码、产品规则、正常/异常业务图、状态及目录说明已同步。完整命令与各阶段回执保存于 `frontend/output/chat-composer-hydration-20261109/final-receipts.md`，r2至r5分别保留结果JSON、截图和trace。Web类型检查、产品静态检查与具名测试静态检查通过；本轮差异空白检查通过。

上述技术验证使用规格自有Vite端口、系统Chrome和合成HTTP边界。本轮未对8765服务执行启动、停止或修改，业务数据未写入；收尾只读检查未观察到8765监听，本轮自有测试进程均已退出。源码验证结束时，真实账户/模型、真机、打包安装和发布保持未执行状态；后续手机交付见下节。

## 2026-11-10 手机构建与安装

用户要求将本次修复打包到手机。当前工作区生成Kastention `0.1.0 (44)`，覆盖安装到已配对的iPhone 16，Bundle ID沿用 `com.inkmemory.mobile`。构建43完整包和本轮恢复副本均保留，源码中的四份私有配置摘要保持一致。

构建主机为16GiB内存的Mac，开始时memory-pressure free为42%，磁盘可用11GiB，无其他发布构建。macOS的Linux cgroup检查不适用。本轮串行执行Next单CPU、Metro单worker与Xcode单job；Node old space预算为2048MiB，各构建阶段20分钟期限。容量依据为同机构建43的成功峰值与本次更高可用比例，参数仅用于本轮。Next最大RSS为1566277632字节，结束时磁盘可用9.7GiB。

| 命令或阶段 | 退出码 | 结果 |
| --- | --- | --- |
| `python3 frontend/ios/build/chat-composer-iphone-20261110-b44/build.py` | 0 | 原prepare-next、完整Next构建、Web及Native类型、Xcode Release、来源复核全部通过；Next30.91秒，Xcode103.44秒。 |
| `python3 frontend/ios/build/chat-composer-iphone-20261110-b44/package.py` | 0 | 83个framework签名、333份Python源码、包内服务配置、profile和IPA校验通过；签名有效期至2026-11-16 23:21:34北京时间。 |
| `python3 frontend/ios/build/chat-composer-iphone-20261110-b44/install.py` | 0 | 同Bundle ID覆盖安装，设备读回0.1.0/44，普通启动PID6753。 |
| `xcrun devicectl device info processes --device <本轮设备>` | 0 | 后续快照确认本次启动的App进程继续运行。 |

构建输入包含579项Next运行源码和386项原生、后端及依赖输入，来源校验通过。包内ChatView、ChatPanel摘要分别匹配本次修复源码，编译资源包含 `CHAT_HISTORY_PENDING` 提交保护。线上Admin地址、原认证回调和MCP回调沿构建43配置；配置仅写入候选包，源配置写入0次，依赖安装0次，卸载0次，模型调用0次。

安装前Library元数据4103项、安装后4101项，原路径保留4097项，缺失6项均为SplashBoard缓存；Application Support原路径缺失0项。该结果证明所检查的目录路径保留，正文内容与完整真实对话业务验收分别登记。

制品与回执目录：`frontend/ios/build/chat-composer-iphone-20261110-b44/`，包含 `package-receipt.json`、`installation-receipt.json`、`process-verification.json`、`fix-package-verification.json`、来源摘要和各阶段命令。IPA为 `Kastention-0.1.0-44.ipa`，153686275字节，SHA-256为 `71793a490fbe60855c0fbabbb56be8e085c6da6c033d3d463f58fe11c0eaed3b`。

当前交付完成构建、签名、手机覆盖安装与普通启动。手机上的真实账户对话、真实模型及App Store发布未执行。

