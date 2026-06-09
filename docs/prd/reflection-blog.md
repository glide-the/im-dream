# Reflection Blog Page — 功能 PRD

> 文档类型：产品功能规格  
> 组件路径：`frontend/src/components/AnalysisView.tsx` → `ReflectionBlogPage`  
> 最后更新：2026-06-09（v3 — 左右分栏布局修订）  
> 颜色规范：`docs/prd/color_system/reflection-blog.md`

---

## 1. 功能概述

**Reflection Blog Page** 是 Ink & Memory 的沉浸式阅读视图，用于展示单条 Past Reflection 的完整内容。  
用户从 Dashboard 的 Past Reflections 卡片进入，读取该日期分析得出的 Echoes / Traits / Patterns 三类洞察。

---

## 2. 用户流程

```
Dashboard (Past Reflections 卡片)
  │
  └─ 点击卡片 ──────────→ Reflection Blog Page（左右分栏）
                              │
                        [右栏 Tab] 点击切换 Section
                              │
                        [右栏列表] 浏览当前 Section 的 title-only 条目
                              │
                        点击某条目 ────────→ [详情区在下方展开]
                                                  左：完整描述 + 置信度
                                                  右：Related Notes 占位
                                                  底部：Player Bar
                                                  │
                                            再次点击 / × → 收起详情
```

---

## 3. 页面结构

### 3.1 固定顶栏 (Sticky Nav)

| 区域 | 内容 |
|---|---|
| 左侧 | `← Past Reflections` 返回按钮（pill 样式） |
| 右侧 | **空** — Section Tab 已移至右栏顶部 |

---

### 3.2 主体：固定高度左右分栏 + 底部浮动 Player Bar

整体使用 **flex column + overflow hidden** 布局，所有区域在视口内分配空间，无外部页面滚动。

```
整体容器 (height:100%; flex column; overflow hidden)
│
├── Sticky Nav (flex-shrink: 0)
│
├── 主内容区 (flex: 1; overflow: hidden; flex column; min-height: 0)
│   │
│   ├── 左右分栏 (flex: 1; overflow: hidden; min-height: 0)
│   │   ├── 左栏 260px (overflow-y: auto)       右栏 flex:1 (overflow: hidden; flex column)
│   │   │   封面艺术块                            ├── Section Tabs (flex-shrink: 0)
│   │   │   REFLECTION 标签                      └── 标题列表 (flex:1; overflow-y:auto; min-height:0)
│   │   │   完整日期
│   │   │   N days / entries / words
│   │   │
│   │   └── [移动端: 上下排列，左栏固定高度]
│   │
│   └── 详情区 (flex-shrink: 0; 固定高度 ~45vh; 仅选中条目时显示)
│       ├── 详情 header (flex-shrink: 0)
│       └── 两列内容 (flex:1; overflow hidden)
│           ├── 左(60%): 描述 + 置信度 (overflow-y: auto)
│           └── 右(40%): Related Notes 占位 (overflow-y: auto)
│
└── Player Bar (flex-shrink: 0; 底部浮动; 仅选中条目时显示)
    [icon] [title / section]  [◀] [●●●●] [▶]  [X/N]
```

**关键布局约束：**
- 分栏区 `flex: 1`：当详情区展开时自动缩小，总高度不超出容器
- 右侧标题列表 `flex: 1; overflow-y: auto; min-height: 0`：独立滚动，不依赖外部页面滚动
- 详情区固定高度（桌面 `45vh`，移动 `52vh`），内容超出时内部各列独立滚动
- Player Bar 始终在视口底部，不随内容滚动

---

### 3.3 左栏 — Hero 信息

| 元素 | 规格 |
|---|---|
| 封面艺术块 | 固定正方形，内含月缩写 + 日期数字（大，Georgia）+ 年份，纸纹背景，阴影 |
| 标签行 | `REFLECTION`（大写，muted，letter-spacing 2.5px） |
| 日期标题 | 全日期字符串，Georgia italic，桌面 ~28px |
| 统计行 | `N days · N entries · N words`，小号辅助色文字 |
| 宽度 | 桌面固定 260px；移动端折叠为全宽横向展示（Hero 在右栏 Tab 上方） |

---

### 3.4 右栏 — Section Tabs + 标题列表

#### Section Tabs（右栏顶部水平排列）

