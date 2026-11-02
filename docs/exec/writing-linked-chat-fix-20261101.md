<!-- [Sync] 2026-11-01: 移动应用PRD迁至docs/prd/mobile-app/mobile-app.md，更新现行引用，保留历史回执。 -->
<!-- [Input] 用户后续修复授权、原只读诊断、Web写作关联规则及现有Native发送入口。 -->
<!-- [Output] 入口与保存上下文修复、技术回执、评审及候选采用边界。 -->
<!-- [Pos] 写作记录关联对话修复执行记录；当前产品与时序归原PRD和写作设计。 -->

# 写作记录关联对话修复

## 范围与交付

用户在只读诊断完成后明确要求修复。当前阶段授权覆盖本项源码、相关回归和文档，原[只读诊断](writing-linked-chat-review-20261101.md)保留当时记录。实施从干净`ios-native`工作区、HEAD `f40a9cfae8e85489a5354ccce7987f0a6a50f57d`开始。执行依据由该修复指令与已确认差异整理一次，范围限定为移动入口、发送时笔记上下文和失效请求隔离。

交付归[现行写作设计](../design/multi-platform/writing-mobile-layout.md#写作记录与关联对话)与[原产品需求](../prd/mobile-app/mobile-app.md#写作记录与关联对话)。[实施前设计](../design/multi-platform/history/writing-linked-chat-before-fix-20261101.md)保留原正文和图示，归档相对引用已调整。

保留原卡片threadId、Voice Thread复用、手动建议writingThreadId与Calendar任务入口。主Chat隐藏和侧会话覆盖期间保留原输入实例；关闭侧会话释放其组件内草稿。新增每笔记唯一Thread、跨关闭草稿存储、后台同步、HTTP接口、数据库Schema、依赖和服务地址变更均为零。

## 当前实现

| 工作项 | 文件与行为 |
| --- | --- |
| 移动卡片入口 | `App.tsx`将现有mobileWriting传给`ChatWidgetUI`，移动展开且有threadId的原按钮直接可见、可点；桌面hover和折叠/缺关联条件保持 |
| 原笔记绑定 | Writing卡片open-thread附带editorSessionId；`WritingView`创建绑定当时documentId与Session的准备回调，`MoreNavigator`原样透传；侧Business以Session/Thread区分身份 |
| 按次准备 | 原WritingDocument state/event承载contextRequest和chat-context/error；`WritingContextRequests`只持有一个在途等待，拒绝其他document/Session/request的回执 |
| 生产保存 | 原`ensureSessionPersistedForAgent`可接收目标Session，保存当前engine快照并复核等待期间的Session与内容；无参Web调用保持原行为。App保存成功且快照签名一致后返回原EditorState |
| 原发送入口 | `useNativeChatThread.submitMessage`在Thread创建、提交登记及原POST前等待可选上下文；原builder投影editor_state；普通主Chat与任务侧会话不增加笔记上下文 |
| 失败与取消 | 保存失败、记录变化、超时或文档失效拒绝准备，原`useComposerDraft`恢复输入。更换读取epoch或卸载取消准备AbortSignal；原重试只读取，不重发消息 |
| 技术超时 | `constants/sessionSync.ts`集中定义WRITING_CHAT_CONTEXT_TIMEOUT_MS，当前30秒；只结束本地等待，已提交的原笔记保存沿原回执完成，Agent任务时限保持 |
| 创建迟到 | `handleAgentSelect`在await后核对触发Session及原Chat卡片仍存在，拒绝向后来笔记或已移除卡片更新导航；服务端已创建Thread及原Voice规则保持 |

所有准备消息沿原固定文档URL、documentId、revision及正常账户校验。快照只用于用户明确发送，不新增正文或凭证日志。源Thread、停止、队列、确认、任务执行及权限继续沿原生产入口。

## 设计复核

| 评审项 | 判断与处理 |
| --- | --- |
| 可行方案 | 采用原卡片按钮及按需上下文消息；打开时缓存正文会绕过发送前保存，已排除；完整Chat移入WebView与新全局状态服务均排除 |
| 业务关系 | 按当前卡片引用进入，A/B允许原Voice复用；切记录不自动建立或切换Thread |
| 草稿 | 失败通过原composer恢复；主Chat实例保持，侧会话关闭释放规则保持，无新增持久草稿 |
| 请求身份 | documentId、Session、requestId、读取epoch及mounted分别覆盖文档、笔记、单次准备和Native选择生命周期 |
| 网络 | 继续原历史读取和前台恢复；原HTTP错误回执与界面入口故障分别记录；无换地址或自动发送 |
| 改动范围 | 复用原App、Writing文档、More、Native提交与原保存；新增业务接口和组件均为零 |

实现资格按下方实际命令判定；设备采用、真实账户和模型资格分别维护。

## 验证回执

确定性阶段由`luna_test_runner`执行，原始命令和首次失败归[本轮回执](/tmp/ink-writing-chat-fix-20261101/validation/receipts.md)。全部数据为合成Writing Session、HTTP DTO与原Hook/组件；真实账户、数据库和模型调用为零。

| 命令或阶段 | 退出码 | 当前结果 |
| --- | --- | --- |
| `pnpm exec tsc --noEmit --incremental false --pretty false`，cwd为frontend | 0 | Web类型检查通过；初次两个DTO断言类型转换错误已修正，首次退出2单独保留 |
| `pnpm native:typecheck`，cwd为frontend | 0 | 原生类型检查通过；同一初次类型错误退出2保留 |
| 聚焦原合同及新增WritingChatContextProtocol，临时playwright.config.mjs | 首次1 | 新协议3项、原chooser2项、建议11项、history8项通过；原ChatThreadBindingConflict完成回执计数波动单独重跑 |
| `pnpm exec playwright test --config=/tmp/ink-writing-chat-fix-20261101/validation/conflict-only.config.mjs` | 0 | 原冲突规格1 passed，8.4s；自身使用Chromium，保留其原配置；无产品修改 |
| 临时frontend副本`NEXT_TELEMETRY_DISABLED=1 pnpm exec next build --webpack` | 0 | 原Next 16.1.6生产构建成功，编译12.7s；原.env、.next和用户服务保持 |
| Native两规格首次 | 1 | 38项中37通过；新增A/B idle测试误用fixture owner=true进入原队列，已在测试前置明确owner=false |
| Native精确`-g 'Writing A/B sends'` | 0 | 1 passed，1.8s；等待准备时零POST，A/B同Thread分别发送对应快照 |
| DOM三规格首次 | 1 | 13项中12通过；新A/B步骤出现旧正文，原快照和保存断言保持 |
| 精确A/B/A重复采证 | 1 | 5次中4次失败，DOM input已更新且尚无Session POST；随后定位到select当前A时旧值断言过早满足，测试可在Calendar异步关闭前向背景textarea填值 |
| 修正可见旅程前置后`-g 'touch A/B/A' --repeat-each=5 --trace=retain-on-failure` | 0 | 等待原`.calendar-popup`实际关闭后编辑，5 passed，10.9s；无固定sleep、无产品诊断接口或额外生产修改 |
| 同一候选完整`writing-document.spec.ts` | 0 | 当时5项全部通过，16.4s；新增迟到保存边界随后单独验证 |
| Native精确`-g 'Writing MCP user messages'` | 0 | 1 passed，1.6s；多段用户消息使用同一准备入口和对应editor_state |
| DOM精确`-g 'a late save of A'` | 0 | 1 passed，1.7s；保存A期间选择B，迟到保存只返回session-changed，不回传A快照，B正文保持 |
| `python3 /tmp/ink-writing-chat-fix-20261101/validation/validate_docs.py` | 0 | 当前20份Markdown和目录合同、127个新增/调整链接、75个锚点，错误0；最后回执补充后再做终检 |
| 当前与历史关联对话Mermaid语法 | 0 | 当前正常、异常、状态3/3，归档3/3；仅语法资格 |
| `git diff --check` | 0 | 已跟踪文件空白检查通过；新增Markdown由文档脚本检查 |

Chrome主阶段复用本机156.0.8078.74，未下载浏览器；旧`writing-manual-suggestions`与`ChatThreadBindingConflict`自身的Chromium设置按原规格执行。技术样本与设备、真实账户验收分别报告。

主Agent已复核失败时间线：复选当前A时，Calendar内部getSession仍在处理，原textarea已显示相同旧值；Playwright.fill具备操作背景字段的能力，界面所有权前置需要等待原日历关闭。该问题由规格补齐可见操作顺序解决，快照字段、保存请求和目标Thread断言均保留。Native idle前置沿原local_owner规则设置，原排队逻辑保持。

指定范围的最终通过覆盖为24项协议/建议/history合同、1项原Web冲突浏览器规格、39项Native组件与Hook规格、14项DOM和相邻写作规格；共78个不同用例，失败项的修订和定向重跑已逐条列出。A/B/A额外连续5次通过，退出0。临时Next及Vite由本轮命名进程启动，均按原afterAll或本轮PID关闭；用户已有服务保持。

局部设计评审通过，源码实现及上述技术验证完成。该结论覆盖原组件、Hook、公开DTO和隔离Next；手机新包、WKWebView候选、真实账户及模型继续独立验收。

## 采用与回退

本阶段未签名、打包IPA、覆盖安装手机、部署服务或调用真实模型。当前改动要进入设备需后续按既有RN与Next配套资源准备、构建和安装流程采用；设备版本记录沿原部署手册，不将源码验证报告为当前手机已修复。

回退范围为本项App/文档协议/Native可选准备接线及原卡片mobileWriting呈现；原HTTP接口、持久化数据、Thread历史、Voice关联和普通Chat保持。回退通过常规代码差异审阅实施，不删除既有记录或容器。
