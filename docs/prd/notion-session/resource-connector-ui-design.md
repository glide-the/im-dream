## ✨ 总体视觉风格（Aesthetic Style）

| 维度 | 设计定义 |
| --- | --- |
| 风格关键词 | 暖纸张、手写感、安静工具台、资料贴签、低饱和编辑台 |
| 视觉气质 | 像一本被轻轻摊开的研究手账：留白充足、边界柔和、信息层级克制，强调“整理资源后再开始思考”的安静秩序。 |
| 光影策略 | 使用极浅阴影、纸边高光、虚线边框与雾面卡片，不做强烈玻璃拟态，避免打断阅读节奏。 |
| 排版策略 | 标题采用 **Noto Serif SC** 增加书卷感，正文与操作采用 **Noto Sans SC**，形成“文档感 + 工具感”的双重语气。 |
| 色彩策略 | Light 模式以米白、奶油、暖灰、墨棕为主；Dark 模式保留暖感，转为深炭褐、烟灰、柔米白，避免冰冷蓝黑。 |
| 交互策略 | 所有反馈都控制在轻量级：悬停上浮 1~2px、边框加深、按钮产生柔和墨色涟漪，强调“可操作但不喧哗”。 |

---

## 🧩 UI 组件结构（Component Structure）

| 模块 | 名称 | 作用 | 关键视觉表现 |
| --- | --- | --- | --- |
| RC-A | ConnectorHeader | 显示连接器身份，并承载分享、更多菜单、主题切换 | 顶部单行、纸张标签式标题、细边按钮 |
| RC-B | ChatInputBar | 发起新聊天，控制模型、语音与发送 | 大圆角输入槽、内嵌工具按钮、暖底描边 |
| RC-C | TabSwitch | 切换“聊天 / 来源”主视图 | 手账胶囊标签、当前态有底色与内阴影 |
| RC-D | EmptySourcePanel | 在无来源时解释价值并给出 CTA | 大面积虚线框、居中图标组、卡片纸板感 |
| RC-E | SourceList | 展示已接入来源与同步状态 | 纵向资源卡、状态胶囊、细分隔线 |
| RC-F | ChatList | 展示历史对话与时间线 | 轻量列表卡、时间标记、摘要层级 |
| RC-G | AddSourceModal | 选择来源接入方式 | 底部 ActionSheet、三类来源入口、柔和遮罩 |

---

## 🎨 CSS Variables 色彩系统

```css
:root {
  --paper-bg: #f6f0e6;
  --paper-panel: rgba(255, 250, 242, 0.9);
  --paper-card: #fffaf2;
  --paper-card-strong: #f2e8d8;
  --paper-border: rgba(114, 92, 72, 0.18);
  --paper-border-strong: rgba(114, 92, 72, 0.32);
  --paper-text: #3f3429;
  --paper-text-soft: #7a6a59;
  --paper-accent: #5f4a36;
  --paper-accent-soft: #d9c6ad;
  --paper-success: #7e9468;
  --paper-warning: #c78855;
  --paper-danger: #a86652;
  --paper-shadow: 0 18px 40px rgba(106, 83, 58, 0.08);
}

html[data-theme='dark'] {
  --paper-bg: #1d1916;
  --paper-panel: rgba(43, 37, 33, 0.92);
  --paper-card: #2a241f;
  --paper-card-strong: #342d27;
  --paper-border: rgba(222, 206, 186, 0.12);
  --paper-border-strong: rgba(222, 206, 186, 0.26);
  --paper-text: #f3e8d8;
  --paper-text-soft: #b7a894;
  --paper-accent: #ead8bd;
  --paper-accent-soft: #544739;
  --paper-success: #9db487;
  --paper-warning: #e2a674;
  --paper-danger: #cd8b78;
  --paper-shadow: 0 20px 48px rgba(0, 0, 0, 0.28);
}
```

---

## 🎞 微交互定义（Micro-interactions）

| 交互对象 | 触发方式 | 反馈定义 |
| --- | --- | --- |
| 顶栏按钮 | Hover / Focus | 背景由透明过渡为纸卡底色，边框略微加深，整体上浮 1px。 |
| 输入框容器 | Focus within | 外圈出现暖棕色柔和 ring，阴影略加深，强化“可以开始提问”的入口感。 |
| Tab 标签 | Switch | 胶囊背景在 180ms 内滑入，未选中态文字降低对比度。 |
| 空状态按钮 | Hover | 轻微上浮并出现更深纸影，箭头图标向右移动 2px。 |
| 来源卡片 | Hover | 卡片整体上移 2px，标题变深，右上角状态标签更清晰。 |
| ActionSheet | Open / Close | 遮罩淡入，底部面板由下向上平滑滑入，关闭时反向执行。 |
| 深色模式 | Toggle | 页面变量切换并带 220ms 颜色过渡，不闪屏。 |

