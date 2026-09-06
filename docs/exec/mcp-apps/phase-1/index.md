<!-- [输入] 当前 canonical task_411/task_434 候选的 N1/C1/S1/M1/H1 与 P1 决策。 -->
<!-- [输出] Phase 1 当前技术证据索引和 production 边界。 -->
<!-- [范围] 证明 provider-free technical preview；不证明真实外部 Server 或 production 发布。 -->
<!-- [同步] 2026-09-06：完成 official AppServer + pnpm + production-module adapter 的当前候选重验。 -->

# MCP Apps Phase 1 当前证据索引

| 范围 | 证据 | 当前结果 | 含义 |
|---|---|---|---|
| 执行输入 | [historical task requirement](filled-task-requirement.md) | trace | 当前实现入口为 task_411-01/02/03 和 task_434。 |
| N1 | [build、health 与 rollback](n1-build-health-rollback.md) | pass | Root Next、strict types、standalone health 和 shell 通过。 |
| C1 / M1 | [projection 与 manager security](c1-m1-contracts.md) | pass | 当前 Python/Node identity、revalidation、allowlist 与 teardown 通过。 |
| S1 | [official AppServer](s1-appserver.md) | pass | 未修改 `1.7.5` 为当前目标，`1.7.4` 兼容 smoke 通过。 |
| H1 | [Browser Host](h1-browser.md) | pass | production modules、完整结果、双 iframe、生命周期和视觉检查通过。 |
| P1 | [decision](p1-gate-decision.yaml) | Go | 只授权 Phase 2/3 technical preview；production 不启用。 |

统一命令、Phase 2/3 状态和真实业务边界见 [Phase 0—3 当前候选技术验收](../current-candidate-validation.md)。全程保持 `production_apps_effective=false`。
