# task_deck_001_backend_manifest-model

## 1. 任务标题

Deck Plugin Manifest 与发布版本模型

## 2. 关联 Issue

- **Issue ID**: `DECK-001`
- **Issue 标题**: Deck Plugin Manifest 与发布版本模型
- **类型**: backend
- **优先级**: P0
- **标签**: `deck-plugin`, `manifest`, `schema`
- **来源设计稿**:
  - `docs/design/deck-plugin-voice-ink-dream-integration.md` §5.1, §5.2, §5.4
- **Issue 清单**: `docs/issue/ISSUES_deck-plugin-voice-ink-dream-integration.md` §3 DECK-001

## 3. 任务目标

实现 Deck Plugin 的 manifest 模型和发布版本管理，作为所有后续 Deck Plugin 相关能力的基础。包括：

1. `DeckPluginManifestV1` schema 定义与字段校验
2. 发布版本状态机（`draft` → `validating` → `published` → `deprecated` → `revoked`）
3. manifest 完整性校验（标识唯一性、schema 结构、能力子集、来源 allowlist）
4. 命名隔离：`deck_plugin_*` 前缀用于业务工作流字段

## 4. 实现步骤

### Step 1: 定义 `DeckPluginManifestV1` 数据模型

在 `backend/models/deck_plugin.py`（新建）中定义 Pydantic / dataclass 模型：

```python
class DeckPluginManifestV1(BaseModel):
    schema_version: Literal["deck-plugin/v1"]
    deck_plugin_id: str          # 全局稳定标识，如 "voice-decks.story-dramatize"
    deck_plugin_version: str     # SemVer，如 "3.1.0"
    display_name: str
    description: str
    author: str
    status: DeckPluginReleaseStatus  # draft/validating/published/deprecated/revoked
    workflow: WorkflowSpec
    compatibility: CompatibilitySpec
    desk: DeskContractSpec
    capabilities: list[str]
    runtime: RuntimeSpec
    dependencies: DependenciesSpec
```

子模型：
- `WorkflowSpec`: `workflow_definition_ref`, `input_schema_ref`, `output_schema_ref`, `steps`
- `CompatibilitySpec`: `deck_host_api`, `claude_agent_contract`, `claude_code`, `story_output_schema`, `desk_snapshot_contract`
- `DeskContractSpec`: `profile_contract`, `required_config_keys`, `secret_ref_kinds`, `allow_profile_versions`
- `RuntimeSpec`: `claude_code_plugins`（列表，每项含 `claude_code_plugin_id`, `source_ref`, `version_constraint`, `required`, `capability_bindings`）
- `DependenciesSpec`: `deck_plugin_releases`（列表）

### Step 2: 定义发布版本状态枚举

```python
class DeckPluginReleaseStatus(str, Enum):
    DRAFT = "draft"           # 可编辑、尚未发布
    VALIDATING = "validating" # 正在解析依赖与校验合同
    PUBLISHED = "published"   # 不可变发布版本
    DEPRECATED = "deprecated" # 可继续解析但不建议新选
    REVOKED = "revoked"       # 安全或合规撤销
```

状态规则：
- 已发布版本禁止回到 `draft`
- 修正必须产生新版本

### Step 3: 实现 manifest 校验器

在 `backend/services/deck_plugin/manifest_validator.py`（新建）中实现：

| 校验项 | 规则 | 失败错误码 |
|---|---|---|
| 标识唯一性 | `deck_plugin_id` 全局稳定；组合键 `deck_plugin_id + deck_plugin_version` 唯一 | `DECK_PLUGIN_MANIFEST_INVALID` |
| SemVer 合规 | `deck_plugin_version` 必须符合 SemVer 2.0 | `DECK_PLUGIN_MANIFEST_INVALID` |
| 工作流引用 | `workflow_definition_ref` 必须是受控、可按版本读取的引用；禁止指向 `latest` | `DECK_PLUGIN_MANIFEST_INVALID` |
| schema 版本 | 输入、输出和 Desk snapshot contract 必须有显式版本 | `DECK_PLUGIN_MANIFEST_INVALID` |
| 能力子集 | 步骤 `required_capabilities` 必须是顶层 `capabilities` 的子集 | `DECK_PLUGIN_MANIFEST_INVALID` |
| 来源 allowlist | 生产来源必须在管理员 allowlist 中 | `DECK_PLUGIN_SOURCE_DENIED` |
| 完整性 | manifest 禁止包含密钥明文和完整 Desk prompt | `DECK_PLUGIN_MANIFEST_INVALID` |
| 降级声明 | optional runtime plugin 或 degraded mode 必须显式声明 | `DECK_PLUGIN_MANIFEST_INVALID` |

### Step 4: 数据库表设计

在 `backend/database.py` 的 `create_tables()` 中追加：

