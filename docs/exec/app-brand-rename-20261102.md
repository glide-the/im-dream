<!-- [Input] 应用更名要求、当前ios-store工作区、现行设计和源码。 -->
<!-- [Output] 更名范围、评审决议、实现追踪和本地验证回执。 -->
<!-- [Pos] 本次应用名称更名执行记录；产品与交互规则归对应正文。 -->
<!-- [Sync] 2026-11-02: 登记现状、兼容边界和实施前评审。 -->

# 应用更名交付记录

## 执行依据

Optimized Prompt：在当前ios-store工作区将应用展示名称统一为默认Kastention和中文本地化卡片结构。读取根合同、目录合同和当前设计，按可见文案、内部身份、历史及外部依赖逐项评估。先完成发现、问题定义、方案比较和明确评审；复用原组件、constants目录和i18next。保持现有流程、账户、存储键、包身份、回调、域名和签名，保留并行改动与历史资料。更新现行产品需求、交互时序、UI规范源及必要PDF/ZIP，记录保留项。仅执行本地实现与必要技术验证；确定性验证按环境要求交由luna_test_runner，返回命令、退出码、关键输出和工具前置限制。

本轮优化一次。开始分支为`ios-store`，工作区含启动、聊天、回顾等体验修复；本轮逐项保留。用户暂不主动启用验证独立工作流的偏好已记录；本次更高优先级执行规则强制路由确定性检查，由专用验证代理执行，主Agent持有方案、实现与验收判断。

## 范围清单与兼容影响

| 位置 | 现有值 | 目标值 | 处理方式与兼容影响 |
| --- | --- | --- | --- |
| Web/Native字标、关于、准备/登录外层、应用标签 | Ink & Memory / Ink Memory | Kastention | 原组件中更新展示，保留生命周期 |
| 原英中翻译 | Ink & Memory / I&M | Kastention / 卡片结构 | 原键、语言偏好和回退保持 |
| 提示、来源、分享新输出 | 旧品牌/ink-memory文件名 | Kastention / kastention | 新输出更新；历史文件保持 |
| Web metadata、JSON-LD、llms.txt | 旧品牌 | Kastention | 原链接、域名及爬取规则保持 |
| 登录背景/社交图片 | 原水彩图内嵌旧字样 | Kastention | imagegen按文字替换目标编辑；原图保留历史，新图沿共享路径常量采用 |
| 系统应用名及用途说明 | Ink & Memory | Kastention | iOS/Android展示属性更新；系统语言新增配置数量为零 |
| 当前PRD、跨平台设计、UI规范、对外草案 | 旧名称 | 新名称 | 当前正文同步；历史叙述及外部链接保留 |
| UI规范v3.0出版物 | 旧品牌PDF/ZIP | v3.1新文件 | 保留原PDF/ZIP和v2.1，旧入口链接现行版 |
| Bundle ID、namespace、RN module、签名 | com.inkmemory.mobile / InkMemory | 原值 | 保留升级、私有容器和原生装配身份 |
| OAuth、API、数据库、存储、事件、env | 原ink/Ink标识 | 原值 | 无迁移；认证、归属与数据继续原合同 |
| MCP clientInfo.name与插件标识 | 原协议值 | 原值 | 保持外部握手标识，iframe可见title单独更新 |
| 业务验证选择器 | 原品牌placeholder/权限标题/来源 | 当前名称 | 更新原验收脚本的可见文案预期，真实业务脚本本轮保持未执行 |
| 合成测试输入 | 显式传入的旧文案样本 | 原值 | 作为任意输入透传样本保留，现行应用选择器采用新名称 |
| 冻结分析prompt、历史记录、旧设计和引用资料 | 原名称 | 原值 | 保留版本语义和来源；现行名称指向新需求 |

## 实施前评审

[PRD](../prd/mobile-app/app-brand.md)及[正式设计](../design/multi-platform/app-brand-interaction.md)已完成范围与方案比较。选定共享名称常量配合原翻译，原生及出版属性沿现有入口更新。内部标识迁移缺少依赖需求，保留原值。名称修订无新增业务状态、确认、引导或账户步骤。修改范围服务于品牌更名；技术验证、设备采用和发布分别登记。

## 实现与验证

当前源码完成名称修订。Web与Native共享`frontend/app/_dream/constants/brand.ts`，后端公开内容复用既有`seo_content.APP_NAME`。原生属性与静态使用说明按原入口更新。当前规范源与17幅SVG沿原导出工具生成v3.1 PDF，旧出版物完整保留。

