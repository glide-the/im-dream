# task_deck_015_backend_revocation-rollback

## 1. 任务标题

安全撤销、回滚与降级路径

## 2. 关联 Issue

- **Issue ID**: `DECK-015`
- **Issue 标题**: 安全撤销、回滚与降级路径
- **类型**: backend
- **优先级**: P1
- **标签**: `security`, `rollback`, `degradation`
- **来源设计稿**:
  - `docs/design/deck-plugin-voice-ink-dream-integration.md` §6.2, §12.2, §12.3
- **Issue 清单**: `docs/issue/ISSUES_deck-plugin-voice-ink-dream-integration.md` §3 DECK-015

## 3. 任务目标

实现安全撤销、回滚和降级路径。包括禁用/撤销/升级中的行为矩阵、降级规则（仅在 manifest 明确声明 `degraded_modes` 时允许）。安全撤销可强制取消活动 run，必须记录撤销人、策略、error_code 和终止事件。

## 4. 实现步骤

### Step 1: 定义行为矩阵

| 变化 | 新 preflight | 已 queued 未启动 | 已 running | 历史 |
|---|---|---|---|---|
| 普通禁用 | 阻止 | 取消并说明或在策略允许时完成启动前检查 | 默认继续至终态 | 不变 |
| 安全撤销 | 阻止 | 取消 | 可以强制取消，记录 `SECURITY_REVOCATION` | 来源保留，制品使用受限 |
| 升级中 | 旧 ready 可用，新版本阻止 | 按已锁旧版本执行 | 按已锁版本继续 | 不变 |
| 物化失败 | 阻止依赖该制品的新 run | 不进入 session | 不影响已经成功加载的会话，除非安全策略要求 | 不变 |
| Desk 当前配置修改 | 新 preflight 取新 snapshot | 已锁 snapshot 不变 | 不变 | 不变 |

### Step 2: 实现撤销服务

在 `backend/services/deck_plugin/revocation_service.py`（新建）中实现：

```python
class RevocationLevel(str, Enum):
    DISABLE = "disable"         # 普通禁用
    REVOKE = "revoke"           # 安全撤销
    EMERGENCY = "emergency"     # 紧急撤销（最高等级）

class RevocationService:
    async def revoke(
        self,
        deck_plugin_id: str,
        version: Optional[str],     # None = 全部版本
        level: RevocationLevel,
        reason: str,
        actor: str
    ) -> RevocationResult:
        """
        执行撤销：
        1. 根据 level 决定影响范围
        2. 更新 installation/release 状态
        3. 按行为矩阵处理已 queued/running 的 run
        4. 记录审计事件
        """

    async def _cancel_running_runs(
        self,
        deck_plugin_id: str,
        version: Optional[str],
        level: RevocationLevel,
        actor: str
    ) -> None:
        """
        安全撤销/紧急撤销时强制取消活动 run：
        - 查询所有 running/queued 且使用该 plugin/version 的 run
        - 发送取消信号
        - 记录 SECURITY_REVOCATION 事件
        - 不得静默终止（必须记录 actor、reason、timestamp）
        """
```

### Step 3: 实现降级规则

```python
class DegradationService:
    async def evaluate_degradation(
        self,
        manifest: DeckPluginManifestV1,
        missing_plugins: list[str],
        missing_capabilities: list[str]
    ) -> DegradationResult:
        """
        降级评估：
        1. 检查 manifest 是否声明 degraded_modes
        2. 确认缺失的是 optional 插件（非 required）
        3. 确认缺失能力不影响输出 schema
        4. 返回 degraded_mode_id 和替代步骤
        5. required 插件缺失、能力授权不足、安全撤销均禁止自动降级
        """
```

降级规则：
- optional Claude Code Plugin 缺失时可省略，但必须满足 manifest 定义的替代步骤
- 降级后的输出必须仍符合相同 story-workspace output schema
- preflight 响应必须显示 degraded mode、缺失能力和用户确认要求
- Workflow Run 必须保存实际 runtime load receipt 和 `degraded_mode_id`
- 默认示例 `degraded_modes=[]`，即不允许降级

### Step 4: 实现回滚路径

