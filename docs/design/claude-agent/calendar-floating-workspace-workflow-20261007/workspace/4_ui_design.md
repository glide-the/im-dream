<!-- [Input] 用户2026-10-07修正、现行PRD/正式稿及既有PDF第5页图像。 -->
<!-- [Output] 阶段4增量：CSS/Token建议与真实验收。 -->
<!-- [Pos] 视觉规格过程证据。 -->
<!-- [Sync] 2026-10-07: 已完成流程的小范围增量证据；设计待独立评审，不表示代码或验证完成。 -->
# 阶段4：视觉增量

Optimized Prompt：把前三阶段落实为现有CSS规格，外壳24/20/18px及原shadow Tokens，内部无卡片，双层flex传递auto/max-height；明确最后行menu与阴影安全区，正式稿正文直接写规格。

| 区域 | 增量参数 |
| --- | --- |
| workspace | height auto/max-height100%/align-self start，opaque paper、24px、原双层soft/medium shadow；overflow visible |
| 内部scroll/section | flex:0 1 auto/min-height0，section height auto/overflow auto；hidden不参与 |
| tabs/section接缝 | 顶/底两角使用同一外壳radius，gap0，无独立border/shadow |
| <=64rem | radius20px/原中幅shadow，max-height none、整体scroll、sticky纸底，外画布bottom2.25rem |
| <=40rem | radius18px/原窄幅shadow，外画布bottom1.75rem |
| menu（待裁决） | wrap display:contents；原menu static/grid-column2/-1/right aligned，原功能边界保留 |

```css
.calendar-popup__workspace { height: auto; max-height: 100%; align-self: start; overflow: visible; }
.calendar-popup__workspace-scroll { display: flex; flex-direction: column; flex: 0 1 auto; min-height: 0; }
.calendar-popup__workspace-scroll > .calendar-popup__section { flex: 0 1 auto; min-height: 0; height: auto; overflow: auto; }
.calendar-popup__more-wrap:has(.calendar-popup__more-menu) { display: contents; }
.calendar-popup__more-menu { position: static; grid-column: 2 / -1; justify-self: end; width: max-content; max-width: 100%; }
```

[正式稿§4](../../calendar-right-panel-tabs-ui-design.md)直接给出完整paper/shadow/corner/media片段及验收，不新增Tailwind/FA/字体/CDN。实际验收须测workspace外边界、短空自然height/动态收回/长上限、所有主题/宽度、最后行menu实际操作、focus/tooltip与原完整3spec。expected安全区不能void；2026-10-06已通过结果不代表本次通过。设计待独立评审。
