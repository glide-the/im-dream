<!-- [Input] 原iPhone账号调试任务、既有AccountEntryUITests及用户复验回执。 -->
<!-- [Output] XCUITest目标、交互断言、执行前提与已有证据范围。 -->
<!-- [Pos] 本次账号入口UI E2E任务文档；当前修订只整理文件。 -->
<!-- [Sync] 2026-11-02: 单列XCUITest与用户手工验收，本轮设备操作为0。 -->

# 账号入口与Google回到应用

## 目标与范围

通过XCUITest确认Dream原登录弹窗、注册入口、左上关闭、Google系统认证进入与取消，以及成功后关闭弹窗并回到原主页的可见交互。正常网页登录、Client ID、PKCE、Cookie/CSRF、原账户和权限沿现有实现。

本轮状态：文档准备。仅整理任务与工具手册，本轮测试方法执行0次、设备安装0次、登录操作0次、模型调用0次。已有修复后的用户真机确认及历史测试单列如下，原业务执行记录见[账号入口修复](../../../../docs/exec/ios-account-entry-fix-20261102.md)。

## 目标与测试入口

| 项目 | 当前记录 |
| --- | --- |
| 设备与App基线 | 前阶段iPhone16、iOS18.0.1，`com.inkmemory.mobile`，0.1.0/27；后续执行前重新核对实际安装版本 |
| 测试源 | 私有生成物`frontend/ios/build/ios-auth-20261102/ui-validation/AccountEntryUITests.swift`；当前未纳入父目录稳定Swift用例 |
| 既有方法 | `AccountEntryUITests.testOriginalRegistrationAndGoogleEntry()`、`testInspectGoogleReturn()`；诊断方法按原源文件单独选择 |
| runner前提 | 既有账号UI runner工程、目标设备、签名、profile及设备信任均可用；具体工程及scheme从该轮私有回执确认 |
| 工程准备限制 | 父目录`prepare-ui-runner.rb`只接受其同目录Swift源；本任务私有账号源无法直接作为该脚本参数。本轮不复制测试源或修改脚本 |
| 取证位置 | 本轮独立`frontend/ios/build/ios-xcuitest-<任务>-<运行号>/`，保留xcresult、summary及截图，Git只记录脱敏摘要 |

后续复用私有源前确认文件存在、内容及其允许操作；本任务文件和方法名属于本次回执，其他工作区缺少生成物时先登记准备依赖。需要长期维护账号UI用例时另行实施父目录测试源归属，本轮代码变更为0。

## 操作及验收

| 步骤 | 操作与目标 | 预期结果 | 失败与恢复 |
| --- | --- | --- | --- |
| 1 | `XCUIApplication`激活指定App，等待原登录入口 | App前台，原页面与输入保留 | 设备或runner失败登记前置失败；排除业务断言结论 |
| 2 | 点击原登录入口，等待登录弹窗 | 原表单显示，左上关闭可操作 | 保存当前状态和截图，按原页面加载阶段定位 |
| 3 | 点击原Create Account入口 | 原Email及注册字段可见，无新账户提交 | 元素不可见时检查实际页面及可访问性；保留原注册流程 |
| 4 | 左上关闭，再次进入登录 | 弹窗关闭且原主页可操作；可重新打开 | 等待关闭和主页各自断言，保持原账户数据 |
| 5 | 点击Google，进入原系统认证会话，再取消 | Google界面可达；取消返回原登录页面，可再次操作 | 系统确认由持有人完成；查询不到元素时记录实际阻塞 |
| 6 | 在已有授权任务范围内完成真实Google登录 | 原回调及会话完成，登录弹窗消失，原主页可操作 | 原错误保留；重新发起原登录，旧授权码重放0次 |
| 7 | 保存步骤截图及结果摘要 | 方法、退出码、断言与附件匹配 | 没有方法执行或断言时按缺失记录 |

上述步骤定义目标覆盖。既有`testOriginalRegistrationAndGoogleEntry`用于原注册表单、Google入口及取消观察；`testInspectGoogleReturn`读取返回页面的固定标记并保存截图。成功登录到主页的完整自动化断言需后续核对并补齐，现有方法名称无法替代覆盖证据。本轮维持现有源文件。

操作时序、失败恢复和工具生命周期见[独立手册](../../../../docs/deploy/ios-device-debugging.md#7-操作时序与生命周期)。该任务中原登录创建WKWebView、Google创建系统会话、原会话成功触发`finishLogin`；XCTest runner结束与Dream后端生命周期分别管理。

## 已有回执与本轮状态

| 来源 | 已有结果 | 覆盖范围 |
| --- | --- | --- |
| 前阶段真机UI测试 | 构建27原Google选择页、取消/关闭及注册字段已观察 | Google账户完整成功返回与新账户创建各自验收 |
| 前阶段`testInspectGoogleReturn`尝试 | iOS以签名、entitlements或信任错误拒绝runner，方法未执行 | 本地签名校验退出0和普通App能启动分别保留 |
| 后续用户反馈 | 独立Admin代理出口修复后，用户确认“好了我已经验证了” | 本次Google修复为用户真机复验通过；自动化逐阶段会话及界面记录缺失 |
| 当前文档任务 | 已整理XCUITest目标、工具步骤与状态规则 | 本轮新增设备/真实业务验收0项 |

既有私有证据根为`frontend/ios/build/ios-auth-20261102/`；`google-current-return-device.xcresult`和对应日志保存runner拒绝记录。截图可能包含个人身份，仅在受限目录中复核。

## 后续执行依赖与回执格式

后续执行前核对明确目标设备、App版本、可用账号runner与设备信任，以及当次允许的登录或取消操作。单次选择一个实际方法，按[工具手册](../../../../docs/deploy/ios-device-debugging.md#6-使用xcuitest点击读取状态与截图)执行。当前未请求真实测试或签名操作。

回执填写：日期及运行号、目标版本/提交、Swift类与方法、实际命令、退出码、方法是否进入、断言结果、xcresult路径、截图文件名、未执行范围及后续依赖。工具前置失败、UI失败和后台网络失败按各自证据记录，原数据和历史回执继续保留。
