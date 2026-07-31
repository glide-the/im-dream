# task_201_backend_story-workspace-schema

## 1. 任务标题

Story Workspace 数据库 Schema 与数据表初始化

## 2. 关联 Issue

- **Issue ID**: `SUO-201-BE-001`
- **Issue 标题**: 数据库 Schema 与数据表初始化
- **类型**: backend
- **优先级**: P0
- **标签**: `database`, `schema`, `migration`
- **来源设计稿**:
  - `docs/design/story-workspace/story-workspace-layout-design.md` §5.1–5.5（数据表结构）
  - `docs/design/story-workspace/story-workspace-prd.md` §3.1 `DEC-004`（`story-workspace` 前缀命名）
- **Issue 清单**: `docs/issue/ISSUES_story-workspace.md` §3 Issue 明细

## 3. 任务目标

根据设计稿数据表结构，在现有 SQLite 数据库中创建 story-workspace 相关的数据表及索引。包括：故事表、角色表、场景表、故事-角色关联表、场景-角色关联表、工作区表。所有表名使用 `story_workspace_*` 前缀。

**核心约束**：
- 项目使用 **SQLite**（非 PostgreSQL），因此设计稿中提到的 `pg_trgm` / `gin_trgm_ops` 索引不可用
- 搜索功能改用 SQLite `LIKE` 或 `FTS5` 实现
- Migration 必须幂等（`CREATE TABLE IF NOT EXISTS` + `ALTER TABLE` 带异常捕获）
- 所有表和索引需支持回滚（`DROP TABLE` 逆操作）

## 4. 实现步骤

### Step 1: 在 `database.py` 的 `create_tables()` 中追加 story-workspace 表创建逻辑

按以下顺序创建 6 张表：

1. **`story_workspace_workspaces`** — 工作区表（先创建，因为其他表外键依赖它）
2. **`story_workspace_stories`** — 故事/剧本表
3. **`story_workspace_characters`** — 角色表
4. **`story_workspace_scenes`** — 场景表
5. **`story_workspace_story_characters`** — 故事-角色关联表
6. **`story_workspace_scene_characters`** — 场景-角色关联表

### Step 2: 定义各表字段（严格对齐设计稿 §5.1–5.5）

#### 2.1 `story_workspace_workspaces`

| 字段 | SQLite 类型 | 约束 | 默认值 | 说明 |
|------|------------|------|--------|------|
| `id` | TEXT | PRIMARY KEY | — | UUID v4 |
| `name` | TEXT | NOT NULL | — | 工作区名称 |
| `owner_id` | INTEGER | NOT NULL | — | 所有者 ID（外键 → users.id） |
| `settings` | TEXT | | '{}' | 工作区设置（JSON 字符串） |
| `created_at` | DATETIME | NOT NULL | CURRENT_TIMESTAMP | 创建时间 |
| `updated_at` | DATETIME | NOT NULL | CURRENT_TIMESTAMP | 更新时间 |

#### 2.2 `story_workspace_stories`

| 字段 | SQLite 类型 | 约束 | 默认值 | 说明 |
|------|------------|------|--------|------|
| `id` | TEXT | PRIMARY KEY | — | UUID v4 |
| `identifier` | TEXT | NOT NULL | — | 业务标识（如 `story-001`） |
| `title` | TEXT | NOT NULL | — | 故事标题（Agent 生成） |
| `description` | TEXT | | NULL | 故事描述（Agent 生成） |
| `status` | TEXT | NOT NULL | 'draft' | 内容状态：draft / published / archived |
| `review_status` | TEXT | NOT NULL | 'pending' | **审阅状态：pending / confirmed / rejected** |
| `type` | TEXT | NOT NULL | 'short' | 类型：short / long / script / outline |
| `content` | TEXT | | NULL | 故事内容（Agent 生成的 Markdown） |
| `author_id` | INTEGER | NOT NULL | — | 创建者 ID（外键 → users.id） |
| `workspace_id` | TEXT | NOT NULL | — | 所属工作区 ID（外键 → story_workspace_workspaces.id） |
| `character_count` | INTEGER | NOT NULL | 0 | 关联角色数（冗余，加速查询） |
| `scene_count` | INTEGER | NOT NULL | 0 | 关联场景数（冗余，加速查询） |
| `agent_generated` | INTEGER | NOT NULL | 1 | **是否由 Agent 生成（0/1）** |
| `agent_session_id` | TEXT | | NULL | **Agent 会话 ID（关联 chat_thread.id）** |
| `review_notes` | TEXT | | NULL | **用户审阅备注/修改意见** |
| `created_at` | DATETIME | NOT NULL | CURRENT_TIMESTAMP | 创建时间（Agent 生成时间） |
| `updated_at` | DATETIME | NOT NULL | CURRENT_TIMESTAMP | 更新时间 |
| `confirmed_at` | DATETIME | | NULL | **用户确认时间** |
| `published_at` | DATETIME | | NULL | 发布时间 |

