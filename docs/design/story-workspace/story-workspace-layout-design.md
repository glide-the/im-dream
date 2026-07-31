# Story Workspace Layout Design — Dreem 创作者 Workspace 骨架与线框设计

> **Design ID**: `design_002_story-workspace-layout`  
> **关联 Issue**: [SUO-199](/SUO/issues/SUO-199)  
> **父 Issue**: [SUO-198](/SUO/issues/SUO-198)  
> **关联 PRD**: [story-workspace-prd.md](./story-workspace-prd.md)  
> **设计阶段**: design → issue → task → stage  
> **最后更新**: 2026-08-01  

---

## 1. 概述

本文档提供 Story Workspace 的详细布局骨架、线框说明、关键交互流程与数据表结构。作为下游实现的可直接消费的设计真相源。

**核心工作流**：Agent 产出剧本/角色/场景 → 页面渲染展示 → 用户审阅确认 → 后续执行

所有业务相关路径、路由、包名、组件/模块标识均使用 `story-workspace` 前缀。

---

## 2. 全局布局骨架

### 2.1 桌面端三栏布局（唯一支持的布局，≥1280px）

> **约束**：本期仅支持桌面端，不包含任何移动端或平板端适配。
>
> **布局来源**：参考 Dreem 创作者协作页截图（PDF 第 3-4 页）的三栏结构——左侧导航边栏 + 中间资产列表 + 右侧详情面板。Dreem 边栏为窄图标栏（~60px），本平台扩展为 240px 文字边栏以提升可读性。
>
> **业务模型**：本布局服务于「Agent 产出 → 用户审阅」工作流。中间区域展示 Agent 生成的内容列表，右侧面板用于审阅确认。

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  AppHeader（全局，高度 56px）                                                  │
│  ┌──────┐  Ink & Memory                                    [用户头像] [设置]  │
│  │ Logo │                                                                   │
│  └──────┘                                                                   │
├──────────┬───────────────────────────────────────────────┬───────────────────┤
│          │                                               │                   │
│ Sidebar  │                                               │ Review Panel      │
│ 240px    │     Main Content Area                         │ 360px             │
│ 固定      │     （填充剩余宽度）                           │ 可折叠            │
│          │                                               │                   │
│ ┌──────┐ │                                               │ ┌───────────────┐ │
│ │ Logo │ │     ┌─────────────────────────────────────┐   │ │ 审阅标题       │ │
│ └──────┘ │     │ Toolbar                             │   │ │ 关闭 [X]      │ │
│          │     │ [搜索____] [筛选▼] [排序▼]          │   │ ├───────────────┤ │
│ 工作台    │     └─────────────────────────────────────┘   │ │               │ │
│  ├ 首页   │                                               │ │  Agent 生成    │ │
│  ├ 故事   │     ┌─────────────────────────────────────┐   │ │  内容审阅      │ │
│  ├ 角色   │     │ Data Table                          │   │ │               │ │
│  ├ 场景   │     │ ┌─────────────────────────────────┐ │   │ │  确认/驳回     │ │
│  │       │     │ │ 表头行                           │ │   │ │  操作按钮      │ │
│ 设置      │     │ ├─────────────────────────────────┤ │   │ │               │ │
│          │     │ │ 数据行 1  ← 选中（右侧细线）      │ │   │ └───────────────┘ │
│          │     │ ├─────────────────────────────────┤ │   │                   │
│          │     │ │ 数据行 2  ◀ 待审阅（左侧黄条）    │ │   │                   │
│          │     │ ├─────────────────────────────────┤ │   │                   │
│          │     │ │ 数据行 3  ◀ 已驳回（左侧红条）    │ │   │                   │
│          │     │ └─────────────────────────────────┘ │   │                   │
│          │     └─────────────────────────────────────┘   │                   │
│          │                                               │                   │
│          │     ┌─────────────────────────────────────┐   │                   │
│          │     │ Pagination                          │   │                   │
│          │     │  ← 1 2 3 ... 10 →                   │   │                   │
│          │     └─────────────────────────────────────┘   │                   │
│          │                                               │                   │
├──────────┴───────────────────────────────────────────────┴───────────────────┤
│                                                                              │
│  页面背景：Warm Canvas #F6EFE5                                                │
│  内容区背景：Paper Cream #FFFAF2（轻纸面分区）                                  │
│  边框：Border Paper #D8C7B3 虚线                                              │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

**审阅状态视觉标记**：
- **待审阅**：行左侧 4px Memory Yellow 竖条 + 轻微背景色变化
- **已确认**：无特殊标记，正常显示
- **已驳回**：行左侧 4px 红色竖条（#E74C3C）+ 背景色变淡
- **Agent 生成中**：行显示骨架屏 + 旋转 Loading 图标

### 2.2 布局约束声明

> **重要**：本期设计仅针对桌面端（≥1280px）。
>
> 以下场景**明确排除**：
> - 移动端（<768px）布局
> - 平板端（768px–1279px）布局
> - 底部导航
> - Sidebar 折叠为图标栏
> - Detail Panel 作为抽屉滑出
> - 触控交互优化
> - 卡片式简化表格视图
>
> 若未来需要扩展响应式支持，应作为独立设计 Issue 处理，不在本期范围内。
---

## 3. 组件级线框说明

### 3.1 Sidebar 导航栏

> **Dreem 截图参考**：Dreem 创作者协作页（PDF 第 3 页）左侧为窄边栏，含 Home、World、Assets、Settings 等图标导航项，当前项有高亮指示。本平台扩展为 240px 宽边栏，保留图标+文字的导航模式。

```
┌──────────────────────┐
│  Sidebar             │
│  宽度：240px（固定）   │
│  背景：Paper Cream    │
│  右边框：虚线 Border   │
├──────────────────────┤
│                      │
│  ┌────────────────┐  │
│  │ Ink & Memory   │  │  ← Logo 区
│  │   创作者工作台  │  │
│  └────────────────┘  │
│                      │
│  ─────────────────── │  ← 分隔线
│                      │
│  ┌────────────────┐  │
│  │ 🏠  工作台首页  │  │  ← 导航项
│  └────────────────┘  │     当前项：Memory Yellow 下划线
│  ┌────────────────┐  │
│  │ 📖  故事管理   │  │
│  └────────────────┘  │
│  ┌────────────────┐  │
│  │ 👤  角色管理   │  │
│  └────────────────┘  │
│  ┌────────────────┐  │
│  │ 🎬  场景管理   │  │
│  └────────────────┘  │
│                      │
│  ─────────────────── │
│                      │
│  ┌────────────────┐  │
│  │ ⚙️  设置       │  │  ← 底部设置入口
│  └────────────────┘  │     （跳转全局 Settings）
│                      │
│  ─────────────────── │
│                      │
│  ┌────────────────┐  │
│  │ [头像] 用户名   │  │  ← 用户信息
│  └────────────────┘  │
│                      │
└──────────────────────┘
```

