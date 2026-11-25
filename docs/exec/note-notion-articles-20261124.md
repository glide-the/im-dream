<!-- [Sync] 2026-11-25: 追加日历插入轻提示的桌面和窄屏验证。 -->
<!-- [Input] 笔记外部文章需求、写作页、连接器和阅读组件。 -->
<!-- [Output] 文章引用交付、空白区域另起一行修订、验证回执与验收状态。 -->
<!-- [Pos] 笔记文章引用实施记录。 -->
# 笔记 Notion 文章引用交付记录

[产品需求](../prd/notes/notion-article-links.md) · [交互设计与评审](../design/edit-session/notion-article-links.md)

本地工作区交付写作纸面、文章识别、紧凑引用、只读接口和阅读窗口。复用既有笔记正文、访问授权、页面 Markdown 与 react-notion-x。隔离浏览器测试使用会话与文章接口样本。服务端测试运行公开 FastAPI 路由、Admin 数据合同及现有正文读取代码。真实账户、真实 Notion 连接、物理设备和发布分别记载。

## 实现位置

| 用户操作 | 源码与职责 |
| --- | --- |
| 进入笔记并持续输入 | [App](../../frontend/app/_dream/App.tsx) 将原生文本框接到 [NotebookLines](../../frontend/app/_dream/components/Editor/NotebookLines.tsx) 与[笔记引用组件](../../frontend/app/_dream/components/notes/NoteNotionTextCell.tsx)，保留原有编辑和会话保存入口 |
| 粘贴、修改或打开原地址 | [链接识别](../../frontend/app/_dream/components/notes/notionArticleLinks.ts) 返回精确文本区间、原地址、页面标识和名称 |
| 点击标题阅读 | [笔记阅读窗口](../../frontend/app/_dream/components/notes/NoteNotionArticleReader.tsx) 读取当前选择，交给[共享阅读组件](../../frontend/app/_dream/components/chat/DeferredNotionDocument.tsx) |
| 检查可读范围 | [只读接口](../../backend/routers/notion.py) 绑定当前账户，[连接器](../../backend/notion/factory.py) 校验页面、读取 Markdown 并复核范围 |

## 写作页浏览器回执

改动前基线使用 `git archive HEAD` 中的 App.tsx。桌面 Chrome 在旧版纸面粘贴带查询参数和区块锚点的地址，追加文字，等待保存后刷新。保存请求与恢复的文本逐字一致，页面上的文章引用控件数为零。

入口为 `/story-workspace/writing`。Chrome 使用独立浏览器上下文，Next 使用本轮源码的隔离副本，会话与 Notion HTTP 响应由规格截获。第一次打开的会话只含既有格式的文本单元。重开时，读取接口返回写作页自动保存提交的 editor_state。

| 场景 | 实际观察 |
| --- | --- |
| 粘贴和撤销 | 系统剪贴板粘贴后出现一个引用，光标在地址末尾。接着输入“下周讨论”，选中并删除整个地址，撤销后两侧文字和锚点逐字恢复 |
| 保存与重开 | 保存请求中只有原来的 TextCell 和完整原文。两次刷新均在“会议资料”和“下周讨论”之间显示一个引用，预览请求数为零 |
| 打开原文和预览 | Chrome 新标签的目标包含完整查询串和区块锚点，外部页面响应由隔离样本提供。预览显示 NotionRenderer 生成的标题和段落。刚重开的笔记关闭预览后从引用末尾继续输入 |
| 窄屏写作与失败恢复 | 360 像素宽度下手动键入地址、换行后出现引用。普通网址、相似域名保持文字。编辑框与操作条纵向分开。未选资源、上游读取失败、重试成功依次显示，再次输入在原光标处追加 |
| 旧笔记与锚点修改 | 旧文本直接显示引用。点击周围文字进入编辑，替换区块标识后原文入口相应变化。撤销恢复原锚点，期间无正文读取 |

首次专项运行发现恢复焦点时缺少明确选区。修订后恢复用户离开文本框时的选区，初次阅读以引用末尾为继续输入的位置。窄屏测试改用明确的文本位置，在 macOS 的自动化中区分整段末尾和视觉行末。共享阅读器回归同步了故障注入位置，渲染失败、查看详情、重试及关闭均沿原测试断言验证。

本机截图保存在 `frontend/output/playwright/note-notion-articles/`。桌面引用为 `writing-article.png`，阅读窗口为 `article-reader.png`，窄屏输入为 `narrow-writing.png`。

