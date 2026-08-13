# Dream Agent Skill 与自动同步设计审查

> 审查结论：**修改后接受**。旧多 Episode 推荐按钮状态机已被拒绝并从当前设计与生产
> 代码移除；接受的是“已安装 Skill 推荐 + 成功边界 Hook 自动同步”的最小方案。

## 审查矩阵

| 审查问题 | 结论 |
|---|---|
| 是否形成第二套 Agent runtime/SSE/reducer | 否；Dream 组合共享 Chat thread、SSE、`ChatPanel`。 |
| 是否存在 Skill 阶段状态机 | 否；除首次 init 外，Skill 可随机、重复执行。 |
| 是否仍有推荐按钮或 Episode action POST | 否；页面只提供 Chat Slash 建议和只读 Artifact 工作台。 |
| Slash 选择是否隐式执行 | 否；只向输入框插入普通文本。 |
| Skill 来源是否真实 | 是；Deck 引用、ready installation、digest/version 和 thread 冻结回执共同决定。 |
| 同步是否依赖 Agent 主动 MCP | 否；before/after Hook 是确定性 owner。 |
| Observer 是否控制同步或 Agent | 否；仅做非控制型投影、审计与告警。 |
| Hook 失败是否会伪装成功 | 否；沿同一 Chat turn 返回唯一失败终态，保留 last-good。 |
| 是否修改 Claude Agent 入口/报文/session | 否；不改 runner、标准报文和 session identity。 |
| 权限是否削弱 | 否；actor/thread/Run/Workspace/Deck 与文件边界继续 fail closed。 |

## 被拒绝的过度设计

- EP01→EP02→EP03 推荐按钮、action projection 与“更多工作流操作”；
- next action、completion fact、checkpoint 和 Skill DAG；
- 专用 Episode 确认弹窗、恢复 POST、内部命令派发器；
- 由前端根据文件推断下一阶段；
- Agent 必须调用 MCP 才能同步；
- Observer 扫描文件、创建 binding、重试发布或推进 Workflow；
- 文件 watcher、子 Agent 完成即提前发布；
- 新增 Dream SSE、EventSource、transport、parser、reducer 或终态；
- 多环境 runtime tier 分支。

## 安全审查

- Slash inventory 只接受安全 Skill 名称、ready 安装和匹配的冻结插件事实；
- Hook 使用服务端派生身份，拒绝路径穿越、符号链接和越界文件；
- 私有发布加锁、写临时文件、fsync、原子替换，manifest 最后提交；
- GET 只读，不恢复、调度或启动 SDK turn；
- MCP 和 Observer 的失败不会成为绕过权限的备用写路径。

## 实施范围审查

方案没有新增 DDL、队列、事件存储、业务状态表或第二 API 协议。保留静态
`producerAction` 仅用于说明某类 Artifact 通常由哪个 Skill 产生，不参与可执行性、顺序、
禁用或推荐判断。

因此该方案是当前目标下的最小实现；删除旧状态机后再实施，而不是为其增加兼容双写。
