<!-- [Input] workflow 第 1 阶段 PRD、第 2 阶段结构草图、第 3 阶段层级逻辑、两张 Codex.app 任务编辑参考截图与 Ink & Memory 现行视觉 token。 -->
<!-- [Output] 高级任务周期编辑弹窗的高保真视觉规格、响应式状态规范与可运行 HTML/Tailwind 2.2.19 参考。 -->
<!-- [Pos] html-design-workflow 第 4 阶段过程证据；供正式 PRD、交互设计与后续实现复用，不替代生产代码。 -->
<!-- [Sync] 2026-10-07: 完成编辑任务、五项重复菜单、高级日程、新聊天、模型和加载/错误/保存状态的桌面及窄屏设计。 -->

# Ink & Memory 高级任务周期 UI 设计（Stage 4）

> 视觉方向：**Ultra-Sensory Minimalism / 暖纸张手记**
>
> 技术基线：HTML5、Tailwind CSS 2.2.19、Font Awesome 6.0.0、Noto Serif SC、Noto Sans SC。
>
> 参考边界：截图用于确认信息结构、折叠关系与菜单顺序；红色矩形是需求标注，不进入成品。

## 1. 视觉结论

任务编辑器是一张从 Calendar/Chat 上抬起的书写纸面。它保留参考图的固定标题栏、正文单滚动轴、固定操作栏、双行日程卡和大触控行，同时改用 Ink & Memory 现有暖纸、墨色、纸线和手写标题语义。界面不复制 Codex.app 的黑灰底、蓝色 switch 或红色标注框。

主标题和区块标题采用仓库现有的 `Excalifont / Xiaolai` 语义，参考页以 `Noto Serif SC` 回退；字段、菜单、状态与按钮采用 `Noto Sans SC`。纸面层级依靠色温、1px 纸线、留白和轻阴影表达，不堆叠重边框。唯一持续强调色为暖棕墨色；成功、警告和错误只用于状态反馈。

高级区只出现“每次运行时都开启新聊天”和“模型”。参考图中的“归档成功运行记录、项目、强度”不进入本轮成品。折叠只改变可见性，不改变任何 `desired` 值。

## 2. 美学样式表（Aesthetic Style）

| 维度 | 高保真规格 | 使用位置 |
| --- | --- | --- |
| 风格 | 暖纸张超感官极简，带轻微手记感 | 弹窗、菜单、二级规则编辑器 |
| App 背景 | `var(--color-bg-app)`；遮罩 `var(--color-bg-overlay)` | 原 Chat / Calendar 与弹窗之间 |
| 主纸面 | `var(--color-bg-paper)` | 主弹窗、窄屏全高 sheet |
| 抬升纸面 | `var(--color-bg-surface-solid)` | 日程组合卡、高级字段、菜单 |
| 柔和填充 | `var(--color-bg-hover)` / `var(--color-bg-active)` | hover、选中星期、加载骨架 |
| 主文字 | `var(--color-text-primary)` | 标题、字段标签、当前值 |
| 正文 | `var(--color-text-body)` | prompt 与说明 |
| 次级文字 | `var(--color-text-secondary)` | 规则摘要、Thread 路径说明、alias |
| 静默文字 | `var(--color-text-muted)` | 占位、禁用项、加载说明 |
| 纸线 | `var(--color-border-paper)`，通常 1px | 分组外框、行分隔、菜单边界 |
| 动作墨色 | `var(--color-action-primary)` | 主按钮、switch 开启、焦点环 |
| 成功 / 警告 / 错误 | 复用 `--color-state-success/warning/danger` | 保存成功、待处理、字段和目录错误 |
| 标题字体 | `Excalifont, Xiaolai, Noto Serif SC, serif`，500–600 | “编辑任务”“高级日程”“高级” |
| UI 字体 | `Noto Sans SC, system-ui, sans-serif`，400–600 | 字段、菜单、按钮、反馈 |
| 圆角 | 行卡 14px；弹窗 24px；菜单 16px；窄屏 sheet 顶角 24px | 与现有 Calendar 纸面保持同族 |
| 阴影 | 桌面弹窗两层暖阴影；卡片以纸线为主 | 只表现真实叠层，不做漂浮卡片墙 |
| 动效 | 160–220ms；位移不超过 8px | 折叠、菜单、switch、sheet、保存反馈 |

### 2.1 视觉变量

生产实现优先直接复用 `frontend/app/_dream/styles/tokens.css`。下列别名只让 Stage 4 参考代码易读，不形成第二套主题来源。

```css
:root {
  --task-app: var(--color-bg-app, #f6efe5);
  --task-paper: var(--color-bg-paper, #fffaf2);
  --task-raised: var(--color-bg-surface-solid, #fffdf8);
  --task-hover: var(--color-bg-hover, rgba(95, 74, 54, .06));
  --task-active: var(--color-bg-active, rgba(95, 74, 54, .12));
  --task-overlay: var(--color-bg-overlay, rgba(39, 31, 24, .50));
  --task-line: var(--color-border-paper, #d8c7b3);
  --task-line-soft: var(--color-border-neutral, #e6ddd0);
  --task-focus: var(--color-border-focus, #5f4a36);
  --task-ink: var(--color-text-primary, #3f3429);
  --task-body: var(--color-text-body, #4b3f33);
  --task-sub: var(--color-text-secondary, #7a6a59);
  --task-quiet: var(--color-text-muted, #9a8a78);
  --task-action: var(--color-action-primary, #5f4a36);
  --task-on-action: var(--color-text-on-action, #fff);
  --task-success: var(--color-state-success, #7e9468);
  --task-warning: var(--color-state-warning, #c78855);
  --task-danger: var(--color-state-danger, #b35f50);
  --task-shadow-soft: var(--color-shadow-soft, rgba(91, 69, 44, .08));
  --task-shadow-medium: var(--color-shadow-medium, rgba(91, 69, 44, .16));
  --task-radius-row: 14px;
  --task-radius-menu: 16px;
  --task-radius-modal: 24px;
  --task-header-h: 72px;
  --task-footer-h: 76px;
}
```

明暗主题由现有 token 切换。暗色模式仍是暖黑纸面：`#2a241f` 主纸、`#342d27` 抬升纸、`#f3e8d8` 主墨；不额外引入纯黑、纯白和高饱和蓝。

## 3. 响应式画布与滚动合同

| 视口 | 主容器 | 尺寸和滚动 | 菜单 / 二级编辑 |
| --- | --- | --- | --- |
| `≥ 768px` | 居中任务弹窗 | `width:min(920px, calc(100vw - 48px))`；`max-height:calc(100dvh - 48px)`；标题和底部固定，只有正文滚动 | 重复、模型为锚定菜单；高级日程为居中二级 dialog |
| `< 768px` | 全高任务 sheet | `position:fixed; inset:0`；标题和底部固定；正文单独滚动；处理上下安全区 | 重复、模型、高级日程统一为 bottom sheet；一次只显示一层 |

