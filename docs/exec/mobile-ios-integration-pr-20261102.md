<!-- [Input] 五个指定任务的最新回执、ios-native现有提交、当前源码与合并前验证。 -->
<!-- [Output] 移动端集成PR范围、任务追踪、验证证据与剩余验收。 -->
<!-- [Pos] 本次RN/iOS集成的项目执行记录；产品规则与交互由原业务文档维护。 -->
<!-- [Sync] 2026-11-02: 汇总启动观测、笔记关联对话、写作布局、ntn与Native Admin HTTP五项任务及文档迁移。 -->

# 移动端集成PR记录

## 需求范围

用户要求将五个指定任务写入PR，创建PR并合并到主分支，随后切换到主分支。GitHub仓库为`glide-the/im-dream`，本轮读取仓库元数据确认默认分支为`develop`。本次合并目标采用`develop`；`main`继续保持现有发布分支职责。

起始分支为`ios-native`，HEAD为`f40a9cfae8e85489a5354ccce7987f0a6a50f57d`，现有基础提交另含`b47e59d9`与`7f87eb2c`。这三项提交尚未进入默认分支，提供RN/RNW工程、iOS内嵌Python/Node/Claude及下表修复的依赖。本次集成沿这些提交推进，新增提交收录当前五项任务的关联改动与已授权的移动PRD迁移。工作区基线与本轮命令回执归`/tmp/ink-mobile-pr-20261102/`。

## 任务与交付追踪