| 状态 | 样式 |
|---|---|
| 激活 | 背景 `var(--color-bg-surface-solid)`，`border-bottom: 2px solid var(--color-text-muted)` |
| 非激活 | 透明背景，`color: var(--color-text-muted)` |
| 布局 | 水平 flex row，底部分隔线，图标 + 名称 + 数量 |

**Tab 行为：**
- 点击 Tab → 切换 `activeSection`，清除 `selectedItemIdx`（收起详情）
- 每个 Tab 显示条目数量徽章

#### 标题列表

- 每条只显示：**序号**（01/02/03）+ **标题**（Georgia italic）+ **→ 箭头**
- 点击某条 → 展开详情区（下方），箭头旋转 90°
- 再次点击同一条 → 收起详情区
- 点击不同条 → 切换详情内容
- 无额外描述、无置信度条（简化展示）

---

### 3.5 详情区 — 标题点击后在分栏下方展开（固定高度）

| 区域 | 内容 |
|---|---|
| 容器高度 | 桌面 `45vh`，移动 `52vh`；固定高度，内容超出时内部滚动 |
| 顶部 header (flex-shrink:0) | Section icon + Section 名 · X/N 计数 + × 关闭按钮 |
| 左栏（60%，overflow-y:auto） | 条目完整标题 + 描述/evidence + 置信度指示器 |
| 右栏（40%，overflow-y:auto） | `RELATED NOTES` + 骨架占位卡 × 3 + "coming soon" 文字 |
| 底部 Player Bar | 见 §3.6，固定在视口底部（在详情区外部） |
| 移动端 | 上下排列（description 上，notes 下） |

---

### 3.6 Player Bar（底部浮动，视口固定）

**位置**：在整个 `ReflectionBlogPage` 容器的 flex 底部（`flex-shrink: 0`），不随内容滚动，始终可见。  
仅当 `selectedItemIdx !== null` 时显示。

```
[封面icon 34×34]  [条目标题 italic]    [◀]  [● ○ ○ ○]  [▶]    [X / N]
                  [Section 名]
```

| 区域 | 内容 |
|---|---|
| 左侧（flex:1） | 34×34 封面图标块 + 条目标题（italic，overflow ellipsis）+ Section 名 |
| 中间（flex-shrink:0） | `◀` + 位置圆点（当前展开为宽椭圆 16px，其余 6px，可点击跳转）+ `▶` |
| 右侧（flex-shrink:0） | `X / N` 计数 |

**Player 交互：**
- `◀ / ▶`：切换上一条 / 下一条，边界时置灰禁用
- 圆点：点击跳转到对应条目
- 更换条目时，左侧标题同步更新

---

## 4. 响应式规格

| 属性 | 桌面 | 移动 |
|---|---|---|
| 分栏方向 | `flex-direction: row`（左右） | `flex-direction: column`（上下） |
| 左栏（移动端）| 折叠为横排 Hero（封面图标左 + 信息右） | 全宽，紧凑 padding |
| 右栏 Section Tabs | 水平排，桌面显示全名 | 可滚动，仅显示图标 + 数量 |
| 详情区 | 两列 row | 单列 column |
| Player Bar | 完整显示 | 标题截断，间距收紧 |

---

## 5. 状态管理

```typescript
const [activeSection, setActiveSection] = useState<SectionKey>(firstAvailableSection);
const [selectedItemIdx, setSelectedItemIdx] = useState<number | null>(null);

// 切换 Tab → setActiveSection + setSelectedItemIdx(null)
// 点击标题 → setSelectedItemIdx(isSelected ? null : i)
// Player ◀/▶ → setSelectedItemIdx(prev ± 1)
// Player 圆点 → setSelectedItemIdx(i)
// × 关闭 → setSelectedItemIdx(null)
```

---

## 6. 非功能性要求

- **无后端改动**：Related Notes 右栏为纯前端占位
- **Token 约束**：所有颜色值通过 `var(--color-*)` 引用
- **动画**：Tab 切换、条目切换 `transition: all 0.2s`；Player 圆点宽度 `transition: all 0.3s`；箭头旋转 `transition: transform 0.25s`
- **自动 scroll**：选中条目后页面 smooth scroll 至详情区

---

## 7. 待实现功能（Future）

- 右栏 Related Notes：关联同期日记条目（需后端关键词匹配 API）
- Player Bar 键盘快捷键（← → 方向键）
- 单条 Reflection 分享卡片生成
