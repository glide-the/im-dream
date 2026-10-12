<!-- [Input] User authorization to implement the sketch input design and repository gates. -->
<!-- [Output] Scope, design review, impact assessment and this-run verification receipts. -->
<!-- [Pos] Chat sketch-input implementation execution record. -->
<!-- [Sync] 2026-10-09: record plan before product implementation. -->

# 绘制草图实施记录

## Optimized Prompt

实现 Ink & Memory 的独立手绘输入：用户从 Chat 添加菜单打开画布，绘制/擦除/撤销/重做/清空，完成后将 PNG 加入当前消息，复用文件上传、授权与发送路径。先补齐业务 PRD 和含三类 Mermaid 的正式稿，独立评审可实施后再写代码。保持双钻石的问题收敛，功能模块以用户目的描述。只修改画布、输入框接入、文案、对应文档与隔离测试；不实现 AI 图像生成、Gateway 图片透传、Admin 模型中心，不改变 Schema、Runtime、线程、流式或取消语义。保护现有未提交内容。由 luna_test_runner 执行确定性、隔离浏览器与文档检查，等待回执、修正问题并重验；明确与真实业务验收的差别。

## 计划与目标

当前 IM Codex 任务继续执行，无重复创建。目标已自动设置：交付手绘草图输入、现行文档、独立评审及完整范围的本轮隔离验证。阶段：目的/证据和设计 → 独立实际稿评审 → 代码 → Luna 本轮验证与修订。

## 影响评估

| 范围 | 本次影响 / 验证 |
| --- | --- |
| 用户入口 | 添加按钮变成两项菜单；键盘、旧文件选择回归 |
| Agent/Tool | 无新执行通路；不进行模型调用 |
| 消息/事件 | 沿用 UploadedFile/toAttachment；发送失败恢复与文本兼容 |
| 前端 | 新画布、操作历史、PNG 与窄屏/深色；完整操作旅程 |
| 文件权限 | 同一上传 hook；HTTP 权限/网络失败注入，真实服务权限未验 |
| 持久化 | 既有图片消息；前端只保留局部草稿，不新增数据库能力 |
| 失败/取消/重试 | 返回保留、空白不添加、上传重试、发送恢复；原 Stop 不改 |

## 状态

设计初稿已保存并经独立评审。首轮发现非白像素判空、暂存/消息保存边界、onAdd返回合同三处缺口，已按 RGB<255 判墨迹、发送后消息保存、Promise<boolean> 修订，独立复审结论为可实施、无阻塞项。frontend-design 产物为现行 PRD 骨架、正式稿和复用现有主题的局部画布。代码已实现，Luna 本轮完整隔离旅程与相关静态检查已通过，收尾文档复验已通过，本轮交付完成，自动关闭 Codex 目标。无部署、无正常业务数据库写入。

## 源码证据保留

本轮恢复安装包静态证据至 `frontend/output/codex-sketch-source-20261009/`。版本 26.1007.21159；app-primary SHA256 `2eaf8f70d72dc2beea9ca16b954b2efcbebebd8e59f823fbde5e75cdeb655756`；composer-state SHA256 `c918713686c99454ff0ad4972eec055c72901d206dbf4d556d68cc4eb7e27aa2`。原 `test-results` 下的本地摘要在浏览器默认输出清理后缺失，后续验证采用独立 `output/sketch-input-20261009`，避免继续清理其他产物。此摘要仅证明安装包源码，不证明当前客户端界面实际点击。

## 本轮失败与修正（保留）

- 初轮类型检查与局部 lint 退出 0，旧输入框 5 例通过；新 4 例未能初始化测试页面。诊断证明 API fixture 的 `**/api/**` 误拦 `/app/_dream/api/*.ts` 源模块并返回 501。修正为只处理 pathname 以 `/api/` 开头的公开接口，其余正常加载。没有修改产品来迎合测试。
- 修正后 9 例得到 7 通过、2 失败（退出 1）：添加状态定位与测试 output 的默认 status 冲突；Workspace 旅程缺少现有 Thread 插件回执只读 DTO。限定弹窗状态并补齐现行 DTO，保留未知请求必须为零的断言；全量 fixed2 重验已获 9/9 通过。
- Mermaid 首次 Node 解析受 DOMPurify 浏览器依赖影响；改为真实 Chrome 渲染后脚本注入前置失败。最终浏览器脚本已渲染 3/3 SVG（退出 0）。图示代码无需绕开语法校验。
- 代码复核增加局部 Portal 粘贴/拖拽隔离，避免画布操作触发底层附件上传；加入对应测试。PNG 验证同时检查 MIME、尺寸和解码后的墨迹，不能仅靠图片文件存在判成功。

