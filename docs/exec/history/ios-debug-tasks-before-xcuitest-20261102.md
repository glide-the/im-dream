<!-- [Input] frontend/e2e/ios/tasks整理前的十份文件及SHA256清单。 -->
<!-- [Output] 原文快照、私有归档位置与迁移说明。 -->
<!-- [Pos] AppleScript任务归档的历史记录；现行目录只记录XCUITest E2E。 -->
<!-- [Sync] 2026-11-02: 用户要求删除任务目录旧内容，核验归档后移除；原文保留。 -->

# iOS调试任务整理前原文

## 归档与迁移

原目录为`frontend/e2e/ios/tasks/`。本轮按用户要求清理该目录；现行[XCUITest任务索引](../../../frontend/e2e/ios/tasks/README.md)保存UI自动化任务。下方五份Markdown以原文快照保存，原相对路径按历史位置解释。原AppleScript、JSON、摘要和ZIP保留于私有完整归档，原脚本执行次数为0。

完整归档：`frontend/ios/build/ios-debug-docs-20261102/tasks-before-xcuitest.tar.gz`，Git忽略。摘要清单：同目录`tasks-before-xcuitest.manifest.json`。这两份文件用于本机恢复，Git历史保留原已跟踪文件。

归档SHA256：`070c0bd34c77e03481c91e5935e24c94ada1da6c4cf6012c5327c114ace56aee`。归档内十份文件已逐份与源SHA256匹配，完成匹配后才删除源文件。

| 原路径 | 字节数 | SHA256 |
| --- | --- | --- |
| `.folder.md` | 1146 | `17b62dde55eedbd6318e673992a262395d7ce8de78d549ed060556f96fbd952a` |
| `.gitignore` | 310 | `c43cb897623a63b86cd96fb1dfde6b80aadccdcd6343fb2cb02cd58e5b4698a5` |
| `README.md` | 1229 | `c62d3bbe18dc4807363525ab00217c18d6a143d237425ea9397d15d54f1b6c9f` |
| `iphone-503-20261031.zip` | 8210 | `5a0560d75661ccf604b6612dfcf9144442869a96157a3e1d12769f031ec0c5f9` |
| `iphone-503-20261031/.folder.md` | 1007 | `a86eff84f6fa1c11705c0754d29b4b05fc46fab0e031ae7c4dd0c6bf240a7433` |
| `iphone-503-20261031/MANIFEST.sha256` | 413 | `7432531439714c25451c118a924fff78d3e87747be696cda362a471a74d25625` |
| `iphone-503-20261031/OPERATIONS.md` | 6738 | `0390bf7c767867e7f270fce73ee14bbf504d8747f9cdd4384f3e5aa58133af5e` |
| `iphone-503-20261031/README.md` | 3051 | `c8bcb2e5814b17a6f7c2dfd8eee8ceebfd96b6d66a7e138ab02df99a0600aace` |
| `iphone-503-20261031/mirror-click.original.applescript` | 1613 | `75ea550295ecd15cb6c897aa1b6923c5ce87076ba43ca8c50e89e5153b53e183` |
| `iphone-503-20261031/receipts.json` | 3762 | `9c121dd24168d844347d3111adce1eb9a6efaaa7dc9a76d9e66aeeab33a2e1f1` |

## 原文：.folder.md

``````text
<!-- [Input] 按业务任务保存的iOS端侧操作过程、历史脚本及脱敏回执。 -->
<!-- [Output] 独立任务目录、任务清单和同名ZIP生成物的归属。 -->
<!-- [Pos] frontend/e2e/ios/tasks任务归档合同；实际业务资格由各任务记录持有。 -->
<!-- [Sync] 2026-11-01: 归档iPhone503任务的AppleScript与OSA JavaScript操作过程。 -->

# iOS任务归档

每项业务任务使用独立目录；目录保存目标、操作过程、脚本、回执和摘要清单，同名ZIP保存该目录的一份副本。操作步骤归属于对应业务任务。

| 文件或目录 | 职责 |
| --- | --- |
| `README.md` | 任务清单、归档方式与执行状态 |
| `.gitignore` | 忽略可从任务目录生成的同名ZIP |
| `iphone-503-20261031/` | iPhone503任务的历史AppleScript操作、失败与未验收项 |
| `*.zip` | 按任务生成的分发副本，内容由该任务摘要清单核对 |

任务包属于验证与执行记录。脚本编译、命令退出、界面反馈和真实业务结果分别登记。当前桌面操作保持停止，整理任务包只执行文件读写和静态检查。
``````

## 原文：README.md

``````text
<!-- [Input] iOS各业务任务的操作过程、源脚本和回执。 -->
<!-- [Output] 一项任务一个目录及一个同名ZIP的访问入口。 -->
<!-- [Pos] frontend/e2e/ios任务包索引。 -->
<!-- [Sync] 2026-11-01: 新增iPhone503的AppleScript过程包，保留实际失败及桌面停止状态。 -->

# iOS任务包

按业务任务分别归档。目录名使用任务名称和原操作日期；整理日期记录在任务正文。任务目录进入源码管理，同级ZIP为生成副本。

