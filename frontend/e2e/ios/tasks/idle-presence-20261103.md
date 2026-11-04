<!-- [Sync] 2026-11-04: 登记v4.2核心通过、限定发丝采样及显式单次真实任务方法。 -->
<!-- [Input] 用户授权的25秒屏保、共享Thread二值及普通Simulator应用。 -->
<!-- [Output] XCUITest步骤、运行回执及平台验收边界。 -->
<!-- [Pos] 仅记录XCUITest E2E；产品规则与实现归multi-platform正式设计。 -->

# 屏保与活跃Thread显示

## 目标与前提

目标为iPhone 16 Plus、iOS 18.6 Simulator，普通App `com.inkmemory.mobile`、构建33。复用已有登录、页面、草稿和端侧Dream；使用安装更新，保留应用数据。真实手机与App Store退出本轮范围。

测试源为[IdleScreenSaverUITests.swift](../IdleScreenSaverUITests.swift)，类`IdleScreenSaverUITests`。独立runner由[prepare-ui-runner.rb](../prepare-ui-runner.rb)创建，显式scheme环境`INK_IOS_UI_TARGET_BUNDLE_ID=com.inkmemory.mobile`绑定普通App。runner无生产App依赖，无重新安装依赖、重置账户或注入业务状态。

## 业务旅程与断言

| 方法 | 步骤 | 预期 |
| --- | --- | --- |
| `testIdleDismissalRetainsPageAndDoesNotTapThrough` | More→无操作→点击底层Chat位置→触摸重计时→后台→前台 | 25秒前不显示，届满覆盖；二值可读；关闭触摸保留More，前台返回重新计时 |
| `testKeyboardAndUnsentDraftRemain` | Chat原输入追加可辨认测试短句→等待28秒→More→屏保→返回Chat→删除本轮短句 | 键盘输入占用阻止屏保；跨栏目与屏保保留原输入；原稿存在时只读核对；原稿为空时清除本轮测试文字并恢复语义空白 |

附加方法：`testUnifiedClockNativeFrames`在屏保中采样两张发丝基线及一张运动帧；`testZCleanupOnlyOwnedMarker`仅在完整草稿等于本轮标记时沿原新建对话操作恢复空输入。`testYReadCurrentConfiguredModel`只读正常设置页；当前Simulator的radio AX值为`checked`／`unchecked`。`testPresenceDuringOneRealTask`须显式选择，沿普通账户和已确认模型发送一条限时Bash等待任务，检查屏保有／无、保留任务及系统截图；禁止自动重发。`testReadCompletedPresenceTask`仅重读同一已完成任务及最终屏保无状态，不发送任何新请求。执行状态归专项回执。

原稿包含非空正文时保持原稿只读；原稿为空时仅输入未发送测试文字。空contenteditable的AX值可含段落换行，清理使用删除键，避免将换行送入原Enter处理。

草稿方法只输入未发送文字；真实任务方法单独授权、显式选择并保留正常历史。禁止删除历史、修改权限或账户。屏保计时准确边界、观察集合完整性与账户隔离另由纯控制器／Factory合同覆盖。系统组件实际创建、锁屏截图与状态变更按独立回执登记；包内扩展存在和屏保截图分别记录。

## 实际命令与证据

私有输出根：`frontend/output/app04-idle-implementation-20261103/`。xcresult、截图和安装目录均排除Git。操作命令如下，具体轮次的日志保留独立文件：

```sh
GEM_HOME=/opt/homebrew/Cellar/cocoapods/1.17.0_1/libexec ruby frontend/e2e/ios/prepare-ui-runner.rb "$IDLE_EVIDENCE/ui-runner" IdleScreenSaverUITests.swift
xcodebuild -project "$IDLE_EVIDENCE/ui-runner/InkNativeUITests.xcodeproj" \
  -scheme InkNativeUITests -destination "platform=iOS Simulator,id=$IDLE_SIMULATOR" \
  -derivedDataPath "$IDLE_EVIDENCE/ui-derived" -resultBundlePath "$IDLE_EVIDENCE/ui-rN.xcresult" \
  -jobs 1 -parallel-testing-enabled NO CODE_SIGNING_ALLOWED=NO test
```

生成后在私有scheme的TestAction配置显式目标App环境；源码及生产配置保持原入口。

| 轮次 | 状态与处理 |
| --- | --- |
| r1 | exit65；runner缺少显式目标环境，两个方法在读取前提时失败，无产品断言执行 |
| r2 | exit65；Debug告警条遮挡导航；后续方法等待底层页时遇到已显示屏保。关闭告警并先关闭屏保再读取导航 |
| r3 | 屏保实际按25秒出现，底层二值已视觉确认；嵌套Text未独立暴露AX，状态断言失败。增加同一二值accessibilityValue；心情／编辑占用与清理继续复测 |
| r4–r5 | 前台返回Chat后WKContentView保留responder，导致计时届满持续延后；改用可见WK文档DOM焦点布尔查询。测试清理按空编辑器语义处理，原稿保留 |
| r6 | runner曾采用旧测试体，改用独立bundle ID及新derivedData；前置失败保留 |
| r7 | exit0；两个核心旅程通过 |
| v4.2-r2 | 三个核心方法通过；额外模型探针选择器失败，整轮exit65 |
| v4.2-observation | exit0；发丝帧方法通过，模型探针跳过1项。像素ROI运动差965、前后基线差0，记录限定帧采样 |

新增v4.2轮次：`ui-clock-r1`中一体化时钟的25秒／关闭／导航／前后台旅程通过；键盘用例的编辑器前提为只读，清理用例缺少焦点。后续键盘检查先沿原入口重试一次读取，仍只读则标记未满足前提；自有标记清理沿原New Chat，仅在整份草稿匹配本轮标记时执行。

最终回执由[专项执行记录](../../../../docs/exec/app-experience-foreground-recovery-20261102.md)统一登记。前置失败、断言失败与成功轮次均保留；未执行范围单列。

测试键盘组合参考[Apple typeKey文档](https://developer.apple.com/documentation/xcuiautomation/xcuielement/typekey(_:modifierflags:)-9ubn)，2026-11-03查阅；本机Xcode iOS XCUIElement头文件已核对该方法。

一体化渲染规则依据用户[v4.2规范](../../../../docs/prd/Kastention-时钟交互规范-v4.2.md)。`StartupScreen`和`IdleScreenSaver`共用生产`StartupArtwork`；资源、时间算术和截图分别核对，原型浏览器验收保持其原范围。

单次真实任务轮次：第一次runner编译失败（exit65、调用0次）；修复后仅发送一条GPT-6.1-Sol任务。运行屏保有通过，105秒正文到达时立即断言停止结束失败（exit65）。主任务通过正常UI关闭一次其间出现的屏保，后续同一任务已显示最终回复、停止结束及屏保无。该辅助观察与整轮XCUITest分别记录，禁止汇报整轮通过。后续等待方法改为正文与停止状态共同结束，未再次发送真实任务。

最终同一任务回读：`testReadCompletedPresenceTask`退出0，1项通过、0失败、0跳过，耗时32.025秒；原最终回复、停止结束及25秒后屏保无均通过。该方法发送0次，原真实任务失败回执保留。