## 本轮验证回执

执行者：当前任务的 `luna_test_runner` 子 Agent `image_comparison_validation`。以下命令 cwd 为 `frontend/`（diff 为仓库根目录）；全部是本轮回执。

| 命令 | 退出码 | 关键结果与覆盖 |
| --- | --- | --- |
| `pnpm exec tsc --noEmit --incremental false` | 0 | 整个生产前端 TypeScript 检查；`tsc-final2.out` 无错误。 |
| `pnpm exec eslint app/_dream/components/chat/SketchInputDialog.tsx app/_dream/components/chat/sketchDrawing.ts app/_dream/components/chat/AIInputDock.tsx app/_dream/i18n.ts e2e/sketch-input.spec.ts` | 0 | 5 个修改/新增 TS 文件；`eslint-fixed2.out` 无错误。 |
| `pnpm exec playwright test e2e/sketch-input.spec.ts app/_dream/components/chat/__tests__/AIInputDockSlashMenuRegression.test.ts --workers=1 --reporter=line --output=output/sketch-input-20261009/browser-fixed2` | 0 | **9 passed (10.8s)**：4 个草图完整旅程和5个原有 slash/Send/Stop 回归。 |
| `python3 output/sketch-input-20261009/check-docs.py` | 0 | 收尾稿复验：12 文件、101 本地链接、3 Mermaid 块、0 errors；包含根目录合同、新源文件/文档 owner 登记和完整需求追踪。 |
| `node output/sketch-input-20261009/render-mermaid.mjs` | 0 | 真实本机 Chrome 渲染 3/3 SVG；脚本/Vite 自有资源关闭。 |
| `git diff --check -- <本轮修改文件清单>` | 0 | 无空白错误；完整 argv 在本机 `frontend/output/sketch-input-20261009/commands.json`。 |

完整浏览器覆盖：空白禁用、绘制、局部擦除至空白、撤销/重做、重做分支替换、清空/撤销、返回继续、触摸、上传进行中不可重复添加、PNG 真实解码墨迹一致、403/断网/JSON解析失败重试、导出失败保留、Workspace 开/关路径及元数据、草图移除、旧文件选择、文字/图片 DTO、发送拒绝恢复、中文/英文、360px 深色、焦点恢复与 Escape、IME/Enter/换行/运行中队列及 Send/Stop。图片通过原 `FileMessagePart` 消费展示。

主执行者已查看本轮窄屏深色截图，工具、画布、错误区和操作符合 PRD 的页面骨架。没有扩展为图层、作品库、矢量持久化或新模型通道，过度设计评审结论为无须新增这些能力。

## 验证边界与发布条件

本轮完成的是代码实现、独立设计评审、文档检查和 Provider-free 技术验证。未执行真实账户/模型验收、正常数据库消息持久化和重开、正常服务文件权限验收或 S3 直传。注入边界仅位于 `frontend/e2e`，生产模块无测试环境分支。编辑笔画没有跨刷新或跨会话保存能力；已发送 PNG 继续依赖现有消息历史。

本轮未部署或重启用户服务。发布前仍需按 `Agent.md` §8，在目标 topology、用户指定真实账户和正常 Admin/Gateway/PostgreSQL 上完成完整发送入口与 SSE 门禁；隔离浏览器通过不代替这一条件。选中模型能否理解 PNG，尤其 Gateway Responses 的图片透传，是另一个已有集成边界，不因新增草图入口而视为解决。

仅本轮具名 Chrome profile、Vite 和测试进程被关闭，未操作数据库或业务资源。保留 raw stdout/exit、失败诊断、成功截图、SVG 和命令清单于 `frontend/output/sketch-input-20261009/` 供复核。

收尾回执：Luna 最终文档与包含根 `.folder.md` 的 scoped diff 均退出 0；7 个受影响源码 SHA256 保存在本机 `frontend/output/sketch-input-20261009/source-hashes-closure.txt`。收尾阶段无源码变动、无需重复已通过的 9 例。Codex 当前任务的手绘输入交付完成；部署/真实业务验收仍未执行。

## 2026-10-10 主对话与图片工具合并交付

上方回执和边界保留为 2026-10-09 历史。主对话的 Gateway 图片转换及独立 Images 工具现已有源码，草图 PNG 的上下文/参考URI到编辑连接测试已补充；本轮重新执行全部相关技术检查和图示检查，实际命令与最终状态见[合并交付记录](chat-image-sketch-delivery-20261010.md)。真实模型理解与正常数据库验收仍未执行。关闭 Workspace Mode 时原Router不会将PNG构造为视觉块；本轮没有自动开启工作区。