**索引**:
- `idx_sw_stories_author` ON `story_workspace_stories(author_id, updated_at DESC)`
- `idx_sw_stories_review_status` ON `story_workspace_stories(review_status, updated_at DESC)`
- `idx_sw_stories_status` ON `story_workspace_stories(status, updated_at DESC)`
- `idx_sw_stories_type` ON `story_workspace_stories(type, updated_at DESC)`
- `idx_sw_stories_search` ON `story_workspace_stories(title)` — SQLite 用普通 B-tree 索引 + LIKE
- `idx_sw_stories_agent` ON `story_workspace_stories(agent_session_id)`

#### 2.3 `story_workspace_characters`

| 字段 | SQLite 类型 | 约束 | 默认值 | 说明 |
|------|------------|------|--------|------|
| `id` | TEXT | PRIMARY KEY | — | UUID v4 |
| `identifier` | TEXT | NOT NULL | — | 业务标识 |
| `name` | TEXT | NOT NULL | — | 角色名称（Agent 生成，用户可编辑） |
| `avatar_url` | TEXT | | NULL | 头像 URL |
| `identity` | TEXT | | NULL | 角色身份/职业（Agent 生成） |
| `personality` | TEXT | | NULL | 性格描述（Agent 生成） |
| `background` | TEXT | | NULL | 背景故事（Agent 生成） |
| `catchphrase` | TEXT | | NULL | 口头禅（Agent 生成） |
| `tags` | TEXT | | '[]' | 性格标签（JSON 字符串数组） |
| `notes` | TEXT | | NULL | 用户审阅备注 |
| `author_id` | INTEGER | NOT NULL | — | 创建者 ID（外键 → users.id） |
| `workspace_id` | TEXT | NOT NULL | — | 所属工作区 ID |
| `story_count` | INTEGER | NOT NULL | 0 | 关联故事数（冗余） |
| `review_status` | TEXT | NOT NULL | 'pending' | **审阅状态：pending / confirmed / rejected** |
| `agent_generated` | INTEGER | NOT NULL | 1 | **是否由 Agent 生成（0/1）** |
| `created_at` | DATETIME | NOT NULL | CURRENT_TIMESTAMP | 创建时间 |
| `updated_at` | DATETIME | NOT NULL | CURRENT_TIMESTAMP | 更新时间 |

**索引**:
- `idx_sw_characters_author` ON `story_workspace_characters(author_id, updated_at DESC)`
- `idx_sw_characters_name` ON `story_workspace_characters(name)` — B-tree + LIKE
- `idx_sw_characters_review` ON `story_workspace_characters(review_status, updated_at DESC)`

#### 2.4 `story_workspace_scenes`

| 字段 | SQLite 类型 | 约束 | 默认值 | 说明 |
|------|------------|------|--------|------|
| `id` | TEXT | PRIMARY KEY | — | UUID v4 |
| `identifier` | TEXT | NOT NULL | — | 业务标识 |
| `name` | TEXT | NOT NULL | — | 场景名称（Agent 生成） |
| `description` | TEXT | | NULL | 场景描述（Agent 生成） |
| `story_id` | TEXT | | NULL | 所属故事 ID（外键 → story_workspace_stories.id） |
| `author_id` | INTEGER | NOT NULL | — | 创建者 ID |
| `workspace_id` | TEXT | NOT NULL | — | 所属工作区 ID |
| `character_count` | INTEGER | NOT NULL | 0 | 出场角色数（冗余） |
| `order_index` | INTEGER | NOT NULL | 0 | 在故事中的顺序 |
| `review_status` | TEXT | NOT NULL | 'pending' | **审阅状态：pending / confirmed / rejected** |
| `agent_generated` | INTEGER | NOT NULL | 1 | **是否由 Agent 生成（0/1）** |
| `created_at` | DATETIME | NOT NULL | CURRENT_TIMESTAMP | 创建时间 |
| `updated_at` | DATETIME | NOT NULL | CURRENT_TIMESTAMP | 更新时间 |

