# task_275a_shared_supply-chain-owner-signoff

> Task ID: `task_275a`
> Source Issue: `DECK-SC-001`
> Paperclip Issue: [SUO-275](/SUO/issues/SUO-275)
> Domain / Priority: `shared` / `P0`
> Gate: `DECK-GATE-DEC-017` / Stage 4 production Gate

## 1. 任务标题

具名 Supply-Chain Owner 任命与最小权限签署合同

## 2. 关联 Issue

| 关联 | 内容 |
|---|---|
| 来源条目 | `DECK-SC-001` — 具名 Owner 任命与签署责任矩阵 |
| Task-stage Issue | [SUO-275](/SUO/issues/SUO-275) |
| 来源编排 | [SUO-258](/SUO/issues/SUO-258) |
| Design 裁决 | [SUO-261](/SUO/issues/SUO-261) — `no_design_delta` |
| Issue 清单 | `docs/issue/ISSUES_deck-plugin-stage4-supply-chain.md` |
| Canonical design | `docs/design/deck/design_002_deck-plugin-decision-gates.md` §4.2.5 |
| 标签 | `supply-chain`, `ownership`, `governance`, `signature` |

## 3. 任务目标

为 security、marketplace/制品平台、runtime 三类生产责任域形成可机器校验、可点击复核的具名任命与签署记录。每名 owner 必须签署其允许和禁止的最小权限范围、否决权、有效期及证据对象 hash；临时覆盖必须有到期时间和替代 owner 行动。

本任务不实现任何服务、UI、测试或生产放行。任务完成只解除治理前置，不代表 `DECK-GATE-DEC-017`、Stage 4 或 production Gate 获批。

### 3.1 shared 边界

| 边界 | 责任 |
|---|---|
| Frontend | N/A；不得把 owner 任命做成 UI 实现 |
| Backend | N/A；不得创建权限或签名服务 |
| 治理 | CEOOrchestrator 路由并确认三类 owner；owner 只签署自身范围 |
| 联调 | N/A；仅验证签署记录引用相同合同 revision/hash |
| 验收 | 独立检查主体、scope、有效期、签名对象和链接是否完整 |

## 4. 实现步骤

1. 冻结一份 `owner_signoff_contract_revision`，其内容至少包括 `DECK-GATE-DEC-017`、trust-policy、双重摘要、留存/冷恢复及 fail-closed 的合同 hash。
2. 解析并记录三类 owner：
   - security owner：信任根、publisher identity、算法矩阵、轮换/撤销/过期、离线验证与 fail-closed；
   - marketplace/制品平台 owner：签名包生成与留存、CAS/冷存储、引用清理、RTO/RPO 与恢复演练；
   - runtime owner：物化后实际字节二次摘要、cache 不可信、load receipt 和拒绝路径。
3. 对每名 owner 记录 `principal_id`、显示名、任命类型、`valid_from`、`valid_until`、允许 scope、禁止 scope、否决权、delegation 规则及应急联系人。
4. 获取每名 owner 对相同 `contract_sha256` 的显式 `approve|request_changes`。签署记录包含签署时间、范围、评论/附件链接和签名方式。
5. 对临时覆盖记录覆盖理由、最大范围、到期时间、正式 owner 补位动作和 owner；过期后自动视为未签署。
6. 生成机器可读 JSON 与人类可读 Markdown 摘要；二者规范化后 hash 必须可重算，链接必须实际可访问。
7. 独立验收者验证无主体自签超出自身 scope、无空白/群组占位 owner、无未到期信息缺失，并给出逐项结论。
8. 任一 owner 缺失、`request_changes`、过期或链接不可访问时输出失败结论并保持 production Gate 阻断。

## 5. 涉及文件路径

| 路径 / 资源 | 动作 | 允许的最小变更 |
|---|---|---|
| `artifacts/deck-plugin-stage4/governance/owner-signoff-matrix.json` | 新建 | 结构化 owner、scope、revision、hash 与签署引用 |
| `artifacts/deck-plugin-stage4/governance/owner-signoff-matrix.md` | 新建 | 人类可读摘要、缺口和 Gate 结论 |
| 当前执行 Issue 的 Paperclip 评论/附件 | 新建 | 具名签署原始证据与可点击链接 |

`artifacts/` 路径是交付物导出位置；若运行环境使用对象存储或 Paperclip 附件，必须在 JSON 中保存不可变 URL 和内容 hash，不得写占位 URL。

## 6. 输入 / 输出说明

### 输入

