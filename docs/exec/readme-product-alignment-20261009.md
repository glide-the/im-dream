<!-- [Input] User's README update requirement, Agent.md README contract, current product designs and source navigation. -->
<!-- [Output] Copy-ready optimized prompt, treatment decision, delivered documentation scope and verification receipts. -->
<!-- [Pos] Execution record for the 2026-10-09 README product alignment; not a feature or deployment acceptance. -->
<!-- [Sync] 2026-10-09: retain first-pass history and record the Notion-based module rewrite, revised diagrams and bounded document checks. -->

# README 主功能对齐

## Optimized Prompt

```text
你是 Ink & Memory 的产品文档维护者和资深工程师。请完成两项工作：
一、判断 README 与当前项目主功能不一致的问题应如何处理；
二、按现行设计稿和当前实现完成 README 更新，并带上相关图片。

每轮任务规划前，先以 Expert Prompt Architect 的角色把本轮任务转换成
精确、专业、可直接执行的 Optimized Prompt，补齐输出、约束和验收要求，
再据此规划和执行；需求明确时不重复询问用户。

判断依据：
1. 读取 AGENTS.md、Agent.md、规则索引及受影响目录的 .folder.md。
2. 查找现行产品设计、业务 PRD 和实际导航，区分当前稿、历史稿和过程证据。
3. 以设计稿说明产品目标，以代码、配置、版本清单和验收回执说明实际边界；
   不将设计目标、隔离测试通过或旧部署回执写成当前功能全部可用。
4. 说明原 README 的定位、内容层级、功能描述和配图分别有哪些偏差。

实施要求：
1. 同步更新 README.md 与 README.zh.md，保持章节、命令、版本、边界和链接一致。
2. 先介绍产品是什么、核心功能和用户流程，再提供安装、架构、验证与排查入口。
3. 准确解释 Chat、Dream/Story Workspace、Decks/Agent、文件、任务、日历和资源连接。
4. 用用户能理解的文字说明价值；技术配置和故障码放在运维部分。
5. 复用安全且相关的现有图片，或制作基于设计事实的产品示意图。
   图片使用仓库相对路径，提供替代文本、来源及必要的功能状态说明。
   实际截图、示意图和规划内容应准确命名，不使用个人正文、账号或凭证做公共配图。
6. 保留精确 SDK/Runtime 安装与 PATH 校验、Admin Schema 所有权、认证/数据边界、
   capability 门槛、平台限制及恢复方式；配置示例与实际模板保持一致。
7. 只修改完成本需求所必需的文件，保留用户和其他 Agent 的改动、历史设计与原始图片。
   不为文档任务修改业务代码、数据库或现有服务。
8. 更新文件头和目录清单，不创建重复 PRD，不将 README 提升为新的产品规则所有者。

验收与交付：
核对中英文标题层级、命令及版本事实；检查 Markdown 链接、锚点、图片和目录清单；
检查 Mermaid 语法与图片显示；执行 git diff --check。
文档检查必须明确标注为文档验证，不能称为功能验收或真实模型测试。
报告处理判断、变更文件、图片来源，以及实际验证命令、退出码和关键输出；
注明 Git/服务状态及必要限制。交付完整可阅读的结果，不停在建议或计划。
```

## Optional Enhancers

- 如后续需要展示真实界面，可加入：“通过正常公开页面读取已授权界面，截取不含个人数据的区域；注明截图日期、页面与功能状态。”
- 如项目定位发生变化，可加入：“先对照新的现行产品设计重新判断主导航和主要用户流程，再更新总览图及双语 README，保持运维合同完整。”

## 任务一：处理判断

这是 README 信息组织与产品事实同步问题，应完成文档重构与配图更新。

