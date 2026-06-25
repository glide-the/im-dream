# Reflection Blog Page — 固定布局播放器交互优化 PRD

> 文档类型：产品功能规格  
> 组件路径：`frontend/src/components/AnalysisView.tsx` → `ReflectionBlogPage`  
> 最后更新：2026-06-26（v5.1 — preserve layout, polish interaction）
> 颜色规范：`docs/prd/color_system/reflection-blog.md`

---

## 1. 产品定位

Reflection Blog Page 是 Past Reflections 的沉浸式阅读视图，用于展示单条历史分析中的 Echoes / Traits / Patterns。页面必须保留既有固定高度阅读结构：左侧日期封面、右侧分区标题列表、下方详情区，以及选中条目后出现的底部播放器控件。

本次目标不是重做信息架构，而是在原有布局上增强“数字杂志 + 可播放阅读队列”的质感，让用户既能像读杂志一样浏览，也能像使用播放器一样在洞察之间前后切换。

---

## 2. 必须保留的整体布局

```text
ReflectionBlogPage（height: 100%; flex column; overflow hidden）
├── Sticky Nav
│   └── ← Past Reflections
├── Main Content（flex: 1; overflow hidden）
│   ├── Split Area（flex: 1; 左右/移动端上下）
│   │   ├── Left Hero：日期封面、完整日期、days / entries / words
│   │   └── Right Panel
│   │       ├── Section Tabs：echoes / traits / patterns
│   │       └── Title List：当前分区 title-only 列表，可独立滚动
│   └── Detail Area（仅选中条目时显示，固定高度）
│       ├── Detail Header：分区、当前位置、关闭按钮
│       ├── Left Detail：标题、描述/evidence、confidence
│       └── Right Related Notes：未来相关笔记占位
└── Bottom Player Bar（仅选中条目时显示）
    ├── 当前条目信息
    ├── 上一条 / 圆点队列 / 下一条
    └── X / N 计数
```

---

## 3. 交互要求

| 场景 | 行为 |
|---|---|
| 点击 Past Reflections 卡片 | 进入 ReflectionBlogPage |
| analyzeEchoes / analyzeTraits / analyzePatterns 完成 | 将单分区结果包装成 ReflectionBlogPage report，直接进入同一阅读页，不再打开旧 PaperStack 弹窗 |
| 一键 Generate New Analysis 完成 | 将三分区结果包装成 ReflectionBlogPage report，直接进入同一阅读页 |
| 点击 Dashboard 的 View Reflections | 使用当前内存中的 echoes / traits / patterns 包装成 ReflectionBlogPage report |
| 点击 Section Tab | 切换当前分区，并清空已选条目，关闭详情区和播放器 |
| 点击标题列表条目 | 展开下方详情区，同时显示底部播放器 |
| 再次点击已选标题 | 收起详情区和播放器 |
| 点击详情关闭按钮 | 收起详情区和播放器 |
| 点击播放器上一条/下一条 | 在当前分区内切换条目，边界按钮 disabled |
| 点击播放器圆点 | 跳转到当前分区对应条目 |

---

## 4. 视觉优化方向

- **保留结构**：不得把固定左右分栏改成整页滚动杂志，不得删除底部播放器。
- **日期封面**：左侧 cover art 使用更强的深色封面、纸张内描边、Issue 日期感和细腻阴影。
- **列表反馈**：选中标题使用渐变底色、序号强化和箭头旋转，让“正在播放的条目”更明确。
- **详情区**：保留双栏详情 + Related Notes，占位态允许存在，但视觉要更轻，不抢主内容。
- **播放器**：底部播放器是核心交互控件，需保持固定在底部，增强玻璃感、阴影和当前 track 识别。
- **动效边界**：只使用轻微 hover、选中态、圆点宽度变化等低成本反馈，不引入复杂动画。

---

## 5. 非目标

- 不实现 Related Notes 后端匹配。
- 不改造为全屏单列杂志长页。
- 不删除底部 Player Bar。
- 不新增弹窗或遮罩层；分析完成后的自动呈现也必须使用 ReflectionBlogPage wrapper。
- 不引入额外 UI 依赖或外部 CDN。