- 桌面正文水平内边距 32px，窄屏 16px；可读内容最大宽 760px并居中。
- 桌面弹窗圆角 24px，窄屏全高 sheet 不保留外圆角；bottom sheet 仅顶部圆角 24px。
- 文本区最小高 176px，允许内部 resize 只限桌面；窄屏固定为 168px 起步并随正文滚动。
- 所有交互目标不小于 `44 × 44px`。菜单选项最小高 48px，switch 热区不小于 52px。
- 主弹窗、菜单、二级编辑器各自管理溢出；任一时刻只存在一个页面级滚动容器。
- 视口跨过断点时保留 `desired`、当前字段、展开状态和返回焦点目标，不重新初始化表单。

## 4. UI 组件结构

| 编号 | 建议组件名 | 视觉职责 | 交互与状态职责 |
| --- | --- | --- | --- |
| `A1` / `K1` | `ScheduledTaskEditor` | 桌面纸面弹窗 / 窄屏全高 sheet | 持有 effective、desired、revision 与焦点恢复 |
| `A2` / `K2` | `TaskEditorHeader` | 手写感标题、关闭入口 | 标题固定；关闭沿用现有未保存规则 |
| `B1` | `TaskPromptField` | 大段 prompt 的纸面书写区 | 沿用现有必填、长度和错误关联 |
| `C1` | `ScheduleSummaryCard` | 两行连续纸卡；第一行频率，第二行完整摘要 | 汇总 desired；不在浏览器推算 effective schedule |
| `C2` / `G1` / `L1` | `RepeatPicker` | 五项单选菜单 | 固定顺序：每小时、每天、工作日、每周、自定义 |
| `C3` / `H1` / `M1` | `AdvancedScheduleEditor` | 规则类型、条件字段、时区、摘要和 next run | “应用”只写 desired；“保存”才提交完整 definition |
| `D1` / `D2` | `AdvancedSection` | 低声量手写小标题与折叠内容 | 折叠不清空 Thread mode 或 modelAlias |
| `D3` / `D4` / `D5` | `RunThreadModeField` | 新聊天 switch 和动态说明 | 关闭映射 `source_thread`；开启映射 `new_thread_each_run` |
| `D6` / `D7` / `J1` | `TaskModelPicker` | 模型展示名、alias、目录状态 | 保留不可用旧值；不静默选默认模型 |
| `E1` | `TaskEditorFeedback` | 页面级错误、revision 冲突、保存反馈 | 保留 desired，提供可行动恢复入口 |
| `A4` / `K4` | `TaskEditorActions` | 固定底栏、暂停/恢复和保存 | 保存防重；成功用完整服务端回执替换基线 |

### 4.1 主弹窗排版

```text
TaskEditor
├─ 72px Header：编辑任务 / 关闭
├─ ScrollBody（32px 桌面，16px 窄屏）
│  ├─ Prompt：纸面多行编辑区
│  ├─ 24px 间距
│  ├─ ScheduleSummaryCard：重复 + 高级日程
│  ├─ 24px 间距
│  ├─ AdvancedSection：新聊天 + 模型
│  └─ Feedback：字段错误 / revision 冲突 / 保存失败
└─ 76px Footer：暂停/恢复 / 保存
```

标题使用 24px/34px 手写感字体。字段主标签为 15px/22px、500；当前值为 14px/22px；辅助说明为 12px/19px。两行日程卡中间只有一条 1px 纸线，避免出现四周重复描边。

### 4.2 五项重复菜单

- 桌面宽 224px，右边缘与当前值对齐；默认向下，空间不足向上翻转。
- 菜单使用抬升纸面、16px 圆角、1px 纸线与两层暖阴影。
- 选项顺序固定为“每小时、每天、工作日、每周、自定义”，不得穿插分组标题。
- 当前 desired 使用浅暖棕底和右侧勾选；hover 只增加柔和底色；焦点环在菜单内部可见。
- 选择“自定义”立即进入高级日程；取消规则编辑时恢复打开前的 desired。
- 窄屏菜单为 bottom sheet，顶部有拖动柄、标题与关闭入口；选项全宽，底部加安全区。

### 4.3 高级日程编辑器

桌面宽 `min(620px, calc(100vw - 48px))`，最大高 `calc(100dvh - 64px)`；窄屏 bottom sheet 最大高 `92dvh`。标题与操作栏固定，字段区单独滚动。

| 规则类型 | 条件区 | 摘要示例 |
| --- | --- | --- |
| 一次 | 日期 + 本地时间 | `2026年10月8日 09:00 · Asia/Shanghai` |
| 间隔 | 正整数 + 分钟/小时/天/周 | `每 2 小时 · 首次运行由服务端计算` |
| 每天 | 本地时间 | `每天 09:00 · Asia/Shanghai` |
| 每周 | 至少一个星期 + 本地时间 | `周一、周三、周五 · 09:00 · Asia/Shanghai` |

- 星期使用 7 个等宽纸片按钮，选中态为暖棕墨底；不能只用颜色表示选中，按钮同时保持 `aria-pressed`。
- 时区显示 IANA 名称。长名称允许横向省略，完整内容在选项中展示。
- H10 是浅暖底摘要条，先显示规范化规则，再显示服务端返回的“下次运行”。加载 next run 时保留规则文本。
- 字段错误紧贴字段；计算失败显示在摘要下方。错误不清空任何输入。
- “应用”只更新主表单 desired；底部文案可写“应用到任务草稿”，避免误解为已保存。

### 4.4 高级折叠、新聊天与模型

“高级”标题为 17px/26px 手写感字体，右侧 16px chevron；整行 44px 可点击。展开时 chevron 旋转 180°，内容用 180ms 高度和透明度过渡。收起后值不变。

新聊天行和模型行各是一张独立纸卡，最小高 76px，间距 12px。新聊天说明随 switch 变化：

| Switch | 主标签下说明 | 持久化语义 |
| --- | --- | --- |
| 关闭（新建 default） | 在创建此任务的聊天中继续运行 | `source_thread` |
| 开启 | 每次运行都会创建独立聊天 | `new_thread_each_run` |

switch 为 48×28px，轨道关闭用纸线灰，开启用暖棕动作色；滑块 22px。键盘 Space 切换，焦点环包围完整控件。不可用时降低饱和度但保留标签可读性。

模型行主文案用展示名，辅助文案用精确 alias。桌面菜单最宽 360px、最大高 320px；每项主文案可换行，alias 使用 12px 次级文字。不可用旧值保留在列表顶部，带“不可用”文字和禁选语义，不用删除线暗示数据已删除。

## 5. 状态与反馈规格

### 5.1 表单与保存

| 状态 | 视觉变化 | 按钮与恢复 |
| --- | --- | --- |
| `idle` | 展示 effective；无全局提示 | 无变化时保存禁用 |
| `editing` | 字段按 desired 更新；底栏顶部可出现 2px 暖棕细线 | 表单完整后保存可用 |
| `saving` | 保存按钮内显示 14px spinner 和“保存中”；按钮宽度固定 | 防重复提交；其他字段保持可读 |
| `saved` | 按钮短暂显示勾选和“已保存”；不弹额外确认框 | 以完整服务端回执替换 effective/desired/revision |
| `revision_conflict` | E1 使用浅警告纸条，列出发生差异的“重复 / 新聊天 / 模型” | “查看最新设置”；desired 保留，重新检查后保存 |
| `save_failed` | E1 使用浅错误纸条 | “重试保存”；不清空 desired |

