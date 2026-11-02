<!-- [Input] 当前tokens.css声明块、主题模块和现行页面用色规则。 -->
<!-- [Output] 暗色主题的当前色值、适用范围与测量缺口。 -->
<!-- [Pos] color_system现行设计；历史原文保存在history。 -->
<!-- [Sync] 2026-11-02: 按实际声明逐字段同步色值，区分暗色声明与系统媒体规则；应用代码保持。 -->

# Dark Theme 暗色主题设计稿

## 1. 视觉语言

暗色使用深暖棕纸面、暖白正文和低面积强调。当前[Web Token](../../../frontend/app/_dream/styles/tokens.css)同时维护`[data-theme='dark']`声明块与后置系统暗色媒体块；[Native投影](../../../frontend/src/components/inkColors.ts)分别维护dark与systemDark。

Web的`:root:not([data-theme='light'])`媒体选择器在系统暗色条件下匹配system及显式dark。表中两组值分别记录声明来源，实际Web颜色依据CSS层叠计算。Native显式dark选择dark，system按系统外观选择systemDark。此处为源码核对，页面跨组合测量继续待验证。

## 2. 品牌基础色板（暗色）

以下为暗色声明块取样。系统媒体块的差异在完整表中列出。

| 用途 | Token | 当前值 |
| --- | --- | --- |
| 应用画布 | `--color-bg-app` | `#1d1916` |
| 阅读与编辑纸面 | `--color-bg-paper` | `#2a241f` |
| 不透明浮层 | `--color-bg-surface-solid` | `#342d27` |
| 主文本 | `--color-text-primary` | `#f3e8d8` |
| 正文 | `--color-text-body` | `#eee8df` |
| 辅助文本 | `--color-text-secondary` | `#c8bcae` |
| 主操作背景 | `--color-action-primary` | `#f3e8d8` |
| 纸面边界 | `--color-border-paper` | `#5a4d3d` |

## 3. 语义 Token 完整列表（暗色值）

| CSS变量 | 暗色声明块 | 系统暗色媒体块 | 用途 |
| --- | --- | --- | --- |
| `--color-bg-app` | `#1d1916` | `#1f1b16` | 应用画布 |
| `--color-bg-paper` | `#2a241f` | `#2a251e` | 阅读与编辑纸面 |
| `--color-bg-surface` | `rgba(42, 37, 33, 0.82)` | `rgba(42, 37, 30, 0.82)` | 半透明承载面 |
| `--color-bg-surface-solid` | `#342d27` | `#332d25` | 不透明浮层 |
| `--color-bg-overlay` | `rgba(0, 0, 0, 0.72)` | `rgba(0, 0, 0, 0.72)` | 遮罩 |
| `--color-bg-hover` | `rgba(255, 255, 255, 0.08)` | `rgba(255, 255, 255, 0.08)` | 悬停或按下叠层 |
| `--color-bg-active` | `rgba(234, 216, 189, 0.16)` | `rgba(129, 183, 210, 0.18)` | 激活状态叠层 |
| `--color-bg-active-hover` | `rgba(234, 216, 189, 0.24)` | `rgba(129, 183, 210, 0.30)` | 激活状态悬停叠层 |
| `--color-border-paper` | `#5a4d3d` | `#5a4d3d` | 纸面边界 |
| `--color-border-neutral` | `#4a4238` | `#4a4238` | 控件分隔 |
| `--color-border-focus` | `#ead8bd` | `#f3eee6` | 聚焦边界 |
| `--color-text-primary` | `#f3e8d8` | `#f3eee6` | 主文本 |
| `--color-text-body` | `#eee8df` | `#eee8df` | 正文 |
| `--color-text-secondary` | `#c8bcae` | `#c8bcae` | 辅助文本 |
| `--color-text-muted` | `#9f9283` | `#9f9283` | 弱信息文字 |
| `--color-action-primary` | `#f3e8d8` | `#f3eee6` | 主操作背景 |
| `--color-action-link` | `#81b7d2` | `#81b7d2` | 链接操作 |
| `--color-action-link-hover` | `#6aa3bf` | `#6aa3bf` | 链接悬停 |
| `--color-state-success` | `#7bcf8f` | `#7bcf8f` | 成功反馈 |
| `--color-state-success-hover` | `#64bd78` | `#5abd72` | 成功状态悬停 |
| `--color-state-warning` | `#f7c96a` | `#f7c96a` | 警示反馈 |
| `--color-state-error` | `#ff7a70` | `#ff7a70` | 失败反馈 |
| `--color-state-danger` | `#ff8a7f` | `#ff8a7f` | 危险操作 |
| `--color-state-danger-hover` | `#e06060` | `#e06060` | 危险操作悬停 |
| `--color-disabled-bg` | `#58504a` | `#58504a` | 禁用背景 |
| `--color-shadow-soft` | `rgba(0, 0, 0, 0.32)` | `rgba(0, 0, 0, 0.32)` | 轻阴影 |
| `--color-shadow-medium` | `rgba(0, 0, 0, 0.45)` | `rgba(0, 0, 0, 0.45)` | 浮层阴影 |
| `--color-scrollbar-thumb` | `#4a4238` | `#4a4238` | 滚动条滑块 |
| `--color-scrollbar-thumb-hover` | `#6a5e52` | `#6a5e52` | 滑块悬停 |
| `--color-voice-blue` | `#81b7d2` | `#81b7d2` | 蓝色声部点缀 |
| `--color-voice-purple` | `#c99be1` | `#c99be1` | 紫色声部点缀 |
| `--color-voice-pink` | `#ff8fbd` | `#ff8fbd` | 粉色声部点缀 |
| `--color-voice-green` | `#7bdba0` | `#7bdba0` | 绿色声部点缀 |
| `--color-voice-yellow` | `#f7c96a` | `#f7c96a` | 黄色声部点缀 |
| `--color-text-on-action` | `#ffffff` | `#ffffff` | 操作文字取值，按具体背景测量 |
| `--color-export-action-bg` | `#6b5a45` | `#6b5a45` | 导出长图操作背景 |
| `--color-export-action-text` | `#ffffff` | `#ffffff` | 导出长图操作文字 |
| `--color-code-bg` | `#0d1117` | `#0d1117` | 代码块背景 |
| `--color-code-text` | `#e6edf3` | `#e6edf3` | 代码块文字 |
| `--color-code-inline-bg` | `rgba(0, 0, 0, 0.18)` | `rgba(0, 0, 0, 0.18)` | 行内代码背景 |