## 命令与技术验证

下表中前端命令在 `frontend/` 执行，Python 命令在仓库根目录执行。浏览器前置检查 `python3 .agents/skills/ink-dream-playwright-qa/scripts/preflight.py` 退出 0，报告已安装 Playwright 1.62.1 和本机 Chrome。

| 命令 | 退出码 | 关键结果 |
| --- | --- | --- |
| `E2E_WEB_BASE=http://127.0.0.1:55176 node_modules/.bin/playwright test --config=/tmp/ink-notion-baseline-qa.8cOI5A/playwright.config.mjs --reporter=line --workers=1` | 0 | 改动前 1 项写作页基线通过，7.7 秒 |
| `E2E_WEB_BASE=http://127.0.0.1:55175 node_modules/.bin/playwright test --config=/tmp/ink-notion-writing-playwright.config.mjs note-notion-articles.spec.ts --reporter=line --workers=1` | 0 | 3 项写作页旅程通过，16.4 秒，桌面 1220×840、窄屏 360×840 |
| `E2E_WEB_BASE=http://127.0.0.1:55176 node_modules/.bin/playwright test --config=/tmp/ink-notion-baseline-qa.8cOI5A/durable.config.mjs --reporter=line --workers=1` | 1 | 在基线服务热更新后，一次桌面粘贴后的追加输入未出现，另外 2 项通过。下两项使用当前源码启动的新服务 |
| `E2E_WEB_BASE=http://127.0.0.1:55177 node_modules/.bin/playwright test --config=/tmp/ink-notion-repeat-qa.BDbyuN/repeat.config.mjs --grep 'paste into a note' --repeat-each=5 --workers=1 --reporter=line` | 外层脚本记录 127，未单独确认测试进程退出码 | Playwright 日志报告带事件记录的桌面旅程 5/5，49.6 秒。粘贴后活动元素为原文本框，输入后选区从 146 推进至 150 |
| `E2E_WEB_BASE=http://127.0.0.1:55177 node_modules/.bin/playwright test --config=/tmp/ink-notion-repeat-qa.BDbyuN/formal.config.mjs --repeat-each=3 --workers=1 --reporter=line` | 0 | 当前源码、正式规格，3 项写作旅程各重复 3 次，9/9 通过，47.6 秒。上次追加输入失败的原因未确认 |
| `PYTHONPATH=backend:backend/tests backend/.venv/bin/python -m unittest -q backend/tests/test_note_notion_article.py backend/tests/test_notion_connector_router_flow.py backend/tests/test_notion_today.py backend/tests/test_notion_operations.py` | 0 | 55 项通过，覆盖账户归属、平台、已选页面、上游身份、撤销选择、Notion 授权过期与现有连接器行为 |
| `node --experimental-strip-types --test app/_dream/components/notes/notionArticleLinks.test.ts` | 0 | 3 项通过，覆盖原文区间、前后标点、主机、页面路径、视图参数和类似域名 |
| `node_modules/.bin/tsc --noEmit --pretty false --incremental false -p tsconfig.json` | 0 | Web TypeScript 类型检查通过 |
| 下方 ESLint 命令 | 0 | 0 个错误，App.tsx 有 16 条既有 Hook 依赖警告 |
| `node_modules/.bin/playwright test --config e2e/notion-preview.config.ts --output /tmp/ink-notion-preview-regression-final-1795454049134 --workers=1` | 0 | 共享 Chat 阅读、错误恢复、历史和适配器回归共 28 项通过 |
| `git diff --check`（本轮受影响路径） | 0 | 差异格式检查通过 |

```sh
node_modules/.bin/eslint app/_dream/App.tsx app/_dream/i18n.ts \
  app/_dream/components/Editor/NotebookLines.tsx \
  app/_dream/components/chat/{DeferredNotionDocument,NotionPageDocument,NotionWorkspacePreview}.tsx \
  app/_dream/components/chat/notionRecordMapAdapter.ts \
  app/_dream/components/notes/{NoteNotionArticleReader,NoteNotionTextCell}.tsx \
  app/_dream/components/notes/notionArticleLinks{,.test}.ts \
  e2e/note-notion-articles.spec.ts
```

