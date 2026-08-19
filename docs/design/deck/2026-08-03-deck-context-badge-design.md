<!-- [Input] Chat Thread Deck/Agent binding, Deck receipt metadata, and enabled Agent projection. -->
<!-- [Output] Deck context badge and same-Deck next-turn Agent-selection interaction contract. -->
<!-- [Pos] Chat consumption interaction design under Deck. -->
<!-- [Sync] 2026-08-17: make enabled Agents clickable while Thread, Deck, content version, and receipt stay fixed. -->

# Deck 上下文徽章 · 交互方案设计稿

- 日期：2026-08-03
- 状态：已实现并纳入自动化验收
- 关联问题：第一次对话时聊天页上方不显示 Deck 信息（复现）

---

## 1. 背景与问题定义

### 1.1 现象

通过 Deck 编辑器「Chat →」或输入区 Deck 选择器选定 Deck 后，发起**第一次对话**时，聊天页顶部操作行不显示任何 Deck 信息；重新打开该线程后显示正常。

### 1.2 根因（已确认，代码逻辑问题）

1. **主因：Deck 信息入口与插件 receipt 强耦合。**
   `PluginReceiptBadge` 的渲染条件是 `threadId && plugins.length > 0`。
   在当前交互模型下，第一次对话从「无线程的新聊天」开始：
   - 发送首条消息前：无 `threadId` → 徽章不渲染；
   - 首条消息发出后、后端 workspace 打包完成前：无 receipt → 徽章不渲染（轮询最长 2 分钟兜底）。
   即第一次对话存在一段**必然的信息空窗**。
2. **次因：当前 Agent 缺少显式交互。**
   `ChatView` 能按 Thread 的 `voice_id` 推导并执行当前 Agent，但弹层只把 Agent 渲染为静态标签。用户在同一个 Deck 的多 Agent 协作场景中无法指定下一轮执行者。

### 1.3 为什么现在才暴露

旧交互中「Chat →」直接跳入已存在的 voice 线程，`threadId` 立即存在，空窗只有"打包耗时"几秒；新交互（预设 Deck + 全新对话）把空窗扩大到"从选中 Deck 到首轮打包完成"的整个区间，结构性缺陷显现。

---

## 2. 设计目标与原则

- **G1 Deck 是一等上下文**：只要会话存在 Deck 上下文（输入区已选 / 线程已绑定），顶部即出现 Deck 徽章，不依赖线程或 receipt 是否存在。
- **G2 信息渐进呈现**：徽章先展示确定信息（Deck 名、Agent 列表、插件配置），receipt 的固化信息（版本、digest、frozen）就绪后无缝补入。
- **G3 不打断阅读**：任何异步数据到达（receipt、线程 hydration）只更新徽章自身，不引起消息区刷新或会话切换。
- **G4 显式 Agent 选择**：顶部当前 Agent 是本 Thread 下一轮执行者；用户只能显式切换到当前 Deck 内已启用 Agent。Deck、内容版本、插件 receipt 与 Thread 身份不随之改变。
- **G5 发送时再校验**：点击仅更新前端下一轮选择；真正发送时后端校验 owner、Deck 归属、Agent 启用状态并以旧 Agent 为 expected value 做 CAS。失败不启动 Agent、不改变原绑定。

---

## 3. 顶部 Deck 徽章 · 状态机

徽章组件：沿用 `PluginReceiptBadge`（改造为 Deck 上下文徽章），位于顶部操作行。

| 状态 | 触发条件 | 徽章表现 | 弹层内容 |
|---|---|---|---|
| S0 无 Deck 上下文 | 无 `badgeDeckId` 且无 receipt | 不渲染 | — |
| S1 已选 Deck，未发消息 | 有 `badgeDeckId`，无 `threadId` | 显示 🧩 + Deck 名 | Deck 名 / Agent 列表 / 插件配置清单（提示"版本与摘要将在首次运行后生成"） |
| S2 首轮运行中，receipt 未就绪 | 有 `threadId`，轮询中 | 同 S1（不加 loading 动画，避免打扰） | 同 S1 |
| S3 receipt 就绪 | 轮询拿到非空 plugins | 🧩 + 插件条目（包名 v版本 · 短 digest），frozen 时 +🔒 | 三区完整：Deck 名 / Agent（当前高亮，可切换）/ 插件清单（版本 + digest 卡片） |
| S3a Agent 待切换 | 活跃 Thread 中点击其他已启用 Agent | Deck/Thread/receipt 不变；弹层关闭，顶部当前 Agent 立即更新 | 下一次发送携带所选 Agent；后端成功后更新 Thread 当前 Agent |
| S3b Agent 冲突/失效 | 发送前 Agent 被禁用、移出 Deck 或旧值已变化 | 不启动运行；保留服务端原 Agent | Chat 显示可恢复错误；刷新后按服务端 Thread 重新水合 |
| S4 切换到其他线程 | `activeThreadId` 变化 | 重新推导；无 Deck 上下文则隐藏（S0） | 随推导结果更新 |
| S5 新建对话 | `activeThreadId` → null | 保留选中 Deck 的徽章（S1） | 同 S1 |

### 状态流转

```
S0 ──选 Deck(Chat→/选择器)──▶ S1 ──首条消息──▶ S2 ──receipt 就绪──▶ S3
S3/S2 ──切换无线程/无Deck上下文──▶ S0/S1（按目标线程重新推导）
任意 ──新建对话且保留选中 Deck──▶ S1
S3 ──点击同 Deck 其他 Agent──▶ S3a ──发送+校验+CAS成功──▶ S3
S3a ──成员/权限/CAS失败──▶ S3b ──刷新──▶ S3
```

