<!-- [Input] Turn-navigation PRD, structure and hierarchy records, Dream theme tokens, and screenshots. -->
<!-- [Output] Rail, hover card, narrow-column list, focus, state, and light/dark visual rules. -->
<!-- [Pos] Archived initial html-design-workflow Stage 4 visual draft; current rules are in turn-navigation-ui.md. -->
<!-- [Sync] 2026-09-29: preserve the initial spaced-rail draft after the compact-motion correction. -->
<!-- [Sync] 2026-09-29: adapt the screenshot reference to Dream's own semantic tokens and fonts. -->

# Dream Chat 用户消息轮次导航 — UI 视觉与交互设计

> 历史草稿：保留最初的宽松刻度与浮卡方案，不作为当前实现规范。现行视觉规则见[轮次导航 UI 规范](./turn-navigation-ui.md)。

> `html-design-workflow` 阶段 4。依据[轮次导航 PRD](./turn-navigation.md)、[结构草图](./turn-navigation-structure.md)、[层级逻辑](./turn-navigation-hierarchy.md)与两张截图。截图里的红框、Codex 文案、深灰背景、蓝色气泡、书签图标均是参考材料，不进入 Ink & Memory 产品。以下尺寸是界面布局建议，非业务配额；颜色取 [tokens.css](../../../frontend/app/_dream/styles/tokens.css)，字体继承 [index.css](../../../frontend/app/_dream/index.css) 的 `--font-family-ui`。

## 视觉判断

截图把注意力放在一条极窄的左侧刻度列；正文仍是主角。被指向的刻度旁出现两层文字的浮卡，第一层提示用户输入，第二层提示随后产生的交互结果。Dream 中采用克制的「纸面索引」方向：轨道像书页边缘的目录标记，浮卡像纸签；亮暗主题均使用现有语义色，不引入新的品牌色、字体、图标或动效依赖。

## Aesthetic Style 样式表

| 元素 | 视觉规范 | 对应现有变量／理由 |
| --- | --- | --- |
| 阅读底面 | 保留现有 Chat 消息阅读区的圆角与底色；轨道无独立大侧栏背景 | `--color-bg-app`，不改变既有消息层次 |
| 轨道 | 消息区左缘占约 `2.75rem`；一根细竖线串起每条用户消息的短横刻度；轨道可独立纵向滚动 | 细线用 `--color-border-paper`，刻度用 `--color-text-muted` |
| 刻度 | 普通短横约 `0.55rem`；当前项延长到约 `1rem` 且加粗；视觉线与实际按钮热区分开 | 当前项用 `--color-action-primary`；长度和粗细同时区分当前位置 |
| 聚焦与悬浮 | 热区最小约 `40×40px`；悬浮有浅底，键盘焦点有完整外轮廓 | `--color-bg-hover`、`--color-border-focus`；不单靠颜色 |
| 摘要浮卡 | 贴近被指向刻度右侧；宽度约 `18–22rem`，随消息区收缩；纸面底、细边框、柔和阴影、适度圆角 | `--color-bg-surface-solid`、`--color-border-paper`、`--color-shadow-medium` |
| 摘要排版 | 顶部小字说明“第 N 条用户消息”；用户预览为主文字，回复预览／状态为次级文字，各自截成几行，完整内容回到原消息读 | `--color-text-primary`、`--color-text-secondary`、`--color-text-muted`；继承 `--font-family-ui` |
| 状态 | 正在回复、暂无回复、失败、状态待核对与摘要不可用都用文字；失败可辅以状态色但不用色彩代替文字 | `--color-state-error` 仅用于已确认失败，其他状态保持中性 |
| 手机展开区 | 消息区上沿轻量“本对话消息”按钮；展开后是可滚动的纸面列表，用户预览与对应结果直接成对显示 | 与桌面使用同一消息索引、文案和颜色 |
| 定位提示 | 被定位的原用户消息可有短暂边框／背景强调；现有气泡与 Markdown 样式保持原样 | `--color-bg-active` 与 `--color-border-focus`；不改消息内容 |

### 视觉密度与边界

