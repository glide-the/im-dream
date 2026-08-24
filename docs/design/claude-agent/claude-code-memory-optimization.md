<!-- [输入] clean-room Runtime 最终 darwin-arm64 制品、同机历史候选样本、Dream 调用链与五次 `/usr/bin/time -l` 测量。 -->
<!-- [输出] 记录当前 Claude Runtime 内存结果、裁剪关系、测量边界和后续验收方法。 -->
<!-- [定位] Dream 自有 Runtime 的本机内存与加载设计真相源；不讨论远程服务器资源调优。 -->
<!-- [同步] 2026-08-24：替换旧远端 OOM 方案，更新为 MIT clean-room Runtime 最终候选的同机实测。 -->

# Claude Runtime 内存与加载设计

## 1. 结论

Dream 当前默认 Runtime 已从旧本地派生候选切换为仓库独立实现的 MIT clean-room Runtime。最终 darwin-arm64 standalone 在同一台 Apple arm64 Mac 上的最大 RSS 中位数为：

- `--version`：45.08 MiB；
- provider-free initialize 后 EOF：50.47 MiB；
- 旧本地派生候选 idle 历史样本：约 126.34 MiB，并额外启动 IDE MCP child。

按 initialize 与旧 idle 的同机观察值比较，最大 RSS 下降约 60%，同时消除了 IM 不使用的 IDE MCP 子进程。该结果来自模块边界收敛和独立 clean-room 实现，不是通过 page cache、swap、cgroup 或 OOM 参数调优得到。

## 2. 本文边界

本文只回答：当前 CLI 改造后占用多少内存、为什么下降、怎样复测。

本文不处理：

- 阿里云/ECS/容器资源配额；
- page cache、磁盘 I/O、swap、cgroup 或 OOM；
- Dream 业务并发策略；
- 数据库或 Schema；
- Provider 长会话的容量规划。

## 3. 测量对象

| 对象 | 身份 |
| --- | --- |
| Runtime package | `@glide-the/ink-claude-code-dream@0.1.0` |
| CLI 兼容输出 | `2.1.241 (Claude Code)` |
| 测量用 darwin-arm64 qualification tgz | SHA-256 `8e0cdc0350b0fc3223e4e1957d182ac0b933b378afd01957c7ce3169ebbc2a73`；公共 registry 压缩包 SHA-256 为 `85906499553664f7af82cd004fcf29041041c9f56c76d675f33a1b8607c7ea63` |
| native executable | SHA-256 `04372c5b48d0e49cb2a908401dfb7bd0b8b7cb18e030f2ca4bfeb9949d0d22be` |
| source tree | 47 个文件、250,859 字节；SHA-256 `2e5f2059db618ae499fee12346d53f13bf0f1460ed600bae602c75b1c60a66ec` |
| compiler | Bun `1.4.0` standalone target |
| host | macOS `15.7.4`、Darwin `24.6.0`、Apple arm64 |

测量直接执行平台 standalone，不包含 selector Node 进程。selector 只完成平台解析并替换为 native executable，长期会话内存由 standalone、Provider/MCP 子进程和工具输出决定。

## 4. 测量结果

每个场景连续执行五次 `/usr/bin/time -l`，读取 `maximum resident set size`。

| 场景 | 样本数 | 最大 RSS 中位数 | 范围 | 场景含义 |
| --- | ---: | ---: | ---: | --- |
| `--version` | 5 | 47,267,840 B（45.08 MiB） | 47,218,688–47,513,600 B | Bun standalone 冷启动、argv 和版本输出 |
| provider-free initialize 后 EOF | 5 | 52,920,320 B（50.47 MiB） | 52,690,944–53,051,392 B | 精确 cwd/tmpdir/config，输出 control success 与 system init |
| 旧本地派生候选 idle | 历史样本 | 129,376 KiB（约 126.34 MiB） | 单组历史观察 | 带额外 IDE MCP child，只作同机旧候选对比 |

下降比例按中位/历史观察值计算：

```text
(129,376 KiB - 52,920,320 B / 1024) / 129,376 KiB ≈ 60%
```

由于旧候选样本不是同一套五次统计，本文只写“约 60%”，不报告为精确基准测试结论。

## 5. 内存下降来自哪里

clean-room Runtime 只实现 Dream 当前接口所需的模块：

- JSONL streaming 与双向 control；
- Provider streaming 与 tool loop；
- permission、PreToolUse、hook 和 cancel；
- session、JSONL transcript 与 resume；
- Workspace、thread-local TMPDIR、sandbox；
- MCP stdio、HTTP、Resources、OAuth 和 management identity；
- plugin、Skill、hook 与普通 Agent/Task 工具；
- Gateway `apiKeyHelper` 与安全错误 DTO。

