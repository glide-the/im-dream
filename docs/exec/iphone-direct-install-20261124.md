<!-- [Input] 当前 develop 工作树、HTTPS IP 传输配置、既有开发签名和已连接 iPhone 16。 -->
<!-- [Output] 构建 49 的来源、包内配置、签名、保数据覆盖安装与真机启动回执。 -->
<!-- [Pos] 源站直连配置的本次 iPhone 交付记录。 -->
<!-- [Sync] 2026-11-24: 构建 49 安装与真机启动通过；登录和消息业务单独列为待验收。 -->

# iPhone 源站直连安装：构建 49

## 交付范围

2026-11-24，按用户要求将 `https://39.97.252.88` 配置打包到现有 iPhone。源码为 `develop` 提交 `41943f300c53d343be6bc0273cd9af36ba3e1b76` 及构建开始时的当前工作树，包含已有认证和消息性能改动。工作区已有未提交修改保持；本轮业务源码修改和依赖安装次数为 0。

已在 iPhone 16、iOS 18.0.1 上将 Kastention `0.1.0 (48)` 覆盖升级为 `0.1.0 (49)`，Bundle ID 为 `com.inkmemory.mobile`。真机检查显示“本地服务已就绪”，返回后显示 Kastention 登录入口。当前验证覆盖包来源、安装、应用启动及上述页面；正常账户登录、历史消息读取和模型业务另行验收。本轮模型调用次数为 0。

## 配置与构建

- 包内 `INK_ADMIN_DREAM_TRANSPORT_BASE_URL` 为 `https://39.97.252.88`；Backend 的 Product API 和 Gateway 使用同一 HTTPS IP。公开 Admin 地址及认证 issuer 保留域名 `ink-admin.suoxya.com`，账户和 MCP 回调保持原 Bundle ID 归属。复用系统 HTTPS 校验。
- 原 `backend/.env`、`backend/.env.mobile`、`frontend/.env.local`、`frontend/.env.online` 四项输入摘要在本轮保持一致。包内采用移动和线上配置，再应用原生 origin 与回调设置。
- Mac 物理内存 16 GiB，预检时内存可用比例约 48%、磁盘可用约 29 GiB；macOS 的 cgroup 检查不适用。复用既有依赖、Pods 与原生缓存，Next、Metro、Xcode 串行执行并限制 worker/job 为 1，Node 每进程 old space 为 2048 MiB。
- Next 在本轮隔离目录重新构建并执行完整类型检查；实际应用包的来源回执和 manifest 经核对。484 项原生、后端及构建输入在构建期间保持一致，包内 338 份 Python 源码、5 份后端 JSON 资源与原 Node 宿主完成核对。
- 包装时将 `frontend/node_modules/node_modules/typescript` 链接规范到包内现有的同版本 pnpm 依赖并同步 manifest；原依赖、版本和锁文件保持。83 个 framework、扩展及主应用完成签名和严格校验。

入口与恢复规则沿用 [iPhone 开发安装手册](../deploy/ios-iphone-install-release.md)；源站 HTTPS 与证书续期的先前回执见 [网络入口执行记录](admin-origin-direct-20261123.md)。

## 实际验证

完整命令、退出码及日志位于 [本轮输出目录](../../frontend/ios/build/iphone-direct-20261124-b49/)。下表耗时记录构建或检查命令执行时间；页面首屏耗时仍需业务测量。

| 命令或检查 | 退出码 | 关键结果 |
| --- | --- | --- |
| `pnpm --dir frontend native:typecheck` | 0 | 原生 TypeScript 检查通过，3.30 秒 |
| `prepare-next.py` 与隔离目录 `pnpm build` | 0 | 完整 Next 构建和类型检查通过，构建 31.24 秒 |
| `bundle-next.py --verify-sources` | 0 | Next 构建后及最终应用资源来源核对通过 |
| `xcodebuild ... CURRENT_PROJECT_VERSION=49 ... build` | 0 | Release 构建成功，99.16 秒 |
| `python3 .../package.py` 与 `codesign --verify --deep --strict` | 0 | 包装、当前应用与恢复包完整签名通过 |
| `devicectl device install app` 与 `device info apps` | 0 | 真机读回 Kastention `0.1.0 (49)` |
| `devicectl device process launch` | 0 | 普通启动成功 |
| `devicectl device info files` | 0 | 安装前后 Library 路径 7405 / 7407 项；原 Application Support 路径缺失数 0；减少的 8 项均为 SplashBoard 截图缓存 |
| 独立 runner 的 `xcodebuild ... build-for-testing` | 0 | 真机 runner 构建通过，14.96 秒 |
| `xcodebuild test-without-building ... StartupReadinessUITests` | 0 | 真机 1 项通过、0 项失败，22.45 秒；服务就绪并返回登录入口 |
| Markdown 清单、引用路径与 `git diff --check` | 0 | 本轮文档检查通过 |

覆盖安装未执行卸载，保留原应用数据容器。路径清单核对覆盖 Application Support 元数据；账户内容、历史正文和完整业务链路的读取尚未执行。

## 制品、有效期与恢复

- [IPA 安装包](../../frontend/ios/build/iphone-direct-20261124-b49/Kastention-0.1.0-49.ipa)，156568402 字节，SHA-256：`e3f7f7e5e292d6cb54e941bcd2bd987a3b78a453a1a938d7e1172ed64c785672`。
- [包装回执](../../frontend/ios/build/iphone-direct-20261124-b49/package-receipt.json)、[安装回执](../../frontend/ios/build/iphone-direct-20261124-b49/installation-receipt.json)、[真机检查摘要](../../frontend/ios/build/iphone-direct-20261124-b49/startup-result.log)。
- [服务就绪截图](../../frontend/ios/build/iphone-direct-20261124-b49/startup-attachments/E9A0D5F6-EBF2-4FCE-B7AD-1DE260E2DE48.png)与[登录入口截图](../../frontend/ios/build/iphone-direct-20261124-b49/startup-attachments/84881251-6E32-451E-BAEF-67BEEBF79E31.png)保存于本机输出目录。
- [构建 48 恢复包](../../frontend/ios/build/iphone-direct-20261124-b49/Restore/InkMemory.app/)已更新有效 profile 并重新验证签名。本轮恢复执行次数为 0。

主应用开发 profile 有效至 **2026-11-26 00:06:08（Asia/Shanghai）**，到期后需要更新开发签名并覆盖安装。此次交付为连接设备的开发安装，App Store 提交次数为 0。
