<!-- [Input] 2026-11-02 Mac SSH 进程参数、旧 relay plist、Admin 临时桥接记录及 OpenSSH 手册。 -->
<!-- [Output] Mac 临时代理反向转发的链路、命令、验证、故障定位与单连接停止步骤。 -->
<!-- [Pos] 临时诊断操作说明；记录个人 Mac 出口依赖，服务器独立出口按 Admin 部署流程维护。 -->
<!-- [Sync] 2026-11-02: 独立说明 17891 → 17890 → Mac 7890 的临时转发，区分隧道进程、出口连通和登录验收。 -->

# Mac 临时 SSH 代理转发说明

“Mac 临时转发”由 Mac 主动建立一条到 ECS 的 SSH 连接，将 ECS 的 `127.0.0.1:17890` 反向转发到 Mac 的 `127.0.0.1:7890`。ECS 上已有的 Tinyproxy 通过该端口使用 Mac 的 HTTP 代理出口。

本说明提供命令和操作条件。本次文档整理只执行本机只读检查，服务启动、转发重建、远程探测和停止命令均留给实际操作时执行。

## 链路与端口

```text
iPhone Google 授权页面 → Google → 公网 Admin 回调
                                      │ 服务端兑换授权码
                                      ▼
ECS Admin → ECS Tinyproxy → ECS SSH 反向转发端口
            127.0.0.1:17891   127.0.0.1:17890
                                      │ SSH 加密连接
                                      ▼
                              Mac HTTP 代理
                              127.0.0.1:7890
                                      │ 代理选定的出口
                                      ▼
                              oauth2.googleapis.com:443
```

| 对象 | 职责与条件 |
| --- | --- |
| iPhone | 浏览器执行 Google 授权；手机上的 VPN 作用范围由手机网络配置决定 |
| ECS Admin | 处理 Google 回调并从服务器向 Google 兑换授权码；该请求使用服务器出口 |
| ECS `17891` | 已有 Tinyproxy HTTP 代理入口；Admin 的既有代理配置指向此处 |
| ECS `17890` | SSH 在服务器建立的监听端口，连接通过 SSH 送到 Mac |
| Mac `7890` | 已有本机 HTTP 或 mixed-port 代理；具体节点和规则由代理软件管理 |

Tinyproxy 现有规则将指定 Google 域名送往上游 `127.0.0.1:17890`；其他域名按既有规则处理。SSH 负责转发 TCP 字节，HTTP CONNECT 和实际出网由代理处理。Google HTTPS 请求在应用与 Google 之间继续使用 TLS。

该方式使用 SSH TCP 端口转发；宿主机 TUN、NAT 路由、默认网关和 iPhone 路由维持原配置。Admin、数据库和业务仍在原位置运行。

## 当时使用的命令

以下命令在 **Mac 终端**执行，沿用当次已配置的 SSH 身份认证：

```bash
ssh -M -S /tmp/ink-google-egress-20261102/control.sock -fNT \
  -o BatchMode=yes \
  -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=15 \
  -o ServerAliveCountMax=3 \
  -R 127.0.0.1:17890:127.0.0.1:7890 \
  root@39.97.252.88
```

关键参数：

```text
-R 127.0.0.1:17890:127.0.0.1:7890
   └──── ECS 监听 ────┘ └──── Mac 目标 ────┘
```

`-R` 左侧地址属于 SSH 服务器，右侧目标由 SSH 客户端连接。两个 `127.0.0.1` 分别属于 ECS 和 Mac。监听地址还受 ECS `sshd` 转发策略约束，建立后须核对实际绑定地址。

| 参数 | 用途 |
| --- | --- |
| `-M -S <socket>` | 为本条连接建立独立控制套接字，便于精确查询和停止 |
| `-fNT` | 后台运行，仅转发端口，关闭远程命令和终端分配 |
| `BatchMode=yes` | SSH 认证缺失时返回失败，避免交互式密码等待 |
| `ExitOnForwardFailure=yes` | 监听建立失败时退出；目标代理和 Google 的可达性需另行验证 |
| `ServerAliveInterval=15`、`ServerAliveCountMax=3` | SSH 存活检测；连接失效后退出，重连由操作者执行 |