| 偏差 | 判断依据 | 处理 |
| --- | --- | --- |
| AutoDL 部署在最前，产品能力压缩为长技术列表 | [现行导航](../design/story-workspace/product-scope-and-navigation.md)与 `StoryWorkspaceSidebar.tsx` 都以 Chat、Dream、Decks 为主入口 | 前置产品介绍、功能表和用户流程，安装运维保留在后半部分 |
| 旧写作界面仍承担主配图 | `assets/writing-area.png` 是早期写作界面，不能解释当前主导航和创作工作台 | 替换为有来源的双语产品总览图；保留原图文件 |
| Dream 仅有笼统的一句介绍 | [重入设计](../design/story-workspace/dream-workspace-and-reentry.md)和[Project/Episode 工作台](../design/story-workspace/project-and-episode-workbench.md)已定义同一 Thread、共享资产与分集产物 | 写明创作、阅读、审阅和重入流程，复用应用已有创作指引插图 |
| 设计与发布状态容易混淆 | MCP Apps 公开关闭，定时模型执行与 Notion 同步增量正常发布仍有记录中的门槛 | 单独说明功能可用状态，链接原始回执；不根据旧回执宣称当前上线 |
| 本机打开地址与前端模板不同 | `frontend/.env.example` 的公开 origin、issuer/resource、callback 使用 localhost | 双语入口改为 localhost，私有监听保留 127.0.0.1 |

原始 UI Design v2 PDF 是品牌和色彩概念稿，不是当前业务导航合同，因此没有将其中的商城等概念写成已实现功能。本文的产品事实以现行业务设计和源码为准。

## 任务二：交付范围

- [英文 README](../../README.md)与[中文 README](../../README.zh.md)：产品总览、六类核心功能、五步使用流程、剧本三阶段、资源连接、功能门槛及设计索引；保留安装、认证、版本、构建、排查和恢复合同。
- [英文总览图](../../assets/readme/product-overview.en.svg)与[中文总览图](../../assets/readme/product-overview.zh.svg)：静态矢量产品示意图，颜色取自 `frontend/app/_dream/styles/tokens.css`，具备 title/desc；不模拟当前页面截图。
- 剧本插图复用 `frontend/public/assets/story-workspace-guide-illustrations/01-mimo-xiaohei-workflow-triptych.png`，与 `StoryWorkspaceCreationGuide.tsx` 和创作工作台设计一致；正文标明第三阶段尚未实现。
- 精确安装版本保持不变；新增调用 `sdk_env` 公开函数的安装后 SDK/PATH Runtime 校验命令，不修改 resolver 或 Runtime。
- 同步根目录、assets/readme 和执行目录清单及文件头。

## 验证回执

所有检查仅覆盖本轮文档与图片，不代表真实业务、功能发布或模型验收。

| 实际命令 | 退出码 | 关键输出 / 检查范围 |
| --- | --- | --- |
| `python3 /tmp/ink-dream-readme-docs-20261009/check_readmes.py` | `0` | 7 份文档；113 处本地链接/图片引用、6 处图片引用、4 个锚点；14 个标题层级、5 个 bash 命令块完全一致；shell 与内嵌 Python 语法有效；18 项版本/平台/origin/功能值、2 张 SVG、13 项本轮目录清单通过。 |
| `qlmanage -t -s 1440 -o /tmp/ink-dream-readme-docs-20261009 assets/readme/product-overview.en.svg assets/readme/product-overview.zh.svg` | `0` | 两张 SVG 均生成预览；随后以 `view_image` 检查，文字与栏目无裁切、无重叠。 |
| `node /tmp/ink-dream-readme-mermaid-20261009/validate-readme-mermaid.mjs` | `0` | `PASS README.md block 1`、`PASS README.zh.md block 1`、`RESULT PASS 2/2 Mermaid blocks parsed`。由 Luna 验证 Agent 使用已安装 Chrome、既有 Playwright 和本仓 Mermaid，单次启动空页面解析；未安装浏览器或依赖。 |
| `git diff --check` | `0` | 无空白错误输出。 |

静态检查器解析双语章节映射和五个命令块，使用 `bash -n` 与 Python AST 检查命令语法，对本轮 Markdown 本地路径及锚点逐项校验；版本值与 `frontend/package.json`、`backend/pyproject.toml`、`sdk_env.py` 对照。未执行安装、migration、registry 下载或功能测试。Mermaid 原始日志由主 Agent 读取复核，浏览器由验证脚本的 `finally` 关闭。

两个 `/tmp/ink-dream-readme-*-20261009` 目录只含本轮检查器、结果日志和 Quick Look 预览，复核后由主 Agent 清理；正式 SVG 与应用原有插图保留。

## 工作区与运行状态

起始分支 `develop`，起始 HEAD `bd8681d1`；收尾只读观察为 `codex/current-work-20261009` / `a83cca00`，共享工作区期间发生了其他工作的分支与提交变化，本轮没有执行 Git 切换或提交。工作区已有图片设计、测试及执行目录改动；只增量更新共享的 `docs/exec/.folder.md`，保留其他内容。没有修改功能代码、数据库或用户已有服务，没有调用真实模型；本轮不提交、不推送、不发布。