**导航项规范**：

| 属性 | 值 |
|------|-----|
| 图标 | 20px，Charcoal Brown |
| 文字 | 14px，500 字重 |
| 间距 | 图标与文字 12px，项之间 4px |
| 当前项 | Memory Yellow 下划线（2px，偏移 4px） |
| Hover | 背景色轻微变化（Paper Cream 深色 5%） |
| 选中 | 右侧 3px Action Brown 竖线 |

### 3.2 Toolbar 工具栏

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Toolbar                                                                     │
│ 高度：56px                                                                   │
│ 背景：透明（继承 Paper Cream）                                                │
│ 底边框：1px Border Paper 虚线                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌────────────────┐  ┌────────┐  ┌────────┐                                 │
│  │ 🔍 搜索...      │  │ 筛选 ▼ │  │ 排序 ▼ │                                 │
│  │ 宽度：240px     │  │        │  │        │                                 │
│  │ 圆角：999px     │  │        │  │        │                                 │
│  │ 边框：Border    │  │        │  │        │                                 │
│  └────────────────┘  └────────┘  └────────┘                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

> **注意**：本期无「新建」按钮，内容由 Agent 自动生成。Toolbar 仅保留搜索、筛选、排序功能。

**批量审阅操作栏**（多选时显示，替换常规 Toolbar）：

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Batch Review Toolbar（固定顶部）                                             │
│ 背景：Action Brown（深色带）                                                  │
│ 文字：白色                                                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  已选择 5 项                              [✓ 批量确认] [✕ 批量驳回] [取消]   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Data Table 数据表格

#### 3.3.1 故事列表表格

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 表头行（高度 44px，背景：透明）                                                │
│                                                                             │
│  [☐]  标题              审阅状态   类型      角色数   场景数   生成时间    操作 │
│        （可排序↑）      （可筛选） （可筛选）                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [☐]  午夜咖啡馆         待审阅    短剧       3        5      2小时前    审阅  │
│  ▓    ─────────────────────────────────────────────────────────────────    │
│        ← 待审阅：左侧 4px Memory Yellow 竖条                                  │
│                                                                             │
│  [☑]  星际旅人 ✓         已确认    长篇       8       12      昨天       审阅  │
│       ← 选中行：右侧 2px Action Brown 竖线                                    │
│       ─────────────────────────────────────────────────────────────────    │
│                                                                             │
│  [☐]  记忆碎片           已确认    剧本       5        8      3天前      审阅  │
│       ─────────────────────────────────────────────────────────────────    │
│                                                                             │
│  [☐]  雨夜漫步           已驳回    大纲       2        3      1周前      审阅  │
│  ▓    ─────────────────────────────────────────────────────────────────    │
│        ← 已驳回：左侧 4px 红色竖条，背景变淡                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**表格行规范**：

| 属性 | 值 |
|------|-----|
| 行高 | 56px |
| 行间距 | 0（连续排列） |
| 行边框 | 底部 1px Border Paper（实线或虚线） |
| 交替背景 | 无（保持统一 Paper Cream） |
| Hover | 背景色：color-mix(Paper Cream 95%, Charcoal Brown) |
| 选中 | 右侧 2px Action Brown 竖线 |
| **待审阅** | **左侧 4px Memory Yellow 竖条** |
| **已驳回** | **左侧 4px #E74C3C 竖条 + 背景透明度 60%** |
| 文字 | 14px，Body Brown |
| 状态标签 | 圆角 999px，小尺寸胶囊 |

**审阅状态标签样式**：

| 状态 | 背景 | 文字 | 边框 |
|------|------|------|------|
| 待审阅 | Memory Yellow 15% | Charcoal Brown | 无 |
| 已确认 | Spark Green 15% | Charcoal Brown | 无 |
| 已驳回 | #E74C3C 10% | #E74C3C | 1px #E74C3C 虚线 |
| 已归档 | Muted Tan 20% | Muted Tan | 无 |

#### 3.3.2 角色列表表格

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 表头行                                                                      │
│                                                                             │
│  [☐]  头像   名称        身份        性格标签              关联故事    操作   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [☐]  [👤]   林小雨      咖啡师      温柔 · 内向 · 细腻       2        ⋮    │
│       ─────────────────────────────────────────────────────────────────    │
│                                                                             │
│  [☐]  [👤]   阿默        记忆守护者   神秘 · 安静 · 古怪       1        ⋮    │
│       ─────────────────────────────────────────────────────────────────    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**性格标签样式**：

```
┌────────┐ ┌────────┐ ┌────────┐
│ 温柔   │ │ 内向   │ │ 细腻   │
└────────┘ └────────┘ └────────┘

背景：Paper Cream 深色 10%
文字：Warm Brown，12px
圆角：999px
内边距：4px 10px
```

### 3.4 Review Panel 审阅面板

> **Dreem 截图参考**：Dreem 创作者协作页（PDF 第 3-4 页）右侧为详情/预览面板，展示资产详情、角色属性、场景信息等。角色页（PDF 第 3 页）左侧展示角色属性字段（名称、身份、性格、背景），中央为大图区。本平台将 Dreem 的「左侧属性 + 中央大图」结构转化为「右侧审阅面板」形式，展示 Agent 生成内容，支持用户审阅确认。

#### 3.4.1 故事审阅面板

