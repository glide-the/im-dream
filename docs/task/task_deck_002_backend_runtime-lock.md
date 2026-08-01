# task_deck_002_backend_runtime-lock

## 1. 任务标题

Deck Runtime Plugin Lock 生成与不可变合同

## 2. 关联 Issue

- **Issue ID**: `DECK-002`
- **Issue 标题**: Deck Runtime Plugin Lock 生成与不可变合同
- **类型**: backend
- **优先级**: P0
- **标签**: `deck-plugin`, `runtime-lock`, `release`
- **来源设计稿**:
  - `docs/design/deck-plugin-voice-ink-dream-integration.md` §5.3, §3.3
- **Issue 清单**: `docs/issue/ISSUES_deck-plugin-voice-ink-dream-integration.md` §3 DECK-002

## 3. 任务目标

实现 Deck Plugin 发布时生成 `DeckRuntimePluginLock` 的能力。将 manifest 中声明的 Claude Code Plugin 版本约束解析为精确版本和制品摘要，生成不可变的 runtime lock。确保同一 `deck_plugin_id + deck_plugin_version` 的工作流定义、运行时锁、能力请求、输入/输出 schema 和 Desk 合同发布后不可变。

## 4. 实现步骤

### Step 1: 定义 `DeckRuntimePluginLock` 数据模型

在 `backend/models/deck_plugin.py` 中追加：

```python
class RuntimePluginLockEntry(BaseModel):
    claude_code_plugin_id: str      # 如 "ink-dream-tools@voice-decks"
    resolved_version: str           # 精确版本，如 "1.4.2"
    source_ref: str                 # 如 "marketplace://voice-decks@2026-08-01"
    artifact_digest: str            # sha256:...
    required: bool
    capability_bindings: list[str]

class DeckRuntimePluginLock(BaseModel):
    runtime_plugin_lock_id: str     # rpl_<uuid>
    deck_plugin_id: str
    deck_plugin_version: str
    deck_plugin_manifest_hash: str  # sha256:...
    claude_code_plugins: list[RuntimePluginLockEntry]
    created_at: datetime
```

### Step 2: 实现版本约束解析器

在 `backend/services/deck_plugin/lock_generator.py`（新建）中实现：

```python
class LockGenerator:
    def generate_lock(
        self,
        manifest: DeckPluginManifestV1,
        marketplace_resolver: MarketplaceResolver
    ) -> DeckRuntimePluginLock:
        """
        将 manifest.runtime.claude_code_plugins 中的 version_constraint
        解析为精确 resolved_version 和 artifact_digest。
        """
```

解析规则：
- `version_constraint` 支持 SemVer 范围（如 `1.4.x`, `>=1.0.0 <2.0.0`）
- 解析失败时进入 `validating` 状态的失败分支
- 无不可变 digest 的来源不得标为 production-ready

### Step 3: 实现不可变性校验

```python
def verify_lock_immutability(
    deck_plugin_id: str,
    deck_plugin_version: str,
    new_lock: DeckRuntimePluginLock
) -> bool:
    """
    检查同一 deck_plugin_id + deck_plugin_version 是否已有 lock。
    若存在，比较 manifest_hash 和 lock 内容，任何差异都拒绝。
    """
```

### Step 4: 数据库表设计

在 `backend/database.py` 中追加：

```sql
CREATE TABLE IF NOT EXISTS deck_runtime_plugin_locks (
    id TEXT PRIMARY KEY,                    -- runtime_plugin_lock_id: rpl_<uuid>
    deck_plugin_id TEXT NOT NULL,
    deck_plugin_version TEXT NOT NULL,
    deck_plugin_manifest_hash TEXT NOT NULL,
    lock_json TEXT NOT NULL,                -- 完整 lock JSON
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (deck_plugin_id, deck_plugin_version)
        REFERENCES deck_plugin_releases(deck_plugin_id, deck_plugin_version)
        ON DELETE RESTRICT,
    UNIQUE(deck_plugin_id, deck_plugin_version)
);

CREATE INDEX IF NOT EXISTS idx_runtime_locks_deck_plugin
    ON deck_runtime_plugin_locks(deck_plugin_id, deck_plugin_version);
```

### Step 5: 集成到发布流程

