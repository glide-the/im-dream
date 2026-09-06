<!-- [输入] Phase 1 当前候选证据、MCP Apps client-host 合同、DEC-002 与服务端权限策略。 -->
<!-- [输出] I2-01—I2-07 受控双向交互的实现、验收和回滚合同。 -->
<!-- [定位] Phase 2 技术工作项；只开放策略允许的低风险页面能力。 -->
<!-- [同步] 2026-09-06：按真实 Phase 1 依赖与 I2 验收重建工作项。 -->

# task_303：MCP Apps Phase 2 受控双向交互

## 1. 目标与边界

在 Phase 1 当前候选证据完整后，实现标准 `tools/call`、`ui/message`、Host→App context 更新和版本化 `window.im` 兼容层。

本阶段不开放需要逐次确认的高风险写工具，不新增私有 Browser/Node 协议、独立 Gateway、数据库 schema 或第二 Chat ingress。

## 2. 必要技术依赖

- Phase 1 的 N1/C1/S1/M1/H1 在同一源码、lock、制品和 Browser 指纹上通过。
- Browser 只连接 IM 同源 endpoint；Node 每次调用前重验 actor/workspace/Server/tool/revision/allowlist。
- Host adapter 持有 AppBridge、双 iframe、sandbox snapshot 和 teardown。
- 普通 fallback、refresh/reconnect no-replay 与 production Apps 关闭证据完整。

## 3. 工作项

| ID | 工作项 | 通过标准 |
|---|---|---|
| I2-01 | 用 `AppBridge.oncalltool` 接管页面工具请求，并沿 Browser Client→Node→Server 标准链路调用。 | Host/Node 均校验；成功调用不创建 Agent turn。 |
| I2-02 | 服务端 App-callable allowlist 只开放策略允许的低风险工具。 | 高风险、未分类和需逐次确认的工具在 Node 拒绝且不上游。 |
| I2-03 | `ui/message` 接入当前页面已有 Thread 的正常 Chat ingress。 | 一次请求生成一个普通用户消息和一个新 Agent turn。 |
| I2-04 | Host→App 发送声明范围内的 input/result/theme/locale/display context。 | 不包含完整对话、系统提示词或敏感配置。 |
| I2-05 | 实现版本化 `window.im` 兼容层。 | 与规范成员保持同参数、返回和失败语义；只改变 namespace。 |
| I2-06 | 文件、modal、display mode 和导航能力逐项 feature detect。 | 只有真实实现的能力才被声明；单项关闭不影响标准 bridge。 |
| I2-07 | 覆盖恶意 tool、URI、message、origin、revision 和重放请求。 | App 无法绕过 Node 权限；拒绝可审计且不上游。 |

## 4. 写入范围

仅修改 Phase 2 直接涉及的 Runtime policy、Browser Host、`window.im` adapter、当前 Chat ingress adapter、focused tests 和对应文档。具体路径必须在执行前按当前源码枚举。

不得修改首次 Agent 工具调用所有权、Thread/EventBus/SSE/resume/cancel 语义、数据库 schema、Gateway、真实 Server 配置、Phase 3 治理或 production Apps 开关。

## 5. 验收与回滚

- 低风险正向调用、拒绝、高风险零上游调用、`ui/message`、context 最小披露和 `window.im` feature detection 均有当前 Chrome 证据。
- Browser refresh、Thread switch、close/reopen、Node restart 和 revision 变化不重放写操作。
- 日志不包含 secret、完整对话、App 正文或 credential。
- 关闭 page-tool、message 或 `window.im` capability 可独立回退到 Phase 1 只读 App。
- 验收失败只关闭对应 capability，保留普通结果与 production Apps 关闭。
