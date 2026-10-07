<!-- [Input] Stage 1/2/3, user reference images, current theme tokens and implementable independent review. -->
<!-- [Output] Stage 4 visual specifications, component mapping and authorized minimum implementation plan. -->
<!-- [Pos] UI Art Director process evidence; current PRD and formal design own business rules and diagrams. -->
<!-- [Sync] 2026-10-07: visual specification preceded source; focused and final type checks passed; prior harness and parallel type failures are preserved. -->

# Stage 4：活动视图视觉规格与实现

## Optimized Prompt:

你是 Ink & Memory 的界面设计与前端实现负责人。阅读本轮输入提示词、两个参考图、Stage 1/2/3、现行活动 PRD、正式交互设计和已明确“可实施”的独立评审，先完成现有主题内的高保真视觉规格，再实现已授权的最小活动侧栏。使用当前 React、CSS、SVG 图标、国际化和 useMobile，不新增 Tailwind、字体或图标依赖，不编写静态原型。新建旁始终显示铃铛，threadSidebarOpen 管理唯一右侧面板，更多历史复用同一入口；与文件、子智能体、任务会话及定时任务详情双向互斥。20rem 桌面侧栏、原小于 768px／设备判定、390px 全宽抽屉、固定标题、单 body 垂直滚动、四勾选显示菜单及明确焦点语义与现行合同一致。近期 Chat 通过真实更新时间降序公开分页直到旧记录或空响应，原始条数推进 offset；五分钟含边界、排除未来及无效时间，今日任务按 task_id 合并，运行任务优先、Dream generating/running 第二层，Chat 不推断运行。独立来源错误、最近成功数据、扫描途中失败、序号、日期及活动会话保护与重试必须落实；关闭、隐藏和卸载停止本功能计时及分页，原 Dream 页面读取不变。保留原搜索、导航及用户主动删除，普通 Dream 点击复用 openDreamRun，修饰键保持 href，孤立触发不伪造定义快照。新增必要纯合同和本机 Chrome 生产组件用例但由指定验证执行者运行，不启动用户服务、不使用数据库或模型、不宣称验证成功。仅小范围补丁并同步文件头、目录清单、双语 README、现行实现映射及实施回执，保留用户和其他 Agent 改动。

## 执行依据

独立评审 [priority-activity-design-review-20261007.md](../../../../exec/priority-activity-design-review-20261007.md) 结论为可实施，正常时序网络所有权 D1 已闭合。实施严格沿用现行产品范围；技能示例字体、Tailwind 和 Font Awesome 由用户要求的现有技术栈替代。

## 视觉方向

| 项目 | 规格 |
| --- | --- |
| 表面与文字 | 复用 `--color-bg-app`、`--color-bg-paper`、`--color-bg-surface-solid`、`--color-text-primary/secondary/muted`，继承现有字体。 |
| 分界与焦点 | `--color-border-paper` 分隔右侧；focus-visible 使用 `--color-action-link`，错误使用 `--color-state-error`。 |
| 桌面 | 20rem 普通右侧栏，顶部固定，内容 `min-height:0`；主 Chat 保留原宽度适配和原消息滚动。 |
| 窄屏 | 使用原 `useMobile`，390px 时固定全宽覆盖抽屉，外壳适配 `100dvh` 与安全区；背景隔离、内部焦点循环。 |
| 入口 | 新建之后为2rem轮廓铃铛，选中使用现有表面，明确名称和展开状态；没有红点或数量。 |
| 行 | 标题单行省略，完整标题可访问；下行显示来源、明确状态及本地时间，长内容不得撑宽。 |
| 菜单 | 四项可连续勾选；独立浮层在 body 之外，按视口约束定位；菜单方向键与 Escape 返回省略号。 |
| 动效 | 仅现有短时背景反馈；不以逐行进入动画干扰刷新，遵守减少动态效果偏好。 |

## 组件结构与实现计划

`ChatViewContent` 保留入口、原历史分页、搜索、删除和导航所有权；`useActivitySidebarData` 在 Chat 目录协调三个公开读取并管理本功能可见性与时钟；`activitySidebarModel` 只做时间、合并、去重及展示排序；`ActivitySidebar` 负责普通侧栏／抽屉、四项菜单、行与来源反馈。原 `useStoryWorkspaceDreamRuns` 保留 landing 读取；活动独立调用同一 `storyWorkspaceFetchDreamRuns`，不改原 hook 生命周期或原 Run 顺序。

1. 写入本视觉规格后添加纯展示模型和局部读取 hook。
2. 替换原历史栏外壳，接入铃铛及互斥，修正历史错误边界与原始分页 offset。
3. 添加有意义的纯合同和生产组件 Chrome 用例，同步现行映射与回执。
4. 交给专用验证执行者运行确切命令，验证之前不声明完成验收。