```sql
CREATE TABLE IF NOT EXISTS deck_plugin_releases (
    id TEXT PRIMARY KEY,                    -- release_id: dr_<uuid>
    deck_plugin_id TEXT NOT NULL,
    deck_plugin_version TEXT NOT NULL,
    display_name TEXT NOT NULL,
    description TEXT,
    author TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    manifest_json TEXT NOT NULL,            -- 完整 manifest JSON
    manifest_hash TEXT NOT NULL,            -- sha256:...
    workflow_definition_ref TEXT NOT NULL,
    input_schema_ref TEXT,
    output_schema_ref TEXT,
    capabilities_json TEXT,                 -- JSON 数组
    compatibility_json TEXT,                -- JSON 对象
    desk_contract_json TEXT,                -- JSON 对象
    runtime_spec_json TEXT,                 -- JSON 对象
    dependencies_json TEXT,                 -- JSON 对象
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    published_at DATETIME,
    UNIQUE(deck_plugin_id, deck_plugin_version)
);

CREATE INDEX IF NOT EXISTS idx_deck_plugin_releases_id_version
    ON deck_plugin_releases(deck_plugin_id, deck_plugin_version);
CREATE INDEX IF NOT EXISTS idx_deck_plugin_releases_status
    ON deck_plugin_releases(status);
```

### Step 5: 实现发布服务

在 `backend/services/deck_plugin/release_service.py`（新建）中实现：

- `create_draft(manifest: DeckPluginManifestV1) -> DeckPluginRelease`: 创建 draft
- `validate_release(release_id: str) -> DeckPluginRelease`: draft → validating → published
- `deprecate_release(release_id: str) -> DeckPluginRelease`: published → deprecated
- `revoke_release(release_id: str, reason: str) -> DeckPluginRelease`: published → revoked
- `get_release(deck_plugin_id: str, version: str) -> Optional[DeckPluginRelease]`

## 5. 涉及文件路径

| 路径 | 动作 | 说明 |
|---|---|---|
| `backend/models/deck_plugin.py` | 新建 | Pydantic 模型定义 |
| `backend/services/deck_plugin/manifest_validator.py` | 新建 | manifest 校验器 |
| `backend/services/deck_plugin/release_service.py` | 新建 | 发布版本服务 |
| `backend/database.py` | 修改 | 追加 `deck_plugin_releases` 表 |
| `backend/tests/test_deck_plugin_manifest.py` | 新建 | manifest 校验单元测试 |

## 6. 输入 / 输出说明

**输入**：
- `DeckPluginManifestV1` JSON 对象（来自 Deck Plugin 发布流程）
- 管理员配置的 `source_allowlist`（来源白名单）

**输出**：
- 校验通过的 `DeckPluginRelease` 记录
- 结构化错误码与恢复动作
- 数据库持久化记录

## 7. 依赖项

- 无前置依赖（这是基础 Issue）
- 下游依赖：`DECK-002`, `DECK-003`, `DECK-004`
- 需要现有 `users` 表（用于作者关联，可选）

## 8. 测试策略

| 测试类型 | 覆盖内容 |
|---|---|
| 单元测试 | 合法/非法 manifest 校验、SemVer 校验、重复标识检测 |
| 单元测试 | 能力子集校验（步骤能力超出顶层能力时拒绝） |
| 单元测试 | 来源 allowlist 校验（白名单内通过、外拒绝） |
| 单元测试 | 状态机流转（draft → published → deprecated → revoked） |
| 单元测试 | 已发布版本禁止回到 draft |
| 单元测试 | manifest 禁止包含密钥明文（检测 `api_key`, `password`, `secret` 等敏感键） |
| 集成测试 | 数据库 CRUD、唯一约束、索引查询 |

## 9. 完成标志

- [ ] `DeckPluginManifestV1` schema 定义完整，包含所有设计稿 §5.1 字段
- [ ] `deck_plugin_id` 全局稳定，`deck_plugin_version` 遵循 SemVer
- [ ] 发布版本状态机完整，已发布版本禁止回到 `draft`
- [ ] manifest 校验覆盖：标识唯一性、schema 结构、能力子集、来源 allowlist、完整性
- [ ] manifest 禁止包含密钥明文和完整 Desk prompt
- [ ] 单元测试覆盖合法/非法 manifest、SemVer 校验、重复标识检测
- [ ] 数据库表创建幂等，支持回滚

## 10. 风险提示

| 风险 | 等级 | 缓解 |
|---|---|---|
| manifest 模型不稳定导致下游全部返工 | 高 | 与 DesignArchitect 确认字段冻结后再推进实现；task 文档仅规划不实现 |
| SemVer 校验规则与团队习惯不一致 | 低 | 使用 `semver` 标准库，文档明确合规规则 |
| 来源 allowlist 配置缺失导致所有发布被拒绝 | 中 | 默认 allowlist 包含官方 marketplace；开发环境放宽 |
| `deck_plugin_id` 命名冲突 | 中 | 采用反向域名风格（`voice-decks.*`），校验器检查格式 |

## 11. 命名隔离声明

- 所有业务工作流字段使用 `deck_plugin_*` 前缀
- 所有 Claude Code 运行时依赖字段使用 `claude_code_plugin_*` 或 `runtime_plugin_*` 前缀
- 禁止在跨域 API 中使用无前缀的 `plugin_id`、`plugin_version`

## 12. 未决决策引用

- `DECK-016`: Deck Plugin catalog 与 Runtime Admin 物理服务边界 —— 默认假设：保持逻辑双边界，由 gateway 聚合
- `DECK-017`: 生产 marketplace 签名、digest 与留存能力 —— 默认假设：无不可变 digest 不得 production-ready
