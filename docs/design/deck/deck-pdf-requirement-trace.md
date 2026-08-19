<!-- [Input] Deck设计需求.pdf visual pages, extracted text, and explicit task priority. -->
<!-- [Output] Page-by-page authoritative requirement ledger and implementation mapping. -->
<!-- [Pos] Primary-source trace for the Deck redesign. -->
<!-- [Sync] 2026-08-17: map Settings to full inventory and the latest skeleton to user published-clean plus system-default Deck home. -->

# `Deck设计需求.pdf` 逐页需求追踪

## 来源身份

- 文件：`docs/design/deck/Deck设计需求.pdf`
- 创建/修改时间：2026-08-16 17:24:21 CST
- 页数：3（A4）
- SHA-256：`5d440adc56e73b4269fcf7886933df021355399ed69854783460cf3e2d1c3671`
- 核对方式：`pdfinfo`、`pdftotext -layout` 和三页 160 DPI 图像逐页视觉检查。

本文只记录 PDF 明确表达的事实。任务显式约束高于 PDF；旧设计只补充 PDF 未定义的业务状态，
不得推翻 PDF 的最新页面布局。

## 第 1 页：设置式启停列表

PDF 原文为“页面布局”“设置的启用禁用配置”“Deck首页布局”。红框中的视觉基准具有以下明确结构：

1. 页面内容是插件设置式扁平列表，不是传统管理表格或 dashboard 卡片。
2. 顶部有分类/数量筛选和搜索。
3. 每行由图标、名称、简短说明和最右侧启停开关组成。
4. 行之间用轻分隔线和留白建立层级，不使用六列表头、彩色左边框或重操作按钮组。

实现映射：

| PDF 事实 | 当前实现 |
|---|---|
| 扁平行列表 | Settings / Work / Deck 的 `ul.deck-manager-list` |
| 图标/名称/说明 | `deck-manager-list__identity` |
| 行尾开关 | `role=switch`，成功后重新读取服务端事实 |
| 分类数量 | 全部/Chat/Dream 真实计数 tab |
| 搜索 | Work / Deck 全宽名称/说明搜索框 |

## 第 2 页：Deck 首页与创建菜单

PDF 原文为“用户新增Deck逻辑，点击创建弹出Deck新建菜单，可在下拉选项选择添加Deck市场”以及
“按照文档 # Deck 管理列表与版本交互设计实现整体功能设计，但是现在需要根据本文档更新页面布局”。

视觉基准的有效页面结构：

1. 顶部右侧放刷新与“创建⌄”。
2. 页面主内容居中，标题和说明保持 IM 层级；管理搜索移入 Work。
3. “已安装”使用横向小图标摘要；映射到 Deck 的“已启用”摘要。
4. 设置按钮位于“已启用”标题右上并直达 Settings / Work；完整分类与启停列表位于 Work / Deck。
5. 点击“创建”必须先展开菜单；确认“创建 Deck”后沿用原逻辑创建服务端对象，再弹出该 Deck 编辑器。

PDF 中“添加 Deck 市场”菜单项与本期显式“市场分发暂缓、不得出现市场入口”冲突，因此按优先级
排除。当前创建菜单只有真实可执行的“创建 Deck”；不得留下禁用市场项、灰色占位或空请求。
注册用户默认拥有的系统内建 Deck 仍必须在 Deck 主页面展示，并与用户自建 Deck 分组区分；该展示
不是社区发布、不是创建副本入口，可打开只读预览页，但不能打开维护弹窗。

## 第 3 页：市场尚未设计

PDF 明确说明：Deck 市场服务模块尚未设计；参考 `agent-skills-register` 仍缺系统集成 Deck 市场设计；
“暂时不设计插件市场”。结合本期更高优先级约束，全部市场注册、发布、安装和分发治理迁移至
[`../deck-register/README.md`](../deck-register/README.md)，当前 UI 与 API client 均不激活。

## 偏差禁止清单

- 禁止恢复六列表格、列头或窄屏表格转卡片方案。
- 禁止把 PDF 的“插件设置式列表”用于重做 Deck 主页面或 Settings 左栏；它只指导 Work 右侧内容。
- 禁止因为市场项出现在第 2 页就违反本期延期约束。
- 禁止用更新时间、Agent binding revision、插件版本或固定 `v1` 填充内容版本；只消费 capability-backed vN。
- 禁止在 Deck 管理页或编辑弹窗加入 Workflow；既有 Claude 插件引用选择属于 Deck 配置，不得再被布局重构误删。
- 禁止恢复 Community、发布到社区、`publishDeck` 或可被别人引用/创建副本入口；系统内建 Deck 仅作为注册用户默认内容展示。