```
┌─────────────────────────────────────┐
│ Review Panel                        │
│ 宽度：360px                          │
│ 背景：Paper Cream                    │
│ 左边框：虚线 Border                  │
├─────────────────────────────────────┤
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ 午夜咖啡馆              [X]     │ │  ← 标题栏
│ │ Agent 生成 · 2小时前             │ │  ← 来源标记
│ └─────────────────────────────────┘ │
│                                     │
│ ─────────────────────────────────── │
│                                     │
│ 审阅状态                            │
│ ┌───────────────────────────────┐   │
│ │ ● 待审阅                      │   │  ← 状态指示
│ └───────────────────────────────┘   │
│                                     │
│ 类型                                │
│ ┌───────────────────────────────┐   │
│ │ 短剧                          │   │  ← 只读展示
│ └───────────────────────────────┘   │
│                                     │
│ 描述（Agent 生成）                   │
│ ┌───────────────────────────────┐   │
│ │ 一个发生在午夜咖啡馆的奇幻    │   │  ← 可编辑
│ │ 故事...                       │   │
│ │                               │   │
│ └───────────────────────────────┘   │
│                                     │
│ ─────────────────────────────────── │
│                                     │
│ 关联角色 (3) — Agent 生成            │
│ ┌───────────────────────────────┐   │
│ │ [👤] 林小雨                   │   │  ← 可点击跳转
│ │ [👤] 阿默                     │   │
│ │ [👤] 老陈                     │   │
│ └───────────────────────────────┘   │
│                                     │
│ 关联场景 (5) — Agent 生成            │
│ ┌───────────────────────────────┐   │
│ │ [🎬] 开场·雨夜                │   │
│ │ [🎬] 咖啡馆内景               │   │
│ │ ...                           │   │
│ └───────────────────────────────┘   │
│                                     │
│ ─────────────────────────────────── │
│                                     │
│ 修改意见（驳回时填写）                │
│ ┌───────────────────────────────┐   │
│ │                               │   │
│ │                               │   │
│ └───────────────────────────────┘   │
│                                     │
│ ─────────────────────────────────── │
│                                     │
│    ┌────────┐ ┌────────┐ ┌──────┐  │
│    │ ✓ 确认 │ │ ✕ 驳回 │ │ 编辑 │  │  ← 审阅操作按钮
│    └────────┘ └────────┘ └──────┘  │
│                                     │
└─────────────────────────────────────┘
```

**审阅操作按钮规范**：

| 按钮 | 背景 | 文字 | 行为 |
|------|------|------|------|
| ✓ 确认通过 | Spark Green #27AE60 | 白色 | 状态→confirmed，Toast「已确认」 |
| ✕ 驳回 | #E74C3C | 白色 | 弹出修改意见输入框，状态→rejected |
| 编辑 | Action Brown | 白色 | 进入编辑模式，字段可修改 |

**编辑模式按钮**：

| 按钮 | 背景 | 文字 | 行为 |
|------|------|------|------|
| 保存并确认 | Spark Green | 白色 | 保存修改 + 状态→confirmed |
| 保存 | Action Brown | 白色 | 仅保存修改，状态不变 |
| 取消 | transparent | Warm Brown | 取消编辑，恢复原始内容 |

### 3.5 空态设计

#### 3.5.1 工作台首页空态（等待 Agent 产出）

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                                                                             │
│                                                                             │
│                           ┌─────────────┐                                   │
│                           │             │                                   │
│                           │   🤖        │  ← 轻纸面图标（Charcoal Brown      │
│                           │  （线条）    │     线条 + Memory Yellow 点缀）    │
│                           │             │                                   │
│                           └─────────────┘                                   │
│                                                                             │
│                         还没有剧本内容                                      │
│                    在 Chat 中让 Agent 为你生成剧本                            │
│                                                                             │
│                                                                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

背景：Paper Cream
标题：20px，Warm Brown，居中
描述：14px，Muted Tan，居中
图标：64px，线条风格
```

#### 3.5.2 故事列表空态（无待审阅项）

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                                                                             │
│                                                                             │
│                           ┌─────────────┐                                   │
│                           │   ✓         │                                   │
│                           │  （线条）    │                                   │
│                           └─────────────┘                                   │
│                                                                             │
│                      暂无待审阅的剧本                                        │
│                   所有剧本已审阅完毕，等待 Agent 新产出                        │
│                                                                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 3.5.2 加载态（骨架屏）

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 表头行                                                                      │
│ ┌────┬────────────┬───────┬───────┬────────┬────────┬──────────┬──────┐     │
│ │ ⬜ │ ████████   │ ████  │ ████  │ ████   │ ████   │ ██████   │ ██   │     │
│ └────┴────────────┴───────┴───────┴────────┴────────┴──────────┴──────┘     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ ┌────┬──────────────────────────────────────────────────────────────────┐   │
│ │ ⬜ │ ████████████████████████████████████████████████████████████████ │   │
│ └────┴──────────────────────────────────────────────────────────────────┘   │
│ ┌────┬──────────────────────────────────────────────────────────────────┐   │
│ │ ⬜ │ ████████████████████████████████████████████████████████████████ │   │
│ └────┴──────────────────────────────────────────────────────────────────┘   │
│ ┌────┬──────────────────────────────────────────────────────────────────┐   │
│ │ ⬜ │ ████████████████████████████████████████████████████████████████ │   │
│ └────┴──────────────────────────────────────────────────────────────────┘   │
│ ┌────┬──────────────────────────────────────────────────────────────────┐   │
│ │ ⬜ │ ████████████████████████████████████████████████████████████████ │   │
│ └────┴──────────────────────────────────────────────────────────────────┘   │
│ ┌────┬──────────────────────────────────────────────────────────────────┐   │
│ │ ⬜ │ ████████████████████████████████████████████████████████████████ │   │
│ └────┴──────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

骨架屏规范：
- 行数：5 行（与分页默认一致）
- 背景：color-mix(Paper Cream 90%, Muted Tan)
- 动画： shimmer（横向渐变扫过）
- 圆角：4px
```

### 3.6 错误态

#### 3.6.1 加载错误

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                                                                             │
│                           ┌─────────────┐                                   │
│                           │    ⚠️       │                                   │
│                           │  （线条）    │                                   │
│                           └─────────────┘                                   │
│                                                                             │
│                         加载失败                                            │
│                         无法获取故事列表，请检查网络连接                       │
│                                                                             │
│                           ┌─────────────┐                                   │
│                           │   重试      │                                   │
│                           └─────────────┘                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 3.6.2 Toast 轻提示

```
┌─────────────────────────────────────────┐
│ ┌─────────────────────────────────────┐ │
│ │ ⚠️ 保存失败，请重试            [X]  │ │  ← 错误
│ └─────────────────────────────────────┘ │
│ ┌─────────────────────────────────────┐ │
│ │ ✅ 故事已创建                    [X] │ │  ← 成功
│ └─────────────────────────────────────┘ │
│ ┌─────────────────────────────────────┐ │
│ │ ℹ️ 正在保存...                       │ │  ← 进行中
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘

位置：页面右下角
背景：Solid Cream #FFFDF8
边框：1px Border Paper
阴影：--color-shadow-soft
圆角：12px
宽度：320px
```

---

## 4. 关键交互流程