- `B1` 只占消息阅读区内部左缘，不挤占全局页面侧栏，也不与右侧 Thread HistorySidePanel 竞争位置。侧边任务会话的消息区变窄时，优先缩小摘要卡宽度；到容器宽度不足时切换手机式展开列表。
- 用户发送的消息数量决定刻度数量和顺序；不模仿截图中任意的刻度数量或物理间距。每项保持独立热区；长列表自身滚动，轨道不会被压成不可点的连续细线。
- 悬浮卡仅显示当前轮次的用户原文预览／附件名称和本轮助手可读回复预览或明确状态；不显示工具流水、技术 ID、模型生成的概括或任意按钮。若定位失败需要“重试”，提供可操作的非模态卡片，而非把按钮塞进纯提示浮层。

## UI Component Structure

| 阶段编号 | 建议组件名 | 容器与责任 | React 映射 |
| --- | --- | --- | --- |
| A1 | `ChatPanel` 既有页头 | 既有标题和操作，无新增顶栏动作 | 不改现有组件 |
| B1 | `TurnNavigation` | 接收当前 Thread 的可读用户消息索引，桌面渲染竖轨道，窄容器渲染展开入口；显示索引覆盖范围 | 作为 `ChatPanel` 消息阅读区域子组件 |
| B2 | `TurnNavigationItem` | 一条已发送用户消息对应一个按钮；暴露顺序、当前位置、悬浮／聚焦和定位请求 | `key={message.id}`，定位目标为同一 `message.id` |
| C1 | `TurnPreview` | 预览用户输入及本轮助手结果／状态；桌面为锚定浮层，手机为列表行内文字 | 接受已计算的预览字符串与状态，不解析或执行 Markdown |
| D1 | `ChatMessageList` 既有阅读区 | 消息滚动和历史分页仍由 `ChatPanel` 协调 | 保留原滚动容器和渲染路径 |
| D2 | 既有用户消息节点 | 承接消息 ID 锚点与短暂定位强调 | 不复制用户消息组件 |
| E1 | `AIInputDock` 既有输入区 | 原发送、停止、排队与草稿区域 | 始终在阅读区下方，浮层不能覆盖 |

## 设计变量与无依赖示意代码

代码仅表达 DOM、组件边界与样式关系。`items`、`preview`、`activeMessageId`、`onNavigate` 均由现有 Chat 状态提供；文字走现有 i18n。按钮与摘要要从 `message.id` 对应的已授权消息派生，不能把示例文案当成产品数据。无 Font Awesome、Tailwind、Google Fonts 或新运行时依赖。

```tsx
// ChatPanel 的消息阅读区域示意：浮卡与滚动层为同级，避免被 overflow-x: hidden 裁切。
<div className="chat-turn-reading-container">
<section className="chat-turn-reading" aria-label={t('chat.turnNavigation.readingRegion')}>
  <TurnNavigation
    items={items}
    activeMessageId={activeMessageId}
    previewMessageId={previewMessageId}
    coverage={coverage}
    onPreview={setPreviewMessageId}
    onNavigate={navigateToUserMessage}
  />
  <div ref={chatContainerRef} className="chat-turn-reading__scroll" onScroll={handleScroll}>
    <ChatMessageList {...existingMessageListProps} />
  </div>
  {preview && isWideReadingArea ? (
    <TurnPreview
      id={`turn-preview-${preview.messageId}`}
      className="chat-turn-preview"
      preview={preview}
      style={{ top: previewTop }}
    />
  ) : null}
</section>
</div>

// TurnNavigation 的桌面部分示意。
<nav className="chat-turn-rail" aria-label={t('chat.turnNavigation.label')}>
  <ol className="chat-turn-rail__list">
    {items.map((item, index) => (
      <li key={item.messageId}>
        <button
          type="button"
          className="chat-turn-rail__item"
          aria-label={t('chat.turnNavigation.item', { index: index + 1, preview: item.userPreview })}
          aria-current={activeMessageId === item.messageId ? 'location' : undefined}
          aria-describedby={previewMessageId === item.messageId ? `turn-preview-${item.messageId}` : undefined}
          onPointerEnter={() => onPreview(item.messageId)}
          onFocus={() => onPreview(item.messageId)}
          onClick={() => onNavigate(item.messageId)}
        >
          <span className="chat-turn-rail__mark" aria-hidden="true" />
        </button>
      </li>
    ))}
  </ol>
  {coverage !== 'complete' ? (
    <p className="chat-turn-rail__coverage">{t('chat.turnNavigation.loadedOnly')}</p>
  ) : null}
</nav>

// TurnPreview 的内容示意；userPreview / answerPreview 均作为普通文本渲染。
<div id={id} className={className} role="tooltip">
  <span className="chat-turn-preview__eyebrow">{t('chat.turnNavigation.itemShort', { index })}</span>
  <p className="chat-turn-preview__user">{userPreview}</p>
  <p className="chat-turn-preview__answer">{answerPreview ?? statusLabel}</p>
</div>
```

