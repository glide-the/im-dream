<!-- [Input] Reported Agent diary error, existing normal-service read receipts and bounded Admin/broker configuration. -->
<!-- [Output] Scoped diagnosis, explicit configuration repair, regression results and running-process adoption status. -->
<!-- [Pos] Diary retrieval repair evidence; synthetic tests remain separate from real-user/model acceptance. -->
<!-- [Sync] 2026-10-06: record the full-text response-budget repair without modifying retrieval, grants, schema or unrelated work. -->

# Agent 日记检索响应容量修复

## 目标与工作边界

优化后的执行提示词：定位 `session_projection_unavailable` / `ADMIN_RESPONSE_INVALID` 的实际失败边界；使用当前本机账户进行必要只读核对，修复服务器配置，保留全部正文候选与现有匹配、排序、结果限制及严格校验。运行公开生产实现的隔离回归，更新现行说明与目录合同；区分源码、配置、运行进程与真实模型验收状态，保护凭证及日记正文。

基线为 `develop` / `dc5c7723`。工作区已有 Calendar/Notion 源码、测试和文档修改，本轮保留。本轮只处理后端响应字节配置、`test_sessions_tool.py` 的回归、README 镜像及其目录合同、日记检索设计和本回执。Admin、Gateway、数据库 schema、检索生产程序、用户日记、账本、模型和订阅不改写。

## 只读诊断

- 原报错调用两次，日期范围均为 `2020-01-01..2026-10-06`，均包含查询正文，结果 `limit` 分别为 15 和 10；只记录日期和参数形状，不记录查询词、对话或日记正文。
- 正常本机 `localhost:5173` 的已登录账户有 560 条 Session。`GET /api/sessions?timezone=Asia%2FShanghai` 为 HTTP 200，响应 164,871 字节；不保存名称、预览或正文。
- 同一正常前端的 Reflections 页面触发 `GET /api/sessions/aggregate`，为 HTTP 503，`detail.error_code=ADMIN_RESPONSE_INVALID`，`outcome_unknown=false`。请求编号为 `a031e57d-35ab-4f11-b4ee-889101ad479f`。
- 本机后端 `INK_ADMIN_DREAM_MAX_RESPONSE_BYTES` 为 `1_048_576`。代码在 `request_admin_dto` 读取原始响应字节时执行这个上限，超限即返回 `ADMIN_RESPONSE_INVALID`；同一数值继续用于 `SessionProjectionBrokerSettings.max_bytes`。
- Admin 和 Dream 的 Session 字段定义一致，普通列表正常；全文 `include_text=true` 在全部正文取得后才执行 fuzzy 和 `limit`。调整结果数量不能减少输入正文容量。
- 诊断 Chrome 标签为本轮新建；用户和其他聊天的原标签未接管。直接打开 JSON 地址被浏览器阻止，raw CDP resource 方法也不可用；改用原应用页面触发普通公开请求，未通过替代账户或后台数据库查询取证。

## 修复

本机被 Git 忽略的 `backend/.env` 仅将响应容量从 `1_048_576` 改为 `16_777_216`。更新时检查该键只有一处且仍等于只读核对值，否则拒绝覆盖。没有读取或输出其余秘密配置。

`backend/.env.example` 同步显式设置 16 MiB，并说明这既保护 Admin HTTP，也保护私有 Session broker；不是日记配额。代码未配置时的 1 MiB 缺省值保持不变。旧进程与已有 turn 的配置不会因修改文件自动变更，后端重新加载配置后新 turn 才能取得新容量。

沿用现有实现，未新增功能代码：严格 DTO、请求编号、认证、权限和 capability 校验保持；不截断正文、不提前截断候选、不取消容量上限、不回退 Dream 数据库。README 中英、受影响目录清单与现行日记检索设计同步，正式设计正文增加正常、失败恢复与状态图；历史设计内容保留。

## 技术回归与证据

`test_sessions_tool.py` 新增回归调用实际 `AdminDataConfig.from_env`、Admin HTTP DTO transport、`AdminRequestAuth` 生成的 broker settings、真实 loopback broker/client 与 `handle_get_sessions_range`；仅注入明确合成的 Admin HTTP Provider 和 grant，不访问数据库或模型。

| 验证 | 实际状态 |
| --- | --- |
| 560 条合成 Session，正文响应超过 1 MiB | 通过：原容量复现 `session_projection_unavailable` / `ADMIN_RESPONSE_INVALID`；模板容量完整读取。 |
| 唯一匹配位于末条、`limit=1` | 通过：返回末条 Session，完整正文不进入工具返回。 |
| 大正文附加未知字段或不同 request_id | 通过：继续拒绝，返回不披露合成正文。 |
| 既有 broker、Admin transport、公开 Session/Chat 与 turn persistence | Luna 执行下方七文件 focused 命令，退出码 0：361 passed、4 subtests passed；25 项既有 FastAPI lifespan 弃用警告，28.01 秒。 |
| Markdown 引用、目录清单与 README 镜像 | 50 个本轮受影响正文中的本地文件引用、受影响清单与文件头检查通过，退出码 0；页内锚点另行核对。 |
| Mermaid | 三个新增业务图语法通过，退出码 0；时序图使用项目 Mermaid parser，状态图使用其官方 Jison parser。仅语法验证，不宣称渲染或功能验收。 |
| `git diff --check` | 退出码 0。 |

在 `backend/` 中运行的最终命令：

```sh
.venv/bin/python -m pytest tests/test_sessions_tool.py tests/test_session_projection_broker.py tests/test_admin_data_boundary.py tests/test_admin_session_routes.py tests/test_admin_chat_routes.py tests/test_admin_turn_persistence.py tests/test_server_claude_agent.py -q
```

首次命令误加目录 `.`，导致扫描 `backend/agentdata` 内已有 workspace 的测试文件，907 项 collection errors、退出码 2，未执行目标回归；随后移除误加目录，按上述确定文件范围重新执行并通过。失败与成功日志都保留，不以首次 collection 失败判断业务缺陷。

验证产物保存在根目录 `output/agent-diary-capacity-20261006/`。仅清理本轮自建 loopback broker；不创建数据库、外部资源或真实模型请求。

## 正常服务采用状态

通过当前 VS Code 的 `Backend: Python (server.py) (ink-dream-memory)` 调试会话重启该后端，让服务重新读取已修复配置。`lsof -nP -iTCP:8765 -iTCP:5173 -iTCP:3000 -sTCP:LISTEN` 退出码 0：后端由原 PID 25653 变为 PID 76818，仍监听 `127.0.0.1:8765`；前端 PID 9971 和 Admin PID 46009 保持原值。没有重启前端、Admin 或其他服务，也没有额外修改调试启动参数。

重载后 `curl -sS -o /dev/null -w 'HTTP %{http_code}\n' http://127.0.0.1:8765/api/health` 退出码 0，HTTP 200；这是进程健康检查，不是检索验收。首次误请求 `/health` 得到 HTTP 404，核对 `server.py` 的正式路由后改为 `/api/health`。

修复后的正常账户检索仍未确认：浏览器自动化连接连续超时，重新创建本轮标签也超时；原应用分析页面出现前端客户端异常，开发错误界面提示浏览器扩展添加的 body 属性引发 hydration 差异。本轮未修改前端或扩展，无法据此认定后端检索成功或失败。需要正常页面可用后，在新 Agent turn 重试原检索；已有 turn 的 broker 不因配置文件变更自动更新。

配置修复、后端重载与技术回归已完成；没有以合成正文回归宣称真实日记检索已恢复。没有 commit、push、PR、远程部署或真实模型验收。
