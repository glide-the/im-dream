<!-- [Input] Immutable Dream local-data commit, Registry101 pins and root deterministic validation. -->
<!-- [Output] Public-route consumer, receipt recovery and post-commit source-only closure evidence. -->
<!-- [Pos] Dream consumer technical receipt; normal-account import remains separate. -->
<!-- [Sync] 2026-09-15: freeze commit 433885c4 and corrected AST deltas. -->

# Dream Registry101 本地数据消费者验证

## Git 与契约

- commit: `433885c4f5ce40bc58857f6e8446a7309d1f932b`
- tree: `dd5216508ccc78f43c441a7690e5225db7dafba4`
- parent: `626747ffb0c4a414b69d9d33dc89570dc59065a2`
- subject: `Route local data import through Admin`
- Admin provider pin: `c051a58e9193b0f39f2b211ac9ff5182fea87d73` / tree `49cd33a9cdf0f73c1faebecc01baccfca0af7a5b`
- `local-data.import`: `f2f13ac392be415b42bb9532d42e20bf04fef2400551cd2f528991f4f6de271d`
- `first-login.complete`: `f06bbfd87fd905139b40df61eccdda6726678adda304dcd141a0bf52cf874cb0`
- committed files: 15，均为 auth route、typed consumer、request registration、tests、API/architecture/inventory/folder docs；Plugin、`.pnpm-store` 与 Root coordination/stage/verification files 不在 commit。

Root 直接读取 commit object 核对文件、tree 和 `auth.py`；目标文件没有 `database` import、`import_user_data` 或 `set_first_login_completed` 调用。`local_data_import.py` commit blob SHA-256 为 `55d33f8092057c75099cc29455d41d16e82a81073d4fbcc4921effee5e3a55b1`。

## 确定性验证

cwd：`/Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory`。

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend /Users/dmeck/project/ink-dream-memory/.venv/bin/python -m pytest -q -p no:cacheprovider backend/tests/test_admin_local_data_routes.py backend/tests/test_auth_registration.py
```

exit0：18 passed。覆盖四类解析、同一请求时钟、strict public body、Admin accepted counts、capability fail closed、legacy DB fence，以及 `local-data.import` 和 `first-login.complete` 各自的 unknown-result receipt-only recovery。

```text
PYTHONDONTWRITEBYTECODE=1 /Users/dmeck/project/ink-dream-memory/.venv/bin/python -m py_compile backend/routers/auth.py backend/services/admin_data/local_data_import.py backend/services/admin_data/request_auth.py backend/tests/test_admin_local_data_routes.py
git diff --check -- <本阶段目标文件>
```

两项 exit0。Dream 任务另报告 5 files / 96 passed、独立 py_compile、Markdown path 和 staged diff gate；Root 没有重复同一扩大测试。

## Source-only AST 关闭证据

运行：

```text
/Users/dmeck/project/ink-dream-memory/.venv/bin/python /private/tmp/ink-auth-migration-validation/scan-dream-current-db-closure-after-local-data-433-source-only.py
```

exit0，`parse_errors=[]`。扫描 524 个排除 dot-dir/venv 的 Python 模块：production entry 80、SQL module 52、SQL literal 496、driver/database import module 33、legacy helper call 63、transaction/connection call 457、Admin-data module 26、operation name 115。相对 Reflections `c49` 后同一算法，driver/database import module 减1、legacy helper call 减3、operation name 加2；`backend/routers/auth.py` 的 database import/helper arrays 都为空，只剩 typed Admin imports。机器回执为 [dream-db-closure-after-local-data-433-source-only.json](dream-db-closure-after-local-data-433-source-only.json)。

## 范围限制

技术验证没有连接正常 Admin/PostgreSQL，也没有执行指定账户的浏览器首次登录或真实导入。旧 helper 定义仍存在于 `database.py`，但已不在三个生产路由调用链；全仓其他 63 个 legacy helper call 继续按域迁移。
