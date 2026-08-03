# Dream Surface Task 2 实施记录（前端消费 plugin-load-receipt 透出 surfaces）

> 依据：`2026-08-03-dream-surface-execution-implementation-plan.md` Task 2（2026-08-03 B7 兼容性修订后的纯前端版本，Step 1–Step 5）
> 日期：2026-08-04

## 任务范围

纯前端、零后端改动。消费既有端点 `GET /api/claude-agent/threads/{thread_id}/plugin-load-receipt`（`backend/routers/claude_agent.py:471-523`，整文件透传 launch-manifest / pack-receipt），解析 `launch_manifest.surfaces`、兜底 `receipt.surfaces`，产出 `useWorkspaceSurfaces(threadId) -> StoryWorkspaceSurface[] | undefined`。

## 测试设施探测结论（硬性约束 1）

- `frontend/package.json` 无 `test` 脚本，devDependencies 无 vitest/jest/@testing-library；`node_modules/.bin` 仅 `playwright` / `playwright-core`。
- 仓库既有前端测试 = Playwright（`e2e/deck-dream.spec.ts`、`e2e/claude-plugin-settings.spec.ts`，均无 config 文件，默认 testDir/testMatch）。
- PLAN Tech Stack 假设的 vitest 与 Step 1 示例的 `renderHook`/`waitFor`（@testing-library/react）**在代码现实中不存在**。按硬性约束「选用仓库已有工具」，采用 **Playwright test runner 的 Node 侧模式**（不取 `page` fixture、不起浏览器）跑合同测试。
- 由此调整测试落点（现实适配，语义不变）：不渲染 hook，改为覆盖 hook 的两个可测 seam——
  1. `fetchWorkspaceSurfaces(endpoint, {fetchImpl, token, signal})`：URL、auth header、`credentials: 'include'`、404/网络异常/坏 JSON 降级；
  2. `resolveWorkspaceSurfaces(payload)`：manifest 优先 → receipt 兜底、pre-pack（`workspace_found:false`）、旧会话（无 `surfaces` 键）、空数组、畸形条目过滤。
  React 包装层（`useState`/`useEffect`/abort）为薄胶水，遵循 `useStoryWorkspaceList` 既有模式。

## hook 行为要点落实（对照 PLAN / 硬性约束 2）

| 要求 | 落实 |
|------|------|
| manifest 优先 → receipt 兜底 | `resolveWorkspaceSurfaces`：`pickSurfaces(launch_manifest?.surfaces) ?? pickSurfaces(receipt?.surfaces)` |
| pre-pack（`workspace_found:false`）视为无 surface | 非 `true` 一律 `undefined`，不再看 manifest/receipt |
| 404 / 网络异常 / 坏 JSON 不报错 | `fetchWorkspaceSurfaces` 全部 catch → `undefined`，UI 永不暴露错误 |
| 旧会话（无 surfaces 字段）缺省 = 无 surface | 键缺失 / 空数组 / 全畸形条目 → `undefined`（非空数组，与「有 surface 但为空」不可区分，统一隐藏入口，DEC-028） |
| 不探测文件系统 | 仅一次 REST GET，零文件系统访问 |
| 合同类型归属 DEC-026 | `StoryWorkspaceSurface`、`StoryWorkspacePluginLoadReceiptResponse` 只放 `frontend/src/hooks/story-workspace/contracts.ts` |

## TDD 过程摘要（Red → Green）

1. **Step 1/2（Red）**：先写 `frontend/src/hooks/story-workspace/__tests__/useWorkspaceSurfaces.test.ts`（11 例：endpoint 构建含转义、manifest 透出 + header/credentials 断言、receipt 兜底、pre-pack、旧会话、空数组、404、坏 JSON、网络异常、畸形条目过滤与回退、null payload）。运行 → `Error: Cannot find module '.../useWorkspaceSurfaces'`（No tests found），确认失败。
2. **Step 3（实现）**：`contracts.ts` 加两个类型；新增 `useWorkspaceSurfaces.ts`（`workspaceSurfacesEndpoint` / `resolveWorkspaceSurfaces` / `fetchWorkspaceSurfaces` / `useWorkspaceSurfaces`）；`index.ts`  barrel 导出 hook 与类型（供 Task 4 消费）。
3. **Step 4（Green）**：`npx playwright test src/hooks/story-workspace/__tests__/useWorkspaceSurfaces.test.ts` → **11 passed (409ms)**。
4. 回归校验：`npx tsc -b` 通过（测试文件在 tsconfig `include: ["src"]` 内，一并类型检查）；`npx eslint src/hooks/story-workspace/` 通过。

## 测试运行输出关键行

```
npx playwright test src/hooks/story-workspace/__tests__/useWorkspaceSurfaces.test.ts --reporter=line
  11 passed (409ms)
npx tsc -b        → exit 0
npx eslint src/hooks/story-workspace/  → exit 0
```

## 与 PLAN 的偏差（均按代码现实调整，语义不变）

1. **测试框架**：PLAN 示例用 vitest + `renderHook`/`waitFor`；代码现实无单测设施，按约束改用 Playwright Node 侧 runner（详见上节）。PLAN「Tech Stack: vitest（前端，按仓库既有栈）」与现实不符，建议后续修订该表述。
2. **测试粒度**：不渲染 hook，改测 seam 函数（`fetchWorkspaceSurfaces` / `resolveWorkspaceSurfaces`）；PLAN 三个 `it` 的断言语义全部保留并有超集（404、坏 JSON、网络异常、畸形条目、header/credentials）。
3. **hook 签名**：`useWorkspaceSurfaces(threadId: string | null | undefined)`（容忍调用方尚无 thread 的场景），返回类型与 PLAN 一致 `StoryWorkspaceSurface[] | undefined`。
4. **barrel 导出**：`index.ts` 追加导出（PLAN Files 未列），为 Task 4 消费方提供既有目录约定入口，无新行为。

## 给 Task 4（按钮消费方）的接口说明

```ts
import { useWorkspaceSurfaces } from '../../hooks/story-workspace';
import type { StoryWorkspaceSurface } from '../../hooks/story-workspace';
```

- `useWorkspaceSurfaces(threadId)` → `StoryWorkspaceSurface[] | undefined`
  - `undefined` = 无 surface（pre-pack / 旧会话 / 任意失败）→ **隐藏按钮**，不渲染错误态。
  - 有值时取 `surfaces.find(s => s.name === 'dream')`，其 `entry_route`（当前恒为 `/story-workspace/dream`）作按钮目标路由。
- 无需自行 fetch、无需缓存处理；threadId 变化自动重新加载。
- 后端零改动依赖：Task 1 已保证 manifest/receipt 仅在非空时写 `surfaces` 键；pre-pack 期间端点返回 `workspace_found:false`（首个 agent turn pack 完成后才转 true）。

## 变更文件清单（commit 范围）

- `frontend/src/hooks/story-workspace/contracts.ts`（+`StoryWorkspaceSurface`、`StoryWorkspacePluginLoadReceiptResponse`）
- `frontend/src/hooks/story-workspace/useWorkspaceSurfaces.ts`（新增）
- `frontend/src/hooks/story-workspace/index.ts`（barrel 导出）
- `frontend/src/hooks/story-workspace/__tests__/useWorkspaceSurfaces.test.ts`（新增）
- `docs/design/story-workspace/2026-08-04-dream-surface-task2-implementation-record.md`（本文件）
