<!-- [Input] Current frontend routes, backend public APIs, and module ownership in the repository. -->
<!-- [Output] Canonical business-documentation index for Ink & Memory. -->
<!-- [Pos] Entry point for all current product and implementation design documentation. -->

# Ink & Memory 文档

本目录只保留两类长期有效内容：当前业务需求与已实现结果，以及支撑这些业务的架构、部署和开发规则。
临时协作材料由 Git、PR、CI 或外部任务系统保存，不进入长期产品文档。

## 当前业务设计

| 模块 | 当前范围 |
|---|---|
| [账号与认证](design/account-auth/README.md) | 注册、登录、Google OAuth、Device Flow 与会话 |
| [Writing 与 Memory](design/writing-memory/README.md) | 写作 Session、时间线、Reflections 与记忆配置 |
| [Chat 与 Agent](design/chat-agent/README.md) | Thread、消息流、工具确认、SubAgent、Plan/TODO 与工作区 |
| [Deck](design/deck/README.md) | 系统/用户 Deck、维护弹窗、内容版本、启用和 Chat/Dream 启动 |
| [Dream](design/dream/README.md) | DreamAgent 启动、共享 Thread、产物同步和 Run 重入 |
| [Story Workspace](design/story-workspace/README.md) | 项目、故事、人物、场景、Episode 和审阅工作台 |
| [资源与插件](design/resources-plugins/README.md) | Notion 资源连接、Claude Plugin 与 Deck Plugin 生命周期 |
| [工作区与存储](design/workspace-storage/README.md) | 文件 CRUD、下载、编辑同步、对象存储与沙箱边界 |
| [订阅与模型](design/subscription-models/README.md) | Admin Product/Gateway 接入、套餐、额度、模型目录和调用资格 |
| [界面与导航](design/ui/README.md) | Story Workspace 路由、响应式布局、主题和可访问性 |

Deck 市场注册、发布、安装和分发治理不在当前产品范围，统一记录在
[Deck 市场分发延期边界](design/deck-register/README.md)。

## 技术与运维

- [系统架构、数据与安全边界](architecture/README.md)
- [部署](deploy/README.md)
- [开发规则](rules/README.md)
