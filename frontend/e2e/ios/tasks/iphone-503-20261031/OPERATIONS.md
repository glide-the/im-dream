<!-- [Input] 本任务中已执行的AppleScript、OSA JavaScript和界面反馈。 -->
<!-- [Output] 按操作项保存的命令、结果、失败和当前执行边界。 -->
<!-- [Pos] iPhone503任务的历史操作过程；命令示例保存原输入。 -->
<!-- [Sync] 2026-11-01: 整理原阶段尝试，命令退出和界面效果分别登记。 -->

# 操作过程

以下命令为2026-10-31历史记录。当前用户要求停止桌面操作，本轮只整理文件和进行静态检查。主机坐标、截图尺寸及窗口信息保留原阶段数值。

## 1. 操作准备

系统iPhone镜像曾要求macOS登录认证，设备持有人完成该步骤。AppleScript执行方式随后获得用户明确授权。账户登录凭据保留在原任务的内存处理范围，系统脚本中无凭据输入。

当时目标为系统镜像应用`com.apple.ScreenContinuity`及同一iPhone上的Ink & Memory。原App构建19保持，新增桌面操作框架和依赖均为0。

## 2. 窗口定位与原脚本

语言：AppleScript。脚本为[mirror-click.original.applescript](mirror-click.original.applescript)。原执行入口位于`frontend/ios/build/iphone-503-20261031/`，本任务包中的文件保持同一内容。

```sh
osascript frontend/ios/build/iphone-503-20261031/mirror-click.applescript inspect
```

退出0，返回窗口位置`1045, 38`和尺寸`314, 699`。该结果属于当次窗口读取。

脚本先定位镜像进程并置前，读取窗口位置/尺寸，再把截图坐标换算为窗口坐标。`inspect`操作同样包含置前步骤，后续执行需纳入桌面操作范围。

## 3. 坐标点击尝试

语言：AppleScript。原输入来自当次630×1398截图，目标区域为原页面底部更多入口。

```sh
osascript frontend/ios/build/iphone-503-20261031/mirror-click.applescript click 519 1294 630 1398
```

命令退出0，返回镜像窗口的group引用；页面未观察到目标变化。重复点击尝试保留相同资格。坐标换算及命令退出独立于手机控件收到点击。

## 4. OSA JavaScript鼠标事件补充

以下代码通过`osascript -l JavaScript`执行。事件坐标为当次Mac桌面坐标`1304, 685`。命令退出和实际界面变化分别记录。

### 4.1 按下与释放

```javascript
ObjC.import("ApplicationServices");
var e = $.CGEventCreateMouseEvent(null, 1, $.CGPointMake(1304, 685), 0);
$.CGEventPost(0, e);
var u = $.CGEventCreateMouseEvent(null, 2, $.CGPointMake(1304, 685), 0);
$.CGEventPost(0, u);
```

退出0，原页面未观察到目标变化。

### 4.2 光标定位与延迟调用失败

```javascript
ObjC.import("ApplicationServices");
var app = Application.currentApplication();
app.includeStandardAdditions = true;
var p = $.CGPointMake(1304, 685);
$.CGWarpMouseCursorPosition(p);
$.CGEventPost(0, $.CGEventCreateMouseEvent(null, 5, p, 0));
app.delay(0.15);
$.CGEventPost(0, $.CGEventCreateMouseEvent(null, 1, p, 0));
app.delay(0.1);
$.CGEventPost(0, $.CGEventCreateMouseEvent(null, 2, p, 0));
```

退出1，返回`-1708`。命令序列中断，界面点击效果未确认；具体失败调用未取得独立定位回执。

### 4.3 移动、按下与释放

```javascript
ObjC.import("Cocoa");
ObjC.import("ApplicationServices");
var p = $.CGPointMake(1304, 685);
$.CGEventPost(0, $.CGEventCreateMouseEvent(null, 5, p, 0));
$.NSThread.sleepForTimeInterval(0.15);
$.CGEventPost(0, $.CGEventCreateMouseEvent(null, 1, p, 0));
$.NSThread.sleepForTimeInterval(0.1);
$.CGEventPost(0, $.CGEventCreateMouseEvent(null, 2, p, 0));
```

退出0，原页面未观察到目标变化。

## 5. 检查器及窗口状态核对

电脑点击工具多次返回`noWindowsAvailable`；检查器截图另有`SCStreamErrorDomain/-3812`。这些结果归电脑控制前置。

检查器曾显示point inspection开启，随后通过原控件关闭并确认off。关闭后再次点击，原页面仍未观察到目标变化。该先后关系保留为观察，点击失败原因保持未确认。

语言：AppleScript。直接读取窗口属性的历史尝试：

```applescript
tell application "System Events" to tell (first application process whose bundle identifier is "com.apple.ScreenContinuity") to return {frontmost, visible, name of windows, value of attribute "AXMinimized" of first window, value of attribute "AXMain" of first window, position of first window, size of first window}
```

退出1，返回`-1719`及window 1索引错误。

一次进程属性读取尝试退出1并返回`-1728`，原表达式如下。原返回中的其他进程清单退出归档。

```applescript
tell application "System Events" to get {name, unix id, visible} of every application process whose bundle identifier is "com.apple.ScreenContinuity"
```

## 6. 激活及重新打开尝试

语言：AppleScript。

```applescript
tell application id "com.apple.ScreenContinuity"
    activate
    reopen
end tell
tell application "System Events"
    set matchingProcesses to every application process whose bundle identifier is "com.apple.ScreenContinuity"
    set facts to {}
    repeat with candidate in matchingProcesses
        tell candidate
            set end of facts to {unix id, frontmost, visible, count of windows}
            if (count of windows) > 0 then set end of facts to {position of first window, size of first window, value of attribute "AXMinimized" of first window}
        end tell
    end repeat
    return facts
end tell
```

退出1，返回`-1708`，错误位于candidate上下文中的count读取。激活与重新打开的实际效果未取得独立成功回执。

## 7. 指定进程读取

语言：AppleScript。

```applescript
tell application "System Events"
    tell process "iPhone Mirroring"
        set windowCount to count of windows
        if windowCount is 0 then return {frontmost, visible, windowCount}
        return {frontmost, visible, windowCount, position of first window, size of first window, value of attribute "AXMinimized" of first window}
    end tell
end tell
```

退出0，返回`false, true, 0`。该回执表示当次进程属性读取及窗口数，手机业务运行状态继续通过原业务回执判定。

## 8. 停止及任务归属

用户随后要求停止镜像操作，并说明正在使用电脑。镜像、窗口置前、键鼠和AppleScript界面操作随后停止；当前归档请求仅涉及文件整理。

构建19的原账户读取和可见历史已有独立回执。原密码表单实际提交、弹窗关闭与一次真实Claude任务保持未完成验收；模型调用0次。后续后台设备通道的状态归[完整执行记录](../../../../../docs/exec/mobile-app-design-review-20261024.md#后台采证约束更新)，本包保存AppleScript阶段原始资格。
