<!-- [Sync] 2026-10-09: 原始测试回执仅保留本机；正文保留命令、退出码和结论，不建立指向忽略目录的仓库链接。 -->
<!-- [Input] 用户要求实际执行双钻石；图片业务目的、现行稿与2026-10-07研究证据。 -->
<!-- [Output] 问题收敛、交互选项裁决、文稿修订、影响评估和本轮独立检查回执。 -->
<!-- [Pos] 本轮文档重做记录；不实现图像功能，不替代功能或真实模型验收。 -->
<!-- [Sync] 2026-10-09: 实际稿独立评审两项问题均已修订并复查关闭；文档复查exit 0，三图渲染通过，交付限于设计文档。 -->

# 聊天图片设计：双钻石重做记录

本记录中的 `frontend/test-results/` 文件是本机验证产物，已由 Git 忽略；命令与结果摘要保留在本文，原始文件不随仓库提交。


本轮执行用户要求，不追加规划提示词，不新建重复执行聊天。复用[既有执行任务](image-generation-design-20261007.md)的研究及技术说明，修改现行产品文档。源码和官方接口证据仍标为2026-10-07基线，没有冒充本轮重新调研或当前客户端观察。

## 发现：从已有证据重新看问题

输入是用户已经表达的目的、源码研究及原设计，不虚构访谈、观察或使用数据。

- 用户要在聊天里生成、编辑、查看并继续使用图片，要求与Codex有证据的交互对齐。
- IM已有工具、附件、图片查看和历史基础，缺少生成执行及完整结果衔接；Claude有通用Tool入口，换Key不等于支持Responses图像工具。
- Codex恢复代码只能支持所读版本的结论，当前界面及私有上游仍未确认。
- 原稿的主要缺陷是先枚举功能，缺少问题定义和方案取舍；保存/历史/后续引用重复拆分，用户看不出为什么这是一套合适的设计。

证据见[研究与文件/符号/行号索引](../design/claude-agent/image-generation-source-research.md)和[完整调用/API对比](../design/claude-agent/codex-image-generation-call-comparison.md)。当前界面无法观察的既有记录继续有效，不绕过访问限制。

## 定义：确定要解决的问题

要解决的是“图片需求不能在对话中形成可继续使用的结果”，不把“接通某个接口”作为业务目的。成功链路：提出需求 → 获得图片 → 查看下载 → 继续修改 → 重开后继续使用。过程准确、原图保留和恢复不意外生成，是链路完成的条件。

边界是已有聊天及当前会话参考图。交付为调研和设计；本轮不改应用/测试源码、服务、账户、数据库或模型，不调用Provider，不实现新图片页面或后台任务。

## 发展：比较后作出选择

| 候选 | 符合目的的部分 | 代价或缺口 | 裁决 |
|---|---|---|---|
| 聊天发起、回复显示图片 | 需求、结果和修改在同一处；已有查看和历史可复用 | 必须补齐生成、文件保存及必要回复衔接 | 采用 |
| 独立生成页面 | 提供专门创作空间 | 增加上下文切换及另一套入口/历史，当前无此需求 | 舍弃 |
| 工具详情或文件链接作为唯一结果 | 接入较少 | 图片难以发现，重开和继续交流未形成完整体验 | 舍弃 |

这三项是设计候选，不是已实现功能或真实用户测试结论。API选型独立于上述交互取舍：保留一个内部图像Tool，首期只接一种已发布授权能力。未有实际Provider与Admin合同，不能声称Codex使用Responses或替IM确定上游。

## 交付：修改实际稿，再检查

已重写[正式稿](../design/claude-agent/image-generation-interaction-design.md)与[PRD](../prd/chat/image-generation.md)：先给出目的和所选交互，再解释证据、范围和取舍；合并保存/历史/后续使用，功能模块只写用户获得的能力；保留桌面/窄屏骨架、正常/异常/状态三图与验收矩阵。

新增“原需求保留在会话而非自动回填输入框”说明，避免引入未经设计的输入状态和重试按钮。异常图将停止结果明确经过ClaudeAgentService返回ChatView，与原通道一致。实施说明保留两种API、输入输出、认证/权限/Schema检查、真实调用关联、安全文件生成及原持久化合同。

重做前正式稿与PRD逐字另存为[正式稿历史](../design/claude-agent/image-generation-interaction-design-20261009-double-diamond-history.md)及[PRD历史](../prd/chat/image-generation-20261009-double-diamond-history.md)，不覆盖前一轮历史；四份历史的字节/SHA基线在history-baseline.json（本机文件 `frontend/test-results/image-design-double-diamond-20261009/history-baseline.json`）。

## 影响评估与验证计划

