<!-- [输入] 已公开的 SDK PyPI 精确版本、Runtime npm 精确版本和期望 CLI 版本文本。 -->
<!-- [输出] 发布后 provider-free registry 验收步骤与 fail-closed 判定。 -->
<!-- [定位] SDK/Runtime 发布后的最小验收；完整打包、发布和 Dream 集成见相邻操作手册。 -->
<!-- [同步] 2026-08-24：更新为已发布 SDK 0.2.143、Runtime 0.1.0 和 standalone npm 布局。 -->

# Claude SDK/Runtime Registry 发布验收

完整发布与 Dream 接入流程见
[`claude-sdk-runtime-packaging-and-integration.md`](claude-sdk-runtime-packaging-and-integration.md)。

## 当前状态

| 制品 | 状态 | 当前版本 |
| --- | --- | --- |
| PyPI SDK | 已公开 | `ink-claude-dream-agent-sdk==0.2.143` |
| npm Runtime selector | 已公开 | `@glide-the/ink-claude-code-dream@0.1.0` |
| npm 平台包 | 四包均已公开 | darwin/linux × arm64/x64 `0.1.0` |

SDK wheel/sdist 当前正式 PyPI 摘要：

| 文件 | 大小 | SHA-256 |
| --- | ---: | --- |
| `ink_claude_dream_agent_sdk-0.2.143-py3-none-any.whl` | 151,684 B | `e64ea7bf468a6911dfc3ab40f09e42245e203fc78712bd2919c70cc77a27bcd1` |
| `ink_claude_dream_agent_sdk-0.2.143.tar.gz` | 372,447 B | `e2b62792d70b02fd7da92988f73356a92eb544ec1570401a76f8ac0b056e2946` |

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
   - `ink-claude-code-dream --version` 输出精确接口版本；
   - selector 只解析当前平台包；
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
