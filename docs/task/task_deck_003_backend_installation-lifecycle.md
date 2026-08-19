# task_deck_003_backend_installation-lifecycle

## 1. 任务标题

Deck Plugin Installation 生命周期管理

## 2. 关联 Issue

- **Issue ID**: `DECK-003`
- **Issue 标题**: Deck Plugin Installation 生命周期管理
- **类型**: backend
- **优先级**: P0
- **标签**: `deck-plugin`, `installation`, `lifecycle`
- **来源设计稿**:
  - `docs/design/deck-plugin-voice-ink-dream-integration.md` §6.1, §6.2
- **Issue 清单**: `docs/issue/ISSUES_deck-plugin-voice-ink-dream-integration.md` §3 DECK-003

## 3. 任务目标

实现 Deck Plugin Installation 的完整生命周期管理。安装记录表达"该实例/工作区被允许消费哪些发布版本"，不是 Claude Code Plugin cache。包括安装记录模型、状态机、升级双版本切换、回滚路径。

## 4. 实现步骤

### Step 1: 定义 Installation 数据模型

在 `backend/models/deck_plugin.py` 中追加：

```python
class DeckPluginInstallation(BaseModel):
    deck_plugin_installation_id: str   # dpi_<uuid>
    scope_type: str                    # "instance" | "workspace"
    scope_id: str
    deck_plugin_id: str
    installed_versions: list[str]      # 已安装版本列表
    default_version: Optional[str]
    status: InstallationStatus
    approved_capabilities: list[str]
    source_policy_id: str
    last_error_code: Optional[str]
    last_error_summary: Optional[str]
    created_at: datetime
    updated_at: datetime

class InstallationStatus(str, Enum):
    INSTALLING = "installing"
    READY = "ready"
    DISABLED = "disabled"
    ERROR = "error"
    UPGRADE_PENDING = "upgrade_pending"
    UNINSTALLED = "uninstalled"
```

### Step 2: 实现状态机

```text
installing ──成功──> ready <────enable──── disabled
    │                 │  └────disable────> │
    └──失败──> error  │
error ──retry───────> installing
ready ──能力扩张升级──> upgrade_pending ──approve──> installing
任一非终态 ──uninstall──> uninstalled
```

在 `backend/services/deck_plugin/installation_service.py`（新建）中实现状态流转：

```python
class InstallationService:
    async def install(self, deck_plugin_id: str, version: str, scope: Scope) -> InstallResult
    async def enable(self, installation_id: str) -> DeckPluginInstallation
    async def disable(self, installation_id: str, reason: str) -> DeckPluginInstallation
    async def upgrade(self, installation_id: str, target_version: str) -> UpgradeResult
    async def rollback(self, installation_id: str, target_version: str) -> DeckPluginInstallation
    async def uninstall(self, installation_id: str, force: bool = False) -> DeckPluginInstallation
```

### Step 3: 升级双版本切换

升级流程：
1. 下载并验证目标 Deck Plugin release，不停止旧版本服务能力
2. 对比 manifest、Deck runtime contract、输出 schema、Claude Code Plugin lock 和能力集合
3. 新增能力或扩大权限时进入 `upgrade_pending`，必须由管理员显式审批
4. 目标版本 runtime lock 全部物化并完成 load smoke 后才可成为 `default_version`
5. 已有 Deck binding 不自动迁移；仅下一次运行生效
6. 目标版本失败时继续保留旧版本 `ready`

### Step 4: 回滚路径

回滚规则：
- 回滚前仍需执行权限、Deck 运行配置、输出 schema 和 runtime materialization 检查
- 旧制品必须通过 digest 校验
- 进行中与历史 run 不随默认版本回滚
- 若不存在兼容旧 release，则状态为 `blocked`，不自动选择"最近可用"

### Step 5: 数据库表设计

在 `backend/database.py` 中追加：

```sql
CREATE TABLE IF NOT EXISTS deck_plugin_installations (
    id TEXT PRIMARY KEY,                    -- dpi_<uuid>
    scope_type TEXT NOT NULL,               -- "instance" | "workspace"
    scope_id TEXT NOT NULL,
    deck_plugin_id TEXT NOT NULL,
    installed_versions_json TEXT NOT NULL,  -- JSON 数组
    default_version TEXT,
    status TEXT NOT NULL DEFAULT 'installing',
    approved_capabilities_json TEXT,        -- JSON 数组
    source_policy_id TEXT,
    last_error_code TEXT,
    last_error_summary TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(scope_type, scope_id, deck_plugin_id)
);

CREATE INDEX IF NOT EXISTS idx_installations_deck_plugin
    ON deck_plugin_installations(deck_plugin_id);
CREATE INDEX IF NOT EXISTS idx_installations_scope
    ON deck_plugin_installations(scope_type, scope_id);
CREATE INDEX IF NOT EXISTS idx_installations_status
    ON deck_plugin_installations(status);
```

### Step 6: 安装响应格式