| 工作项 | 实现对应 |
| --- | --- |
| 名称、本地化和默认回退 | brand.ts、i18n.ts；`ink-language`保持 |
| 启动、页头、登录外层和无障碍 | StartupScreen、SessionGate、App、ScreenFrame；原操作保持 |
| 导航、关于、提示和分享 | Sidebar、AboutView、aboutPresentation、AIInputDock、ThreadImageCard、exportThreadImage、slashSkillCommands |
| 公开元信息与发现 | RootLayout、seo_content、两种FastAPI展示标题 |
| 原生系统属性 | Info.plist、AndroidManifest.xml、AndroidPlatformActions；原包标识与回调保持 |
| 当前设计与说明 | app-brand PRD/设计、相关现行PRD、启动稿、UI规范源、三份公开草案 |
| 出版物 | Kastention-App-UI-Guidelines-v3.1.pdf、Kastention-UI-v3.1-Editable-Sources.zip |

本轮未执行应用发布构建，文档导出沿原ReportLab工具完成。远程部署、设备安装、商店发布、真实账户与模型调用均在本轮授权范围之外。

### 本地验证回执

专用`luna_test_runner`执行确定性检查，主Agent读取原始日志及截图。证据目录为`/tmp/kastention-rename-20261102/validation/`。临时配置精确指向源码目录，使用已安装Chrome，真实账户、数据库与模型调用数量为零。

| 命令或阶段 | 退出码 | 关键结果 |
| --- | --- | --- |
| `corepack pnpm run native:typecheck` | 0 | 修正导入后Native类型检查通过 |
| `corepack pnpm exec tsc --noEmit --pretty false --incremental false` | 0 | 修正导入后Web类型检查通过 |
| `backend/.venv/bin/python -m unittest discover -s backend/tests -p test_seo_content.py` | 0 | 4项通过，名称与原URL/索引边界保持 |
| `python3 .agents/skills/ink-dream-playwright-qa/scripts/preflight.py` | 0 | 现有依赖可用；复用本机Chrome，无浏览器下载 |
| 源码`native-session-gate.spec.ts`，临时配置channel=chrome、workers=1 | 0 | 15项通过，原准备、登录、诊断和恢复检查保持 |
| 同一原fixture追加名称/几何检查 | 0 | 16项通过；320×568、390×320、390×844准备/关于页名称完整，无横向溢出 |
| bundled Python执行`docs/prd/mobile-app/ui-guidelines/export_pdf.py` | 0 | 19页、17图，overflow为空；后续渲染独立核对 |

初轮两项类型检查发现注释内导入插入位置错误，修正后通过；失败日志保留。首次Slash测试发现旧构建目录内的同名源码，56项通过只作为初次结果，最终数量以精确源码重跑为准。设备系统名称、安装升级、完整真实业务、远程公开页面和商店登记继续独立验收。

## 登录图片交付

原图位于`frontend/public/login-banner.jpg`，检查确认中央含旧品牌文字。本轮使用内置image_gen的text-localization编辑，产物保存为`frontend/public/kastention-login-banner.png`，Web登录与元信息共用`BRAND_BANNER_PATH`。原图保持完整，运行引用采用新图；主Agent已检查字样为Kastention，水彩、指南针、心形、云与书本元素保持原构图语言。

生成提示词：

```text
Use case: text-localization. Asset type: existing application login background and social preview. Edit target: the provided 1408x768 watercolor banner. Replace only the large central words “Ink & Memory” with the exact single word “Kastention” (K a s t e n t i o n). Match the original purple-blue hand-painted watercolor lettering, approximate central baseline and visual weight, and keep the complete word easily readable. Preserve the original landscape composition, light paper texture, colorful watercolor splashes, compass, heart, cloud, open book, and all peripheral artwork. Keep the original visual identity, colors, objects and spacing; no new visual system, slogans, extra text, characters or watermarks. Deliver a landscape banner with the same aspect ratio as the original. Text verbatim: Kastention.
```

### 最终名称专项与出版检查

