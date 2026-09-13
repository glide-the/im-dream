<!--
[Input] Current actor/thread Notion projection, Runtime 0.1.3 failure baseline, published Runtime 0.1.4, and normal Dream Chat acceptance evidence.
[Output] Track the cross-repository root cause, ownership, implementation boundary, verification ledger, and completed release work.
[Pos] Dream-side implementation task record; detailed design and sequence authority remain under docs/design/notion-session/.
[Sync] 2026-08-30: record completed implementation, real-business verification, same-SHA npm publication, and Dream 0.1.4 adoption.
-->

# Notion CLI 环境进入 Agent Bash 修复任务

<!-- [Sync] 2026-09-13: separate current config-read regression from completed historical 0.1.4 acceptance. -->

## 当前 config-read 回归（2026-09-13）

本轮任务 `01a09969-a9f1-7382-b707-c83337e2ae53` 基于 Dream `98f72dbd`，
SDK 0.2.145 / 正常 Runtime 0.1.9 / ntn 0.15.1。历史任务最终 0.1.4 候选
验收确已通过，旧 blocked 仅是早期阶段；下方发行及服务记录均属于历史，
不能表示当前安装或替代本轮真实回执。

本轮已用 installed Runtime 和真实 ntn、合成 config 复现相同读取错误，
定位到 `2577b9a` 引入的严格 PATH 相对项拒绝与本机缺失相对目录组合。
最小修改只在 Dream `sdk_env.py` 对当前有效 Notion launch 去除最终 cwd 下
确证缺失的非空相对 PATH 目录；不重排有效路径、不前置目录、不改认证源、
Runtime 版本或 resume。细节与影响矩阵见既有修复设计，业务图见既有时序文档。

修复后四文件最终回归：45 passed，exit 0，0 skipped。包含 native fixture、
installed ntn config 与 existing-relative-shadow-denied 三个 production Runner case。
installed ntn case 空 auth、有效合成 config 返回本地未选 workspace；
另一次 A/B 使用 synthetic token 到达外部 invalid-token 响应，明确不算离线。
14 个正常命令 lookup 对照保持原路径，父 PATH 未改。
四文件为 `test_notion_credentials.py`、`test_sdk_env.py`、
`test_notion_runtime_integration.py`、`test_claude_agent_notion_cli_runtime.py`；
准确运行命令和日志目录见修复设计本轮验收段。
`git diff --check` exit 0；11 个 Markdown 文件、35 个相对链接检查通过，
README EN/ZH 结构和新增事实一致。

正常 backend 由并行 resume 任务唯一启动（PID 68562），本轮补丁已应用到正常仓库；
现有前端/Admin/Gateway 未修改。真实 thread `56887baf-e44a-4816-a3aa-0cfb44f3b0a1`
三轮 completed：首轮普通聊天/时间工具成功，Grep 不计 Notion；后二轮各一次
真实 `ntn api v1/search` 返回 list、results=1、has_more=true 和 request_id，
无 config 错误。第二/三轮 turn 为 `0f8f03d1-ad7d-4b0e-9b83-0745f048617a` /
`b436289e-8f40-4391-8db2-9ca124950d1f`，保持首轮回写的同一 Claude ID。
刷新重开后三轮历史可见，completed/idle、输入可用。三次 config 投影 mtime
严格递增，权限仍为 config0600/home0700且非 symlink。具体元数据和边界见修复设计。
该结果只证明在线只读 API 可用，不评价搜索匹配；未进行 Notion 写入。
SDK/Runtime/ntn 继续使用正常安装 0.2.145/0.1.9/0.15.1，没有发布或替换制品。

## 历史任务记录（0.1.4）

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