专项浏览器命令使用的临时配置绑定本机 Chrome 和隔离输出目录。再次运行时，可将 E2E_WEB_BASE 指向包含本次源码的隔离 Next 服务，从 frontend 运行 `node_modules/.bin/playwright test --config e2e note-notion-articles.spec.ts --reporter=line --workers=1`。规格使用公开写作路由并接管测试数据。后端虚拟环境未安装 pytest，以上 unittest 命令直接执行仓库的 unittest 测试类。

## 文档验证

- `python3 -` 从标准输入执行本地链接检查，最终复核包含 PRD、交互设计、交付记录及相关索引，共 7 个 Markdown 文件。12 个新增文件均有目录清单条目，两幅页面骨架、“验收”标题与三个图块均已找到，退出码 0。
- `node --input-type=module` 在隔离 Vite 服务上通过已安装的 Chrome 调用 mermaid.parse，依次加载正式设计中的三段 Mermaid，正常时序、异常恢复时序和状态图均解析成功，退出码 0。

## 验收范围

真实账号访问私有 Notion 文章、真实 PostgreSQL 写入及物理设备键盘均待实测。需求父页已用当前 Notion 连接读取，该调研回执独立于 Dream 账户验收。此次工作未执行发布。截图左下角保留 Next 开发模式的诊断标记。隔离服务日志另有既有的卡片结构语音配置加载错误。三项写作旅程的浏览器均成功完成断言，采集 pageerror 的两项旅程记录为零。

## 单条文章引用的换行修订

用户反馈只有一条文章引用时点空白无法继续写，并明确要求点击以后直接另起一行。点文章标题预览，点箭头打开原文，点引用区域的空白在该段下面插入或复用空行。点击已有文字仍在所点位置编辑。末尾纸面和“另起一行”从当前正文末尾续写。新增换行进入原 TextCell，使用原有笔记保存路径。

当时的纸面和引用共用整段文本框的换行处理。11 月 25 日改为[按行展示和编辑](../../frontend/app/_dream/components/notes/NoteNotionTextCell.tsx)。[浏览器规格](../../frontend/e2e/note-notion-articles.spec.ts)中的桌面与触摸场景直接点击后输入，并断言重复点击只保留一个空行。

本机写作路由的只读请求 `curl --noproxy '*' http://localhost:5173/story-workspace/writing` 返回 HTTP 200。读取该页面加载的前端资源，组件包含 focusNewWritingLine 和 insertLineBreak，语言资源包含新操作文案。本轮按用户要求关闭 Luna 验证；上表的浏览器回执属于先前版本。最终点击自动另起一行的场景尚未取得浏览器操作回执。

## 11 月 25 日修订 · 日历插入与按行续写

从写作页打开日历，浏览 9 月 27 日的文章，点击“插入日记”。9 月 28 日正在编辑的日记在原有文字下一行收到完整地址。保存成功后，文章旁显示“已插入当前日记。”。再次点击显示“当前日记已包含这篇文章。”。360 像素宽度下模拟保存失败，用户能看到重试提示，重试和重开后日记仅含一个原地址及其区块锚点。操作全程没有发起文章正文读取。

在桌面和触摸窄屏上点击引用行右侧，文章保留原位置，紧接其下的独立文本框获得焦点。输入“下周讨论”后，保存请求包含文章、换行和该文字。两篇文章之间插入两行、回车、撤销本行输入，以及重开后原后文与第二篇文章位置均有浏览器断言。纸面和文本框使用纯色背景。窄屏逐键输入长地址的复测发现移动评论在相同光标状态下重复更新，修订后原速键入连续通过三次。

以下命令在仓库根目录运行。浏览器命令的 `E2E_WEB_BASE` 为 `http://127.0.0.1:5173`，`QA` 为本轮临时验证目录 `/tmp/ink-writing-lines-1125.Md4B2q`。Chrome 使用当前源码的写作页和独立上下文，登录、日历、笔记读写与 Notion 响应由隔离样本提供。

