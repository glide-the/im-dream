<!-- [Input] Dream commit 99970790 and Stage43 primary/Luna/source/scanner command receipts. -->
<!-- [Output] Durable sanitized verification evidence for the Chat Session tool private broker. -->
<!-- [Pos] Dream technical validation receipt; excludes Reflections snapshot, real services, PostgreSQL, browser and model acceptance. -->
<!-- [Sync] 2026-09-15: archive exact focused tests, harness correction and current AST closure counts. -->

# Dream Chat Session 工具 broker 技术回执

## 验证对象

- 仓库：`/Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory`
- 提交：`999707909c7bfce3a1af250a55a90f2b8a483f89`（`Route Chat Session tool through Admin broker`）
- 实现边界：Chat turn 的 `server-persistence` owner 提供 Session 投影；`sessions_tool.py` 保留日期、正文 fuzzy、labels、limit、Unicode 和 vector 状态处理。Reflections `worker-load` snapshot provider 仍是后续依赖。
- 数据边界：子进程只保留 broker host、临时端口、256-bit capability、timeout/max-bytes 与两项检索策略。Claude、Admin、数据库、actor、Thread 和自定义环境均在导入 MCP server 前清除。

## 实际命令与结果

| 执行方 | 工作目录 | 命令范围 | 结果 |
| --- | --- | --- | --- |
| Dream 任务 | Dream worktree | `python -m pytest -q`：broker、Session tool、turn persistence、Runner、Service、request auth、data boundary 共7文件 | exit 0；370 passed、1 skipped，13.63s |
| Luna | Dream worktree | 相同 argv，首次在受限 sandbox 执行 | exit 1；21 failed、349 passed、1 skipped；失败均始于 `127.0.0.1:0` bind，属于 loopback harness 前置限制 |
| Luna | Dream worktree | 相同 argv，允许具名 loopback 后重跑 | exit 0；370 passed、1 skipped，13.68s |
| Luna | Dream worktree | 8个变更 production Python 文件内存编译 | exit 0；compiled 8 production Python files |
| Luna | Dream worktree | `git diff --check` | exit 0；无 whitespace error |
| Dream 任务 | Dream worktree | source boundary probe | exit 0；blocked imports 0、legacy helper mentions 0、protocol Admin/DB imports 0；清理顺序、exact allowlist 与 credential tombstones 均为 true |
| Dream 任务 | Dream worktree | 当前 dirty-safe Python AST scanner | exit 0；514 modules、80 production entries、52 SQL modules、496 SQL literals、37 driver/DB import modules、94 legacy helper calls、457 tx/connection calls、24 Admin data modules、88 operation names、104 nonproduction entries、166 schema literals、parse errors 0 |

测试覆盖 missing/wrong capability、strict forbidden 字段、malformed/oversized request 和 response、timeout、closed owner、in-flight close drain、当前续期 grant、`include_text` 投影、产品检索兼容、Admin 不可用与无 PostgreSQL fallback。实际子进程测试从包含伪造 Claude/Admin/数据库/actor/Thread/custom secret 的 parent env 启动，调用生产 sanitizer 后逐项断言缺失；测试值均为 synthetic，不包含真实凭据。

## 结论与限制

Chat Session 工具生产路径不再依赖 Dream `database` helper 或 PostgreSQL 凭据，技术验证通过。刷新扫描仅证明本次入口减少1个 driver/database import module 和1个 legacy helper call；全仓仍有52个 SQL 模块及94处旧 helper，不能据此宣称数据库迁移完成。

本回执未访问正常 Admin、PostgreSQL、Google、浏览器、共享文件业务数据或真实模型。首次 Luna 失败保留为 harness 证据，不作为产品缺陷；真实业务验收和 Reflections background Session provider 尚未执行。
