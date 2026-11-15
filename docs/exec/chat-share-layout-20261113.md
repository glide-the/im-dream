<!-- [Input] 用户要求AI Chat分享预览的布局和样式与ChatMessageList相同。 -->
<!-- [Output] 呈现统一的交付范围、技术验证与采用状态。 -->
<!-- [Pos] 分享业务项目执行记录；产品规则及正式设计分别由对应文档所有。 -->
# Chat分享呈现统一

日期：2026-11-13。

用户要求图片预览沿用Chat页面布局和样式。发现阶段核对ChatMessageList、UserMessagePart、AssistMessagePart、公开阅读与ThreadImageCard；原分享具有独立气泡、字体和Markdown。范围收敛为消息呈现与图片捕获，选用共用消息组件及列表几何；方案依据与业务图见[正式设计](../design/sharing/external-links.md)，规则及骨架见[产品需求](../prd/sharing/external-links.md)。

| 需求项 | 交付物 | 结果 |
| --- | --- | --- |
| AI分享消息与Chat一致 | chatMessageLayout、UserMessagePart、AssistMessagePart | 共用用户气泡、AI正文、字体、行距、间距、Markdown与主题；公开阅读仅提供正文复制。 |
| 图片预览与Chat一致 | ThreadImageCard、ChatShareImage.css | 保留品牌框架和原捕获宽度，采用同一消息正文，图片长代码自动换行。 |
| 完整图表捕获 | MermaidBlock、exportThreadImage | 等待字体及当前图表完成；绘制失败沿原源码视图继续捕获。 |
| 公开及平台边界 | ChatMarkdown publicView、原工作区媒体适配器 | 公开引用保持文字；私有图片保留原认证字节读取和资源释放。 |
| 文档交付 | PRD、正式设计、目录合同 | 更新桌面/窄屏骨架、正常/异常时序和状态图。 |

验证由主Agent执行，luna-test-stage保持暂停。技术入口使用合成正文、实际生产组件和本机Chrome；Vite监听本轮临时端口，未写入账户、业务数据库、Run或Hook。现有服务和用户未提交改动保留。本轮Vite与Chrome进程均由验证入口关闭，专用Vite缓存已清理，截图和命令日志保留。

| 命令或检查 | 退出码 | 关键结果 |
| --- | --- | --- |
| `cd frontend && pnpm exec playwright test --config e2e/external-share.config.ts` | 0 | 26 passed：分享API、四组布局、两种图表捕获、匿名阅读、笔记及原生分享。 |
| `cd frontend && pnpm exec playwright test --config e2e/external-share.config.ts chat-share-layout.spec.ts` | 0 | 6 passed：1200/390 px、深浅主题，实际公式节点、长代码换行及PNG滚动条边界，SVG与源码回退捕获；PNG宽2160 px。 |
| `cd frontend && pnpm exec tsc --noEmit --pretty false --incremental false` | 0 | Web类型检查通过。 |
| `cd frontend && pnpm run native:typecheck --incremental false` | 0 | Native类型检查通过。 |
| 针对本轮消息、公开呈现及验证入口执行`pnpm exec eslint` | 0 | 0 errors、0 warnings。 |
| `python3 /tmp/ink-chat-share-layout-docs-20261113.py`及本机Chrome Mermaid解析 | 0 | 10份文档、29条相对引用、5个新增清单项；9/9图示解析通过。 |

首次浏览器入口遇到AJV模块默认导出错误；测试入口显式扫描自身依赖后通过。图表捕获断言改为核对图表预览SVG，排除工具栏图标；源码回退和正常绘制均完成捕获。最终样式专项使用现行公式分隔符并核对实际KaTeX节点。PNG目视检查发现代码区域的滚动条；图片样式沿代码换行设置隐藏溢出，并核对长行完整落在可见区域。

交付状态：本地实现与隔离技术验证完成。本轮覆盖前端消息呈现，服务发布、真实账户和设备验收分别记录。截图与PNG位于`frontend/test-results/external-sharing/`，命令日志使用`/tmp/ink-chat-share-style-*-20261113.log`。文档检查结果仅说明文档有效性。
