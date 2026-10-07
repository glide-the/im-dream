<!-- [Sync] 2026-10-05: link the calendar business PRD; skeletons belong to PRD and formal business diagrams to the interaction design. -->
<!-- [Input] Stage 1/2/3、inputs/target_image.png、现行 PRD、项目 Tokens 与 Calendar/Chat 源码。 -->
<!-- [Output] Stage 4 正式 UI 规格的保存位置、视觉决策、组件职责与交付边界。 -->
<!-- [Pos] 日历右侧页签设计流程 Stage 4；现行交互规则由正式交互稿维护。 -->
<!-- [Sync] 2026-10-04: 完成仅文档交互设计，记录独立评审的 URL/日期合同修正，保持项目视觉和完整性阻塞。 -->

# Stage 4：正式交互设计

优化后的执行提示词：根据前三阶段、用户图片与当前源码，完成中文正式交互稿，以“背景与问题、目标与边界、概念与规则”为基础，明确桌面/窄屏单栏目布局、图标页签全部状态、已有任务和日记状态保留、Notion 行结构与分组计数、权限/时间/范围、加载与失败恢复、只读 API、并发及可访问性。采用项目现有 Tokens、字体、SVG 和 Notion 字形，不输出功能或原型代码。关联 Mermaid、R01–R14 矩阵和独立评审；聚合 GET 未返回不显示实时数量，外链无预检/正文读取，严格全部今日文档目标保留阻塞。

交付项：[正式交互稿](../calendar-right-panel-tabs-ui-design.md)、本阶段记录和目录清单；[现行 PRD](../../../prd/calendar/calendar-right-panel-tabs-prd.md)仍负责产品规则。[正式业务图](../calendar-right-panel-tabs-ui-design.md)、[阶段流程证据](./3_hierarchy_logic.md)、[独立评审](../../../exec/calendar-right-panel-tabs-design-review-20261004.md)与[文档验证回执](../../../exec/calendar-right-panel-tabs-doc-validation-20261004.md)分别保存业务结构、独立结论与实际检查结果。

## 1. 背景与问题

附件只提供导航选中项的圆角背景、图标和名称组合。Home、聊天、日历与深色背景是视觉示例。当前 Calendar 两个右侧纸面同时可见；Chat 的页签是内联实现，不能直接声称有完整共享组件。新今日功能缺创建时间、细粒度错误、部分结果与明确 API 日期合同；Search 的非完整枚举限制不能靠视觉稿消除。

## 2. 目标与边界

保留左月历、透明画布、现有任务/日记入口，将右侧改为定时任务/日记/Notion 三个互斥页签与一个当前纸面。仅交付中文文档。用户要求优先于技能参考中的 HTML/Tailwind、Font Awesome、Google Fonts 和新风格默认；不引入其代码/依赖，也不新增全文、活动数据库、Webhook、队列或同步系统。

## 3. 概念与规则

### 3.1 视觉方向与规格

| 维度 | 正式设计决定 |
| --- | --- |
| 总体表面 | 透明 Modal 画布、原月历纸面、单一当前栏目纸面，继承明暗主题 |
| 选中项 | Chat 当前 surface/border/shadow token、胶囊圆角、图标与名称 |
| 未选中项 | 图标为主，text-secondary、hover token，完整可访问名称和 hover/focus tooltip |
| 焦点 | 现有 border-focus 的 2px outline/offset；手动激活，与选中独立 |
| 字体与图标 | App 现有本地 Excalifont/Xiaolai/功能字体，Clock、File、局部 NotionMark 字形最小提取 |
| 布局 | 延续 Calendar 现有左右 grid、64rem/40rem 断点；窄屏月历→导航→单面板 |
| 行密度 | 复用任务行无叠层阴影，标题/时间/标识/外链可换行，不横向溢出 |
| 动效 | 项目原反馈与 reduced-motion，无新增滑动或加载延迟 |

### 3.2 组件职责

P01/P02/P05/P06/P10 复用原 Modal、月历、任务、日记与编辑/历史。P03/P04 提供本地页签及唯一可见 panel。P07/P08/P09 仅处理今日元数据头、两组行和局部状态。状态保留使用现有 owner 或局部已展示面板，隐藏面板不可聚焦/读出、不留 Portal、不发新查询，不新建全局 store。

### 3.3 交互决定

1. 已登录三个栏目默认定时任务；未登录沿用现状隐藏任务项，只提供日记/Notion，默认日记，键盘只遍历可见项；登出时当前任务回日记。不新增登录弹窗，沿用 App 原初始日期。未连接 Notion 保留页签并去 Settings。
2. 同日切栏目保留滚动、安排输入、任务结果与已读状态；编辑/历史 Modal 打开时背景不能切换。换日保留栏目，任务回 LIST，列表回顶部，安排未发送输入保留。关闭重开不持久化。
3. Notion 仅今天，用户 IANA 时区半开区间与上游原始时间；非今天不查询/不显示旧列表，回到今天同步月历。
4. 创建优先归组，双命中两标识一计数，编辑组排除创建组，按组时间降序和身份稳定排序。标题缺失为未命名文档，图标默认资源图标。
5. 今日 GET 是建议未实现，一次聚合扫描无进度流；返回前计数未知，partial 只计已知结果。扫描完成不等于全集。
6. 有效外链直接新标签打开，不预检或读全文；URL 无效禁用并刷新。页级反馈只来自已有接口明确结果或 Notion 目的地，不由 Search 遗漏推断删除。
7. Request generation 与 actor/connector/date/tz 匹配后提交，Abort 不是唯一保护。旧结果只在同上下文非权限失败保留；授权/归属撤销与登出清除。
8. tablist/tab/tabpanel 关联、完整可访问名称、可见焦点、手动键盘激活与 tooltip 焦点支持；切栏焦点留页签。

## 4. 交付结论

正式交互稿已保存，关联三个 Mermaid 图和 R01–R14 实施/验收矩阵。PRD 的聚合分页加载文案、Data Source timestamp filter 结构与外链页级反馈边界同步为一致规则。严格“全部今日创建或编辑文档”仍存在阻塞，Search 可发现范围仅为待接受候选；功能未实施、真实业务未验收。独立评审与文档验证由后续独立角色执行，不由本阶段自评替代。

独立评审修正：当前页面 URL 原样投影，复用范围限于 Settings 新标签/`noopener noreferrer` 打开；今日 DTO 的 HTTPS/服务器允许主机校验待补。正式稿与 PRD 已同步，日期筛选使用 compound AND 表示半开区间，不将组合示意称为固定 CLI 已验证请求。