旧 `com.ink-memory.admin-ecs-relay` plist 同时包含 `-L 127.0.0.1:3000:127.0.0.1:3000` 和上述 `-R`。本次临时命令仅建立 `-R`，Mac 的本地 Admin 3000 端口维持原监听。旧 launch agent 的启停沿原维护流程处理。

## 按需复现

### 1. 确认前提

- Mac 代理已启动，目标端口支持 HTTP CONNECT；Mac 能通过此代理访问 Google。
- Mac 已具备到目标 ECS 的 SSH 认证及已核验的主机密钥。
- ECS 允许所需 remote forwarding，目标端口空闲。
- Admin 继续使用现有 Tinyproxy，Google 的上游仍指向待转发端口。若上游已切到服务器独立代理，应沿新出口流程操作。

在 Mac 核对监听及代理出口：

```bash
lsof -nP -iTCP:7890 -sTCP:LISTEN

curl --noproxy '' --proxy http://127.0.0.1:7890 \
  --connect-timeout 10 --max-time 20 \
  --silent --show-error --output /dev/null \
  --write-out 'connect=%{http_connect} http=%{http_code}\n' \
  https://oauth2.googleapis.com/token
```

上述探测执行匿名 GET，携带的 Google 授权码、Cookie、Client Secret 和用户 Token 均为零。根据 HTTP 响应判断网络阶段，登录验收单独执行。

### 2. 建立转发

以下变量值为当次操作示例，可按目标覆盖；全部命令在同一个 Mac shell 中执行。SSH 用户沿已有授权配置选择。

```bash
ECS_SSH_TARGET='root@39.97.252.88'
MAC_PROXY_PORT='7890'
ECS_REVERSE_PORT='17890'
RELAY_DIR='/tmp/ink-google-egress-20261102'
RELAY_SOCKET="${RELAY_DIR}/control.sock"

# 首次创建本轮专用目录。目录已存在时先核对所有者和所属连接。
test -d "$RELAY_DIR" || (umask 077; mkdir "$RELAY_DIR")

ssh -S "$RELAY_SOCKET" -O check "$ECS_SSH_TARGET"
```

控制命令成功表示该套接字已有连接；继续验证其转发参数和出口。套接字不存在且 ECS 目标端口空闲时执行创建；套接字存在且控制命令失败时先确认所属进程，保留其他连接。

```bash
ssh -M -S "$RELAY_SOCKET" -fNT \
  -o BatchMode=yes \
  -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=15 \
  -o ServerAliveCountMax=3 \
  -R "127.0.0.1:${ECS_REVERSE_PORT}:127.0.0.1:${MAC_PROXY_PORT}" \
  "$ECS_SSH_TARGET"
```

### 3. 按阶段验证

| 阶段 | 命令或操作 | 通过条件 |
| --- | --- | --- |
| Mac 目标代理 | 前述 `lsof` 和 Mac 代理 GET | 目标端口监听，代理 CONNECT 与 Google HTTP 响应可读 |
| SSH 主连接 | `ssh -S "$RELAY_SOCKET" -O check "$ECS_SSH_TARGET"` | 命令退出 0；该结果仅确认 SSH 主进程可响应控制命令 |
| ECS 监听 | 下方 `ss` 命令 | 核对 `17890`、`17891` 监听进程和绑定地址，访问范围限定 loopback |
| SSH 上游链路 | ECS 经 `17890` 匿名 GET | CONNECT 成功，Google HTTP 响应可读 |
| Tinyproxy 完整出口 | ECS 经 `17891` 匿名 GET | 同一目标可达，原域名上游规则生效 |
| Google 真实登录 | iPhone 原 Google 登录入口 | 授权完成、原登录窗口关闭、App 进入主页并取得有效会话 |

只读监听检查和匿名网络探测：

