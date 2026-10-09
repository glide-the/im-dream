<!-- [Sync] 2026-10-09: 原始测试回执仅保留本机；正文保留命令、退出码和结论，不建立指向忽略目录的仓库链接。 -->
<!-- [Input] 用户重申的任务目的、业务描述写作要求和现行图像PRD/正式设计/源码对比。 -->
<!-- [Output] 现行稿重写、原文保留、影响评估、实际稿评审与本次文档检查回执。 -->
<!-- [Pos] 本轮文档重写记录，不实现新图像功能，不替代前轮技术或真实业务验收。 -->
<!-- [Sync] 2026-10-09: 业务重写/技术合同分离完成；Luna实际稿评审无新问题，11文档/两历史SHA/三图渲染均有fresh exit 0回执。 -->

# 聊天图像设计：按任务目的重写记录

本记录中的 `frontend/test-results/` 文件是本机验证产物，已由 Git 忽略；命令与结果摘要保留在本文，原始文件不随仓库提交。


本轮按用户最新要求直接改写最终设计，不输出或追加规划提示词。目标是让业务正文清楚回答用户能完成什么、各模块提供什么、哪些事情在本次范围内；源码、协议、权限与保存的执行细节归独立实施说明。既有研究证据沿用2026-10-07读取范围，不以此次文字重写宣称当前接口或Codex界面得到重新观察。

## 范围与顺序

先逐字保存现行正式稿与PRD，再重写两份业务正文，提取必须保留的实施合同到独立说明；同步现行引用和目录。实际文稿完成后，用luna-test-stage指定的luna_test_runner检查完整业务覆盖、目标/边界一致性、历史SHA、文件头/清单/引用与Mermaid实际渲染。主执行者修订问题，取得fresh回执后交付。

本轮只改文档及具名验证产物。不会修改应用源码、现有测试、运行服务、账户、数据库、模型配置或调用图像Provider；不创建重复执行聊天。旧测试结果仅保留，不作为本轮回执。

## 历史原文

- [正式稿原文](../design/claude-agent/image-generation-interaction-design-20261009-history.md)：重写前完整内容与四张原图逐字保留。
- [PRD原文](../prd/chat/image-generation-20261009-history.md)：重写前完整内容与桌面/窄屏骨架逐字保留。
- SHA与字节基线保存在`frontend/test-results/image-design-purpose-20261009/history-baseline.json`；由本轮检查核验，不修改历史文件头或原图。

## 影响评估与检查选择

| 范围 | 本轮文档处理 | 验证范围 |
|---|---|---|
| 发起/编辑 | 保留当前聊天与附件入口，以用户行动描述需求。 | 正文、骨架和正常流程一致。 |
| Agent/Tool | 保留通用MCP接入判断，注册、校验和Provider细节移入实施说明。 | 技术合同完整，没有把新能力写成已实现。 |
| 消息/事件/前端 | 描述处理反馈、图片展示、查看下载；原事件/组件名只用于实施映射和图示。 | 状态表、三张图与验收一致，不制造进度或新事件。 |
| 文件/权限 | 业务稿说明当前会话图片范围；实施说明保留所有权与安全文件发布要求。 | 不丢原权限合同，不新增用户确认。 |
| 保存/历史 | 分开“图片可见”和“会话保存”；保留重开与继续引用。 | 正常及保存失败路径齐全。 |
| 失败/停止/重试 | 用用户可理解反馈与下一步动作描述，保留不自动重复生成的规则。 | 图示和验收覆盖生成、结果、读取、中断、取消、保存失败。 |
| 兼容性/数据库 | 原文本/Tool/媒体和运行路径不改；技术所有权与Schema规则保留。 | 文档追踪，无程序/数据库检查或业务验收。 |

## 当前状态

现行正式稿与PRD已重写，技术合同独立维护；历史原文、清单与现行引用已同步。Luna已基于实际稿完成独立评审与本轮文档检查，回执经主执行者核对；本次文档交付完成，新图像功能仍未实现或验收。

## 主执行者已完成的稿件修订

