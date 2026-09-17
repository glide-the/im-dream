<!-- [Input] Immutable Dream picture consumer commit, Registry103 pins and root/task deterministic validation. -->
<!-- [Output] Three-route compatibility, date-boundary and post-commit source-only closure evidence. -->
<!-- [Pos] Dream consumer technical receipt; normal-account picture acceptance remains separate. -->
<!-- [Sync] 2026-09-15: freeze commit 101fce6e and corrected AST deltas. -->

# Dream Registry103 图片历史消费者验证

## Git 与契约

- commit: `101fce6e3a1176504f949f92051e4fc6405446e4`
- tree: `53abcb16bf91841893e66c0bf2abc38af10a20db`
- parent: `433885c4f5ce40bc58857f6e8446a7309d1f932b`
- subject: `Route picture history through Admin`
- Admin provider: `547e89896776627b43ecaab0a5ac848891f21a94` / tree `1eec30f84691d53a1cf35e04a4ccaf98c93c04f2`
- operations: `picture-history.list` `d03993f15860caadba56b6788a4c1b1d0fa086e949f1831b6e805a2eabee028d`；`picture-history.full` `e35e76d3425641660da361f2671f0004042a3600b2f3d4072386233c0d90efa3`
- commit 包含16个 route/typed consumer/registration/test/current design/sequence/API/inventory/folder文件；Plugin、`.pnpm-store` 和 Root coordination/stage/verification 文件不在 commit。

Root 直接读取 commit object，`backend/routers/pictures.py` 没有 `database`、`get_db` 或三个 legacy picture helper。consumer blob SHA-256 是 `68941046484647ac45ec19c8a8f8685f40db0cfb669b3b365ac298ccef72aea1`。

## 确定性验证

cwd：`/Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory`。

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend /Users/dmeck/project/ink-dream-memory/.venv/bin/python -m pytest -q -p no:cacheprovider backend/tests/test_admin_picture_history_routes.py backend/tests/test_auth_registration.py
```

exit0：33 passed。覆盖普通列表、范围/空白边界、limit、thumbnail/full投影、404、OAuth/capability/transport/bad output、runtime legacy helper fence和production registration。Root 评审发现共享日期 helper可接受长度10的ISO week date；局部 canonical校验后 `2026-W37-1` 的 range/full均在Admin调用前返回原固定400，未改共享helper。

```text
PYTHONDONTWRITEBYTECODE=1 ... python -m py_compile <route/consumer/request_auth/test>
git diff --cached --check
```

两项 exit0。Dream任务另报告扩大回归 `309 passed + 4 subtests`，只有既有FastAPI `on_event` deprecation warnings；Markdown path/inventory、AST fence均exit0。

## Source-only AST 关闭证据

```text
/Users/dmeck/project/ink-dream-memory/.venv/bin/python /private/tmp/ink-auth-migration-validation/scan-dream-current-db-closure-after-picture-101-source-only.py
```

exit0，`parse_errors=[]`。同一算法扫描526个排除dot-dir/venv模块：production entry80、SQL module52、SQL literal496、driver/database import module32、legacy helper call60、transaction/connection call457、Admin-data module27、operation name117。相对 local-data `433885c4` 后，driver/database import module减1、legacy helper call减3、Admin-data module加1、operation name加2；picture route不再出现在legacy import/helper列表。机器回执为 [dream-db-closure-after-picture-101-source-only.json](dream-db-closure-after-picture-101-source-only.json)。

## 范围限制

以上没有连接正常Admin/PostgreSQL，也没有用指定账户打开真实图片页面。`database.py`中的旧picture helper定义仍存在但已不在三个生产路由调用链；其余60个legacy helper call继续迁移。
