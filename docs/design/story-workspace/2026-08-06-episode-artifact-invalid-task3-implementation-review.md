# Episode 产物合同异常隔离：任务三实现与代码评审记录

- 日期：2026-08-06
- 设计输入：`design_010_episode-artifact-contract-isolation-and-progressive-degradation.md`
- 评审结论：**PASS**
- 未关闭问题：P0 = 0，P1 = 0，P2 = 0
- `/events`：保持独立遗留，未纳入本期实现

## 1. 实现单元评审

### U1 canonical source-key-to-view-ID mapping

结论：PASS。

- narrative 继续用原始 Shot identity seed 生成 ID，并按 ASCII 大小写查找键拒绝碰撞：`episode_artifact_adapter.py:533-545,1017-1031`。
- service 从 narrative DTO 构建 `sourceKey → existing viewId` 映射并传给 auxiliary：`episode_artifact_service.py:946-954,969-977,1048-1056`。
- auxiliary 只消费映射；linked item 返回 map entry 的 canonical public key 和现有 view ID：`episode_auxiliary_artifact_adapter.py:228-244,404-437,542-571,630-664`。
- Review 不再因 `_ordered_matches` 的大写结果重算 narrative UUID：`episode_auxiliary_artifact_adapter.py:1559-1568`。

### U2 stable ID、冲突与闭包

结论：PASS。

- canonical target map 拒绝空白、Unicode、非法 ID 和 ASCII case collision：`episode_auxiliary_artifact_adapter.py:834-860,1146-1160`。
- Prompt/Render 按 canonical target key + discriminator 检查唯一性：`episode_auxiliary_artifact_adapter.py:408-418,542-553`。
- Review 大小写变体重复不再静默去重：`episode_auxiliary_artifact_adapter.py:637-649`。
- service 明确执行 sourceKey/viewId same-entry closure：`episode_artifact_service.py:1057-1061,1093-1157`。
- frontend strict parser 同样要求 exact canonical key 和 view ID 属于同一 entry；真实 B ID 不能替 A 通过：`contracts.ts:2023-2069`。

### U3 per-artifact invalid / unavailable isolation

结论：PASS。

- 只有 inode/type 已验证后的受控 `os.read` 或目录 `os.listdir` 瞬时 errno 进入 local unavailable：`episode_artifact_service.py:188-193,384-428,452-466`。
- root 归属与 manifest 投影：`episode_artifact_service.py:673-750,1179-1185,1222-1234`。
- open/stat/fstat、symlink、绑定、权限与身份错误没有被降级；原安全测试继续通过。
- frontend cache 同时保留 `invalid` 和 `unavailable` 的 per-root last-good，并在 available revision 到达后恢复：`useStoryWorkspaceEpisodeArtifacts.ts:503-519,585-610`。

### U4 Execution 页面交互

结论：PASS。

- `invalid` 与 `unavailable` 分开报告；`not_generated` 继续由 artifact 和局部组件表达：`StoryWorkspaceExecutionPage.tsx:1145-1170`。
- Review 定位先展开 canonical ancestor，再原子提交 selection：`StoryWorkspaceExecutionPage.tsx:553-586`。
- 定位后标题接收 `preventScroll` focus，并按 reduced-motion 选择 auto/smooth：`StoryWorkspaceExecutionPage.tsx:276-292`。
- 页面没有挂载 ChatView；artifact truth 仍来自 REST。

### U5 `/events`

结论：按设计不实现。

- workflow-run `/events` 仍为 404；Dream Agent events 为 200。
- Episode artifact REST 为 200，严格合同通过，页面可用，证明 SSE 路径不一致不是本次 stable-ID 根因。

## 2. TDD 与回归

- Red：`evidence/2026-08-06-episode-artifact-task3-red.txt`。
- Green：`evidence/2026-08-06-episode-artifact-task3-green.txt`。
- Backend：339 passed。
- Frontend Playwright Node seam：72 passed。
- TypeScript：PASS。
- 改动前端文件 ESLint：PASS。
- `git diff --check`：PASS。

## 3. 代码评审重点

| 检查项 | 结论 |
|---|---|
| narrative 单一 ID truth owner | PASS |
| auxiliary 不重新计算 narrative ID | PASS |
| A-key/B-ID cross-wire fail closed | PASS |
| unknown 保持 orphan/null | PASS |
| 禁止数组下标配对 | PASS |
| 三类 case collision 局部 invalid | PASS |
| transient read error 局部 unavailable | PASS |
| 路径、symlink、权限、绑定安全不降级 | PASS |
| frontend strict defense-in-depth | PASS |
| per-root last-good 与 available recovery | PASS |
| review selection/focus/scroll/reduced-motion | PASS |
| 不挂载 ChatView、不暴露敏感内容 | PASS |

## 4. 真实浏览器评审

真实账户、同一 run、同一 Episode 的结果记录在 `evidence/2026-08-06-episode-artifact-real-browser-after.txt`。桌面与窄屏截图分别为：

- `evidence/2026-08-06-episode-artifact-valid-after-desktop.png`
- `evidence/2026-08-06-episode-artifact-valid-after-narrow.png`

原用户 8765 进程没有被停止或热替换。验收使用本轮自有的 route-only FastAPI 进程加载改后生产模块和同一真实 DB/workspace，通过浏览器透明转发唯一 Episode artifact 请求；没有使用 mock payload。验收后该进程与 Chromium 均已关闭。

## 5. 最终裁决

实现与 design_010 一致，stable-ID 根因已经在后端 truth owner 修复；frontend 只保留严格校验和局部恢复，没有掩盖后端错误。代码可以交付。部署或开发环境需由服务所有者按正常流程重新加载 Python 进程后，原 8765 才会使用新模块；本轮遵守“不停止用户原有开发服务”的约束，没有代替所有者执行该操作。
