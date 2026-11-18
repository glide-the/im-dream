<!-- [Input] 用户指定react-notion-x、Next.js starter kit、Kastention UI规范v3.1及当前Notion读取实现。 -->
<!-- [Output] Next.js集成事实、数据合同差异、方案比较、样式映射与待验证项。 -->
<!-- [Pos] Notion工作空间预览的替换方案调研；本文建议模块与调用均未实现。 -->
<!-- [Sync] 2026-11-18: 根据用户“先调研”要求完成资料和源码核查，保留已有格式修复。 -->
# Notion 工作空间预览：react-notion-x 与 Next.js 集成调研

> 阶段记录：本文保留调研时的建议与待实施状态。用户随后确认方案A，现行实现、评审与验证归[正式设计](notion-workspace-preview.md)及[执行记录](../../exec/notion-workspace-preview-20261118.md)。

## 背景与问题

用户明确指定使用 [react-notion-x](https://github.com/NotionX/react-notion-x)，参考 [nextjs-notion-starter-kit](https://github.com/transitive-bullshit/nextjs-notion-starter-kit) 的Next.js集成方式，并按 [Kastention应用UI规范v3.1](../../prd/Kastention-App-UI-Guidelines-v3.1.pdf) 调整界面。用户最新要求为先完成方案调研。

当前代码已修复Read制表符编号，正常浏览器的既有对话可识别19条页面结果。正文仍交给 `ChatMarkdown`，Notion的 `<file>`、`<mention-page>`、`<empty-block>` 等标签保留为文字。当前实现状态与真实页面只读复核见[执行记录](../../exec/notion-workspace-preview-20261118.md)。

本轮读取starter kit的组件、App Router布局、样式、数据读取与依赖声明；读取NotionX的renderer、类型、兼容层；提取19页PDF文字并查看第8—11页组件和页面图。资料调查与当前代码核查完成。组件接入、数据适配及样式变更待实施。

## 目标与边界

目标为当前Chat中的摘要、完整阅读和JSON操作接入真正的 `NotionRenderer`，让文件、页面引用及实际出现的内容结构获得对应展示。网页桌面与窄屏复用原Thread、Modal、焦点和主题状态。

数据目标为展示该次Agent读取的内容，历史记录继续可读。预览展示不自动替换为Notion当前页面。全站发布、博客路由、站内搜索、分析统计、主题系统、公开页面配置与新的Notion登录流程位于本轮范围外。

## 概念与规则

| 对象 | 当前事实或职责 |
| --- | --- |
| Read返回值 | `ok`、`page_id`、`title`、`url`、`markdown` 和来源元信息，可能包装为带行号文本 |
| 增强Markdown | 当前API输出包含Notion扩展标签和普通Markdown；旧消息已经保存该内容 |
| ExtendedRecordMap | `NotionRenderer`要求的结构化数据，核心为block映射、父子顺序和富文本装饰，另含collection与signed_urls等映射 |
| NotionRenderer | 拥有Notion区块布局和交互；通过官方components扩展注册可选组件 |
| 数据适配 | 将既有内容转换为renderer输入；只负责区块类型、文本、属性、顺序、链接和格式校验 |
| Kastention样式 | 以现有Token、字体和页面组件覆盖renderer默认视觉，作用域限定于本预览 |

### 已核实的Next.js集成

1. starter kit当前采用App Router。其 [app/layout.tsx](https://github.com/transitive-bullshit/nextjs-notion-starter-kit/blob/main/app/layout.tsx) 先加载 `react-notion-x/styles.css`，再加载站点覆盖样式，代码与公式另有样式入口。
2. [NotionPage.tsx](https://github.com/transitive-bullshit/nextjs-notion-starter-kit/blob/main/components/NotionPage.tsx) 是客户端组件，将recordMap交给NotionRenderer，并通过components注册代码、公式、PDF等可选能力。PDF和媒体弹层采用关闭服务端预渲染的动态组件。
3. [styles/notion.css](https://github.com/transitive-bullshit/nextjs-notion-starter-kit/blob/main/styles/notion.css) 说明库默认视觉与站点覆盖的职责；项目按类名修改排版、间距及颜色。本仓库使用相同集成结构，具体取值归Kastention规范。
4. Next.js官方支持在客户端组件中使用 `next/dynamic` 按需加载；`ssr: false` 必须位于客户端组件。依据：[官方懒加载文档](https://nextjs.org/docs/app/guides/lazy-loading)。
5. starter kit的 [lib/notion-api.ts](https://github.com/transitive-bullshit/nextjs-notion-starter-kit/blob/main/lib/notion-api.ts) 使用 `notion-client`，其 [getPage](https://github.com/transitive-bullshit/nextjs-notion-starter-kit/blob/main/lib/notion.ts) 获取recordMap。该数据获取路径属于其网站来源配置；本仓库沿原Dream连接器和授权读取。

### 数据合同差异

[renderer源码](https://github.com/NotionX/react-notion-x/blob/master/packages/react-notion-x/src/renderer.tsx) 的输入为 `ExtendedRecordMap`。现有页面JSON含一个Markdown字符串，直接传给recordMap无法完成渲染。安装组件和样式后仍需要解决此数据差异。

[notion-compat](https://github.com/NotionX/react-notion-x/tree/master/packages/notion-compat) 可将Notion官方页面及区块数据转换为RecordMap；其 [convertPage](https://github.com/NotionX/react-notion-x/blob/master/packages/notion-compat/src/convert-page.ts) 接收pageMap、blockMap、子项及父项映射。该函数的输入为结构化区块，当前Markdown字符串需要独立转换步骤。直接使用NotionCompatAPI.getPage会发起新的读取，不能恢复旧消息读取时已经丢失的区块属性。

官方[增强Markdown格式](https://developers.notion.com/guides/data-apis/enhanced-markdown)明确包含文件、引用、提示、折叠和分栏等结构。当前标签问题可追溯到格式差异。API版本迁移属于独立工作，本次保持当前已保存内容和来源合同。

### 本仓库对应位置

| 位置 | 已有能力 | 建议职责，未实现 |
| --- | --- | --- |
| [ChatMessageList](../../../frontend/app/_dream/components/chat/ChatMessageList.tsx) | 识别工具结果、历史过程外摘要 | 沿用已有结果入口 |
| [notionPreviewProjection](../../../frontend/app/_dream/components/chat/notionPreviewProjection.ts) | Read编号、JSON、页面标识与错误匹配 | 保持结果识别；摘要提取须去除资源URL和原始标签 |
| [NotionWorkspacePreview](../../../frontend/app/_dream/components/chat/NotionWorkspacePreview.tsx) | 卡片、对话区域展开、JSON查看和下载 | 展开时加载Notion正文组件 |
| NotionPageDocument，建议、未实现 | 新组件 | 封装NotionRenderer及官方可选组件 |
| NotionRecordMapAdapter，建议、未实现 | 新数据适配 | 既有增强Markdown转为可校验RecordMap |
| [frontend/app/layout.tsx](../../../frontend/app/layout.tsx) | 唯一Next布局与全局样式 | 加载库基础CSS；业务覆盖限定预览作用域 |
| [NotionWorkspacePreview.css](../../../frontend/app/_dream/components/chat/NotionWorkspacePreview.css) | 卡片与对话区域滚动 | 增加Kastention作用域下的Notion组件覆盖 |

## 数据来源方案比较

| 方案 | 旧对话 | 数据与权限影响 | 成本及限制 | 结论 |
| --- | --- | --- | --- | --- |
| A：既有读取内容转换为RecordMap，再由NotionRenderer展示 | 可直接使用已保存正文 | 沿原历史消息权限；展示不增加Notion读取 | 需要明确转换范围；原Markdown缺少的区块属性无法恢复 | 推荐作为当前需求的实施入口 |
| B：在新的读取中保存官方区块，再经notion-compat转换 | 旧消息仍需A或另外读取 | 后端需要递归读取、分页、归属及失败处理，并扩展结果合同 | 可获得更多区块信息；调用成本与历史兼容范围增加 | 适合后续需要更高区块还原度时单独评审 |
| C：直接采用starter kit的notion-client获取页面 | 获取的是当前页面 | 新增数据获取及私有内容授权路径 | 需要处理现有挂载范围、历史差异和来源一致性 | 当前授权及历史内容需求优先使用原链路 |

A的选择依据为旧对话已经存在、输入内容明确、展示必须使用react-notion-x、原连接和消息权限可复用。A需要编写数据转换合同，库负责全部支持区块的展示。将标签替换成手写DOM、继续用ChatMarkdown承担Notion正文的方案不进入本轮实现。

## 推荐集成结构：建议、未实现

```text
原Read工具结果 / 原历史结果
        ↓ 编号、JSON、页面标识校验（已实现）
NotionWorkspacePreview 摘要卡片（已实现）
        ↓ 用户展开
按需加载 NotionPageDocument（建议、未实现）
        ↓
NotionRecordMapAdapter（建议、未实现）
        ↓ ExtendedRecordMap
NotionRenderer（待安装和接入）
        ↓
Kastention作用域样式（待按PDF修订）
```

集成设置建议：正文使用 `fullPage=false`，外层标题、JSON和关闭仍由原Modal持有。Code、Equation、PDF按实际内容注册；媒体弹层继续沿原宿主的焦点和关闭机制。图片和引用链接使用已保存的来源值；签名过期提供明确反馈，不在渲染时自动重新读取页面。

优先转换范围覆盖当前记录中出现的文件、图片、页面/数据库引用、空块、换行、提示、折叠、分栏和表格，以及原Markdown的段落、标题、列表、代码和公式。格式字段保留原数据；缺失字段按renderer明确支持的默认值处理。未知区块采用可读反馈和原JSON入口。代码块、行内代码及转义标签必须保持字面文本。

## 按UI规范v3.1对齐

| PDF依据 | 本预览落实方式 |
| --- | --- |
| 第3页：内容层级、轻纸面、局部强调 | 页面标题和正文为主；摘要使用留白和细分隔；附件和引用采用简洁条目 |
| 第4页：色彩与主题 | 将renderer的前景、背景和边框变量映射到既有 `--color-*` Token；同步显式浅色、显式暗色和系统主题 |
| 第5页：字体与阅读 | 标题/标签沿已确认手写字体范围；功能文字保持可辨读；正文沿Chat阅读规则，代码和JSON保留等宽字体 |
| 第6页：布局与滚动 | 固定顶部操作，正文独立纵滚；代码、表格和JSON局部横滚；窄屏操作可达 |
| 第7、9页：图标、列表 | 复用Icons，图标独立提供名称；文件显示文件名，引用显示页面标题；细线与留白建立层级 |
| 第10页：预览和返回 | 复用关闭、下载、焦点恢复及原对话区域；保留用户阅读来源 |
| 第11页：Chat结构 | 复用原消息、导航、输入和任务范围；Notion正文保持在原阅读区域 |
| 第16页：可访问性 | 覆盖键盘、长标题、触摸尺寸和实际前景/背景测量；规范中的既有对比度缺口单独登记 |

规范将写作正文18px的数值限定于写作场景；本次Chat预览不据此新增全局字号。starter kit的渐变、博客页眉和整站主题保留在参考项目；Kastention使用本仓库Token和原组件职责。

## 依赖与待验证项

调研时npm registry返回react-notion-x候选版本8.0.8，React及React DOM peer要求为>=18，覆盖本仓库React19.1.0。此信息证明声明范围兼容，实际Next16.1.6集成仍需构建和浏览器验证。

该版本依赖KaTeX0.18.4，本仓库直接依赖0.16.47。公式可选组件及CSS的共存方式需在隔离验证中确认，主应用现有公式依赖和行为继续保留。Code与PDF额外模块仅按内容加载。锁文件及包版本应在实施阶段精确记录。

待执行：依赖安装、RecordMap适配原型、真实Notion文件/引用与复杂结构对照、代码字面量和URL校验、加载失败恢复、原JSON下载一致性、明暗主题与窄屏截图、Next类型/编译检查。当前未执行上述组件集成测试。

## 调研结论与实施门槛

集成结构可以沿starter kit采用NotionRenderer、可选组件按需加载和作用域CSS覆盖。当前关键工作是既有Read内容到RecordMap的数据合同。推荐A作为当前历史预览的实现入口；B作为需要完整区块来源时的独立后续路线。

进入实现前应先列明A对实际标签和结构的映射及无法恢复的属性，再更新正式交互设计和验收矩阵。当前交付为有来源的调研方案；react-notion-x渲染、Kastention样式替换和新组件验收均为待实施。