### 5.2 模型目录

| 状态 | 模型行表现 | 菜单表现 |
| --- | --- | --- |
| `loading_catalog` | 保留已有模型名；右侧小 spinner；辅助文案“正在更新可用模型” | 暂不打开空菜单 |
| `catalog_ready` | 展示 desired 模型 | 当前项勾选，其余可调用模型可选 |
| `catalog_empty` | 值区显示“当前没有可调用模型” | 提供“查看模型与订阅设置” |
| `catalog_failed` | 错误色短句“模型目录暂不可用” | 同行“重试”；不清空 effective alias |
| `saved_alias_unavailable` | 展示旧模型名和“不可用”标签 | 旧值禁选；必须选择可调用 alias 才能保存相关变更 |

模型错误或 Thread 配置错误需要处理时自动展开高级区，并把焦点移到对应错误标题。不能用 toast 取代字段反馈。

### 5.3 高级日程错误

- 缺日期、时间、星期或时区：相应字段边框切换到错误色，下面显示 12px 可行动说明。
- interval 非正整数：保留原输入，提示“请输入大于 0 的整数”。
- next run 计算失败：保留规范化规则和输入，摘要下显示“暂时无法计算下次运行时间，请重试”。
- capability 不可用：二级编辑器顶部显示页面级错误，应用禁用；不退化为浏览器 timer。

## 6. 微交互与可访问性

- 弹窗进入：200ms `opacity + translateY(8px)`；窄屏 bottom sheet：220ms `translateY(16px)`。离开反向。
- 菜单进入：160ms `opacity + translateY(-4px)`；向上翻转时方向相反。
- switch：轨道颜色 160ms，滑块 180ms cubic-bezier；不使用弹跳。
- 高级折叠：180ms；页面自动展开错误时不做大幅滚动，只使用 `scrollIntoView({block:'nearest'})`。
- `prefers-reduced-motion: reduce` 下取消位移和高度动画，只保留即时显隐。
- 主弹窗为 `role="dialog" aria-modal="true"`；二级规则编辑器打开时主弹窗暂时不可交互。
- 重复和模型菜单使用 `role="menu"` / `menuitemradio`；方向键移动，Enter/Space 选择，Escape 关闭并返回入口。
- switch 使用原生 button + `role="switch"` + `aria-checked`；状态说明通过 `aria-describedby` 关联。
- 所有 spinner 提供屏幕阅读器文本；装饰图标统一 `aria-hidden="true"`。

```css
@keyframes task-editor-in {
  from { opacity: 0; transform: translateY(8px) scale(.995); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
@keyframes task-sheet-in {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes task-spin { to { transform: rotate(360deg); } }
```

## 7. HTML + Tailwind CSS 2.2.19 可运行参考

以下代码可保存为独立 `.html` 直接打开。它实现主弹窗、高级折叠、五项重复菜单、新聊天 switch、模型目录加载/失败/不可用状态、模型菜单、高级日程编辑器和保存状态。数据只用于视觉演示；生产实现必须接入真实 desired/effective/revision、Admin schedule 回执与 Gateway 模型目录。