> 鼠标从按钮移往浮卡时，二者所属的交互区域应保持打开；指针和焦点都离开、按 Escape 或切换 Thread 才关闭。`role="tooltip"` 只用于纯文字预览；含“重试”按钮的定位失败卡改用带可读标题的非模态 `role="dialog"`，并确保按钮可由键盘到达。`onPointerEnter` 不能成为唯一入口，键盘聚焦、手机触摸均要可用。

```css
/* 变量只承接本功能尺寸；色彩始终引用 Dream 的语义 token。 */
.chat-turn-reading-container {
  display: flex;
  flex: 1;
  min-width: 0;
  min-height: 0;
  container: chat-turn-reading / inline-size;
}
.chat-turn-reading {
  --turn-rail-width: 2.75rem;
  --turn-card-gap: 0.45rem;
  --turn-card-width: 22rem;
  position: relative;
  display: grid;
  grid-template-columns: var(--turn-rail-width) minmax(0, 1fr);
  min-width: 0;
  min-height: 0;
  flex: 1;
  background: var(--color-bg-app);
  border-radius: 1.5rem;
}
.chat-turn-reading__scroll {
  min-width: 0;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior-y: contain;
  padding: 1rem 1rem 1.5rem;
}
.chat-turn-rail {
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding-block: 0.75rem;
}
.chat-turn-rail__list {
  position: relative;
  min-height: 0;
  margin: 0;
  padding: 0;
  list-style: none;
  overflow-y: auto;
  overscroll-behavior-y: contain;
  scrollbar-width: thin;
}
.chat-turn-rail__list::before {
  content: '';
  position: absolute;
  inset-block: 0.65rem;
  inset-inline-start: 1.1rem;
  width: 1px;
  background: var(--color-border-paper);
  pointer-events: none;
}
.chat-turn-rail__item {
  position: relative;
  display: grid;
  place-items: center;
  width: 100%;
  min-height: 2.5rem;
  padding: 0;
  border: 0;
  border-radius: 0.5rem;
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
}
.chat-turn-rail__mark {
  width: 0.55rem;
  height: 2px;
  border-radius: 999px;
  background: currentColor;
  transition: width 140ms ease, height 140ms ease;
}
.chat-turn-rail__item:hover,
.chat-turn-rail__item:focus-visible { background: var(--color-bg-hover); color: var(--color-text-primary); }
.chat-turn-rail__item[aria-current='location'] { color: var(--color-action-primary); }
.chat-turn-rail__item[aria-current='location'] .chat-turn-rail__mark { width: 1rem; height: 3px; }
.chat-turn-rail__item:focus-visible { outline: 2px solid var(--color-border-focus); outline-offset: -2px; }
.chat-turn-rail__coverage { margin: 0; padding: 0.35rem; color: var(--color-text-secondary); font-size: 0.68rem; line-height: 1.3; }
.chat-turn-preview {
  position: absolute;
  z-index: 2;
  inset-inline-start: calc(var(--turn-rail-width) + var(--turn-card-gap));
  width: min(var(--turn-card-width), calc(100% - var(--turn-rail-width) - 1rem));
  max-height: min(18rem, calc(100% - 1rem));
  overflow: auto;
  box-sizing: border-box;
  padding: 0.8rem 0.9rem;
  border: 1px solid var(--color-border-paper);
  border-radius: 0.85rem;
  background: var(--color-bg-surface-solid);
  box-shadow: 0 10px 28px var(--color-shadow-medium);
  color: var(--color-text-body);
  font-family: var(--font-family-ui);
  line-height: 1.5;
}
.chat-turn-preview__eyebrow { color: var(--color-text-muted); font-size: 0.7rem; }
.chat-turn-preview__user,
.chat-turn-preview__answer { display: -webkit-box; overflow: hidden; -webkit-box-orient: vertical; overflow-wrap: anywhere; margin: 0.35rem 0 0; }
.chat-turn-preview__user { -webkit-line-clamp: 2; color: var(--color-text-primary); font-size: 0.85rem; font-weight: 600; }
.chat-turn-preview__answer { -webkit-line-clamp: 3; color: var(--color-text-secondary); font-size: 0.78rem; }
.chat-turn-message--located { outline: 2px solid var(--color-border-focus); outline-offset: 3px; }
@media (prefers-reduced-motion: reduce) {
  .chat-turn-rail__mark { transition: none; }
}
```

