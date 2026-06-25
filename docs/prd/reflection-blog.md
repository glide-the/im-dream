# Reflection Blog Page — 数字杂志阅读页 PRD

> 文档类型：产品功能规格  
> 组件路径：`frontend/src/components/AnalysisView.tsx` → `ReflectionBlogPage`  
> 最后更新：2026-06-26（v5 — luxury digital magazine redesign）
> 颜色规范：`docs/prd/color_system/reflection-blog.md`

---

## 1. 产品定位

Reflection Blog Page 是 Past Reflections 的沉浸式阅读页。它不再像工具面板，而是像一份可收藏的数字杂志专题：用日期封面、编辑引语、栏目切换、核心要点和编辑笔记，把 echoes / traits / patterns 组织成一次有审美节奏的阅读体验。

---

## 2. 核心交互目标

| 目标 | 设计决策 |
|---|---|
| 降低阅读负担 | 默认显示一组激活栏目，卡片只展示标题、描述和最核心 evidence |
| 提升杂志感 | Hero 使用深色封面、Issue 日期、Georgia italic 大标题、法语/英语装饰文字 |
| 快速切换分区 | Section tabs 保留 echoes / traits / patterns，显示数量与图标 |
| 保留读者收获感 | 右侧 Core Takeaways 自动提炼当前栏目标题列表 |
| 补充编辑语气 | Editor's Note 作为边栏注释，给出阅读建议而不是功能提示 |

---

## 3. 页面结构

```text
ReflectionBlogPage
├── Back pill：返回 Past Reflections
└── Magazine Article Shell
    ├── Header / Cover Spread
    │   ├── Left Cover：日期、Issue 标识、Reflections 大标题、副标题
    │   └── Right Lead：Editor's Selection 引用 + Insights / Entries / Words 数据
    ├── Section Tabs：echoes / traits / patterns
    └── Main Grid
        ├── Insight Story List
        │   ├── 序号 + confidence tone
        │   ├── title
        │   ├── description
        │   └── evidence quote
        └── Editorial Sidebar
            ├── Core Takeaways
            └── Editor's Note · Conseil
```

---

## 4. 视觉规范

- **版面气质**：Vogue/Elle 数字专题感，强调留白、细边框、纸张阴影和 serif 斜体标题。
- **日期区域**：深色封面块内使用大号日期数字 + issue date，强化杂志期刊感。
- **标题与副标题**：`Reflections` 使用 Georgia italic，正文和元数据使用系统 sans-serif。
- **引用区块**：Hero lead 使用大号 editorial quote；每张 insight card 内的 evidence 使用左边框 quote block。
- **核心要点**：右侧边栏以编号列表呈现当前 section 的标题摘要。
- **编辑笔记**：深色边栏卡片，使用 `Editor's Note · Conseil` 标题和短句提示。

---

## 5. 响应式要求

| 区域 | 桌面 | 移动 |
|---|---|---|
| Header | 左右双栏封面 | 单栏堆叠 |
| Main Grid | 内容 1fr + Sidebar 300px | 单栏 |
| Section Tabs | 横向 wrap | 横向 wrap |
| Insight Cards | 大卡片列表 | 紧凑卡片 |

---

## 6. 非目标

- 不引入外部 CDN；沿用 React app 内现有字体和 CSS variables。
- 不实现 Related Notes 后端匹配。
- 不保留旧版 Player Bar，因为该交互与杂志阅读心智不一致。
- 不增加弹窗；阅读页所有信息都在页面内直接呈现。