在 `release_service.py` 中，发布流程更新为：

```
draft → validating:
  1. manifest 校验（DECK-001）
  2. 调用 LockGenerator.generate_lock()
  3. 若解析失败 → validating 失败，返回 RUNTIME_PLUGIN_UNRESOLVED
  4. 若 digest 缺失 → 标记为 non-production-ready，允许继续但警告
  5. 原子保存 release 记录 + lock 记录
  6. 状态转为 published
```

## 5. 涉及文件路径

| 路径 | 动作 | 说明 |
|---|---|---|
| `backend/models/deck_plugin.py` | 修改 | 追加 RuntimePluginLockEntry、DeckRuntimePluginLock 模型 |
| `backend/services/deck_plugin/lock_generator.py` | 新建 | Lock 生成器 |
| `backend/services/deck_plugin/release_service.py` | 修改 | 集成 lock 生成到发布流程 |
| `backend/database.py` | 修改 | 追加 `deck_runtime_plugin_locks` 表 |
| `backend/tests/test_deck_plugin_lock.py` | 新建 | lock 生成与不可变性单元测试 |

## 6. 输入 / 输出说明

**输入**：
- `DeckPluginManifestV1`（来自 DECK-001）
- Marketplace 解析器（需与制品存储交互）
- 来源 allowlist 配置

**输出**：
- `DeckRuntimePluginLock` 记录
- 解析失败时的结构化错误码（`RUNTIME_PLUGIN_UNRESOLVED`, `RUNTIME_MARKETPLACE_UNAVAILABLE`）

## 7. 依赖项

- **前置依赖**: `DECK-001`（manifest 模型）
- **下游依赖**: `DECK-003`, `DECK-006`, `DECK-008`
- 需要 marketplace/制品存储交互能力（默认假设：接口已存在，具体实现由运行平台提供）

## 8. 测试策略

| 测试类型 | 覆盖内容 |
|---|---|
| 单元测试 | 版本约束解析（`1.4.x` → `1.4.2`，`>=1.0.0 <2.0.0` → 精确版本） |
| 单元测试 | 解析失败处理（marketplace 不可用、版本不匹配） |
| 单元测试 | digest 缺失拒绝 production-ready |
| 单元测试 | 不可变性校验（同一 id+version 不允许变更 lock） |
| 单元测试 | 历史引用保留（revoked release 的 lock 仍可读取） |
| 集成测试 | 发布流程端到端（draft → validating → published + lock） |

## 9. 完成标志

- [ ] 发布时解析 `claude_code_plugins` 版本约束为精确 `resolved_version` 和 `artifact_digest`
- [ ] 生成 `runtime_plugin_lock_id` 并与发布版本原子关联
- [ ] 相同 `deck_plugin_id + deck_plugin_version` 不允许变更 manifest hash 或 runtime lock
- [ ] 无不可变 digest 的来源不得标为 production-ready
- [ ] 历史引用存在时必须保留对应制品或可验证的恢复源
- [ ] 单元测试覆盖发布锁生成、不可变性校验、digest 缺失拒绝

## 10. 风险提示

| 风险 | 等级 | 缓解 |
|---|---|---|
| marketplace 解析器接口不稳定 | 高 | 定义抽象接口 `MarketplaceResolver`，具体实现由运行平台注入；默认假设下可推进 |
| 制品 digest 算法未标准化 | 中 | 默认使用 sha256；`DECK-017` 决策单确认后更新 |
| 同一版本多次发布（并发） | 中 | 数据库唯一约束 `UNIQUE(deck_plugin_id, deck_plugin_version)` + 事务保护 |
| 历史制品清理导致不可复现 | 中 | 引用计数机制；`DECK-017` 决策单确认留存策略 |

## 11. 命名隔离声明

- `DeckRuntimePluginLock` 中的字段使用 `runtime_plugin_*` 前缀
- 内部条目使用 `claude_code_plugin_id`、`resolved_version`、`artifact_digest`
- 禁止与 `deck_plugin_*` 字段混用

## 12. 未决决策引用

- `DECK-017`: 生产 marketplace 签名、digest 与留存能力 —— 默认假设：无不可变 digest 不得 production-ready；阻塞生产部署前必须解决
