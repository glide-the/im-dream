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