以下 IM 未使用产品面没有进入 clean-room 源和 bundle：

- Remote Session/Remote Control/CCR；
- swarm/team/teammate；
- IDE integrations、terminal UI、Ink REPL；
- voice、SSH remote、browser product tool；
- updater、feedback/reporting；
- 交互历史选择器和增强 telemetry；
- 无关产品 services registry。

因此启动时不需要加载这些模块，也不会为了 IDE 能力派生额外 MCP child。这里的“删除”是从生产实现图中不存在，不是对非公开/恢复 bundle 做二进制删文件。

## 6. 与 Dream 业务能力的关系

内存优化不能牺牲以下 IM 合同：

| 合同 | 当前证据 |
| --- | --- |
| 新会话、首 Token、SSE | Runtime protocol tests；真实 Chat |
| 连续两轮与 resume | session tests；真实页面刷新后同一 Thread |
| tool use/result 与确认 | permission 8/8；真实两次 `get_server_info` |
| Workspace/TMPDIR/sandbox | workspace/session/sandbox tests；`.claude-tmp` `0700` |
| MCP HTTP/OAuth/Resources | OAuth 6/6、management 9/9；真实 Comfy Chrome OAuth |
| plugin/Skill/hook | session extensions 与 integration tests |
| Gateway authentication | `apiKeyHelper` focused tests；真实 Gateway 请求 |
| cancel/timeout/异常退出 | protocol、sandbox、late-write regression |

最终真实业务验收使用 `dmeck123@suoxya.com`、本机 Dream/Admin/Gateway/真实 PostgreSQL 与 `https://cloud.comfy.org/mcp`，完成两轮只读工具调用、刷新 resume、Logout/Remove，Playwright `1 passed (2.3m)`。

## 7. 不能从当前数字推导什么

50.47 MiB 不是完整业务会话上限。以下内容会增加进程或内存：

- Provider SDK streaming buffer 和较长上下文；
- MCP stdio server 子进程；
- HTTP MCP inventory 与大 tool result；
- Bash、rg 和 sandbox helper；
- 长 transcript、plugin/Skill 物化；
- 大文件读取和大 Workspace 输出。

当前数字也不能外推到 darwin-x64、linux-arm64 或 linux-x64。四平台已完成 native format、checksum 和可复现构建，但目标宿主 RSS 与 Linux `bubblewrap` 需要在对应平台独立测量。

## 8. 标准复测方法

发布候选必须先验证可执行文件哈希，再在空白临时 workspace 中测量。

```bash
shasum -a 256 /absolute/path/to/ink-claude-code-dream
/usr/bin/time -l /absolute/path/to/ink-claude-code-dream --version
```

initialize 场景必须提供：

- 规范化绝对 cwd；
- cwd 内真实 `.claude-tmp`，权限 `0700`；
- 独立 config home；
- provider-free 输入；
- EOF 后等待进程正常退出。

每个场景至少五次，报告中位数和范围，不只挑最低值。对比版本必须记录 package/tgz/executable/source SHA，避免不同产物混在一张表中。

## 9. 后续基准矩阵

| 场景 | 当前状态 | 后续要求 |
| --- | --- | --- |
| `--version` | 5 次通过 | 每次 release 复测 |
| initialize/EOF | 5 次通过 | 每次 release 复测 |
| 单轮真实 Provider | 业务通过，未单独采 RSS | 记录 Runtime 与 Gateway client 峰值 |
| 两轮 resume | 业务通过，未单独采 RSS | 记录 transcript 增量后的峰值 |
| HTTP MCP OAuth/tool | 业务通过，未单独采 RSS | 分离 Runtime 与远端 HTTP client |
| stdio MCP | 协议通过 | 分离 Runtime 与 MCP child RSS/PSS |
| 大 tool result | 未建立性能基线 | 使用隔离 fixture，不写真实业务数据 |
| Linux sandbox | 构建/格式通过 | 在真实 glibc + bubblewrap host 测量 |

## 10. 回滚

若新 Runtime 在目标宿主出现协议或内存回归：

1. 保留当前内容寻址 release，不原地覆盖；
2. 将绝对 `CLAUDE_CODE_CLI_PATH` 指向预检过的 official CLI；
3. 保留同一 SDK、Thread、Workspace 和 transcript 合同；
4. 记录失败 executable/package/source SHA 与测量命令；
5. 只在 Runtime 仓库修复并重跑协议、MCP、业务和内存矩阵。

回滚不允许通过修改 Dream 业务状态机、关闭 resume 或绕过 sandbox 来换取更低内存。
