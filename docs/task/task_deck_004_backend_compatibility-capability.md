# task_deck_004_backend_compatibility-capability

## 1. 任务标题

兼容性判定与能力交集权限

## 2. 关联 Issue

- **Issue ID**: `DECK-004`
- **Issue 标题**: 兼容性判定与能力交集权限
- **类型**: backend
- **优先级**: P0
- **标签**: `deck-plugin`, `compatibility`, `capability`, `security`
- **来源设计稿**:
  - `docs/design/deck-plugin-voice-ink-dream-integration.md` §6.3, §6.4
- **Issue 清单**: `docs/issue/ISSUES_deck-plugin-voice-ink-dream-integration.md` §3 DECK-004

## 3. 任务目标

实现 Deck Plugin 的兼容性判定链和能力交集计算。兼容性判定按固定顺序执行，有效能力按多个维度取交集。这是 selection validation 和 execution preflight 的共同基础。

## 4. 实现步骤

### Step 1: 定义兼容性判定链

在 `backend/services/deck_plugin/compatibility_service.py`（新建）中实现：

```python
class CompatibilityCheck(str, Enum):
    RELEASE_AVAILABLE = "release_available"
    DECK_HOST_COMPATIBLE = "deck_host_compatible"
    CLAUDE_AGENT_COMPATIBLE = "claude_agent_compatible"
    STORY_SCHEMA_COMPATIBLE = "story_schema_compatible"
    DESK_CONFIG_COMPATIBLE = "desk_config_compatible"
    RUNTIME_PLUGIN_RESOLVED = "runtime_plugin_resolved"
    WORKFLOW_PERMISSION = "workflow_permission"
    RUNTIME_PLUGIN_READY = "runtime_plugin_ready"

class CompatibilityResult(BaseModel):
    passed: bool
    failed_check: Optional[CompatibilityCheck]
    error_code: Optional[str]
    recovery_action: Optional[str]
```

判定顺序（固定，失败即停止）：

| 顺序 | 检查 | 失败错误码 |
|---|---|---|
| 1 | release 为 `published`/策略允许的 `deprecated`，installation 为 `ready` | `DECK_PLUGIN_UNAVAILABLE` |
| 2 | Deck host API 与 manifest schema 兼容 | `DECK_HOST_INCOMPATIBLE` |
| 3 | ClaudeAgent contract 与 Claude Code 版本兼容 | `CLAUDE_AGENT_INCOMPATIBLE` |
| 4 | story-workspace input/output schema 兼容 | `STORY_SCHEMA_INCOMPATIBLE` |
| 5 | Desk profile/snapshot contract 兼容 | `DESK_CONFIG_INCOMPATIBLE` |
| 6 | runtime lock 中每个来源、版本、摘要可解析 | `RUNTIME_PLUGIN_UNRESOLVED` |
| 7 | 管理员 grant、Desk policy、用户权限满足能力交集 | `WORKFLOW_PERMISSION_DENIED` |
| 8 | required runtime plugin 已物化、可加载 | `RUNTIME_PLUGIN_NOT_READY` |

### Step 2: 实现能力交集计算

```python
def compute_effective_capabilities(
    manifest_requested: set[str],
    installation_approved: set[str],
    desk_snapshot_policy: set[str],
    user_and_workspace_grants: set[str],
    claude_agent_runtime_supported: set[str]
) -> set[str]:
    """
    有效能力 = manifest_requested ∩ installation_approved ∩ desk_snapshot_policy
             ∩ user_and_workspace_grants ∩ claude_agent_runtime_supported
    未知能力默认拒绝。
    """
```

### Step 3: 实现兼容性判定服务

```python
class CompatibilityService:
    async def check_compatibility(
        self,
        deck_plugin_id: str,
        deck_plugin_version: str,
        scope: Scope,
        runtime_context: RuntimeContext
    ) -> CompatibilityResult:
        """按固定顺序执行 8 步兼容性判定。"""

    async def check_capability_expansion(
        self,
        installation_id: str,
        target_manifest: DeckPluginManifestV1
    ) -> CapabilityDiff:
        """
        对比目标版本与当前安装版本的能力集合。
        新增能力或扩大权限时返回需要审批的 diff。
        """
```

