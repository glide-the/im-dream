# Execution 第一集产物工作台同页展开顺序返工记录

> 日期：2026-08-06  
> 性质：用户反馈问题判定、canonical 设计修订与实现验收 owner  
> 上游：`design_009_drama-forge-first-episode-storyline-storyboard-workbench.md`  
> 约束：同一 run execution 路由；不改变 artifact owner、恢复合同或 Dream Agent 边界；不执行归档

## 0. 本轮规划前置器

### 0.1 Optimized Prompt

修正 `StoryWorkspaceExecutionPage` 的正文层级：保持 `/story-workspace/runs/:runId/execution` canonical 路由和 run key 不变，把 `<section aria-label="第一集产物工作台">` 从页面前部移动到既有“Dream 初稿阶段投影” disclosure 及其 overview/focus article 之后，使完整 EP01 产物在当前执行页面向下展开。保留 Episode binding、artifact revisions/polling、叙事选择稳定性、继续操作确认框和 Dream Agent dialog；不得新增 route、复制数据 owner、用 CSS order 伪造阅读顺序或改动无关工作线。

### 0.2 Optional Enhancers

- 增加源码结构 seam，直接断言 disclosure 先于唯一 artifact section，并断言 router 仍以 run ID key 挂载同一页面。
- 在确定性浏览器测试中同时验证 canonical URL、DOM following 关系、桌面和 390px 的滚动可达及无横向溢出。
- 以源码 `open` 守门和 revision 前后 `HTMLDetailsElement.open` 断言保留现有默认折叠及用户手动展开状态，避免本轮位置修正同时改变用户状态和焦点模型。

### 0.3 执行计划

1. 读取当前 JSX、CSS、router、design_009 与 deterministic E2E，确认反向顺序和滚动 owner。
2. 修订 canonical 设计并独立评审；不通过先返工设计。
3. Red：增加 DOM 顺序、唯一 section 与路由稳定守门，记录失败输出。
4. Green：只移动同一 JSX section 与其 continue dialog，不改数据和事件逻辑。
5. 运行聚焦 Node seam、TypeScript、改动文件 ESLint 与隔离浏览器桌面/窄屏验收；独立代码评审后再提交。

### 0.4 验收标准

- URL 仍为 `/story-workspace/runs/:runId/execution`，router 仍传入相同 run ID 并以其作为 React key。
- 页面 DOM/读屏顺序为 masthead → Dream 初稿阶段投影 → 第一集产物工作台；artifact section 唯一且位于整个 disclosure 之后。
- disclosure 初次进入 `open=false`，用户手动展开后 artifact revision 重绘仍保持展开。
- 不改变 Episode surface、artifact revisions、选择、continue action、Dream Agent dialog 与文件 truth ownership。
- 页面根 computed `overflow-y:auto`；桌面和 390px 均能用同一纵向滚动面把后置工作台操作带入视口，无严重遮挡、横向溢出或键盘不可达。

## 1. 问题判定与产品裁决

问题  
→ 第一集产物工作台当前出现在 Execution 页面既有 Dream 初稿投影之前，用户期望它作为后续工作流在当前页面后面展开。

现状证据  
→ 当前页面 masthead 后立即渲染 `<section aria-label="第一集产物工作台">`（`frontend/src/pages/story-workspace/StoryWorkspaceExecutionPage.tsx:867-1042`），其后才渲染“Dream 初稿阶段投影” `<details>`，聚焦分支内的 article 位于 `:1062-1127`。router 已在 `run-execution` 分支将 URL 中的 run ID 同时作为 component key 和 `runId` prop（`frontend/src/router/story-workspace.tsx:184-190`）。页面根元素本身是纵向滚动 owner（`frontend/src/pages/story-workspace/StoryWorkspaceExecutionPage.css:20-30`），artifact section 是普通不可伸缩纵向子项（同文件 `:491-504`）。

根因  
→ Episode workbench 首次接入时被插入 masthead 后，但没有把“既有 Dream 初稿投影是上游内容、完整 EP01 产物是其后续展开”编码为 DOM 层级约束；现有测试只验证 workbench 内部 master-detail，没有验证它与旧投影的先后关系（`frontend/src/pages/story-workspace/__tests__/StoryWorkspaceExecutionPageLayout.test.ts:66-78`）。

可选方案  
→ A. 新增独立 Episode route；B. 保持 DOM 不变，仅用 CSS `order` 视觉换位；C. 在同一页面直接移动 JSX sibling，使整个 Dream disclosure 在前、artifact section 在后。

最终决策  
→ 采用 C。A 会破坏用户明确要求的同页推进和既有 run deep-link；B 会让视觉顺序与 DOM、键盘及读屏顺序分裂。保留 disclosure 的默认折叠、工作台内部布局和所有 hook/state，只重排同级正文节点。Episode continue dialog 跟随其触发工作台放在正文之后，Dream Agent dialog 继续位于页面末尾并以 overlay 交互。

影响范围  
→ `design_009`、Execution Page JSX、页面结构 seam 和 deterministic browser assertion。router、CSS、API、adapter、后端和数据库合同无需改变。

