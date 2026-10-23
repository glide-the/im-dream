<!--
[Input] 本机 Natapp CLI 服务帮助、LaunchDaemon 配置、launchctl 状态与日志。
[Output] 已有双隧道服务的启动、重启、停止、状态查询与日志操作说明。
[Pos] macOS 本机 Natapp 服务维护手册；边缘 nginx 操作见 natapp-edge-relay.md。
[Sync] 2026-10-18: 整理已有两个服务，记录进程状态与隧道认证结果及恢复命令。
[Sync] 2026-10-18: 按用户范围删除新实例安装步骤，补充已有服务的启动、停止与恢复加载。
[Sync] 2026-10-18: 管理命令直接使用已核对的本机服务名称，删除变量准备和手动输入步骤。
[Sync] 2026-10-18: 启动入口使用 bootstrap 恢复 bootout 卸载的服务；重启入口使用 kickstart -k。
[Sync] 2026-10-18: 补充运行日志、云端访问日志与本地请求详情入口；Admin 监控保存为 4041，本机日志参数待管理员应用。
-->

# macOS Natapp 双隧道服务

## 运行结构与配置来源

macOS 系统域的 `launchd` 管理两个 Natapp 实例。每个实例使用独立的服务名称和隧道令牌，服务文件位于 `/Library/LaunchDaemons/`，开机加载后由 `KeepAlive=true` 持续维持进程。

本机检查确认客户端为 `/opt/natapp/natapp`。以下命令用于管理本机已存在的两个服务。Natapp 控制台保存隧道的协议、目标地址、目标端口和公网入口。

| 对象 | 本机配置与来源 |
| --- | --- |
| 第一条已有服务 | `natapp_200c05cea2838689` |
| 第二条已有服务 | `natapp_365f97d9b2e381d2` |
| 服务定义 | `/Library/LaunchDaemons/` 中对应服务名称的 `.plist` 文件 |
| 启动参数 | plist 中的 `ProgramArguments` |
| 标准输出 | plist 中的 `StandardOutPath`，查看命令见“检查服务和隧道” |
| 标准错误 | plist 中的 `StandardErrorPath`，查看命令见“检查服务和隧道” |

命令直接使用上述两个服务的现有名称。2026-10-18 控制台核对：`natapp_200c05cea2838689` 对应 Admin，目标为 `127.0.0.1:3000`；`natapp_365f97d9b2e381d2` 对应 Dream，目标为 `127.0.0.1:5173`。

本机 plist 的 `Disabled=false`、`KeepAlive=true`、`RunAtLoad=false`。本机 `man launchd.plist` 说明 `KeepAlive` 隐含加载时启动；系统域服务随开机加载，运行期间由 launchd 管理进程恢复。

公网边缘主机的 nginx 配置和回滚操作见 [Natapp 边缘转发](natapp-edge-relay.md)。本手册负责本机隧道进程维护。

## 启动服务（停止后恢复）

```bash
sudo launchctl bootstrap system /Library/LaunchDaemons/natapp_200c05cea2838689.plist
sudo launchctl bootstrap system /Library/LaunchDaemons/natapp_365f97d9b2e381d2.plist
```

`bootstrap` 从已有 plist 将服务加载到系统域，`KeepAlive=true` 随即启动进程。执行 `bootout` 停止后，通过这两条命令恢复启动。管理员命令由 `sudo` 在终端请求系统密码。

服务已经加载时，使用下一节的重启命令。`kickstart` 及 `kickstart -k` 均要求服务已经加载；提示 `Could not find service` 时，执行本节对应的 `bootstrap` 命令。

## 重启服务

```bash
sudo launchctl kickstart -k system/natapp_200c05cea2838689
sudo launchctl kickstart -k system/natapp_365f97d9b2e381d2
```

`kickstart -k` 对已加载的服务终止当前进程并立即重新启动，正在经过该隧道的连接会中断。通常执行一次，再检查认证结果。

## 停止服务

```bash
sudo launchctl bootout system/natapp_200c05cea2838689
sudo launchctl bootout system/natapp_365f97d9b2e381d2
```

`bootout` 停止指定进程并从当前系统域卸载服务。plist 保留在原路径，下次开机仍按已有配置加载。停止后再次启动，执行“启动服务（停止后恢复）”中的 `bootstrap` 命令。`KeepAlive=true` 会拉起直接终止的进程，手动停止使用上述命令。

## 加载失败排查

`bootstrap` 加载失败时，检查两个已有文件的语法：

```bash
sudo plutil -lint /Library/LaunchDaemons/natapp_200c05cea2838689.plist
sudo plutil -lint /Library/LaunchDaemons/natapp_365f97d9b2e381d2.plist
```

遇到 `Load failed: 5` 时，执行下一节的 `launchctl print`，确认服务是否已经加载。输出服务信息时可直接使用重启命令；找不到服务且 plist 校验成功时，保留 `bootstrap` 的错误输出继续排查。