| 任务 | 操作日期 | 内容 | 当前状态 |
| --- | --- | --- | --- |
| [iPhone503](iphone-503-20261031/README.md) | 2026-10-31 | AppleScript窗口检查、点击尝试、OSA JavaScript补充、原始脚本及脱敏结果 | 过程已归档；点击效果未取得成功回执；完整真机业务继续待验收 |

每份任务包直接包含操作过程、脚本、回执、文件清单和SHA256摘要。步骤记录语言、目标、输入、命令退出与实际效果。账户凭据、Cookie、授权数据、业务正文和完整桌面截图退出归档。

当前用户要求停止镜像和桌面输入。任务包整理与编译检查沿该边界执行；后续界面执行按当时的任务范围处理。
``````

## 原文：iphone-503-20261031/.folder.md

``````text
<!-- [Input] iPhone503任务中已执行的AppleScript和OSA JavaScript尝试。 -->
<!-- [Output] 原脚本、逐步操作、脱敏回执及任务摘要清单。 -->
<!-- [Pos] iPhone503任务包文件合同；脚本保留原阶段内容。 -->
<!-- [Sync] 2026-11-01: 将原build私有目录中的脚本及会话操作过程归档到E2E任务目录。 -->

# iPhone503任务包

| 文件 | 职责 |
| --- | --- |
| `README.md` | 任务目标、归档范围、执行资格与访问入口 |
| `OPERATIONS.md` | 按操作项保存命令、输入、返回、界面观察与失败处理 |
| `mirror-click.original.applescript` | 原窗口定位与坐标点击脚本的逐字节副本 |
| `receipts.json` | 脱敏操作结果与任务完成状态 |
| `MANIFEST.sha256` | 本目录五份来源文件的SHA256摘要 |

原始脚本的Input/Output/Pos头保留原文，其当前归档状态由本目录合同及README定义。ZIP包含本表五份文件和MANIFEST.sha256；摘要清单自身退出摘要条目。
``````

## 原文：iphone-503-20261031/OPERATIONS.md

``````text
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
``````

## 原文：iphone-503-20261031/README.md

``````text
<!-- [Input] 2026-10-31 iPhone503任务中的桌面操作记录及原始AppleScript。 -->
<!-- [Output] 独立任务包、操作过程、失败回执与未完成业务资格。 -->
<!-- [Pos] iPhone503的AppleScript过程归档；完整网络修复及设备回执归原执行记录。 -->
<!-- [Sync] 2026-11-01: 首次打包，保留原脚本字节与实际操作结果，桌面执行继续停止。 -->

# iPhone503：AppleScript操作过程

原操作日期：2026-10-31。整理日期：2026-11-01。

任务目标为在同一iPhone的原App中恢复登录、配置、历史及一次真实Claude任务。此包记录其中的系统脚本操作过程；[完整执行记录](../../../../../docs/exec/mobile-app-design-review-20261024.md#2026-10-31-iphone-503定向采证与修复)持有网络定位、构建19及HTTP回执。

## 文件入口

- [操作过程](OPERATIONS.md)：窗口检查、坐标点击、窗口恢复、实际结果和停止条件。
- [原始AppleScript](mirror-click.original.applescript)：从原生成物目录逐字节复制。
- [脱敏回执](receipts.json)：按操作项登记命令退出与业务效果。
- [文件摘要](MANIFEST.sha256)：核对源文件及ZIP内容。
- [任务ZIP](../iphone-503-20261031.zip)：本目录的一份分发副本。

## 范围与状态

AppleScript承担窗口定位与点击尝试。`osascript -l JavaScript`执行的代码标注为OSA JavaScript，两种语言分别记录。原脚本、直接命令、界面观察和失败按实际来源保留。

| 验证层级 | 结果 |
| --- | --- |
| AppleScript窗口信息读取 | 曾返回位置1045,38及尺寸314,699；后续读取返回窗口数0 |
| 点击命令退出 | 原脚本及部分OSA JavaScript命令退出0 |
| 点击业务效果 | 页面未观察到目标变化，点击成功资格未取得 |
| 原账户读取与历史 | 构建19原会话、配置、历史200，原页面曾显示历史及完全访问；资格归原任务回执 |
| 原密码表单、弹窗关闭 | 未完成验收 |
| 本轮真实模型任务 | 调用0次，未完成验收 |
| 当前桌面操作 | 用户要求停止镜像、窗口和键鼠操作；本轮整理保持停止 |

任务包排除登录凭据、Cookie、Bearer、授权码、PKCE、业务正文、桌面截图和全量进程清单。账号授权及原业务状态继续由原任务持有。

## 阅读与验证方式

先阅读操作过程和回执，再按MANIFEST.sha256核对文件。原坐标仅用于说明历史输入，后续操作需要重新取得截图、窗口和目标区域。

静态编译使用独立输出路径：

```sh
: "${TASK_VALIDATION_DIR:?指定本轮可删除的验证输出目录}"
osacompile -o "$TASK_VALIDATION_DIR/mirror-click.scpt" frontend/e2e/ios/tasks/iphone-503-20261031/mirror-click.original.applescript
```

`TASK_VALIDATION_DIR`由验证调用方指向本轮可删除的生成物目录。该命令只编译脚本；窗口访问、点击、登录和模型均退出本轮整理的执行范围。编译结果、ZIP完整性和业务验收分别登记。
``````
