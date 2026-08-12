# Repository guidelines

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
