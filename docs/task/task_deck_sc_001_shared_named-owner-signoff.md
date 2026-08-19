# task_deck_sc_001_shared_named-owner-signoff

## 1. 任务标题

`DECK-GATE-DEC-017` 具名 Owner 任命与签署责任矩阵

## 2. 唯一映射与 Domain

| 字段 | 值 |
|---|---|
| Task ID | `TASK-DECK-SC-001` |
| 来源 Issue | `DECK-SC-001`（`docs/issue/ISSUES_deck-plugin-stage4-supply-chain.md`） |
| Paperclip TaskDesign Issue | [SUO-275](/SUO/issues/SUO-275) |
| Canonical design | `docs/design/deck/design_002_deck-plugin-decision-gates.md` §4.2.5 / `DECK-GATE-DEC-017` |
| Domain | `shared`（治理与跨域 production Gate） |
| 优先级 | P0 |
| 下游 Stage 映射键 | `stage4.supply_chain.DECK-SC-001` |

该映射是唯一映射；后续 Stage 不得把本 Task ID 复用于其他来源 Issue，也不得以通用“审批完成”替代本 task 的三类具名签署。

## 3. 任务目标与非目标

建立安全、marketplace/制品平台、runtime 三类 owner 的具名任命、权限边界、否决权和可审计签署合同，使后续技术 task 能消费确定的 trust root、算法、失败策略、留存/恢复承诺及双重摘要校验审批。

非目标：不实现 trust-policy、签名、摘要、留存或 runtime 代码；不批准 production Gate；不以 CEO/Agent 名称占位模拟真实生产 owner；不修改 canonical design。

## 4. 实现步骤

1. 从组织目录解析三个角色的稳定主体 ID、显示名、团队、有效任期和代理/升级链；缺位时记录 `owner_missing`，不得填匿名团队名。
2. 形成责任矩阵：安全 owner 覆盖 trust root、identity/算法 allowlist、撤销/过期/离线 cache 和 fail-closed；marketplace/制品平台 owner 覆盖签名包、CAS、冷恢复、留存和演练；runtime owner 覆盖发布端冻结结果消费、物化后二次 digest 校验和 receipt 绑定。
3. 定义每类签署的 scope、输入摘要、决策枚举（`approve|request_changes|reject`）、否决权、失效条件和 re-approval 触发条件。
4. 收集三类 owner 的真实签署；每条签署绑定 `DECK-GATE-DEC-017`、`trust_policy_revision`（未知时明确 `pending`）、材料 SHA-256、签署人 ID 和时间。
5. 由治理复核者检查主体有效性、scope 完整性和材料 hash；任何缺位或非 `approve` 结论写入阻断清单。
6. 发布机器可读矩阵和人类可读摘要，并在 Paperclip Issue 中附可点击证据；不得仅写“owner 已确认”。

## 5. 涉及文件与写入边界

### 5.1 允许修改闭集

| 路径 | 动作 | 最小变更 |
|---|---|---|
| `docs/evidence/deck-plugin/supply-chain/DECK-SC-001/owner-responsibility-matrix.json` | 新建/修改 | 三类 owner、scope、任期、升级链和状态 |
| `docs/evidence/deck-plugin/supply-chain/DECK-SC-001/owner-signoffs.json` | 新建/追加 | append-only 签署记录、材料 hash 和裁决 |
| `docs/evidence/deck-plugin/supply-chain/DECK-SC-001/README.md` | 新建/修改 | 人类可读索引、证据链接和未决项 |

未列出的路径默认禁止修改；Paperclip 评论、附件和 work product 只用于发布上述真实证据，不扩张文件写入范围。

### 5.2 禁止修改范围

- `docs/design/`、`docs/issue/`、`docs/task/`、`docs/stage/`、`docs/exec/`；
- 所有实现/测试源码、依赖文件、部署配置和生产策略配置；
- 删除、覆盖或原地改写既有签署；变更必须以 superseding record 追加；
- 把临时代理权限默认为永久任命，或把缺失签署写成 `approve`。

## 6. 输入 / 输出与证据格式

输入：§4.2.5 审批动作、组织身份目录、owner 授权记录、待签材料及其 SHA-256。

输出：责任矩阵、签署记录、未决阻断列表。每条签署至少包含：

