<!-- [输入] Dream SDK/Runtime resolver、Docker 回滚物、自有 SDK provenance、自有 Runtime manifest 与协议差分回执。 -->
<!-- [输出] 记录当前 SDK × Runtime 配对、历史兼容问题、发布门、验证结果和回滚合同。 -->
<!-- [定位] Claude Agent SDK 与 Claude Runtime 兼容性的当前报告；历史 Route A 仅保留为问题证据。 -->
<!-- [同步] 2026-08-24：更新为自有 SDK 0.2.143 + production-qualified 自有 Runtime 0.1.0，并记录本机内容寻址安装。 -->

# Claude Agent SDK × Claude Runtime 兼容性报告

> 状态：当前本机配对已完成构建、安装、启动、SDK 协议差分和同 core hash 业务回执验证；最新 stdio/HTTP MCP comparator 重跑存在下述参考环境阻断。
>
> 范围：`ink-claude-dream-agent-sdk`、`ink-claude-code-dream` 与显式官方回滚 CLI。
>
> 日期：2026-08-24

## 1. 当前结论

Dream 正常路径已经从“官方 SDK + npm CLI”切换为“自有 SDK distribution + 自有最小 Runtime”，但没有改变上游公开 Python import/API 和进程协议。

| 组件 | 当前身份 | 结论 |
| --- | --- | --- |
| Python | 本机 `3.12.9`；容器 Python 3.12 | 当前 SDK 和后端基线 |
| 自有 SDK | `ink-claude-dream-agent-sdk==0.2.143`，Dream 固定 commit `bcdfbcf9f72bc34865d0efeb5f971d6df005f5b4` | 唯一提供 `claude_agent_sdk`；`packaging/upstream.json` 与 `scripts/verify_upstream.py` 证明 `src/` 对上游 `542fefb3...` 基线空差异 |
| 自有 Runtime | `ink-claude-code-dream==0.1.0`，Runtime commit `cb91a9901303dccb98c5b41cbfa6d56ab88ce97a` | 默认 PATH 入口；manifest `corePruned=true`、`productionEligible=true` |
| Runtime 核心 | 恢复源码证据 `2.1.88`；Dream-facing 兼容标识 `2.1.241` | 只声明 Dream 保留合同通过，不声明与 official `2.1.241` 全产品行为或源码等价 |
| Runtime bundle | SHA-256 `a300fe7fb3da453e45b2f2cd7721bef1963aa991498c26a2826fef8b381161f5` | 1,989 inputs、48 outputs、0 gaps、88 个非必要 feature gate 关闭 |
| Runtime Bun | 独立 `1.4.0`，命令 `ink-claude-code-bun-1.4.0` | 内容寻址安装；不覆盖 ambient Bun `1.2.20` |
| Docker official rollback | Claude Code `2.1.241` | 仅由绝对 `CLAUDE_CODE_CLI_PATH` 选择，不是默认 Runtime |
| 本机 ambient official CLI | `2.1.220` | 只作为当前本机事实；不是 Dream 默认，也不是 Docker 回滚版本 |

兼容性接合面不是包名，而是以下合同：

- `ClaudeAgentOptions.cli_path` 和 subprocess launcher；
- stdio JSONL / stream-json；
- SDK control request/response；
- session ID、transcript 与 resume；
- tools、permission、hooks、plugins、skills 和 ordinary subagent；
- Workspace、sandbox 与 thread-local `CLAUDE_CODE_TMPDIR`；
- MCP stdio/HTTP/OAuth/Resources/management identity；
- authentication 与 Admin Gateway provider 路由。

## 2. SDK 与 Runtime 解析合同

### 2.1 SDK distribution 门

`backend/server.py` 启动时调用 `require_dream_claude_sdk_distribution()`，要求：

1. distribution 名精确为 `ink-claude-dream-agent-sdk`；
2. 版本精确为 `0.2.143`；
3. `claude_agent_sdk` 只能由该 distribution 提供；
4. `ClaudeAgentOptions`、`ClaudeSDKClient`、`query` 和 canonical stream types 存在；
5. official `claude-agent-sdk` 不得并存。

SDK 镜像只改变 distribution 名和打包流程，import namespace 继续为 `claude_agent_sdk`，不提供兼容 shim，也不复制 Agent 状态机。

### 2.2 Runtime 解析顺序

| 优先级 | 来源 | 行为 |
| --- | --- | --- |
| 0 | options 已有 `cli_path` | 保留调用方显式值 |
| 1 | `CLAUDE_CODE_CLI_PATH` | 只接受绝对、存在、可执行路径；版本/hash/capability 由发布预检负责，resolver 不会认证任意 override |
| 2 | PATH 中 `ink-claude-code-dream` | 读取 release-relative manifest/capabilities 并验证生产资格 |
| 3 | 无 | fail closed；不使用 SDK bundled 或 ambient `claude` |

