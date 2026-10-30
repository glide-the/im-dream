<!-- [Input] RN/RNW统一工程、端侧运行库和现有业务。 -->
<!-- [Output] 现行设计入口与历史策略归档。 -->
<!-- [Pos] 跨平台文档导航；2026-10-27统一frontend工程。 -->

# React Native 前端复用取舍

现行选择为共享RN组件、React Native Web与平台文件。取舍依据及当前逐模块状态归[RN/RNW工程设计](react-native-web-project-structure.md)。

- 纯DTO、HTTP合同、parser/reducer与Stop逻辑直接复用。
- 普通页面和弹窗逐项迁移为RN组件，Web通过RNW渲染已迁移子树。
- 图标等自有叶子只按原生实际调用范围适配；原Web CSS与DOM版本保持。
- 网页登录、复杂编辑器及MCP App HTML采用局部网页文档适配，第三方包保持原始源码。

完整业务WebView首发策略已撤回，[历史原文](history/rn-container-before-rnw-20261027/frontend-reuse-tradeoffs.md)保留。