**索引**:
- `idx_sw_scenes_story` ON `story_workspace_scenes(story_id, order_index)`
- `idx_sw_scenes_author` ON `story_workspace_scenes(author_id, updated_at DESC)`
- `idx_sw_scenes_review` ON `story_workspace_scenes(review_status, updated_at DESC)`

#### 2.5 `story_workspace_story_characters`（关联表）

| 字段 | SQLite 类型 | 约束 | 说明 |
|------|------------|------|------|
| `story_id` | TEXT | NOT NULL, PK(1) | 故事 ID |
| `character_id` | TEXT | NOT NULL, PK(2) | 角色 ID |
| `role_type` | TEXT | | 主角 / 配角 / 龙套 |
| `created_at` | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 关联时间 |

**主键**: (`story_id`, `character_id`)
**外键**: `story_id` → `story_workspace_stories.id`, `character_id` → `story_workspace_characters.id`

#### 2.6 `story_workspace_scene_characters`（关联表）

| 字段 | SQLite 类型 | 约束 | 说明 |
|------|------------|------|------|
| `scene_id` | TEXT | NOT NULL, PK(1) | 场景 ID |
| `character_id` | TEXT | NOT NULL, PK(2) | 角色 ID |
| `created_at` | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 关联时间 |

**主键**: (`scene_id`, `character_id`)
**外键**: `scene_id` → `story_workspace_scenes.id`, `character_id` → `story_workspace_characters.id`

### Step 3: 实现幂等 Migration 模式

遵循项目现有模式（`database.py` 中已有）：

```python
# 1. CREATE TABLE IF NOT EXISTS
db.execute("""
CREATE TABLE IF NOT EXISTS story_workspace_workspaces (
  id TEXT PRIMARY KEY,
  ...
)
""")

# 2. 索引 CREATE INDEX IF NOT EXISTS
db.execute("CREATE INDEX IF NOT EXISTS idx_sw_workspaces_owner ON story_workspace_workspaces(owner_id)")

# 3. 列迁移（try/except 静默跳过已存在列）
for col, col_type in (("settings", "TEXT"), ("some_new_col", "TEXT")):
    try:
        db.execute(f"ALTER TABLE story_workspace_workspaces ADD COLUMN {col} {col_type}")
    except Exception:
        pass
```

### Step 4: 实现回滚函数

在 `database.py` 中新增 `drop_story_workspace_tables(db)` 函数（用于测试和紧急回滚）：

```python
def drop_story_workspace_tables(db):
    """Drop all story-workspace tables. For migration rollback / testing only."""
    tables = [
        "story_workspace_scene_characters",
        "story_workspace_story_characters",
        "story_workspace_scenes",
        "story_workspace_characters",
        "story_workspace_stories",
        "story_workspace_workspaces",
    ]
    for table in tables:
        db.execute(f"DROP TABLE IF EXISTS {table}")
    db.commit()
```

### Step 5: 验证约束一致性

- [ ] 所有外键约束指向正确的父表
- [ ] 所有 NOT NULL 约束与设计稿一致
- [ ] 所有默认值（DEFAULT）与设计稿一致
- [ ] `review_status` 仅允许 `pending` / `confirmed` / `rejected`
- [ ] `status` 仅允许 `draft` / `published` / `archived`
- [ ] `type` 仅允许 `short` / `long` / `script` / `outline`
- [ ] `agent_generated` 使用 INTEGER 0/1（SQLite 无原生 boolean）
- [ ] `tags` 使用 TEXT 存储 JSON 数组字符串

## 5. 涉及文件路径

| 路径 | 说明 |
|------|------|
| `backend/database.py` | 核心文件：在 `create_tables()` 中追加表创建逻辑；新增 `drop_story_workspace_tables()` |
| `backend/data/ink-and-memory.db` | 数据库文件（运行时自动生成） |
| `backend/tests/test_database.py` | 现有测试文件，需追加 schema 测试 |