本机默认安装路径是内容寻址 release/toolchain 加 PATH 软链接。启动器会跟随自身软链接定位真实 `lib/core/cli.js`，然后优先发现专用 Bun `1.4.0`。这修复了两个启动问题：

- 直接把 PATH 软链接指向 launcher 时，POSIX shell 的 `$0` 仍是软链接路径，旧代码错误定位到 `~/.local/lib/core/cli.js`；
- ambient Bun 为 `1.2.20`，不能执行需要精确 Bun `1.4.0` 的核心。

安装器现在验证 package、Bun 版本和 digest，复制到不可变内容寻址目录，再原子创建两个 PATH 软链接；不会修改全局 Bun。

容器当前只在源码层安装自有 SDK；受再分发边界约束，自有 Runtime artifact 不进入 Dream Git/Docker build context。容器要么由受控拓扑额外安装同一 qualified artifact 到 PATH，要么显式设置 `CLAUDE_CODE_CLI_PATH=/usr/local/bin/claude` 使用 Docker build 已验证的 official `2.1.241`；两者都缺失时启动 fail closed。

SDK 三个 Git 身份的包含关系如下：Anthropic `542fefb3...` 是 MIT `src/` 基线；Dream 安装的 `bcdfbcf...` 是下游 distribution/portable packaging 提交；当前打包仓库 `e3182c...` 是 `bcdfbcf...` 的直接子提交且只补文档。机器可审计真相源为 [固定上游提交](https://github.com/anthropics/claude-agent-sdk-python/tree/542fefb3b94be87760b2513fff889b91bb5b6672)、打包仓库 `packaging/upstream.json` 和 `scripts/verify_upstream.py`。

## 3. 当前 Runtime 能力与裁剪结果

保留并通过 manifest/接口测试约束的能力：

- headless/SDK query、streaming、双向 control 和 cancel；
- tools、tool result、permission/tool confirmation；
- session/transcript/resume；
- Workspace/cwd/file tools、sandbox、`CLAUDE_CODE_TMPDIR`；
- stdio/HTTP MCP、OAuth、Resources、tool inventory、带冒号 server name；
- plugins、skills、hooks 和 ordinary subagent；
- authentication、Gateway/provider 与必要 diagnostics。

编译期关闭 88 个与 IM 当前合同无关的 feature gate，包括 Remote Control/CCR、team/swarm 产品面、IDE/terminal UI、voice、SSH remote、浏览器工具、上传用户设置、反馈/增强 telemetry 等。删除依据是 source profile、hash assertion、DCE 和协议差分，不是模块名称猜测。

## 4. MCP 最新兼容增量

恢复树为 `2.1.88`，因此最近两个与当前 Dream 直接相关的 MCP 行为以独立、可审查、hash-bound transforms 补齐。transform 真相源是 Runtime 仓库 `compat/mcp-auth/src/patch-spec.ts`：每项记录目标路径、目标源 SHA-256、断言和后置条件，artifact receipt 要求六个 transform ID 全部出现。它不是 `2.1.89–2.1.241` 的全量源码移植。

| 版本证据 | 补齐行为 | 当前验证 |
| --- | --- | --- |
| Claude Code `2.1.238` changelog | stdio initialize 先于 discovery；disabled server 的 list/get 不触发连接；headers helper trust/cwd；凭据环境过滤 | source assertion、compat tests、stdio/HTTP MCP 差分 |
| Claude Code `2.1.239` changelog | remote MCP 在 mid-session reconnect/cloud/SDK `setMcpServers` 遇瞬时 5xx 时有界恢复 | retry classification/backoff、401/403 non-retry、错误脱敏 |

OAuth 另有独立 source-bound 修复：保持 Commander `--no-browser`、一致的 `http://localhost:3118/callback`、pipe/PTY 输入、DCR client information 生命周期、token save 后 `credentials_present` 校验和固定安全错误分类。

## 5. 历史兼容问题与当前处理

### 5.1 `can_use_tool` 应答方言

旧 `claude-code-sdk 0.0.25` 发送 `{"allow": true}`，新版 CLI 需要 `{behavior: "allow", updatedInput}` 或 `{behavior: "deny", message}`；失败表现为静默 deny。迁移到当前 SDK 后以真实序列化和工具确认合同验证。

### 5.2 `HookJSONOutput` Union

SDK `0.2.128` 将 `HookJSONOutput` 变为 TypedDict Union；把它当构造器会抛异常并可能让 deny 决策丢失。Dream 已统一使用纯 dict 字面量，并保留真实类型形状回归。

### 5.3 bundled CLI 抢占

旧 SDK `_find_cli()` bundled 优先，曾遮蔽显式修补的系统 CLI。当前 resolver 只允许 manifest-qualified `ink-claude-code-dream` 或绝对 `CLAUDE_CODE_CLI_PATH`，不存在 bundled/ambient 隐式路径。

### 5.4 2.1.220 单二进制与 seccomp

官方 `2.1.220` 产物结构不再包含旧 `vendor/seccomp` patch 面，`sandbox.seccomp.applyPath` 也被实证为不可用。当前自有 Runtime 不依赖该旧补丁；Docker official rollback 使用新版 nested sandbox/optional seccomp 配置并保留构建期 capability probe。

### 5.5 启动器软链接与 Bun 漂移

旧本机安装直接软链接 artifact launcher，会让 runtime root 解析错误；同时全局 Bun `1.2.20` 与构建要求不一致。当前 launcher 解析完整软链接链，安装器提供独立版本化 Bun `1.4.0`，并用测试证明实际执行的是内容寻址 release 中的 core。

## 6. 验证记录

| 验证 | 命令/范围 | 结果 |
| --- | --- | --- |
| Runtime 全量仓库验证 | `PATH=/Users/dmeck/.nvm/versions/node/v24.13.0/bin:$PATH bun run verify`（Runtime 仓库） | exit 0；Node 44 passed / 2 external OAuth-fixture skips；MCP compatibility 46 passed / 6 source-fixture skips；SDK/acceptance/release/reproducibility 通过 |
| 安装器聚焦测试 | `node --test --test-concurrency=1 tests/core-package-local.test.mjs` | 10/10 passed |
| package verifier | `node scripts/verify-core-package-local.mjs` | 62 files、61 checksums、`productionEligible=true` |
| installed Runtime | 清除两个 override 后执行 `ink-claude-code-dream --version` | `2.1.241 (Claude Code)`；ambient Bun 仍为 `1.2.20` |
| Dream FastAPI startup | 清除 override 后启动 uvicorn | 输出 `Claude Agent factory started` 与 `Application startup complete`，随后干净关闭 |
| SDK 真实进程差分 | official comparator 与 installed candidate | 本轮 exit 0；stream/tool/permission/Workspace/extensions/resume/sandbox/cancel 对齐，不包含本轮 stdio/HTTP MCP comparator 重跑 |
| MCP management | installed candidate + Dream production driver | exit 0；HTTP lifecycle、colon name、OAuth help、identity/redaction 通过 |
| Dream 真实业务 | `dmeck123@suoxya.com` + `剧本创作团队` | 同一 core hash 的既有回执覆盖新会话、多轮、resume、SSE、Workspace、Gateway/ledger；本轮安装器修复未另建 Run |
| Comfy OAuth | `https://cloud.comfy.org/mcp` | 当前自有 Runtime connected，`comfyui-cloud 0.40.1`，41 Tools；logout/remove 完成；费用门禁下未执行远端 Tool |

新一轮 stdio/HTTP MCP 差分校准没有执行到候选：本机 ambient official CLI 是 `2.1.220`，且当前 Dream Python 环境中的 MCP `1.27.1` 不提供该 fixture 需要的 `MCPServer` import，参考 lane 先失败。因此本轮不能声明 stdio/HTTP comparator“重跑通过”。当前可用证据是已安装候选本轮通过的 MCP management/OAuth/inventory，以及先前绑定同一 source digest 与 core SHA-256 的完整 stdio/HTTP 差分回执。

## 7. 发布与许可证边界

- 自有 SDK 源码基线为 MIT；portable wheel/sdist 排除官方 bundled CLI。
- Runtime 仓库只提交自有脚本、patch、manifest、测试和文档。
- 恢复源码和派生 Runtime bundle 不进入公开 Git。
- 当前 Runtime manifest：`productionEligible=true`、`publicationAllowed=false`、`redistributionAllowed=false`。
- 技术资格不能解释为 Anthropic 再分发授权。

## 8. 升级规约

任一 SDK、Runtime、Bun、MCP 或 official rollback 版本变化都必须作为原子升级处理：

1. 更新版本和来源矩阵；
2. 重新验证 SDK `src/` 与上游基线差异；
3. 重放 Runtime source assertions、feature DCE 和 MCP transforms；
4. 运行 SDK/MCP/management 协议差分；
5. 重建 package、SBOM、license report 和 checksums；
6. 运行 Dream startup 与完整业务链；
7. 只有 manifest 与测试全绿后才更新默认 PATH release。

## 9. 回滚

回滚时把 `CLAUDE_CODE_CLI_PATH` 设置为已由发布流程验证的 official CLI 绝对路径；当前 Docker 路径是 `/usr/local/bin/claude`。由于 resolver 只检查绝对/存在/可执行，设置前必须另行验证 exact version、MCP help 和协议 smoke。SDK public API、Dream 业务代码、PostgreSQL Schema、Thread/Run、Workspace、transcript 与 SSE 合同均不需要分叉或迁移。恢复默认时删除该 override，并确保 PATH 中的 `ink-claude-code-dream` 指向 production-qualified 内容寻址 release。