原型支持在浏览器控制台调用 `previewModelCatalog('loading'|'ready'|'error'|'unavailable')` 和 `previewSave('saving'|'error'|'conflict'|'saved')` 查看状态；这些预览入口不进入产品 UI。

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover" />
  <title>Ink & Memory · 编辑任务</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;500;600&family=Noto+Sans+SC:wght@300;400;500;600&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="https://lf6-cdn-tos.bytecdntp.com/cdn/expire-100-M/font-awesome/6.0.0/css/all.min.css" />
  <link rel="stylesheet" href="https://lf3-cdn-tos.bytecdntp.com/cdn/expire-1-M/tailwindcss/2.2.19/tailwind.min.css" />
  <style>
    :root {
      --color-bg-app:#f6efe5; --color-bg-paper:#fffaf2;
      --color-bg-surface-solid:#fffdf8; --color-bg-overlay:rgba(39,31,24,.50);
      --color-bg-hover:rgba(95,74,54,.06); --color-bg-active:rgba(95,74,54,.12);
      --color-border-paper:#d8c7b3; --color-border-neutral:#e6ddd0;
      --color-border-focus:#5f4a36; --color-text-primary:#3f3429;
      --color-text-body:#4b3f33; --color-text-secondary:#7a6a59;
      --color-text-muted:#9a8a78; --color-action-primary:#5f4a36;
      --color-text-on-action:#fff; --color-state-success:#7e9468;
      --color-state-warning:#c78855; --color-state-danger:#b35f50;
      --color-disabled-bg:#d6cbbb; --color-shadow-soft:rgba(91,69,44,.08);
      --color-shadow-medium:rgba(91,69,44,.16);
      --task-app:var(--color-bg-app); --task-paper:var(--color-bg-paper);
      --task-raised:var(--color-bg-surface-solid); --task-hover:var(--color-bg-hover);
      --task-active:var(--color-bg-active); --task-overlay:var(--color-bg-overlay);
      --task-line:var(--color-border-paper); --task-line-soft:var(--color-border-neutral);
      --task-focus:var(--color-border-focus); --task-ink:var(--color-text-primary);
      --task-body:var(--color-text-body); --task-sub:var(--color-text-secondary);
      --task-quiet:var(--color-text-muted); --task-action:var(--color-action-primary);
      --task-on-action:var(--color-text-on-action); --task-success:var(--color-state-success);
      --task-warning:var(--color-state-warning); --task-danger:var(--color-state-danger);
      --task-shadow-soft:var(--color-shadow-soft); --task-shadow-medium:var(--color-shadow-medium);
    }
    @media (prefers-color-scheme:dark) {
      :root {
        --color-bg-app:#1f1b16; --color-bg-paper:#2a251e;
        --color-bg-surface-solid:#332d25; --color-bg-overlay:rgba(0,0,0,.72);
        --color-bg-hover:rgba(255,255,255,.08); --color-bg-active:rgba(234,216,189,.16);
        --color-border-paper:#5a4d3d; --color-border-neutral:#4a4238;
        --color-border-focus:#f3eee6; --color-text-primary:#f3eee6;
        --color-text-body:#eee8df; --color-text-secondary:#c8bcae;
        --color-text-muted:#9f9283; --color-action-primary:#f3eee6;
        --color-text-on-action:#302820; --color-state-success:#7bcf8f;
        --color-state-warning:#f7c96a; --color-state-danger:#ff8a7f;
        --color-disabled-bg:#58504a; --color-shadow-soft:rgba(0,0,0,.32);
        --color-shadow-medium:rgba(0,0,0,.45);
      }
    }
    * { box-sizing:border-box; }
    html, body { height:100%; }
    body { margin:0; overflow:hidden; color:var(--task-body); background:var(--task-app); font-family:"Noto Sans SC",system-ui,sans-serif; }
    button, input, textarea, select { font:inherit; }
    button { color:inherit; }
    .font-hand { font-family:"Excalifont","Xiaolai","Noto Serif SC",serif; }
    .demo-page { min-height:100dvh; padding:32px; background:radial-gradient(circle at 20% 15%, var(--task-raised), var(--task-app) 55%); }
    .demo-note { width:min(540px,100%); margin:0 auto; padding-top:10vh; color:var(--task-sub); }
    .demo-note h1 { color:var(--task-ink); font-family:"Noto Serif SC",serif; font-size:30px; font-weight:500; }
    .backdrop { position:fixed; inset:0; z-index:20; display:grid; place-items:center; padding:24px; background:var(--task-overlay); }
    .task-editor {
      width:min(920px,calc(100vw - 48px)); max-height:calc(100dvh - 48px);
      display:flex; flex-direction:column; overflow:hidden; border:1px solid var(--task-line);
      border-radius:24px; background:var(--task-paper);
      box-shadow:0 12px 28px var(--task-shadow-soft),0 32px 72px var(--task-shadow-medium);
      animation:task-editor-in 200ms ease-out both;
    }
    .editor-header { min-height:72px; padding:14px 20px 14px 32px; border-bottom:1px solid var(--task-line-soft); }
    .editor-body { min-height:0; overflow-y:auto; overscroll-behavior:contain; scrollbar-gutter:stable; padding:28px 32px 36px; }
    .editor-inner { width:100%; max-width:760px; margin:0 auto; }
    .editor-footer { min-height:76px; padding:14px 24px; border-top:1px solid var(--task-line-soft); background:var(--task-paper); }
    .icon-button { width:44px; height:44px; display:inline-grid; place-items:center; border:0; border-radius:12px; background:transparent; color:var(--task-sub); }
    .icon-button:hover { color:var(--task-ink); background:var(--task-hover); }
    .focusable:focus-visible { outline:2px solid var(--task-focus); outline-offset:3px; }
    .prompt-field { width:100%; min-height:176px; resize:vertical; padding:18px 20px; border:1px solid var(--task-line); border-radius:16px; outline:0; background:var(--task-raised); color:var(--task-body); line-height:1.75; }
    .prompt-field:focus { border-color:var(--task-focus); box-shadow:0 0 0 3px var(--task-active); }
    .paper-group { border:1px solid var(--task-line); border-radius:16px; background:var(--task-raised); }
    .paper-row { width:100%; min-height:72px; padding:14px 18px; border:0; background:transparent; color:var(--task-ink); text-align:left; }
    .paper-row + .paper-row { border-top:1px solid var(--task-line-soft); }
    .paper-row:hover { background:var(--task-hover); }
    .paper-row:first-child { border-radius:15px 15px 0 0; }
    .paper-row:last-child { border-radius:0 0 15px 15px; }
    .paper-card { border:1px solid var(--task-line); border-radius:14px; background:var(--task-raised); }
    .paper-card:hover { border-color:var(--task-focus); }
    .menu-wrap { position:relative; }
    .menu {
      position:absolute; top:calc(100% + 8px); right:0; z-index:45; width:224px; max-height:320px;
      overflow-y:auto; padding:6px; border:1px solid var(--task-line); border-radius:16px;
      background:var(--task-raised); box-shadow:0 10px 24px var(--task-shadow-soft),0 24px 56px var(--task-shadow-medium);
      animation:menu-in 160ms ease-out both;
    }
    .menu.model-menu { width:min(360px,calc(100vw - 32px)); }
    .menu-item { width:100%; min-height:48px; padding:10px 12px; border:0; border-radius:11px; background:transparent; text-align:left; }
    .menu-item:hover, .menu-item:focus-visible { outline:0; background:var(--task-hover); }
    .menu-item[aria-checked="true"] { background:var(--task-active); color:var(--task-ink); }
    .menu-item:disabled { cursor:not-allowed; color:var(--task-quiet); }
    .advanced-trigger { width:100%; min-height:44px; border:0; background:transparent; text-align:left; }
    .advanced-chevron { transition:transform 180ms ease; }
    .advanced-trigger[aria-expanded="true"] .advanced-chevron { transform:rotate(180deg); }
    .advanced-content { display:grid; gap:12px; animation:fold-in 180ms ease-out both; }
    .switch { position:relative; width:48px; height:28px; flex:none; border:0; border-radius:999px; background:var(--task-line); transition:background 160ms ease; }
    .switch::after { content:""; position:absolute; top:3px; left:3px; width:22px; height:22px; border-radius:50%; background:var(--task-raised); box-shadow:0 1px 4px var(--task-shadow-medium); transition:transform 180ms cubic-bezier(.2,.8,.2,1); }
    .switch[aria-checked="true"] { background:var(--task-action); }
    .switch[aria-checked="true"]::after { transform:translateX(20px); }
    .primary-button, .secondary-button { min-height:44px; padding:0 18px; border-radius:12px; font-weight:600; }
    .primary-button { border:1px solid var(--task-action); background:var(--task-action); color:var(--task-on-action); }
    .primary-button:disabled { border-color:var(--color-disabled-bg); background:var(--color-disabled-bg); color:var(--task-quiet); cursor:not-allowed; }
    .secondary-button { border:1px solid var(--task-line); background:var(--task-raised); color:var(--task-ink); }
    .secondary-button:hover { background:var(--task-hover); }
    .feedback { display:flex; align-items:flex-start; gap:10px; margin-top:16px; padding:12px 14px; border:1px solid var(--task-line); border-radius:12px; background:var(--task-raised); font-size:13px; line-height:1.6; }
    .feedback[data-kind="error"] { border-color:var(--task-danger); }
    .feedback[data-kind="warning"] { border-color:var(--task-warning); }
    .feedback[data-kind="success"] { border-color:var(--task-success); }
    .spinner { width:14px; height:14px; display:inline-block; border:2px solid currentColor; border-right-color:transparent; border-radius:50%; animation:task-spin 700ms linear infinite; }
    .overlay-layer { position:fixed; inset:0; z-index:60; display:grid; place-items:center; padding:24px; background:rgba(39,31,24,.38); }
    .schedule-dialog { width:min(620px,calc(100vw - 48px)); max-height:calc(100dvh - 64px); display:flex; flex-direction:column; overflow:hidden; border:1px solid var(--task-line); border-radius:22px; background:var(--task-paper); box-shadow:0 24px 72px var(--task-shadow-medium); animation:task-editor-in 180ms ease-out both; }
    .schedule-head { min-height:68px; padding:12px 16px 12px 24px; border-bottom:1px solid var(--task-line-soft); }
    .schedule-body { min-height:0; overflow-y:auto; padding:22px 24px 28px; }
    .schedule-footer { min-height:72px; padding:12px 20px; border-top:1px solid var(--task-line-soft); background:var(--task-paper); }
    .field-label { display:block; margin-bottom:8px; color:var(--task-ink); font-size:13px; font-weight:600; }
    .field { width:100%; min-height:44px; padding:10px 12px; border:1px solid var(--task-line); border-radius:12px; outline:0; background:var(--task-raised); color:var(--task-body); }
    .field:focus { border-color:var(--task-focus); box-shadow:0 0 0 3px var(--task-active); }
    .rule-tabs { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:4px; padding:4px; border-radius:13px; background:var(--task-hover); }
    .rule-tab { min-height:38px; border:0; border-radius:10px; background:transparent; color:var(--task-sub); }
    .rule-tab[aria-selected="true"] { background:var(--task-raised); color:var(--task-ink); box-shadow:0 1px 4px var(--task-shadow-soft); }
    .weekday-grid { display:grid; grid-template-columns:repeat(7,minmax(0,1fr)); gap:6px; }
    .weekday { min-width:0; min-height:42px; border:1px solid var(--task-line); border-radius:10px; background:var(--task-raised); }
    .weekday[aria-pressed="true"] { border-color:var(--task-action); background:var(--task-action); color:var(--task-on-action); }
    .summary-note { padding:14px 16px; border-left:3px solid var(--task-action); border-radius:0 12px 12px 0; background:var(--task-hover); }
    .desktop-hide { display:none !important; }
    .mobile-sheet-head { display:none; }
    [hidden] { display:none !important; }
    @keyframes task-editor-in { from { opacity:0; transform:translateY(8px) scale(.995); } to { opacity:1; transform:none; } }
    @keyframes task-sheet-in { from { opacity:0; transform:translateY(16px); } to { opacity:1; transform:none; } }
    @keyframes menu-in { from { opacity:0; transform:translateY(-4px); } to { opacity:1; transform:none; } }
    @keyframes fold-in { from { opacity:0; transform:translateY(-4px); } to { opacity:1; transform:none; } }
    @keyframes task-spin { to { transform:rotate(360deg); } }
    @media (max-width:767px) {
      .backdrop { display:block; padding:0; }
      .task-editor { width:100%; height:100dvh; max-height:none; border:0; border-radius:0; animation:task-sheet-in 200ms ease-out both; }
      .editor-header { min-height:calc(60px + env(safe-area-inset-top)); padding:calc(8px + env(safe-area-inset-top)) 8px 8px 12px; }
      .editor-body { padding:20px 16px 32px; }
      .editor-footer { min-height:calc(72px + env(safe-area-inset-bottom)); padding:12px 16px calc(12px + env(safe-area-inset-bottom)); }
      .prompt-field { min-height:168px; resize:none; }
      .paper-row { min-height:68px; padding:13px 14px; }
      .menu {
        position:fixed; top:auto; right:0; bottom:0; left:0; z-index:70; width:100% !important; max-height:min(78dvh,560px);
        padding:8px 12px calc(12px + env(safe-area-inset-bottom)); border-width:1px 0 0;
        border-radius:24px 24px 0 0; animation:task-sheet-in 200ms ease-out both;
      }
      .menu::before { content:""; display:block; width:38px; height:4px; margin:2px auto 10px; border-radius:999px; background:var(--task-line); }
      .overlay-layer { align-items:end; padding:0; }
      .schedule-dialog { width:100%; max-height:92dvh; border-width:1px 0 0; border-radius:24px 24px 0 0; animation:task-sheet-in 220ms ease-out both; }
      .schedule-head { padding:12px 8px 12px 20px; }
      .schedule-body { padding:20px 16px 28px; }
      .schedule-footer { padding:12px 16px calc(12px + env(safe-area-inset-bottom)); }
      .weekday-grid { gap:4px; }
      .weekday { min-height:40px; font-size:13px; }
      .mobile-hide { display:none !important; }
      .desktop-hide { display:inline-grid !important; }
      .mobile-sheet-head { display:flex; min-height:52px; align-items:center; justify-content:space-between; padding:0 2px 4px 10px; }
    }
    @media (prefers-reduced-motion:reduce) {
      *, *::before, *::after { scroll-behavior:auto !important; animation-duration:.01ms !important; transition-duration:.01ms !important; }
    }
  </style>
