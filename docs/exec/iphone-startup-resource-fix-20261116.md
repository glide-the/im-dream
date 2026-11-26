<!-- [Input] 构建45的真机错误、当前Python资源装配入口及已连接iPhone16。 -->
<!-- [Output] 启动资源修复、构建46、覆盖安装、冷启动与真机页面检查回执。 -->
<!-- [Pos] iPhone启动失败修复执行记录；安装流程由开发安装手册维护。 -->

# iPhone启动资源遗漏修复与构建46

## 问题与范围

2026-11-16，用户反馈构建45持续显示启动失败。开发者控制页返回`RUNTIME_START_FAILED`，原异常为缺少`app/services/admin_data/external_share_contract.json`。构建45的进程启动与存活检查通过；应用内服务就绪检查存在缺口。真机冷启动日志随后复现`python_runtime_bind`及`startup_total`失败。

[`external_share_data.py`](../../backend/services/admin_data/external_share_data.py)在导入时读取同目录合同。原[`bundle-python.py`](../../frontend/ios/scripts/bundle-python.py)复制Python源码与两份memory合同，外部分享合同缺少打包条目。

## 修复与交付

- 在原Admin JSON资源复制清单追加`external_share_contract.json`，沿用源合同字节。
- 新增[`StartupReadinessUITests.swift`](../../frontend/e2e/ios/StartupReadinessUITests.swift)，激活显式指定的已安装应用，检查“本地服务已就绪”，返回原账户页面并保存截图。
- 基于`develop`提交`5051868a168bc62496288220a07fe204b3c94f8f`及本轮打包修复生成Kastention `0.1.0 (46)`。前端运行源码保持，复用构建45已验证的Next制品；来源检查覆盖623项运行输入。
- 复用原依赖锁、Pods和本机构建缓存，构建阶段串行执行，Xcode单job、Metro单worker。构建前Mac内存可用比例61%，磁盘可用约25GiB；保留构建44的完整恢复制品。
- 包装校验覆盖337份Python源码、5份Admin及memory JSON资源和83个framework签名。源私有配置保持原摘要，沿用线上Admin及原权限。

## 验证证据

私有输出目录为[`frontend/ios/build/iphone-startup-fix-20261116-b46/`](../../frontend/ios/build/iphone-startup-fix-20261116-b46/)。

| 命令或步骤 | 退出码 | 结果 |
| --- | --- | --- |
| `bundle-next.py --verify-sources` | 0 | 623项当前运行输入一致 |
| `xcodebuild ... CURRENT_PROJECT_VERSION=46 ... build` | 0 | `BUILD SUCCEEDED`，132.84秒 |
| 本轮`package.py`及`codesign --verify --deep --strict` | 0 | 5份JSON资源与源码一致，签名通过 |
| `devicectl device install app`与版本读取 | 0 | iPhone16读回Kastention `0.1.0 (46)` |
| `devicectl device process launch` | 0 | 普通启动完成 |
| 冷启动控制台采集 | 观察器主动结束 | `python_runtime_bind`与`startup_total`均为`ok`；仅结束本轮日志观察进程 |
| 首次UI runner构建 | 70 | 生成工程默认Simulator平台，设备destination匹配失败；记录为测试准备失败 |
| 指定iphoneos的`xcodebuild ... build-for-testing` | 0 | 本轮独立真机runner构建通过，21.54秒 |
| `xcodebuild test-without-building ... StartupReadinessUITests` | 0 | 1项真机检查通过，0项失败；页面显示服务就绪并返回已有Chat页面 |
| Markdown清单、引用路径及`git diff --check` | 0 | 本轮文档引用与文件清单有效 |

覆盖安装前后，Application Support原路径缺失数为0；减少的5项均为SplashBoard截图缓存。卸载、账户写入和模型调用次数均为0。真实模型生成及其他业务任务维持各自验收范围。

开发profile有效至2026-11-16 23:21:34北京时间。签名到期后沿原流程重新签名安装。

## 制品与回执

- [IPA安装包](../../frontend/ios/build/iphone-startup-fix-20261116-b46/Kastention-0.1.0-46.ipa)，SHA-256为`dd46e56c8761b5b9c50d2b19715718ce2550aa25d1cf0824b3d68482bab8d74f`。
- [包装回执](../../frontend/ios/build/iphone-startup-fix-20261116-b46/package-receipt.json)与[安装回执](../../frontend/ios/build/iphone-startup-fix-20261116-b46/installation-receipt.json)。
- [冷启动回执](../../frontend/ios/build/iphone-startup-fix-20261116-b46/cold-start-verification.json)与[真机检查命令](../../frontend/ios/build/iphone-startup-fix-20261116-b46/startup-readiness-command.json)。
- [页面截图清单](../../frontend/ios/build/iphone-startup-fix-20261116-b46/startup-attachments/manifest.json)保存在本机私有目录，保留原账户页面截图供复核。
