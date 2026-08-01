# Exec Report: task_201 - Story Workspace 数据库 Schema 与 Migration

## 1. 执行上下文

- **Paperclip Issue**: `SUO-212` — `[execute][story-workspace][task_201] 数据库 Schema 与 Migration`
- **逻辑 Issue**: `SUO-201-BE-001`（父 Issue `SUO-198`）
- **Task ID**: `task_201`
- **Task 文档**: `docs/task/task_201_backend_story-workspace-schema.md`
- **关联设计稿**:
  - `docs/design/story-workspace/story-workspace-layout-design.md` §5.1–5.5
  - `docs/design/story-workspace/story-workspace-prd.md` §3.1 `DEC-004`
- **关联 Stage**: `docs/stage/stage_story-workspace.md`（`stage_001_story-workspace`，Wave 1）
- **执行 Agent**: `ExecTaskAgent` (`2a7a15fe-2ebb-4dc5-91a8-48ae2bcc5471`)
- **执行时间**: `2026-08-01 08:00 CST (+0800)`
- **执行锁**: Paperclip harness 已为本 run checkout，未重复调用 checkout API
- **完成状态**: `completed`

## 2. 执行准入与 TASK-REQUIREMENT-FORMAT 填充摘要

- **模板路径**: `docs/task/TASK-REQUIREMENT-FORMAT.md`
- **模板处理**: 完整读取只读模板；未修改模板或其他 task 文档
- **任务输入**:
  - Title: `[execute][story-workspace][task_201] 数据库 Schema 与 Migration`
  - Identifier: `SUO-212`
  - Priority: `medium`
  - Description: 当前 Issue 中的 `task_201` 执行目标、关联文档、允许/禁止范围、验收、测试与回滚要求
- **格式化后的执行目标**: 在项目现有 SQLite `create_tables()` 迁移模式内创建 6 张 `story_workspace_*` 表及指定索引，提供幂等执行与回滚能力，并用隔离数据库验证完整 Schema 合同
- **关键约束**:
  - 只修改 `backend/database.py`、`backend/tests/test_database.py` 与本报告
  - 不修改既有 `users`、`chat_thread` 等表
  - 不实现 REST、Service、UI、复杂画布、视频、移动端、手工创建等排除项
  - `agent_session_id` 按 Task 合同仅做逻辑关联，不强制外键
- **验收条件**: 6 表、指定索引、外键/非空/默认值一致、迁移幂等、回滚函数可用
- **模型生成方式**: 当前 ExecTaskAgent 模型使用格式化后的模板与任务输入生成执行任务；环境未配置外部 Anthropic SDK / API key，因此未走外部 Claude API 调用路径

## 3. 模型生成的执行任务

范围校验通过的模型输出如下：

1. 在 `backend/database.py:create_tables()` 中按父表到子表顺序创建工作区、故事、角色、场景及两张关联表。
2. 将 Task 中的枚举合同落为 SQLite `CHECK`，将 Agent 布尔标志落为受约束的 `INTEGER 0/1`；按 Task 定义配置外键、非空和默认值。
3. 使用 `CREATE INDEX IF NOT EXISTS` 创建 13 个 Task 指定的 SQLite B-tree 索引；不引入 PostgreSQL `gin_trgm_ops`。
4. 新增 `drop_story_workspace_tables(db)`，按逆依赖顺序删除 6 表并提交事务。
5. 在 `backend/tests/test_database.py` 中增加隔离的内存 SQLite 测试，覆盖表/列合同、索引列序与 DESC、外键、默认值、约束、幂等与回滚。
6. 不创建独立 migration 文件，因为 `backend/src/db/migrations/` 目录不存在，且本次变更可遵循项目既有 `database.py` 约定完成。

## 4. 实现变更记录

| 文件 | 操作 | 说明 |
|---|---|---|
| `backend/database.py` | update | 新增 6 张 `story_workspace_*` 表、13 个索引、枚举/布尔检查约束及 `drop_story_workspace_tables(db)` |
| `backend/tests/test_database.py` | update | 新增 `StoryWorkspaceDatabaseTestCase` 的 6 个隔离测试及完整 Schema 期望合同 |
| `docs/exec/exec_task_201_story-workspace-schema.md` | create | 本次执行任务、变更、测试、证据、风险和回滚报告 |

### 4.1 新增表

1. `story_workspace_workspaces`
2. `story_workspace_stories`
3. `story_workspace_characters`
4. `story_workspace_scenes`
5. `story_workspace_story_characters`
6. `story_workspace_scene_characters`

### 4.2 新增索引

- `idx_sw_workspaces_owner`
- `idx_sw_stories_author`
- `idx_sw_stories_review_status`
- `idx_sw_stories_status`
- `idx_sw_stories_type`
- `idx_sw_stories_search`
- `idx_sw_stories_agent`
- `idx_sw_characters_author`
- `idx_sw_characters_name`
- `idx_sw_characters_review`
- `idx_sw_scenes_story`
- `idx_sw_scenes_author`
- `idx_sw_scenes_review`