```jsonc
{
  "operation_id": "op_...",
  "deck_plugin_installation_id": "dpi_...",
  "deck_plugin_id": "voice-decks.story-dramatize",
  "target_version": "3.1.0",
  "status": "installing",
  "capability_diff": { "added": [], "removed": [] },
  "runtime_readiness": "materializing"
}
```

## 5. 涉及文件路径

| 路径 | 动作 | 说明 |
|---|---|---|
| `backend/models/deck_plugin.py` | 修改 | 追加 Installation 模型和状态枚举 |
| `backend/services/deck_plugin/installation_service.py` | 新建 | Installation 生命周期服务 |
| `backend/database.py` | 修改 | 追加 `deck_plugin_installations` 表 |
| `backend/tests/test_deck_plugin_installation.py` | 新建 | 生命周期单元测试 |

## 6. 输入 / 输出说明

**输入**：
- `deck_plugin_id` + `deck_plugin_version`（来自 DECK-001/DECK-002）
- 安装 scope（instance/workspace + scope_id）
- 管理员审批决策（能力扩张时）

**输出**：
- `DeckPluginInstallation` 记录
- 安装响应（含 `operation_id`, `capability_diff`, `runtime_readiness`）
- 结构化错误码

## 7. 依赖项

- **前置依赖**: `DECK-001`（manifest 模型）, `DECK-002`（runtime lock）
- **下游依赖**: `DECK-004`, `DECK-005`, `DECK-015`
- 需要与 runtime materialization 服务交互（默认假设：接口已存在）

## 8. 测试策略

| 测试类型 | 覆盖内容 |
|---|---|
| 单元测试 | 状态机流转（所有合法路径） |
| 单元测试 | 升级双版本切换（旧版本保持 ready，目标版本物化后切换） |
| 单元测试 | 能力扩张进入 upgrade_pending |
| 单元测试 | 回滚路径（digest 校验、历史 run 不变） |
| 单元测试 | 卸载软删除 vs 强制 purge |
| 单元测试 | 并发安装（同一 scope + plugin） |
| 集成测试 | 安装 → 升级 → 回滚 → 卸载端到端 |

## 9. 完成标志

- [ ] Installation 模型完整，包含设计稿 §6.1 所有字段
- [ ] 状态机完整，覆盖所有合法流转和错误恢复
- [ ] 升级采用双版本切换：目标版本 runtime lock 全部物化并完成 load smoke 后才成为 `default_version`
- [ ] 回滚只影响默认版本或 Deck 下一次运行 binding，不改历史 run
- [ ] 卸载默认软删除并保留历史引用；强制 purge 前证明不存在历史审计或留存义务
- [ ] 安装响应包含 `operation_id`、`capability_diff`、`runtime_readiness`
- [ ] 单元测试覆盖状态流转、升级回滚、并发安装、错误恢复

## 10. 风险提示

| 风险 | 等级 | 缓解 |
|---|---|---|
| 与 Paperclip PluginStatus 类型混淆 | 中 | 显式声明 Deck 域独立状态枚举；代码审查检查 |
| 升级失败导致旧版本也被破坏 | 高 | 双版本切换：目标版本失败不影响旧版本 ready 状态 |
| 并发升级导致状态不一致 | 中 | 数据库行锁 + 乐观并发控制 |
| 卸载后历史审计丢失 | 中 | 软删除默认；强制 purge 需证明无留存义务 |

## 11. 允许修改范围与禁止修改范围

### 允许修改范围

- `backend/models/deck_plugin.py`（仅追加 Installation 模型和 Deck 域状态枚举）
- `backend/services/deck_plugin/installation_service.py`（仅新增 Installation 生命周期服务）
- `backend/database.py`（仅增量追加 `deck_plugin_installations` 表及其幂等初始化）
- `backend/tests/test_deck_plugin_installation.py`（仅新增本 task 的单元测试）

以上闭集与 §5“涉及文件路径”一致；未列出的文件默认不授权。

### 禁止修改范围

- `docs/design/`、`docs/issue/`、`docs/task/`、`docs/stage/`、`docs/exec/`
- `frontend/`、Paperclip `PluginStatus` / Plugin worker 实现和 ClaudeAgent runtime 实现
- 除上述 4 个路径以外的任何实现、测试、依赖锁或部署配置
- `backend/models/deck_plugin.py` 与 `backend/database.py` 中和 Installation 生命周期无关的既有模型、表或初始化逻辑
- 借本 task 改写发布 lock、兼容性判定或 Workflow Run 状态机

## 12. 命名隔离声明

- Installation 记录使用 `deck_plugin_installation_id` 前缀
- 状态枚举为 Deck 业务域独立定义，禁止直接复用 Paperclip `PluginStatus`

## 13. 未决决策引用

- `DECK-016`: 物理服务边界未定 —— 默认假设：Installation 由 Voice Decks 逻辑域提供
- `DECK-019`: 安全撤销是否强制终止活动 run —— 默认假设：普通禁用不终止；安全撤销允许强制终止并审计