`previewTop` 按所指按钮相对阅读区的纵坐标计算，并夹在阅读区上下边界内；卡片的实际尺寸由测量结果决定，不能仅靠固定 `top`。卡片与消息滚动层同级，所以不会被原 `overflow-x: hidden` 裁掉。卡片绝不能延伸到阅读区下方的 `AIInputDock`。顶部过近时下移、底部过近时上移；阅读区高度短时卡片内部滚动。右侧历史面板展开仅改变阅读区实际宽度，卡片使用容器宽度重新排版。

## 手机与窄容器状态

当 `ChatPanel` 实际消息区宽度约 `31rem` 以下，改为展开式入口。使用容器宽度判断，因侧边任务会话即使在桌面屏幕上也可能很窄。桌面轨道与手机列表只呈现同一份 `items`；不生成不同的数据规则。展开列表位于阅读区内、输入 Dock 上方，不覆盖底部 Chat／Dream／Decks／More 导航。选择一行后收起列表，再在既有消息滚动区定位；展开本身不滚动原消息区。

```tsx
<div className="chat-turn-mobile">
  <button type="button" className="chat-turn-mobile__toggle" aria-expanded={isOpen} aria-controls="chat-turn-mobile-list" onClick={toggleOpen}>
    {t('chat.turnNavigation.mobileLabel')}
    <span aria-hidden="true">{isOpen ? '▴' : '▾'}</span>
  </button>
  {isOpen ? (
    <ol id="chat-turn-mobile-list" className="chat-turn-mobile__list">
      {items.map((item, index) => (
        <li key={item.messageId}>
          <button type="button" aria-current={activeMessageId === item.messageId ? 'location' : undefined} onClick={() => onNavigate(item.messageId)}>
            <span className="chat-turn-mobile__number">{index + 1}</span>
            <span className="chat-turn-mobile__copy">
              <strong>{item.userPreview}</strong>
              <span>{item.answerPreview ?? item.statusLabel}</span>
            </span>
          </button>
        </li>
      ))}
    </ol>
  ) : null}
</div>
```

```css
.chat-turn-mobile { display: none; }
@container chat-turn-reading (max-width: 31rem) {
  .chat-turn-reading { display: flex; flex-direction: column; }
  .chat-turn-rail, .chat-turn-preview { display: none; }
  .chat-turn-mobile { display: block; flex: none; min-width: 0; padding: 0.45rem 0.65rem 0; }
  .chat-turn-mobile__toggle { min-height: 2.75rem; width: 100%; border: 1px solid var(--color-border-paper); border-radius: 0.65rem; background: var(--color-bg-surface-solid); color: var(--color-text-primary); font: inherit; text-align: start; padding: 0.5rem 0.7rem; }
  .chat-turn-mobile__toggle:focus-visible,
  .chat-turn-mobile__list button:focus-visible { outline: 2px solid var(--color-border-focus); outline-offset: 2px; }
  .chat-turn-mobile__list { max-height: min(42vh, 18rem); margin: 0.4rem 0 0; padding: 0; overflow-y: auto; list-style: none; border: 1px solid var(--color-border-paper); border-radius: 0.65rem; background: var(--color-bg-surface-solid); }
  .chat-turn-mobile__list button { display: flex; align-items: flex-start; gap: 0.65rem; width: 100%; min-height: 2.75rem; border: 0; border-bottom: 1px solid var(--color-border-neutral); background: transparent; color: var(--color-text-body); font: inherit; text-align: start; padding: 0.65rem 0.75rem; }
  .chat-turn-mobile__list button[aria-current='location'] { background: var(--color-bg-active); }
  .chat-turn-mobile__number { flex: none; color: var(--color-text-secondary); font-size: 0.75rem; }
  .chat-turn-mobile__copy { display: grid; min-width: 0; gap: 0.2rem; }
  .chat-turn-mobile__copy strong,
  .chat-turn-mobile__copy span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .chat-turn-mobile__copy strong { color: var(--color-text-primary); font-size: 0.82rem; }
  .chat-turn-mobile__copy span { color: var(--color-text-secondary); font-size: 0.72rem; }
}
```

