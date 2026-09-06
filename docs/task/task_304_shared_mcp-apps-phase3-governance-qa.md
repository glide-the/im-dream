<!-- [输入] Phase 2 当前候选证据、插件生命周期设计、多会话隔离和观测需求。 -->
<!-- [输出] G3-01—G3-07 的治理、版本、隔离、诊断、资源策略与最终 QA 合同。 -->
<!-- [定位] Phase 3 技术工作项；不替代生产发布证据。 -->
<!-- [同步] 2026-09-06：按真实 Phase 2 依赖和 G3 验收重建工作项。 -->

# task_304：MCP Apps Phase 3 治理与最终 QA

## 1. 目标

完成插件 manifest、安装/禁用/升级/销毁、多用户多会话隔离、分段诊断、版本漂移测试、资源策略和最终回滚演练。

Phase 3 完成仍不自动启用 production Apps；真实外部 Server、生产权限、运维和发布需要当前环境的独立证据。

## 2. 必要技术依赖

- Phase 2 的 I2-01—I2-07 在同一当前候选上通过。
- 低风险 allowlist、高风险拒绝、`ui/message` 和 `window.im` 的权限与 no-replay 证据完整。
- Host/Node/Python/Chat 的 identity、revision、teardown 和普通 fallback 稳定。

## 3. 工作项

| ID | 工作项 | 通过标准 |
|---|---|---|
| G3-01 | manifest 声明 Browser/Node entry、协议/SDK 版本范围和 feature flag。 | 声明与实际能力一致；不兼容时 fail closed。 |
| G3-02 | 安装、启用、禁用、升级、销毁和不兼容处理。 | 禁用立即失效已有 Client/View/session；普通结果保留。 |
| G3-03 | 多用户、多 workspace、多 Server、多 Browser session 隔离。 | catalog、result、notification 和 credential 不串用。 |
| G3-04 | Browser、Chat、Node endpoint、上游 Server 分段诊断。 | 能区分投影、transport、resource、iframe、权限和上游错误。 |
| G3-05 | 协议版本和依赖升级合同测试。 | 升级前重跑官方 demo、inspector、Browser 和回归矩阵。 |
| G3-06 | resource 大小、超时、并发和网络访问策略。 | 超限只影响目标请求，不传播到 Agent turn。 |
| G3-07 | 仅在出现多 Host 或跨网络真实需求时评估独立 Bridge/Gateway。 | 新拓扑有独立 ADR；默认继续使用 Next Node Runtime。 |

## 4. 最终 QA

- 覆盖普通 MCP、无 UI tool、只读 App、低风险交互 App 和全部 fallback。
- 覆盖安装、禁用、升级、版本不兼容、断线、Node restart、Thread switch、refresh 和 teardown。
- 覆盖多维隔离、恶意消息、权限拒绝、资源超限、CSP/origin、日志脱敏和供应链漂移。
- 根 build/start/standalone、Backend/Node/Browser suites、Markdown/link/diff 和清理回执均基于同一候选。
- 生产开关在验证前后保持关闭。

## 5. 回滚

按插件版本、Server 或 App 禁用；关闭 Apps capability 并释放无引用连接。不得改变普通 Claude Agent MCP 路径、数据库 schema、用户历史或生产配置。
