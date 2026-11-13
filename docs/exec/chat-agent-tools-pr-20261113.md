<!-- [Input] 用户的PR合并要求、当前Chat交付及原工作区未提交改动。 -->
<!-- [Output] 独立提交范围、依赖、可复查截图及独立工作区验证。 -->
<!-- [Pos] Chat统一入口与Thread工具的集成回执；原运行日志与历史记录分别保留。 -->

# Chat统一入口与Thread工具集成

## 范围

目标分支为仓库默认分支`develop`。交付包含统一Agent入口、独立模型选择、逐条消息与排队工具快照、授权范围内的MCP过滤、中文菜单及导航修订。资源连接配置和认证继续归Settings；工作台更多菜单包含写作、时间线、回顾、主题、设置五项。

平台工具描述符依赖同批提供的`mobile_clock_audio`元数据问答协议、原AskUserQuestion答案校验和SDK内存适配。其权限为精确low-sensitivity例外，问答持续收集用户答案，缺失答案拒绝执行。原生播放器、音频读取和后台持续计算保持未实现或未验收状态。

独立工作区以`develop`为基础，通过各阶段源码前像拆分Chat变更。原工作区的外部分享呈现、历史加载、后台恢复、Admin错误处理、编辑器设置和构建缓存继续保留。目录合同只登记本次相关文件。

## 独立工作区验证

| 命令 | 退出码 | 关键结果 |
| --- | --- | --- |
| `pnpm exec tsc --noEmit --incremental false --pretty false` | 0 | Web完整类型检查通过 |
| `pnpm native:typecheck` | 0 | Native完整类型检查通过 |
| `INK_MORE_EVIDENCE_DIR=output/chat-pr/screenshots pnpm exec playwright test --config=e2e/chat-tools.config.ts e2e/chat-composer-zh.spec.ts e2e/chat-tools.spec.ts e2e/chat-route-cache.spec.ts e2e/more-navigation.spec.ts e2e/native-more-navigation.spec.ts app/_dream/components/chat/__tests__/AIInputDockSlashMenuRegression.test.ts app/_dream/components/chat/__tests__/ThreadInputQueue.test.ts --output=output/chat-pr/browser` | 0 | 55项：8中文、18工具／模型、4正常路由与缓存、13导航、5输入栏、7队列 |
| `PYTHONPATH=backend backend/.venv/bin/python -m pytest -q backend/tests/test_admin_chat_routes.py backend/tests/test_claude_mcp_runtime_snapshot.py backend/tests/test_claude_agent_service.py backend/tests/test_claude_agent_thread_input_queue.py backend/tests/test_mobile_clock_audio.py backend/tests/test_claude_agent_runner.py` | 0 | 297 passed、1 skipped、217 subtests passed |
| `PYTHONPATH=backend backend/.venv/bin/python -m pytest -q backend/tests/test_mobile_mcp.py` | 0 | 7 passed，原MCP内存适配、媒体问答和投影恢复 |
| `node frontend/output/chat-pr-20261113/docs/check-docs-selected.mjs`（原工作区运行，目标为独立工作区） | 0 | 54份Markdown库存、140处链接、24个Mermaid图及6张版本化截图通过；3份MIT来源快照Git blob一致 |

后端六份规格使用SDK stub；原生MCP规格使用实际SDK类型并运行独立Python进程。首次将两类规格放入同一进程时，集合阶段的`_KwargsBase`替换了MCP配置类型，产生7项失败。独立进程分别通过，失败日志保留于本机`frontend/output/chat-pr-20261113/backend/`，最终日志位于`backend-final/`。前端原始日志位于同一目录下的`frontend/`。

## 中文截图

| 场景 | 修复前 | 修复后 |
| --- | --- | --- |
| 桌面级联，深色 | [前](assets/chat-composer-20261113/desktop-before.png) | [后](assets/chat-composer-20261113/desktop-after.png) |
| 窄屏模型，浅色 | [前](assets/chat-composer-20261113/narrow-model-before.png) | [后](assets/chat-composer-20261113/narrow-model-after.png) |
| Native浏览器呈现，深色 | [前](assets/chat-composer-20261113/native-before.png) | [后](assets/chat-composer-20261113/native-after.png) |

截图使用生产组件与合成公开DTO，Native采用React Native Web。55项独立用例使用已安装Chrome、自有临时端口与显式HTTP夹具，原服务保持运行。真机、真实账户／模型／MCP、安装构建与发布验收保持未执行。

产品规则见[Chat PRD](../prd/chat/agent-tool-composer.md)，接口与时序见[开发设计](../design/claude-agent/chat-agent-tool-composer.md)。各阶段执行记录中的`frontend/output/`路径为本机日志位置，版本化截图由本目录维护。