| 命令 | 退出码 | 关键结果 |
| --- | --- | --- |
| `frontend/node_modules/.bin/playwright test --config=$QA/qa.config.mjs note-notion-articles.spec.ts` | 0 | 8/8，41.0 秒，含跨日期日历插入、保存重试、旧笔记、桌面点击、触摸续写和阅读窗口 |
| `frontend/node_modules/.bin/playwright test --config=$QA/qa.config.mjs -g 'type a standalone' --repeat-each 3` | 0 | 原速逐键输入、换行和读取失败恢复连续通过 3/3 |
| `frontend/node_modules/.bin/playwright test --config=$QA/mobile.config.mjs writing-mobile-layout.spec.ts` | 0 | 7/7，18.3 秒，含纯色纸面、长文折行、焦点、选择器与模拟原生文档 |
| `cd frontend && node --experimental-strip-types --test app/_dream/components/notes/notionArticleLinks.test.ts` | 0 | 4/4，日历地址保留匹配页面的查询与锚点，缺少匹配地址时按页面标识处理 |
| `PYTHONPATH=backend:backend/tests backend/.venv/bin/python -m unittest -q backend/tests/test_note_notion_article.py backend/tests/test_notion_connector_router_flow.py backend/tests/test_notion_today.py backend/tests/test_notion_operations.py` | 0 | 55/55，文章资源范围、上游读取与日历连接器回归 |
| `cd frontend && node_modules/.bin/tsc --noEmit --incremental false` | 0 | Web 类型检查通过 |
| 下方 ESLint 命令 | 0 | 0 个错误，App 和 useComments 共 17 个 Hook 依赖警告 |
| `python3 "$QA/check_docs.py"`、`node "$QA/diagrams.mjs"`、`git diff --check` | 0，各项 | 核对本轮文档、目录登记和相对链接，Chrome 成功解析并渲染两幅时序图和一幅状态图 |

```sh
cd frontend
node_modules/.bin/eslint app/_dream/{App.tsx,i18n.ts} \
  app/_dream/components/{CalendarNotionPanel,CalendarPopup}.tsx \
  app/_dream/components/Editor/NotebookLines.tsx \
  app/_dream/components/notes/{NoteNotionTextCell.tsx,notionArticleLines.ts,notionArticleLinks.ts,notionArticleLinks.test.ts} \
  app/_dream/hooks/{useTextCells,useComments}.ts app/_dream/engine/EditorEngine.ts \
  e2e/{writing-mobile-layout,note-notion-articles}.spec.ts
```

本机截图位于 `frontend/output/playwright/note-notion-articles/`。其中 `calendar-inserted.png` 为跨日期插入后的提示，`focused-row-1220.png` 和 `focused-row-360.png` 为桌面和窄屏正在编辑的新行。真实账号写入、真实 Notion 阅读、物理设备软键盘和发布尚未验收。

## 日历插入按钮的轻提示

此前的反馈显示在文章标题下方。点击“插入日记”后，本次修订将共享 Toast 锚定到所点按钮，箭头指向该按钮，多篇文章各自对应独立的插入入口。等待保存期间提示持续可见，成功、重复和失败结果沿用共享组件的 2.8 秒展示时间。用户可以继续点原按钮重试或关闭日历。桌面与窄屏的截图分别保存在 `frontend/output/playwright/note-notion-articles/calendar-tip-desktop.png` 和 `calendar-tip-narrow.png`。

在 `frontend/` 执行以下命令。浏览器基址 `E2E_WEB_BASE=http://127.0.0.1:5173`，配置位于 `/tmp/ink-calendar-insert-tip.GOC0Gu/qa.config.mjs`。

| 命令 | 退出码 | 观察结果 |
| --- | --- | --- |
| `node_modules/.bin/playwright test --config=/tmp/ink-calendar-insert-tip.GOC0Gu/qa.config.mjs note-notion-articles.spec.ts --grep 'calendar article insertion'` | 0 | 2/2，从写作日历进入，同一列表有两篇文章。点击第二篇时，保存中的提示完整可见、与触发按钮相隔至多 12 像素并通过 aria-describedby 关联，成功、重复、失败及重试均有反馈。提示自动消失后可再次触发，关闭日历后提示消失 |
| `node_modules/.bin/playwright test --config=/tmp/ink-calendar-insert-tip.GOC0Gu/qa.config.mjs note-notion-articles.spec.ts` | 0 | 按钮旁气泡定位完成后 8/8 通过，43.1 秒，包含两种宽度的日历反馈、续写、保存重开和阅读 |
| `node_modules/.bin/tsc --noEmit --incremental false` | 0 | Web 类型检查通过 |
| `node_modules/.bin/eslint app/_dream/components/{CalendarNotionPanel.tsx,chat/Toast.tsx} e2e/note-notion-articles.spec.ts` | 0 | 专项文件无警告或错误 |

本轮使用本机 Chrome 和隔离的认证、文章与日记数据。真实账户和物理设备待验收。