### 4.1 Agent 产出 → 审阅确认 核心工作流

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Agent 产出 → 审阅确认 完整工作流                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  用户在 Chat 中触发                                                          │
│  「生成一个关于午夜咖啡馆的短剧」                                              │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────────────────────────┐                                    │
│  │  Agent 生成中                        │                                    │
│  │  - 生成剧本标题、描述                 │                                    │
│  │  - 生成角色列表（名称/身份/性格）      │                                    │
│  │  - 生成场景列表（名称/描述）           │                                    │
│  │  - 存入数据库，review_status=pending  │                                    │
│  └─────────────────────────────────────┘                                    │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────────────────────────┐                                    │
│  │  页面渲染（story-workspace）          │                                    │
│  │  - 表格展示新生成的剧本               │                                    │
│  │  - 行左侧 Memory Yellow 竖条标记待审阅 │                                    │
│  │  - Dashboard 显示「1 项待审阅」        │                                    │
│  └─────────────────────────────────────┘                                    │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────────────────────────┐                                    │
│  │  用户审阅                            │                                    │
│  │  - 点击待审阅行                      │                                    │
│  │  - 右侧 Review Panel 展开            │                                    │
│  │  - 查看 Agent 生成的完整内容          │                                    │
│  └─────────────────────────────────────┘                                    │
│       │                                                                     │
│       ├─────────────────┬─────────────────┬─────────────────┐               │
│       ▼                 ▼                 ▼                 ▼               │
│  ┌─────────┐      ┌─────────┐      ┌─────────┐      ┌─────────┐            │
│  │ 直接确认 │      │编辑后确认│      │  驳回   │      │  忽略   │            │
│  │ ✓ 确认   │      │修改字段 │      │✕ 驳回   │      │暂不处理 │            │
│  └─────────┘      │保存并确认│      │填修改意见│      └─────────┘            │
│       │           └─────────┘      └─────────┘               │               │
│       ▼                 ▼                 ▼                 ▼               │
│  status=confirmed  status=confirmed  status=rejected   保持pending           │
│  进入后续执行       进入后续执行      Agent 重新生成      待后续处理          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 审阅确认流程

```
用户选中待审阅项（点击表格行）
        ↓
右侧 Review Panel 展开，显示 Agent 生成内容
        ↓
用户查看内容
        ↓
┌─────────────────┬─────────────────┬─────────────────┐
│   直接确认       │   编辑后确认     │    驳回         │
│   「✓ 确认通过」 │   修改字段      │   「✕ 驳回」    │
│                 │   「保存并确认」 │   填写修改意见   │
└─────────────────┴─────────────────┴─────────────────┘
        ↓                 ↓                 ↓
   状态→confirmed    状态→confirmed     状态→rejected
   Toast「已确认」    Toast「已确认」    Toast「已驳回」
   进入后续执行       进入后续执行        Agent 重新生成
   行标记消失         行标记消失          行变红色标记
```

### 4.3 批量审阅流程

```
用户勾选多行 Checkbox（仅限待审阅项）
        ↓
Toolbar 替换为 Batch Review Toolbar（Action Brown 深色带）
        ↓
用户选择批量操作（确认/驳回）
        ↓
确认弹窗：「确定要确认选中的 5 个剧本吗？」
        ↓
确认后执行 → Toast 结果 → 表格刷新
```

### 4.4 筛选流程

```
用户点击「筛选 ▼」
        ↓
下拉面板展开：
┌─────────────────────────────┐
│ 审阅状态                     │
│ ☐ 待审阅                    │
│ ☐ 已确认                    │
│ ☐ 已驳回                    │
│ ☐ 已归档                    │
│ ─────────────────────────── │
│ 类型                        │
│ ☐ 短剧                      │
│ ☐ 长篇                      │
│ ☐ 剧本                      │
│ ☐ 大纲                      │
│ ─────────────────────────── │
│         [重置] [应用]       │
└─────────────────────────────┘
        ↓
用户选择条件 → 点击「应用」
        ↓
表格刷新，Toolbar 显示筛选标签（可点击移除）
┌──────────────────────────────────────────┐
│ 审阅：待审阅 ×  类型：短剧 ×  [清除全部]  │
└──────────────────────────────────────────┘
```

---

## 5. 数据表结构

### 5.1 故事表 (`story_workspace_stories`)

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `id` | UUID | ✅ | auto | 主键 |
| `identifier` | string | ✅ | auto | 业务标识（如 `story-001`） |
| `title` | string(200) | ✅ | - | 故事标题（Agent 生成） |
| `description` | text | ❌ | null | 故事描述（Agent 生成） |
| `status` | enum | ✅ | `draft` | 内容状态：draft / published / archived |
| `review_status` | enum | ✅ | `pending` | **审阅状态：pending / confirmed / rejected** |
| `type` | enum | ✅ | `short` | 类型：short / long / script / outline |
| `content` | text | ❌ | null | 故事内容（Agent 生成的 Markdown） |
| `author_id` | UUID | ✅ | - | 创建者 ID（外键 → users） |
| `workspace_id` | UUID | ✅ | - | 所属工作区 ID |
| `character_count` | int | ✅ | 0 | 关联角色数（冗余，加速查询） |
| `scene_count` | int | ✅ | 0 | 关联场景数（冗余，加速查询） |
| `agent_generated` | boolean | ✅ | `true` | **是否由 Agent 生成** |
| `agent_session_id` | string | ❌ | null | **Agent 会话 ID（关联 chat_thread）** |
| `review_notes` | text | ❌ | null | **用户审阅备注/修改意见** |
| `created_at` | datetime | ✅ | now | 创建时间（Agent 生成时间） |
| `updated_at` | datetime | ✅ | now | 更新时间 |
| `confirmed_at` | datetime | ❌ | null | **用户确认时间** |
| `published_at` | datetime | ❌ | null | 发布时间 |

**索引**：
- `idx_stories_author`: (`author_id`, `updated_at` DESC)
- `idx_stories_review_status`: (`review_status`, `updated_at` DESC) — **按审阅状态查询**
- `idx_stories_status`: (`status`, `updated_at` DESC)
- `idx_stories_type`: (`type`, `updated_at` DESC)
- `idx_stories_search`: (`title` gin_trgm_ops) — 用于搜索
- `idx_stories_agent`: (`agent_session_id`) — **关联 Agent 会话**

### 5.2 角色表 (`story_workspace_characters`)

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `id` | UUID | ✅ | auto | 主键 |
| `identifier` | string | ✅ | auto | 业务标识 |
| `name` | string(100) | ✅ | - | 角色名称（Agent 生成，用户可编辑） |
| `avatar_url` | string | ❌ | null | 头像 URL |
| `identity` | string(200) | ❌ | null | 角色身份/职业（Agent 生成） |
| `personality` | text | ❌ | null | 性格描述（Agent 生成） |
| `background` | text | ❌ | null | 背景故事（Agent 生成） |
| `catchphrase` | string(500) | ❌ | null | 口头禅（Agent 生成） |
| `tags` | string[] | ❌ | [] | 性格标签（Agent 生成） |
| `notes` | text | ❌ | null | 用户审阅备注 |
| `author_id` | UUID | ✅ | - | 创建者 ID |
| `workspace_id` | UUID | ✅ | - | 所属工作区 ID |
| `story_count` | int | ✅ | 0 | 关联故事数（冗余） |
| `review_status` | enum | ✅ | `pending` | **审阅状态：pending / confirmed / rejected** |
| `agent_generated` | boolean | ✅ | `true` | **是否由 Agent 生成** |
| `created_at` | datetime | ✅ | now | 创建时间 |
| `updated_at` | datetime | ✅ | now | 更新时间 |

