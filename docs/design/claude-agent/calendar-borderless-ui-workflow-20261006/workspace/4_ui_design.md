<!-- [Input] 顺序阶段1/2/3、PDF 第5页规则图及现有 CalendarPopup React/CSS/Tokens。 -->
<!-- [Output] 右侧浅纸无边框规格与可实施 CSS 片段，正式正文已同步；代码与验证待执行。 -->
<!-- [Pos] 阶段4过程证据，不替代 PRD 骨架、正式交互图或实际回执。 -->
<!-- [Sync] 2026-10-06: 复用现有类与 Token，保留原三幅业务图、断点、滚动及功能浮层。 -->
# 阶段4：Calendar 右侧视觉规格

读取[阶段1](./1_prd_draft.md)、[阶段2](./2_structure_sketch.md)、[阶段3](./3_hierarchy_layout.md)和[PDF 规则图](../inputs/target_image.png)。用户和仓库明确复用优先，本阶段用现有 React/CSS 片段替代技能模板的 HTML/Tailwind；不引入 Font Awesome、Google Fonts、CDN、框架、原型应用或新组件。

## 风格与结构

| 项目 | 可实施规格 |
| --- | --- |
| 轻纸面 | workspace 透明；tabs/current section 连续 opaque paper，gap=0，border/radius/shadow=0。 |
| 留白 | tabs/heading/body 水平对齐：>40rem 1.5rem，<=40rem 1rem；tabs 上/下 .75/.5rem，heading/body 上 1rem；组间 1.5rem、行距 .75rem。 |
| 字体与层级 | 原字体、标题 1.1rem、任务标题 .94rem、副文字 .77rem、Notion 组 .94rem及原状态 .78rem；不新增字号体系。 |
| 交互反馈 | 未选透明；selected active 浅底圆角，未选 hover 轻 hover 底；无位移/浮动动画。焦点 outline、输入/按钮功能边界保留。 |
| 结构 | 原 tabs → 当前 heading/body → 条件状态/恢复 → 原列表或 RESULT；唯一 tabpanel 与全部 owner 不变。 |
| 响应式 | 1440 原左右/section 滚动；<=64rem（含1024）原堆叠/Calendar 外层滚动+tabs sticky；390/430 原40rem规则。 |

## 核心 CSS 片段（尚未写入生产文件）

片段应用到现有 `CalendarPopup.css` 右侧作用域，或等价地修改原定义；不得误改左月历/独立 Modal。须覆盖原两个 media 对 section 重新赋予的圆角与阴影。以下不是完整应用样式，功能控件与布局尺寸沿用原文件。

```css
.calendar-popup__workspace { gap: 0; }
.calendar-popup__workspace .calendar-popup__tabs,
.calendar-popup__workspace .calendar-popup__section {
  border: 0;
  border-radius: 0;
  background: var(--color-bg-paper);
  box-shadow: none;
}
.calendar-popup__workspace .calendar-popup__tabs {
  padding: .75rem 1.5rem .5rem;
}
.calendar-popup__workspace .calendar-popup__tabs [role='tab'] {
  border: 0;
  background: transparent;
  box-shadow: none;
}
.calendar-popup__workspace .calendar-popup__tabs [role='tab'][aria-selected='true'] {
  background: var(--color-bg-active);
  color: var(--color-text-primary);
}
.calendar-popup__workspace .calendar-popup__tabs [role='tab']:not([aria-selected='true']):hover {
  background: var(--color-bg-hover);
}
.calendar-popup__workspace .calendar-popup__section-heading {
  flex-wrap: wrap;
  padding: 1rem 1.5rem;
  border-bottom: 0;
}
.calendar-popup__workspace .calendar-popup__card-body {
  padding-top: 1rem;
}
.calendar-popup__workspace .calendar-popup__task-list,
.calendar-popup__workspace .calendar-popup__diary-list {
  gap: .75rem;
}
.calendar-popup__workspace .calendar-popup__task,
.calendar-popup__workspace .calendar-popup__diary,
.calendar-popup__workspace .calendar-popup__undo-row {
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}
.calendar-popup__workspace .calendar-popup__task:hover,
.calendar-popup__workspace .calendar-popup__task:focus-within,
.calendar-popup__workspace .calendar-popup__diary:hover {
  background: var(--color-bg-hover);
}
.calendar-popup__workspace .calendar-popup__diary--current,
.calendar-popup__workspace .calendar-popup__diary--current:hover {
  background: var(--color-bg-active);
}
.calendar-popup__workspace .calendar-popup__notion-group { margin-top: 1.5rem; }
.calendar-popup__workspace .calendar-popup__notion-group h4 { margin: 0 0 .75rem; }
.calendar-popup__workspace .calendar-popup__notion-group ul { margin: 0; gap: .75rem; }
.calendar-popup__workspace .calendar-popup__task-result > header { border-bottom: 0; }
.calendar-popup__workspace .calendar-popup__task-result > footer { border-top: 0; }

@media (max-width: 40rem) {
  .calendar-popup__workspace .calendar-popup__tabs { padding-left: 1rem; padding-right: 1rem; }
  .calendar-popup__workspace .calendar-popup__section-heading { padding-left: 1rem; padding-right: 1rem; }
}
```

保留 tabs 现有 inset focus 和 tooltip，原 input/button 的焦点与错误/禁用状态不被上述规则清零。原 `__notion-group` 本身无卡片边框；正文时间、外链、无效 URL 与恢复提示沿用。所有 alpha 色均在 opaque paper 上合成后验证；设计阶段不报告对比度通过。

## 正式正文交付与门禁

[现行 PRD](../../../../prd/calendar/calendar-right-panel-tabs-prd.md)直接包含骨架和原断点/滚动规则；[正式设计稿 §4.1–4.4](../../calendar-right-panel-tabs-ui-design.md)直接包含 selector/Token、状态、响应式及390/430/1024/1440与主题验收。正式稿原正常/异常/状态三个 Mermaid 不变，完整修改前文本已另存[历史](../../calendar-right-panel-tabs-ui-design-pre-borderless-20261006-history.md)。

原三个 E2E 完整旅程保留，视觉断言只对右侧要求无 border/shadow，左月历与原 Modal 保持。独立评审、CSS 实现、浏览器/静态/文档验证均待执行；本阶段未写生产代码、未执行测试、未启动资源。[执行记录](../../../../exec/calendar-borderless-ui-20261006.md)保存门禁及历史 SHA。
