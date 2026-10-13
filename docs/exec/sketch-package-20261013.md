<!-- [Input] Original task, readonly CharcoalNarrative source, existing Chat sketch/upload production path. -->
<!-- [Output] Selected migration scope, design review, impact assessment and fresh validation receipts. -->
<!-- [Pos] Second-task sketch component package delivery record. -->
<!-- [Sync] 2026-10-13: source UI restored, 29 technical journeys/build passed; normal image persisted, extra model request rejected separately. -->

# 图片与草图组件迁移

## 优化提示词与执行计划

在本聊天完成第二项任务。只读评估 CharcoalNarrative 的炭笔、擦除、视图变换及分层合成，抽取适用于 Chat 图片输入的能力；目标为一个 pnpm workspace 包，包内按画布、图片输入、历史和 React 界面分模块。复用 Chat Modal、国际化、Cookie/CSRF 上传及消息 DTO，不移入来源项目的故事、年代、全局 store 或模拟 AI 功能。补齐本地图片导入描画，保持关闭保留草稿、添加成功清空、失败保留并重试。先完成发现、定义、方案比较和范围评审，再更新 PRD/设计并实现。技术验证由 Luna 执行完整组件旅程和相关回归；正常账户验证由主 Agent 使用现有账户和会话执行，不以注入事件冒充真实业务，不调用与组件验收无关的模型。保留参考项目与其他本地改动，完成后报告可复核结果，不请求阶段确认。

计划：源码评估与设计收敛 → 组件包及 Chat 接入 → 完整技术流程与布局验证 → 正常入口复核、文档同步及交付。目标已在本聊天设置；没有另建聊天。

## Double Diamond 与范围评审（首次选型，后文已修订）

发现：当前 Chat 已有 `SketchInputDialog`、操作历史、白底 PNG 和完整 `handleFiles` 通路。参考目录的 `CanvasManager.ts` 包含颗粒炭笔、透明擦除、变换后的坐标映射；`CharcoalScene.tsx` 有两层合成。该目录没有文件上传控件，`index.tsx` 的模型生成被注释并以计时器模拟。不能把整个故事应用搬入 Chat 或把模拟结果称为生成。

定义：缺少的是可维护的组件包及图片导入描画，不是新的上传、Agent 或图片模型架构。公开输入为本地 File 和受控草稿，公开输出为白底 PNG File；应用继续拥有真实上传与发送。

比较：整套移植会带入来源项目 store、年代/故事常量与无效 AI；仅搬旧代码不复用指定来源能力，也不支持图片描画。选择一个 `@ink-dream/sketch-input` 包：复用炭笔算法和分层合成，随机颗粒改为笔画 seed 的确定性重放，沿用旧操作历史；图片层不被橡皮破坏。保留画笔、橡皮大小、撤销/重做/清空和视图缩放/移动，排除作品管理、年代、叙事、AI 假进度、额外包和后端入口。

评审：包不反向导入应用源码，所有文案/最大文件大小由宿主输入；Modal 和授权在宿主。添加只上传，不发送；解码失败不修改草稿，返回取消解码，上传失败保留草稿；PNG 不包含视图缩放/移动。一个生产组件路径替换旧绘图实现。设计与图示分别由 [PRD](../prd/chat/sketch-input.md) 和 [正式设计](../design/claude-agent/sketch-input-interaction-design.md) 所有。

## 测试影响评估

| 事实与来源 | 写入/同步 owner | 最终消费者 | 本轮影响 |
| --- | --- | --- | --- |
| 本地图片与草稿 | SketchEditor / 受控 SketchDocument | Canvas、PNG、待发送附件 | 改变：炭笔、图片导入、视图操作 |
| Thread 与 CLI session | ChatView / ClaudeAgentService | Chat 历史 | 必须保持原标识与协议 |
| storage / workspace 文件 | 原 handleFiles、useFileUpload、workspace API | 附件及消息图片 | 仅用户添加时发生既有写入 |
| Project / Episode / canonical Artifact | 原 Agent / successful Hook | Story/Execution 页面 | 不在范围；本轮不请求故事修改 |
| Run-private .dream publication / PostgreSQL projection | 原 after-turn Hook / Admin | 原业务页面 | 不改结构、同步 owner 或授权 |
| 消息 DTO、slash、Send/Stop | 原 AIInputDock 与 transport | Chat | 必须保持现有行为 |

技术测试：绘制→擦除→历史→关闭重开→导入/替换图片→描画→PNG 上传→发送 DTO→下游图片；非法/损坏图片、导出/上传/发送失败恢复；缩放/移动不改输出，触摸、取消 pointer、窄屏/短屏、中文/英文、深色/浅色、键盘、原上传入口。生产构建和包解析单独检查。真实正常账户验证只走公开 UI，模型调用计划为 0；组件无需推理就能验证图片上传和下游可见消费。若确需验证模型理解，须另记明确模型与次数，不能将组件旅程结论扩大到推理。

