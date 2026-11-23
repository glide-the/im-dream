<!-- [Input] 用户授权的源站 HTTPS、FlClash 固定解析、iOS 打包配置和消息读取复测。 -->
<!-- [Output] 源站、证书续期、配置采用和同会话消息读取的执行回执。 -->
<!-- [Pos] 本轮网络入口与 Chat 读取性能执行记录。 -->
<!-- [Sync] 2026-11-24: 完成 HTTPS、续期和正常账户复测；登记首次认证等待与设备验证缺口。 -->
<!-- [Sync] 2026-11-24: 追加构建 49 的 iPhone 安装与启动检查回执链接。 -->
# Admin 源站 HTTPS 与消息读取复测

## 范围与判断

用户要求本机和 iOS 连接 `39.97.252.88`，并在 Access Token 会话完成后复测既有消息读取。当前源站原配置仅监听 HTTP 80。已取得同时覆盖 `ink-admin.suoxya.com` 与该 IP 的公开证书，在原 nginx server 增加 HTTPS 443。证书采用 Let’s Encrypt shortlived profile，有效期约六天；现有 systemd 负责每日两次续期检查，成功续期后先校验再 reload nginx。

本机 FlClash 使用精确域名 DIRECT 规则及 hosts 固定解析。iOS 复用 `INK_ADMIN_DREAM_TRANSPORT_BASE_URL=https://39.97.252.88`，由系统 URLSession 校验证书中的 IP SAN。公开认证 issuer 为 `https://ink-admin.suoxya.com/api/auth`。现有打包脚本继续从 `backend/.env`、`frontend/.env.local` 复制配置，两项输入已经采用相同直连目标。`.env.mobile`、`.env.online` 同步该目标。普通 Backend 的 Gateway 与 Product API 原配置指向本机服务，复测前已同步为同一 HTTPS IP；现有 service key 与 JWT 配置保持原值。

