<!-- [Input] 用户授权的UI规范重整、历史PDF与现行源码。 -->
<!-- [Output] 问题诊断、方案选择、交付追踪、范围评审及文档验证证据。 -->
<!-- [Pos] 2026-11-02应用UI规范文档任务执行记录；应用代码修改退出范围。 -->
<!-- [Sync] 2026-11-02: 完成19页/17图规范、六图渲染、120项色彩、历史保留与应用源码保护检查。 -->

# 应用UI规范重整评审

## 需求与授权

用户要求重整Ink & Memory应用UI规范，补充图示、版式与术语，完成交互设计和评审，交付可编辑源文件与新版PDF。本轮应用代码修改数量目标为零，历史PDF原文保留。正式规范直接描述产品规则与版本沿革。

本轮规划使用用户已确认的优化提示词，内部收敛为“以现有产品为依据，按文档职责重整规范，制作可编辑矢量示例，交付PDF与交互评审”。初始规划执行一次优化；原计划内制作与验证继续沿用该范围。

## 发现与定义

| 问题位置 | 观察事实 | 影响 | 处理 | 优先级 |
| --- | --- | --- | --- | --- |
| 原PDF封面及第2页 | 文内v2.1，文件名v2；主体为品牌官网首屏 | 应用规范的读者与范围不清 | 新版v3.0说明文档范围，原文件邻接处增加指引 | 高 |
| 原PDF第6-15、17-19页 | 角色、官网区块、文案和生成提示词占主要篇幅 | 组件与交互查阅成本较高 | 以现有应用样式、组件和页面组织正文 | 高 |
| 原PDF全稿 | 页面以文字和表格为主，图示不足 | 布局与状态规则依赖文字理解 | 加入色板、排版样张、组件和双端骨架 | 高 |
| 原PDF第3、16页等 | 短内容独占整页 | 阅读节奏和信息密度不稳定 | 统一页面栅格、分页、页眉页脚与图注 | 中 |
| 原PDF第1、4页 | 引用旧frontend/src/styles路径 | 当前来源查阅受阻 | 核对并引用app/_dream及Native来源 | 高 |
| 原稿“无卡片”表述 | 现行MoreNavigationContent已有卡片与用途说明 | 全局用语与具体页面范围冲突 | 按Settings/Deck/More/输入容器分别说明规则 | 高 |
| 亮暗色来源文档 | 亮色表为早期值，暗色表混合声明块与系统媒体值 | 新规范来源互相冲突 | 历史原文归档，现行文档按三组40项Token校准 | 高 |
| 当前Token配对 | 暗色主操作白字、亮色弱文本与链接存在对比度缺口 | 普通文本阅读受影响 | 记录计算与后续建议，应用数值保持 | 高 |

### 输入资料

- 历史PDF：[原文](../prd/Ink%20%26%20Memory%20UI%20Design%20v2.pdf)，19页、A4，内文版本v2.1。
- 现行依据：[移动PRD](../prd/mobile-app/mobile-app.md)、[色彩系统](../prd/color_system/README.md)、[写作设计](../design/multi-platform/writing-mobile-layout.md)、[更多组件](../../frontend/app/_dream/components/story-workspace/layout/MoreNavigationContent.tsx)、[Native主题投影](../../frontend/src/components/inkColors.ts)。

核心问题定义：应用规范需要覆盖可查阅的规则、可视化示例、状态与来源，文档布局需要支持连续阅读和定位。

## 方案比较与交付收敛

| 方案 | 目标覆盖 | 工作量与维护 | 产品影响 | 结论 |
| --- | --- | --- | --- | --- |
| 原内容集中排版与配图 | 改善版式，应用规则缺口继续存在 | 工作量低，旧定位持续维护 | 小 | 排除 |
| 基于现有产品重整应用规范 | 覆盖定位、图示、组件、术语和交互 | 正文与单文档导出工具，来源可追溯 | 文档范围 | 采用 |
| 全面重做品牌与应用界面 | 超出本轮目标 | 需要独立产品与实现周期 | 大 | 排除 |

采用统一A4纵向阅读版。每页围绕一项查阅任务组织标题、图示和规则，复杂页面以桌面与窄屏对照骨架表达。PDF嵌入中文字体与矢量图，正文和图形定义均可编辑。