---

## 4. 点击弹层 · 信息架构

点击徽章弹出（再次点击 / 点击外部 / Esc 关闭），三区结构：

1. **Deck 名称**：当前上下文 Deck 的本地化名称；无 Deck 时显示"本次对话未绑定 Deck"。
2. **Agent**：Deck 内启用的 Agent 胶囊按钮（图标 + 品牌色）；当前 Agent 以实色高亮 + 「当前」标记并使用 `aria-pressed=true`、不可重复点击。活跃 Thread 中的其他 Agent 可点击切换下一轮执行者；无线程预览态只展示，不在此入口创建 Thread。
3. **插件清单**：
   - **receipt 态（S3）**：每个插件一张卡片 —— `package_spec`、`v版本`、`sha256` 短摘要（悬停看完整 digest）；frozen 时标题旁标注锁定。
   - **配置态（S1/S2）**：展示占位文案"插件将在首次运行打包后显示版本与摘要"；receipt 到达后原位替换，弹层不关闭、不跳动。

---

## 5. 边界情况

- **无插件 Deck**：徽章照常显示 Deck 名与 Agent；插件清单区显示"此 Deck 未配置插件"。
- **系统 Deck**：仍不可编辑 Deck 定义，但 Chat 消费态与用户 Deck 一致，可在该系统 Deck 已启用的 Agent 之间选择；不会产生启停、编辑或版本写入。
- **工作区未启用（workspace_enabled=false）**：后端不打包，receipt 永远为空 → 徽章停留在配置态（S1 样式），不无限轮询报错。
- **多语言**：所有新增文案走 i18n（en/zh 双键）；Deck/Agent 名按界面语言取 `name_zh/name_en` 回落 `name`。
- **单 Agent Deck**：只有当前按钮且不可点击，不显示额外切换入口。
- **禁用/跨 Deck Agent**：前端不展示禁用项；伪造或过期请求由 `DeckChatContextService` fail closed，不更新 Thread。
- **并发切换**：后端以当前 `voice_id` 为 expected value 更新；CAS 失败返回 `CHAT_AGENT_CONFLICT`，不启动本轮运行。
- **运行提示词**：下一轮只使用经后端重新解析的所选 Agent `system_prompt`，不信任浏览器传入提示词。

---

## 6. 组件职责划分

| 组件 | 职责 |
|---|---|
| `ChatView` | 推导 `badgeDeckId` / `displayVoice` / `threadVoiceEntry`；向徽章传当前 Agent 和选择回调；将下一轮 `deckId` / `voiceId` 交给 `ChatPanel` |
| `PluginReceiptBadge`（Deck 上下文徽章） | 按状态机渲染徽章与弹层；receipt 拉取与有界轮询（3s × 40）；只把启用 Agent 渲染为选择控件 |
| `DeckChatSelector` | 输入区的 Deck 选择入口（不变） |
| `ChatPanel` | 每轮发送 `deckId` / `voiceId`；不创建另一条 Chat 或 Deck 切换流程 |
| 后端 | `DeckChatContextService` 重验 owner/Deck/Agent；`select_chat_thread_voice` 做 actor+Deck+expected Agent CAS；消息 metadata 保存实际 `deckId`/`voiceId` |

---

## 7. 实现要点（任务三按此执行）

1. `PluginReceiptBadge`：渲染条件改为 `deck || (threadId && plugins.length > 0)`；徽章文案按 S1/S3 切换；弹层插件区加"配置态"占位；保留现有轮询。
2. i18n：新增 `metadataPacking`（首次运行后显示版本与摘要）、`metadataNoPlugins`（此 Deck 未配置插件）。
3. `ChatView`：活跃历史 Thread 向徽章提供 `setSelectedAgentId`；选中后顶部和下一轮请求同步更新，Thread ID 与 Deck ID 不变。
4. 后端：移除“Agent 永久不可切换”的旧拒绝；保留 Deck 不可变，并在发送入口执行成员/权限校验与 CAS。每轮消息写入所用 Deck/Agent 元数据。
5. 验证：静态合同、后端 route/CAS 单测、provider-free Playwright、构建与真实只读页面检查。

---

## 8. 验收标准

- A1：Chat → 落地新聊天（未发消息），顶部立即显示 Deck 徽章，点击可见 Deck 名 / Agent 列表 / 插件配置提示。
- A2：发出首条消息后，receipt 就绪时徽章自动升级为插件版本/digest 展示，弹层内容原位更新，消息区无刷新。
- A3：切换到无 Deck 的历史线程，徽章隐藏；切回 Deck 线程，徽章恢复且 receipt 信息完整。
- A4：历史 Thread 弹层中当前 Agent 明确高亮且不可重复点击；其他已启用 Agent 可点击，点击后保持同一 Thread/Deck/receipt 并更新顶部 Agent。
- A5：下一次发送由后端确认 Agent 属于当前 Deck 且已启用；成功后 CAS 更新当前 Agent并把 `deckId`/`voiceId` 写入该轮消息元数据。
- A6：跨 Deck、禁用、无权限或并发冲突均不启动 Agent，原 Thread Agent 保持不变并可刷新恢复。
- A7：系统 Deck 使用同一消费交互，但没有启停、编辑或版本写入口。
- A8：类型、构建、单元与 Playwright 通过，无新增浏览器异常或横向溢出。