`signoff_id`、`decision_id`、`role`、`principal_id`、`principal_display_name`、`authority_scope`、`material_sha256`、`decision`、`signed_at`、`expires_at|null`、`delegation_ref|null`、`veto_scope`、`comment_ref`、`supersedes_signoff_id|null`。

证据必须可从 Paperclip work product/附件点击访问，JSON 可解析，README 能反向链接到签署记录；人名文本或“文档已写”本身不是完成证据。

## 7. 依赖、并行性与 StagePlanner 输入

- 直接前置：无。
- 下游：`TASK-DECK-SC-002` 的生产策略冻结依赖安全 owner `approve`；`TASK-DECK-SC-006` 依赖 marketplace/制品平台 owner 的恢复承诺；`TASK-DECK-SC-004` 的 production rollout 依赖 runtime owner 双路径校验 `approve`。
- 可并行性：owner 解析与三份材料准备可并行；三类签署可并行收集。非生产技术实现可在签署未完成时限域推进，但不得越过 production freeze point。
- 冻结点：三类有效 `approve` 且材料 hash 与当前 revision 一致；任何 `owner_missing`、过期或 `request_changes|reject` 均冻结 Stage 4 production Gate。
- Execute readiness：组织目录可读、三类签署 scope 已定义、材料 hash 已生成、签署渠道与治理复核者已具名。

## 8. 验收条件

- [ ] 安全 owner 具名且权限覆盖 trust root、identity/算法 allowlist、失败策略和轮换/撤销/过期。
- [ ] Marketplace/制品平台 owner 具名且权限覆盖签名包、CAS、冷恢复、留存和演练。
- [ ] Runtime owner 具名且权限覆盖发布端验证冻结、runtime 二次摘要和 load receipt。
- [ ] 每条签署包含稳定主体 ID、时间、scope、材料 SHA-256、裁决和否决权。
- [ ] 治理复核确认所有签署仍有效，且机器可读记录与可点击材料一致。
- [ ] 缺失任一 owner/签署时明确输出 `production_gate=blocked`；未把 `DECK-GATE-DEC-017` 写成 approved。

## 9. 最小测试 / 验证命令

```bash
python -m json.tool docs/evidence/deck-plugin/supply-chain/DECK-SC-001/owner-responsibility-matrix.json >/dev/null
python -m json.tool docs/evidence/deck-plugin/supply-chain/DECK-SC-001/owner-signoffs.json >/dev/null
rg -n 'security_owner|marketplace_artifact_owner|runtime_owner|principal_id|material_sha256|decision|signed_at' docs/evidence/deck-plugin/supply-chain/DECK-SC-001
git diff --check -- docs/evidence/deck-plugin/supply-chain/DECK-SC-001
```

人工/治理验证：逐一反查三个 `principal_id` 的当前授权；重新计算材料 SHA-256；确认 `approve` 不是由执行者自签伪造。通过标准为三类 scope 无缺口且所有引用可访问。

## 10. 完成信号与回滚

完成信号：三类具名 owner 的有效 `approve`、治理复核和可点击证据全部存在；否则 task 可交付阻断结论，但 production freeze 不解除。

回滚：不删除历史签署。授权撤销、主体离职、材料变化或 scope 变化时追加 superseding/revocation record，将 `production_gate` 立即恢复为 `blocked`，并要求新 owner 对新材料重新签署。

## 11. 风险与 Clarification

| 风险/澄清 | 处理 | Owner / action |
|---|---|---|
| 三类 owner 未具名 | 保持 Gate 阻断；技术 task 仅 non-production | `CEOOrchestrator`：任命真实主体或记录限时代理 scope/期限 |
| 同一主体承担多个角色 | 不自动拒绝，但披露职责集中与否决冲突 | `CEOOrchestrator` + 治理复核者：确认是否满足组织职责分离政策 |
| 材料 revision 变化 | 旧签署不得继承 | 对应 owner：对新 `material_sha256` 重新裁决 |

## 12. Gate 声明

本 task 只定义并收集生产 Gate 的治理输入。Task 文档完成、矩阵存在或技术实现推进均不等于 `production_ready`；在三类有效签署和后续独立证据复审完成前，Stage 4 production Gate 保持阻断。
