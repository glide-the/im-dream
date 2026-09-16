<!-- [Input] Final Registry185–191 provider/consumer source and reproducible validation commands. -->
<!-- [Output] Sanitized Story Workspace database-cutover technical receipt with explicit acceptance limits. -->
<!-- [Pos] Cross-project deterministic evidence; real Google/model/account acceptance remains separate. -->
<!-- [Sync] 2026-09-16: record final Admin, Dream, Runtime, BFF, build and database-closure results. -->

# Story Workspace Artifact 最终技术回执

## 实现边界

Admin Registry185–191 采用 strict Zod DTO → Service → typed Drizzle Repository → transaction/receipt/audit。Dream 采用 strict Pydantic DTO/client/provider，浏览器请求传递当前 OAuth，Agent turn 复用 exact Thread/Run persistence grant。SQL、owner 过滤、锁、事务与持久化只在 Admin；Dream 保留共享文件读写、路径防护、Episode registry、`.dream` 投影、Runtime、EventBus、SSE 和 turn/resume/cancel。

Dream 生产启动不再读取数据库 URL 或创建连接池。旧 database/schema/persistence 和 SQL 运维脚本只位于 `backend/tests/**`，生产依赖导出不含 psycopg。Admin 不可用时消费者失败关闭，不回退数据库。

## 实际命令与结果

| 工作目录 | 命令 | 退出码 | 关键结果 |
| --- | --- | ---: | --- |
| `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory` | `pnpm exec vitest run app/lib/dream/storyWorkspaceArtifactDto.test.ts app/lib/dream/storyWorkspaceArtifactRegistration.test.ts app/lib/dream/storyWorkspaceArtifactService.test.ts app/lib/dream/claudePluginDataRegistration.test.ts` | 0 | 4 files、9 tests passed |
| 同上 | `pnpm exec tsc --noEmit --incremental false` 与受影响 ESLint | 0 | 类型与 lint 通过 |
| 同上 | `pnpm test:run` | 0 | 274 files passed、17 skipped；2067 tests passed、36 skipped |
| 同上 | `pnpm build` | 0 | DB package 与 Next.js 16.1.6 生产构建通过 |
| `/Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory` | `CLAUDE_CODE_CLI_PATH=<qualified-0.1.9> PYTHONPATH=backend backend/.venv/bin/python -m pytest -q backend/tests` | 0 | 3523 passed、24 skipped、615 subtests passed |
| 同上 | `CLAUDE_CODE_CLI_PATH=<qualified-0.1.9> PYTHONPATH=backend backend/.venv/bin/python -m pytest -q backend/tests/test_claude_resume_runtime.py -s` | 0 | 4 passed；同 Session resume、200/201 UTF-16 cwd 与 transcript 消失恢复通过 |
| 同上 | `PYTHONPATH=backend backend/.venv/bin/python -m pytest -q backend/tests/test_postgres_runtime_sql_boundaries.py` | 0 | 4 passed；生产模块无数据库 driver/import、pool、Story SQL 和部署 DSN |
| 同上 | `uv lock --check --project backend` 与无 dev 依赖导出比较 | 0 | lock 通过，requirements 1068 个依赖内容行一致 |
| 同上 | `bash -n ...` 与 `./deploy/autodl-ssh/test-topology.sh` | 0 | topology 通过，生成环境不含数据库键 |
| `/Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory/frontend` | `node --test app/api/_auth/*.test.ts`（5 个明确文件） | 0 | 35 tests passed |
| 同上 | `pnpm exec tsc --noEmit`、`pnpm lint` | 0 | 类型通过；lint 0 error、17 个既有 hook warning |
| 同上 | `pnpm build` | 0 | Next.js 16.1.6 生产构建通过 |
| Dream 根目录 | 变更 Markdown 相对链接检查与 `git diff --check` | 0 | 69 个非回执 Markdown 与 138 个回执 Markdown 均无缺失目标；diff 无空白错误 |

Runtime 命令中的路径指向本机已构建且 manifest/capability 校验通过的 `ink-claude-code-dream` 0.1.9；回执不记录凭据、Token 或用户正文。Drama Forge fixture 从主工作区同步到 worktree 并保持 Git 忽略，只用于确定性 Episode adapter 测试。

## 验收限制

本回执不包含真实 Google 登录、指定账户的完整 Dream Run、真实模型调用、账本结算或日常 Admin 页面可见性。它们必须通过本机正常 Dream/Admin/Gateway/PostgreSQL 公开入口另行执行并保留业务记录；在这些条件完成前，整体任务状态保持 active。