</head>
<body>
  <main class="demo-page" aria-hidden="true">
    <div class="demo-note">
      <p class="text-xs tracking-widest uppercase">Ink & Memory</p>
      <h1>把重要的事，交给时间慢慢完成。</h1>
      <p class="mt-4 leading-7">背景只表示原 Chat / Calendar 上下文；任务编辑器打开后背景停止交互。</p>
    </div>
  </main>

  <div class="backdrop" id="editor-backdrop">
    <section class="task-editor" role="dialog" aria-modal="true" aria-labelledby="editor-title">
      <header class="editor-header flex-none flex items-center justify-between">
        <button class="icon-button focusable desktop-hide" type="button" aria-label="返回 Chat">
          <i class="fa-solid fa-arrow-left" aria-hidden="true"></i>
        </button>
        <h1 id="editor-title" class="font-hand text-2xl font-semibold" style="color:var(--task-ink)">编辑任务</h1>
        <button class="icon-button focusable" type="button" aria-label="关闭任务编辑器">
          <i class="fa-solid fa-xmark text-lg" aria-hidden="true"></i>
        </button>
      </header>

      <div class="editor-body flex-1">
        <div class="editor-inner">
          <label for="task-prompt" class="sr-only">任务说明</label>
          <textarea id="task-prompt" class="prompt-field" spellcheck="false">你是一个求职助手，整理 Boss 直聘投递与岗位市场分析。