**索引**：
- `idx_characters_author`: (`author_id`, `updated_at` DESC)
- `idx_characters_name`: (`name` gin_trgm_ops)
- `idx_characters_tags`: (`tags` gin)
- `idx_characters_review`: (`review_status`, `updated_at` DESC) — **按审阅状态查询**

### 5.3 场景表 (`story_workspace_scenes`)

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `id` | UUID | ✅ | auto | 主键 |
| `identifier` | string | ✅ | auto | 业务标识 |
| `name` | string(200) | ✅ | - | 场景名称（Agent 生成） |
| `description` | text | ❌ | null | 场景描述（Agent 生成） |
| `story_id` | UUID | ❌ | null | 所属故事 ID（外键 → stories） |
| `author_id` | UUID | ✅ | - | 创建者 ID |
| `workspace_id` | UUID | ✅ | - | 所属工作区 ID |
| `character_count` | int | ✅ | 0 | 出场角色数（冗余） |
| `order_index` | int | ✅ | 0 | 在故事中的顺序 |
| `review_status` | enum | ✅ | `pending` | **审阅状态：pending / confirmed / rejected** |
| `agent_generated` | boolean | ✅ | `true` | **是否由 Agent 生成** |
| `created_at` | datetime | ✅ | now | 创建时间 |
| `updated_at` | datetime | ✅ | now | 更新时间 |

**索引**：
- `idx_scenes_story`: (`story_id`, `order_index`)
- `idx_scenes_author`: (`author_id`, `updated_at` DESC)
- `idx_scenes_review`: (`review_status`, `updated_at` DESC) — **按审阅状态查询**

### 5.4 关联表

#### 5.4.1 故事-角色关联 (`story_workspace_story_characters`)

| 字段 | 类型 | 说明 |
|------|------|------|
| `story_id` | UUID | 故事 ID |
| `character_id` | UUID | 角色 ID |
| `role_type` | enum | 主角 / 配角 / 龙套 |
| `created_at` | datetime | 关联时间 |

**主键**：(`story_id`, `character_id`)

#### 5.4.2 场景-角色关联 (`story_workspace_scene_characters`)

| 字段 | 类型 | 说明 |
|------|------|------|
| `scene_id` | UUID | 场景 ID |
| `character_id` | UUID | 角色 ID |
| `created_at` | datetime | 关联时间 |

**主键**：(`scene_id`, `character_id`)

### 5.5 工作区表 (`story_workspace_workspaces`)

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `id` | UUID | ✅ | auto | 主键 |
| `name` | string(100) | ✅ | - | 工作区名称 |
| `owner_id` | UUID | ✅ | - | 所有者 ID |
| `settings` | jsonb | ❌ | {} | 工作区设置 |
| `created_at` | datetime | ✅ | now | 创建时间 |
| `updated_at` | datetime | ✅ | now | 更新时间 |

---

## 6. API 路由设计

### 6.1 REST API 路由

```
/api/story-workspace
├── GET    /workspace              ← 获取当前用户工作区
├── PATCH  /workspace/:id          ← 更新工作区设置
│
├── GET    /stories                ← 列表（支持 search/filter/sort/pagination）
├── GET    /stories/:id            ← 详情
├── PATCH  /stories/:id            ← 更新（用户编辑 Agent 生成内容）
├── POST   /stories/:id/confirm    ← **确认审阅**
├── POST   /stories/:id/reject     ← **驳回（含修改意见）**
├── POST   /stories/:id/archive    ← 归档
├── POST   /stories/:id/publish    ← 发布
│
├── GET    /characters             ← 列表
├── GET    /characters/:id         ← 详情
├── PATCH  /characters/:id         ← 更新
├── POST   /characters/:id/confirm ← **确认审阅**
├── POST   /characters/:id/reject  ← **驳回**
│
├── GET    /scenes                 ← 列表
├── GET    /scenes/:id             ← 详情
├── PATCH  /scenes/:id             ← 更新
├── POST   /scenes/:id/confirm     ← **确认审阅**
├── POST   /scenes/:id/reject      ← **驳回**
│
└── POST   /batch                  ← 批量操作
     └── body: { action: 'confirm'|'reject'|'archive', ids: [], review_notes?: string }
```

### 6.2 查询参数规范

**列表接口通用参数**：

| 参数 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `q` | string | 搜索关键词 | `q=咖啡` |
| `review_status` | string | **审阅状态筛选** | `review_status=pending,confirmed` |
| `status` | string | 内容状态筛选 | `status=draft,published` |
| `type` | string | 类型筛选 | `type=short,long` |
| `sort` | string | 排序字段 | `sort=updated_at` |
| `order` | string | 排序方向 | `order=desc` |
| `page` | int | 页码 | `page=1` |
| `per_page` | int | 每页条数 | `per_page=20` |

**响应格式**：

```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 156,
    "total_pages": 8
  }
}
```

---

## 7. 前端组件结构

### 7.1 页面组件

```
frontend/src/pages/story-workspace/
├── StoryWorkspaceDashboardPage.tsx      ← 工作台首页
├── StoryWorkspaceStoriesPage.tsx        ← 故事列表
├── StoryWorkspaceCharactersPage.tsx     ← 角色列表
├── StoryWorkspaceScenesPage.tsx         ← 场景列表
└── index.ts
```

### 7.2 布局组件

```
frontend/src/components/story-workspace/layout/
├── StoryWorkspaceLayout.tsx             ← 根布局（三栏）
├── StoryWorkspaceSidebar.tsx            ← 侧边栏导航
├── StoryWorkspaceReviewPanel.tsx        ← **审阅面板（原 Detail Panel）**
├── StoryWorkspaceToolbar.tsx            ← 工具栏（无新建按钮）
├── StoryWorkspaceBatchReviewToolbar.tsx ← **批量审阅操作栏**
└── index.ts
```

### 7.3 表格组件