- 目的集中为在现有聊天中得到、使用和继续修改图片；各功能模块只写功能描述。
- 将JSON、接口字段、真实调用ID、保留名、权限、文件安全和数据库合同从业务正文移到实施说明，不以删除细节代替分工。
- 两种上游继续作为可选接入，首期只选一种；保留CLI不能仅靠换Key取得能力、Image API仍需图像模型、Codex上游未知的原研究边界。
- 保留原授权区和停止，不增加确认；参考图通过原输入/附件指定，不设计新的选择器。
- 原图、已完成图片保留；重新加载只读取文件；会话保存失败与图片读取失败分别说明，断线不自动重发。
- 正常/异常图的授权回复经ChatView与ClaudeAgentService返回Runner，避免把ToolConfirmationDock写成直接控制Runner。
- 实施说明保留新图像结果不使用通用auto-register fallback、重复事件不重复发布，以及原partial保存要求。

人工自查判断：配套实施说明承担原有必要技术合同，业务稿没有新增产品功能或扩大运行路径。下述独立评审确认本次分工和业务覆盖一致；文档回执不能替代功能验收。

## 独立评审与验证回执

本轮复用`/root/image_comparison_validation`的`luna_test_runner`，使用新的具名目录和fresh命令；没有复用2026-10-07检查结果。独立实际稿评审（本机文件 `frontend/test-results/image-design-purpose-20261009/consistency-review.md`）未发现具体矛盾、引用或符号问题，确认业务模块只写功能描述，目的/边界/流程/状态/恢复/验收与三图一致，原技术合同仍在实施说明中，未增加后台任务、表、Runner、控制通道或方案选择UI。

| 命令 | cwd | 退出码 | 实际结果/覆盖 |
|---|---|---|---|
| `python3 frontend/test-results/image-design-purpose-20261009/check-docs.py` | 仓库根 | 0 | 本轮初验11/11文件头、8清单、127本地引用、37行号、8JSON，errors=[]；两历史稿SHA与字节完全相同。覆盖现行/历史PRD、正式稿、实施说明、研究/对比、exec与三目录。 |
| `node test-results/image-design-purpose-20261009/render-mermaid.mjs` | frontend | 0 | 本机Chrome一次startup通过，正式稿3/3图均parse并生成SVG；自有Chrome/Vite已关闭。 |
| `git diff --check -- docs/design/claude-agent/image-generation-interaction-design.md docs/design/claude-agent/image-generation-implementation-notes.md docs/design/claude-agent/image-generation-interaction-design-20261009-history.md docs/design/claude-agent/image-generation-source-research.md docs/design/claude-agent/codex-image-generation-call-comparison.md docs/design/claude-agent/.folder.md docs/prd/chat/image-generation.md docs/prd/chat/image-generation-20261009-history.md docs/prd/chat/.folder.md docs/exec/image-design-purpose-rewrite-20261009.md docs/exec/.folder.md` | 仓库根 | 0 | 无空白错误；未跟踪新文件也由Python空白/换行检查覆盖。 |

原始stdout：文档检查（本机文件 `frontend/test-results/image-design-purpose-20261009/check-docs-rerun-20261009.out`）、图示渲染（本机文件 `frontend/test-results/image-design-purpose-20261009/render-mermaid.out`）、逐图JSON（本机文件 `frontend/test-results/image-design-purpose-20261009/mermaid-receipt.json`）、空白检查（本机文件 `frontend/test-results/image-design-purpose-20261009/git-diff-check-rerun-20261009.out`）。该目录同时保留初次输出及三个SVG；本轮没有失败验证命令。回执写入后仅复查文档/空白，最终输出文件为同目录`check-docs-final.out`和`git-diff-check-final.out`，图未变不重复启动Chrome。

## 未验证与任务边界

本轮没有运行业务页面E2E、模型/API、数据库或真实账户，没有重新观察Codex当前界面、验证其私有执行路径或联网重验22个官方/外部引用。没有修改应用源码、既有测试、模型配置或用户服务；没有数据库或业务记录可清理。主执行者仅保留本轮文档与具名产物，前轮回执与他人改动均保留。

新功能实施仍需Admin发布已授权图像能力、确认参考图映射和持久文件访问，并完成完整技术链及指定账户/实体/模型的真实业务验收。此次交付只确认设计稿按任务目的重写、技术要求未丢失、文档和图示通过检查；不宣布图像功能完成。