| 指定任务 | 当前交付 | 现行文档与回执 | 剩余验收 |
| --- | --- | --- | --- |
| [设计移动端启动监测方案](codex://threads/01a196d5-0aed-72e0-b4aa-7963bd6450d8) | 原异步启动与共享Promise保留；准备页和关于页进入同一只读开发者页。展示启动/会话状态、总耗时及各来源最近一次原始错误；原文显示与复制沿用户补充要求。Next Worker错误沿既有私有通道传递，刷新只读取进程内状态 | [独立PRD](../prd/mobile-app/mobile-startup.md)、[正式交互](../design/multi-platform/mobile-startup-interaction.md)、[专项记录](mobile-startup-design-review-20261101.md) | 启动成功、真实端口占用错误、显示/复制及生命周期已有模拟器回执；完整真机页面、系统挂起、正常配置和目录读取继续验收 |
| [诊断端侧笔记对话切换问题](codex://threads/01a19582-ffee-77b0-8160-62abf77a478e) | 已有对话入口支持触屏；每次发送前取得并保存对应Writing Session快照，校验document/session/request及取消边界；拒绝切换后的迟到回执，失败保留输入。原Thread关联与普通Chat提交保持 | [写作交互](../design/multi-platform/writing-mobile-layout.md#写作记录与关联对话)、[修复记录](writing-linked-chat-fix-20261101.md) | 78项不同技术用例与A/B/A五次回执已有记录；真机可见A/B/A与真实模型上下文单独验收 |
| [设计评审移动端写作布局](codex://threads/01a19548-fa0a-73c0-926c-a50ece9b8df5) | 窄屏稿纸线沿文字行框重排，空输入使用单行；心情内容可触摸纵滚，入口归写作页头；选择后保持键盘关闭，桌面与原保存规则保持。包内Next采用源码来源检查 | [布局交互](../design/multi-platform/writing-mobile-layout.md)、[布局评审](writing-mobile-layout-review-20261101.md) | 真实Hermes/WKWebView模拟器交互及7项Web回归已有回执；物理设备、Android和系统字体缩放单独验收 |
| [修复iOS ntn检测与调用](codex://threads/01a19544-dbec-74c1-8e3b-f0c7f0e723ed) | 固定ntn随包分发；精确绑定的解释执行文件以可读性检测，继续包体摘要、私有Worker及路径/权限校验；区分缺失与执行失败。网页外链保留Linking接收者并交系统默认浏览器，保留原失败反馈 | [ntn记录](ios-notion-20261101.md)、[外链记录](ios-notion-links-20261101.md) | 构建21真机版本/帮助命令成功，资源读取401；构建22外链崩溃修复已安装。完整Notion授权与资源读取继续验收 |
| [iPhone 503与原认证链路修复](codex://threads/01a19241-da33-7133-91e3-b8fc1e9edb9c) | 请求阶段诊断；失败的Native Admin HTTP连接池退役；响应头和正文尚未接收时，对固定只读操作在原期限内进行一次恢复；原密码网页登录、Client/PKCE、Cookie/CSRF、权限、写入及任务语义保持 | [集成执行记录](mobile-app-design-review-20261024.md)、[认证排障](../deploy/mobile-auth-troubleshooting.md) | 构建20真机原协议登录、配置、历史及唯一真实任务completed并持久化结算；物理链路根因、可见登录弹窗/历史/回复与诱导网络恢复单独验收 |

## 当前设备与发布状态

截至2026-11-02最新任务回执，构建`0.1.0 (24)`已覆盖安装到原iPhone并普通启动；安装与启动退出0，原2161项数据目录元数据保持。11月1日构建24首次安装连接中断的记录完整保留，11月2日重连安装回执独立追加。

本次PR合并整理不操作设备、不重新签名、不调用真实模型、不维护账号或数据库。构建20的真实协议/模型回执、构建22/23/24的安装回执、模拟器页面验证及本轮技术检查各按对应版本和范围记录。TestFlight、App Store与Android安装发布尚待对应任务。

设备构建、摘要、签名与安装命令归[真机安装记录](../deploy/ios-iphone-install-release.md#2026-11-02-构建24覆盖安装与普通启动)。

## 文档与工作区维护

移动应用PRD已迁至[移动应用目录](../prd/mobile-app/mobile-app.md)，旧`docs/prd/dream-workspace/mobile-app.md`保留53个原章节入口；产品规则及桌面/窄屏骨架继续归PRD，架构、正常/异常时序与状态图归`docs/design/multi-platform/`。独立启动需求和设计沿各自文件维护，历史快照及历史命令保留原文。

提交范围按当前文件清单显式选择，保留原有未提交内容。源env、证书、签名材料、安装包与ignored构建资源进入Git的数量为0；未使用reset、stash、卸载或数据清理。

## 本轮合并前检查

本轮复用各任务已保留的历史验收，另对当前集成候选执行类型、合成后端/Node合同、浏览器交互、文档和隔离Next构建。原始证据归`/tmp/ink-mobile-pr-20261102/validation/`，下表记录当前集成候选的实际结果。

| 检查 | 命令/范围 | 结果 |
| --- | --- | --- |
| Web类型 | `pnpm exec tsc --noEmit --pretty false --incremental false` | 退出0 |
| Native类型 | `pnpm run native:typecheck` | 退出0 |
| 后端合同 | `cd backend`后使用`PYTHONPATH=. .venv/bin/python -m pytest -q`运行五个指定规格 | 退出0，31项通过；首两次命令的目录/导入路径前置失败单独保留 |
| Node合同 | `check-admin-http.mjs`、`check-host-auth-env.mjs`、`check-notion-staging-paths.mjs` | 均退出0，分别8/22/5项通过；网络请求与凭证使用为0 |
| 浏览器技术回归 | 当前源码68项启动/会话/配置/设置/更多/上下文用例；隔离Next的`writing-document.spec.ts`6项 | 均退出0，共74个当前源码用例；本机已安装Chrome，排除ios/build副本 |
| Next构建及来源 | `INK_IOS_NEXT_ROOT=frontend/ios/build/pr-mobile-20261102/Next`准备与隔离`next build --webpack`，随后`bundle-next.py --verify-sources` | 均退出0；550份当前runtime输入通过，复用已安装依赖，原`.next`与服务保持 |
| 文档 | `current-doccheck.py`与`current-mermaid-check.mjs` | 均退出0；12份Markdown、239链接、86源码引用、207锚点通过；本机Chrome实际生成27/27图SVG |
| 空白与提交范围 | `git diff --check`、暂存清单与凭证/产物路径核对 | 未暂存检查退出0；暂存标准检查发现历史快照末尾1处原有空行，原文保留；其余暂存文件和历史文件的其他空白项分别检查。提交清单78文件，无env/证书/安装包路径 |

首次浏览器收集因Writing规格缺少`E2E_WEB_BASE`退出1；随后复用旧配置发现旧构建副本，单独限定当前源码后68项退出0。Writing文档在本轮隔离Next上另行6项退出0。文档校验初次将已存在的具名`/tmp`回执判为越界，校验脚本增加该精确文件的存在性核验后退出0；产品文档与原回执保持。上述前置和校验脚本失败均未触发产品代码修改。新增历史快照`history/mobile-startup-expanded-draft-20261101.md`末尾原有空行触发标准暂存空白检查；该文件与本轮开始时的原文逐字一致。其余文件使用标准暂存检查，该历史文件仅关闭`blank-at-eof`后单独检查，其他空白规则保留。

当前源代码、正常服务和原工作区内容保持；验证未安装依赖、未调用真实账户或模型、未操作数据库或物理设备。源码提交、远端CI、PR合并与当前分支分别以对应Git/GitHub回执为准；本记录的技术检查结果只覆盖本轮指定范围。