```
frontend/src/components/story-workspace/table/
├── StoryWorkspaceStoryTable.tsx         ← 故事表格
├── StoryWorkspaceCharacterTable.tsx     ← 角色表格
├── StoryWorkspaceSceneTable.tsx         ← 场景表格
├── StoryWorkspaceTableRow.tsx           ← 表格行（通用，含审阅状态标记）
├── StoryWorkspacePagination.tsx         ← 分页
├── StoryWorkspaceReviewStatusBadge.tsx  ← **审阅状态标签**
└── index.ts
```

### 7.4 审阅组件

```
frontend/src/components/story-workspace/review/
├── StoryWorkspaceReviewActions.tsx      ← **审阅操作按钮（确认/驳回/编辑）**
├── StoryWorkspaceReviewNotesInput.tsx   ← **驳回修改意见输入**
├── StoryWorkspaceAgentContentDisplay.tsx ← **Agent 生成内容展示**
└── index.ts
```

### 7.5 状态组件

```
frontend/src/components/story-workspace/state/
├── StoryWorkspaceEmptyState.tsx         ← 空态
├── StoryWorkspaceLoadingState.tsx       ← 加载态（骨架屏）
├── StoryWorkspaceErrorState.tsx         ← 错误态
└── index.ts
```

### 7.6 Hooks

```
frontend/src/hooks/story-workspace/
├── useStoryWorkspaceStore.ts            ← Zustand 状态管理
├── useStories.ts                        ← 故事数据查询
├── useCharacters.ts                     ← 角色数据查询
├── useScenes.ts                         ← 场景数据查询
└── index.ts
```

---

## 8. 状态管理设计

### 8.1 Zustand Store 结构

```typescript
interface StoryWorkspaceState {
  // 当前视图
  currentView: 'dashboard' | 'stories' | 'characters' | 'scenes';
  
  // 选中项
  selectedStoryId: string | null;
  selectedCharacterId: string | null;
  selectedSceneId: string | null;
  selectedIds: string[];  // 批量选中（仅限待审阅项）
  
  // **审阅面板**
  reviewPanelOpen: boolean;
  reviewPanelMode: 'view' | 'edit';  // **无 'create' 模式（Agent 生成）**
  
  // 筛选/排序
  filters: {
    reviewStatus?: string[];  // **审阅状态筛选**
    status?: string[];
    type?: string[];
    search?: string;
  };
  sort: {
    field: string;
    order: 'asc' | 'desc';
  };
  
  // 分页
  pagination: {
    page: number;
    perPage: number;
  };
  
  // UI 状态
  sidebarCollapsed: boolean;
  isLoading: boolean;
  error: string | null;
  
  // **审阅操作状态**
  reviewActionInProgress: boolean;  // 确认/驳回操作中
  reviewNotes: string;  // 驳回修改意见
}
```

---

## 9. 路由配置

```typescript
// frontend/src/router/story-workspace.tsx
const storyWorkspaceRoutes = [
  {
    path: '/story-workspace',
    component: StoryWorkspaceLayout,
    children: [
      { path: '', redirect: '/story-workspace/dashboard' },
      { path: 'dashboard', component: StoryWorkspaceDashboardPage },
      { path: 'stories', component: StoryWorkspaceStoriesPage },
      { path: 'characters', component: StoryWorkspaceCharactersPage },
      { path: 'scenes', component: StoryWorkspaceScenesPage },
    ],
  },
];
```

---

## 10. 与现有系统的集成点

### 10.1 复用现有能力

| 能力 | 来源 | 集成方式 |
|------|------|----------|
| 用户认证 | 全局 Auth | 复用现有用户体系 |
| **Agent 服务** | **`claude-agent` 服务** | **Agent 通过 SSE 端点生成剧本内容，存入 story-workspace 数据表** |
| 文件上传 | Workspace API | 角色头像走 `/api/workspace/files` |
| 色彩系统 | tokens.css | 直接引用 CSS Variable |
| 字体系统 | 全局字体 | 复用现有字体配置 |
| Toast 通知 | 全局组件 | 复用现有 Toast 组件 |
| Modal/Dialog | 全局组件 | 复用现有 Modal 组件 |
| 按钮/Input | 全局组件 | 复用现有基础组件 |

### 10.2 与 claude-agent 服务的集成

```
用户 Chat 对话
     │
     │ "生成一个关于午夜咖啡馆的短剧"
     ▼
┌─────────────────────────────┐
│  claude-agent 服务           │
│  POST /api/claude-agent      │
│  - 接收用户指令              │
│  - Agent 生成剧本内容        │
│  - 调用 story-workspace API  │
└─────────────────────────────┘
     │
     ▼
┌─────────────────────────────┐
│  story-workspace API         │
│  POST /api/story-workspace/  │
│  - 接收 Agent 生成的数据     │
│  - 存入数据库                │
│  - 标记 review_status=pending│
└─────────────────────────────┘
     │
     ▼
┌─────────────────────────────┐
│  Story Workspace 页面        │
│  - 轮询/推送获取新数据       │
│  - 渲染 Agent 生成内容       │
│  - 用户审阅确认              │
└─────────────────────────────┘
```

### 10.3 与 Deck 编辑器的关系（后续迭代）

```
Story Workspace          Deck Editor
     │                        │
     │  故事内容编辑            │
     │  （本期：纯文本/Markdown）│
     │  （后续：富文本/Deck 集成）│
     │                        │
     ▼                        ▼
┌──────────┐           ┌──────────┐
│ 故事详情  │ ───────→ │ Deck 卡片 │  （后续：故事内容可转为 Deck）
│ content  │           │ 编辑     │
└──────────┘           └──────────┘
```

---

## 11. 验收清单

### 11.1 布局验收

- [ ] 桌面端三栏布局渲染正确（Sidebar 240px + Main 自适应 + Review Panel 360px）
- [ ] 确认无移动端/平板端相关代码或样式
- [ ] Sidebar 始终 240px 展开，不可折叠为图标栏
- [ ] Review Panel 始终 360px 展开，不作为抽屉
- [ ] **审阅状态标记正确显示（待审阅黄条 / 已驳回红条）**
- [ ] 批量审阅操作栏正确替换 Toolbar

### 11.2 交互验收

- [ ] 表格行点击选中，右侧审阅面板展开
- [ ] **Agent 生成内容在审阅面板中正确展示**
- [ ] **确认/驳回/编辑后确认操作流程完整**
- [ ] **批量审阅（批量确认/驳回）流程完整**
- [ ] 表格排序、筛选、分页功能正常
- [ ] 空态、加载态、错误态、选中态均有实现
- [ ] **Agent 生成中状态有 Loading 指示**

### 11.3 视觉验收

- [ ] 色彩与 tokens.css 一致
- [ ] 轻纸面分区原则贯彻
- [ ] **审阅状态标签样式符合规范（待审阅/已确认/已驳回）**
- [ ] 选中态使用右侧细线
- [ ] **待审阅项左侧 Memory Yellow 竖条标记**