## 4. 高亮色（暗色）

当前App.css中的五个voice-highlight类包含固定SVG笔刷填色。修订前原文中的color.highlight.*及rgba建议保存于历史稿，当前全局Token表依据实际注册变量列出。暗色笔刷与正文配对列为待测项目。

## 5. 组件级衍生变量（暗色效果）

稿纸页边线从state-error以24%透明混合派生；横线从border-paper以58%透明混合派生。实际显示随有效主题和背景变化，移动写作横线继续按实际行框绘制。

## 6. 亮色 → 暗色映射关系

| 用途 | 亮色 | 暗色声明块 | 系统暗色媒体块 |
| --- | --- | --- | --- |
| 应用画布 | `#f6efe5` | `#1d1916` | `#1f1b16` |
| 阅读与编辑纸面 | `#fffaf2` | `#2a241f` | `#2a251e` |
| 不透明浮层 | `#fffdf8` | `#342d27` | `#332d25` |
| 主文本 | `#3f3429` | `#f3e8d8` | `#f3eee6` |
| 主操作背景 | `#5f4a36` | `#f3e8d8` | `#f3eee6` |
| 聚焦边界 | `#5f4a36` | `#ead8bd` | `#f3eee6` |
| 成功状态悬停 | `#6f835c` | `#64bd78` | `#5abd72` |

## 7. 使用规则（暗色补充）

- 背景、纸面和浮层的层级通过对应Token表达；正文与状态使用实际前景和背景配对。
- Settings连接器与Deck沿其轻纸面规则，更多页沿现行卡片规则。
- 当前text-on-action值为白色；该值配暗色声明块action-primary时取样1.21:1。AnalysisView.native的primary Action采用此配对，后续需要单独评估。
- 配色建议、测量结果与应用采用状态分别维护，完整说明见[UI规范](../mobile-app/ui-guidelines/README.md)。

## 8. 浮层 / Popover / Dropdown 暗色配色

下表取暗色声明块。系统暗色实际值查第3节的媒体列。

| 用途 | Token | 当前值 |
| --- | --- | --- |
| 不透明浮层 | `--color-bg-surface-solid` | `#342d27` |
| 控件分隔 | `--color-border-neutral` | `#4a4238` |
| 浮层阴影 | `--color-shadow-medium` | `rgba(0, 0, 0, 0.45)` |
| 悬停或按下叠层 | `--color-bg-hover` | `rgba(255, 255, 255, 0.08)` |
| 激活状态叠层 | `--color-bg-active` | `rgba(234, 216, 189, 0.16)` |
| 正文 | `--color-text-body` | `#eee8df` |
| 辅助文本 | `--color-text-secondary` | `#c8bcae` |

## 历史与维护

[修订前原文](history/dark-theme-before-ui-guidelines-20261102.md)完整保留早期颜色、对照表和建议。本次按来源同步文档，CSS和Native颜色保持。
