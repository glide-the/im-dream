# task_deck_008_backend_reconcile-load-receipt

## 1. 任务标题

ClaudeAgent 声明式 Reconcile 与 Load Receipt

## 2. 关联 Issue

- **Issue ID**: `DECK-008`
- **Issue 标题**: ClaudeAgent 声明式 Reconcile 与 Load Receipt
- **类型**: backend
- **优先级**: P0
- **标签**: `claude-agent`, `reconcile`, `materialization`
- **来源设计稿**:
  - `docs/design/deck-plugin-voice-ink-dream-integration.md` §7.1, §7.2, §7.3, §7.4
  - `docs/design/plugin-remote-interaction.md` §4.2, §4.3, §4.4
- **Issue 清单**: `docs/issue/ISSUES_deck-plugin-voice-ink-dream-integration.md` §3 DECK-008

## 3. 任务目标

实现 ClaudeAgent 的声明式 reconcile 和 load receipt 生成。生产主路径为 settings 意图 + headless reconcile，CLI 为受控备选。实现 runtime plugin 的三维状态管理和物化幂等合同。

## 4. 实现步骤

### Step 1: 定义三维状态模型

在 `backend/models/runtime_plugin.py`（新建）中定义：

```python
class RuntimePluginMaterialization(BaseModel):
    runtime_materialization_id: str     # rm_<uuid>
    runtime_environment_id: str
    claude_code_plugin_id: str
    resolved_version: str
    artifact_digest: str

    # 三维状态（独立记录，不可合并）
    declaration_status: DeclarationStatus      # undeclared | declared | disabled
    materialization_status: MaterializationStatus  # missing | materializing | materialized | failed
    activation_status: ActivationStatus        # inactive | loadable | loaded | load_failed

    # 物化元数据
    materialization_key: str            # hash(runtime_env, plugin_id, version, digest)
    attempt_id: str                     # 每次 attempt 唯一
    attempt_count: int                  # 重试次数
    last_error: Optional[str]
    created_at: datetime
    updated_at: datetime

class DeclarationStatus(str, Enum):
    UNDECLARED = "undeclared"
    DECLARED = "declared"
    DISABLED = "disabled"

class MaterializationStatus(str, Enum):
    MISSING = "missing"
    MATERIALIZING = "materializing"
    MATERIALIZED = "materialized"
    FAILED = "failed"

class ActivationStatus(str, Enum):
    INACTIVE = "inactive"
    LOADABLE = "loadable"
    LOADED = "loaded"
    LOAD_FAILED = "load_failed"
```

### Step 2: 实现声明式 Reconcile（主路径 A）

在 `backend/services/runtime_plugin/reconcile_service.py`（新建）中实现：

```python
class ReconcileService:
    async def declare_and_reconcile(
        self,
        runtime_lock: DeckRuntimePluginLock,
        runtime_environment_id: str
    ) -> ReconcileResult:
        """
        路径 A（主路径）：声明意图 + headless reconcile
        1. 将 runtime lock 中的插件写入 settings（enabledPlugins / extraKnownMarketplaces）
        2. 启动 headless 会话，env: CLAUDE_CODE_SYNC_PLUGIN_INSTALL=true
        3. 等待 reconcile 完成（首条 query 前同步完成）
        4. 校验 init.plugins 包含目标插件
        5. 返回 InstallReceipt
        """
```

Settings 写入格式：
```json
{
  "enabledPlugins": {
    "ink-dream-tools@voice-decks": true
  },
  "extraKnownMarketplaces": {
    "voice-decks": {
      "source": "github",
      "repo": "voice-decks/marketplace"
    }
  }
}
```

### Step 3: 实现 CLI 备选路径（路径 B）

```python
async def cli_install(
    self,
    claude_code_plugin_id: str,
    resolved_version: str,
    scope: str = "project"
) -> CliResult:
    """
    路径 B（备选）：受控子进程执行
    1. 校验来源在 allowlist 中
    2. 执行 `claude plugin install <plugin_id> --scope <scope> --json`
    3. 捕获输出、校验 JSON、超时控制
    4. 记录审计日志
    5. 禁止把用户文本拼成 shell
    """
```

### Step 4: 实现物化幂等合同

```python
async def materialize(
    self,
    runtime_environment_id: str,
    claude_code_plugin_id: str,
    resolved_version: str,
    artifact_digest: str
) -> MaterializationResult:
    """
    物化幂等合同：
    1. materialization_key = hash(runtime_env, plugin_id, version, digest)
    2. 同一 key 同时只允许一个 reconcile owner
    3. 重复请求返回同一个 materialization/operation
    4. 下载到临时位置后校验摘要，再原子发布到版本化 cache
    5. 旧制品在被历史 runtime lock 引用时不得清理
    """
```

### Step 5: 实现 Load Receipt 生成

```python
class RuntimeLoadReceipt(BaseModel):
    runtime_load_receipt_id: str    # rlr_<uuid>
    workflow_run_id: str
    entries: list[LoadReceiptEntry]
    created_at: datetime

class LoadReceiptEntry(BaseModel):
    claude_code_plugin_id: str
    resolved_version: str
    artifact_digest: str
    loaded_capabilities: list[str]
    load_status: str                # loaded | load_failed | skipped
    loaded_at: datetime
```