## 后续修订：按具体功能编写

用户指出“从想法到创作项目”过于空泛，要求依据具体设计直接编写，每个模块只说明功能、目的和任务边界。本节是最新修订回执；上方提示词、首轮结构与验证保留为过程历史。本轮没有生成或执行新的规划提示词。

### 依据与处理

通过已连接的 Notion 读取用户指定的[项目说明](https://app.notion.com/p/ink-and-memory-38f30b7547c3804cb8a0d1250a3b8ae2?source=copy_link#e4f30b7547c3837ab5d4815f3f1b0e37)、任务管理模块和 Work 连接器设计。项目说明将产品定位于个人思维模式整理，并指出创作成果反馈统计、画布、知识库和完整制作链路尚未完成。历史笔记中的认证和自动写作建议描述由当前本地设计及实现校正。

- 删除泛化五步流程和含命令的剧本阶段表，以九个模块的自然语言功能描述替代：思维模式、Chat、写作与日记、回顾分析、任务与进度、定时任务与日历、资源连接、文件工作区、Dream。
- 思维模式说明采用同期 PRD（`docs/prd/deck/thinking-modes.md`）及[设计索引](../design/deck/README.md)，保留其他工作刚统一的中文名称；不将概念中的 Skills/MCP/Plugin 组合写成已交付的自动绑定功能。
- 写作说明依据[手动建议设计](../design/writing-manual-suggestions.md)和现有 `WritingSuggestionCell`；回顾说明依据[回顾分析 PRD](../prd/reflection-blog.md)与 `AnalysisView`。不延用早期自动生成建议或完整成果反馈系统的设想。
- Dream 明确以剧本组织和分镜为当前重点，保留现有创作插图，并标明图中下部制作能力为未来方向。
- 双语总览图同步为个人思维模式与九模块总览。技术 capability、安装、版本、认证和运维合同保留，部署门槛收进独立折叠说明。
- 同步根目录、assets 与执行目录清单；只编辑文档及 SVG，保留其他 Agent 的业务代码与设计改动。

### 本轮文档检查

所有结果仅为文档与配图检查，不作为功能、真实业务、模型或部署验收。

| 实际命令 | 退出码 | 关键输出与范围 |
| --- | --- | --- |
| `python3 /tmp/ink-dream-readme-modules-20261009/check_readmes.py` | `0` | 7 份文档；106 处本地引用、6 处图片引用、4 个锚点；双语 20 个标题层级、9 个模块、5 个命令块及链接目标一致；shell / 内嵌 Python 语法、19 项版本/平台/origin/功能事实、2 张无外部依赖的可访问 SVG、13 项目录清单通过。 |
| `qlmanage -t -s 1440 -o /tmp/ink-dream-readme-modules-20261009 assets/readme/product-overview.en.svg assets/readme/product-overview.zh.svg` | `0` | 两张更新后的 SVG 生成预览；通过 `view_image` 复核九模块内容及布局，无文字重叠。 |
| `git diff --check` | `0` | 无空白错误输出。 |

本轮 Mermaid 内容与当前 Git HEAD 一致，沿用上方首轮 2/2 解析回执，没有重复启动浏览器。静态检查器初次执行发现其 SVG 文本节点预期计数漏算页脚；修正检查器为 25 后通过，产品文件无需为此修改。临时目录仅包含本轮检查器与 Quick Look 预览，复核后清理。

收尾只读观察分支为 `develop`、HEAD 为 `b5c90efc`；工作区存在其他任务的未提交更改。本轮未切换分支、提交、推送、修改数据库或启动/停止服务。

### 独立提交范围

提交双语 README、两张产品总览图、受影响目录清单与本记录。同期思维模式 PRD 属于另一任务的未提交文档，README 的公开设计入口改用已入库的 Deck 设计索引；本记录保留调研时读取该 PRD 的事实。根目录与执行目录清单仅暂存本次 README 所需条目，其余任务的改动保留在工作区。

提交前以 `python3` 静态检查暂存内容，退出码 `0`：9 个文件、104 处本地引用均可在 Git index 中解析，双语标题层级、命令块和九模块一致，SVG XML 有效。`git diff --cached --check` 退出码 `0`。
