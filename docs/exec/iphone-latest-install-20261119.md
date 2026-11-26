<!-- [Input] develop最新提交、现有移动配置、开发签名及已连接iPhone16。 -->
<!-- [Output] 构建48的来源、包装、覆盖安装、数据目录与真机启动检查回执。 -->
<!-- [Pos] 本次手机部署执行记录；操作入口由iPhone开发安装手册维护。 -->
<!-- [Sync] 2026-11-26: 整理构建48历史回执，本机日志和制品使用输出路径登记。 -->

# iPhone最新代码安装：构建48

## 交付范围

2026-11-19，按用户要求将最新代码部署到现有iPhone16。源码为`develop`提交`3c8ddac1`，构建前执行`git fetch origin develop`，本地与远端提交一致，工作区干净。

已将Kastention `0.1.0 (47)`覆盖升级为`0.1.0 (48)`，Bundle ID沿用`com.inkmemory.mobile`。应用启动、应用内服务就绪和返回原账户页面的真机检查通过。业务代码修改、卸载、账户写入及模型调用次数均为0。

## 构建与包装

- Mac物理内存16GiB，容量检查时内存可用比例46%，磁盘可用7.23GiB。Next、Metro、Xcode依次运行，Next单worker、Metro单worker、Xcode单job；Node old space按每进程2048MiB执行，Next父进程和worker分别计入预算。macOS容量检查采用本机内存诊断，cgroup检查标记为不适用，交换配置保持。
- 复用已安装依赖、Pods及原生编译缓存；构建47制品中的依赖锁摘要与当前锁文件一致。重新准备和构建本轮具名Next目录，633项前端运行输入校验通过，484项原生、后端及构建输入在构建期间保持一致。
- 包内338份Python源码、5份Admin与memory JSON资源、原Node宿主和Next来源回执完成核对；83个framework及主应用完成签名。包内配置沿现有移动及线上配置准备，原配置文件摘要保持。
- 首次包装遇到Next追踪结果中的失效TypeScript链接：`frontend/node_modules/node_modules/typescript`。本轮制品将该链接指向闭包内同版本的`frontend/node_modules/.pnpm/typescript@5.8.3/node_modules/typescript`，同步`mobile-manifest.json`后重新签名。原依赖目录、依赖版本和锁文件保持，首次失败制品及回执保留在本轮私有输出中。
- 真机检查复用现有`StartupReadinessUITests.swift`。默认Ruby缺少`xcodeproj`时使用已安装CocoaPods的gem目录；生成runner的默认Simulator目标调整为iphoneos，随后完成真机runner构建。新增依赖安装次数为0。

## 实际验证

当次输出目录为 `frontend/ios/build/iphone-latest-20261119-b48/`，属于本机构建输出，未纳入版本管理。下表保留当次命令、退出码与验证摘要。

| 命令或检查 | 退出码 | 结果 |
| --- | --- | --- |
| `pnpm --dir frontend native:typecheck` | 0 | 原生TypeScript检查通过，3.27秒 |
| `python3 frontend/ios/scripts/prepare-next.py`及本轮Next目录的`pnpm build` | 0 | 完整编译和类型检查通过，构建32.57秒 |
| `bundle-next.py --verify-sources` | 0 | 633项前端运行输入与当前源码匹配 |
| `xcodebuild ... CURRENT_PROJECT_VERSION=48 ... build` | 0 | `BUILD SUCCEEDED`，114.75秒 |
| 本轮包装与`codesign --verify --deep --strict` | 0 | 包资源、恢复包及完整签名通过 |
| `devicectl device install app`及`device info apps` | 0 | 设备读回Kastention `0.1.0 (48)` |
| `devicectl device process launch` | 0 | 应用启动成功 |
| `devicectl device info files` | 0 | 安装前后Library路径均为4383项，Application Support原路径缺失数为0；减少7项均属SplashBoard截图缓存 |
| `xcodebuild ... build-for-testing` | 0 | 本轮独立真机runner构建通过，10.81秒 |
| `xcodebuild test-without-building ... StartupReadinessUITests` | 0 | 真机1项通过、0项失败；显示“本地服务已就绪”并返回原账户页面，34.48秒 |
| Markdown清单、引用路径及`git diff --check` | 0 | 本轮文档检查通过 |

首次签名校验失败及runner目标匹配失败分别保留原回执；修正各自包装或测试准备条件后执行后续检查。应用安装、启动与上述页面检查具备本轮证据；真实模型生成、其他业务任务和商店发行保持各自验收范围。

## 制品与恢复

- IPA安装包：当次输出目录内的 `Kastention-0.1.0-48.ipa`，SHA-256：`03e5b380b8b9b9b243e470480fec2ce101877f92ffdcd13f7b55904bb9d1c075`。
- 包装回执、安装回执及真机检查摘要：当次输出目录内的 `package-receipt.json`、`installation-receipt.json` 和 `startup-result.log`。
- 真机截图附件：当次输出目录内的 `startup-attachments/`，按本机私有附件管理。
- 构建47恢复包：当次输出目录内的 `Restore/InkMemory.app/`，当次已验证签名。本次恢复执行次数为0。

主应用开发profile有效至2026-11-26 00:06:08北京时间，活动扩展profile有效至2026-11-23 15:50:46北京时间。后续签名到期时沿[开发安装手册](../deploy/ios-iphone-install-release.md)更新签名并覆盖安装。
