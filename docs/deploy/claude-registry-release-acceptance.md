<!-- [输入] 已公开的 SDK PyPI 精确版本、Runtime npm 精确版本、期望 CLI --version 文本。 -->
<!-- [输出] provider-free registry 发布验收命令、结构化回执与 fail-closed 排障边界。 -->
<!-- [定位] SDK/Runtime 真正发布后的 Dream 依赖切换前置门；不负责发布或修改依赖锁。 -->
<!-- [同步] 2026-08-24：新增 PyPI wheel/sdist、npm 五包、隔离安装与 404 安全错误合同。 -->

# Claude SDK/Runtime Registry 发布验收

## 当前外部状态（2026-08-24）

两个 registry 包都**尚未发布**：PyPI 查询
`ink-claude-dream-agent-sdk==0.2.143` 为 404，npm 查询
`@glide-the/ink-claude-code-dream@0.1.0` 也为 404。因此当前不能生成成功回执，
也不能据此把 Dream 的不可变 Git 依赖或本机 Runtime 安装切换到 registry。

已确认的发布控制面状态如下：

- SDK GitHub repository 已创建 `testpypi`、`pypi` environments；required reviewer
  是 `glide-the`，因为当前唯一 collaborator 是本人，所以平台允许自审；deployment tag
  policy 只允许 `v*`。
- Runtime GitHub repository 已创建 npm environment，只允许 `main`；当前 private plan
  不支持 required reviewer，不能把“无 reviewer 门”描述成审批已完成。
- Runtime repository 的 Actions self-hosted runners 当前为 `0`；四平台 qualification
  workflow 尚无可执行的 self-hosted runner capacity。

这些状态只说明控制面已有部分配置，不证明制品已经上传、四平台资格已完成或法律发布门已
满足。registry 404 必须保持 fail closed，不得降级为 skip、本机制品或 GitHub artifact。

## 适用时机与命令

仅在 PyPI 与 npm 都真正出现精确版本以后，从 Dream 仓库根目录执行：

```bash
python3 scripts/verify_claude_registry_release.py \
  --sdk-version 0.2.143 \
  --runtime-version 0.1.0 \
  --expected-cli-version '2.1.241 (Claude Code)'
```

本验收不执行 publish，不修改 `pyproject.toml`、`uv.lock`、`requirements.txt`、Docker
或数据库。前置条件是 Python 能创建 venv，且 PATH 中存在 npm。当前仅支持
`darwin-arm64`、`darwin-x64`、`linux-arm64`、`linux-x64`；Windows、Linux musl
和其他架构继续 fail closed。

## 验收内容

脚本只访问官方公开 PyPI/npm registry，并只写测试自有临时目录：

1. 从 PyPI 精确版本端点取得 canonical 文件名的唯一 wheel 与唯一 sdist；下载字节的
   SHA-256 必须与 metadata 一致。ZIP/TAR 拒绝绝对路径、路径穿越、链接/设备节点，
   任意层级不得包含 `*.map`。
2. 从 npm 读取 selector 与 Darwin/Linux arm64/x64 四个平台包的同一精确版本；
   selector 的 `optionalDependencies` 必须恰好映射四个平台包，不能是 range、tag 或漏包。
3. 对五个包分别执行 `npm pack`；registry `dist.integrity`、pack 回执与本地 SHA-512
   SRI 必须三方一致。每个 tgz 再解析 `package/package.json`，复验 name/version、selector
   bin 与四包映射、无普通 dependencies，以及平台 os/cpu、严格唯一的
   `bun@1.4.0` dependency、`inkRuntime`；五包还必须有非空且非 `UNLICENSED`
   的 license、public/provenance publishConfig 与 canonical prepack；链接/设备与任意
   `*.map` 均拒绝。
4. 在临时 npm project 中用已校验的 selector 和当前平台 tgz 执行正常 `npm install`。
   当前平台包是 root explicit dependency，所以使用 `--omit=optional` 避免安装 selector
   的其余跨平台 optional 包；不使用 `--ignore-scripts`，让 `bun@1.4.0` 完成真实
   postinstall，再确认生成
   `node_modules/.bin/ink-claude-code-dream`。
5. 在临时 venv 安装已校验 wheel；`claude_agent_sdk` import provider 必须唯一为
   `ink-claude-dream-agent-sdk`，official `claude-agent-sdk` 必须不存在；distribution
   version、`sdk.__version__`、`_cli_version.__cli_version__` 与公开
   `ClaudeAgentOptions`、`ClaudeSDKClient`、`query` 必须一致。
6. 用公开 `ClaudeAgentOptions(cli_path=...)` 指向临时 npm 安装的 CLI，并对同一绝对
   路径执行 `--version`，stdout 必须与命令行给出的期望文本完全相同。

整个流程不调用 `query`、不访问模型、Provider、Gateway、MCP、数据库或 Dream 服务。
子进程环境采用 allowlist，只保留 PATH、locale、公开网络代理和证书变量；
Anthropic/Claude 模型凭据，以及 npm/PyPI/PIP registry token/config 环境变量均不转发。
代理变量可能包含代理自身认证信息，所以成功回执只陈述上述两类 credential environment
未转发，不泛称“所有 credentials 均未转发”。临时目录在退出时删除。

## 回执与失败语义

成功时退出码为 `0`，stdout 是 `ink-claude-registry-acceptance/v1` JSON，包含两类
Python 制品 SHA-256、五个 npm tgz 的 SHA-512 integrity、当前平台包、唯一 import
provider、SDK/API/CLI 版本与 CLI 绝对路径。临时路径不进入 artifact 摘要。

任一 registry 404、网络错误、metadata/哈希/integrity/版本/包集合不一致、source map、
安装失败或 API/CLI smoke 失败都退出 `2`。stdout 只输出
`ink-claude-registry-acceptance-error/v1` 的闭集安全字段，不回显 npm/pip stderr、URL
query、环境变量或 Token。当前 404 应呈现为：

```json
{
  "schemaVersion": "ink-claude-registry-acceptance-error/v1",
  "status": "failed",
  "safe": true,
  "error": {
    "code": "REGISTRY_VERSION_NOT_FOUND",
    "phase": "pypi-download",
    "message": "requested PyPI release is unavailable",
    "registry": "pypi",
    "package": "ink-claude-dream-agent-sdk",
    "version": "0.2.143",
    "http_status": 404
  }
}
```

只有成功回执才能进入后续“原子更新三份 Python 依赖真相源与容器安装合同”任务；本脚本
永不执行该变更。

## Provider-free 回归测试

```bash
backend/.venv/bin/python -m pytest -q \
  backend/tests/test_verify_claude_registry_release.py
```

测试动态构造本地 wheel/sdist/npm tgz，使用
`backend/tests/fixtures/claude_registry_release.json` 的非生产身份，并注入假 registry
runner；不访问真实 PyPI/npm。隔离安装用例只安装无依赖假 SDK，并执行本地假 CLI 的
`--version`，不访问模型、凭据、数据库或服务。
