<!-- [Input] RN/RNW统一工程、端侧运行库和现有业务。 -->
<!-- [Output] 现行设计入口与历史策略归档。 -->
<!-- [Pos] 跨平台文档导航；2026-10-27统一frontend工程。 -->
<!-- [Sync] 2026-10-28: Web当前可用性和原页面回归先于后续原生推进，RN精简主页面继续停止正式部署。 -->

# Ink & Memory 跨平台方案

**React Native生成iOS、Android原生主界面；共享组件通过React Native Web接入Next；业务通过HTTP访问端侧Dream Python和Claude。**

现行方案为[React Native / React Native Web统一工程设计](react-native-web-project-structure.md)，包含工程树、逐模块迁移、正常/异常时序、实例生命周期、状态转换、验收和评审。

统一发布工程归`frontend/`：`src/`共享源码，`ios/`与`android/`原生工程，`app/`保留Next服务端和现有Web视图；精确别名与平台文件选择由Next/Metro配置。旧`mobile/`工程已退役，代码存入`frontend/legacy/`。

当前状态：工程迁移与RN接线开发中。Web通过`App.web.tsx`保持原业务；原生业务逐项迁移。主界面整页WebView策略已撤回，原文保存于[历史快照](history/rn-container-before-rnw-20261027/README.md)。

执行前提：先保证正常Web服务、原页面、网页登录和桌面/窄屏交互可用。共享改动逐次完成Web类型、生产构建与原页面回归后继续原生接线；精简RN主页面保留未验收状态。当前检查和实际业务范围见[执行记录](../../exec/mobile-app-design-review-20261024.md)。

[运行库架构](mobile-runtime-architecture.md)、[iOS运行库与平台差异](mobile-ios-interaction.md)、[Android运行库与平台差异](mobile-android-interaction.md)继续提供端侧执行依据；前端目录、主界面承载与交互以统一工程设计为准。产品范围见[移动PRD](../../prd/dream-workspace/mobile-app.md)，制品与账号前提见[发布设计](../../deploy/mobile-app-release.md)。