IP 证书的 webroot 签发与 deploy hook 续期采用 [Let’s Encrypt 的 Certbot 指南](https://letsencrypt.org/2026/03/11/shorter-certs-certbot)。

## 业务验证范围

| 对象 | 事实来源与读取入口 | 本轮操作 |
| --- | --- | --- |
| 既有 Chat Thread 与消息 | 正常账户、正常 PostgreSQL、原消息 API 与 Chat 页面 | 读取同一 Thread 历史，记录请求耗时和调用次数 |
| Project、Episode、正式作品与 Run 私有产物 | 原业务文件与投影 | 本轮场景为 Chat 历史读取，这些对象处于范围外 |
| Agent Run、工具、after-turn Hook、Gateway 结算 | 原运行与结算入口 | 本轮场景仅读取历史，不触发执行入口 |
| 用户与权限 | 原 OAuth、Bearer、scope 和资源归属 | 通过已有正常会话读取 |

## 已取得的基础证据

- 源站域名 HTTPS 强制解析、IP HTTPS 均返回预期未认证 401，curl 证书校验值为 0，样本约 0.11 秒。
- FlClash 重载后，域名实际解析为 `39.97.252.88`，请求列表显示 DIRECT；样本约 0.12 秒。
- Certbot 5.10.0 生产证书覆盖 DNS 与 IP SAN；到期时间为 2026-11-30 14:36:20（Asia/Shanghai）。续期 dry-run 与 deploy hook 退出 0。
- `ink-admin-certificate-renew.timer` active。配置启用时 Admin 为 active、MainPID 722566。最终核对为 active、MainPID 2933948。
- 生产 AdminDataClient 通过同一 IP 完成三次正常服务认证与 capabilities 读取，约 838、347、511 毫秒，均校验到原 canonical issuer，目录含 301 项 operation。该项为真实上游配置验证。
- 续期 systemd service 实际执行结果为 `Result=success`、`ExecMainStatus=0`。
- 两项实际 iOS 打包 env 输入通过现有 `validate_mobile_environment`，transport 均为 HTTPS IP；设备与已安装包验证另行记录。
- Access Token 会话 `01a1f420-3afc-7d20-a9bf-3b35a8e241ef` 最新 turn completed，关闭重开恢复的处理已完成。

## 消息复测

2026-11-24 完成正常账户复测。先确认 Access Token 会话最新 turn completed，再从正常 OAuth 入口恢复既有账户。首次 Chrome 操作被其他操作反复切换，后续按用户指定改用 Boss 插件，选取用户原 Thread 的历史入口并读取消息。测试入口为本机正常开发服务 5173 与 8765，Admin、Gateway 和 PostgreSQL 使用正常 ECS 服务。

| 测量 | 首次打开 | 再次打开 |
| --- | --- | --- |
| 完整消息页，`limit=20` | 6242.8 ms | 1062.7 ms |
| 最新消息标识增量核对 | 369.1 ms | 397.8 ms |
| messages 读取次数 | 2 | 2 |
| 消息执行过程读取次数 | 2 | 2 |

请求数来自浏览器 Resource Timing。打开至采样结束的其他请求包含状态、计划、工具记录、输入等；输入接口存在后续轮询，当前记录保留原请求列表。Boss 插件原始 Network 事件观察器未完整记录请求，原始事件流的计数未用于验收。

首次慢请求 Trace 为 `85f7628cc8fd74409cff3993f49a9e32`。ARMS 完整列表显示 Next 6.15 秒、Python 6.14 秒、Python `dream.authentication` 5.38 秒；BFF `bff.authentication` 为 262 微秒。该 Trace 有三次 Python→Admin HTTP，分别为 `principal`、`chat-thread.get`、`chat-message.page`，耗时约 815、376、374 毫秒；`browser-sessions/resolve` 为零。Next 编译仅 21 毫秒。

最终 systemd 核对记录 Admin 在 2026-11-23 23:59:41 重启，`NRestarts=0`，工作目录仍为 `/srv/ink-admin-releases/actions-44364200393-871fa480450c/app`。本轮直接执行的服务操作为 nginx reload 和本机自有 Backend 换配置。首次消息请求从 23:59:44.797 开始，位于该次 Admin 重启后约四秒的冷启动窗口。两次读取的启动状态不同，当前样本分别登记原值。

Python 认证从 23:59:44.807 开始，第一笔 `principal` HTTP span 从 23:59:49.375 开始。约 4.57 秒位于认证前半段，现有 span 包含线程池调度、JWT 校验、catalog/token 共享锁与本地处理。当前证据明确该等待区间，具体排队或共享锁耗时仍待分段测量。首次消息延迟仍未完成优化。

原会话首批消息与再次打开均返回 200，页面消息展示成功。正常页面初始化产生原应用的 Session 保存请求；本轮未提交 Agent 对话或触发模型推理。原业务记录保留。证据为 `output/playwright/admin-origin-direct-20261123/measurements.json`，包含全部采样请求与 ARMS span 列表。

[ARMS 首次消息 Trace](https://cmsnext.console.aliyun.com/next/region/cn-beijing/workspace/default-cms-1230976711767463-cn-beijing/app/apm/trace-detail?regionId=cn-beijing&traceId=85f7628cc8fd74409cff3993f49a9e32&hidTopBar=true&mode=normal&querySource=&source=trace&startTime=1795448877583&endTime=1795449777583&from=1795448877583&to=1795449777583&hideSiderbar=true&hideTopbar=true&hiddenBack=true&readOnly=true&hideBreadcrumb=true&hideTopbarTabs=true)


## 运维与恢复位置

- nginx 配置为 `/etc/nginx/sites-available/ink-memory-admin`，原配置备份后缀分别为 `bak-20261123T153222Z`、`bak-20261123T153541Z`。
- 证书为 `/etc/letsencrypt/live/ink-admin-direct/`；独立 Certbot 环境为 `/opt/ink-admin-acme/`；HTTP-01 webroot 为 `/var/lib/ink-admin-acme/`。
- 续期单元为 `ink-admin-certificate-renew.service` 与 `.timer`，deploy hook 为 `/usr/local/sbin/ink-admin-acme-reload`。
- 本机配置私有备份位于 `~/Library/Application Support/InkMemoryNetwork/20261123T233657/`，仅保存于本机。

## iPhone 后续采用

2026-11-24 已将相同 HTTPS IP 传输配置打入构建 49 并覆盖安装到 iPhone 16，包内来源、签名和真机启动检查通过。实际页面为登录入口，正常账户的消息读取单独验收。详见 [iPhone 安装回执](iphone-direct-install-20261124.md)。上文消息耗时记录保留其本机 Web 样本范围。
