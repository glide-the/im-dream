# AGENTS Instructions
本仓库是 Ink & Memory

## Vibe Contract
- Any functional, architectural, or coding-style change must update affected folder docs and file headers before session end.
- Prefer reuse-first refactor: search existing modules/components before adding new implementations.
- Avoid hard-coded business IDs, thresholds, hosts, paths, or policy values; resolve to env/config/policy first.

## Source Of Truth
- Root pointer: `CLAUDE.md`
- Folder contracts: `**/.folder.md`
- Rules index: `docs/rules/README.md`
- Cursor rules: `.cursor/rules/*.mdc`

## Validation
- Run requested validation commands after meaningful changes.
- When touching docs, verify Markdown inventory and referenced paths remain valid.
- Report concrete evidence (`command`, exit code, key output) in the final summary.

## 数据库 Schema 协议

- 共享 PostgreSQL Schema 由 `https://github.com/glide-the/ink-admin-memory` 项目的`/drizzle` 唯一管理。
- 禁止新增 Alembic revision、Alembic version table、runtime DDL、自动建表或 SQLite fallback。
- Dream 需要新增表、字段、索引、约束、函数或触发器时，必须先在 Admin Drizzle 中提交前向 migration 和 capability。
- Dream 代码只能依赖已经发布的 capability，不得依赖 Drizzle 全局最新 head。
- 缺少 capability 时必须 fail closed，不得在 Dream 仓库临时补建 schema。
- SQLite 代码只允许存在于明确命名的数据导入或测试 fixture 中，且不得成为运行时依赖。
- 跨版本发布必须遵循 expand → Dream 双版本兼容 → backfill/validate → contract。

## 工作区安全

- 当前仓库可能同时包含用户和其他 Agent 的未提交改动；不得回退、覆盖或格式化无关文件。
- PostgreSQL 写入测试只允许使用明确命名、可删除的隔离数据库，并必须验证目标身份。

## 单一运行路径与 Harness 协议

- 本项目禁止按 `development`、`test`、`production`、`unknown` 等部署环境名称实现多套业务行为；设计、生产代码和数据库合同不得使用 `INK_ENVIRONMENT` 解锁功能、改变状态机、选择 Agent runtime、跳过持久化或降低权限校验。
- Dream/Chat 在所有部署中必须执行同一条生产业务路径。运行位置使用服务器所有的明确 topology/capability（例如 `local_persistent`）表达，不得把测试环境名称当作 runtime capability。
- 测试 harness 的差异只能存在于 `backend/tests/**`、`frontend/e2e/**` 或明确命名的验证脚本中，并通过依赖注入、隔离数据库、fake/real provider 选择、显式 capability、显式 secret 和可控 clock 配置；禁止在业务模块中放置 test-only fallback、固定测试密钥或“非测试环境直接 return”的分支。
- Harness 必须调用公开生产入口和真实 DTO/协议，不得复制一套测试入口、状态机、SSE、parser、reducer 或 runtime。真实模型测试必须显式选择模型、限制调用次数、保护正文与凭证并清理自有进程/端口/临时资源。
- 环境缺少必需 secret、数据库 capability、插件摘要或权限时应由对应配置/业务边界 fail closed；不得通过笼统的环境标签推断这些事实。
