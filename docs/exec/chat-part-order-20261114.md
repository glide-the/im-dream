<!-- [Input] Notion窄屏反馈、原生消息展示源码、当前工作区和模拟器验证授权。 -->
<!-- [Output] 问题原因、最小修复、Simulator与类型检查证据。 -->
<!-- [Pos] 原生文字与工具顺序修复执行记录；真实模型和发布资格独立登记。 -->
<!-- [Sync] 2026-11-14: 登记原生排序基线复现、最小修复及分轮Simulator回执。 -->
# 原生对话文字与工具顺序修复

日期：2026-11-14，Asia/Shanghai。分支：`develop`。保留当前工作区的既有未提交改动。

来源：[Notion窄屏幕对话显示问题](https://app.notion.com/p/40b30b7547c380f7ac22f85fdd2dbdd0#41830b7547c38001808ac54e327216aa)。用户要求修复并在模拟器验证。

## 范围与判断

`ChatMessageList.native.tsx`的`MessageRow`将完整消息的最后文字移动到工具之后。修复限定展示层：完整消息按`parts`原序渲染，合法完成历史继续通过既有投影显示过程及最终正文。后端、SSE、权限、账户和数据库保持原实现。

需求规则与页面骨架归[消息阅读PRD](../prd/chat/message-reading.md#原生回复中的文字与工具顺序2026-11-14)，正常、异常和状态图归[正式交互稿](../design/multi-platform/chat-message-reading.md#原生消息片段顺序2026-11-14)。选择展示层最小修复，避免调整业务协议和消息数据。

## 验证安排

复用既有Simulator App外壳的独立副本，标识`com.inkmemory.chatorderqualification`。本轮仅编译Metro/Hermes验证入口和XCTest runner。主机16 GiB，初查可用内存34%、磁盘18 GiB；macOS无Linux cgroup。Metro单worker与Xcode单job串行执行，完整Next/App构建及依赖安装数量为零。原App外壳保留为可恢复来源。

`frontend/e2e/native/chat-part-order-fixture.tsx`使用生产消息列表、工具渲染器与显式`UIMessage`片段。`frontend/e2e/ios/ChatPartOrderUITests.swift`测量真实原生元素顺序和位置，验证当前回复完成、取消以及完成历史折叠。该验证无账户、模型、数据库或业务HTTP调用。

## 执行回执

独立目标为`Kastention-ChatOrder-20261114`，iPhone 16 / iOS 18.6，UDID为`EAEC203C-B540-4327-B2C4-53FC1D62DDD2`。复用外壳版本为0.1.0/build17，实际加载本轮编译的Hermes消息组件；普通产品安装包与物理iPhone保持原版本。

私有回执根目录为`frontend/ios/build/chat-part-order-20261114/`，保留基线源码、修订源码、bundle、编译日志、xcresult、截图及摘要。

| 命令或阶段 | 退出码 | 关键输出 |
| --- | --- | --- |
| `corepack pnpm exec react-native bundle --platform ios --dev false --entry-file e2e/native/chat-part-order-fixture.tsx --max-workers 1`，分别指定baseline/fixed输出 | 均0 | 两轮Metro bundle生成完成 |
| `hermesc -O -emit-binary`、独立副本签名、`codesign --verify --deep --strict`与`simctl install` | 均0 | 两轮Hermes编译、签名核对与Simulator安装成功 |
| `xcodebuild build-for-testing ... -jobs 1`，初版及最终runner | 均0 | `TEST BUILD SUCCEEDED` |
| `xcodebuild test-without-building ... -only-testing:InkNativeUITests/ChatPartOrderUITests/testLiveTextAndToolsKeepSourceOrder`，baseline | 65 | 实际执行1项并复现排序失败：文字y=283pt，Read卡片y=183pt |
| 同一runner执行整个测试类，fixed-r1 | 65 | 2项通过、1项测试定位失败；Hermes时长文案为`1 sec`，初版查询使用`1s` |
| 同一测试类，fixed-r2 | 0 | 4项通过、0失败，35.770秒；`TEST EXECUTE SUCCEEDED` |
| `corepack pnpm native:typecheck` | 0 | 原生完整类型检查通过 |
| `corepack pnpm exec tsc --noEmit --pretty false -p ios/build/chat-part-order-20261114/tsconfig.fixture.json` | 0 | 独立fixture连同既有原生声明的类型检查通过 |
| `node ios/build/chat-part-order-20261114/docs/validate-docs.mjs`，frontend目录 | 0 | 三份文档、九项清单、六张Mermaid图解析与渲染通过；引用路径存在 |
| `git diff --check`，限定本轮文件 | 0 | 空白错误为0 |

runner准备首次因当前Ruby未加载既有`xcodeproj`而退出1，随后显式使用已安装CocoaPods的gem目录成功；依赖安装为0。fixture首次独立类型配置缺少既有`textEncoding.native.d.ts`，退出2；加入该声明后通过。fixed-r1的历史页面已显示“Expand process, Took 1 sec”，定位调整为现有过程入口的语义标签，产品代码保持本轮单行修订。原失败回执分别保留。

完整命令形态如下，构建、结果和日志路径均位于本轮目录：

```bash
xcodebuild test-without-building \
  -xctestrun frontend/ios/build/chat-part-order-20261114/runner/DerivedData/Build/Products/InkNativeUITests_iphonesimulator18.5-arm64.xctestrun \
  -destination 'platform=iOS Simulator,id=EAEC203C-B540-4327-B2C4-53FC1D62DDD2' \
  -only-testing:InkNativeUITests/ChatPartOrderUITests \
  -parallel-testing-enabled NO -collect-test-diagnostics never \
  -resultBundlePath frontend/ios/build/chat-part-order-20261114/fixed-r2.xcresult
```

本轮`xctestrun`仅增加`INK_CHAT_ORDER_UI_TARGET=com.inkmemory.chatorderqualification`，用于指定隔离应用。生产行为配置保持原值。

## 修复结果与证据

生产修订仅将`finalIndex`的完整消息回退从`lastText`改为`-1`；最终正文仍从合法历史`projection`读取。完整消息的文字和工具留在原`parts`容器，片段键及原工具调用标识保持。

四项Simulator方法覆盖：

1. 两轮文字与工具交替、三次工具结果更新、当前回复完成及深浅色截图。首段位置保持183pt，Read卡片在239.333pt；后续文字的12次连续采样均为340.667pt，跨度0pt。
2. 已完成历史默认收起过程、展示最终正文、展开后保留片段原序，再收起过程。
3. 取消后的历史展示完整交替片段。
4. 长历史上滑阅读期间，三次工具更新及新增最终正文后，原阅读文字位置均为307.667pt；原“滚动到底部”操作回到最新正文。

截图：[新增Read后](../../frontend/ios/build/chat-part-order-20261114/live-read-order.png)、[文字与工具交替](../../frontend/ios/build/chat-part-order-20261114/live-interleaved-order.png)、[完成历史展开](../../frontend/ios/build/chat-part-order-20261114/history-expanded.png)、[深色完成回复](../../frontend/ios/build/chat-part-order-20261114/completed-live-dark.png)。已逐张检查排序、完整正文与深色对比。

实际安装的`main.jsbundle`与候选SHA-256一致：`5656d03734032735d1fdf87d1ca306ae28863a047a76e1e03ecfeb7cb9894914`，回执为`installed-bundle-receipt.json`。源码及验证入口摘要归`final-source-sha256.json`。

## 验证边界与收尾

本轮结果属于生产消息组件的Simulator技术验证。真实账户、业务数据库、Gateway、真实模型和物理设备调用数量为0；普通App重新打包、真机安装及发布均未执行。当前工作区既有改动继续保留。

截图、xcresult、源码与构建回执保留。仅关闭并删除本轮具名Simulator，原Simulator、应用数据和本机服务保持。
