<!-- [Input] 用户2026-10-07修正、现行Calendar PRD/正式稿、影响记录与当前CSS/DOM/harness。 -->
<!-- [Output] 唯一浮空外壳、自然高度及in-flow菜单的独立设计门禁和实施差距。 -->
<!-- [Pos] 实施前独立评审；不是实现或测试回执，20261006证据保留。 -->
<!-- [Sync] 2026-10-07: 设计可实施，实际高度/菜单/阴影安全区及完整回归仍待验证。 -->
# Calendar右侧浮空workspace：独立设计评审

## 结论与范围

**可实施。** [现行PRD](../prd/calendar/calendar-right-panel-tabs-prd.md)骨架及[正式稿§4](../design/claude-agent/calendar-right-panel-tabs-ui-design.md)已准确表达用户修正：右侧仅一层圆角浮空纸片，内部延续简约留白；短内容自然结束，左右不强制等高。未发现需先修改产品范围或正式规格的设计阻塞。本结论开放限定CSS实施门禁，**不表示实现、实际高度、菜单可达性或测试已通过**；实际回执追加到[本轮执行记录](./calendar-floating-workspace-20261007.md)。

评审独立于本次设计作者，仅新增此文件和目录登记；未修改生产/测试代码、未执行测试、未启动服务。旧[20261006评审](./calendar-borderless-ui-design-review-20261006.md)、执行记录及全文历史保持。

## 设计裁决

| 项目 | 裁决与边界 |
| --- | --- |
| 唯一外壳 | workspace拥有opaque paper、24/20/18px既有paper圆角及对应soft/medium shadow；border0、gap0。tabs仅顶角、active section仅底角绘制同一纸片，内部不恢复独立卡片或装饰线；功能控件/menu/tooltip识别保留。 |
| 桌面自然高度 | 原确定高度Calendar的grid row明确为minmax(0,1fr)，workspace auto/max-height100%、内部两层min-height0/flex-shrink传递上限，属于可实施CSS方案。短/空不填满，长active section滚动，tabs外置；hidden/inert面板不参与高度，RESULT原内层滚动不改。浏览器实际收缩链仍须验证。 |
| 窄屏与阴影 | 原64rem堆叠、Calendar整体滚动和tabs sticky保留；workspace取消max-height、section overflow visible。外画布底部2.25/1.75rem保护外壳底角和阴影，移除内部尾部垫片；无需新scroll owner或测量JS。 |
| 最后行menu | 同一more-wrap仅打开menu时display:contents，原menu static、grid-column2/-1参与task下方高度，是可实施的最小CSS方案。DOM/ref/contains及moreOpen、原首项聚焦/键盘/操作owner保持，无新Portal或菜单副本；menu打开可使短纸片增高，到上限后由原section滚动。 |
| 业务和历史 | 不改左月历尺寸、原Modal/焦点、API/状态/文案、Notion快照/权限；正式稿三幅原业务图不受CSS增量影响，完整pre-floating正文另存。无需Admin/schema依赖。 |

## 实施差距与必需验收

1. 当前CSS仍为workspace/section height100%、workspace无角/阴影，menu absolute，窄屏Calendar底padding0。这些与新规格的差距必须按原定义和断点落实，避免局部覆盖留下旧高度、裁切或外壳接缝。
2. 现有`readFloatingPaperSafety`以section内部边界测量，`expectFloatingPaperSafety`仍`void expected`。必须从Calendar与workspace真实外边界测侧/底安全区，实际比较expected：桌面36/56、中幅20/36、小幅16/28px（16px root；按实际rem换算），并保留滚到底的圆角/阴影截图。不能用正文padding冒充外部留白。
3. 三栏目在1440/1024/430/390及浅/深/系统主题覆盖短/空/loading/error/partial、短→长→短、切栏/换日/刷新及LIST↔RESULT，记录真实wrapper高度、上限和原scroll owner；hidden长内容不撑高。computed `height:auto`或单张截图不能证明自然高度。
4. 短一行任务与长列表最后行menu需实际打开、键盘导航、最后项点击及编辑/历史焦点返回；同时确认more命中区、Tab顺序、refs、原Escape/切栏关闭。仅menu矩形可见不足以证明可操作。
5. 保留实际alpha/opaque对比、focus/tooltip/菜单不裁切，以及原三份完整E2E旅程；本轮必要静态/文档检查和自建资源清理由Luna执行并记录实际回执。旧48/48不作为此次新CSS通过依据，技术验证不称为真实业务验收。