- §4.2.5 三类审批动作及 `DECK-SC-001` 验收条件；
- 三类 owner 的可验证 principal identity、任命依据和权限系统 scope；
- 待签署合同 revision 与 SHA-256。

### 输出

```jsonc
{
  "owner_signoff_contract_revision": "deck-sc-owner/v1",
  "contract_sha256": "sha256:<64-lowercase-hex>",
  "owners": [{
    "role": "security|artifact_platform|runtime",
    "principal_id": "...",
    "appointment": "temporary|permanent",
    "valid_from": "...",
    "valid_until": "...",
    "allowed_scopes": ["..."],
    "forbidden_scopes": ["..."],
    "veto_scope": ["..."],
    "decision": "approve|request_changes",
    "signed_at": "...",
    "evidence_url": "...",
    "evidence_sha256": "sha256:..."
  }]
}
```

## 7. 依赖项、可并行性与冻结点

- 前置依赖：无。
- 下游：`task_275b` 的 production trust-policy approval、`task_275f` 的运营承诺、`task_275d` 的 runtime 签署。
- 技术实现可限域准备，但任何 `production_ready`、Stage 4 Gate 通过或 rollout 复审都冻结到三名 owner 有效签署。
- Clarification owner/action：`CEOOrchestrator` 任命三类 owner；若临时覆盖，必须明确有限 scope、期限及正式补位动作。

## 8. 测试策略

| 方法 | 场景 | 通过标准 |
|---|---|---|
| `python -m json.tool artifacts/deck-plugin-stage4/governance/owner-signoff-matrix.json` | JSON 可解析 | 退出码 0 |
| schema 校验脚本 | 必填字段、枚举、时间与三类角色唯一性 | 三类角色恰好各一条有效记录 |
| `shasum -a 256` | 合同/证据 hash 重算 | 与记录值一致 |
| 链接检查 | 评论、附件、任命依据 | 全部可点击且内容 hash 匹配 |
| 权限复核 | allowed/forbidden/veto scope | 无空白、群组占位或超范围自签 |

## 9. 完成标志

- [ ] security owner 已具名并签署信任根、算法、失败策略和轮换/撤销 scope。
- [ ] marketplace/制品平台 owner 已具名并签署签名包、CAS、留存、冷恢复和运营指标 scope。
- [ ] runtime owner 已具名并签署发布冻结结果消费、二次摘要和 load receipt scope。
- [ ] 每条记录含主体 ID、时间、范围、否决权、revision/hash 和可点击证据。
- [ ] 临时覆盖包含到期时间和正式补位 owner/action。
- [ ] 独立验收结论已留存；缺失项明确保持 production Gate 阻断。

## 10. 风险提示与回滚

| 风险 | 处理 / 回滚 |
|---|---|
| 用团队名代替个人主体 | 判定失败；要求可验证 principal ID |
| CEO 临时覆盖无限期或无限 scope | 判定失败；补充到期和有限 scope |
| 签署对象后续变化 | 旧签署失效；新 revision/hash 重新签署 |
| 链接存在但内容可变 | 保存内容 hash 或不可变附件版本 |

回滚只能撤销或 supersede 任命记录并恢复 Gate 阻断；不得删除历史签署或把过期签署继续视为有效。

## 11. 允许 / 禁止修改范围

- 允许：§5 列出的治理 artifact 与当前执行 Issue 的评论/附件。
- 禁止：`docs/design/`、`docs/issue/`、`docs/task/`、`docs/stage/`、`docs/exec/`、源码、测试、配置、密钥和权限系统本身。
- 未列出的路径默认禁止；真实密钥、证书私钥或 bearer token 不得进入证据。

## 12. StagePlanner / Execute Readiness

| 字段 | 值 |
|---|---|
| 前序 | 无 |
| 可并行 | 三名 owner 的资料收集可并行；最终 hash 冻结后分别签署 |
| Freeze point | 同一 `contract_sha256` 的三方有效签署 |
| 最小 execute readiness | 三类 principal 可解析、合同 revision 已冻结、证据存储可生成不可变链接 |
| 证据格式 | owner-signoff JSON/Markdown、不可变证据 URL 与 SHA-256、独立验收 verdict |
| Clarification owner/action | `CEOOrchestrator` 任命三类 owner；临时覆盖必须补充有限 scope、到期时间和正式补位动作 |
| 未满足 Gate | 真实实现、演练、独立 reviewer 与独立复审均仍待后续 task |

本 task 标记完成不等于 production Gate approve。
