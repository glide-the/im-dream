<!-- [输入] 当前 Backend projection 与 Node Runtime 的 focused/adversarial tests。 -->
<!-- [输出] C1-01—C1-06 和 M1-01—M1-08 的最小披露、授权、连接与 teardown 证据。 -->
<!-- [定位] 当前 Phase 1 provider-free C1/M1 回执；不含真实 credential 或生产连接。 -->
<!-- [同步] 2026-09-06：完成 OAuth refresh revision、profile drift 与 canonical Runtime identity 验收。 -->
<!-- [同步] 2026-09-13：明确 Server/workspace/tool-use ID 校验条件；仅修正文案，不重跑或扩大旧回执范围。 -->

# C1 / M1 当前合同证据

## C1 Python projection

- 服务身份使用固定时间比较；actor、workspace、Server、enabled、transport、discovery、config/credential/policy revision 和有效期均在解密前校验。
- 静态视图与短时单 Server connection view 分离；OAuth refresh 后重读权威 record/credential 并要求 revision 单调推进；响应只包含当前 scope 必需 URL/profile/headers/env，`repr` 和错误均脱敏。
- 结果身份按当前 managed Server 注册记录、turn workspace 及 tool-use ID 确定；输入 `_meta.serverRef` 与该调用确定的 Server 不匹配，或结果为 error 时，只丢弃 App 结果 DTO，普通输出保留。Server 标识只用于调用关联，不能作为授权依据。
- `RuntimeSnapshotLoader.load()` 和普通 Agent turn 继续原生产路径；没有新增 schema、DDL、队列或控制通道。

## M1 Node Runtime

- 单一 Next Route Handler 委派进程级 Runtime；支持标准 GET/POST/DELETE、initialize、notifications、list/read/call 和 session close。
- 每个请求重新取得当前 Python view 并检查 actor/workspace/Server/Browser session/plugin/policy/config/credential revision。
- connector key 覆盖所有身份维度；connection profile 的 canonical SHA-256 digest 进入 same-revision identity 但不包含明文 secret。并发 acquire 合并仅发生在同 scope，同 revision/异值、回滚、禁用、过期、provider error 均 teardown；active lease 也受短时 view expiry timer 约束。
- Phase 1 `tools/call` 零上游；Phase 2 仅服务端正向列表中的低风险工具可调用。资源 URI、tool、network host、redirect、catalog pages、bytes、timeout 和 concurrency 均由 server config/policy 约束。
- 结构化 diagnostics 只有 stage/code/opaque identity，不序列化 URL、query、header、credential、body、HTML 或对话。

## Final receipts（2026-09-06）

| Command | Exit | Result |
|---|---:|---|
| `pnpm --dir frontend test:mcp-apps-runtime` | 0 | 36 passed；包含无后续请求的 adapter session expiry。 |
| `pnpm --dir frontend typecheck:mcp-apps` | 0 | Runtime 与 integration typecheck 无诊断。 |
| 当前 Backend Phase 1—3 + MCP/Agent regression command（见统一回执） | 0 | 262 passed，8 subtests passed。 |

统一完整命令与失败迭代见 [current-candidate-validation.md](../current-candidate-validation.md)。