### 11.4 数据验收

- [ ] 数据表结构与文档一致（含 review_status / agent_generated 字段）
- [ ] API 路由与文档一致（含 confirm / reject 端点）
- [ ] 组件命名与文档一致

---

## 12. 关键决策记录

| 决策 ID | 日期 | 决策 | 决策者 | 影响 |
|---------|------|------|--------|------|
| DEC-001 | 2026-08-01 | 采用轻纸面分区布局 | DesignArchitect | 影响所有页面视觉 |
| DEC-002 | 2026-08-01 | 复杂画布以数据表呈现 | DesignArchitect | 降低本期复杂度 |
| DEC-003 | 2026-08-01 | 三栏桌面布局 | DesignArchitect | 影响布局组件设计 |
| DEC-004 | 2026-08-01 | `story-workspace` 前缀命名 | DesignArchitect | 影响所有代码命名 |
| DEC-005 | 2026-08-01 | 排除视频模块 | DesignArchitect | 明确范围边界 |
| DEC-006 | 2026-08-01 | **仅桌面端设计，排除移动端/平板端** | DesignArchitect + local-board | **明确排除所有移动端适配** |
| **DEC-007** | **2026-08-01** | **核心工作流：Agent 产出 → 页面渲染 → 用户审阅确认 → 执行** | **DesignArchitect + local-board** | **重新定义业务模型：从手动 CRUD 改为审阅确认** |
| **DEC-008** | **2026-08-01** | **用户不手动创建内容，仅审阅 Agent 产出** | **local-board** | **明确用户角色为审阅者而非创作者** |

---

## 13. 增量变更说明

- **初始版本**（2026-08-01）：创建本文档，定义 story-workspace 布局骨架设计
- **修订 2**（2026-08-01）：根据评论「设计稿的主要属性，应该参考 Dreem 调研 PDF 中的截图」—— 在 2.1 布局骨架、3.1 Sidebar、3.4 Detail Panel 等章节增加 Dreem 截图参考说明；新增 15. Dreem 截图参考详解章节
- **修订 3**（2026-08-01）：**根据评论「交互流程应该是 Agent 产出剧本工作空间，然后页面渲染剧本信息，用户确认，后续执行」—— 重大业务模型修正：从「手动 CRUD」改为「Agent 产出 → 用户审阅确认」模式。影响范围：全局布局说明、Toolbar（移除新建按钮）、Data Table（审阅状态标记）、Detail Panel → Review Panel（审阅操作按钮）、交互流程、数据表结构（新增 review_status/agent_generated 字段）、API 路由（新增 confirm/reject 端点）、组件结构、状态管理、验收清单**

---

## 14. 附录

### 12.1 命名前缀汇总

| 类型 | 前缀 | 示例 |
|------|------|------|
| 路由 | `/story-workspace/` | `/story-workspace/stories` |
| 页面组件 | `StoryWorkspace*Page` | `StoryWorkspaceStoriesPage` |
| 布局组件 | `StoryWorkspace*Layout` | `StoryWorkspaceThreeColumnLayout` |
| 业务组件 | `StoryWorkspace*` | `StoryWorkspaceStoryTable` |
| API 路由 | `/api/story-workspace/` | `/api/story-workspace/stories` |
| 数据库表 | `story_workspace_*` | `story_workspace_stories` |
| TypeScript 类型 | `StoryWorkspace*` | `StoryWorkspaceStory` |
| Hooks | `useStoryWorkspace*` | `useStoryWorkspaceStore` |
| CSS 类 | `.story-workspace-*` | `.story-workspace-table-row` |
| 目录 | `story-workspace/` | `pages/story-workspace/` |

### 12.2 参考文档

- [story-workspace-prd.md](./story-workspace-prd.md) — 本设计的 PRD 文档
- [Ink & Memory UI Design v2](../../prd/Ink%20&%20Memory%20UI%20Design%20v2.pdf) — 品牌视觉规范
- [Color System](../../prd/color_system/README.md) — 色彩系统
- [Workspace Filesystem](../workspace/workspace-filesystem.md) — 工作区文件系统
- [Workspace Storage API](../workspace/workspace-storage-api.md) — 文件管理 API
- [调研 Dreem app 平台](../story-workspace/调研Dreem_app平台.pdf) — Dreem 平台调研资料（截图来源）

---

## 15. Dreem 截图参考详解

本章详细记录从 Dreem 调研 PDF 截图中提取的视觉参考点，按页面/截图分类，标注采纳与适配差异。

### 15.1 截图来源索引

| 截图内容 | PDF 页码 | 本章引用标记 |
|----------|----------|-------------|
| 创作者协作页 — 资产总览 | 第 3-4 页 | [Dreem-资产页] |
| 创作台页 — 剧本编辑 | 第 2 页 | [Dreem-创作台] |
| 角色资产页 — 角色详情 | 第 3 页 | [Dreem-角色页] |
| 场景资产页 — 场景列表 | 第 4 页 | [Dreem-场景页] |
| 故事线/叙事点 — 大纲视图 | 第 6 页 | [Dreem-故事线] |
| 交互控件 — 决策点 | 第 7-8 页 | [Dreem-交互控件] |
| 移动端消费页 | 第 9-11 页 | [Dreem-移动端]（本期排除） |

### 15.2 [Dreem-资产页] 创作者协作页（PDF 第 3-4 页）

**截图描述**：
Dreem 创作者协作页采用三栏布局：
- 左侧：窄边栏导航（Home、World、Assets、Settings 图标）
- 中间：资产列表区，分 Assets / Outline 标签页
  - Assets 标签下展示 Characters（角色头像+名称+artifact 数）、Locations（场景缩略图+名称）、Script（查看全文按钮）、World assets（World Builder 入口）
- 右侧：详情/预览面板（选中资产后展示）
- 顶部：面包屑导航 `< Ordinary Waiting Day > Storylines > A`

**提取的设计参考**：

| Dreem 元素 | 本平台处理方式 | 位置 |
|------------|---------------|------|
| 三栏布局骨架 | ✅ 采纳，Sidebar 240px + Main + Detail 360px | 2.1 全局布局 |
| 左侧图标边栏 | 🔄 适配，扩展为 240px 图标+文字边栏 | 3.1 Sidebar |
| Assets / Outline 标签 | 🔄 适配，转化为 Sidebar 导航项（故事/角色/场景） | 4.1 信息架构 |
| 资产卡片（缩略图+名称+数量） | 🔄 适配，转化为表格行（头像+名称+字段） | 3.3 Data Table |
| 面包屑导航 | ❌ 排除，以 Sidebar 导航替代 | — |
| World Builder 入口 | ❌ 排除，本期无世界构建 | — |
| 暗色主题 | ❌ 排除，使用暖纸色浅色主题 | 6.1 色彩应用 |

