<!-- [输入] 已公开的 SDK PyPI 精确版本、Runtime npm 精确版本和期望 CLI 版本文本。 -->
<!-- [输出] 发布后 provider-free registry 验收步骤与 fail-closed 判定。 -->
<!-- [定位] SDK/Runtime 发布后的最小验收；完整打包、发布和 Dream 集成见相邻操作手册。 -->
<!-- [同步] 2026-08-28：更新为已发布 SDK 0.2.144、Runtime 0.1.2、same-SHA workflow 回执和 provider-free registry fresh install。 -->

# Claude SDK/Runtime Registry 发布验收

完整发布与 Dream 接入流程见
[`claude-sdk-runtime-packaging-and-integration.md`](claude-sdk-runtime-packaging-and-integration.md)。

## 当前状态

| 制品 | 状态 | 当前版本 |
| --- | --- | --- |
| PyPI SDK | 已公开 | `ink-claude-dream-agent-sdk==0.2.144` |
| npm Runtime selector | 已公开 | `@glide-the/ink-claude-code-dream@0.1.2` |
| npm 平台包 | 四包均已公开 | darwin/linux × arm64/x64 `0.1.2` |

SDK wheel/sdist 当前正式 PyPI 摘要：

| 文件 | 大小 | SHA-256 |
| --- | ---: | --- |
| `ink_claude_dream_agent_sdk-0.2.144-py3-none-any.whl` | 151,704 B | `50801104b1dcf8c0eb64555eb62f27f6238b37635c2ccbcb391bd562ee85ca56` |
| `ink_claude_dream_agent_sdk-0.2.144.tar.gz` | 373,286 B | `1b2b6dfad5bfa766de24682d7b26ef1f1394097b92a5d32be1eae40530fbd517` |

Runtime registry tarball 当前 SHA-256：

| npm 包 | 大小 | SHA-256 |
| --- | ---: | --- |
| selector | 18,405 B | `0d6ed5371614b478b57fe192ff5555537279d790ae552818cd4b0b307e24ddc3` |
| darwin-arm64 | 27,006,615 B | `2c39bf8146ebcc65f3f1ecb55d969b722ad9779473398d41c784cb88caa8eeb2` |
| darwin-x64 | 29,157,799 B | `7050576a5b809e6662bc791138efb28a04fa56d053d220cfb892034b4b36f8e9` |
| linux-arm64 | 37,968,588 B | `abc209eccd9ace4ad20050db9f04d587959560e48fc3373f5b478288c5f80da2` |
| linux-x64 | 37,472,361 B | `0af763146bf0f5656baa552445e8953de18cec7650938a5060d1d6cd62bdd53b` |

发布回执：SDK workflow `32874352449`；Runtime release `main@c3e4d4e2f74960c75b42b1cd48adedf90345a10b`，
qualification workflow `33149053281`，publish workflow `33151128000`。Runtime token fallback 只允许
五个 Runtime 包读写、无 organization 权限；GitHub `npm` Environment 的 `NPM_TOKEN` 与 npm token
按用户要求保留，当前到期日为 2026-11-26，本地明文中转副本已清除。

## 最小验收

### PyPI

1. 查询精确版本 JSON，确认 canonical wheel/sdist 各一个。
2. 比较 registry metadata 与实际下载字节的 SHA-256。
3. 检查归档没有 CLI、`*.map`、凭据、transcript 或 Workspace 数据。
4. 在全新 Python 3.12 venv 安装，确认：
   - distribution 是 `ink-claude-dream-agent-sdk`；
   - import 是 `claude_agent_sdk`；
   - official `claude-agent-sdk` 不共存；
   - 公共 API 与版本一致；
   - 没有 Git `direct_url.json`。

### npm

1. 查询 selector 和四个平台包的精确版本、`dist.integrity`、license、os/cpu。
2. selector `optionalDependencies` 必须精确映射四个平台包的同一版本。
3. 对五包执行 registry `npm pack` 并比较 SHA-512 integrity。
4. 检查 selector launcher 与平台 standalone 的 manifest、capability、SBOM、checksum。
5. Bun 版本记录在 Runtime manifest 中；平台包不得要求目标机器安装 ambient Bun。
6. 源、tgz 和 fresh install 均不得包含 `*.map`。
7. 在当前支持平台全新安装 selector，验证：
   - `ink-claude-code-dream --version` 与 `claude --version` 都输出 `2.1.241 (Claude Code)`；
   - selector 只解析当前平台包；
   - release manifest 配对 SDK `0.2.144` 与 Runtime `0.1.2`；
   - Dream Runtime resolver 通过。

## 失败语义

以下任一情况必须 fail closed：

- registry 404；
- 版本、文件名、大小、哈希或 integrity 不一致；
- selector 缺少平台包或使用非精确版本；
- 当前 os/cpu 不受支持；
- manifest、capability、SBOM 或 checksum 不一致；
- 归档或安装树出现 `*.map`；
- SDK import provider 不唯一；
- CLI version 或 Dream resolver 失败。

不得把 404/失败降级为使用本机旧产物、GitHub artifact、Git 安装源或 ambient CLI。

## 测试边界

Registry 验收不调用模型、Gateway、MCP、数据库或 Dream 服务，不转发 Anthropic、npm、
PyPI Token。若发布的是此前已经通过业务验收的同一字节，只需补 registry 安装与接入
smoke；实现字节或接口合同发生变化时，必须再执行完整 Claude/MCP 和真实 IM 业务验收。

本次命令为 `python3 scripts/verify_claude_registry_release.py --sdk-version 0.2.144
--runtime-version 0.1.2 --expected-cli-version '2.1.241 (Claude Code)'`，exit 0。回执为
`status=passed`、`providerFree=true`、`modelInvoked=false`；当前平台 selector 安装、SDK wheel 和
sdist 两条隔离路径均通过，未透传模型 Provider 或 package registry 凭证。