文档以章节编排、图文配合与标注说明规则，产品主题、角色、业务页面与组件依据现行资料。代表页面数量为四类，涵盖内容输入、阅读、任务反馈与导航。

## 交付物与所有权

| 交付物 | 位置 | 维护职责 |
| --- | --- | --- |
| 规范正文 | [README](../prd/mobile-app/ui-guidelines/README.md) | 产品规则摘要、页面骨架、术语和来源 |
| 图形与导出源 | [export_pdf.py](../prd/mobile-app/ui-guidelines/export_pdf.py)及同目录assets | 图形源定义、矢量SVG和PDF布局 |
| 正式交互 | [设计稿](../design/multi-platform/ui-guidelines-interaction.md) | 正常、异常恢复、状态图与验收 |
| 阅读版PDF | [阅读版](../prd/Ink-Memory-App-UI-Guidelines-v3.pdf) | 导出制品，源文件决定内容 |
| 历史入口 | [v2版本指引](../prd/Ink%20%26%20Memory%20UI%20Design%20v2.md) | 保留旧PDF原文与现行链接 |
| 色彩来源校准 | [亮色](../prd/color_system/light-theme.md)、[暗色](../prd/color_system/dark-theme.md)及[历史目录](../prd/color_system/history/.folder.md) | 逐字段同步三组40项声明；保留修订前原文 |

正文中的page注释划分出版页。SVG可由矢量编辑器打开；修改图形定义后重新导出，保持SVG与PDF一致。文档导出脚本位于产品文档目录，应用运行与构建入口保持。

## 目标与范围评审

| 原始目标 | 交付位置 | 检查方法 | 当前状态 |
| --- | --- | --- | --- |
| 明确规范定位 | 阅读与使用、版本指引 | 核对范围与来源 | 文档已编写 |
| 图示解释规则 | 基础样式、组件和四类页面 | 逐页视觉检查 | 19页、17幅矢量图检查通过 |
| 标准化文档布局 | 封面、目录、章节、页码和图注 | PDF全页检查 | 页码完整，溢出0，中文字体已嵌入 |
| 增加专业名词解释 | 两页术语与上下文说明 | 定义和产品例子核对 | 文档已编写 |
| 完成交互设计 | 正式设计稿六幅Mermaid | 解析、渲染及源码核对 | 六图可见渲染，控制台错误0 |
| 控制设计范围 | 方案比较及本表 | 核对新增内容的使用任务 | 设计范围通过 |
| 保护应用代码 | 1775项源码及原PDF指纹基线 | 执行后逐文件摘要核对 | 应用源码和旧PDF保持；一处并发目录文档变化单列 |
| 校准来源表 | 亮色、暗色与系统媒体声明 | 逐字段对照CSS | 120/120值匹配，历史副本摘要一致 |

范围评审：新增业务页面、导航、设置项、确认弹窗、接口、数据库和应用依赖数量均为零。新增组件变体与全局字号系统数量为零；图形样例属于文档示意。可访问性建议只记录待处理范围，当前Token保持。

## 可访问性取样与剩余事项

对不透明前景/背景按sRGB相对亮度与WCAG公式计算。主文本/亮画布10.61:1；辅助文本/亮画布4.56:1；弱文本/亮画布2.93:1；链接/亮画布2.88:1；白字/显式暗色主操作1.21:1。弱文本、链接及采用action-primary/text-on-action的按钮配对需要后续单独评估，普通文本目标为4.5:1。按钮采用位置见AnalysisView.native中的primary Action；其他组件按实际颜色分别检查。

建议配对深棕/显式暗色主操作的取样为10.00:1。该配对标记为建议、未实现；后续需要覆盖全部主题、透明叠加和状态。