## 验证回执

第一版及纠正后的原始回执分别保留，不将旧界面通过当作当前版本通过。最终结果见文末；技术流程与正常账户结果分开列出。


## 正常业务复核计划补充

用户最新明确要求完成第二个组件任务；本轮直接推进，不继续套用第一项未发生实际自动压缩的旧等待门槛，也不把该缺口宣称为已经通过。

优化提示词：保留已通过的27项技术流程及单包边界，通过既有正常Chrome会话核对指定真实账户，选择原有Thread与gpt-6.1-sol。正常用户从添加菜单导入本轮自有测试图片、描画并添加，沿原upload与发送入口发送一条自然语言读图请求，核对可见回复、真实图片、刷新/历史和正常Admin回执。最多一次模型调用，不调用图像生成，不更改配置/数据库/其他业务实体，保留正常记录；技术故障注入结论不扩大为真实模型结论。相较原0调用组件验证计划，仅补一条发送以证明正常消息下游，其他技术场景不调用模型。

正常账户：dmeck@suoxya.com，沿上一轮Chrome受权会话；用户菜单实际显示该身份，未再次输入或保存密码。原服务3000/8765继续运行，Next已在原5173运行；本轮未停止或重启其他服务。浏览器沿已使用的chrome-dev:boss-delivery控制通道，不更换账户/浏览器或注入认证。


## 用户纠正：完整保留原组件交互

用户指出当前界面与原组件不一致。第一版仅抽取炭笔和图片合成、保留旧Modal工具栏，未完整迁移原组件的视觉结构与图层/快照历史；该选型不满足用户要求，27项技术通过与build成功仅属于第一版，不代表纠正后的交付完成。真实流程仅完成账户/模型/原会话核对和本地图片读取，尚未上传或发送，模型调用数0。本轮自有未发送草稿已清空，不修改历史消息或服务。

优化提示词：按用户纠正将CharcoalNarrative作为一个完整的可复用画布组件迁移，保持原纸张画布、左上标识、右上悬浮工具栏、图层/擦除目标工具箱、左侧纸片快照历史和视图交互；包内部模块化，宿主只适配Modal、i18n、草稿寿命和原上传回调。不再把UI重写成旧表单。原组件与图片/草图相关的真实工具必须可用；来源已停用的模拟AI/故事功能不产生假结果。保留已完成核心的确定性重放与PNG输出，补图层可见性、图片层擦除和快照恢复；正常与异常图、双屏骨架及评审同步。修订后重新执行完整相关旅程和生产构建，再做实际正常入口复核；不请求用户决策。

修订计划：补齐原组件布局/工具箱/历史边栏 → 更新当前PRD与正式图示 → 实现同包内部UI模块与图层渲染 → 完整复测及正常账户验证。保持一个package、一条上传/消息路径、只读来源和原20处其他改动。

## 当前组件交付与最终验证

当前选择为一个 `@ink-dream/sketch-input` 私有 workspace 包，内部包含 drawing/history/imageInput/gestures 和四个 React 界面模块。原纸张、悬浮玻璃工具栏、图层与擦除目标工具箱、纸片历史及笔/橡皮光标已接入真实 Chat；宿主仍负责 Modal、i18n、Thread 草稿寿命和原 `handleFiles`。图层隐藏禁止隐形绘制，清空历史保留两层像素作为可继续编辑的起点；关闭/恢复历史及 Escape 将焦点返回入口。原故事、年代和模拟 AI 未迁入。

修订后的 round4 已有 27 项通过。新增图层/时间线用例在 round5 把工具 SVG 的 `img` role 也计为历史缩略图，期望2、实际8；改为按 `Sketch fragments N` 名称检查恰好2张真实缩略图，round6完整旅程通过。没有删除后续像素、历史、擦除、上传/发送断言。随后补抽屉焦点恢复与断言，以当前最终代码执行 round7全套验证：