```python
async def rollback_installation(
    self,
    installation_id: str,
    target_version: str,
    actor: str
) -> RollbackResult:
    """
    回滚：
    1. 校验目标版本仍为 published/deprecated 且 installation 记录存在
    2. 校验 digest 完整
    3. 执行兼容性检查（目标版本与当前 host/runtime）
    4. 更新 default_version
    5. 已有 Deck binding 不自动迁移（仅影响下一次运行）
    6. 记录审计事件
    """
```

### Step 5: 审计要求

安全撤销必须记录：
- 撤销人（actor）
- 撤销策略/等级（level）
- 错误码（`SECURITY_REVOCATION`）
- 终止事件（`workflow.run.security_cancelled`）
- 时间戳
- 受影响 run 列表

## 5. 涉及文件路径

| 路径 | 动作 | 说明 |
|---|---|---|
| `backend/services/deck_plugin/revocation_service.py` | 新建 | 撤销服务 |
| `backend/services/deck_plugin/degradation_service.py` | 新建 | 降级服务 |
| `backend/services/deck_plugin/rollback_manager.py` | 新建 | 回滚管理器 |
| `backend/tests/test_revocation_rollback.py` | 新建 | 撤销/回滚/降级单元测试 |

## 6. 输入 / 输出说明

**输入**：
- `deck_plugin_id` + `version`（可选）
- `RevocationLevel`
- 撤销原因
- 执行者身份

**输出**：
- `RevocationResult`（影响范围、已处理 run 列表）
- 审计事件

## 7. 依赖项

- **前置依赖**: `DECK-003`（Installation 生命周期）, `DECK-007`（Workflow Run）
- **下游依赖**: 无
- 需要与事件系统（DECK-013）集成

## 8. 测试策略

| 测试类型 | 覆盖内容 |
|---|---|
| 单元测试 | 禁用/撤销/升级行为矩阵（所有组合） |
| 单元测试 | 普通禁用阻止新 binding 和新 run，不删除历史 |
| 单元测试 | 安全撤销强制取消活动 run，记录 SECURITY_REVOCATION 审计 |
| 单元测试 | 降级仅在 manifest 声明 degraded_modes 时允许 |
| 单元测试 | 降级后输出仍符合相同 output schema |
| 单元测试 | required 插件缺失禁止自动降级 |
| 单元测试 | 升级失败保留旧版本 ready |
| 单元测试 | 回滚只影响 default/binding，不改历史 run |
| 集成测试 | 端到端撤销/回滚/降级场景 |

## 9. 完成标志

- [ ] 禁用/撤销/升级行为矩阵完整，覆盖设计稿 §12.2
- [ ] 普通禁用阻止新 binding 和新 run，不删除历史
- [ ] 安全撤销可强制取消活动 run，记录 `SECURITY_REVOCATION` 审计
- [ ] 降级仅在 manifest 声明 `degraded_modes` 时允许
- [ ] 降级后输出仍符合相同 story-workspace output schema
- [ ] required 插件缺失、能力授权不足、安全撤销均禁止自动降级
- [ ] 升级失败保留旧版本 `ready`
- [ ] 单元测试覆盖撤销场景、降级路径、升级失败恢复

## 10. 风险提示

| 风险 | 等级 | 缓解 |
|---|---|---|
| 强制取消活动 run 导致数据丢失 | 高 | 撤销前告警；用户确认；记录完整审计 |
| 降级被滥用绕过安全策略 | 高 | required 插件缺失禁止降级；安全撤销禁止降级 |
| 回滚到已不兼容的旧版本 | 中 | 回滚前执行兼容性检查 |
| 紧急撤销误触发 | 高 | 多重确认；仅特定角色可执行 |

## 11. 命名隔离声明

- 撤销等级：`DISABLE`、`REVOKE`、`EMERGENCY`
- 审计事件：`workflow.run.security_cancelled`
- 降级标识：`degraded_mode_id`

## 12. 未决决策引用

- `DECK-019`: 安全撤销是否强制终止活动 run —— 默认假设：普通禁用不终止；安全撤销允许强制终止并审计。本 task 实现该默认假设，待决策单确认后更新策略。