## 核心语义示例

```html
<aside aria-labelledby="chat-activity-title">
  <header><h2 id="chat-activity-title">活动</h2><!-- 搜索、刷新、关闭 --></header>
  <div class="activity-sidebar__body"><!-- 优先级和日期历史，共用唯一滚动区 --></div>
  <!-- 显示菜单为独立浮层，不置于滚动 body 内 -->
</aside>
```

窄屏外壳增加 `role="dialog"` 与 `aria-modal="true"`；桌面不增加 modal。搜索打开时活动侧栏的焦点循环暂停，搜索自身接管；搜索关闭回原搜索按钮。菜单先处理 Escape，显式关闭活动回铃铛，导航关闭由目标接管焦点。刷新不重置滚动、不抢焦点；当前聚焦活动行移出时移动到同列表下一可用行或标题。

## 当前交付状态

视觉规格先于源代码写入。12项focused及最终全仓类型技术检查通过；源代码、历史失败恢复及确切验证命令见 [实施回执](../../../../exec/priority-activity-implementation-20261007.md)。本文件不作为功能或真实业务验收证据。

## 实际模块映射收口的 Optimized Prompt:

保持已冻结源码和业务规则，只核对正式稿与输入执行依据的当前模块映射。Dream 活动由 useActivitySidebarData 独立调用 storyWorkspaceFetchDreamRuns，原 useStoryWorkspaceDreamRuns 只保留 landing 职责；菜单勾选和展示派生经过 ChatViewContent，纯模型不直接向组件发消息或发网络请求。正常时序以真实调用与props传递表达，三来源取消段记录可选AbortSignal与序号／会话／日期保护，输入提示词使用 getScheduledDay(localDate, displayTimeZone) 并保留用户独立主动删除边界。只解析本次改动的正常Mermaid图，追加实际退出码和结果；不重跑其余图、业务页面或功能验证。

`node --input-type=module` 只提取当前正式稿首幅 Mermaid 并执行 `mermaid.parse`：退出0，`normal_sequence=PASS type=sequence dream_read=storyWorkspaceFetchDreamRuns display_owner=ChatViewContent model_direct_view_calls=0`。当前其他三图未重复解析或运行，文档映射检查不作为功能验收。

## 验证失败恢复的 Optimized Prompt:

依据首轮6项纯模型通过、5项浏览器在挂载阶段失败、类型通过及7条hooks依赖警告的实际结果，先记录fixture挂载前的console/pageerror/requestfailed及安全fixture正文，保留原失败。严格区分公开 `/api/` 与 Vite 的源码 `/app/_dream/api/`，让源码模块继续加载，避免把harness失败判为业务缺陷。按真实依赖消除标题首次聚焦、稳定removeChat回调、历史分页多余依赖、日期作为原分组输入及cleanup映射引用的7条警告；cleanup捕获映射对象，仍取消刷新后写入该映射的当前controller。先由专用runner执行一个bell用例诊断，再根据真实结果恢复focused回归；不改发送路径、产品规则或扩展环境初始化。

## 历史分页夹具分离的 Optimized Prompt:

依据修后生产组件可挂载、focused 10项通过但组合失败用例的offset19注入未触发的实际证据，只拆分技术测试流程。来源错误反馈位于列表下部，真实点击会滚动body并触发原自动历史分页，所以来源失败／重试与历史删除／延迟旧响应／raw offset不能共享“仅消费20条”的假设。新增独立历史场景，通过正常显示菜单关闭Chat优先项、在已有Thread中打开活动并将唯一body滚到顶部，明确首批20条及公开offset0请求后删除首行，再注入offset19失败和重试，保留原lookahead及迟到删除保护。不开force click，不屏蔽真实滚动和生产自动分页，不改生产源码；交专用runner重跑完整focused并记录实际结果。

## 最终技术证据收口的 Optimized Prompt:

保持已通过12项focused和10项相关合同的生产源码与业务断言冻结，只在browser harness关闭前附加安全console／pageerror／requestfailed及fixture API路径JSON，不能把未断言console推导为零。专用runner重跑6个browser收集附件，结果按22个unique检查报告，不累计重复运行。保存明确命名的只读文档检查脚本，纳入当前PRD、正式稿、四阶段过程、实施与评审回执、本次Chat Sidebar／Dashboard迁移指引、完整pre-priority历史原文及对应inventory；不扫描并行无关文档。正式稿四图以本机Chrome DOM加载已安装Mermaid逐图parse/render，避免Node无DOM的DOMPurify前置问题；仅创建和finally关闭自有文档browser，不访问业务页面或API。最后记录真实退出码、并行Notion类型复核限制、模拟接口截图范围和develop未提交未发布状态；文档与provider-free技术证据不作为真实业务或模型验收。
