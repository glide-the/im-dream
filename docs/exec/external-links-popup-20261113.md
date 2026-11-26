<!-- [Input] 用户提供的拷贝链接/查看/设置菜单与共享设置截图。 -->
<!-- [Output] 外部链接操作浮层、共享设置和技术验证的交付记录。 -->
<!-- [Pos] 分享业务执行记录；产品规则与技术设计由对应现行文档所有。 -->
# 外部链接操作浮层与共享设置

日期：2026-11-13。

需求范围：有效记录的更多菜单依次展示“拷贝链接”“查看”、分隔线和“设置”；设置进入“共享设置”，展示通用访问权限、持有链接的访问范围和“可以查看”。失效操作沿原单条链接规则执行。本轮沿既有只读分享和单向失效规则，公开快照字段保持。

发现阶段读取用户截图、Web/Native设置、共享Hook、API和原Modal；比较行内按钮展开与浮层加共享设置后，采用截图层级。当前访问范围为持有链接的任何人，阅读权限为只读；访问范围下拉提供使链接失效。产品规则、桌面/窄屏骨架见[产品需求](../prd/sharing/external-links.md)，模块、正常/异常与状态图见[正式设计](../design/sharing/external-links.md)。

| 工作项 | 交付物 | 结果 |
| --- | --- | --- |
| 行更多菜单 | ExternalShareMenu | 图标与三项操作、视口内定位、方向键/Esc、外部点击、滚动和尺寸变化收起。 |
| 共享设置 | ExternalShareSettingsDialog及原Modal | 完整标题、访问范围、只读权限、访问说明、原内容与完整链接信息。 |
| 单条失效与恢复 | 原useExternalLinks回调 | 稳定request_key、CSRF、当前归属、确认后更新、失败重试和unknown状态核对保留。 |
| 原生设置 | ExternalLinksSettings.native | 一个原生Modal切换操作与共享设置，系统复制/打开沿原平台所有者。 |
| 语言与主题 | i18n及语义主题token | 中英文、明暗主题、桌面和窄屏沿同一业务合同。 |
| 文档交付 | PRD、设计稿及目录合同 | 同步菜单、共享设置骨架、恢复流程和界面状态。 |

技术验证由主Agent执行，luna-test-stage继续暂停。使用实际设置组件、AuthProvider、useExternalLinks和externalShareApi；合成HTTP在测试进程中保存状态。变化范围为页面及弹窗；API、归属和CSRF合同保持。Project、Episode、canonical Artifact、Run-private `.dream`、Run、after-turn Hook、PostgreSQL与模型均处于范围外。原生浏览器回执使用显式RNW/系统操作替代，物理设备和系统浏览器验收另行记录。

| 验证命令 | 退出码 | 关键结果 |
| --- | --- | --- |
| `cd frontend && pnpm exec playwright test --config e2e/external-share.config.ts` | 0 | 39 passed，包含13项新菜单/设置规格和26项既有分享回归。 |
| `cd frontend && pnpm exec tsc --noEmit --pretty false --incremental false` | 0 | Web类型检查通过。 |
| `cd frontend && pnpm run native:typecheck --incremental false` | 0 | Native类型检查通过。 |
| 针对本轮设置、菜单、弹窗、语言及测试入口执行`pnpm exec eslint` | 0 | 0 errors、0 warnings。 |
| `python3 /tmp/ink-external-popup-docs-20261113.py`及本机Chrome Mermaid解析 | 0 | 11份文档、29条相对引用、5项新增清单，12/12图示解析通过。 |

专项覆盖菜单三项顺序、布局保持、键盘与外部点击关闭、靠近视口底部定位；1200/390 px与深浅主题、弹窗焦点和完整地址；中英文、当前状态复查、复制失败和系统打开；403明确失败后的同key重试、500未知结果的active/revoked核对；账户替换、原内容删除和原生复制/打开及失效。注入的403/500按精确接口登记，预期之外的console/page/request失败为0。桌面与窄屏截图完成目视检查。原生操作结束时的冗余菜单关闭移除后，单独复跑原生规格：1 passed，exit 0。

交付状态：本地实现与技术验证完成。截图保存在`output/playwright/external-links-popup-20261113/`，命令日志为`/tmp/ink-external-popup-*-20261113.log`。本轮前端交付沿原API和数据库能力；服务发布、真实账户与物理设备验收单独登记。既有用户和其他Agent的未提交改动保留。

本轮Vite和Chrome均由验证入口关闭；专用popup缓存与本轮重新生成的Chat分享缓存已清理，截图和命令日志保留。常规服务由原所有者管理，本轮未启动或停止5173/8765服务。
