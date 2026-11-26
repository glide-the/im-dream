<!-- [Input] 用户的参考截图、Thread范围修正、现行源码及原候选交付。 -->
<!-- [Output] 本轮工作项、范围、采用方案、验证证据和验收边界。 -->
<!-- [Pos] Chat工具范围修正执行记录；产品与开发正文由各独立专项所有。 -->
<!-- [Sync] 2026-11-13: 逐条工具选择和分组级联实现；技术验证按实际回执登记。 -->

# Chat工具选择与级联菜单修正

## 需求与决策

用户要求Chat采用参考菜单的分组与级联交互，MCP工具作为Chat消息传入的工具选择，开关范围为当前Thread。资源连接设置继续负责连接与认证。

发现：原ComposerToolsMenu调用useClaudeMcpResources.toggle并PATCH账户／工作区配置；Chat请求固定为空allowedMcpServers，平台tools已支持逐条传入。参考AgentSelector使用侧向子菜单，参考MCP选择修改Chat输入状态。

定义：工具选择归当前Thread，每条消息捕获选择；连接启用归Settings。发展：复用原Agent／模型目录和管理读取接口，将MCP名称纳入tools，按服务粒度选择。交付：更新组件、普通／首次／排队请求与后端授权过滤，同步独立产品和开发稿。

## 交付物

- [Chat产品交互](../prd/chat/agent-tool-composer.md)：背景、边界、概念、桌面／窄屏骨架、正常／异常时序及状态。
- [Chat开发设计](../design/claude-agent/chat-agent-tool-composer.md)：模块职责、tools DTO、Thread状态、队列及授权快照接线。
- Web：一个当前Agent入口、桌面侧向级联列表、分组菜单和Thread工具开关。
- Native：原底部面板中进入／返回Agent列表；工具选择沿同一Thread与消息合同。
- `useChatMcpCatalog`只读取连接；`useChatToolSelection`维护内存中的Thread选择。
- 新对话首条由queuedTools固定提交选择，普通消息和排队消息显式携带各自tools。后端区分平台types和托管MCP names，过滤后取得凭据。
- 资源设置的连接启用、认证和配置版本保持原所有权；界面说明指向Chat当前对话选择。

选择在当前前端进程中按Thread保留，重载或App重启后回到关闭。跨设备或数据库持久化偏好、单服务内逐工具筛选、工作流／预设目录、原生音频播放器及部署退出本轮范围。

## 验证证据

证据目录：[本轮回执](../../frontend/output/chat-thread-tools-20261113/checks/delivery-receipt.md)。原始失败日志和每轮截图分别保留在同目录和browser-pass目录。

| 验证项 | 命令与结果 |
| --- | --- |
| 后端DTO／授权快照／Service／队列／音频协议 | `PYTHONPATH=backend backend/.venv/bin/python -m pytest -q backend/tests/test_admin_chat_routes.py backend/tests/test_claude_mcp_runtime_snapshot.py backend/tests/test_claude_agent_service.py backend/tests/test_claude_agent_thread_input_queue.py backend/tests/test_mobile_clock_audio.py`；exit 0，131 passed，24 subtests passed |
| 正常Chat入口及原composer | 首轮定向Playwright中6项正常路由与5项原composer通过；包含桌面／窄屏首条和后续tools请求 |
| Web类型 | `pnpm exec tsc --noEmit --incremental false --pretty false`；最终源码复核exit 0 |
| Native类型 | `pnpm native:typecheck`；最终源码复核exit 0 |
| Chat菜单隔离与视觉 | `pnpm exec playwright test --config=e2e/chat-tools.config.ts e2e/chat-tools.spec.ts app/_dream/components/chat/__tests__/ThreadInputQueue.test.ts --output=output/chat-thread-tools-20261113/browser-pass4`；exit 0，25 passed |
| 文档与图示 | Markdown路径、目录索引、源码头、15幅图、2份历史原文及3份上游快照已核对；最终命令和计数由delivery-receipt登记 |

追加正常入口命令：`pnpm exec playwright test --config=e2e/chat-tools.config.ts e2e/chat-route-cache.spec.ts --grep "normal Chat wires Agent" --output=output/chat-thread-tools-20261113/browser-first-snapshot`，exit 0，2 passed。首次提交快照、已有Thread的后续空选择均通过。

失败与修复：首轮fixture缺少Thread receipt GET，补齐后验证。第二／三轮Left收起失败；焦点诊断确认activeElement停在外层触发器。Popover和子菜单原本在visibility:hidden时尝试聚焦，改为可见DOM提交后聚焦。第四轮完整通过。文档检查首轮命令路径缺少frontend前缀，按实际路径执行后识别两处目录说明元数据，补齐后进行最终检查。失败证据完整保留。

浏览器使用安装的Chrome、明确fixture和自有随机端口，无正常业务数据库或真实模型调用。Native可视化为React Native Web；真机、真实账户／模型／MCP与发布验收尚未执行。

## 历史与工作区

Thread范围修订前的两份完整原文及原图已保留并由现行稿链接。最早双入口历史继续保留。源码前像、任务文件清单、失败日志与最终回执在`frontend/output/chat-thread-tools-20261113/`。用户及其他Agent的未提交改动保留，未执行提交、推送或发布。目录原有空白行保留，新增行及新增文件的空白检查分别留存。
