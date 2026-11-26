<!-- [Input] 用户的中文字体／布局反馈、参考菜单截图及删除独立资源导航的要求。 -->
<!-- [Output] 局部修复范围、前后截图、当前验证回执与验收边界。 -->
<!-- [Pos] 中文Chat菜单与工作台导航修订执行记录；原Thread工具及历史回执保持。 -->

# 中文Chat菜单与工作台导航修订

## 执行范围与判断

复用当前Thread工具候选，实现中文菜单的字体、字号、行高、图标、开关、截断及滚动修复。删除工作台侧栏和更多菜单的独立资源入口，保留设置内资源管理、原路由与内部管理意图。现有Agent目录、模型偏好、Thread选择、消息DTO、权限及音频问答规则保持；真实账户、模型、MCP、数据库、依赖、提交、推送和部署退出本轮范围。

发现：正常Chat输入栏继承手绘内容字体，Portal继承页面UI字体；服务名使用默认粗体，Agent与模型字号偏小，字形箭头随字体变化。长中文触发器可将附件和Agent挤成两行；级联子菜单先按未受约束的高度定位，较窄桌面存在父子面板重叠。Native标签使用分段手绘字形，搜索框使用系统字体。

选定复用现有`--font-family-ui`与原生Text界面字体，仅修改菜单和输入栏操作行。标题、分组、选项、辅助文字采用明确层级；图标和开关保持固定占位。内容编辑器及全局字体继续由原组件管理。

## 交付物

- Web统一Agent／模型触发器与Portal字体；菜单正文14px／22px，标题16px／24px，辅助文字12px／20px。服务名400字重、标题600、分组500。
- 复用原SVG箭头、关闭和勾选；服务开关44px操作范围，名称单行截断；Agent列表单独滚动，搜索与返回可达。768px桌面校验父子菜单分列与视口边界。
- Native菜单局部使用Text／TextInput；开关采用独立轨道，正文、输入文档与其他InkLabel组件保持原所有权。Native证据使用React Native Web。
- 输入栏附件、Agent、模型与发送／停止保持同排，长名称在各自区域内收缩。
- `StoryWorkspaceSidebar`移除独立资源按钮，资源深链选中“设置”；两端“更多”保留写作、时间线、回顾、主题、设置五项。
- 保留`/story-workspace/settings/resources`与Settings内连接管理；Native的`resourceRequestNonce/onResources`沿原Settings所有者处理内部资源意图。

## 截图与证据

截图采用合成中文目录、原App字体文件与生产ChatView／Router；每项按相同用户操作打开菜单、角色列表和模型选择器。浏览器页面使用本轮随机端口；Native使用显式平台与配色边界。

修复前Web截图位于`frontend/output/chat-composer-zh-20261113/before/browser/`，包含1200px／390px、明暗主题。Native有效配色基线位于`before-native-theme/browser/`；早期两轮Native基线记录了夹具的配色参数缺失，诊断证据分别保留于`before/`和`before-native/`。

修复后截图、字体测量与最终命令回执由`frontend/output/chat-composer-zh-20261113/final-browser/`保存。首轮29项通过后，视觉复核补充了768px级联不重叠、初始高度定位，以及Native动画结束后首个开关可见的断言；当前交付采用最后截图。

## 验证范围

原有输入栏5项回归、正常Chat首次／后续消息2项，以及导航13项已按本轮实际源码执行。两端类型检查沿完整工程运行。中文最终矩阵包含1200px／768px／390px的明暗主题和390px Native明暗主题；当前结果与命令按最终回执登记。

版本化截图位于`assets/chat-composer-20261113/`；其余`frontend/output/`路径指向本机保留的命令日志与过程证据。

有效用例集合为8项中文、18项原工具／模型、5项原输入栏、2项正常Chat发送及13项导航，共46项。重复执行按同一用例记录，计数采用最后覆盖各用例的回执。

| 命令（前端工作目录） | 退出码 | 结果 |
| --- | --- | --- |
| `pnpm exec tsc --noEmit --incremental false --pretty false` | 0 | 最后级联定位修订后Web完整类型检查通过 |
| `pnpm native:typecheck` | 0 | Native完整类型检查通过；随后修订限定Web级联定位 |
| `pnpm exec playwright test --config=e2e/chat-tools.config.ts e2e/chat-composer-zh.spec.ts e2e/chat-tools.spec.ts --output=output/chat-composer-zh-20261113/delivery/browser` | 0 | 26项通过，26.3秒；8项中文最终矩阵与18项工具／模型回归 |
| `pnpm exec playwright test --config=e2e/chat-tools.config.ts e2e/chat-composer-zh.spec.ts e2e/chat-tools.spec.ts app/_dream/components/chat/__tests__/AIInputDockSlashMenuRegression.test.ts --output=output/chat-composer-zh-20261113/after/browser` | 0 | 初轮29项，包含5项原输入栏回归；中文及工具当前结果采用最终26项回执 |
| `pnpm exec playwright test --config=e2e/chat-tools.config.ts e2e/chat-route-cache.spec.ts --grep 'normal Chat wires Agent' --output=output/chat-composer-zh-20261113/normal-route/browser` | 0 | 正常Chat首次／后续tools请求2项通过，11.4秒 |
| `INK_MORE_EVIDENCE_DIR=output/chat-composer-zh-20261113/navigation-final/screenshots pnpm exec playwright test --config=e2e/chat-tools.config.ts e2e/more-navigation.spec.ts e2e/native-more-navigation.spec.ts --output=output/chat-composer-zh-20261113/navigation-final/browser` | 0 | 13项通过，18.4秒；五项菜单、资源入口移除、设置选中态及内部资源intent |

原始命令和日志见[中文与工具最终回执](../../frontend/output/chat-composer-zh-20261113/delivery/validation-receipt.md)、[Native类型及输入栏回执](../../frontend/output/chat-composer-zh-20261113/after/validation-receipt.md)、[正常Chat回执](../../frontend/output/chat-composer-zh-20261113/normal-route/validation-receipt.md)和[导航回执](../../frontend/output/chat-composer-zh-20261113/navigation-final/validation-receipt.md)。范围静态检查使用`frontend/output/chat-composer-zh-20261113/files.json`登记的37个路径；文档检查入口为`node frontend/output/chat-composer-zh-20261113/checks/check-docs.mjs`。

| 场景 | 修复前 | 修复后 |
| --- | --- | --- |
| 桌面中文级联，深色 | [1200px](assets/chat-composer-20261113/desktop-before.png) | [1200px](assets/chat-composer-20261113/desktop-after.png) |
| 窄屏中文模型，浅色 | [390px](assets/chat-composer-20261113/narrow-model-before.png) | [390px](assets/chat-composer-20261113/narrow-model-after.png) |
| Native工具，深色，RNW | [390px](assets/chat-composer-20261113/native-before.png) | [390px](assets/chat-composer-20261113/native-after.png) |

修复后768px、390px与1200px的浅色／深色菜单、角色列表、模型面板均分别留图。768px键盘收起再展开曾出现父子菜单位置竞态，已增加父面板位置观察和重新展开后的不重叠断言；诊断截图保留于`final-browser/`。

导航首轮新断言将设置按钮限定在侧栏内部的navigation节点，实际按钮由footer持有；修订测试定位后13项通过。生产资源路由的设置选中态保持完整断言，原失败日志保留。

本轮为隔离技术与视觉验证。Native浏览器渲染覆盖局部文字和布局；iOS／Android真机、系统键盘与辅助功能、真实账户／模型／MCP、原生音频播放、后台持续计算和发布均未执行。当前运行服务、数据、认证与其他未提交改动保持。