| 实际命令 | Exit | 关键结果 |
| --- | --- | --- |
| `corepack pnpm --dir frontend --filter @ink-dream/sketch-input typecheck` | 0 | 独立包类型通过 |
| `corepack pnpm --dir frontend exec tsc --noEmit --incremental false` | 0 | 前端类型通过，不写原 tsbuildinfo |
| `corepack pnpm --dir frontend exec eslint 'packages/sketch-input/src/*.ts' 'packages/sketch-input/src/*.tsx' app/_dream/components/chat/SketchInputDialog.tsx app/_dream/components/chat/AIInputDock.tsx app/_dream/i18n.ts e2e/sketch-input.spec.ts` | 0 | 包、薄适配、文案和测试均通过 |
| `corepack pnpm --dir frontend exec playwright test e2e/sketch-input.spec.ts app/_dream/components/chat/__tests__/AIInputDockSlashMenuRegression.test.ts app/_dream/components/chat/__tests__/SlashSkillCommands.test.ts app/_dream/components/chat/__tests__/ChatSubmissionStop.test.ts --reporter=line --workers=1 --output=/tmp/im-sketch-package-20261013/round7/results` | 0 | 29 passed，18.3s；9个草图完整旅程及20个既有slash/Send/Stop回归 |
| `NODE_ENV=production corepack pnpm run build`（本轮自有隔离构建 checkout） | 0 | Next16.1.6 webpack生产构建、类型及静态3/3通过；不写正常服务的 `.next` |
| 当前 Mermaid Chrome parser / 文档清单及hash checker | 0 | 正式设计3图解析通过；10个目录清单、19份Markdown及32个相对引用无缺失；20项原改动和13份来源源码hash保持不变 |
| `git diff --check` | 0 | 无空白错误 |

原始 [round7回执](/tmp/im-sketch-package-20261013/round7/receipt.md) 保留完整命令、退出码与失败记录。文档 checker 首次误写历史文件日期，exit1；改用实际 `20261009` 历史文件后 exit0。4份历史版本保留对应原文，当前规则/图示位于现行PRD与正式设计。主执行者查看了桌面、320×480短屏及窄屏历史截图；图层、纸片、工具、页内边界和底部操作可见。所有上述浏览器结果均为 Provider-free 技术验证，未写正常数据库或调用模型。

## 正常账户复核结果及模型边界

指定现有账户、原 Thread `27872a7b-1544-4742-9004-76995652a7c0` 和正常3000/5173/8765/PostgreSQL服务保持不变。通过公开 Chat 入口导入本轮自有参考图、真实指针描画、添加：原 workspace同步及 storage upload 均HTTP200；PNG为900×600、31027字节，storage key为 `uploads/fa38abd69d7a42c39b5e329f9c821db9-__.png`。上传成功后编辑草稿清空，重开为禁用添加/撤销的空白画布。

按补充计划发送一次 `gpt-6.1-sol` 读图请求，实际正常Admin模型请求只有1条：`req_827008b50d134b0d878842ec760c5db5`，2026-10-13 02:16:17北京时间，`settled/failed`、HTTP400、`UPSTREAM_REQUEST_REJECTED`，input/output tokens均0。正常页面显示消息处理未完成；未重试或更换模型/Provider，没有把此请求称为成功模型验收。正常SSE给出实际 turnId `d113052c-ecc0-4352-835d-2618a5394538` 和 error/finish(error)。模型提供方拒绝原因的更细分类没有取得；本轮不修改该组件边界之外的代理/模型合同。

原发送持久化了第81条用户输入和 PNG，刷新并重开同一会话后 `FileMessagePart` 仍显示相同storage图片，实际浏览器解码complete=true、900×600。该组件现有消费者为内联图片，不存在用户图片点击查看器；已按现行源码修正PRD/正常图。一次浏览器图片定位读取超时归为工具读取失败，随后使用同一浏览器的只读DOM检查取得图片尺寸，不判断为页面缺陷。

安全回执位于 `/tmp/im-sketch-package-20261013/normal/`：upload-receipt.json、history-receipt.json、admin-receipt.json和stream-metadata.json，仅保存本轮图片、业务标识、状态和实际用量，不保存密码、请求头或历史正文。正常消息、文件和失败请求保留供日常Admin/Chat复核。组件的本地编辑、输出、原上传、消息展示与历史范围已验证；此次额外模型读图输出失败单独保留，不构成组件逻辑的替代实现或通过证据。第一项真实自动压缩未观察到的旧缺口仍未被本轮宣称完成。

只清理本轮具名构建checkout及技术图示harness，不停止正常服务，不清理真实业务记录。所有提交外既有认证/README/缓存改动与参考项目保持原字节。

## 拉取请求与主分支收口

用户明确授权创建PR、合并到实际主分支并切换当前工作区。优化提示词：仅提交本轮草图组件、接入、测试和文档；保留20项既有认证/README/缓存改动，Admin仓库不在范围。GitHub确认Dream默认分支为develop，当前HEAD与origin/develop均为b75fdeb8。复用源码未变化后的29项回归、生产构建及文档回执，按仓库PR检查完成合并，然后读取MERGED状态与merge commit，切换develop并确认HEAD包含该提交。用户已要求停止3000及8765，两个端口均已释放，本步骤不重新启动正常服务或追加模型请求。

执行顺序：核对提交清单及原改动hash → 更新文档并检查 → 精确提交本轮文件、创建PR并检查 → 合并develop → fetch并切换/快进当前develop → 复核合并、分支、原改动和服务状态。实际PR链接和合并回执由本聊天最终结果及具名安全回执记录，不在合并前伪写已完成事实。
