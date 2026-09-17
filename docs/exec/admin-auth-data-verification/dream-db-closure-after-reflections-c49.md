<!-- [Input] Dream c49 Reflections commit plus current dirty-safe Python source tree and baseline inventory. -->
<!-- [Output] Corrected AST-only production database closure counts and next-domain evidence. -->
<!-- [Pos] Interim migration inventory; it cannot prove runtime or final production closure by itself. -->
<!-- [Sync] 2026-09-15: exclude backend/.venv after preserving the initial harness defect. -->

# Reflections 后 Dream 数据库访问闭包扫描

首次运行旧 scanner 时发现 worktree 新增 `backend/.venv`。旧脚本把其中 2053 个依赖模块算作生产源码，得到 2575 modules / 120 production entries；该结果只证明 harness 分类错误，不作为关闭证据。未覆盖该回执，改用新输出文件并在 source selection 中排除点目录、`node_modules` 和 `__pycache__`。

修正版命令：

```text
python3 /private/tmp/ink-auth-migration-validation/scan-dream-current-db-closure-after-reflections-c49-source-only.py
```

- cwd: `/Users/dmeck/project/ink-dream-memory`
- exit: `0`
- HEAD: `c49fca694af560e21ecd16aab5efe29167729c27`
- parsed repository Python modules: `522`
- production entries: `80`
- production SQL modules/literals: `52 / 496`
- production driver or legacy database import modules: `34`
- production legacy helper calls: `66`
- production transaction/connection calls: `457`
- production Admin-data import modules / discovered static operation names: `26 / 113`
- parse errors: `0`

Reflections 路由已不在旧 helper 列表。剩余 helper 集中于 Story/Deck workflow、Claude Plugin、local-data/pictures、MCP/Notion、启动和若干运行时服务。SQL 字面量包括尚未切换的生产路径与保留的内部实现，最终关闭必须再结合调用闭包、依赖注入和公开路由运行 fence；不能仅凭此计数声明完成。