### 15.3 [Dreem-创作台] 创作台页（PDF 第 2 页）

**截图描述**：
Dreem 创作台页展示智能体驱动的创作界面：
- 左侧：故事大纲导航（场景列表）
- 中间：主编辑区（剧本内容）
- 右侧：属性面板（场景、人物、故事大纲属性）
- 底部：进度指示

**提取的设计参考**：

| Dreem 元素 | 本平台处理方式 | 位置 |
|------------|---------------|------|
| 左-中-右三区结构 | ✅ 采纳，Sidebar + Table + Detail Panel | 2.1 全局布局 |
| 左侧大纲导航 | 🔄 适配，转化为 Sidebar 模块导航 | 3.1 Sidebar |
| 中间内容编辑 | 🔄 适配，表格列表 + 详情面板编辑 | 3.3 / 3.4 |
| 右侧属性面板 | ✅ 采纳，Detail Panel 表单 | 3.4 Detail Panel |
| 智能体驱动表单 | 🔄 适配，本期为 Agent 产出 → 用户审阅确认 | 4.1 核心工作流 |
| 底部进度指示 | ❌ 排除，本期简化 | — |

### 15.4 [Dreem-角色页] 角色资产页（PDF 第 3 页）

**截图描述**：
Dreem 角色资产页展示：
- 左侧：角色属性面板（名称、身份、性格、背景、口头禅等）
- 中央：角色大图 + 四视角转面图（正面/侧面/背面）
- 标签系统：角色属性以标签/字段形式组织

**提取的设计参考**：

| Dreem 元素 | 本平台处理方式 | 位置 |
|------------|---------------|------|
| 角色属性字段体系 | ✅ 采纳（名称、身份、性格、背景、口头禅） | 4.3.3 角色资产 |
| 标签系统 | ✅ 采纳，性格标签以胶囊标签展示 | 3.3.2 角色表格 |
| 四视角转面图 | ❌ 排除，本期仅支持单张头像 | 4.3.3 角色属性字段 |
| 左侧属性 + 中央大图 | 🔄 适配，转化为表格行 + 右侧详情面板 | 3.4.2 角色详情面板 |
| 人物三视图 | ❌ 排除，本期以数据表呈现 | — |

### 15.5 [Dreem-场景页] 场景资产页（PDF 第 4 页）

**截图描述**：
Dreem 场景资产页展示：
- 场景缩略图网格（Apartment Bedroom、Apartment Kitchen、Metro Train Car 等）
- 每个场景显示缩略图 + 名称 + artifact 数量
- 场景详情面板：描述、关联角色、场景布局

**提取的设计参考**：

| Dreem 元素 | 本平台处理方式 | 位置 |
|------------|---------------|------|
| 场景列表 + 详情结构 | ✅ 采纳 | 4.3.4 场景资产 |
| 场景描述 + 关联角色 | ✅ 采纳 | 5.3 场景表 |
| 缩略图网格 | ❌ 排除，本期以表格呈现 | — |
| 场景布局可视化 | ❌ 排除，本期以数据表呈现 | — |

### 15.6 [Dreem-故事线] 故事线/叙事点（PDF 第 6 页）

**截图描述**：
Dreem 故事线页面展示：
- 左侧：故事线列表（Late Start, Dull Ache / The Interview... / Bug Report...）
- 每个故事线显示 nodes 数量（如 "4 nodes"）
- 右侧：叙事点分组窗口
- 点击叙事点展开镜头描述文稿

**提取的设计参考**：

| Dreem 元素 | 本平台处理方式 | 位置 |
|------------|---------------|------|
| 故事线 → 叙事点层级 | ✅ 采纳（故事 → 场景层级） | 4.1 信息架构 |
| 节点计数 | ✅ 采纳（角色数/场景数字段） | 4.3.2 故事表格 |
| 故事线可视化编辑 | ❌ 排除，本期以表格呈现 | — |
| 镜头文稿呈现 | ❌ 排除，本期排除视频模块 | — |

### 15.7 [Dreem-交互控件] 交互控件/决策点（PDF 第 7-8 页）

**截图描述**：
Dreem 交互控件展示：
- 决策选项：Hold 1500ms → Into the Afternoon
- 可添加/编辑交互选项
- 预览窗口：镜头预览 + 控件叠加
- 历史版本：History / version 切换

**提取的设计参考**：

| Dreem 元素 | 本平台处理方式 | 位置 |
|------------|---------------|------|
| 决策/选项概念 | ✅ 采纳（以交互类型字段记录） | 4.3.2 故事表格 |
| 可视化决策控件 | ❌ 排除，本期以纯文本/Markdown 记录 | — |
| 预览窗口 | ❌ 排除，本期排除视频模块 | — |
| 历史版本 | ❌ 排除，后续迭代 | — |

### 15.8 [Dreem-移动端] 移动端消费页（PDF 第 9-11 页）

**截图描述**：
Dreem 移动端展示：
- 底部导航栏（Home、Explore、+、Chats、Profile）
- 角色/故事卡片网格
- 视频播放器界面
- 用户画像/关注/粉丝

**提取的设计参考**：

| Dreem 元素 | 本平台处理方式 |
|------------|---------------|
| 底部导航 | ❌ 排除（DEC-006：仅桌面端） |
| 卡片网格 | ❌ 排除（本期以表格呈现） |
| 视频播放器 | ❌ 排除（本期排除视频模块） |
| 用户画像/关注 | ❌ 排除（后续迭代） |

### 15.9 Dreem → Ink & Memory 视觉映射表

| 维度 | Dreem 风格 | Ink & Memory 适配 |
|------|-----------|-------------------|
| 主题 | 暗色/浅色双主题 | 暖纸色浅色单主题 |
| 背景色 | 深色 #1a1a1a / 白色 | Warm Canvas #F6EFE5 |
| 边栏 | 窄图标栏 ~60px | 240px 图标+文字 |
| 资产展示 | 缩略图卡片 | 数据表格行 |
| 选中态 | 背景色块高亮 | 右侧 2px 竖线 |
| 强调色 | 橙色 #FF6B35 | Action Brown #5F4A36 |
| 标签 | 圆角胶囊深色底 | 圆角胶囊 Paper Cream 底 |
| 分割线 | 实线细边框 | Border Paper 虚线 |
| 字体 | 系统无衬线 | 系统无衬线 + Excalifont |
| 按钮 | 圆角矩形，橙色填充 | 圆角 8px，Action Brown 填充 |