---

## 💻 单文件 HTML + Tailwind 实现

```html
<!DOCTYPE html>
<html lang="zh-CN" data-theme="light">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>资源连接器 · Warm Paper Workbench</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;500;600;700&family=Noto+Sans+SC:wght@300;400;500;700&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="https://lf6-cdn-tos.bytecdntp.com/cdn/expire-100-M/font-awesome/6.0.0/css/all.min.css" />
  <link rel="stylesheet" href="https://lf3-cdn-tos.bytecdntp.com/cdn/expire-1-M/tailwindcss/2.2.19/tailwind.min.css" />
  <style>
    :root {
      --paper-bg: #f6f0e6;
      --paper-panel: rgba(255, 250, 242, 0.9);
      --paper-card: #fffaf2;
      --paper-card-strong: #f2e8d8;
      --paper-border: rgba(114, 92, 72, 0.18);
      --paper-border-strong: rgba(114, 92, 72, 0.32);
      --paper-text: #3f3429;
      --paper-text-soft: #7a6a59;
      --paper-accent: #5f4a36;
      --paper-accent-soft: #d9c6ad;
      --paper-success: #7e9468;
      --paper-warning: #c78855;
      --paper-danger: #a86652;
      --paper-shadow: 0 18px 40px rgba(106, 83, 58, 0.08);
      --paper-ring: rgba(95, 74, 54, 0.16);
    }

    html[data-theme='dark'] {
      --paper-bg: #1d1916;
      --paper-panel: rgba(43, 37, 33, 0.92);
      --paper-card: #2a241f;
      --paper-card-strong: #342d27;
      --paper-border: rgba(222, 206, 186, 0.12);
      --paper-border-strong: rgba(222, 206, 186, 0.26);
      --paper-text: #f3e8d8;
      --paper-text-soft: #b7a894;
      --paper-accent: #ead8bd;
      --paper-accent-soft: #544739;
      --paper-success: #9db487;
      --paper-warning: #e2a674;
      --paper-danger: #cd8b78;
      --paper-shadow: 0 20px 48px rgba(0, 0, 0, 0.28);
      --paper-ring: rgba(234, 216, 189, 0.12);
    }

    * { box-sizing: border-box; }
    html, body { min-height: 100%; }
    body {
      margin: 0;
      font-family: 'Noto Sans SC', sans-serif;
      color: var(--paper-text);
      background:
        radial-gradient(circle at top left, rgba(212, 191, 164, 0.18), transparent 28%),
        radial-gradient(circle at bottom right, rgba(185, 164, 136, 0.14), transparent 26%),
        var(--paper-bg);
      transition: background-color .22s ease, color .22s ease;
      position: relative;
      overflow-x: hidden;
    }

    body::before {
      content: '';
      position: fixed;
      inset: 0;
      pointer-events: none;
      opacity: .35;
      background-image:
        linear-gradient(rgba(255,255,255,.04) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,.03) 1px, transparent 1px);
      background-size: 28px 28px;
      mix-blend-mode: soft-light;
    }

    .serif { font-family: 'Noto Serif SC', serif; }
    .paper-shell {
      background: var(--paper-panel);
      border: 1px solid var(--paper-border);
      box-shadow: var(--paper-shadow);
      backdrop-filter: blur(14px);
    }

    .paper-card {
      background: var(--paper-card);
      border: 1px solid var(--paper-border);
      box-shadow: 0 10px 24px rgba(102, 78, 52, 0.06);
    }

    .paper-muted {
      color: var(--paper-text-soft);
    }

    .paper-btn,
    .paper-tab,
    .paper-card,
    .paper-input,
    .paper-chip {
      transition: transform .18s ease, background-color .22s ease, border-color .22s ease, box-shadow .22s ease, color .22s ease, opacity .22s ease;
    }

    .paper-btn:hover,
    .paper-tab:hover,
    .paper-card:hover,
    .paper-chip:hover {
      transform: translateY(-1px);
    }

    .paper-btn:focus-visible,
    .paper-tab:focus-visible,
    .paper-chip:focus-visible,
    .menu-item:focus-visible,
    .source-option:focus-visible,
    .input-action:focus-visible {
      outline: none;
      box-shadow: 0 0 0 4px var(--paper-ring);
    }

    .paper-input {
      background: rgba(255,255,255,.32);
      border: 1px solid var(--paper-border);
    }

    .paper-input:focus-within {
      border-color: var(--paper-border-strong);
      box-shadow: 0 0 0 4px var(--paper-ring), 0 14px 32px rgba(91, 69, 44, 0.08);
    }

    .paper-tab.is-active,
    .paper-chip.is-active {
      background: var(--paper-card);
      border-color: var(--paper-border-strong);
      color: var(--paper-text);
      box-shadow: inset 0 1px 0 rgba(255,255,255,.45), 0 8px 22px rgba(91, 69, 44, 0.08);
    }

    .soft-divider {
      border-color: var(--paper-border);
    }

    .icon-tile {
      width: 3.25rem;
      height: 3.25rem;
      border-radius: 1rem;
      background: linear-gradient(180deg, rgba(255,255,255,.72), rgba(230,214,192,.58));
      border: 1px solid var(--paper-border);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      color: var(--paper-accent);
      box-shadow: inset 0 1px 0 rgba(255,255,255,.65);
    }

    html[data-theme='dark'] .icon-tile {
      background: linear-gradient(180deg, rgba(80,68,57,.9), rgba(56,47,40,.92));
    }

    .status-dot {
      width: .5rem;
      height: .5rem;
      border-radius: 9999px;
      display: inline-block;
    }

    .sheet-overlay {
      background: rgba(44, 33, 26, 0.36);
      opacity: 0;
      pointer-events: none;
      transition: opacity .22s ease;
    }

    .sheet-panel {
      transform: translateY(110%);
      transition: transform .28s cubic-bezier(.22, 1, .36, 1);
    }

    .sheet-overlay.open {
      opacity: 1;
      pointer-events: auto;
    }

    .sheet-overlay.open .sheet-panel {
      transform: translateY(0);
    }

    .fade-in {
      animation: fadeInUp .55s ease both;
    }

    @keyframes fadeInUp {
      from { opacity: 0; transform: translateY(18px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .menu-panel {
      opacity: 0;
      transform: translateY(8px);
      pointer-events: none;
      transition: opacity .18s ease, transform .18s ease;
    }

    .menu-panel.open {
      opacity: 1;
      transform: translateY(0);
      pointer-events: auto;
    }

    .source-option:hover {
      border-color: var(--paper-border-strong);
      background: var(--paper-card-strong);
    }

    .line-clamp-2 {
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }

    @media (max-width: 768px) {
      .mobile-stack {
        flex-direction: column;
        align-items: stretch;
      }
    }
  </style>
</head>
<body>
  <main class="px-4 py-6 sm:px-6 lg:px-10">
    <div class="mx-auto max-w-5xl rounded-[2rem] paper-shell fade-in">
      <div class="border-b soft-divider px-5 py-4 sm:px-7 sm:py-5">
        <div class="flex mobile-stack gap-4 sm:items-center sm:justify-between">
          <div class="flex items-center gap-3 min-w-0">
            <button class="paper-btn h-11 w-11 rounded-2xl inline-flex items-center justify-center" style="background: var(--paper-card); border: 1px solid var(--paper-border);" aria-label="返回连接器列表">
              <i class="fa-solid fa-chevron-left text-sm"></i>
            </button>
            <div class="icon-tile"><i class="fa-solid fa-paperclip"></i></div>
            <div class="min-w-0">
              <p class="text-xs tracking-[0.22em] uppercase paper-muted mb-1">Resource Connector</p>
              <div class="flex items-center gap-2 min-w-0">
                <h1 id="connectorNameText" class="serif text-2xl sm:text-3xl font-semibold truncate cursor-text">资源连接器</h1>
                <input id="connectorNameInput" class="hidden rounded-2xl px-3 py-2 text-lg sm:text-xl font-medium paper-input bg-transparent w-56 sm:w-72" value="资源连接器" aria-label="编辑连接器名称" />
                <button id="editNameBtn" class="paper-btn h-9 w-9 rounded-xl inline-flex items-center justify-center" style="background: var(--paper-card); border: 1px solid var(--paper-border);" aria-label="编辑连接器名称">
                  <i class="fa-solid fa-pen-to-square text-sm"></i>
                </button>
              </div>
            </div>
          </div>

          <div class="flex items-center gap-2 self-start sm:self-auto">
            <button class="paper-btn rounded-2xl px-4 h-11 inline-flex items-center gap-2" style="background: var(--paper-card); border: 1px solid var(--paper-border);" aria-label="分享连接器">
              <i class="fa-solid fa-arrow-up-from-bracket text-sm"></i>
              <span class="text-sm">分享</span>
            </button>
            <button id="themeToggle" class="paper-btn h-11 w-11 rounded-2xl inline-flex items-center justify-center" style="background: var(--paper-card); border: 1px solid var(--paper-border);" aria-label="切换明暗模式">
              <i class="fa-solid fa-moon text-sm"></i>
            </button>
            <div class="relative">
              <button id="moreBtn" class="paper-btn h-11 w-11 rounded-2xl inline-flex items-center justify-center" style="background: var(--paper-card); border: 1px solid var(--paper-border);" aria-label="更多菜单">
                <i class="fa-solid fa-ellipsis text-sm"></i>
              </button>
              <div id="moreMenu" class="menu-panel absolute right-0 mt-2 w-48 rounded-2xl p-2 paper-card z-20">
                <button class="menu-item w-full text-left rounded-xl px-3 py-2 text-sm">重命名连接器</button>
                <button class="menu-item w-full text-left rounded-xl px-3 py-2 text-sm">复制连接器</button>
                <button class="menu-item w-full text-left rounded-xl px-3 py-2 text-sm">归档</button>
                <button class="menu-item w-full text-left rounded-xl px-3 py-2 text-sm" style="color: var(--paper-danger);">删除</button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="px-5 pt-5 sm:px-7 sm:pt-6">
        <section class="paper-input rounded-[1.75rem] p-4 sm:p-5">
          <div class="flex mobile-stack gap-4 sm:items-end">
            <div class="flex-1 min-w-0">
              <div class="flex items-start gap-3">
                <button class="paper-btn input-action mt-1 h-10 w-10 flex-shrink-0 rounded-2xl inline-flex items-center justify-center" style="background: var(--paper-card); border: 1px solid var(--paper-border);" aria-label="添加附件">
                  <i class="fa-solid fa-plus text-sm"></i>
                </button>
                <div class="flex-1">
                  <label for="chatInput" class="block text-xs tracking-[0.18em] uppercase paper-muted mb-2">在资源连接器中开启新聊天</label>
                  <textarea id="chatInput" rows="3" class="w-full resize-none bg-transparent outline-none text-sm sm:text-base leading-7" style="color: var(--paper-text);" placeholder="你可以直接提问、总结来源、比对文档，或让 Agent 基于已接入资源生成分析。"></textarea>
                </div>
              </div>
            </div>
            <div class="flex items-center gap-2 sm:pl-4">
              <button class="paper-btn rounded-2xl px-4 h-11 inline-flex items-center gap-2" style="background: var(--paper-card); border: 1px solid var(--paper-border);" aria-label="选择模型">
                <i class="fa-solid fa-sparkles text-xs"></i>
                <span class="text-sm">Claude 4.5</span>
                <i class="fa-solid fa-chevron-down text-xs opacity-60"></i>
              </button>
              <button class="paper-btn input-action h-11 w-11 rounded-2xl inline-flex items-center justify-center" style="background: var(--paper-card); border: 1px solid var(--paper-border);" aria-label="语音输入">
                <i class="fa-solid fa-microphone-lines text-sm"></i>
              </button>
              <button id="sendBtn" class="paper-btn rounded-2xl px-5 h-11 inline-flex items-center gap-2" style="background: var(--paper-accent); color: var(--paper-bg); border: 1px solid transparent; opacity: .55;" aria-label="发送消息">
                <span class="text-sm">发送</span>
                <i class="fa-solid fa-arrow-up text-xs"></i>
              </button>
            </div>
          </div>
        </section>
      </div>

      <div class="px-5 py-5 sm:px-7 sm:py-6">
        <div class="flex mobile-stack gap-3 sm:items-center sm:justify-between mb-5">
          <div class="inline-flex rounded-full p-1 paper-card">
            <button data-tab="chat" class="paper-tab rounded-full px-5 py-2 text-sm paper-muted" aria-controls="chatPanel">聊天</button>
            <button data-tab="source" class="paper-tab is-active rounded-full px-5 py-2 text-sm" aria-controls="sourcePanel">来源</button>
          </div>

          <div id="sourceToolbar" class="flex flex-wrap items-center gap-2">
            <button class="paper-chip is-active rounded-full px-4 py-2 text-sm" style="background: var(--paper-card); border: 1px solid var(--paper-border);">最近更新</button>
            <button class="paper-chip rounded-full px-4 py-2 text-sm paper-muted" style="background: transparent; border: 1px solid var(--paper-border);">Notion</button>
            <div class="inline-flex rounded-full p-1 paper-card ml-0 sm:ml-2">
              <button data-source-view="empty" class="paper-chip is-active rounded-full px-4 py-2 text-sm">空状态</button>
              <button data-source-view="filled" class="paper-chip rounded-full px-4 py-2 text-sm paper-muted">已连接</button>
            </div>
          </div>
        </div>

        <section id="sourcePanel" class="space-y-4">
          <div id="sourceEmptyState" class="paper-card rounded-[2rem] border-2 border-dashed px-6 py-10 sm:px-10 sm:py-14 text-center">
            <div class="flex justify-center gap-3 mb-6">
              <span class="icon-tile"><i class="fa-solid fa-link"></i></span>
              <span class="icon-tile"><i class="fa-solid fa-file-lines"></i></span>
              <span class="icon-tile"><i class="fa-solid fa-layer-group"></i></span>
            </div>
            <p class="serif text-2xl sm:text-3xl font-semibold mb-3">先把资料轻轻放上工作台</p>
            <p class="max-w-2xl mx-auto text-sm sm:text-base leading-7 paper-muted mb-8">
              添加网页、文件、Notion 或 Deck 之后，Agent 会在当前连接器里理解你的背景资料、归档上下文，并让后续每一段对话都更有依据。
            </p>
            <button id="openSourceModalFromEmpty" class="paper-btn inline-flex items-center gap-3 rounded-full px-6 py-3 text-sm sm:text-base" style="background: var(--paper-accent); color: var(--paper-bg); box-shadow: 0 12px 30px rgba(93, 71, 47, 0.18);" aria-label="添加来源">
              <i class="fa-solid fa-plus"></i>
              <span>添加来源</span>
              <i class="fa-solid fa-arrow-right text-xs"></i>
            </button>
          </div>

          <div id="sourceFilledState" class="hidden space-y-4">
            <article class="paper-card rounded-[1.6rem] p-5 sm:p-6">
              <div class="flex mobile-stack gap-4 sm:items-start sm:justify-between">
                <div class="min-w-0">
                  <div class="flex flex-wrap items-center gap-3 mb-2">
                    <span class="inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs" style="background: var(--paper-card-strong); color: var(--paper-accent); border: 1px solid var(--paper-border);">
                      <i class="fa-solid fa-note-sticky"></i>
                      <span>🔗 Notion</span>
                    </span>
                    <span class="inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs" style="background: rgba(126, 148, 104, 0.12); color: var(--paper-success); border: 1px solid rgba(126, 148, 104, 0.25);">
                      <span class="status-dot" style="background: var(--paper-success);"></span>
                      已同步
                    </span>
                  </div>
                  <h3 class="serif text-xl font-semibold mb-2">品牌研究资料库</h3>
                  <p class="paper-muted text-sm leading-7 line-clamp-2">包含品牌资产、采访纪要、竞品观察与内容日历，共 24 页内容，最近同步于今天 14:25。</p>
                </div>
                <div class="flex items-center gap-2">
                  <span class="rounded-full px-3 py-2 text-xs paper-muted" style="background: var(--paper-card-strong); border: 1px solid var(--paper-border);">24 pages</span>
                  <button class="paper-btn rounded-full px-4 py-2 text-sm" style="background: var(--paper-card); border: 1px solid var(--paper-border);">查看</button>
                </div>
              </div>
            </article>

            <article class="paper-card rounded-[1.6rem] p-5 sm:p-6">
              <div class="flex mobile-stack gap-4 sm:items-start sm:justify-between">
                <div class="min-w-0">
                  <div class="flex flex-wrap items-center gap-3 mb-2">
                    <span class="inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs" style="background: var(--paper-card-strong); color: var(--paper-accent); border: 1px solid var(--paper-border);">
                      <i class="fa-solid fa-note-sticky"></i>
                      <span>🔗 Notion</span>
                    </span>
                    <span class="inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs" style="background: rgba(199, 136, 85, 0.12); color: var(--paper-warning); border: 1px solid rgba(199, 136, 85, 0.25);">
                      <span class="status-dot" style="background: var(--paper-warning);"></span>
                      同步中
                    </span>
                  </div>
                  <h3 class="serif text-xl font-semibold mb-2">用户访谈摘录 / Q2</h3>
                  <p class="paper-muted text-sm leading-7 line-clamp-2">设计团队与研究团队联合维护的访谈笔记，当前导入到第 12 页，预计 2 分钟后完成。</p>
                </div>
                <div class="flex items-center gap-2">
                  <span class="rounded-full px-3 py-2 text-xs paper-muted" style="background: var(--paper-card-strong); border: 1px solid var(--paper-border);">12 / 18 pages</span>
                  <button class="paper-btn rounded-full px-4 py-2 text-sm" style="background: var(--paper-card); border: 1px solid var(--paper-border);">重试</button>
                </div>
              </div>
            </article>

            <article class="paper-card rounded-[1.6rem] p-5 sm:p-6">
              <div class="flex mobile-stack gap-4 sm:items-start sm:justify-between">
                <div class="min-w-0">
                  <div class="flex flex-wrap items-center gap-3 mb-2">
                    <span class="inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs" style="background: var(--paper-card-strong); color: var(--paper-accent); border: 1px solid var(--paper-border);">
                      <i class="fa-solid fa-note-sticky"></i>
                      <span>🔗 Notion</span>
                    </span>
                    <span class="inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs" style="background: rgba(168, 102, 82, 0.12); color: var(--paper-danger); border: 1px solid rgba(168, 102, 82, 0.25);">
                      <span class="status-dot" style="background: var(--paper-danger);"></span>
                      需要授权
                    </span>
                  </div>
                  <h3 class="serif text-xl font-semibold mb-2">Campaign Archive 2024</h3>
                  <p class="paper-muted text-sm leading-7 line-clamp-2">历史 campaign 回顾资料，包含复盘、投放截图与关键结论；账号令牌已过期，需要重新连接。</p>
                </div>
                <div class="flex items-center gap-2">
                  <span class="rounded-full px-3 py-2 text-xs paper-muted" style="background: var(--paper-card-strong); border: 1px solid var(--paper-border);">31 pages</span>
                  <button id="openSourceModalFromList" class="paper-btn rounded-full px-4 py-2 text-sm" style="background: var(--paper-card); border: 1px solid var(--paper-border);">重新连接</button>
                </div>
              </div>
            </article>
          </div>
        </section>

        <section id="chatPanel" class="hidden space-y-3">
          <article class="paper-card rounded-[1.5rem] p-5 sm:p-6">
            <div class="flex items-start justify-between gap-4">
              <div>
                <p class="text-xs tracking-[0.18em] uppercase paper-muted mb-2">今天 14:32</p>
                <h3 class="serif text-xl font-semibold mb-2">请基于品牌研究资料库整理三段式首页叙事</h3>
                <p class="paper-muted text-sm leading-7">最后一条消息：已综合 Notion 中的品牌语调、目标受众与竞品分析，建议采用“起笔 / 证据 / 收束”三段叙事结构。</p>
              </div>
              <button class="paper-btn rounded-full px-4 py-2 text-sm" style="background: var(--paper-card); border: 1px solid var(--paper-border);">继续</button>
            </div>
          </article>

          <article class="paper-card rounded-[1.5rem] p-5 sm:p-6">
            <div class="flex items-start justify-between gap-4">
              <div>
                <p class="text-xs tracking-[0.18em] uppercase paper-muted mb-2">昨天 19:08</p>
                <h3 class="serif text-xl font-semibold mb-2">从用户访谈中提炼 5 个反复出现的情绪词</h3>
                <p class="paper-muted text-sm leading-7">最后一条消息：高频情绪词包括“安心、效率、被理解、克制、可信”，并附有对应访谈片段。</p>
              </div>
              <button class="paper-btn rounded-full px-4 py-2 text-sm" style="background: var(--paper-card); border: 1px solid var(--paper-border);">继续</button>
            </div>
          </article>

          <article class="paper-card rounded-[1.5rem] p-5 sm:p-6">
            <div class="flex items-start justify-between gap-4">
              <div>
                <p class="text-xs tracking-[0.18em] uppercase paper-muted mb-2">06/29 10:14</p>
                <h3 class="serif text-xl font-semibold mb-2">比较 2024 Campaign Archive 与当前提案的视觉偏移</h3>
                <p class="paper-muted text-sm leading-7">最后一条消息：当前提案较历史项目更柔和、信息密度更低，建议保留手写感标题作为品牌锚点。</p>
              </div>
              <button class="paper-btn rounded-full px-4 py-2 text-sm" style="background: var(--paper-card); border: 1px solid var(--paper-border);">继续</button>
            </div>
          </article>
        </section>
      </div>
    </div>
  </main>

  <div id="sourceSheet" class="sheet-overlay fixed inset-0 z-40 flex items-end justify-center px-4 pb-4 sm:px-6 sm:pb-6">
    <div class="sheet-panel w-full max-w-2xl rounded-[2rem] paper-shell overflow-hidden">
      <div class="border-b soft-divider px-5 py-4 sm:px-6 flex items-center justify-between">
        <div>
          <p class="text-xs tracking-[0.2em] uppercase paper-muted mb-1">Add Source</p>
          <h2 class="serif text-2xl font-semibold">选择一种来源接入方式</h2>
        </div>
        <button id="closeSheetBtn" class="paper-btn h-10 w-10 rounded-2xl inline-flex items-center justify-center" style="background: var(--paper-card); border: 1px solid var(--paper-border);" aria-label="关闭添加来源面板">
          <i class="fa-solid fa-xmark"></i>
        </button>
      </div>
      <div class="p-5 sm:p-6 space-y-3">
        <button class="source-option w-full rounded-[1.4rem] paper-card p-4 text-left">
          <div class="flex items-center justify-between gap-4">
            <div class="flex items-center gap-4">
              <span class="icon-tile"><i class="fa-solid fa-note-sticky"></i></span>
              <div>
                <p class="text-base font-medium">Notion</p>
                <p class="paper-muted text-sm mt-1">连接知识库、页面数据库与团队文档。</p>
              </div>
            </div>
            <i class="fa-solid fa-chevron-right paper-muted"></i>
          </div>
        </button>

        <button class="source-option w-full rounded-[1.4rem] paper-card p-4 text-left">
          <div class="flex items-center justify-between gap-4">
            <div class="flex items-center gap-4">
              <span class="icon-tile"><i class="fa-solid fa-file-arrow-up"></i></span>
              <div>
                <p class="text-base font-medium">File</p>
                <p class="paper-muted text-sm mt-1">上传 PDF、DOCX、TXT、CSV 或图片素材。</p>
              </div>
            </div>
            <i class="fa-solid fa-chevron-right paper-muted"></i>
          </div>
        </button>

        <button class="source-option w-full rounded-[1.4rem] paper-card p-4 text-left">
          <div class="flex items-center justify-between gap-4">
            <div class="flex items-center gap-4">
              <span class="icon-tile"><i class="fa-solid fa-layer-group"></i></span>
              <div>
                <p class="text-base font-medium">Deck</p>
                <p class="paper-muted text-sm mt-1">导入演示稿、研究 deck 与章节化资料集。</p>
              </div>
            </div>
            <i class="fa-solid fa-chevron-right paper-muted"></i>
          </div>
        </button>
      </div>
    </div>
  </div>

  <script>
    const htmlEl = document.documentElement;
    const themeToggle = document.getElementById('themeToggle');
    const editNameBtn = document.getElementById('editNameBtn');
    const connectorNameText = document.getElementById('connectorNameText');
    const connectorNameInput = document.getElementById('connectorNameInput');
    const moreBtn = document.getElementById('moreBtn');
    const moreMenu = document.getElementById('moreMenu');
    const sendBtn = document.getElementById('sendBtn');
    const chatInput = document.getElementById('chatInput');
    const tabButtons = Array.from(document.querySelectorAll('[data-tab]'));
    const sourceViewButtons = Array.from(document.querySelectorAll('[data-source-view]'));
    const chatPanel = document.getElementById('chatPanel');
    const sourcePanel = document.getElementById('sourcePanel');
    const sourceToolbar = document.getElementById('sourceToolbar');
    const sourceEmptyState = document.getElementById('sourceEmptyState');
    const sourceFilledState = document.getElementById('sourceFilledState');
    const sourceSheet = document.getElementById('sourceSheet');
    const openSheetButtons = [
      document.getElementById('openSourceModalFromEmpty'),
      document.getElementById('openSourceModalFromList')
    ];
    const closeSheetBtn = document.getElementById('closeSheetBtn');

    let activeTab = 'source';
    let activeSourceView = 'empty';

    function updateThemeIcon() {
      const icon = themeToggle.querySelector('i');
      icon.className = htmlEl.dataset.theme === 'dark' ? 'fa-solid fa-sun text-sm' : 'fa-solid fa-moon text-sm';
    }

    function updateSendState() {
      const hasText = chatInput.value.trim().length > 0;
      sendBtn.style.opacity = hasText ? '1' : '.55';
      sendBtn.style.pointerEvents = hasText ? 'auto' : 'none';
    }

    function renderTabs() {
      tabButtons.forEach((btn) => {
        const isActive = btn.dataset.tab === activeTab;
        btn.classList.toggle('is-active', isActive);
        btn.classList.toggle('paper-muted', !isActive);
      });

      const sourceVisible = activeTab === 'source';
      sourcePanel.classList.toggle('hidden', !sourceVisible);
      sourceToolbar.classList.toggle('hidden', !sourceVisible);
      chatPanel.classList.toggle('hidden', sourceVisible);
    }

    function renderSourceView() {
      sourceViewButtons.forEach((btn) => {
        const isActive = btn.dataset.sourceView === activeSourceView;
        btn.classList.toggle('is-active', isActive);
        btn.classList.toggle('paper-muted', !isActive);
      });

      sourceEmptyState.classList.toggle('hidden', activeSourceView !== 'empty');
      sourceFilledState.classList.toggle('hidden', activeSourceView !== 'filled');
    }

    function openSheet() {
      sourceSheet.classList.add('open');
      document.body.style.overflow = 'hidden';
    }

    function closeSheet() {
      sourceSheet.classList.remove('open');
      document.body.style.overflow = '';
    }

    function startEditingName() {
      connectorNameText.classList.add('hidden');
      connectorNameInput.classList.remove('hidden');
      connectorNameInput.focus();
      connectorNameInput.select();
    }

    function saveName() {
      const nextValue = connectorNameInput.value.trim() || '资源连接器';
      connectorNameText.textContent = nextValue;
      connectorNameInput.value = nextValue;
      connectorNameText.classList.remove('hidden');
      connectorNameInput.classList.add('hidden');
    }

    themeToggle.addEventListener('click', () => {
      htmlEl.dataset.theme = htmlEl.dataset.theme === 'dark' ? 'light' : 'dark';
      updateThemeIcon();
    });

    editNameBtn.addEventListener('click', startEditingName);
    connectorNameText.addEventListener('click', startEditingName);
    connectorNameInput.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') {
        event.preventDefault();
        saveName();
      }
      if (event.key === 'Escape') {
        connectorNameInput.value = connectorNameText.textContent.trim();
        saveName();
      }
    });
    connectorNameInput.addEventListener('blur', saveName);

    chatInput.addEventListener('input', updateSendState);

    tabButtons.forEach((btn) => {
      btn.addEventListener('click', () => {
        activeTab = btn.dataset.tab;
        renderTabs();
      });
    });

    sourceViewButtons.forEach((btn) => {
      btn.addEventListener('click', () => {
        activeSourceView = btn.dataset.sourceView;
        renderSourceView();
      });
    });

    moreBtn.addEventListener('click', (event) => {
      event.stopPropagation();
      moreMenu.classList.toggle('open');
    });

    document.addEventListener('click', (event) => {
      if (!moreMenu.contains(event.target) && !moreBtn.contains(event.target)) {
        moreMenu.classList.remove('open');
      }
    });

    openSheetButtons.forEach((btn) => btn && btn.addEventListener('click', openSheet));
    closeSheetBtn.addEventListener('click', closeSheet);
    sourceSheet.addEventListener('click', (event) => {
      if (event.target === sourceSheet) closeSheet();
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') closeSheet();
    });

    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (prefersDark) htmlEl.dataset.theme = 'dark';

    updateThemeIcon();
    updateSendState();
    renderTabs();
    renderSourceView();
  </script>
</body>
</html>
```

---

## ✅ 说明

- 默认展示 **“来源”** 主 Tab，并通过次级切换展示 **空状态 / 已连接状态**。
- 同一份 HTML 内已包含：`ConnectorHeader`、`ChatInputBar`、`TabSwitch`、`EmptySourcePanel`、`SourceList`、`ChatList`、`Add Source Modal`。
- 页面支持 **Light / Dark** 模式切换、连接器名称行内编辑、更多菜单展开、来源 ActionSheet 打开/关闭。