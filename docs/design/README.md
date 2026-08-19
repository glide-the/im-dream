<!-- [Input] Current product routes, backend services, and business boundaries. -->
<!-- [Output] Business-module design map without delivery-process artifacts. -->
<!-- [Pos] Canonical index for docs/design. -->

# 当前业务设计

设计文档按用户能够理解的业务模块组织。每个模块只回答四件事：业务目标、当前需求、已实现结果和
代码所有权。若文档与可执行代码冲突，以当前生产入口和公开 DTO 为准，并同步修正文档。

| 模块 | 文档 |
|---|---|
| 账号与认证 | [account-auth](account-auth/README.md) |
| Writing 与 Memory | [writing-memory](writing-memory/README.md) |
| Chat 与 Agent | [chat-agent](chat-agent/README.md) |
| Deck | [deck](deck/README.md) |
| Dream | [dream](dream/README.md) |
| Story Workspace | [story-workspace](story-workspace/README.md) |
| 资源与插件 | [resources-plugins](resources-plugins/README.md) |
| 工作区与存储 | [workspace-storage](workspace-storage/README.md) |
| 订阅与模型 | [subscription-models](subscription-models/README.md) |
| UI 与导航 | [ui](ui/README.md) |

## 共同约束

1. Dream、Chat 和 Deck 使用同一套生产身份、Thread、权限与持久化入口，不为测试或页面复制业务路径。
2. PostgreSQL Schema 只由 Admin 仓库 Drizzle 管理；Dream 只依赖已发布 capability，并在缺失时关闭能力。
3. 浏览器不接触 Provider Key、Gateway Service Key、数据库凭据或服务间 JWT Secret。
4. 系统 Deck 与产品初始化默认副本按 System Decks 只读展示；普通用户 Deck 必须已启用、已发布且没有未提交草稿才能进入启动页。
5. Deck 市场分发继续延期，当前导航和活跃前端客户端不提供入口；遗留分享 transport 不构成已交付市场产品。