| 范围 | 本轮影响 | 检查 |
|---|---|---|
| 用户发起 | 原聊天/附件入口、明确参考对象 | 正常流程与两种骨架一致 |
| Agent/Tool | 保留Claude与单一内部工具方向 | Key判断、授权、未实现标记及最小范围 |
| 消息/事件 | 结果直接在回复；原通道不变 | 图示、术语及实施说明一致 |
| 前端反馈/图片 | 合并重复功能，保留查看器、可访问性及读取恢复 | 全部状态和可用操作匹配 |
| 文件/权限 | 现有访问与新增安全发布合同不变 | 参考图、权限、文件错误不漏项 |
| 保存/历史 | 重开后继续使用为成功条件 | 保存、重开、继续编辑及保存失败齐全 |
| 失败/停止/重试 | 明确重新加载与再次生成、拒绝/等待停止不发起 | 各错误和恢复路径、已完成图片保留 |
| 兼容性/Schema | 无业务代码或数据库改动 | 不增加Runner、事件、表、降级或环境分支 |

按luna-test-stage将确定性文档检查交现有luna_test_runner。检查实际稿的问题定义与取舍、完整流程/状态/恢复/验收一致性，再执行具名Markdown清单、路径/行号、JSON、历史字节检查及三张Mermaid的parse/render。使用本机Chrome一次轻量启动，不安装浏览器；只关闭本轮自有浏览器和Vite进程。文档检查不作为技术功能或真实业务验收。

## 本轮回执

独立评审已返回，主执行者核对原始输出并修订两项问题：

1. Chat目录新增Sync位于标题前而合同注释位于标题后，造成头部检查失败；将原标题移至合同注释后，保留所有Sync和目录条目，不放宽检查。
2. 短实施说明只写“首期一种”，没有带入完整对比稿的条件性取舍；已增加选择条件表：两种能力均满足时优先Image API，已选Provider仅支持Responses时适配Responses，均不满足则不接入。没有断言当前Codex上游、费用或质量，也不增加双接口fallback。

首次评审（本机文件 `frontend/test-results/image-design-double-diamond-20261009/consistency-review.md`）确认业务目的、候选取舍、六模块功能描述、完整流程与恢复、文图和验收一致，未发现新增无依据产品或架构能力。首次命令commands.json（本机文件 `frontend/test-results/image-design-double-diamond-20261009/commands.json`）记录：

| 命令 | cwd | 退出码 | 关键结果 |
|---|---|---|---|
| `python3 frontend/test-results/image-design-double-diamond-20261009/check-docs.py` | 仓库根 | 1 | 13文件中12文件头通过；10清单、153本地链接、37行号、8JSON及4份历史SHA通过；唯一失败为Chat目录文件头顺序。 |
| `node test-results/image-design-double-diamond-20261009/render-mermaid.mjs` | frontend | 0 | 本机Chrome一次启动成功，正式稿3/3图parse/render并生成SVG；自有Chrome/Vite关闭。 |
| 限定11路径的`git diff --check`，完整命令见commands.json | 仓库根 | 0 | 无空白错误；未跟踪文件另由Python检查。 |

原始输出：文档初验（本机文件 `frontend/test-results/image-design-double-diamond-20261009/check-docs.out`）、图示渲染（本机文件 `frontend/test-results/image-design-double-diamond-20261009/render-mermaid.out`）、逐图结果（本机文件 `frontend/test-results/image-design-double-diamond-20261009/mermaid-receipt.json`）、空白检查（本机文件 `frontend/test-results/image-design-double-diamond-20261009/git-diff-check.out`）。初次失败与首次评审保留。修订后的独立复查（本机文件 `frontend/test-results/image-design-double-diamond-20261009/consistency-review-rerun.md`）确认两项均已关闭，未发现过度设计：新增能力均服务于同一聊天中的图片持续使用，未引入无业务依据的页面、控制通道、运行分支或数据库能力。

复查命令（本机文件 `frontend/test-results/image-design-double-diamond-20261009/commands-rerun.json`）及原始输出（本机文件 `frontend/test-results/image-design-double-diamond-20261009/check-docs-rerun.out`）记录`check-docs.py` exit 0：13/13文件头、10清单、160本地链接、37行号、8JSON、4/4历史SHA，errors=[]；22外部链接未联网核验。限定11路径`git diff --check` exit 0，输出（本机文件 `frontend/test-results/image-design-double-diamond-20261009/git-diff-check-rerun.out`）为空。三张图在修订中未改变，不重复启动Chrome。

主执行者已核对初验和复查的原始JSON/stdout及逐图结果。本轮设计、PRD、目录与历史交付完成；补录回执后再执行一次文档/空白检查，最终回执保存为同目录`commands-final.json`、`check-docs-final.out`与`git-diff-check-final.out`。新图像功能未实现，不宣称功能或真实模型验收完成。

## 尚未验证与实施前条件

本轮没有新增用户访谈、当前Codex界面观察、联网重验API、业务E2E、真实模型请求或生产写入。新功能尚未实现，不能取得真实业务验收结论。实施前需确认Admin已发布的图像授权/计费与结果合同、参考图映射、持久文件访问，以及实际Provider路径。实现后再运行完整技术链，按仓库协议使用指定正常账户、模型及已有业务实体验收。

原执行任务已经登记，本轮不递归创建聊天或新目标；本轮独立评审及fresh回执已闭合文档工作；`get_goal`本轮返回null，没有活动目标可标记，未为本次文档修订另建目标。旧目标完成状态不作为本轮验证证据。