风险  
→ 现有 disclosure 内容包含内部滚动层；若把它改成固定高度或新的 flex owner，可能令后置工作台不可达。因此本轮不新增高度/overflow 规则，仅依赖页面根滚动，并以浏览器几何和无溢出验收。纯源码字符串测试若只比较 article 会漏掉 overview 分支，因此必须比较整个 `<details>` 与唯一 artifact section。

验收方式  
→ 源码 seam 证明 JSX 顺序、唯一性及 `<details>` 没有 `open` prop；router seam 证明 canonical route 未变；确定性浏览器在真实 React DOM 比较 `Node.DOCUMENT_POSITION_FOLLOWING`，断言初始 `details.open=false`，手动展开并触发 artifact revision 后仍为 `true`。在 1440×1000 与 390×844 读取页面根 computed `overflow-y:auto` 及 `scrollHeight/clientHeight`，对后置 section 内的当前操作执行 `scrollIntoView` 并断言进入 viewport，同时验证无横向溢出。

## 2. 非目标

- 不新增或切换 Episode 页面路由。
- 不修改 outline/script/storyboard/prompts/renders/review 的 truth owner。
- 不自动展开 Dream 初稿 disclosure，不改变 focus/selection。
- 不修改 artifact polling、ETag/revision 或恢复事实。
- 不挂载 `ChatView`，不展示隐藏推理、原始工具参数、凭证、敏感路径或调试事件。
- 不增加业务失败、驳回、人工重试或归档状态。

## 3. 实现与验收台账

### 3.1 设计评审

- 首轮：FAIL（P0=0 / P1=1 / P2=1）。缺口为默认折叠/跨 revision 展开状态没有机器门，以及滚动 owner/后置 section 可达性描述不具体。
- 返工：增加源码无 `open`、真实 `details.open` revision 前后断言，以及 1440/390 的 computed overflow、scroll dimensions、`scrollIntoView`/viewport 门。
- 复评：PASS（P0=0 / P1=0 / P2=0），允许进入实现。

### 3.2 Red

新增 `StoryWorkspaceExecutionPageLayout.test.ts` 结构用例后运行：`9 passed, 1 failed`。失败点为 artifact source index `31769`，早于 Dream disclosure close index `46321`，准确复现页面顺序反向；失败断言位于 `StoryWorkspaceExecutionPageLayout.test.ts:80`。

### 3.3 Green、代码评审与浏览器证据

- Green：仅将同一个 Dream projection `<details>` 块移动到 masthead 后、artifact section 前；artifact section、Episode continue dialog、Dream Agent dialog 的相对次序保持为正文 → Episode modal → Agent modal。实现 diff 为 `151 insertions / 151 deletions` 的块搬移；未改 hook/state/condition/CSS/router，未给 details 增加 `open`。
- 结构 seam：`10 passed`，覆盖整个 disclosure → 唯一 artifact section → Agent dialog、默认无 `open`、root `overflow-y:auto` 与 run route/key。
- TypeScript：`npx tsc -b`，exit 0。
- ESLint：Execution Page、layout seam、Episode browser spec 三个改动前端文件，exit 0。
- 确定性浏览器主用例：`1 passed (6.3s)`。使用 mocked REST facts，只证明 UI/恢复合同，不冒充外部 drama-forge workflow 成功；验证同一 run URL、真实 DOM `DOCUMENT_POSITION_FOLLOWING`、初始折叠、手动展开跨 revision、1440×1000 与 390×844 的 computed overflow、scroll dimensions、`scrollIntoView`、viewport 和无横向溢出。
- 浏览器证据：`output/playwright/story-workspace-episode-execution-u12/desktop-1440x1000.png`、`narrow-390x844.png`、`narrow-storyline-390x844.png`、`trace.zip`。
- 补充集成组：18 passed；3 个 browser harness 因用户原有 Vite 占用 5173 而无法绑定，失败均为 `Port 5173 is already in use`，不是产品断言失败。未关闭用户服务。
- Episode spec 整文件的另一个 Dream Panel 用例遇到当前其他工作线新增的 `GET /api/story-workspace/dream-runs` 未进入该测试旧 allowlist；本轮不修改该无关测试合同，主 Episode 顺序用例已按名称隔离复跑通过。
- 独立代码评审：PASS（P0=0 / P1=0 / P2=0）。评审逐字比较证明移动前后 details 块内容一致（5962 chars equality），确认 DOM/读屏顺序、默认折叠、跨 revision 展开、滚动可达、router/truth/polling/selection/dialog 均无回归；source + real DOM 两层测试不存在 CSS 顺序假阳性。

### 3.4 工作区与清理

- 本轮隔离启动 Vite `127.0.0.1:4177`，浏览器验收后已关闭并确认端口释放。
- 用户原有 `127.0.0.1:5173` 与 `127.0.0.1:8765` 保持运行，没有关闭。
- 本轮失败重跑产生的 `frontend/test-results/*` 临时目录已删除，`.last-run.json` 已恢复至本轮前内容。
- 未修改 `backend/database.py`，未触发插件制品变化，未执行归档操作。
