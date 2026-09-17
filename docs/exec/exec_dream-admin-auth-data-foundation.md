<!-- [Input] Actual Dream worktree commands and dedicated Luna validation receipts. -->
<!-- [Output] Foundation-stage evidence and explicitly open production migration gates. -->
<!-- [Pos] Dream implementation receipt; technical checks do not replace real business acceptance. -->
<!-- [Sync] 2026-09-14: record 55 Python tests, 6 BFF tests, targeted TypeScript and docs checks. -->

# Dream Admin 消费端基础执行回执

## 当前结果与边界

工作区 `/Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory`，分支 `codex/dream-admin-auth-data-client`，baseline `7d38715c`。goal active。基础阶段初次记录生产替换数量 **0**（后续已完成资源2方法，见下方首批回执）；108数据访问候选文件（100生产候选/8导入维护）和159事务候选仍需逐入口DTO/API/Repository闭合，不把foundation单测或候选数量当迁移完成。

已实现 `backend/services/admin_data` 的配置、strict Pydantic principal/capabilities/handle/receipt DTO、HTTP client、注册DTO operation能力匹配与ES256/JWKS验证；`frontend/app/api/_auth` 的AES-GCM/PKCE/callback/return/origin/handle-CSRF边界。生产路由/后台未切换。旧认证/Device/项目架构原文按字节保存历史，现行目标设计与六图/README镜像同步。

## 实际验证

以下测试均由专用`luna_test_runner`执行，cwd为上述worktree，无PG/模型/网络/真实账户/浏览器调用。

| 命令 | exit | 关键输出/适用范围 |
| --- | --- | --- |
| `PYTHONPATH=/private/tmp/dream-admin-data-test-deps:backend /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python -m pytest backend/tests/test_admin_data_boundary.py -q` | 0 | `55 passed in 0.22s`；JWT字段/签名/缓存/轮换、service/user分开、strict DTO/unknown提交/receipt |
| `node --experimental-strip-types --test frontend/app/api/_auth/login-boundary.test.ts` | 0 | `tests 6`, `pass 6`, `fail 0`；纯server BFF helper |
| `/Users/dmeck/project/ink-dream-memory/frontend/node_modules/.bin/tsc --noEmit --strict --skipLibCheck --target ES2022 --module NodeNext --moduleResolution NodeNext --allowImportingTsExtensions --types node --typeRoots /Users/dmeck/project/ink-dream-memory/frontend/node_modules/@types frontend/app/api/_auth/login-boundary.ts frontend/app/api/_auth/login-boundary.test.ts` | 0 | 无输出；仅两个新BFF文件typecheck，不是full frontend build |
| `/Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python /private/tmp/dream-admin-doc-check.py` | 0 | 12文档、168本地链接、README heading parity、3历史原文匹配baseline、6Mermaid计数、failures空；未渲染Mermaid |
| `git diff --check` | 0 | 无输出 |
| `/Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python -m compileall -q backend/services/admin_data backend/tests/test_admin_data_boundary.py` | 0 | 初轮编译通过；仅语法检查 |

首轮pytest因现有venv无pytest而未执行（exit1，harness依赖缺口）。主任务通过 `UV_CACHE_DIR=/private/tmp/dream-admin-data-uv-cache uv pip install --python /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python --target /private/tmp/dream-admin-data-test-deps 'pytest>=8,<9'` 安装临时pytest8.4.2，未修改用户venv。sandbox内uv发生macOS系统配置NULL对象panic（exit101），同专用tmp命令获自动审查通过后沙箱外执行（exit0）。

补充流式response过大用例发现frozen Exception被contextlib赋traceback时产生FrozenInstanceError（54pass/1fail）。改为普通错误dataclass并隐藏DTO输入错误后fresh55测试通过。该结果只证明consumer故障处理，不证明Admin数据库事务。

runner清理本轮pyc；专用tmp依赖/cache/checker保留供后续验证。未停止或修改用户服务、账户、DB、SDK/Runtime pins。

## 依赖与下一批生产入口

1. Admin exact resource-policy.read/observer DTO、Drizzle Repository与input/output版本及已发布capability，随后替换独立PG policy provider/sink，LKG与单worker排序保留。
2. thread/run/client/service/scope绑定长期委托及renew、Gateway授权；不能将全局Admin service/Google/Auth秘密注入Runtime/Bash/hooks/外部MCP，旧DATABASE_URL显式注入仍是待移除入口。
3. Admin密码/注册/Google authorization UI与旧PK/bcrypt显式迁移、实际OAuth client注册，完成BFF public start/callback/AuthContext/REST/SSE/Voice切换。
4. 全域DTO/domain/typedRepository/Drizzle ORM操作与原事务、数据权限、idempotency/unknown恢复逐项闭合；正常本机真实业务验收和full no-PG runtime证明仍未执行。

## 首批生产资源接口回执

生产替换 **2个领域方法**：`resource_policy.Provider.load` 与 `resource_postgres_sink._write_sync`，`agent_factory` 也已移除database import。当前 resource file/class/internal singleton 的历史名字保留；SQL已移除，Admin拥有DB clock/TTL/receipt。其他生产领域、startup PG、旧认证/Gateway与Tool PG注入继续待迁移，因此goal保持active，未部署正常本机服务。

专用Luna实际cwd为本worktree；命令 `PYTHONPATH=/private/tmp/dream-admin-data-test-deps:backend /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python -m pytest backend/tests/test_admin_data_boundary.py backend/tests/test_admin_resource_data.py backend/tests/test_claude_agent_resource_policy.py backend/tests/test_claude_agent_resource_postgres_sink.py backend/tests/test_claude_agent_resource_observer.py backend/tests/test_claude_agent_resource_diagnostics.py -q` exit0，输出 `111 passed in 1.54s`；覆盖strict request/response/hash版本、资源状态、精确数值、原LKG/revision与observer/diagnostics、queue/timeout/drain及未知写原receipt恢复。`git diff --check` exit0无输出。无PG/网络/账户/模型/harness启动失败；只清本轮pyc，既有一项pyc未删除。

## Admin/Auth 子进程凭据边界回执

实际SDK parent-env overlay用精确服务器秘密键空值tombstone保护，server保留原值；用户覆盖和二次merge不能恢复，内部/外部stdio MCP显式env也去除同一组键。阶段5 fresh命令 `PYTHONPATH=/private/tmp/dream-admin-data-test-deps:backend /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python -m pytest backend/tests/test_admin_server_credentials.py backend/tests/test_sdk_env.py backend/tests/test_claude_agent_runner.py -q` exit0，`187 passed, 1 skipped in 0.98s`；diffcheck exit0。首轮5fail/182pass/1skip均为旧exact字典断言未包含空值键；更新为先断言秘密键为空，再保持其余原exact优先级/路由字典后fresh通过。没有新harness失败。

资源阶段docs fresh命令主venvpython `/private/tmp/dream-admin-doc-check.py` exit0：15文件/172本地链接/历史3原文SHA/README heading parity/6Mermaid计数/无失败。Luna readonly AST检查3生产文件41个方法，database/persistence import及execute/get_db/commit/rollback/connection调用 violations空；它不是全域runtime无PG证据。Mermaid尚未渲染，全域数据库/认证/长期委托、正常本机真实业务验收仍待完成。

首批commit前文档fresh复核：主venvpython `/private/tmp/dream-admin-doc-check.py` exit0，16文件/177本地链接/README heading parity/历史3份字节hash匹配/6Mermaid计数/failures空；`git diff --check` exit0。源代码测试已通过后未重复运行或扩大覆盖。
