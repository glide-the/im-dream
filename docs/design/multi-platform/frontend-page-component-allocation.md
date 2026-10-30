<!-- [Input] RN/RNW统一工程、端侧运行库和现有业务。 -->
<!-- [Output] 现行设计入口与历史策略归档。 -->
<!-- [Pos] 跨平台文档导航；2026-10-27统一frontend工程。 -->

# React Native 页面与组件迁移清单

现行逐模块分配、最小改动、原生化与局部网页保留范围统一维护于[RN/RNW工程设计](react-native-web-project-structure.md#按实际模块迁移)。主界面使用RN组件，Web保留平台文件；原始CSS/SVG与第三方DOM包在其适用区域继续复用。

原“RN App级页面＋持久完整业务WebView”分配已退役。[历史原文](history/rn-container-before-rnw-20261027/frontend-page-component-allocation.md)保留原路由核查与决策记录，现行实施逐项遵循统一工程设计及验收矩阵。

