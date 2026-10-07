<!-- [Input] 用户2026-10-07修正、现行PRD/正式稿及既有PDF第5页图像。 -->
<!-- [Output] 阶段3增量：可见内容/菜单/焦点的owner关系。 -->
<!-- [Pos] 层级映射过程证据。 -->
<!-- [Sync] 2026-10-07: 已完成流程的小范围增量证据；设计待独立评审，不表示代码或验证完成。 -->
# 阶段3：层级增量

Optimized Prompt：仅映射高度、菜单与可见状态owner，保留原业务3幅图和API，不扩任务/Notion状态机。

```text
Calendar Modal（原initialFocus/focus trap）
├ 左月历（原date owner）
└ workspace（唯一浮空外壳，无新state）
  ├ tabs（activeTab/focusedTab/tooltip owner）
  └ workspace-scroll（仅CSS可收缩）
    └ 当前section（原panelRefs、内容与scroll）
      ├ LIST/diary/Notion（透明行/状态/恢复）
      └ task（原moreOpen/ref/键盘/操作）
        └ 原menu打开时作为下方右对齐功能区参与高度
```

hidden/inert section的display none继续排除高度。快照读取/校验及任务loading→内容/错误只触发现有DOM排版；切tabs、换日、LIST/RESULT、短→长→短不新增数据读取。menu原首可用项聚焦与Arrow/Home/End处理已见源码；Escape/Tab/点击关闭以现有owner为准，不创造新语义。display:contents只移除wrap盒子，DOM/ref/contains与more命中区必须实际验证；这项呈现待独立评审。
