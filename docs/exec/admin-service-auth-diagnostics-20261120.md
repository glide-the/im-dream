<!-- [Input] 用户提供的服务令牌503堆栈、当前调试进程、Admin源站与公开生产客户端回执。 -->
<!-- [Output] 故障边界、脱敏HTTP状态诊断、后台等待语义及隔离回归记录。 -->
<!-- [Pos] 认证异常执行记录；Admin数据合同及Agent执行规则继续由原模块所有。 -->

# Admin服务令牌异常与资源快照诊断

## 问题与边界

2026-11-20用户在本机测试时提供`ADMIN_SERVICE_AUTH_UNAVAILABLE (503)`堆栈，以及`Claude Agent resource snapshot write failed: code=write_timeout`日志。堆栈定位到`service_token.py`收到非2xx HTTP响应后的拒绝分支，业务capabilities请求尚未派发。原异常仅保留统一503，触发时的上游状态和时间缺失，历史拒绝原因尚未确认。

当前源码HEAD为`41943f30`，Web Bearer迁移已合并。本机8765由用户IDE调试进程PID71112运行，启动时间为2026-11-20 15:01（Asia/Shanghai）。该进程与前次发布验收使用的Python进程不同。前次Web登录、历史、续期及退出验收回执继续保留，本次单独核对后台服务认证和资源发布。

## 当前证据

| 检查 | 结果 |
| --- | --- |
| 进程有效配置 | Admin public/transport均为线上Admin；issuer与resource匹配既有合同 |
| 服务凭据比较 | Python、frontend online配置与已发布Web快照的service ID/secret相同；凭据值排除输出 |
| 公开令牌与capabilities探测 | HTTP200 / HTTP200 |
| 实际生产客户端 | `AdminDataClient.capabilities_snapshot`成功；令牌200、capabilities200，301项operation |
| 上述生产客户端耗时 | 冷令牌加capabilities合计5.191秒；响应由既有Cloudflare入口返回 |
| Admin服务 | `active`，`NRestarts=0`，现用制品`actions-44364200393-871fa480450c/app` |
| 源站最近35分钟令牌记录 | 23条200、1条400；400发生于15:00:47，User-Agent归Node，无法与Python堆栈建立对应 |
| 资源发布等待 | 原异步等待预算1秒；超时后保留同一driver调用并等待其结束，后续写入保持单worker顺序 |

当前生产入口返回200，原503未复现。源站记录无法覆盖边缘节点直接返回的响应；现有证据不足以将历史拒绝归因于凭据、限流或网络入口。资源发布等待超时仅进入旁路计数，Agent turn继续执行；写入最终结果需由该次driver回执确认。

## 源码变更

- [service_token.py](../../backend/services/admin_data/service_token.py)：HTTP拒绝继续返回`ADMIN_SERVICE_AUTH_UNAVAILABLE (503)`，异常附加`remote=admin.oauth.token http_status=<数字>`。响应正文、Header和凭据排除异常。HTTP拒绝仍单次派发，下一次独立调用可恢复并进入原短期缓存。
- [resource_postgres_sink.py](../../backend/claude_agent/resource_postgres_sink.py)：异步等待超时日志采用`write wait timed out: code=write_timeout outcome=pending`。原1秒预算、队列、单worker、未完成调用、计数和收尾规则保持。
- 对应测试覆盖400/401/403/429/503的单次拒绝及脱敏、后续调用恢复、超时后的单调用顺序和最终完成；目录合同同步更新。

2026-11-20现场的用户IDE调试进程保持运行，新诊断在后续正常启动加载。该阶段未重启本机或Admin服务，未更改运行配置、数据库或模型调用。

## 验证

Provider-free回归由Luna test-stage执行，真实凭据操作由主Agent执行；隔离回归只使用MockTransport和注入writer。

| 命令 | 目录 | 退出码 | 回执 |
| --- | --- | --- | --- |
| `PYTHONPATH="$PWD:$PWD/.venv/lib/python3.12/site-packages" uv run --no-project --python .venv/bin/python --with pytest==8.4.2 python -m pytest tests/test_admin_service_token.py tests/test_claude_agent_resource_postgres_sink.py tests/test_admin_data_boundary.py -q` | backend | 0 | 117 passed in 1.56s |
| `git diff --check` | 仓库根目录 | 0 | 无空白错误 |

pytest复用原site-packages与临时uv环境；`.venv`、manifest和lock保持。测试未新增数据库、端口、进程或待清理生成物。

## 2026-11-26集成复核

默认分支develop的`39fb4b8a`独立工作树重新运行同一pytest命令，退出码0，117项通过。临时uv pytest环境只读复用原site-packages，原工作区、运行配置及服务保持。该回执属于Provider-free技术验证。
