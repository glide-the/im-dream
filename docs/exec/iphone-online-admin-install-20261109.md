<!-- [Input] 当前Dream工作树、现有线上Admin配置、iOS签名资源及已连接iPhone16。 -->
<!-- [Output] Release43构建、资源校验、覆盖安装、启动及数据目录核对回执。 -->
<!-- [Pos] 本次真机安装执行记录；安装步骤由iPhone开发安装手册维护。 -->
<!-- [Sync] 2026-11-09: 当前工作树完成线上Admin包构建与同设备覆盖安装。 -->

# iPhone线上Admin构建43与安装记录

## 需求与交付范围

用户要求使用最新代码，将接入线上Admin的应用打包并安装到当前连接的手机。本轮交付Kastention `0.1.0 (43)`，Bundle ID沿用`com.inkmemory.mobile`，目标设备为已配对的iPhone16。

构建起始源码为`codex/frontend-online-admin-20261109`分支的`c2a367db`及工作树已有业务源码。`git fetch origin`完成后，该提交包含当时`origin/develop`全部提交，另含前端线上Admin启动配置提交。安装结束时，共享工作区已由并行工作切换到`develop`的PR101合并提交`7721594a`；该提交与`c2a367db`的受跟踪文件差异为0。末次校验确认579项Next运行输入及386项原生、后端与锁文件输入摘要保持；包内333份Python源码与工作树逐项匹配。

本轮执行开发设备安装。完整登录、真实模型调用、跨端继续对话及商店发布的验收状态保持待执行。

## 配置与数据

- 后端完整配置读取私有`backend/.env.mobile`，Next完整配置读取私有`frontend/.env.online`，仅写入候选安装包。
- 认证、Dream数据传输、Product API及Gateway均指向`https://ink-admin.suoxya.com`；认证issuer沿用该地址的`/api/auth`。
- 包内public origin按现有`host-config.json`设置为`http://127.0.0.1:4173`；账号回调采用`com.inkmemory.mobile.auth:/auth/callback`，MCP回调采用`com.inkmemory.mobile.mcp:/oauth/callback`。
- 包内sandbox值沿用工程现有`false`。原认证凭据、Cookie密钥及业务权限继续由完整配置和原运行模块管理。
- 本机四份私有配置文件构建前后SHA-256保持一致；本轮源配置写入次数为0，依赖安装次数为0，卸载次数为0，模型调用次数为0。
- 同Bundle ID覆盖安装。安装前读取3953项Library元数据，安装后读取3950项，保留原路径3945项；减少的8项均为SplashBoard缓存，Application Support原路径缺失数为0。

## 容量与恢复准备

构建主机为16GiB内存的Mac，构建前系统可用比例31%，磁盘可用约7.8GiB。macOS无Linux cgroup限额。构建串行执行，Next采用现有准备脚本的单CPU配置，Node old space本轮预算2048MiB，Metro单worker，Xcode单job；各构建阶段设置20分钟期限。Next完整类型检查继续执行。

复用已安装依赖、Pods及已有DerivedData。Next构建最大RSS为1267826688字节；Xcode命令进程最大RSS为203276288字节，此数值仅描述该进程，worker总占用按构建预算管理。封装后磁盘可用约6.8GiB。

原构建35完整App继续保留。原profile已于2026-11-08北京时间到期，本轮通过Xcode自动签名更新profile，并将原制品副本重新签名；恢复副本通过`codesign --verify --deep --strict`。新包profile有效期至2026-11-16 23:21:34北京时间。

## 执行命令与结果

以下相对路径均以仓库根目录为起点。私有输出目录为`frontend/ios/build/iphone-online-admin-20261109-b43/`，详细命令、退出码、日志、源码摘要及设备JSON分别保存。

| 命令或阶段 | 退出码 | 关键结果 |
| --- | --- | --- |
| `git fetch origin`及`git rev-list --left-right --count HEAD...origin/develop` | 0 | 输出`1 0`，工作树提交包含远端develop |
| `python3 frontend/ios/scripts/prepare-next.py`，设置本轮独立`INK_IOS_NEXT_ROOT` | 0 | 生成当前源码的无凭据Next构建目录 |
| 在本轮`Next/build-source`执行已安装的`next build --webpack` | 0 | 编译、TypeScript及静态资源生成完成，34.34秒 |
| `python3 frontend/ios/scripts/bundle-next.py --verify-sources` | 0 | 构建前后来源校验均通过 |
| 在frontend执行`tsc --noEmit --pretty false -p tsconfig.native.json` | 0 | 原生类型检查通过 |
| 下方完整`xcodebuild`命令 | 0 | `BUILD SUCCEEDED`，163.93秒 |
| 首次执行本轮`package.py` | 1 | 辅助校验拒绝源配置中的同值重复键；校验调整为接受同值、拒绝异值，源配置保持 |
| 最终执行本轮`package.py`及`codesign --verify --deep --strict` | 0 | 83个framework签名通过，333份Python及Next/Node资源来源一致 |
| `xcrun devicectl device install app --device <本轮设备> <本轮App>` | 0 | 同Bundle ID覆盖安装完成 |
| `xcrun devicectl device info apps --device <本轮设备> --bundle-id com.inkmemory.mobile` | 0 | 设备读回Kastention `0.1.0`、构建`43` |
| `xcrun devicectl device process launch --device <本轮设备> com.inkmemory.mobile` | 0 | 普通启动成功，PID为5059 |
| `xcrun devicectl device info processes --device <本轮设备>` | 0 | 后续读取确认PID5059继续运行 |
| 安装前后`devicectl device info files` | 0 | Application Support原路径全部保留 |
| `git diff --check`及本轮Markdown清单、引用路径检查 | 0 | 三份文档检查通过，全部本地引用有效 |

```bash
xcodebuild \
  -workspace frontend/ios/InkMemory.xcworkspace \
  -scheme InkMemory -configuration Release -sdk iphoneos \
  -destination 'generic/platform=iOS' \
  -derivedDataPath frontend/ios/build/rebuild-iphone-20261031/DerivedData \
  -jobs 1 COMPILER_INDEX_STORE_ENABLE=NO -allowProvisioningUpdates \
  CURRENT_PROJECT_VERSION=43 ENTRY_FILE=index.native.js build
```

## 制品与证据

- [IPA安装包](../../frontend/ios/build/iphone-online-admin-20261109-b43/Kastention-0.1.0-43.ipa)：153683804字节，SHA-256为`3475f4190d31b6c564205e1ce43c675651ef4879b8ac0038df72658c8f03b951`。
- [封装回执](../../frontend/ios/build/iphone-online-admin-20261109-b43/package-receipt.json)：包内服务地址、签名、profile、源码匹配及源配置保持证据。
- [安装回执](../../frontend/ios/build/iphone-online-admin-20261109-b43/installation-receipt.json)：安装、版本读回、启动及文件元数据摘要。
- [启动后进程核对](../../frontend/ios/build/iphone-online-admin-20261109-b43/process-verification.json)：原App进程继续运行。
- [构建输入校验](../../frontend/ios/build/iphone-online-admin-20261109-b43/input-verification.json)：386项输入，变更数为0。
- [结束时源码状态](../../frontend/ios/build/iphone-online-admin-20261109-b43/final-source-state.json)：develop合并提交与运行源码一致。
- [安装手册](../deploy/ios-iphone-install-release.md)及[容量与恢复手册](../deploy/build-memory-and-recovery.md)维护后续操作规则。

制品和详细日志位于Git忽略的本机私有目录，文件权限及目录边界沿本轮输出管理。公开记录只保留目标版本、状态和摘要。