> CSS 片段是视觉示意。命名容器放在 `.chat-turn-reading-container`，被查询的 `.chat-turn-reading` 是它的子元素，容器查询才能生效。展开列表的最大高度是为了给消息正文保留可读空间，若极矮窗口仍不足，列表应在阅读区内滚动。

## 微交互与状态呈现

| 事件／状态 | 视觉反馈 | 操作和无障碍要求 |
| --- | --- | --- |
| 进入无历史 Thread | 无轨道／无手机入口 | 不留下空白装饰列。 |
| 索引或历史加载中 | 轨道位置出现简短加载文字；不画假刻度 | 现有消息仍可读；不用无限循环动效。 |
| 指针悬浮／键盘聚焦 | 当前按钮浅底、刻度稍伸长；卡片在右侧 `120–160ms` 淡入 | 打开卡片不滚动消息；焦点轮廓始终清晰。 |
| 移开／Escape | 卡片关闭，刻度回原状态 | 指针进入卡片期间维持打开；Escape 不取消原消息或草稿。 |
| 激活导航 | 当前刻度变长；目标用户消息进入可读区域并短暂强调 | 原滚动区定位；Enter／Space 与点击等价；焦点留在导航按钮。 |
| 用户自行滚动 | 当前刻度随主要可见用户消息切换 | 不强行改滚动位置，不反复闪动。 |
| 进行中 | 卡片次行写“正在回复” | 回复文本到达时更新同一卡片；不新增刻度。 |
| 无回复／失败／待核对 | 分别写“暂无回复”“本轮失败”“状态待核对” | 失败只在已有回执确认后展示；SSE 暂断不推断失败。 |
| 定位历史中／失败 | 卡片附近写“正在定位”或“暂时无法定位”，失败时提供“重试” | 失败时原消息位置不动；较早请求不能覆盖新目标。 |
| 索引范围不完整 | 轨道底部或手机列表顶部写“仅显示已加载消息” | 不把已加载项说成完整 Thread。 |
| 纯附件／摘要无法构造 | 显示附件名／“已发送附件”；必要时写“摘要暂不可用” | 仍允许定位，不编造正文。 |

动画仅用于减少视觉突变：

```css
@keyframes chat-turn-preview-in {
  from { opacity: 0; transform: translateY(3px); }
  to { opacity: 1; transform: translateY(0); }
}
.chat-turn-preview { animation: chat-turn-preview-in 140ms ease-out both; }
@media (prefers-reduced-motion: reduce) {
  .chat-turn-preview { animation: none; }
  .chat-turn-reading__scroll { scroll-behavior: auto; }
}
```

## 视觉验收点

1. 亮色与暗色均从 `tokens.css` 取语义色；字体继承现有 UI 字体；不含截图产品的蓝色气泡、黑灰侧栏、红框或书签动作。
2. 三条已发送用户消息只对应三条刻度；其中当前项除颜色外还通过长度／粗细区分。纯附件项有可读文本预览。
3. 在主 Chat、右侧历史展开、侧边任务聊天和约 `390px` 手机宽度下，正文无页面级横向滚动，浮卡或展开列表不盖住输入 Dock。
4. 键盘 Tab 能到达每个项，聚焦可读摘要，Enter／Space 定位，Escape 关闭；读屏能获知顺序、当前位置和实际回复状态。
5. 预览文字溢出时折行／截断，不渲染 Markdown 链接或执行消息内容；用户通过原消息阅读完整内容。
