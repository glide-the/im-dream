# Deck 上下文徽章 · 交互方案设计稿

- 日期：2026-08-03
- 状态：待实现（任务三按此稿执行）
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
2. **次因：`voiceSystemPrompt` 注入范围过宽。**
   `ChatView` 无条件把 `activeVoice?.systemPrompt` 注入每次运行，与"agent 名仅为信息展示"的新模型矛盾，且会泄漏到无关线程。

### 1.3 为什么现在才暴露

旧交互中「Chat →」直接跳入已存在的 voice 线程，`threadId` 立即存在，空窗只有"打包耗时"几秒；新交互（预设 Deck + 全新对话）把空窗扩大到"从选中 Deck 到首轮打包完成"的整个区间，结构性缺陷显现。

---

## 2. 设计目标与原则

- **G1 Deck 是一等上下文**：只要会话存在 Deck 上下文（输入区已选 / 线程已绑定），顶部即出现 Deck 徽章，不依赖线程或 receipt 是否存在。
- **G2 信息渐进呈现**：徽章先展示确定信息（Deck 名、Agent 列表、插件配置），receipt 的固化信息（版本、digest、frozen）就绪后无缝补入。
- **G3 不打断阅读**：任何异步数据到达（receipt、线程 hydration）只更新徽章自身，不引起消息区刷新或会话切换。
- **G4 信息展示 ≠ 行为注入**：顶部 agent 名仅作上下文展示；不向 Deck 对话注入单个 voice 的 system prompt。

---

## 3. 顶部 Deck 徽章 · 状态机

徽章组件：沿用 `PluginReceiptBadge`（改造为 Deck 上下文徽章），位于顶部操作行。

| 状态 | 触发条件 | 徽章表现 | 弹层内容 |
|---|---|---|---|
| S0 无 Deck 上下文 | 无 `badgeDeckId` 且无 receipt | 不渲染 | — |
| S1 已选 Deck，未发消息 | 有 `badgeDeckId`，无 `threadId` | 显示 🧩 + Deck 名 | Deck 名 / Agent 列表 / 插件配置清单（提示"版本与摘要将在首次运行后生成"） |
| S2 首轮运行中，receipt 未就绪 | 有 `threadId`，轮询中 | 同 S1（不加 loading 动画，避免打扰） | 同 S1 |
| S3 receipt 就绪 | 轮询拿到非空 plugins | 🧩 + 插件条目（包名 v版本 · 短 digest），frozen 时 +🔒 | 三区完整：Deck 名 / Agent（当前高亮）/ 插件清单（版本 + digest 卡片） |
| S4 切换到其他线程 | `activeThreadId` 变化 | 重新推导；无 Deck 上下文则隐藏（S0） | 随推导结果更新 |
| S5 新建对话 | `activeThreadId` → null | 保留选中 Deck 的徽章（S1） | 同 S1 |

### 状态流转

```
S0 ──选 Deck(Chat→/选择器)──▶ S1 ──首条消息──▶ S2 ──receipt 就绪──▶ S3
S3/S2 ──切换无线程/无Deck上下文──▶ S0/S1（按目标线程重新推导）
任意 ──新建对话且保留选中 Deck──▶ S1
```

---

## 4. 点击弹层 · 信息架构

点击徽章弹出（再次点击 / 点击外部 / Esc 关闭），三区结构：

1. **Deck 名称**：当前上下文 Deck 的本地化名称；无 Deck 时显示"本次对话未绑定 Deck"。
2. **Agent**：Deck 内启用的 agent 胶囊列表（图标 + 品牌色）；当前驱动会话的 agent 以实色高亮 + 「当前」标记（优先按 voice id 匹配，回落名称匹配）。
3. **插件清单**：
   - **receipt 态（S3）**：每个插件一张卡片 —— `package_spec`、`v版本`、`sha256` 短摘要（悬停看完整 digest）；frozen 时标题旁标注锁定。
   - **配置态（S1/S2）**：展示占位文案"插件将在首次运行打包后显示版本与摘要"；receipt 到达后原位替换，弹层不关闭、不跳动。

---

## 5. 边界情况

- **无插件 Deck**：徽章照常显示 Deck 名与 Agent；插件清单区显示"此 Deck 未配置插件"。
- **系统 Deck**：只读，仅展示；不尝试回写 voice.thread_id。
- **工作区未启用（workspace_enabled=false）**：后端不打包，receipt 永远为空 → 徽章停留在配置态（S1 样式），不无限轮询报错。
- **多语言**：所有新增文案走 i18n（en/zh 双键）；Deck/Agent 名按界面语言取 `name_zh/name_en` 回落 `name`。
- **voiceSystemPrompt 收窄**：仅当 voice 是本次会话的实际驱动者（voice 线程精确推导命中，或刚通过 voice 通道打开的请求线程）才注入；Deck 对话不注入单个 voice prompt。

---

## 6. 组件职责划分

| 组件 | 职责 |
|---|---|
| `ChatView` | 推导 `badgeDeckId` / `displayVoice` / `threadVoiceEntry`；向徽章传 `deck`、当前 voice 标识、`threadId`；按收窄后的条件向 `ChatPanel` 传 `voiceSystemPrompt` |
| `PluginReceiptBadge`（Deck 上下文徽章） | 按状态机渲染徽章与弹层；receipt 拉取与有界轮询（3s × 40） |
| `DeckChatSelector` | 输入区的 Deck 选择入口（不变） |
| `ChatPanel` | 消费 `deckId` / `voiceSystemPrompt`（不变） |
| 后端 | receipt 路由只读（不变）；run 启动时打包（不变） |

---

## 7. 实现要点（任务三按此执行）

1. `PluginReceiptBadge`：渲染条件改为 `deck || (threadId && plugins.length > 0)`；徽章文案按 S1/S3 切换；弹层插件区加"配置态"占位；保留现有轮询。
2. i18n：新增 `metadataPacking`（首次运行后显示版本与摘要）、`metadataNoPlugins`（此 Deck 未配置插件）。
3. `ChatView`：`voiceSystemPrompt` 改为按 `threadVoiceEntry` / `isRequestedThreadActive` 收窄后的值。
4. 验证：`tsc --noEmit`、ESLint（改动文件零新报错）。

---

## 8. 验收标准

- A1：Chat → 落地新聊天（未发消息），顶部立即显示 Deck 徽章，点击可见 Deck 名 / Agent 列表 / 插件配置提示。
- A2：发出首条消息后，receipt 就绪时徽章自动升级为插件版本/digest 展示，弹层内容原位更新，消息区无刷新。
- A3：切换到无 Deck 的历史线程，徽章隐藏；切回 Deck 线程，徽章恢复且 receipt 信息完整。
- A4：Deck 对话的后端请求不再携带单个 voice 的 system prompt（voice 线程行为不变）。
- A5：tsc / ESLint 通过，无新增报错。
