<!-- [Input] React Native统一客户端、Next Web发布、端侧执行和减少整体改动的目标。 -->
<!-- [Output] RN框架内的渐进取舍、现行设计入口和共同运行合同。 -->
<!-- [Pos] Ink & Memory跨平台设计入口。 -->
<!-- [Sync] 2026-10-27: RN为固定框架，按当前源码明确首发原生页面、持久WebView页面、原样复用模块和移动排除范围。 -->

# Ink & Memory 跨平台方案

**React Native统一iOS、Android客户端；Next继续Web发布；移动业务通过HTTP访问端侧Python/Claude。**减少改动通过RN应用内的区域划分实现，原平台代码用于运行库和系统适配。

先读[RN页面承载与组件复用设计](frontend-page-component-allocation.md)。该稿逐项登记当前路由、页面和关键组件，明确首发RN原生化、持久WebView保留、原样复用和移动排除边界。[RN框架内的前端复用取舍](frontend-reuse-tradeoffs.md)保留方案比较与通用约束。

| RN内的方式 | 取舍 |
| --- | --- |
| RN宿主＋完整业务WebView | 原业务组件保持，改动最小，业务区域仍为网页渲染 |
| RN原生App级页面＋持久业务WebView | **当前首发策略**：启动、一级导航、恢复层和系统操作原生化；现有范围内业务页保持完整网页树 |
| 全面RN原生页面＋RN Web | 已排除的首发候选；未来存在明确业务需求时重新评审 |

### 保持的目标

- 现有DOM组件、Hooks、纯业务逻辑、DTO和parser/reducer继续随业务WebView与Next Web复用；首发不建立RN Web共享组件层。
- RN原生区域与网页区域使用相同HTTP业务合同；正常网页登录、原权限、状态、持久化和计费保持。
- App级管理器管理解释器、Node、HTTP/Next等实例；后端中介者协调具体用例，复用原Factory/服务，禁止按组件添加包装。
- 端侧不展示或适配Dream工作台创建、初始生成和审核确认；Web及已有数据保留。

阅读顺序：[页面承载与复用设计](frontend-page-component-allocation.md) → [复用取舍](frontend-reuse-tradeoffs.md) → [RN业务交互设计](mobile-react-native-interaction.md) → [架构与实例生命周期](mobile-runtime-architecture.md#前端取舍适用范围) → [iOS](mobile-ios-interaction.md) / [Android](mobile-android-interaction.md) → [发布设计](../../deploy/mobile-app-release.md)。产品范围与骨架见[移动PRD](../../prd/dream-workspace/mobile-app.md)。

当前状态为设计交付，RN App级页面、持久业务WebView与运行库尚未接线。实施按具体清单推进；同一WebView Cookie会话、增量读取、运行库共存及两平台实际业务分别验证，当前网页结果不替代安装包业务验收。

本轮记录见[RN内前端复用取舍评审](../../exec/mobile-app-design-review-20261024.md#2026-10-27-rn框架内的前端复用取舍评审)。原文见[历史快照](../../exec/history/mobile-design-before-multi-platform-20261027.md)。