### Step 4: 结构化错误响应

每个失败必须返回：
- `error_code`: 规范错误码
- `failed_check`: 失败的判定步骤
- `recovery_action`: 可恢复动作（如"升级 host"、"申请授权"、"选择兼容版本"）
- 禁止泄露敏感详情（manifest 内容、Desk prompt、secret 等）

### Step 5: 能力扩张审批

```python
class CapabilityDiff(BaseModel):
    added: list[str]
    removed: list[str]
    requires_approval: bool

async def approve_capability_expansion(
    installation_id: str,
    approved_capabilities: list[str],
    actor: str
) -> DeckPluginInstallation:
    """管理员显式审批能力扩张后，installation 进入 ready 状态。"""
```

## 5. 涉及文件路径

| 路径 | 动作 | 说明 |
|---|---|---|
| `backend/models/deck_plugin.py` | 修改 | 追加 CompatibilityResult、CapabilityDiff 模型 |
| `backend/services/deck_plugin/compatibility_service.py` | 新建 | 兼容性判定服务 |
| `backend/services/deck_plugin/capability_evaluator.py` | 新建 | 能力交集计算 |
| `backend/tests/test_deck_plugin_compatibility.py` | 新建 | 兼容性判定单元测试 |

## 6. 输入 / 输出说明

**输入**：
- `deck_plugin_id` + `deck_plugin_version`
- `DeckPluginInstallation` 记录（来自 DECK-003）
- `DeckPluginManifestV1`（来自 DECK-001）
- `DeckRuntimePluginLock`（来自 DECK-002）
- 运行时上下文（host API 版本、Claude Code 版本、runtime 支持能力）
- 用户/workspace 权限

**输出**：
- `CompatibilityResult`（通过/失败 + 错误码 + 恢复动作）
- `CapabilityDiff`（能力差异 + 是否需要审批）

## 7. 依赖项

- **前置依赖**: `DECK-001`（manifest 模型）, `DECK-003`（installation 生命周期）
- **下游依赖**: `DECK-005`, `DECK-006`, `DECK-014`
- 需要与身份/权限服务集成

## 8. 测试策略

| 测试类型 | 覆盖内容 |
|---|---|
| 单元测试 | 8 步判定链各维度边界（每步单独失败） |
| 单元测试 | 能力交集计算（各种组合） |
| 单元测试 | 未知能力默认拒绝 |
| 单元测试 | 能力扩张进入 upgrade_pending |
| 单元测试 | 结构化 reason code 与恢复动作 |
| 单元测试 | 禁止客户端版本字符串比较（服务端强制判定） |
| 集成测试 | 端到端兼容性判定（通过/各种失败场景） |

## 9. 完成标志

- [ ] 兼容性判定顺序固定，失败即停止并返回结构化 reason code
- [ ] 8 步判定覆盖设计稿 §6.3 所有检查项
- [ ] 有效能力交集计算正确，未知能力默认拒绝
- [ ] 能力扩张升级进入 `upgrade_pending`，必须由管理员显式审批
- [ ] 禁止用客户端版本字符串比较替代服务端兼容性判定
- [ ] 目录响应返回结构化 reason code 与可恢复动作
- [ ] 单元测试覆盖各维度边界与结构化 reason code

## 10. 风险提示

| 风险 | 等级 | 缓解 |
|---|---|---|
| 兼容性判定与前端判定不一致 | 高 | 所有判定必须在服务端完成；前端只做展示 |
| 版本比较规则与 SemVer 标准差异 | 中 | 使用标准 semver 库；文档明确边界规则 |
| 能力交集计算性能（大量能力时） | 低 | set 交集操作 O(n)；能力数量通常 < 100 |
| 权限服务不可用导致所有判定失败 | 中 | 优雅降级：返回 `WORKFLOW_PERMISSION_DENIED`，不崩溃 |

## 11. 命名隔离声明

- 能力名称使用平台可审计的命名空间（如 `story.context.read`）
- 未知能力默认拒绝，不得自动授权

## 12. 未决决策引用

- `DECK-016`: 物理服务边界未定 —— 兼容性判定由哪个服务执行需确认
- `DECK-019`: 安全撤销策略 —— 影响权限判定中的撤销等级处理
