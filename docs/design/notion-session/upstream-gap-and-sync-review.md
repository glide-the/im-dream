<!-- [Input] Upstream develop@e3523db9, current connector/Runtime code, real-account timing evidence, and lightweight-index requirement. -->
<!-- [Output] Evidence-based upstream/version/requirement gap, chosen synchronization scope, and anti-over-design decision. -->
<!-- [Pos] Notion upstream reconciliation decision record in docs/design/notion-session. -->
<!-- [Sync] 2026-08-28: retain upstream file navigation while replacing full-content sync and Agent CLI/MCP with lazy Runtime Read. -->

# Notion 上游差异与需求同步评审

Status: Implemented and verified  
Updated: 2026-08-28  
Upstream baseline: `glide-the/ink-and-memory develop@e3523db9f07400736123d2361111f428e60db0e4`

## 1. 版本证据

读取上游 `.claude/skills/notion-session/SKILL.md` 及三个 references 后，确认其业务导航是：

1. 读取 `.notion/connector.json`；
2. 读取 `.notion/index.json` 或 `.notion/databases/<id>.json` 定位 ID；
3. 只有需要正文时才调用 page Markdown endpoint。

上游有效的是“轻索引定位 + 按需正文”职责划分，不是 Agent 直接运行 `ntn` 的安全边界。

## 2. 代码与需求差异

| 对象 | 上游 `e3523db9` | 本仓库改造前 | 当前需求/实现 |
|---|---|---|---|
| Skill 制品 | 根 `.claude/skills`，Bash + `ntn api` | backend-owned Skill，显式 `mcp__notion__*` | backend-owned Skill，只允许 `Read`。 |
| 凭证 | `NOTION_HOME` 前置条件 | actor source + thread projection | 保留 actor 模式；Agent 不读 home/env。 |
| Snapshot | index 用于定位 | builder 逐 row 抓 page + Markdown + blocks | 定时同步只发布 ID/紧凑元数据，`pages={}`。 |
| 页面读取 | CLI Markdown endpoint | Agent 显式 MCP `read_page` | `Read(.notion/pages/<id>.json)` 触发 Runtime hook。 |
| 数据库 ID | 文档仍称 database | 已适配 data source query | public 名称保留，内部走 `data_sources/{id}/query`。 |
| 状态 | 未规定 selection 过渡 | insert 即 `synced` | `pending`，成功 index 精确提交后 `synced`。 |
| Runtime | CLI 可见 | MCP namespace 可见 | 单一文件协议；hook 内部调用 Dream-owned driver。 |

## 3. 真实故障证据

- actor 路径和 credential 权限正确；直接 data source query 成功，说明认证/API 通道并非根因。
- 旧单来源 current 包含 49 个嵌入 page body，3,069,491 bytes；完整构建约 225 秒后才原子出现。
- 选择 5 个来源后，旧同步持续 600 秒仍保持 1 database/49 pages 的 LKG；最终约 18 分钟后才发布 255 个嵌入正文、15,125,505 bytes 的 current。
- UI 同时把 5 个刚选来源显示为“已同步”，因为 repository insert 硬编码 `sync_status='synced'`。

因此“目录为空/旧内容不更新”的直接原因是后台同步错误抓取所有正文；“页面显示已同步”是独立的状态发布错误。

## 4. 方案决策

采用“保留 Dream-owned CLI driver + actor provider + Runtime Read hook”：

- `ntn` 继续负责 device login、file credential 格式和只读 API；
- Dream 负责 actor 归属、索引策略、原子 current、thread 投影与 hook；
- Agent 只认 `.notion` 文件协议，不认 CLI/MCP 参数。

未采用独立 CLI 产品路径，因为会恢复 home/权限/双状态问题；未采用 Dream 重写 OAuth/API，因为没有业务证据支持扩大实现面。

## 5. 同步到当前仓库的最小范围

### 保留

- 上游 `.notion` 文件导航和三个 reference 的业务知识；
- actor agentdata、credential staging、thread-private projection、固定 CLI；
- data source query 适配、原子 LKG、现有 scheduler/policy 和错误边界。

### 删除

- 后台 `get_page`、Markdown、blocks 全量抓取和 snapshot 正文；
- Agent Bash/CLI、显式 `mcp__notion__*` 工具说明及 Runtime namespace；
- selection 即 synced、静态 `.notion/pages/*.json` 正文文件和 Chat 远程同步。

### 新增/收敛

- data source cursor 分页轻索引；
- exact pending→synced 提交；
- `.notion/pages/<id>.json` PreToolUse lazy Read、index membership 校验、thread temp 清理；
- `.notion` sandbox denyWrite 与稳定安全错误。

### 延期

- 增量/webhook、跨副本租约、全文搜索、附件、任意远程 query、写入、多账号。

## 6. 反过度设计结论

本次没有新增服务、队列、表、migration、独立控制 API 或第二个正文消费者。后台只负责轻索引；Runtime 只负责用户请求触发的单页正文。保留 MCP 的“用户凭证受控快照”原则，但不保留 Agent-visible Notion MCP 工具。

## 7. 验收重点

- 自动化证明 index build 不调用正文接口，Read hook 才调用 Markdown；
- 未选 ID、跨用户或缺 credential 不发错误身份的远程请求；
- 新 current 不含正文；真实账户 5 来源/255 条索引在 8.4 秒发布为 111,408 bytes，并替换旧 15.1 MB snapshot；
- Skill/Runtime/前端不再声称“所有内容已同步”；
- 普通 Agent turn、其他 MCP/Skill、resume/cancel/EventBus/SSE 无回归。