| 命令或阶段 | 退出码 | 关键结果 |
| --- | --- | --- |
| 最终`corepack pnpm run native:typecheck`与`corepack pnpm exec tsc --noEmit --pretty false --incremental false` | 各0 | 新图片共享路径接线后的Native/Web类型检查通过 |
| 源码SlashSkillCommands单文件临时Playwright配置，`--reporter=line --workers=1` | 0 | 精确源码8项通过；旧build副本退出最终计数 |
| 原`more-navigation.spec.ts`，Chrome单文件配置 | 0 | 8项通过；增加桌面品牌英中切换检查的临时副本9项通过 |
| AboutView Web临时fixture | 0 | 1项通过，1440×900与390×844完整名称，无横向溢出 |
| 原RootLayout经临时esbuild装载，Node读取metadata与JSON-LD；原i18next英中资源读取 | 0 | title/applicationName/OG/JSON-LD采用Kastention；中文为卡片结构；工具变量插值保持；配置URL仍控制canonical及图片输出 |
| `plutil -lint frontend/ios/InkMemory/Info.plist`、Python XML/plist身份读取与修改Python文件语法编译 | 各0 | 展示名称更新；原Bundle ID变量、applicationId与两类回调保持；Python语法通过 |
| bundled `pdfinfo`、`pdftoppm -png`与文本/版式检查 | 各0 | 19页全部渲染；17幅SVG可读取；PDF旧品牌匹配0、overflow为空 |
| 本轮Markdown路径与Mermaid检查 | 0 | 61份Markdown、498条本地引用，路径缺失0；62个Mermaid在本机Chrome渲染，失败0，含新增2图 |
| 三份公开Markdown/HTML正文归一化比较 | 0 | 三份正文缺失段落0、可见旧品牌匹配0；原草案状态和运营信息保持 |
| 源文件包检查 | 0 | ZIP CRC通过；37项仓库源文件字节匹配，另含1份独立包装说明 |

主Agent核对全部19页联系图，并放大检查第11页的新字标、页脚与骨架；Web及Native关于页、准备页截图的名称完整。旧v3.0 PDF/ZIP和v2.1 PDF在Git中保持原始字节状态。文档验收覆盖名称、引用、图语法与版式；设备与真实业务沿各专项资格。

原Markdown标题存在14个HEAD已有锚点缺口，本轮新增路径/标题锚点失效为零；15条源码`#Lnn`按行号引用处理。分类回执见证据目录的`docs-links-mermaid-final-filtered.json`。初次公开正文比较将列表/链接格式计为缺失，修正harness归一化后通过，正文无需追加修订。初次Mermaid参与者`LINK`命中语法保留字，已改别名`EXTERNAL`；另修正iOS设计的一处启动PRD相对路径。EOF空行按本轮文档格式检查收敛。

### 补充回归缺口

| 命令与场景 | 退出码 | 实际证据及范围 |
| --- | --- | --- |
| `corepack pnpm exec playwright test --config playwright.brand-rename-provider-free-temp.config.mjs --reporter=line --workers=1`，精确ChatSubagentStatus临时副本 | 1 | 页面显示`Task relationships are temporarily unavailable`，预期任务关系按钮缺失；尚未执行新名称权限标题断言 |
| 同一临时配置精确Dream/Chat综合fixture，追加`--grep 'S04'` | 1 | 首次fake SSE请求数期望1、实际0，5秒超时；尚未执行新名称权限标题断言 |

两项失败保留原状态；本轮完成独立名称/i18n检查，完整任务关系与Dream/Chat确认旅程继续待验收。修改范围限定展示名称、原验收选择器与文档，无新增Chat业务修复。真实账户/模型脚本只更新名称选择器，本轮执行次数为零。

### 交付与剩余验收

本地交付包含应用名称源码、产品需求、交互评审、现行规范PDF/SVG及源文件包。英文默认Kastention，中文应用称谓沿原语言设置采用卡片结构。图标、主题、布局、业务、认证和内部身份保持原合同。

剩余验收包括：两项补充隔离综合场景；iOS/Android完整包构建后的系统桌面名称与原位升级；实体设备展示与完整真实业务；远程Web采用、商店名称登记和正式发布。本轮验证覆盖源码、隔离界面与文档；包体验证、设备采用、真实账户和发布分别留待对应任务。设备安装、真实账户写入、远程部署和商店发布需要对应授权及现场证据。

精确临时配置、命令及原始输出见`/tmp/kastention-rename-20261102/validation/commands-and-configs.md`与同目录日志。临时配置、spec和自有服务已清理，页面截图、PDF单页与联系图留存供复核。

收尾证据归验证目录的`closure-final.log`与`closure-final.json`：历史三份出版物与HEAD字节一致，临时配置/spec/bundle和自建进程清理完成。源包根README为包装说明，仓库README继续持有产品介绍。