## 检查服务和隧道

```bash
sudo /opt/natapp/natapp -service list
sudo launchctl print system/natapp_200c05cea2838689
sudo launchctl print system/natapp_365f97d9b2e381d2
sudo /opt/natapp/natapp -service status -servicename=natapp_200c05cea2838689
sudo /opt/natapp/natapp -service status -servicename=natapp_365f97d9b2e381d2
```

`state = running` 与进程 ID 说明本机进程已启动。隧道在线需要 Natapp 认证成功、控制台在线，以及配置的公网入口能返回对应本机应用内容。

读取近期日志：

```bash
sudo tail -n 50 /var/log/natapp_200c05cea2838689.out.log /var/log/natapp_200c05cea2838689.err.log
sudo tail -n 50 /var/log/natapp_365f97d9b2e381d2.out.log /var/log/natapp_365f97d9b2e381d2.err.log
```

日志路径变更时，从对应 plist 读取当前 `StandardOutPath` 和 `StandardErrorPath`。

## 运行日志与请求详情

| 入口 | 内容 | 当前配置 |
| --- | --- | --- |
| 两个 `.out.log` 文件 | 客户端运行、认证、连接和错误输出 | 开启运行日志的参数为 `-log=stdout -loglevel=INFO`；系统服务参数待管理员应用 |
| [Dream 本地监控](http://127.0.0.1:4040) | Dream HTTP 请求详情 | 控制台已开启，端口为 4040；本机监听待服务重载后核对 |
| [Admin 本地监控](http://127.0.0.1:4041) | Admin HTTP 请求详情 | 已在控制台保存开启，端口为 4041；本机监听待服务重载后核对 |
| [Natapp 我的隧道](https://natapp.cn/tunnel/lists) → 日志 | 请求路径、方法、状态码、来源 IP 与统计 | 两条隧道列表均提供日志入口 |

客户端日志参数写入各自 plist 的 `ProgramArguments`，由 `StandardOutPath` 接收标准输出。Natapp CLI 的 `-log` 默认为 `none`；本机核对时两个服务均未设置该参数。

本地请求详情由 Natapp 控制台的“本地流量监控控制台”配置。两个实例使用独立端口，保存后重载对应客户端。该页面提供请求头、请求数据和响应详情，记录数量与截断行为见 [官方监控说明](https://natapp.cn/article/webinterface)。云端查询入口见 [官方访问日志说明](https://natapp.cn/article/access_log)。

持续查看两个运行日志文件：

```bash
sudo tail -F /var/log/natapp_200c05cea2838689.out.log /var/log/natapp_365f97d9b2e381d2.out.log
```

`tail -F` 持续跟随文件，按 `Ctrl+C` 结束查看。

| 检查结果 | 处理方式 |
| --- | --- |
| 找不到系统域服务 | 核对 Label、plist 路径与语法，通过 `bootstrap` 加载 |
| `running`，日志停在连接认证服务器 | 核查认证域名解析、出站网络与后续认证结果 |
| `errorCode :1104`，提示隧道已过期 | 到 Natapp 控制台确认隧道有效期并续费；认证资格恢复后检查在线状态，必要时手动触发 |
| 认证成功，公网入口连接本机失败 | 核对控制台目标地址、端口和对应应用监听状态 |
| Natapp 入口正常，边缘域名异常 | 按边缘转发手册检查显式 origin、nginx 和公开路由 |

## 2026-10-18 本机核对记录

- 两个 plist 均存在，上述两条 `launchctl print` 分别返回 `state = running`，进程 ID 为 `553` 与 `554`。
- 两份标准输出日志末尾均出现 `errorCode :1104 Msg:隧道已过期,请及时续费,资源将在7天后释放`。日志文件修改时间分别为当天 `22:47:25 +0800` 与 `22:03:31 +0800`；日志行自身没有时间戳，错误日期依据文件修改时间记录。
- 该次核对覆盖本机配置、进程状态与已有日志；隧道在线、当前有效期和公网业务可用性待控制台与入口检查。
- 本轮只整理文档和读取本机状态。此前记录中的进程运行与 TCP 连接证据，仅支持对应进程和传输状态。
- 用户后续执行两条 `bootout` 后，两条服务均从系统域卸载；随后 `kickstart` 返回 `Could not find service`，退出码为 `113`。恢复操作使用本手册“启动服务（停止后恢复）”的 `bootstrap` 命令，恢复结果待实际执行核对。
- 日志配置后续核对：控制台两条隧道有效期均为 2026-11-18；Dream 监控已开启为 4040，Admin 监控从关闭改为开启并保存为 4041。准备的本机管理脚本会备份两个原 plist、追加运行日志参数并逐个重新加载；管理员执行和后续进程、日志及本机监控页面验证待完成。前述过期信息保留为历史日志观察。