## 5. 测试与验证

### 5.1 已执行测试

| 命令 | 结果 |
|---|---|
| `cd backend && python -m py_compile database.py tests/test_database.py` | PASS，无语法错误 |
| `cd backend && python -m unittest tests.test_database.StoryWorkspaceDatabaseTestCase -v` | PASS，`Ran 6 tests` / `OK` |
| 内存 SQLite 中连续执行两次 `create_tables()`，查询 `sqlite_master`，再调用 `drop_story_workspace_tables()` | PASS，`tables=6`、`indexes=13`、`remaining_after_rollback=0` |
| `git diff --check` | PASS，无空白或 patch 格式错误 |

### 5.2 测试覆盖结果

- `test_story_workspace_tables_exist`: PASS
- `test_story_workspace_schema_contract`: PASS
  - 精确列集合与 SQLite 类型
  - `NOT NULL`、默认值、主键顺序
  - 每张表的精确外键集合
- `test_story_workspace_indexes_exist`: PASS
  - 13 个索引存在
  - 索引列顺序及 `updated_at DESC` 一致
- `test_story_workspace_defaults_and_constraints`: PASS
  - 实际插入后默认值正确
  - 非法 `status` / `review_status` / `type` / `agent_generated` 被拒绝
  - 无效 `owner_id` 外键被拒绝
- `test_story_workspace_migration_idempotent`: PASS
- `test_drop_story_workspace_tables`: PASS，且回滚后可重新创建

### 5.3 验证证据

独立查询结果：

```text
tables=6 ['story_workspace_characters', 'story_workspace_scene_characters',
          'story_workspace_scenes', 'story_workspace_stories',
          'story_workspace_story_characters', 'story_workspace_workspaces']
indexes=13 ['idx_sw_characters_author', 'idx_sw_characters_name',
            'idx_sw_characters_review', 'idx_sw_scenes_author',
            'idx_sw_scenes_review', 'idx_sw_scenes_story',
            'idx_sw_stories_agent', 'idx_sw_stories_author',
            'idx_sw_stories_review_status', 'idx_sw_stories_search',
            'idx_sw_stories_status', 'idx_sw_stories_type',
            'idx_sw_workspaces_owner']
remaining_after_rollback=0
```

### 5.4 未执行测试及原因

- 未运行全量 backend 测试：本 Task 仅要求数据库 Schema/Migration，已运行能直接证明合同的最小隔离测试。
- 未运行 pytest：当前解释器没有安装 pytest；测试使用项目现有脚本可兼容的 Python 标准库 `unittest`，无需扩大依赖范围。
- 未在 `backend/data/ink-and-memory.db` 上执行迁移：避免在验证阶段改写用户/运行时数据库；内存 SQLite 使用同一 `create_tables()` 代码路径完成验证。

## 6. 风险与阻塞

- **阻塞**: 无。
- **残余风险**:
  - SQLite 的普通 B-tree 索引不能优化所有前导通配符 `LIKE '%term%'` 查询；本 Task 明确排除 PostgreSQL trigram，并接受普通索引方案。
  - 回滚函数会永久删除全部 Story Workspace 数据，只能在确认备份或测试数据库中调用。
- **并行工作区说明**: 范围检查时发现其他任务生成的 `backend/types/` 与 `docs/exec/exec_task_205_story-workspace-shared-types.md`；本任务未读取、修改或纳入变更摘要。
- **需要上游澄清的问题**: 无。

## 7. 完成状态

- [x] 已完成模板读取、任务填充与模型执行任务生成
- [x] 已完成 6 张表与指定索引实现
- [x] 已完成外键、非空、默认值及值域约束
- [x] 已完成幂等与回滚实现
- [x] 已完成 Task §8 对应测试
- [x] 已记录变更、命令、结果与未验证项
- [x] 已满足当前 Issue 验收条件
- [x] 可进入 review / audit

## 8. 回滚建议

### 8.1 数据库回滚

在确认已备份 Story Workspace 数据后，将项目数据库连接传入：

```python
database.drop_story_workspace_tables(db_connection)
```

函数会按 `scene_characters → story_characters → scenes → characters → stories → workspaces` 的逆依赖顺序删除表；表所属索引由 SQLite 同步删除。

### 8.2 代码回滚

- 回退 `backend/database.py` 中本次 Story Workspace Schema、索引与回滚函数。
- 回退 `backend/tests/test_database.py` 中 `StoryWorkspaceDatabaseTestCase` 及其期望合同常量。
- 归档或删除本执行报告。
- 若本变更已经形成独立提交，优先使用可审计的 `git revert <commit>`，避免影响并行任务文件。

## 9. 执行完成报告

`task_201` 已完成。实现仅落在授权的两个后端文件和本 Issue 指定报告中；隔离测试与独立 SQLite 证据均满足 6 表、13 索引、合同约束、幂等和回滚验收要求。建议将 `SUO-212` 标记为 `done`，后续可由 review / audit 复核。