每次开始前，先查看今天的日程安排，再继续未完成的岗位分析。</textarea>

          <section class="paper-group mt-6" aria-label="日程设置">
            <div class="menu-wrap">
              <button id="repeat-trigger" class="paper-row focusable flex items-center justify-between gap-4" type="button" aria-haspopup="menu" aria-expanded="true">
                <span class="font-medium">重复</span>
                <span class="min-w-0 flex items-center gap-3" style="color:var(--task-sub)">
                  <span id="repeat-value" class="truncate">工作日</span>
                  <i class="fa-solid fa-chevron-down text-xs" aria-hidden="true"></i>
                </span>
              </button>
              <div id="repeat-menu" class="menu" role="menu" aria-label="重复选项">
                <div class="mobile-sheet-head">
                  <strong class="font-hand text-lg" style="color:var(--task-ink)">重复</strong>
                  <button class="icon-button focusable" type="button" data-close-menu="repeat" aria-label="关闭重复选项"><i class="fa-solid fa-xmark" aria-hidden="true"></i></button>
                </div>
                <button class="menu-item focusable flex items-center justify-between" type="button" role="menuitemradio" aria-checked="false" data-repeat="每小时"><span>每小时</span><i class="fa-solid fa-check text-xs opacity-0" aria-hidden="true"></i></button>
                <button class="menu-item focusable flex items-center justify-between" type="button" role="menuitemradio" aria-checked="false" data-repeat="每天"><span>每天</span><i class="fa-solid fa-check text-xs opacity-0" aria-hidden="true"></i></button>
                <button class="menu-item focusable flex items-center justify-between" type="button" role="menuitemradio" aria-checked="true" data-repeat="工作日"><span>工作日</span><i class="fa-solid fa-check text-xs" aria-hidden="true"></i></button>
                <button class="menu-item focusable flex items-center justify-between" type="button" role="menuitemradio" aria-checked="false" data-repeat="每周"><span>每周</span><i class="fa-solid fa-check text-xs opacity-0" aria-hidden="true"></i></button>
                <button class="menu-item focusable flex items-center justify-between" type="button" role="menuitemradio" aria-checked="false" data-repeat="自定义"><span>自定义</span><i class="fa-solid fa-check text-xs opacity-0" aria-hidden="true"></i></button>
              </div>
            </div>

            <button id="schedule-trigger" class="paper-row focusable flex items-center justify-between gap-5" type="button" aria-haspopup="dialog">
              <span class="min-w-0">
                <span class="block font-medium">高级日程</span>
                <span id="schedule-summary" class="block mt-1 text-xs leading-5" style="color:var(--task-sub)">周一至周五 · 09:00 · Asia/Shanghai</span>
              </span>
              <span class="flex-none text-sm font-medium" style="color:var(--task-sub)">编辑规则</span>
            </button>
          </section>

          <section class="mt-6" aria-labelledby="advanced-label">
            <button id="advanced-trigger" class="advanced-trigger focusable flex items-center gap-2" type="button" aria-expanded="true" aria-controls="advanced-content">
              <span id="advanced-label" class="font-hand text-lg font-semibold" style="color:var(--task-ink)">高级</span>
              <i class="advanced-chevron fa-solid fa-chevron-down text-xs" style="color:var(--task-sub)" aria-hidden="true"></i>
            </button>

            <div id="advanced-content" class="advanced-content mt-3">
              <div class="paper-card min-h-full px-4 py-4 flex items-center justify-between gap-5">
                <div class="min-w-0">
                  <p class="m-0 text-sm font-medium" style="color:var(--task-ink)">每次运行时都开启新聊天</p>
                  <p id="thread-mode-help" class="m-0 mt-1 text-xs leading-5" style="color:var(--task-sub)">在创建此任务的聊天中继续运行</p>
                </div>
                <button id="thread-switch" class="switch focusable" type="button" role="switch" aria-checked="false" aria-label="每次运行时都开启新聊天" aria-describedby="thread-mode-help"></button>
              </div>

              <div id="model-field" class="paper-card menu-wrap">
                <button id="model-trigger" class="focusable w-full min-h-full px-4 py-4 border-0 bg-transparent flex items-center justify-between gap-5 text-left" type="button" aria-haspopup="menu" aria-expanded="false">
                  <span class="min-w-0">
                    <span class="block text-sm font-medium" style="color:var(--task-ink)">模型</span>
                    <span id="model-status" class="block mt-1 text-xs leading-5" style="color:var(--task-sub)">gpt-5.6-sol</span>
                  </span>
                  <span class="min-w-0 flex items-center gap-3">
                    <span id="model-value" class="truncate text-sm" style="max-width:240px;color:var(--task-sub)">GPT-5.6 Sol</span>
                    <span id="model-spinner" class="spinner" aria-label="正在更新模型目录" hidden></span>
                    <i id="model-chevron" class="fa-solid fa-chevron-down text-xs" style="color:var(--task-sub)" aria-hidden="true"></i>
                  </span>
                </button>
                <div id="model-menu" class="menu model-menu" role="menu" aria-label="选择模型" hidden>
                  <div class="mobile-sheet-head">
                    <strong class="font-hand text-lg" style="color:var(--task-ink)">模型</strong>
                    <button class="icon-button focusable" type="button" data-close-menu="model" aria-label="关闭模型选择"><i class="fa-solid fa-xmark" aria-hidden="true"></i></button>
                  </div>
                  <button class="menu-item focusable flex items-center justify-between gap-4" type="button" role="menuitemradio" aria-checked="true" data-model="GPT-5.6 Sol" data-alias="gpt-5.6-sol">
                    <span><strong class="block text-sm font-medium">GPT-5.6 Sol</strong><small class="block mt-1" style="color:var(--task-sub)">gpt-5.6-sol</small></span><i class="fa-solid fa-check text-xs" aria-hidden="true"></i>
                  </button>
                  <button class="menu-item focusable flex items-center justify-between gap-4" type="button" role="menuitemradio" aria-checked="false" data-model="GPT-6.1 Sol" data-alias="gpt-6.1-sol">
                    <span><strong class="block text-sm font-medium">GPT-6.1 Sol</strong><small class="block mt-1" style="color:var(--task-sub)">gpt-6.1-sol</small></span><i class="fa-solid fa-check text-xs opacity-0" aria-hidden="true"></i>
                  </button>
                  <button class="menu-item focusable flex items-center justify-between gap-4" type="button" role="menuitemradio" aria-checked="false" data-model="GPT-6 Astra" data-alias="gpt-6-astra">
                    <span><strong class="block text-sm font-medium">GPT-6 Astra</strong><small class="block mt-1" style="color:var(--task-sub)">gpt-6-astra</small></span><i class="fa-solid fa-check text-xs opacity-0" aria-hidden="true"></i>
                  </button>
                  <button id="unavailable-model" class="menu-item flex items-center justify-between gap-4" type="button" role="menuitemradio" aria-checked="false" disabled hidden>
                    <span><strong class="block text-sm font-medium">原模型</strong><small class="block mt-1" style="color:var(--task-danger)">legacy-model · 不可用</small></span><span class="text-xs">不可选</span>
                  </button>
                </div>
              </div>
            </div>
          </section>

          <div id="editor-feedback" class="feedback" role="status" hidden></div>
        </div>
      </div>

      <footer class="editor-footer flex-none flex items-center justify-end gap-3">
        <button class="secondary-button focusable mr-auto" type="button">暂停</button>
        <button class="secondary-button focusable mobile-hide" type="button">取消</button>
        <button id="save-button" class="primary-button focusable" type="button"><span>保存</span></button>
      </footer>
    </section>
  </div>

  <div id="schedule-layer" class="overlay-layer" hidden>
    <section class="schedule-dialog" role="dialog" aria-modal="true" aria-labelledby="schedule-title">
      <header class="schedule-head flex-none flex items-center justify-between">
        <div>
          <h2 id="schedule-title" class="font-hand m-0 text-xl font-semibold" style="color:var(--task-ink)">高级日程</h2>
          <p class="m-0 mt-1 text-xs" style="color:var(--task-sub)">调整任务草稿中的运行规则</p>
        </div>
        <button id="schedule-close" class="icon-button focusable" type="button" aria-label="关闭高级日程"><i class="fa-solid fa-xmark" aria-hidden="true"></i></button>
      </header>

      <div class="schedule-body flex-1">
        <fieldset>
          <legend class="field-label">规则类型</legend>
          <div class="rule-tabs" role="tablist" aria-label="规则类型">
            <button class="rule-tab focusable" type="button" role="tab" aria-selected="false" data-rule="once">一次</button>
            <button class="rule-tab focusable" type="button" role="tab" aria-selected="false" data-rule="interval">间隔</button>
            <button class="rule-tab focusable" type="button" role="tab" aria-selected="false" data-rule="daily">每天</button>
            <button class="rule-tab focusable" type="button" role="tab" aria-selected="true" data-rule="weekly">每周</button>
          </div>
        </fieldset>

        <div id="rule-once" class="mt-5" hidden>
          <label class="field-label" for="once-date">运行日期</label>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <input id="once-date" class="field" type="date" value="2026-10-08" />
            <input class="field" type="time" value="09:00" aria-label="运行时间" />
          </div>
        </div>
        <div id="rule-interval" class="mt-5" hidden>
          <label class="field-label" for="interval-value">运行间隔</label>
          <div class="grid grid-cols-2 gap-3">
            <input id="interval-value" class="field" type="number" min="1" step="1" value="2" inputmode="numeric" />
            <select class="field" aria-label="间隔单位"><option>分钟</option><option selected>小时</option><option>天</option><option>周</option></select>
          </div>
        </div>
        <div id="rule-daily" class="mt-5" hidden>
          <label class="field-label" for="daily-time">本地时间</label>
          <input id="daily-time" class="field" type="time" value="09:00" />
        </div>
        <div id="rule-weekly" class="mt-5">
          <span class="field-label">运行星期</span>
          <div class="weekday-grid" aria-label="选择运行星期">
            <button class="weekday focusable" type="button" aria-pressed="true">一</button><button class="weekday focusable" type="button" aria-pressed="true">二</button><button class="weekday focusable" type="button" aria-pressed="true">三</button><button class="weekday focusable" type="button" aria-pressed="true">四</button><button class="weekday focusable" type="button" aria-pressed="true">五</button><button class="weekday focusable" type="button" aria-pressed="false">六</button><button class="weekday focusable" type="button" aria-pressed="false">日</button>
          </div>
          <label class="field-label mt-4" for="weekly-time">本地时间</label>
          <input id="weekly-time" class="field" type="time" value="09:00" />
        </div>

        <div class="mt-5">
          <label class="field-label" for="timezone">时区</label>
          <select id="timezone" class="field"><option selected>Asia/Shanghai</option><option>Asia/Tokyo</option><option>America/Los_Angeles</option></select>
        </div>

        <div class="summary-note mt-5" aria-live="polite">
          <p id="rule-summary" class="m-0 text-sm font-medium" style="color:var(--task-ink)">周一至周五 · 09:00 · Asia/Shanghai</p>
          <p class="m-0 mt-1 text-xs leading-5" style="color:var(--task-sub)">下次运行：2026年10月8日 09:00（由服务端返回）</p>
        </div>
      </div>

      <footer class="schedule-footer flex-none flex items-center justify-end gap-3">
        <button id="schedule-cancel" class="secondary-button focusable" type="button">取消</button>
        <button id="schedule-apply" class="primary-button focusable" type="button">应用到任务草稿</button>
      </footer>
    </section>
  </div>

  <script>
    const $ = (selector) => document.querySelector(selector);
    const $$ = (selector) => [...document.querySelectorAll(selector)];
    const setHidden = (node, hidden) => { node.hidden = hidden; };

    function closeMenus(except) {
      [$('#repeat-menu'), $('#model-menu')].forEach(menu => {
        if (menu !== except) menu.hidden = true;
      });
      $('#repeat-trigger').setAttribute('aria-expanded', String(!$('#repeat-menu').hidden));
      $('#model-trigger').setAttribute('aria-expanded', String(!$('#model-menu').hidden));
    }

    $('#repeat-trigger').addEventListener('click', () => {
      const menu = $('#repeat-menu');
      const next = !menu.hidden;
      closeMenus(menu);
      menu.hidden = next;
      $('#repeat-trigger').setAttribute('aria-expanded', String(!next));
    });

    $$('#repeat-menu [data-repeat]').forEach(item => item.addEventListener('click', () => {
      const value = item.dataset.repeat;
      $('#repeat-value').textContent = value;
      $$('#repeat-menu [data-repeat]').forEach(option => {
        const selected = option === item;
        option.setAttribute('aria-checked', String(selected));
        option.querySelector('i').classList.toggle('opacity-0', !selected);
      });
      $('#repeat-menu').hidden = true;
      $('#repeat-trigger').setAttribute('aria-expanded', 'false');
      if (value === '每小时') $('#schedule-summary').textContent = '每 60 分钟 · 下次运行由服务端计算';
      if (value === '每天') $('#schedule-summary').textContent = '每天 · 09:00 · Asia/Shanghai';
      if (value === '工作日') $('#schedule-summary').textContent = '周一至周五 · 09:00 · Asia/Shanghai';
      if (value === '每周') $('#schedule-summary').textContent = '每周一 · 09:00 · Asia/Shanghai';
      if (value === '自定义') openSchedule(); else $('#repeat-trigger').focus();
    }));
    $$('[data-close-menu]').forEach(button => button.addEventListener('click', () => {
      const kind = button.dataset.closeMenu;
      const menu = kind === 'repeat' ? $('#repeat-menu') : $('#model-menu');
      const trigger = kind === 'repeat' ? $('#repeat-trigger') : $('#model-trigger');
      menu.hidden = true;
      trigger.setAttribute('aria-expanded', 'false');
      trigger.focus();
    }));

    $('#advanced-trigger').addEventListener('click', () => {
      const trigger = $('#advanced-trigger');
      const expanded = trigger.getAttribute('aria-expanded') === 'true';
      trigger.setAttribute('aria-expanded', String(!expanded));
      $('#advanced-content').hidden = expanded;
    });

    $('#thread-switch').addEventListener('click', () => {
      const control = $('#thread-switch');
      const next = control.getAttribute('aria-checked') !== 'true';
      control.setAttribute('aria-checked', String(next));
      $('#thread-mode-help').textContent = next ? '每次运行都会创建独立聊天' : '在创建此任务的聊天中继续运行';
    });

    let catalogState = 'ready';
    $('#model-trigger').addEventListener('click', () => {
      if (catalogState === 'loading') return;
      if (catalogState === 'error') { previewModelCatalog('loading'); setTimeout(() => previewModelCatalog('ready'), 700); return; }
      const menu = $('#model-menu');
      const next = !menu.hidden;
      closeMenus(menu);
      menu.hidden = next;
      $('#model-trigger').setAttribute('aria-expanded', String(!next));
    });

    $$('#model-menu [data-model]').forEach(item => item.addEventListener('click', () => {
      $('#model-value').textContent = item.dataset.model;
      $('#model-status').textContent = item.dataset.alias;
      $$('#model-menu [data-model]').forEach(option => {
        const selected = option === item;
        option.setAttribute('aria-checked', String(selected));
        option.querySelector('i').classList.toggle('opacity-0', !selected);
      });
      $('#model-menu').hidden = true;
      $('#model-trigger').setAttribute('aria-expanded', 'false');
      $('#model-trigger').focus();
    }));

    window.previewModelCatalog = function(state) {
      catalogState = state;
      const spinner = $('#model-spinner');
      const chevron = $('#model-chevron');
      const unavailable = $('#unavailable-model');
      const field = $('#model-field');
      spinner.hidden = state !== 'loading';
      chevron.hidden = state === 'loading' || state === 'error';
      unavailable.hidden = state !== 'unavailable';
      field.style.borderColor = state === 'error' || state === 'unavailable' ? 'var(--task-danger)' : 'var(--task-line)';
      if (state === 'loading') $('#model-status').textContent = '正在更新可用模型';
      if (state === 'ready') $('#model-status').textContent = 'gpt-5.6-sol';
      if (state === 'error') $('#model-status').textContent = '模型目录暂不可用 · 点击重试';
      if (state === 'unavailable') { $('#model-value').textContent = '原模型'; $('#model-status').textContent = 'legacy-model · 不可用，请选择其他模型'; }
    };

    function openSchedule() { closeMenus(); $('#schedule-layer').hidden = false; setTimeout(() => $('#schedule-close').focus(), 0); }
    function closeSchedule() { $('#schedule-layer').hidden = true; $('#schedule-trigger').focus(); }
    $('#schedule-trigger').addEventListener('click', openSchedule);
    $('#schedule-close').addEventListener('click', closeSchedule);
    $('#schedule-cancel').addEventListener('click', closeSchedule);

    $$('.rule-tab').forEach(tab => tab.addEventListener('click', () => {
      $$('.rule-tab').forEach(item => item.setAttribute('aria-selected', String(item === tab)));
      ['once','interval','daily','weekly'].forEach(rule => { $('#rule-' + rule).hidden = rule !== tab.dataset.rule; });
      const summaries = { once:'2026年10月8日 09:00 · Asia/Shanghai', interval:'每 2 小时 · 首次运行由服务端计算', daily:'每天 09:00 · Asia/Shanghai', weekly:'周一至周五 · 09:00 · Asia/Shanghai' };
      $('#rule-summary').textContent = summaries[tab.dataset.rule];
    }));

    $$('.weekday').forEach(day => day.addEventListener('click', () => day.setAttribute('aria-pressed', String(day.getAttribute('aria-pressed') !== 'true'))));
    $('#schedule-apply').addEventListener('click', () => {
      const summary = $('#rule-summary').textContent;
      $('#schedule-summary').textContent = summary;
      const selectedRule = $('.rule-tab[aria-selected="true"]').dataset.rule;
      const selectedDays = $$('.weekday[aria-pressed="true"]').map(day => day.textContent.trim()).join('');
      const weeklyLabel = selectedDays === '一二三四五' ? '工作日' : selectedDays.length === 1 ? '每周' : '自定义';
      $('#repeat-value').textContent = selectedRule === 'daily' ? '每天' : selectedRule === 'weekly' ? weeklyLabel : '自定义';
      closeSchedule();
    });

    const feedback = $('#editor-feedback');
    window.previewSave = function(state) {
      const button = $('#save-button');
      feedback.hidden = true;
      button.disabled = state === 'saving';
      if (state === 'saving') button.innerHTML = '<span class="spinner mr-2" aria-hidden="true"></span><span>保存中</span>';
      if (state === 'saved') { button.innerHTML = '<i class="fa-solid fa-check mr-2" aria-hidden="true"></i><span>已保存</span>'; feedback.dataset.kind='success'; feedback.innerHTML='<i class="fa-regular fa-circle-check mt-1" aria-hidden="true"></i><span>任务设置已更新，后续触发将使用新的 revision。</span>'; feedback.hidden=false; }
      if (state === 'error') { button.innerHTML='<span>重试保存</span>'; feedback.dataset.kind='error'; feedback.innerHTML='<i class="fa-solid fa-circle-exclamation mt-1" aria-hidden="true"></i><span><strong>保存失败。</strong> 当前任务仍使用原设置，你的修改已保留。</span>'; feedback.hidden=false; }
      if (state === 'conflict') { button.innerHTML='<span>重新检查并保存</span>'; feedback.dataset.kind='warning'; feedback.innerHTML='<i class="fa-solid fa-triangle-exclamation mt-1" aria-hidden="true"></i><span><strong>任务已在其他位置更新。</strong> 重复与模型存在差异，请查看最新设置后再次保存。</span>'; feedback.hidden=false; }
    };
    $('#save-button').addEventListener('click', () => { previewSave('saving'); setTimeout(() => previewSave('saved'), 850); });

    document.addEventListener('keydown', event => {
      if (event.key !== 'Escape') return;
      if (!$('#schedule-layer').hidden) return closeSchedule();
      if (!$('#repeat-menu').hidden) { $('#repeat-menu').hidden=true; $('#repeat-trigger').focus(); }
      if (!$('#model-menu').hidden) { $('#model-menu').hidden=true; $('#model-trigger').focus(); }
    });
  </script>