## 6. 输入 / 输出说明

### 输入

- 设计稿数据表结构：`docs/design/story-workspace/story-workspace-layout-design.md` §5.1–5.5
- 现有数据库模式：`backend/database.py` 中 `create_tables()` 的实现模式
- 现有用户表：`users(id INTEGER PRIMARY KEY AUTOINCREMENT, ...)`
- 现有 chat_thread 表：`chat_thread(id TEXT PRIMARY KEY, ...)` — 用于 `agent_session_id` 外键关联

### 输出

- `backend/database.py` 更新：追加 6 张表的 `CREATE TABLE IF NOT EXISTS` 语句
- `backend/database.py` 更新：追加所有索引的 `CREATE INDEX IF NOT EXISTS` 语句
- `backend/database.py` 更新：新增 `drop_story_workspace_tables()` 回滚函数
- `backend/tests/test_database.py` 更新：追加 schema 验证测试

## 7. 依赖项

| 依赖 | 类型 | 说明 |
|------|------|------|
| 无 | — | 本任务无前置依赖，是后端工作的基础 |
| `users` 表 | 现有 | 外键依赖：所有 story-workspace 表通过 `author_id` 关联 `users.id` |
| `chat_thread` 表 | 现有 | 逻辑关联：`agent_session_id` 对应 `chat_thread.id`（不强制外键） |

## 8. 测试策略

### 8.1 Schema 结构测试

```python
def test_story_workspace_tables_exist():
    """Verify all story-workspace tables are created."""
    db = get_db()
    tables = ["story_workspace_workspaces", "story_workspace_stories",
              "story_workspace_characters", "story_workspace_scenes",
              "story_workspace_story_characters", "story_workspace_scene_characters"]
    for table in tables:
        result = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        assert result is not None, f"Table {table} should exist"
```

### 8.2 索引存在测试

```python
def test_story_workspace_indexes_exist():
    """Verify all expected indexes are created."""
    db = get_db()
    indexes = ["idx_sw_stories_review_status", "idx_sw_stories_author",
               "idx_sw_characters_review", "idx_sw_scenes_story", ...]
    for idx in indexes:
        result = db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name=?", (idx,)
        ).fetchone()
        assert result is not None, f"Index {idx} should exist"
```

### 8.3 约束测试

```python
def test_story_review_status_constraint():
    """Verify review_status only accepts valid values."""
    db = get_db()
    # SQLite 无原生 CHECK 约束强制执行（除非 PRAGMA foreign_keys = ON）
    # 测试通过应用层验证
```

### 8.4 Migration 幂等性测试

```python
def test_migration_idempotent():
    """Running create_tables twice should not fail."""
    db = get_db()
    create_tables(db)  # First run
    create_tables(db)  # Second run — should not raise
```

### 8.5 回滚测试

```python
def test_drop_story_workspace_tables():
    """Verify drop function removes all tables."""
    db = get_db()
    drop_story_workspace_tables(db)
    result = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'story_workspace_%'"
    ).fetchall()
    assert len(result) == 0
```

## 9. 完成标志

- [ ] `story_workspace_stories` 表创建，含所有字段（id, identifier, title, description, status, review_status, type, content, author_id, workspace_id, character_count, scene_count, agent_generated, agent_session_id, review_notes, created_at, updated_at, confirmed_at, published_at）
- [ ] `story_workspace_characters` 表创建，含所有字段
- [ ] `story_workspace_scenes` 表创建，含所有字段
- [ ] `story_workspace_story_characters` 关联表创建
- [ ] `story_workspace_scene_characters` 关联表创建
- [ ] `story_workspace_workspaces` 表创建
- [ ] 所有设计稿中指定的索引已创建
- [ ] Migration 文件可回滚（`drop_story_workspace_tables` 可用）
- [ ] 数据库约束（外键、非空、默认值）与设计稿一致
- [ ] 测试通过：`test_story_workspace_tables_exist`
- [ ] 测试通过：`test_story_workspace_indexes_exist`
- [ ] 测试通过：`test_migration_idempotent`

