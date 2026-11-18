<!-- [Sync] 2026-11-18: 依据正常浏览器旧对话补齐制表符Read格式，并留存实际页面只读复核。 -->
<!-- [Input] Notion问题来源、当前develop工作区、正式设计与本轮技术验证回执。 -->
<!-- [Output] 本轮范围、评审、源码交付与验证状态记录。 -->
<!-- [Pos] Notion工作空间预览执行记录；真实业务和发布分别留存。 -->
<!-- [Sync] 2026-11-18: 登记来源、实施前评审、网页源码与已完成技术验证回执。 -->
# Notion 工作空间预览执行记录

## 需求与范围

来源：[近期需求目标区块](https://app.notion.com/p/40b30b7547c380cd9930c384ab35023c#41b30b7547c3803a9079e5c84adc127d)。已通过Notion连接读取完整所属页面、目标标题区块及三张示意图。目标区块自身只有标题，正文位于所属页面的同一章节。

[PRD](../prd/chat/notion-workspace-preview.md)拥有任务、范围和桌面/窄屏骨架。[正式设计](../design/workspace/notion-workspace-preview.md)拥有来源事实、方案比较、正常/异常时序、状态图及实施前评审。

本轮交付网页Chat中既有Notion Read结果的摘要、对话区域阅读、JSON查看和下载。原生客户端扩展、Notion专属区块布局、真实账户操作、部署与生产配置调整留待独立范围。后端既有读取/授权合同已满足本轮数据需求。

## 工作区保护

启动分支为 `develop`。启动时已有未提交改动：Claude Agent TypeScript迁移文档、执行目录索引、iOS目录索引、`bundle-python.py`、iPhone启动执行记录与StartupReadinessUITests。上述内容由原工作保留。本轮仅向共享 `docs/exec/.folder.md` 追加本需求索引。

## 设计过程与评审

发现：读取需求、三张图、Notion Read重定向、Chat工具结果及历史过程读取代码。定义：在Chat阅读该次Agent已读取页面。方案比较：复用Markdown结果、引入recordMap采集、点击重新读取。选定既有Markdown结果和JSON阅读，缩小数据与授权改动。

实施前评审通过。修订包括将展开范围绑定当前ChatPanel、仅摘要挂载短文字、JSON按需序列化、保留原历史受限读取。代码核查进一步确认 `useHistoricalChatProcess` 已自动限量恢复过程，PRD和设计已按现行代码修订。

## 实现工作项

| 工作项 | 交付物 | 状态 |
| --- | --- | --- |
| 来源核查与方案收敛 | PRD和正式交互设计 | 已完成 |
| Read结果投影 | notionPreviewProjection.ts | 已完成，技术验证通过 |
| 页面摘要与阅读 | NotionWorkspacePreview.tsx / CSS | 已完成，技术验证通过 |
| Chat和共享弹层接线 | ChatMessageList、ChatPanel、Modal | 已完成，技术验证通过 |
| 双语反馈 | i18n.ts | 已完成，技术验证通过 |
| 核心及相关回归 | 纯合同、隔离浏览器、类型与lint | 已完成 |
| 文档核查 | Markdown清单、路径与Mermaid语法 | 已完成 |

## 验证边界

测试通过原生产组件、Read DTO和历史过程读取构造隔离场景。Project、Episode、创作Artifact、Run私有发布、Hook及数据库投影均位于本场景范围外；测试不创建或修改这些实体。浏览器仅使用本轮Vite临时端口和现有Chrome，清理由本轮server.close负责。

本轮未执行真实用户Notion读取、真实模型、原生客户端运行或部署。隔离浏览器结果只证明网页呈现和原DTO消费合同。

## 命令回执

所有以下技术命令由 `luna_test_runner` 执行。业务源码、测试和文档修订由主Agent完成。

### 初轮与修订

| 轮次 | 命令范围 | 退出码与结果 | 修订 |
| --- | --- | --- | --- |
| 第一轮 | 专项Playwright，输出results | 1；5通过、2浏览器失败，void-elements依赖加载失败 | 夹具改用现有Vite依赖发现；历史process mock改为顶层DTO |
| 第一轮 | TypeScript | 2；大小写相同的模块主体名称造成解析冲突 | 展示投影改名为notionPreviewProjection.ts |
| 第二轮 | 专项Playwright，输出rerun | 1；6通过、1失败，标题定位同时命中h2和h1 | 正文标题按level:1定位 |
| 第二轮 | TypeScript / ESLint / diff | 全部0 | 源码类型、规范和空白检查通过 |
| 第三轮 | 专项Playwright，输出final | 1；7通过、1失败，Mermaid动态导入绕过Vite依赖转换 | Mermaid由虚拟模块静态导入并按现有依赖预构建 |
| 第二轮 | Mermaid Node脚本 | 1；两个时序图解析通过，状态图遇到DOMPurify.addHook缺少DOM依赖 | 转入已安装Chrome中的实际Mermaid解析器 |

上述夹具失败保留各轮回执，按对应原因修订；功能断言通过范围按终轮结果确认。

### 已完成检查

工作目录：仓库根。

```bash
python3 .agents/skills/ink-dream-playwright-qa/scripts/preflight.py --json
```

退出码0：依赖和入口存在，Playwright声明及安装均为1.62.1；5173空闲、8765已有服务。本轮未操作该已有服务。

工作目录：`frontend/`。

```bash
corepack pnpm exec tsc --noEmit --pretty false --incremental false
corepack pnpm exec eslint app/_dream/components/chat/notionPreviewProjection.ts app/_dream/components/chat/NotionWorkspacePreview.tsx app/_dream/components/chat/Modal.tsx app/_dream/components/chat/ChatMessageList.tsx app/_dream/components/chat/ChatPanel.tsx app/_dream/i18n.ts
```

两条命令退出码均为0，无错误输出。其后业务源码保持同一版本，后续修订位于测试夹具与交付文档。

### 终轮专项与相关回归

工作目录：`frontend/`。

```bash
corepack pnpm exec playwright test app/_dream/components/chat/__tests__/NotionWorkspacePreview.test.ts app/_dream/components/chat/__tests__/NotionWorkspacePreview.browser.test.ts --reporter=line --workers=1 --output=/tmp/ink-notion-preview-20261118-luna/verified
```

退出码0，8/8通过，31.4秒。覆盖5项纯展示合同、桌面/窄屏阅读、JSON查看与下载及失败重试、空正文/权限反馈、Thread切换、焦点恢复、历史过程外摘要与正式设计3图语法。已审看桌面及窄屏截图。

```bash
corepack pnpm exec playwright test app/_dream/components/chat/__tests__/WorkspaceReportPreview.test.ts app/_dream/components/chat/__tests__/AssistantTurnGroup.browser.test.ts app/_dream/components/chat/__tests__/ChatHistoryProcessLazyLoad.browser.test.ts --reporter=line --workers=1 --output=/tmp/ink-notion-preview-20261118-luna/related
```

退出码0，收集项140/140通过，约2.2分钟。仓库原Playwright收集同时包含 `frontend/ios/build/**` 下的构建副本；140为实际收集数量，包含指定源规格及其构建副本。共享回归覆盖原报告预览、弹层焦点、过程折叠及历史恢复。

状态图在末轮文档复核中明确“每次Read独立卡片，重新读取保留先前结果”，随后仅复验图示：

```bash
corepack pnpm exec playwright test app/_dream/components/chat/__tests__/NotionWorkspacePreview.browser.test.ts --grep 'parses all formal design Mermaid' --reporter=line --workers=1 --output=/tmp/ink-notion-preview-20261118-luna/mermaid-final
```

退出码0，1/1通过，三个Mermaid图均在已安装Chrome/Vite中解析成功。此项属于文档语法验证。

### 最终文档与工作区核对

工作目录：仓库根。

```bash
python3 /tmp/ink-notion-preview-doc-check.py
git diff --check
```

退出码均为0。文档脚本检查3篇Markdown、10条相对引用、5项新增源码/测试清单和3段Mermaid提取，并核对本轮文档用语。图示语法由上方浏览器检查确认。

截图保留于 `/tmp/ink-notion-preview-20261118-luna/verified/app-_dream-components-chat-38d5b--narrow-conversation-bounds/desktop-json.png` 和同目录的 `narrow-json.png`。测试保留本轮回执目录，所有Vite实例按finally关闭；原用户服务与数据库保持。本轮下载的3张Notion参考图临时文件已清理。

交付状态：网页源码、设计评审和必要技术验证完成。真实账户Notion读取、真实模型验收、原生客户端接入及部署均未执行；当前结果证明既有DTO的网页消费和交互合同。Notion专属区块排版和附件签名刷新继续由独立数据合同定义。


## 用户现场跟进：实际历史记录未渲染

用户截图显示 `.notion/pages/` 的读取结果仍为终端JSON。主Agent在正常Chrome的 `http://localhost:5173/story-workspace/chat` 中复核同一现有对话，修改前19条带页面JSON的结果均落入终端，预览卡片为0。

根因：实际Read输出使用 `1\t{JSON}`，正文后带空行和 `<system-reminder>`。首五个字符码为 `[49, 9, 123, 34, 111]`，其中9为制表符。原解析器仅支持箭头编号，首轮隔离夹具采用了箭头和直接对象，缺少实际Runtime制表符格式。

修复：`notionPreviewProjection.ts`接受制表符或箭头编号，允许行号从0或1开始，要求行号连续且同一结果的分隔符一致。部分结果、跳号、重复编号和混用分隔符继续沿原工具展示。浏览器规格改为带制表符及尾部reminder的原始文本；纯合同新增成功/失败、0起始、多行、CRLF与损坏编号覆盖，夹具正文使用合成内容。

正常浏览器只读结果：热更新后同一对话显示19张卡片，包含18个成功正文和1个读取失败反馈，原对应页面JSON终端为0。主Agent打开《近期需求》核对正文及JSON详情，确认JSON包含同一页面标识；关闭后对话卡片保留，焦点恢复至原展开按钮。截图：`/tmp/ink-notion-preview-20261118-real-page/reader-json.png`；关闭后的正常对话卡片截图为同目录 `cards.png`。

本次正常页面复核只使用既有账户、对话和读取记录，没有发送消息、调用模型、重新抓取Notion正文、修改历史记录或重启服务。该结果证明当前正常浏览器的既有结果展示；新增读取执行、模型链路和其他终端仍沿原验证边界。

本次格式修复的Luna回执：

```bash
# 工作目录：frontend/
corepack pnpm exec playwright test app/_dream/components/chat/__tests__/NotionWorkspacePreview.test.ts app/_dream/components/chat/__tests__/NotionWorkspacePreview.browser.test.ts --reporter=line --workers=1 --output=/tmp/ink-notion-preview-20261118-luna/tab-format
corepack pnpm exec tsc --noEmit --pretty false --incremental false
corepack pnpm exec eslint app/_dream/components/chat/notionPreviewProjection.ts
# 工作目录：仓库根
python3 /tmp/ink-notion-preview-doc-check.py
git diff --check
```

退出码均为0。专项10/10通过，31.8秒；类型与规范检查无错误。文档检查3篇正文、10条相对引用、5项新增源码/测试清单及3段Mermaid提取，图示语法由专项中的浏览器解析确认。隔离Vite按finally关闭，正常服务保持。


## 用户指定react-notion-x、UI规范与Next.js参考

最新工作项为先调研方案。资料包含NotionX renderer与compat、starter kit App Router组件/布局/样式/数据来源、Next.js官方懒加载说明及UI规范v3.1。PDF共19页；已提取文字并查看第8—11页组件及页面示意。

已确认：NotionRenderer接收ExtendedRecordMap，原Read保存增强Markdown；starter kit的数据获取使用notion-client，原Dream读取仍由现行连接器所有。推荐保留旧消息来源，定义RecordMap转换范围后用库渲染；官方区块和notion-compat作为后续完整来源路线比较。UI映射按PDF章节记录，未迁移参考网站主题。

交付物：[react-notion-x与Next.js集成调研](../design/workspace/notion-workspace-preview-react-notion-x-research.md)。当前状态：调研完成、数据适配合同与组件实施待推进。本阶段未安装依赖、未修改渲染代码、未改Next配置、未部署。前文制表符格式修复保留，10项回归属于原展示基线。

本阶段文档检查：`python3 /tmp/ink-notion-preview-doc-check.py`退出码0，检查4篇Markdown、20条相对引用、5项源码/测试清单与3段Mermaid提取；`git diff --check`退出码0。以上属于文档核查，react-notion-x组件集成尚未执行验证。


## 用户确认后的react-notion-x实施与最终验证

### 交付范围与评审

用户已确认执行方案A，并要求连续推进。正式设计在正文接线前补齐转换映射、数据来源和UI规则；实施前评审选择“既有增强Markdown转ExtendedRecordMap，由NotionRenderer负责区块DOM”。现行正式稿收敛为A；早期Markdown稿完整保存在设计目录，调研原文保留其阶段状态。

已交付：

- `NotionPageDocument.tsx`使用react-notion-x 8.0.8，展开时按需加载；fullPage=false，标题和操作继续由原Modal所有。
- `notionRecordMapAdapter.ts`复用mdast/GFM和原Chat数学语法，转换文件、引用、空块、换行、提示、折叠、分栏、表格、代码、图片和公式。代码及转义标签保持字面文本。URL校验和原始HTML隔离在展示边界执行。
- 文件及PDF使用库文件条目；引用使用原地址与已有标题；真实来源额外出现的自闭合link-preview使用原地址及域名标签。未知内容保留可读原文及JSON。
- Next layout先加载库基础CSS，预览覆盖使用Kastention现行Token、可辨读功能字体、固定顶部操作和局部滚动。文件图标、表头、链接和正文覆盖明暗/系统主题；窄屏分栏纵向排列。
- Code扩展沿库组件，Mermaid和公式复用原宿主。KaTeX直接依赖保持0.16.47，未接入库的另一套数学CSS。依赖精确锁定，原已有包版本保持；mdast-util-from-markdown从开发依赖移为直接运行依赖。
- 摘要先移除完整图片/文件标记和资源URL，再截取文字；组件失败、图片失败和下载失败保留局部恢复。原JSON查看与下载来源保持同一payload。

主要交付：[PRD](../prd/chat/notion-workspace-preview.md)、[正式设计及评审](../design/workspace/notion-workspace-preview.md)、[方案调研](../design/workspace/notion-workspace-preview-react-notion-x-research.md)。相关源码、测试、Next入口及目录清单已同步。

### 技术验证

Luna首轮检查暴露类型收窄缺口，修复后类型与lint通过。首轮浏览器17项中16项通过；失败断言将库的.notion-h1输出要求为h1。按NotionRenderer的标题输出语义修订断言并移除重复锚点名称后，定向回归通过。该问题属于验证定位与库语义差异。

最终定向检查，工作目录frontend：

```bash
corepack pnpm exec tsc --noEmit --pretty false --incremental false
corepack pnpm exec eslint app/_dream/components/chat/notionRecordMapAdapter.ts app/_dream/components/chat/NotionPageDocument.tsx app/_dream/components/chat/NotionWorkspacePreview.tsx app/_dream/components/chat/notionPreviewProjection.ts app/_dream/components/chat/remarkChatMath.ts app/layout.tsx e2e/notion-preview.config.ts app/_dream/components/chat/__tests__/NotionWorkspacePreview.browser.test.ts app/_dream/components/chat/__tests__/notionRecordMapAdapter.test.ts
corepack pnpm exec playwright test --config=e2e/notion-preview.config.ts --reporter=line --workers=1 --output=/tmp/ink-notion-react-final-20261118/browser
```

退出码均为0。定向回归25/25通过，44.5秒，包含原Modal/history/报告规格及Notion展示合同、真实库渲染、JSON下载一致性、故障注入后重试、图片失败恢复、桌面/360px与两种显式主题。故障注入日志`Isolated renderer fault`为对应失败恢复规格的预期输入。配置仅收集源规格，无iOS构建副本。源码类型与lint无错误；截图已审看。

正常账户复核发现link-preview后，补跑最新适配合同和系统主题规格：

```bash
corepack pnpm exec playwright test --config=e2e/notion-preview.config.ts app/_dream/components/chat/__tests__/notionRecordMapAdapter.test.ts --reporter=line --workers=1 --output=/tmp/ink-notion-next-build-20261118/incremental/adapter
corepack pnpm exec playwright test --config=e2e/notion-preview.config.ts --grep 'renders enhanced tags|self-closing link-preview' --reporter=line --workers=1 --output=/tmp/ink-notion-next-build-20261118/incremental/browser
```

退出码均为0，分别7/7与2/2通过。增量规格与25项回归存在重叠，数量分别记录；系统主题在浅色和暗色媒体偏好之间切换，库主题类名同步更新。正文前景/背景对比度两主题均达到4.5以上；JSON与代码局部滚动，360px无页面或正文横向溢出。

### 隔离Next生产编译

本次执行为本机技术编译。目标为macOS本机Next16.1.6、当前已安装依赖与同一锁文件；原用户dev服务和.next保持。入口为package.json的`build`，实际执行`next build --webpack`。检查取得16GiB物理内存、系统空闲约53%、磁盘可用16GiB；macOS无Linux cgroup。NODE_OPTIONS无堆参数，脚本无内联堆覆盖。10核主机的Next默认静态页worker为9，webpack和类型检查worker各1；单一构建串行执行，预算沿约8GiB空闲核对。

使用rsync将当前frontend镜像至`/tmp/ink-notion-next-build-20261118/frontend`，排除node_modules、.next、iOS/Android、legacy、dist、output、test-results、嵌套历史frontend、.env及tsbuildinfo；链接现有node_modules。镜像复制退出码0，无私有环境复制。

```bash
# 工作目录：/tmp/ink-notion-next-build-20261118/frontend
NODE_ENV=production corepack pnpm build
```

退出码0。webpack编译成功、完整TypeScript通过、静态页9/9生成。实际耗时23.90秒，最大常驻内存2,621,358,080字节；该指标来自time回执，未将其解释为进程组内存。无重试，无发布和服务重启。磁盘可用约16GiB变为15GiB；自有node_modules链接和.next/cache已清理，BUILD_ID、路由清单及其余本轮产物供复核。原Next PID54052/54057保留，无本轮残留构建或Vite进程。

证据根目录：`/tmp/ink-notion-react-final-20261118/`与`/tmp/ink-notion-next-build-20261118/`。截图包含desktop-json.png、narrow-json.png、enhanced-light.png、enhanced-dark.png和enhanced-narrow-dark.png，位于对应浏览器规格目录。

### 正常账户既有结果只读复核

主Agent使用原Chrome、原localhost:5173页面和既有对话。Next样式热更新后，重新打开同一历史对话读取已有消息，显示19张页面卡片。打开《近期需求》后确认：真实NotionRenderer存在；2个文件条目、16个正文链接、2个表格、2栏；file、mention-page、empty-block和link-preview原始标签可见数量为0。JSON详情的page_id与来源页面一致；源标签统计与显示对象对应，其中file2、mention-page2、link-preview1、columns1、column2、table2。

旧图片存在加载失败，已显示图片重试及打开原图。未自动刷新签名。关闭后卡片19张保持，弹层为0，焦点恢复至“展开近期需求”，背景滚动锁释放。截图：`/tmp/ink-notion-react-real-20261118/actual-files.png`。

此项仅复核正常账户已保存结果的阅读、JSON及返回。没有发送消息、调用模型、重新读取Notion、修改历史、连接、数据库或配置。新增读取执行、真实模型链路、签名刷新、原生客户端和部署未在本轮验证；这些项目不影响已保存正文的网页阅读交付。

### 最终状态

react-notion-x接入、设计规范映射、交互评审、源码、分层验证与目录同步完成。改动保留在当前工作区，用户及其他Agent的无关修改保持。前轮类型检查生成的本轮tsbuildinfo已还原为任务开始时版本；最终类型检查使用incremental=false。

文档清单、相对引用、用语与Mermaid提取由最终文档检查确认；现行正式设计3图通过浏览器Mermaid语法解析，历史基线3图保留原文。文档核查独立于功能验证。


## 摘要卡片视觉细化

本轮需求为用户指出的NotionWorkspacePreview卡片视觉。已核查当前正常页面及UI规范v3.1的现行文字源，使用frontend-design技能收敛布局。实施前评审采用限定宽度文档卡片、图标/来源/标题层级、三行功能字体摘要、底部下载与阅读操作；正式设计与PRD已同步。

| 业务对象或边界 | 影响 |
| --- | --- |
| 摘要卡片布局、字体、入口位置 | 本轮调整 |
| 当前Thread、已保存Read、JSON及原NotionRenderer | 保持原合同 |
| Project、Episode、canonical Artifact、Run私有发布、Hook、PostgreSQL/API投影 | 本轮范围外 |
| 验证通道 | 隔离技术浏览器验证及正常页面只读视觉复核 |

本轮未发送Agent消息或更改真实业务数据。验证回执如下。


### 卡片实现与技术回执

NotionWorkspacePreview采用文档图标、来源与两行标题、三行摘要、底部下载和阅读操作。宽屏卡片上限640px，窄屏沿容器收缩；摘要和功能操作使用既有功能字体，来源沿原展示字体。阅读入口的辅助功能名称继续包含完整页面标题，aria-haspopup声明dialog。失败结果显示查看详情，下载、JSON及Modal生命周期沿原路径。

notionPreviewExcerpt增加展示清理：去除与卡片重复的首行标题，优先跳过完整代码围栏与外管线Markdown表格行；纯代码或表格沿可读文字回退。原markdown和payload保持。相应用例补充正常、窄屏、长标题、空正文和失败截图及摘要合同。

工作目录frontend，Luna首轮视觉回归：

```bash
corepack pnpm exec playwright test --config=e2e/notion-preview.config.ts --reporter=line --workers=1 --output=/tmp/ink-notion-card-ui-20261118/browser
```

退出码0，27/27通过，45.1秒。摘要清理后按受影响源规格复验：

```bash
corepack pnpm exec playwright test --config=e2e/notion-preview.config.ts NotionWorkspacePreview --reporter=line --workers=1 --output=/tmp/ink-notion-card-ui-final-20261118/browser
corepack pnpm exec tsc --noEmit --pretty false --incremental false
corepack pnpm exec eslint app/_dream/components/chat/NotionWorkspacePreview.tsx app/_dream/components/chat/notionPreviewProjection.ts app/_dream/components/chat/__tests__/NotionWorkspacePreview.test.ts app/_dream/components/chat/__tests__/NotionWorkspacePreview.browser.test.ts
```

退出码均为0。受影响14/14通过，7.9秒；27项与14项存在重叠，分别记录。原阅读、JSON下载、历史卡片、组件/图片恢复、关闭焦点和Thread切换继续通过。控制台的Isolated renderer fault属于原故障注入输入；正常规格无pageerror。卡片覆盖浅/暗主题、桌面/360px、长标题、空内容及错误操作可达，7张截图由主Agent审看。

最终卡片截图位于`/tmp/ink-notion-card-ui-final-20261118/browser/NotionWorkspacePreview.bro-7d835-ow-width-and-content-states/`，文件为card-desktop-light.png、card-desktop-dark.png、card-narrow-light.png、card-narrow-dark.png、card-narrow-long-title.png、card-narrow-empty.png、card-narrow-error.png。本轮隔离Vite已清理，用户既有服务保持；本次视觉修订未重复生产构建或部署。

### 卡片正常页面只读复核

主Agent在既有Chrome对话中打开原执行过程加载既有Read结果，再收起过程；19张卡片保持。近期需求卡片实测宽640px、高约249px，摘要为400字重的既有功能字体。阅读页面打开原NotionRenderer，关闭后弹层0、卡片19，原展开入口焦点恢复，背景滚动锁释放。无Agent消息、模型调用或业务数据变更。

本轮截图保存在`/tmp/ink-notion-card-ui-real-20261118/`；组件视觉矩阵使用上方隔离截图，正常页面回执记录原Thread阅读行为。

仓库根的`python3 /tmp/ink-notion-preview-doc-check.py`与`git diff --check`退出码均为0；文档清单、引用与现行设计图沿原门禁单独核对。本轮交付为工作区中的卡片UI修订，用户视觉验收与部署分别记录。


## 用户跟进：无外框紧凑预览

用户要求缩小临时记事本等预览、去除大边框并参考原Notion设计截图。主Agent通过原Notion连接重读来源及第一张截图，确认标题右侧下载/展开结构；评审选择无外框轻量条目。设计与PRD在实施前同步：36rem宽度、14px单行标题、13px两行摘要、16px文档图标、右侧常显图标操作、透明背景、无阴影/外边框。

本轮影响为CSS与图标操作位置。原Thread、JSON、下载、NotionRenderer和Modal保持；Project/Episode/Artifact/Hook/PostgreSQL位于范围外。验证采用原隔离展示旅程，正常页面只做已保存结果阅读。


紧凑版技术回执（工作目录frontend）：

```bash
corepack pnpm exec playwright test --config=e2e/notion-preview.config.ts NotionWorkspacePreview --reporter=line --workers=1 --output=/tmp/ink-notion-compact-20261118/browser
corepack pnpm exec tsc --noEmit --pretty false --incremental false
corepack pnpm exec eslint app/_dream/components/chat/NotionWorkspacePreview.tsx app/_dream/components/chat/__tests__/NotionWorkspacePreview.browser.test.ts
```

退出码均为0。14/14通过，8.1秒；覆盖下载、完整阅读、JSON、关闭/焦点、历史恢复、明暗与360px、长标题/空/失败展示。正常摘要高度上限112px的几何断言通过；7张截图位于`/tmp/ink-notion-compact-20261118/browser/NotionWorkspacePreview.bro-7d835-ow-width-and-content-states/`，主Agent已审看桌面及窄屏。故障注入日志沿原预期；隔离Vite清理完成。

正常页面只读复核：用户指出的临时记事本-11-8宽576px、高99.6px，border为0、shadow为none、背景透明；标题右侧两个原操作可用。展开后原NotionRenderer可见，关闭后19张卡片保持、弹层0、焦点恢复。截图为`/tmp/ink-notion-compact-real-20261118/preview.png`与同目录context.png。未发送消息、调用模型或修改业务数据。原Notion参考图复核完成后清理本轮下载临时文件。

根目录文档与工作区检查沿`python3 /tmp/ink-notion-preview-doc-check.py`及`git diff --check`，结果单独留存。本轮未执行构建或部署。