</body>
</html>
```

## 8. 实现映射与状态边界

- `CalendarPopup` / shared `Modal` 提供现有弹窗、焦点和主题 token；本参考不要求复制一套 Modal。
- `ScheduleSummaryCard` 只投影 desired。保存后的 effective 必须由 Admin 完整回执替换，不能本地拼字段。
- “每小时”投影现有 `interval_minutes=60`；“工作日 / 每周 / 自定义星期”仍依赖正式设计中标记为建议、未实现的 `weekly` capability。本视觉稿不暗示 capability 已交付。
- 模型项来自现有 `fetchGatewayModels()` / `/api/gateway/models` 的可调用目录；示例 modelAlias 仅作占位。
- 新聊天 switch 只编辑 `run_thread_mode`；来源 Thread 身份由服务端捕获，页面不允许输入或改写 `source_thread_id`。
- `loading_catalog`、目录错误和保存状态必须局部更新，保持 prompt、schedule 和其他 desired 可见。
- 二级高级日程的“应用”只回到主表单；主弹窗“保存”才提交 expected revision。

## 9. 视觉验收清单

- [ ] 桌面主弹窗标题与底部动作固定，正文是唯一页面级滚动区。
- [ ] 窄屏为全高 sheet，重复、模型与高级日程使用 bottom sheet，底部安全区不遮挡动作。
- [ ] 重复菜单严格显示“每小时、每天、工作日、每周、自定义”，当前项有文字之外的勾选状态。
- [ ] 高级日程覆盖一次、间隔、每天、每周的条件字段、IANA 时区、摘要和服务端 next run。
- [ ] 高级折叠只含新聊天和模型，收起再展开后值保持。
- [ ] 新建任务的新聊天 switch 默认关闭，说明清楚“在创建此任务的聊天中继续运行”。
- [ ] 模型行覆盖 loading、ready、empty/error、旧 alias 不可用和重试，不清空 effective 旧值。
- [ ] 保存覆盖 idle、editing、saving、saved、revision conflict 和失败；按钮宽度不因 spinner 抖动。
- [ ] 纸面、墨色、手写标题、细线和阴影使用现有 Ink & Memory token；红色截图标注不出现。
- [ ] 键盘可完成菜单、switch、规则编辑、保存和关闭；焦点返回及 reduced motion 有定义。
