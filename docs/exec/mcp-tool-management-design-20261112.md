<!-- [Input] Notion新增Web/App MCP前端参考、现行资源连接源码与音频接入边界。 -->
<!-- [Output] 范围判断、设计交付、模块对应和文档验证记录。 -->
<!-- [Pos] 本轮只改产品/开发文档与参考资产；新UI和业务接线未实施。 -->
<!-- [Sync] 2026-11-12: 共用MCP卡片管理与App音频选择的设计补充。 -->

# 两端MCP工具管理设计补充

## 目标与工作边界

用户在[近期需求的新增前端段落](https://app.notion.com/p/40b30b7547c380cd9930c384ab35023c#41530b7547c380f48038c931c30580b8)要求Web和App按参考图实现MCP工具加载交互。读取了页面中ui交互、原音频约束和未完成的功能边界，并取得图片block `41530b75-47c3-8052-94f5-cb3419a94221`原图。参考图为MCP服务管理页，包含连接工具入口、连接卡片、状态和断开操作。

本轮收敛为设计同步：两端共用资源链接页结构、卡片行为和真实状态；音频工具保持App专属、默认关闭、Low-Sensitivity与AskUserQuestion。源代码、配置、依赖、服务、数据库、设备及模型保持原任务范围。本轮不实施新UI或播放器。

## 优化目标

复用原Settings资源链接页、MCP连接/认证/详情/API及后端turn快照，补充卡片布局、启停保存/冲突反馈、设备工具选择和两端骨架。明确Agent编排、MCP能力发布、管理组件、音频问答与播放器职责。远程MCP由原管理接口启停和后端快照加载，客户端tools只选择固定平台type；界面不携带任意MCP配置或凭据进入Chat请求。保留原音频三图与历史版本。交付产品稿、前端接入增量及目录引用，定向验证清单、片段、历史边界、图示和空白。

## 发现、定义、比较与交付判断

- 发现：Notion参考图为已连接应用卡片网格，用户新增两端共用要求；现行ClaudeMcpResourceSection已有Web/Native版本，useClaudeMcpResources/useClaudeMcpServer和claudeMcpApi提供原配置、认证、版本更新与清单流程。
- 定义：连接服务、服务enabled、当次Agent可用范围与音频播放回答分别表达；连接和工具选择不直接执行工具或播放音频。
- 比较：采用原资源链接页的卡片组织与原管理接口；额外应用商店、第二连接store和客户端MCP配置注入退出方案。独立Notion连接器继续原业务，MCP Apps使用策略与端侧音频选择独立。
- 交付：通用资源连接PRD维护两端页面骨架、卡片与状态；前端专项追加管理/加载接口和三幅业务图，原音频三图保持；原稿独立归档，Settings与目录增加引用。

## 源码核对与接入状态

| 模块 | 当前证据与后续工作 |
| --- | --- |
| Web/Native MCP列表 | 原组件与共享hook已存在；卡片重排和列表快捷启停为新增设计 |
| 原新增／认证／详情 | configure、start/cancel/logout、详情inventory与原removable边界继续复用 |
| 原更新helper | 提交完整配置和expected_revision；快捷enabled改动须沿当前配置与CAS，失败保留期望 |
| 当次MCP加载 | 原Service读取actor/workspace enabled快照；新revision在后续turn生效，运行中快照保持 |
| 设备音频工具 | 后端固定type和问答已有接入；本地资源卡、选择状态、媒体组件和原生播放器待实现 |
| Web/App平台资格 | 共享管理语义；平台执行资格按实际能力；未核对能力不展示可执行承诺 |
| 后续研究 | Notion中的Bridge、IDENTITY/USER/HEARTBEAT与多Agent生命周期保持未设计／未实施范围 |

## 交付物

- [资源连接产品稿](../prd/resource-connections/mcp-tool-management.md)：参考图、产品规则、桌面/窄屏骨架及验收。
- [前端接入稿](../design/multi-platform/mobile-clock-audio-frontend.md#web与app共用的mcp管理交互2026-11-12)：管理API、默认/期望/实际/版本、平台资格及正常/异常/状态三图。
- [音频组件产品稿](../prd/mobile-app/ios-system-player.md)：补通用MCP管理与App专属音频的关系。
- [Settings入口](../prd/Settings.md#2026-11-12-web与app工具连接卡片)：保留原页面与专项链接。
- [补充前原文](../design/multi-platform/history/mobile-clock-audio-frontend-before-mcp-management-20261112.md)：逐字保存原音频前端稿及原三图。

页面原始参考与相关段落摘录保存于本机`frontend/output/mcp-tool-selection-design-20261112/`，仅保存本任务相关内容；未保存短期签名下载URL。参考图保存在产品资产目录，标为布局对照。

## 文档验证

定向文档清单、引用/片段、历史原文及六幅前端图示由验证Agent检查；实际命令、退出码和结果在完成后追加。本轮不执行应用功能、真实MCP连接、Agent模型调用或播放验收。

### 验证结果

| 命令 | 退出码 | 关键结果 |
| --- | --- | --- |
| `node frontend/output/mcp-tool-selection-design-20261112/checks/validate-docs.mjs` | 0 | R2：14份Markdown清单及头注释有效；本地链接131项、历史路径6项、片段39项，断链0；新正文禁用词违规0 |
| 同一命令的Mermaid阶段 | 0 | 前端稿六图parse/render和实际SVG几何均通过；原三图与补充前快照一致，新增三图覆盖MCP管理、失败恢复和状态转换 |
| 定向 `git diff --check`、`git diff --cached --check` | 0 | 当前/暂存范围无空白诊断；新增未跟踪文档另作空白扫描，问题0 |
| 参考PNG有效性检查 | 0 | 图片1200×517，来源与用途已标明 |

R1验证器将App专属/默认关闭规则限定在前端增量稿匹配，实际规则由新产品稿维护；修正检查器取证位置后R2通过，业务要求保持。历史原文除围栏分隔换行外与本轮前置快照一致；三幅原音频图在现行稿中原样保留。

主代理读取原始报告和命令回执。输出位于`frontend/output/mcp-tool-selection-design-20261112/checks/`，包含`command-receipt.md`、`docs-validation.json`及六张SVG。浏览器console/page/request错误与外部网络请求均为零，浏览器已关闭。该结果属于文档与图示验证，新卡片交互、真实MCP连接、端侧能力选择与音频播放均未在本轮实施或验收。
