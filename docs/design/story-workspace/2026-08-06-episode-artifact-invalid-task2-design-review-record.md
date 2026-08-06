# Episode 产物合同异常隔离与渐进降级：任务二独立评审记录

- 日期：2026-08-06
- 被评审设计：`design_010_episode-artifact-contract-isolation-and-progressive-degradation.md`
- 输入裁决：`2026-08-06-episode-artifact-invalid-task1-problem-decision-record.md`
- 评审方式：独立只读评审；评审者未修改设计稿或生产代码
- 最终结论：**PASS**
- 最终级别：P0 = 0，P1 = 0，P2 = 3（均为非阻断实施提醒）

## 1. 第一轮评审与返工

第一轮结论为 `FAIL`，无 P0，共发现四个 P1 和三个 P2：

1. 关联闭包只验证 `targetViewId` 是否存在，未验证 `sourceKey ↔ viewId` 是否来自同一 canonical map entry。
2. 大小写规范化后的 auxiliary identity collision 未定义。
3. `unavailable` 的后端产生阶段、errno 与安全边界不可实施。
4. 固定三栏布局违反 design_009 的两层架构，且 1200px 几何不可满足。
5. public target kind 与 UUID seed token 淆乱。
6. 空白、Unicode 和视觉混淆字符缺少测试合同。
7. Review 定位缺少 selection、focus、scroll 与 reduced-motion 的完整验收。

返工后的关键证据：

- canonical sourceKey/viewId 同 entry 与 cross-wire 拒绝：设计稿第 264—269 行。
- auxiliary canonical collision：设计稿第 141—142、216—218 行。
- `unavailable` 精确错误分类：设计稿第 318—349 行。
- 两层布局与内容容器断点：设计稿第 608—702 行。
- 固定 `beat/scene/shot` seed 与 exact UUID fixture：设计稿第 182—195 行。
- ASCII-only 查找、空白与 confusable 规则：设计稿第 208—218 行。
- Review 原子定位与 reduced-motion：设计稿第 524—533、763、788 行。

## 2. 第二轮独立评审结论

第二轮逐项复核后判定 `PASS`：

| 质量门 | 结论 | 设计证据 |
|---|---|---|
| narrative 是 view ID 唯一 truth owner | PASS | 第 107—141 行 |
| same-entry closure 与真实 ID cross-wire 拒绝 | PASS | 第 264—269、749、782 行 |
| Prompt/Render/Review collision 局部隔离 | PASS | 第 141、216、748、781 行 |
| strict parser 保留且不做客户端补链 | PASS | 第 264—269、757、785 行 |
| auxiliary invalid 时保留 narrative | PASS | 第 299—310 行 |
| `not_generated` / orphan / invalid / unavailable / HTTP error 区分 | PASS | 第 299—349、444—458 行 |
| revision、selection、focus、scroll、刷新恢复 | PASS | 第 464—533 行 |
| UI Design v2、窄屏与无障碍 | PASS | 第 608—702 行 |
| 不新增 Episode 业务失败状态机 | PASS | 第 293—297 行 |
| `/events` 404 独立于本期根因 | PASS | 第 596—603 行 |

## 3. 非阻断提醒与任务三约束

1. 页面级最多一条虚线；D2/D3 内部使用实线或留白，避免虚线嵌套。
2. 1024/1200/1280/1440 的几何测试必须固定 sidebar collapse 状态；核心断言以实际 Episode/C2 容器宽度为准。
3. 前端测试显式覆盖 `unavailable + per-root last-good → available recovery`，避免现有 cache 合并逻辑提前丢弃 last-good。

这些提醒不改变设计结论，但属于任务三代码评审和浏览器验收的必查项。

## 4. 任务三冻结门槛

- 后端先保证 canonical mapping、same-entry closure 与 per-root isolation；前端只做严格 defense-in-depth。
- 必须先保存 exact UUID、cross-wire、三类 auxiliary collision、ASCII/confusable 与 errno-stage 的 Red 输出。
- 任何 `200` Episode surface 必须整体通过 frontend strict parser。
- 单一 auxiliary `invalid` 或 `unavailable` 不得清空已验证 narrative。
- 浏览器覆盖 1024/1200/1280/1440/390、两层 DOM 归属、容器几何、无横向溢出及 Review 真实定位。
- `/events` 404 继续作为诚实遗留记录，不纳入本期实现。

## 5. 评审声明

任务二设计已经建立唯一 truth owner、修复 stable ID 根因、保留严格合同并定义部分可用边界；它没有通过修改真实 Episode 文件、前端静默补链或数组位置关联来掩盖后端缺陷。设计稿可以作为任务三唯一实施输入。
