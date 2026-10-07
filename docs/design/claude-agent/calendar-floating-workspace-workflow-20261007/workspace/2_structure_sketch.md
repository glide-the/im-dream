<!-- [Input] 用户2026-10-07修正、现行PRD/正式稿及既有PDF第5页图像。 -->
<!-- [Output] 阶段2增量：外壳与滚动结构。 -->
<!-- [Pos] 结构草图过程证据。 -->
<!-- [Sync] 2026-10-07: 已完成流程的小范围增量证据；设计待独立评审，不表示代码或验证完成。 -->
# 阶段2：结构增量

Optimized Prompt：基于阶段1和真实DOM，明确唯一外壳、自然高度及既有scroll owner；1024已堆叠，不能复制桌面等高方案。

```text
1440：固定左月历 │ 右workspace自然height/可用max-height
                ├ tabs（上角、纸底）
                └ active section（下角；长列表才scroll）
短内容底边可高于左月历；hidden section不参与高度。
1024/430/390：原Calendar整体scroll
             左月历 → 原间距 → 同一圆角workspace
                              sticky tabs → 自然section
             画布底部安全留白 → 阴影完整可见
```

workspace overflow visible，不增加wrapper scroll/裁切。内tabs/section仅绘制同一外壳的角，不加独立卡片；桌面36/56px、1024为20/36px、430/390为16/28px侧/底安全区取自原/本次CSS留白（实际按computed rem）。RESULT/独立Modal原子滚动保持。结构直接同步PRD正文，不以过程草图替代。
