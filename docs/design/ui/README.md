<!-- [Input] Current Story Workspace routes, component styles, i18n, and UI reference PDF. -->
<!-- [Output] Current navigation, responsive, theme, and accessibility requirements. -->
<!-- [Pos] Canonical UI design baseline. -->

# 界面与导航

视觉参考：[Ink & Memory UI Design v2](./Ink%20%26%20Memory%20UI%20Design%20v2.pdf)。参考图只用于信息
密度、层级和布局骨架；最终组件必须使用 Ink & Memory 的颜色、排版和交互语义。

## 当前要求与结果

- 登录后默认进入 Story Workspace；浏览器 URL 是可恢复状态，刷新和前进/后退不能丢失当前模块。
- 桌面侧栏承载一级导航；Settings 使用分类侧栏，Work 内再切换 Deck、资源链接和插件。
- 窄屏复用同一路由、查询和 API，通过重排、折叠和可滚动区域适配，不复制业务流程。
- 页面使用安静的内容层级、足够留白、轻边界和语义状态；不照搬 Coze/ChatGPT 的品牌颜色或工作台结构。
- Loading、Empty、Error、Permission、Conflict 均有明确文本和恢复动作；错误不会通过隐藏 DOM 或假数据掩盖。
- 交互控件具备可见 focus、键盘顺序、ARIA name/state 和 `prefers-reduced-motion` 兼容。
- 界面文案由 `frontend/src/i18n.ts` 与组件 locale 资源提供；“工作台”是中文，“Work”是英文，不在同一语言环境重复显示双语标题。

## 代码所有权

- 路由：`frontend/src/router/storyWorkspacePath.ts`
- 外壳：`frontend/src/components/story-workspace/layout/`
- 页面：`frontend/src/pages/story-workspace/`
- 全局主题：`frontend/src/index.css`、`frontend/src/styles/`
- 国际化：`frontend/src/i18n.ts`