依据：[W3C文本对比度](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum)、[W3C目标尺寸](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum)、[Apple界面设计](https://developer.apple.com/design/tips/)。检索日期2026-11-02。

设备触摸、VoiceOver、系统文字缩放、软键盘、旋转、Android及真实账户业务沿原专项记录继续验收。本轮文档检查与真实业务资格分别报告。

源码核对同时记录：Web后置系统暗色媒体选择器匹配system及显式dark；Native分别投影dark与systemDark。现行色彩文档已经分列两组暗色值；跨组合页面测量与是否统一规则留待后续任务。

## 验证命令与结果

运行目录为仓库根。下表的`PYTHON`指本次使用的`/Users/dmeck/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3`，`NODE`指同运行库下的`dependencies/node/bin/node`。这是记录中的命令变量说明，运行时按本机实际路径指定。

| 命令 | 退出码 | 关键结果 |
| --- | --- | --- |
| `PYTHON docs/prd/mobile-app/ui-guidelines/export_pdf.py` | 0 | 19页、17图，overflow为空 |
| `pdfinfo output/pdf/Ink-Memory-App-UI-Guidelines-v3.pdf` | 0 | A4纵向、19页，元数据版本v3.0 |
| `pdffonts output/pdf/Ink-Memory-App-UI-Guidelines-v3.pdf` | 0 | ArialUnicodeMS与Xiaolai均已嵌入；PDF标准字体保持内建引用 |
| `pdftoppm -scale-to 1400 -png output/pdf/Ink-Memory-App-UI-Guidelines-v3.pdf tmp/pdfs/ink-ui-20261102/final-page` | 0 | 最终19页图像；全页联系表检查，重点页另做1500px检查 |
| `NODE tmp/pdfs/ink-ui-20261102/validation/mermaid_validate.mjs` | 0 | 本机Chrome156.0.8078.74，6/6图rendered且visible，控制台错误0 |
| `NODE tmp/pdfs/ink-ui-20261102/validation/markdown_validate.mjs tmp/pdfs/ink-ui-20261102/validation/markdown-validation.json` | 0 | 正文17图片，路径与禁用话术问题0；汇总JSON保存实际计数 |
| `PYTHON tmp/pdfs/ink-ui-20261102/validation/color_validate.py` | 0 | 三组各40项，120/120原字符串匹配；两个历史副本与Git原文摘要一致 |
| `PYTHON tmp/pdfs/ink-ui-20261102/validation/pdf_validate.py` | 0 | 01/19至19/19完整，中文缺字指标0 |
| `PYTHON tmp/pdfs/ink-ui-20261102/validation/baseline_compare.py` | 0 | 1775项基线，应用源码及历史PDF保持；frontend/ios/.folder.md并发变化单列 |
| `PYTHON tmp/pdfs/ink-ui-20261102/validation/index_added_links.py` | 0 | 目录新增引用问题0 |
| `git diff --check -- docs/prd/.folder.md docs/prd/color_system docs/prd/mobile-app/.folder.md docs/design/multi-platform/.folder.md docs/design/multi-platform/README.md docs/exec/.folder.md` | 0 | 空白与补丁格式检查通过 |

首轮交互图的`Create`参与者别名触发Mermaid保留字冲突；改为`Factory`后六图通过。色彩校验首轮脚本将Markdown反引号计入字段值，修正harness抽取后120项通过。目录检查曾使用错误Python路径，实际验证在修正命令后执行。上述失败与恢复在证据中分别保留。

视觉评审覆盖全部19页，检查标题、图注、表格、页码、字形和区域边界；第4、11、16、17、18、19页进行局部细查。当前结果属于文档验证，应用真实业务及设备资格沿原记录。

详细结果归[验证汇总](ui-guidelines-validation-20261102.json)。[新版PDF](../prd/Ink-Memory-App-UI-Guidelines-v3.pdf)与[可编辑源文件包](../prd/Ink-Memory-UI-v3-Editable-Sources.zip)集中存放于docs/prd；[验证附件包](../../output/pdf/Ink-Memory-UI-v3-Validation.zip)保留原位置。正文、SVG、交互稿及评审记录均保留在文档目录。验证Chrome与自有HTTP服务已退出；临时预览在归档后清理。

## 出版文件位置

用户指定新版PDF和可编辑源文件包存放于docs/prd。迁移保留PDF原字节，导出工具默认路径同步为docs/prd；源文件包中的文档、导出工具和编辑说明同步更新。上表出版命令保留首次执行位置，现行文件入口采用本节链接。
