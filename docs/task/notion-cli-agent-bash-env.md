<!--
[Input] Current actor/thread Notion projection, Runtime 0.1.3 failure baseline, published Runtime 0.1.4, and normal Dream Chat acceptance evidence.
[Output] Track the cross-repository root cause, ownership, implementation boundary, verification ledger, and completed release work.
[Pos] Dream-side implementation task record; detailed design and sequence authority remain under docs/design/notion-session/.
[Sync] 2026-08-30: record completed implementation, real-business verification, same-SHA npm publication, and Dream 0.1.4 adoption.
-->

# Notion CLI 环境进入 Agent Bash 修复任务

## 任务记录

| 字段 | 内容 |
|---|---|
| 目标 | 确认并修复当前 actor/thread 的 Notion CLI 环境无法进入 Dream 管理的 Agent Bash，并验证新 turn、resume 与只读 `ntn`。 |
| Dream 仓库 | `/Users/dmeck/project/ink-dream-memory`；负责 credential projection、SDK options、真实 Chat harness、设计与业务回执引用。 |
| Runtime 仓库 | `/Users/dmeck/project/ink-claude-code-dream`；负责 production Bash sandbox、capability、构建、测试与 v2 回执。 |
| Runtime 独立 Codex 任务 | `01a05121-4b9c-77a0-b6ca-9e05611e22ef`。 |
| 当前状态 | 实现、真实业务验收、四目标资格、五包 npm 发布、registry fresh install 与 Dream 默认版本升级完成。 |
| Schema / migration | 不需要；未修改数据库 schema、表、migration 或数据合同。 |
| 业务数据 | 保留正常 thread `4ce9fd1a-1244-4893-ab68-a81de14396bb` 与业务日志；未修改 Notion 页面内容或 connector。 |

## 根因与所有权

Dream 的 actor credential source、thread `.notion-home` 投影、`resolve_notion_cli_runtime_env`、最终 SDK `options.env` 和 Python SDK merge 顺序均正确。Runtime 0.1.3 的 production sandbox 在最终 Bash spawn 前只保留通用 shell allowlist，删除了 Dream 已注入的 Notion binding。当前 actor 没有 `workers.json`，因此 workers 配置保持 unset 是独立且正确的可选状态。

最小修复位于 Runtime 0.1.4 的既有 production sandbox：只把通过 canonical thread home、权限、token、workers 和 native `ntn` 校验的 binding 交给 Agent Bash，并继续从 provider helper、stdio MCP、Hook 和无关子进程清除这些值。Dream 生产代码无需修改，避免重复 credential store、wrapper、API、队列或全局 shell 注入。

详细根因矩阵、交互规则、反过度设计结果和完成性审计见 [runtime-bash-env-remediation.md](../design/notion-session/runtime-bash-env-remediation.md)；六类 Mermaid 时序见 [runtime-credential-and-skill-sequence.md](../design/notion-session/runtime-credential-and-skill-sequence.md)。

## 验证账本

- Dream projection/runner focused suite：exit 0，`203 passed, 1 skipped, 122 subtests`。
- Runtime focused sandbox/compiled suite：exit 0，`14 passed`。
- Runtime 最终全套：exit 0，`130 tests, 125 passed, 5 skipped, 0 failed`；formal four-target/five-package lane 通过。
- Runtime lint/packaging contract：exit 0，`2 passed, 1 candidate-only skip`；`productionEligible`、`publicationAllowed`、`redistributionAllowed`、`npmPublishAllowed` 均为 true。
- 正常 Dream Playwright：exit 0，`1 passed (1.8m)`；3 turns、6 个 Bash parts 全部 `output-available`，fresh/resume 两轮均为 token/keyring set、workers unset、`ntn 0.15.1`、doctor/identity ok，普通 Chat 无新增 Bash。
- Runtime v2 回执：`runtime/attestations/dream-real-business-acceptance-0.1.4.json`，授权后 SHA-256 `87f3d1c6040e5462d85e6259a5cb16509a5d26838d5299d1ba350a4ba463dbea`。
- Runtime release：`main@0ebafe95db22101cf77db2c27e73b561d3af37a6`；qualification `33306855166`；publish `33306940462`；五个 `0.1.4` 包均公开。
- Registry fresh install：Node `24.13.0` 下 selector + darwin-arm64 安装成功，两个 alias 输出 `2.1.241 (Claude Code)`，manifest/attestation/`sandbox.notion-cli`/零 map 均通过。

## 运行与发行边界

Dream backend 继续通过受控绝对路径运行与公开包相同 source/executable binding 的 darwin-arm64 0.1.4；frontend 未因本次文档/制品发布重启。Dream 源码 resolver、Docker、双语 README 与测试现统一固定 0.1.4。npm global PATH 仍由操作者按 README 单独升级与验证，不用 `CLAUDE_CODE_CLI_PATH` 隐藏过期默认安装。
