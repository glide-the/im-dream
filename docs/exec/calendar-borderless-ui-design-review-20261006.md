<!-- [Input] 用户右侧 workspace 定位、UI v2.pdf 第5页、现行 PRD/正式设计、顺序阶段1–4与当前 DOM/CSS/E2E。 -->
<!-- [Output] 无边框视觉调整的独立设计门禁、代码差距与必要验收边界。 -->
<!-- [Pos] 实施前独立评审证据；不是代码、文档技术检查或真实业务验收回执。 -->
<!-- [Sync] 2026-10-06: 设计可实施，生产 CSS 与视觉断言尚待调整；不扩大业务范围。 -->
# Calendar 右侧无边框 UI：独立设计评审

## 1. 结论

**可实施。** 现行 PRD 与正式稿已将用户定位的 `calendar-popup__workspace` 限定为视觉修改，落实浅纸底、留白和文字层级，未发现阻止此范围实施的设计缺口。此结论开放 CSS 实施门禁，**不表示代码完成、对比度达标或业务旅程已通过**。实际实现和验证须追加到[执行记录](./calendar-borderless-ui-20261006.md)。

评审独立于阶段1–4的设计作者；只读取输入并新增本评审和目录登记，未写生产代码、未执行测试、未启动或清理服务。

## 2. 依据与核对

| 核对项 | 来源与结论 |
| --- | --- |
| 用户范围及 PDF | [UI v2.pdf](../prd/Ink%20%26%20Memory%20UI%20Design%20v2.pdf)第5页 §5.4要求减少面板、增加留白、普通条目无静态卡片。用户明确此区域无边框，因此不追加 PDF 通用页面级虚线；功能焦点和图标描线保持。 |
| 正式正文交付 | [PRD §4.1–4.4](../prd/calendar/calendar-right-panel-tabs-prd.md)直接包含桌面/窄屏骨架、状态和范围；[正式稿 §4.1–4.4](../design/claude-agent/calendar-right-panel-tabs-ui-design.md)直接包含 selector、Token、间距、断点、滚动和验收。阶段1–4仅为过程证据。 |
| 承载与对比 | workspace 透明、gap=0；tabs 与当前 section 同用 opaque paper，相接而不留透明缝隙；未选 tab 透明，selected/hover alpha 色在实际纸底上合成。设计没有将透明色 RGB 当作对比度通过的依据。 |
| 无装饰卡片 | tabs/section 的 border、radius、静态 shadow 为0，所有断点一致；header、普通内容行及任务 RESULT header/footer不保留装饰线。选中页签浅底圆角属于导航状态，保留。 |
| 保留功能识别 | focus-visible outline、输入/按钮/危险态、Notion 图标描线、tooltip/menu定位和独立编辑/历史 Modal保持；日记当前文字标记与轻 active 底保持。禁止宽泛清除全部 border/outline。 |
| DOM及滚动 owner | 当前 DOM为 tabs → workspace-scroll → 唯一可见 section；隐藏section继续 hidden/inert。1440桌面为section滚动；原64rem断点含1024上下堆叠，Calendar外层滚动且tabs sticky；390/430沿用40rem。RESULT/Modal内层滚动不改。 |
| 业务与历史 | 不改左月历、原初始日期、状态 owner、API、文案或 Notion快照/日期/权限规则。正式稿保留原正常、异常、状态三个 Mermaid；[PRD历史](../prd/calendar/calendar-right-panel-tabs-prd-pre-borderless-20261006-history.md)及[正式稿历史](../design/claude-agent/calendar-right-panel-tabs-ui-design-pre-borderless-20261006-history.md)完整另存，哈希复核和图示语法验证留给后续技术检查。 |

## 3. 当前代码差距与实施风险

1. `CalendarPopup.css` 当前 workspace仍有 `.75rem` gap；未选 tab有实底，selected有描边；section有1px边框、24px圆角和双层阴影，header有横线。64rem/40rem规则又为section赋予圆角与阴影。必须限定右侧作用域并消除所有断点的旧覆盖，不能仅修桌面。
2. 日记/撤销行仍继承外框和卡片底，当前日记有成功色整行描边；任务RESULT仍有header/footer线。按正式稿取消这些装饰，同时保留当前文字、精确结果、内部滚动与业务按钮。
3. 旧 `scheduled-task-calendar.spec.ts` 将左月历和右侧section都断言为有边框/阴影。需分别断言左侧现状与右侧无边框，继续执行原完整任务旅程，不能删除相关验证。
4. 旧 `calendar-right-panel-tabs.spec.ts` 仅覆盖1440/390的视觉组合，直接用tab背景计算对比，并拒绝未测量的半透明层。需扩展430/1024和三个栏目，正确合成transparent/alpha背景、hover/selected与focus的实际颜色；保留4.5:1文字及3:1图标/焦点阈值，不能把阈值调低或临时给测试加实底。
5. 长标题/状态可能使heading换行，窄屏sticky和正文边缘可能裁切focus或tooltip。实现应沿用原最小命中区、内容滚动与功能入口，以实际视口/交互证据确认。

以上是已明确的实施差距和验证风险，无需改变产品范围或增加接口/schema。不得用本设计批准覆盖此前Notion业务回执或声称扩大资源全集。

## 4. 必要完成门禁

| 验证 | 必须保留的证据 |
| --- | --- |
| 视觉和可访问性 | tasks/diary/Notion × 390/430/1024/1440 × 浅/深主题；系统主题映射；normal/hover/selected/focus的computed style、实际合成对比、截图、tooltip和视口边界；左月历/独立Modal未被去边框规则误伤。 |
| 长内容和完整旅程 | 原三个E2E specs全部必要旅程：栏目/日期/重开、草稿/滚动/LIST-RESULT保留、任务编辑/失败/冲突/运行/历史/结果/Thread/暂停恢复/删除撤销、日记打开返回/当前/删除，以及Notion快照/校验/刷新/异常/并发。 |
| 静态和文档 | 相关TypeScript/ESLint及必要构建，Markdown清单和新增引用、历史保存、Mermaid语法/渲染和diff检查；记录实际命令、退出码、失败修复/复测及自建资源清理。 |

确定性执行交给指定Luna runner；harness仅使用允许的测试目录/具名脚本和依赖注入，复用已安装Chrome，不改共享构建输出、不停止用户服务。技术验证与正常账户截图分别报告，不把技术结果称为完整真实业务验收。

## 5. 过程依据

- [阶段1 PRD草案](../design/claude-agent/calendar-borderless-ui-workflow-20261006/workspace/1_prd_draft.md)
- [阶段2结构草图](../design/claude-agent/calendar-borderless-ui-workflow-20261006/workspace/2_structure_sketch.md)
- [阶段3层级映射](../design/claude-agent/calendar-borderless-ui-workflow-20261006/workspace/3_hierarchy_layout.md)
- [阶段4 CSS规格](../design/claude-agent/calendar-borderless-ui-workflow-20261006/workspace/4_ui_design.md)
