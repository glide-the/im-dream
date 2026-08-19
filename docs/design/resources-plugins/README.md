<!-- [Input] Notion connector, Claude Plugin, Deck Plugin, and Settings Work implementation. -->
<!-- [Output] Current resource-link and plugin lifecycle design. -->
<!-- [Pos] Canonical resources-plugins module design. -->

# 资源链接与插件

参考视觉需求：[资源连接器交互 PDF](./链接器概念的交互设计稿.pdf)。

## Settings / Work

`/story-workspace/settings/work` 使用 Deck、资源链接、插件三个内部页签。它们共享设置页面外壳和
权限上下文，但数据所有权彼此独立。

## Notion 资源链接

- 用户创建 Connector 后发起 Notion Device 登录，并轮询认证结果。
- 认证成功后读取可用数据库、页面和资源；用户显式选择的资源才进入持久化来源。
- Settings 与 Chat 读取同一 Connector/Resource 状态；Chat 不复制独立连接器数据库。
- 用户可同步或移除已选资源；删除 Connector 前由服务端处理其资源归属。
- 当前代码具备 Connector CRUD、认证、发现、选择和同步基线；进一步的 Notion 导入产品迭代暂停。

生产入口为 `/api/connectors/**`，前端所有权在 `frontend/src/components/dashboard/`，后端所有权在
`backend/routers/notion.py` 和 `backend/notion/`。

## Claude Plugin

- Plugin 安装是异步操作，可查询 operation 与 installation 状态。
- Deck 通过 `/api/decks/{deck_id}/claude-plugins` 保存引用，引用变化进入 Deck 聚合草稿。
- Runtime 只物化已安装、兼容且允许的引用，并向 Thread 保存 load receipt。
- 卸载、失败或不兼容不会静默加载旧内容。

代码位于 `frontend/src/components/claude-plugin-admin/`、`backend/routers/claude_plugins.py` 和
`backend/services/claude_plugin/`。

## Deck Plugin

- 后端已具备安装、启用、禁用、升级审批、回滚、reconcile、卸载和 runtime readiness 合同。
- manifest、兼容性、权限、digest 和 runtime lock 在服务端校验；失败保持来源版本和上一份可用物化结果。
- `frontend/src/components/plugin-admin/` 存在管理组件，但当前生产路由没有挂载 `PluginAdminPage`；
  Settings / Work 的“插件”页签实际挂载的是 `ClaudePluginAdminPage`。因此 Deck Plugin 不能描述为当前
  用户可操作页面，只能作为已实现的后端/runtime 基线。
- Deck binding 与内容版本是不同事实：内容版本描述 Deck 表单快照，Plugin semver 描述运行依赖。

代码位于未挂载的 `frontend/src/components/plugin-admin/`、`backend/routers/deck_plugins.py`、
`backend/routers/deck_plugin_binding.py` 和 `backend/services/deck_plugin/`。