## 10. 风险提示

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| **SQLite 方言差异** | 高 | 设计稿假设 PostgreSQL（`gin_trgm_ops`），实际项目用 SQLite。搜索索引改用 B-tree + `LIKE '%term%'`；`tags` 数组改用 JSON 字符串存储 |
| **无原生 boolean 类型** | 中 | SQLite 使用 INTEGER 0/1 表示 boolean。`agent_generated` 字段需文档化此约定 |
| **无原生 enum 类型** | 中 | SQLite 无 CHECK 约束强制执行（除非 `PRAGMA foreign_keys = ON`）。`review_status` / `status` / `type` 的 enum 约束需在应用层校验 |
| **外键约束默认关闭** | 中 | SQLite 默认 `PRAGMA foreign_keys = OFF`。如需强制执行外键，需在连接时显式开启 |
| **Migration 与现有数据冲突** | 低 | 使用 `CREATE TABLE IF NOT EXISTS` 和 `try/except` 模式，与项目现有 migration 风格一致 |
| **chat_thread.id 类型不匹配** | 低 | `chat_thread.id` 是 TEXT，`agent_session_id` 也是 TEXT，类型一致。但 `users.id` 是 INTEGER，`author_id` 需匹配 INTEGER |

## 11. 允许与禁止修改范围

- **仅允许修改**：`backend/database.py`、`backend/tests/test_database.py`。
- **禁止修改**：`docs/design/`、`docs/issue/`、`docs/stage/`、`docs/exec/`、`docs/prd/` 以及任何前端代码或实现代码。
- **禁止行为**：不得把本 task 文档当作 execute 授权直接实现；不得修改设计稿或 Issue 清单。

## 12. 下游执行提示

- **StagePlanner 注意**: 本任务是后端所有工作的前置基础。Stage 排期时应将本任务放在最前，且需等待完成后才能启动 `SUO-201-BE-002`（REST API）。
- **共享类型对齐**: `SUO-201-SH-002`（命名规范与类型定义）可与本任务并行，但建议先完成本任务以确定最终字段名。后端类型模型是规范源，Schema 字段名应与其保持一致。
- **前端消费边界**: 本任务完成后，前端可通过 `database.py` 的 schema 了解字段结构，但正式的类型定义在 `SUO-201-SH-002` 中产出。

## 12. 执行边界

### 允许修改范围
- `backend/database.py` — 在 `create_tables()` 中追加 story-workspace 表的 `CREATE TABLE IF NOT EXISTS` 和 `CREATE INDEX IF NOT EXISTS` 语句；新增 `drop_story_workspace_tables()` 回滚函数。
- `backend/tests/test_database.py` — 追加 schema 验证、索引验证、幂等性测试、回滚测试。
- 如需新增独立的 migration 文件，仅允许放在 `backend/src/db/migrations/`（若项目存在该目录）。

### 禁止修改范围
- ❌ `docs/design/`、`docs/issue/`、`docs/stage/`、`docs/exec/` — 任何设计阶段产物。
- ❌ `docs/task/TASK-REQUIREMENT-FORMAT.md` — 提示词模板。
- ❌ 前端代码、前端 task 文件 — 不在本 Agent 职责范围内。
- ❌ 现有 `users`、`chat_thread` 等无关表的结构 — 仅新增 story-workspace 相关表，不修改现有表。
- ❌ 实现代码（REST 路由、Service、UI）— 本任务仅为 Schema 与 Migration，不实现业务逻辑。

### 明确排除项（本期不在范围）
- **复杂画布编辑器** — 故事板/时间线可视化编辑的数据模型不在本期；本期仅数据表呈现。
- **视频生成模块** — 镜头生成、视频预览相关字段不在本期 Schema 中。
- **移动端适配** — 后端 API 不假设移动端消费者，但 Schema 本身与设备无关；本期明确排除移动端/平板端适配需求。
- **用户手动创建内容** — 所有内容均由 Agent 生成，`agent_generated` 默认 `1`；本期不设计用户手动创建的数据模型。
- **实时协作** — 无多创作者同时编辑的并发控制字段（如 `version`、`lock_owner_id`）。
- **四视角转面图** — 角色表 `avatar_url` 仅支持单张头像，不扩展为多视角。
- **历史版本管理** — 无版本快照表。
- **@提及系统** — 无提及/通知相关表。
- **计费/积分系统** — 无积分消耗、配额限制相关字段。
