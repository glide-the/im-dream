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

## 连续编辑与删除事实补充审查

> 结论：**接受**。

- `.dream/WORKBENCH.md` 只是 Agent 可读的工作台合同文件和本轮服务端事实，不存储
  lifecycle、不产生事件、不控制 Hook，因此不是第二状态源。
- 每 turn 动态上下文复用既有 `assemble_context → build_user_message`，没有增加公开 DTO、
  Dream 报文或执行入口，也不修改 `claude_session_id`/resume 语义。
- stage 删除只在当前完整源集合为空时发生；新源集合仍通过既有 allowlist、路径、UTF-8、
  数量、大小和 actor/thread/run 权限校验。它修复追加式投影，不引入 Workflow 状态机。
- 不采用文件 watcher、命令识别、模型输出解析或 Observer 补偿。标题修改仍由主 Agent
  编辑 canonical `project.yaml`，Hook 只同步成功 turn 后的文件事实。

## 工作台上下文初始化与逐轮读取补充审查

> 结论：**修改后接受**。旧实现必须先补齐“初始化即部署”和“每轮实际路径读取”两项，
> 才符合业务目标；更新后的设计见 `workbench-context-injection-design.md`。

| 审查项 | 结论 |
|---|---|
| 是否只依赖首次 `_launch_instruction` | 否；每个 Dream turn 在 `assemble_context` 刷新并注入。 |
| 初始化时是否已有上下文文件 | 是；静态合同与 Dream surface 三文件原子部署。 |
| 是否把整个设计稿直接塞进 prompt | 否；运行时只使用 `backend/story_workspace` 下稳定的 Agent 合同。 |
| Agent 是否获得同步后的真实路径 | 是；路径由 server-owned workspace 解析、验证，只进入内部 message。 |
| Agent 是否会反向写上下文文件 | 否；Agent 必须 Read，刷新只由宿主完成。 |
| 是否改变公开 DTO、SSE、runner 或 session | 否。 |
| 是否形成第二状态源或 Observer 控制 | 否；上下文是定位合同，不保存 lifecycle。 |
| 是否引入 watcher、重试队列或状态机 | 否。 |

修改后方案仍只复用现有 workspace pack、`assemble_context` 和 context builder 三个稳定扩展点，
不增加数据库、API 或后台任务，是满足逐轮上下文要求的最小实现，因此接受后进入代码实现。

## Project 页面投影补充审查

> 结论：**修改后接受**。

原实现只把 `project.yaml` 复制到 `.dream`，没有在 `after_main_turn` 刷新既有 PostgreSQL
Story 投影，文件正确但真实消费页面仍可能显示旧标题。修改后的最小方案复用现有
`ArtifactStoryIndexService` 和 Story Index REST，不增加表、队列、状态机或第二协议：

- Hook 在成功根 turn 的文件发布与 Episode 绑定后执行一次幂等 Story materialize；
- `artifact_missing` 表示 Episode 尚不可索引，等待后续成功 turn，不制造失败状态机；
- 其他投影失败沿同一 Chat turn 失败路径返回，不由 Observer 补偿或反向控制；
- Story Index DTO只增加 bounded `projectTitle`，不暴露路径或内部身份；
- Execution masthead消费 Project title，Episode 标题仍消费 Episode artifact；
- 真实测试逐轮检查文件、Hook、PostgreSQL/API 和页面，避免用文件 SHA 掩盖消费链断点。

该改动直接补齐已有链路的最后一个投影边界，没有复制 reducer、引入 watcher、轮询补偿或
前端写操作，符合“Hook 按文件事实同步、Observer 非控制型”的目标。

## Dream 工作空间展示标题补充审查

> 结论：**接受**。

- Project 已物化时直接复用 `story_workspace_stories.title`，不新增 Run title、缓存表或
  前端写回；Project 尚未物化时才从已有 launch Source Message 派生 80 字符目标前缀。
- Execution、Dream 回访和 Admin Run 列表共享解析顺序，但分别通过既有 Story Index 或
  PostgreSQL 只读查询消费，不创建跨仓库的新协议。
- Episode 标题、Deck 名称和 workflow summary 不得覆盖 canonical Project title，避免
  再次形成多个页面局部标题来源。
- Admin 仍是只读运营消费者，不扫描 Artifact，也不取得 Dream 文件写权限。

方案只补一个 DTO 字段、两个现有查询和页面显示，不需要 DDL、Observer、Hook 扩展、消息
协议或状态机；这是满足所有列表一致性的最小范围。

## Agent 资产协作补充审查

> 结论：**修改后接受**。完整设计见 `asset-collaboration-design.md`。

- 真实 Run 证明失败原因是 Dream turn 仍收到普通 Chat 的 standalone JSON proposal 合同，
  同时工作台上下文缺少可执行资产 CRUD 规则；Claude session 和 thread history 没有丢失。
- Dream 身份继续由 `ClaudeAgentService.assemble_context` 的服务端 mapper 决定；不得在公开
  Claude Agent 报文中增加 `run_id`、Dream flag 或浏览器可伪造字段。
- `ASSET-COLLABORATION.md` 与 `WORKBENCH.md` 一样只是 Agent 可读合同，不存储 lifecycle、
  revision 或 completion，因此不是第二状态源。
- 人物、场景、分镜共享一个合同和现有 Hook 文件事实扫描，不复制三套运行时或同步器。
- Hook 不解析 assistant JSON，也不依赖 MCP；失败、Stop、无变化和同步失败仍沿既有单终态
  与 last-good 规则处理。
- 不新增 DDL、CRUD REST、Watcher、后台重试、命令状态机或 Observer 控制，属于满足自然
  语言资产编辑的最小改动。