```bash
ssh -o BatchMode=yes "$ECS_SSH_TARGET" \
  "ss -ltnp '( sport = :17890 or sport = :17891 )'"

ssh -o BatchMode=yes "$ECS_SSH_TARGET" \
  "curl --noproxy '' --proxy http://127.0.0.1:${ECS_REVERSE_PORT} \
    --connect-timeout 10 --max-time 20 \
    --silent --show-error --output /dev/null \
    --write-out 'connect=%{http_connect} http=%{http_code}\\n' \
    https://oauth2.googleapis.com/token"

ssh -o BatchMode=yes "$ECS_SSH_TARGET" \
  "curl --noproxy '' --proxy http://127.0.0.1:17891 \
    --connect-timeout 10 --max-time 20 \
    --silent --show-error --output /dev/null \
    --write-out 'connect=%{http_connect} http=%{http_code}\\n' \
    https://oauth2.googleapis.com/token"
```

`--noproxy ''` 使本次探测明确使用指定代理；探测进程之外的配置维持原值。`connect=200` 表示 HTTP CONNECT 隧道建立；匿名 GET 的 `http=404` 等 Google HTTP 响应仅用于连通性判断。Google 授权码兑换、最终 App 会话和真实业务分别验收。

## 故障判断

| 观察结果 | 检查位置与处理 |
| --- | --- |
| Mac `7890` 无监听 | 检查本机代理软件状态和实际 HTTP/mixed-port；目标具备监听后再验证隧道 |
| `remote port forwarding failed` | 检查 ECS 端口占用与 sshd 转发策略，确认已有连接归属 |
| SSH 检查成功，代理请求失败 | 检查 Mac 目标代理、节点及 Google 出口；SSH 存活与业务连通分别判断 |
| ECS `17890` 成功、`17891` 失败 | 检查 Tinyproxy 监听、域名上游及运行日志；保留 Admin 进程 |
| 两个出口均成功，Google 登录失败 | 按授权回调日志定位授权码兑换、回调跳转及会话；保留原 Client ID、PKCE、权限和网页流程 |
| Mac 睡眠、断网或代理关闭 | 临时出口失效；恢复目标代理和连接后重新探测，再重新发起正常登录 |

隧道重建完成后，通过 App 原入口重新发起 Google 登录。已使用或过期的授权码沿原认证规则处理。

## 停止与替换

停止前确认 Tinyproxy 当前上游及依赖方。若 Google 出口仍依赖本条隧道，停止会使相关服务器请求失败。服务器独立代理完成配置与连通验证后，再移除此依赖。

以下命令只终止指定控制套接字对应的 SSH 主连接：

```bash
ssh -S "$RELAY_SOCKET" -O exit "$ECS_SSH_TARGET"
```

清理仅涉及本轮目录中已确认失效的套接字与空目录。避免按 `ssh` 进程名批量终止连接；其他隧道、本地 Admin、远程 Admin、数据库和 launch agent 按各自维护流程处理。

## 本次核对范围与资料

- 2026-11-02 本机只读核对：找到使用上述完整参数的 SSH 进程和对应控制套接字；PID 为短期观测值，运维定位使用控制套接字。
- 同轮 `lsof -nP -iTCP:7890 -sTCP:LISTEN` 退出 1、输出为空；该观测未发现 Mac `7890` 监听，需在实际操作时再次确认代理状态。
- 本轮未执行 ECS 探测、Google 登录、重建或停止隧道；服务器当前上游及后续独立出口进度由主任务回执维护。
- 本地参数来源：`/Users/dmeck/Library/LaunchAgents/com.ink-memory.admin-ecs-relay.plist`，仅核对转发与存活参数。
- Admin 配置依据：[临时桥接历史记录](../../../ink-admin-memory/docs/verification/ecs-admin-temporary-bridges-20261029.md)、[Admin 服务部署说明](../../../ink-admin-memory/docs/deploy-services.md)。这两个链接需要同级 `ink-admin-memory` checkout；运行配置按实际主机核对。
- 官方命令语义：[OpenSSH ssh(1)](https://man.openbsd.org/ssh)，查阅日期 2026-11-02。

本机参数核对支持链路说明；当前网络连通、完整 Google 登录和服务器独立出口保留各自验收状态。