### Step 6: 数据库表设计

在 `backend/database.py` 中追加：

```sql
CREATE TABLE IF NOT EXISTS runtime_plugin_materializations (
    id TEXT PRIMARY KEY,            -- rm_<uuid>
    runtime_environment_id TEXT NOT NULL,
    claude_code_plugin_id TEXT NOT NULL,
    resolved_version TEXT NOT NULL,
    artifact_digest TEXT NOT NULL,
    declaration_status TEXT NOT NULL DEFAULT 'undeclared',
    materialization_status TEXT NOT NULL DEFAULT 'missing',
    activation_status TEXT NOT NULL DEFAULT 'inactive',
    materialization_key TEXT NOT NULL UNIQUE,
    attempt_id TEXT NOT NULL,
    attempt_count INTEGER DEFAULT 0,
    last_error TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(runtime_environment_id, claude_code_plugin_id, resolved_version, artifact_digest)
);

CREATE TABLE IF NOT EXISTS runtime_load_receipts (
    id TEXT PRIMARY KEY,            -- rlr_<uuid>
    workflow_run_id TEXT NOT NULL,
    receipt_json TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(id)
);
```

## 5. 涉及文件路径

| 路径 | 动作 | 说明 |
|---|---|---|
| `backend/models/runtime_plugin.py` | 新建 | Runtime Plugin 三维状态模型 |
| `backend/services/runtime_plugin/reconcile_service.py` | 新建 | Reconcile 服务 |
| `backend/services/runtime_plugin/materialization_manager.py` | 新建 | 物化管理器 |
| `backend/database.py` | 修改 | 追加 `runtime_plugin_materializations`、`runtime_load_receipts` 表 |
| `backend/tests/test_runtime_plugin_reconcile.py` | 新建 | Reconcile 单元测试 |

## 6. 输入 / 输出说明

**输入**：
- `DeckRuntimePluginLock`（来自 DECK-002）
- `runtime_environment_id`
- Settings 写入目标（user/project/local）

**输出**：
- `MaterializationResult`（物化结果）
- `RuntimeLoadReceipt`（加载回执）
- 三维状态记录

## 7. 依赖项

- **前置依赖**: `DECK-002`（runtime lock）, `DECK-006`（preflight）
- **下游依赖**: `DECK-009`
- 需要与 Claude Code runtime 环境集成
- 需要 settings 文件写入权限

## 8. 测试策略

| 测试类型 | 覆盖内容 |
|---|---|
| 单元测试 | settings 意图写入格式正确 |
| 单元测试 | headless reconcile 同步完成 |
| 单元测试 | CLI 备选路径（来源校验、超时、输出捕获） |
| 单元测试 | 三维状态独立记录 |
| 单元测试 | 物化幂等（同一 key 返回同一结果） |
| 单元测试 | 原子发布（临时位置 → 版本化 cache） |
| 单元测试 | load receipt 逐项记录 |
| 单元测试 | required 插件全部 loaded 后才 ready |
| 集成测试 | reconcile 成功/失败端到端 |

## 9. 完成标志

- [ ] settings 意图写入 `enabledPlugins`/`extraKnownMarketplaces`
- [ ] headless reconcile 在第一条 query 前同步完成
- [ ] CLI 备选路径受控执行，校验来源、超时、输出和审计
- [ ] 三维状态独立记录，UI 显示"已声明但未物化"而非笼统"已安装"
- [ ] 物化幂等：`materialization_key` 唯一、原子发布、旧制品留存
- [ ] 加载回执 `runtime_load_receipt_id` 逐项记录插件加载状态
- [ ] required 插件全部 `loaded` 后才能进入 `running`
- [ ] 单元测试覆盖 reconcile 成功/失败、幂等物化、load receipt 生成

## 10. 风险提示

| 风险 | 等级 | 缓解 |
|---|---|---|
| settings 写入失败导致 reconcile 无限重试 | 高 | 最大重试次数 + 指数退避 + 错误记录 |
| CLI 子进程注入攻击 | 高 | 禁止拼接用户输入；使用列表传参；校验来源 |
| marketplace 下载超时 | 中 | 可配置超时；失败进入 `materialization_status=failed` |
| 多节点场景 readiness 误报 | 高 | 默认按具体 runtime environment 判定；`DECK-018` 决策单确认后更新 |
| `/plugin` 文本被误用 | 高 | 代码审查 + 测试断言：任何路径不得发送 `/plugin install` 文本 |

## 11. 命名隔离声明

- 物化记录使用 `runtime_materialization_id` 前缀
- 加载回执使用 `runtime_load_receipt_id` 前缀
- Claude Code Plugin 字段使用 `claude_code_plugin_*` 前缀

## 12. 未决决策引用

- `DECK-017`: 生产 marketplace 签名、digest 与留存能力 —— 默认假设：无 digest 不得 production-ready
- `DECK-018`: 多节点/临时 runtime 分发策略 —— 默认假设：readiness 按具体 persistent runtime environment 判定
