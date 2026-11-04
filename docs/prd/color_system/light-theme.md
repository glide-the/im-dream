<!-- [Input] 当前tokens.css声明块、主题模块和现行页面用色规则。 -->
<!-- [Output] 亮色主题的当前色值、适用范围与测量缺口。 -->
<!-- [Pos] color_system现行设计；历史原文保存在history。 -->
<!-- [Sync] 2026-11-02: 按实际声明逐字段同步色值，区分暗色声明与系统媒体规则；应用代码保持。 -->

# Light Theme 亮色主题设计稿

## 1. 视觉语言

暖纸张、手写笔记本与安静工具台构成亮色视觉语言。当前来源为[Web Token](../../../frontend/app/_dream/styles/tokens.css)的`:root`声明块；Native投影归[inkColors](../../../frontend/src/components/inkColors.ts)。用户模式缺省为system；无系统暗色偏好时使用亮色，显式light使用亮色。

## 2. 品牌基础色板（亮色）

| 用途 | Token | 当前值 |
| --- | --- | --- |
| 应用画布 | `--color-bg-app` | `#f6efe5` |
| 阅读与编辑纸面 | `--color-bg-paper` | `#fffaf2` |
| 不透明浮层 | `--color-bg-surface-solid` | `#fffdf8` |
| 主文本 | `--color-text-primary` | `#3f3429` |
| 正文 | `--color-text-body` | `#4b3f33` |
| 辅助文本 | `--color-text-secondary` | `#7a6a59` |
| 主操作背景 | `--color-action-primary` | `#5f4a36` |
| 纸面边界 | `--color-border-paper` | `#d8c7b3` |

## 3. 语义 Token 完整列表（亮色值）

数值逐字段取自当前`:root`声明。透明色的最终呈现需要结合实际背景计算。

| CSS变量 | 亮色值 | 用途 |
| --- | --- | --- |
| `--color-bg-app` | `#f6efe5` | 应用画布 |
| `--color-bg-paper` | `#fffaf2` | 阅读与编辑纸面 |
| `--color-bg-surface` | `rgba(255, 250, 242, 0.9)` | 半透明承载面 |
| `--color-bg-surface-solid` | `#fffdf8` | 不透明浮层 |
| `--color-bg-overlay` | `rgba(39, 31, 24, 0.5)` | 遮罩 |
| `--color-bg-hover` | `rgba(95, 74, 54, 0.06)` | 悬停或按下叠层 |
| `--color-bg-active` | `rgba(95, 74, 54, 0.12)` | 激活状态叠层 |
| `--color-bg-active-hover` | `rgba(95, 74, 54, 0.18)` | 激活状态悬停叠层 |
| `--color-border-paper` | `#d8c7b3` | 纸面边界 |
| `--color-border-neutral` | `#e6ddd0` | 控件分隔 |
| `--color-border-focus` | `#5f4a36` | 聚焦边界 |
| `--color-text-primary` | `#3f3429` | 主文本 |
| `--color-text-body` | `#4b3f33` | 正文 |
| `--color-text-secondary` | `#7a6a59` | 辅助文本 |
| `--color-text-muted` | `#9a8a78` | 弱信息文字 |
| `--color-action-primary` | `#5f4a36` | 主操作背景 |
| `--color-action-link` | `#4a90e2` | 链接操作 |
| `--color-action-link-hover` | `#357abd` | 链接悬停 |
| `--color-state-success` | `#7e9468` | 成功反馈 |
| `--color-state-success-hover` | `#6f835c` | 成功状态悬停 |
| `--color-state-warning` | `#c78855` | 警示反馈 |
| `--color-state-error` | `#a86652` | 失败反馈 |
| `--color-state-danger` | `#b35f50` | 危险操作 |
| `--color-state-danger-hover` | `#9f4f42` | 危险操作悬停 |
| `--color-disabled-bg` | `#d6cbbb` | 禁用背景 |
| `--color-shadow-soft` | `rgba(91, 69, 44, 0.08)` | 轻阴影 |
| `--color-shadow-medium` | `rgba(91, 69, 44, 0.16)` | 浮层阴影 |
| `--color-scrollbar-thumb` | `#cab7a4` | 滚动条滑块 |
| `--color-scrollbar-thumb-hover` | `#b29d88` | 滑块悬停 |
| `--color-voice-blue` | `#4a90e2` | 蓝色声部点缀 |
| `--color-voice-purple` | `#9b59b6` | 紫色声部点缀 |
| `--color-voice-pink` | `#e91e63` | 粉色声部点缀 |
| `--color-voice-green` | `#27ae60` | 绿色声部点缀 |
| `--color-voice-yellow` | `#f39c12` | 黄色声部点缀 |
| `--color-text-on-action` | `#ffffff` | 操作文字取值，按具体背景测量 |
| `--color-export-action-bg` | `#5f4a36` | 导出长图操作背景 |
| `--color-export-action-text` | `#ffffff` | 导出长图操作文字 |
| `--color-code-bg` | `#2c2c2c` | 代码块背景 |
| `--color-code-text` | `#f3eee6` | 代码块文字 |
| `--color-code-inline-bg` | `rgba(0, 0, 0, 0.08)` | 行内代码背景 |

## 4. 高亮色（亮色）

[App.css](../../../frontend/app/_dream/App.css)中的voice-highlight类通过SVG背景定义黄色、蓝色、粉色、绿色和紫色笔刷。其固定fill与全局语义Token分别维护，暗色可读性需要按实际页面测量。

## 5. 组件级衍生变量（亮色）

| 变量 | 当前派生 | 适用对象 |
| --- | --- | --- |
| `--notebook-margin-line` | `color-mix(in srgb, var(--color-state-error) 24%, transparent)` | 原稿纸页边线 |
| `--notebook-rule-line` | `color-mix(in srgb, var(--color-border-paper) 58%, transparent)` | 原稿纸横线 |

移动写作的横线与实际行框对齐，桌面稿纸保留原规则，详见[写作设计](../../design/multi-platform/writing-mobile-layout.md)。

## 6. 使用规则

- 页面画布、纸面、正文和状态依据语义Token选择。
- Settings连接器与Deck使用其现行轻纸面、分隔与选中规则；更多页沿MoreNavigationContent已有卡片。
- 状态以文字或图标结合色彩表达。链接和弱文本按其实际字号、背景及状态测量。
- 主操作的前景与背景作为配对检查。Chat、回顾及导出按钮依据具体组件使用方式分别测量。
- 当前普通文本取样中，弱文本与链接在亮色画布上的对比度为2.93:1和2.88:1，后续配对建议见[UI规范](../mobile-app/ui-guidelines/README.md)。

## 7. 浮层 / Popover / Dropdown 配色

| 用途 | Token | 当前值 |
| --- | --- | --- |
| 不透明浮层 | `--color-bg-surface-solid` | `#fffdf8` |
| 控件分隔 | `--color-border-neutral` | `#e6ddd0` |
| 浮层阴影 | `--color-shadow-medium` | `rgba(91, 69, 44, 0.16)` |
| 悬停或按下叠层 | `--color-bg-hover` | `rgba(95, 74, 54, 0.06)` |
| 激活状态叠层 | `--color-bg-active` | `rgba(95, 74, 54, 0.12)` |
| 正文 | `--color-text-body` | `#4b3f33` |
| 辅助文本 | `--color-text-secondary` | `#7a6a59` |

## 历史与维护

[修订前原文](history/light-theme-before-ui-guidelines-20261102.md)完整保留早期色板与说明。本次同步为文档校准，应用Token和组件数值保持。
