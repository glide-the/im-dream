# drama-forge 第一集工作台：任务二设计实施与独立评审记录

> 日期：2026-08-05
> 设计 owner：`design_009_drama-forge-first-episode-storyline-storyboard-workbench.md`
> 上游裁决：`2026-08-05-drama-forge-ep01-task1-problem-decision-record.md`
> 最终结果：独立评审 PASS
> 生产代码：本阶段未修改

## 1. 本轮 Optimized Prompt

以任务一唯一推荐方案为不可回退输入，创建 `design_009` canonical 交互设计：完整覆盖 vendor 第一集工作流、artifact truth ownership、稳定身份与关联质量、Episode 故事线 master-detail、叙事点/场景/镜头导航、上下文详细分镜、Prompt/Render/Review 辅助层、受控“继续下一步”、REST revision 恢复、权限与安全边界、响应式和无障碍。设计提供指定的全部流程图、依赖图、时序图、边界图和桌面/窄屏线框；符合暖纸张、轻分区、低卡片感的 UI v2；不重新引入 ChatView、任意路径读取、浏览器真相源或新业务状态机。

## 2. Optional Enhancers

- 同时设计完整 outline 与 legacy outline 无 SC 叙事点两种真实数据形态。
- 在各层级标注 owner、stable ID、source revision 与关联覆盖率。
- 区分“尚未生成”“尚未关联”“技术解析异常”。
- 分离 aggregate 首屏与 prompts/renders 分页详情。

## 3. 执行计划与验收标准

执行计划：创建未占用 `design_009`；补齐全部图、线框和合同；由独立代理按 vendor、artifact、storyline、Dream 独立性、ownership、恢复、UI v2、异常边界十项质量门评审；失败先运行返工规划前置器，再修订和复验。

验收标准：22 个必需主题和用户指定图稿齐全；选择、焦点、revision、窄屏行为可实现；独立评审 PASS；本阶段不改生产代码。

## 4. 设计交付范围

`design_009` 最终 25 个章节，覆盖：

1. canonical 适用范围与旧条款替代表；
2. vendor 12 步流程、命令/产物依赖和本期边界；
3. Episode binding、manifest、producer/consumer 与 availability；
4. Episode→Arc→Beat→Scene→Shot 信息架构和稳定 ID；
5. Shot→Prompt 与 Shot→Render Queue 的独立关联质量门；
6. truth ownership；
7. 桌面 master-detail、窄屏 drill-in 和 detailed shot inspector；
8. Prompt/Queue/Review 辅助展示；
9. Dream confirmation、Episode stage dispatch 和 Dream Agent dialog 边界；
10. binding recovery、next-action、claim/lease/active-turn；
11. ETag、REST polling、session-only last-good、刷新/重入；
12. API/file/adapter/view-model/component 边界；
13. 响应式、键盘、焦点、aria-live 和 Escape；
14. 技术异常、未来多 episode、本期非目标和验收映射。

指定图稿位置：

| 图稿 | design_009 行号（最终版） |
| --- | --- |
| 从零到完整第一集业务流程图 | `design_009:53-69` |
| 命令与产物依赖图 | `design_009:71-100` |
| truth ownership 图 | `design_009:286-309` |
| 故事线→叙事点→场景→镜头关系图 | `design_009:205-224` |
| 首次进入时序图 | `design_009:540-564` |
| artifact 渐进到达时序图 | `design_009:566-583` |
| 离开后重入时序图 | `design_009:585-605` |
| 叙事点→详细分镜交互时序图 | `design_009:611-628` |
| 桌面线框 | `design_009:315-339` |
| 窄屏线框 | `design_009:631-672` |
| 文件/API/adapter/view model/component 边界图 | `design_009:680-724` |

## 5. 独立评审过程

评审代理：`/root/task2_design_review`。评审只读，不修改文件；每轮交叉核对 vendor README/实现/样例、task1、design_004—008、router 与 UI Design v2。

### 5.1 第一轮：FAIL

无 P0，7 个 P1：

1. design_009 未声明对旧“Execution 无后续操作”的增量替代范围。
2. binding 的建立时点和可信来源不足。
3. continue 未接入既有持久 claim/lease/active-turn 门禁。
4. artifact availability 与 association 混为一类；跨刷新 last-good 无 owner。
5. 多 Prompt/多 Render 的 coverage 可能超过 100%。
6. manifest 缺少 producer/consumer DTO 字段。
7. 首次进入图使用了错误 route。

另有 P2：Prompt 设置需要 allowlist；无权/不存在需统一不可见；episode-commit 不是跨文件事务；registered media 没有 vendor schema。

返工前已重新执行 Prompt Architect。修订证据：

- canonical 优先级和一次 confirmation/多次 dispatch：`design_009:9-23`。
- binding 可信建立、不可换绑和测试矩阵：`design_009:128-205`。
- coordinator/claim/lease/active-turn：`design_009:496-525`。
- availability/association/session-only last-good：`design_009:183-194`。
- coverage、producer/consumer：`design_009:157-181,269-283`。
- canonical route：`design_009:548`；router owner：`frontend/src/router/storyWorkspacePath.ts:57-61`。

### 5.2 第二轮：FAIL

第一轮问题基本关闭，剩余 2 个 P1 和 1 个 P2：

1. 当前样例只能证明 Shot→Queue，仍残留 Prompt→Render/registered media 语义。
2. legacy unbound 缺少自动补建或受控恢复 API 闭环。
3. task1 尚未同步 session-only last-good 与 producer/consumer。

返工前再次执行 Prompt Architect。修订证据：

- 真实 EP01 明确为 45 Shot→Prompt、45 Shot→Queue、0 Prompt→Render：`2026-08-05-drama-forge-ep01-task1-problem-decision-record.md:94-118`。
- 当前/未来 Render 边界、queue stable ID、duplicate diagnostic 和 coverage：`design_009:218-224,245-283,409-417`。
- legacy 自动补建和不可证明 unbound：`design_009:128-142`。
- 无路径参数 binding recovery、claim/idempotency：`design_009:448-462`。
- unbound UI：`design_009:356-360`。
- task1 session-only last-good、producer/consumer：`2026-08-05-drama-forge-ep01-task1-problem-decision-record.md:345-366,407-416`。

### 5.3 第三轮：PASS

独立评审确认无 P0/P1/P2 遗留：

- Shot→Prompt、Shot→Render Queue 与 future-only media 边界通过。
- legacy binding 自动补建与不可证明恢复闭环通过。
- session-only last-good 与 manifest producer/consumer 通过。
- 第一轮已关闭项继续通过：canonical 优先级、binding 安全、并发派发、availability/association、route、Prompt allowlist、统一不可见、episode-commit 非事务语义。

## 6. 八项质量门结论

| 质量门 | 结论 | 证据 |
| --- | --- | --- |
| 忠实还原 vendor 工作流 | PASS | `design_009:51-108`；`vendor/drama-forge/drama-forge/README.md:353-381` |
| 覆盖完整第一集产物 | PASS | `design_009:126-181` |
| 建立故事线/叙事点交互 | PASS | `design_009:205-283,350-390` |
| 保持 Dream 独立模块 | PASS | `design_009:422-440` |
| truth ownership 唯一 | PASS | `design_009:286-309` |
| 支持刷新和重新进入 | PASS | `design_009:530-605` |
| 符合 UI Design v2 | PASS | `design_009:341-348,631-672`；`docs/prd/Ink & Memory UI Design v2.pdf:4-5` |
| 无业务失败状态机扩张 | PASS | `design_009:748-760` |

## 7. 任务二结论

任务二通过。任务三必须严格按 `design_009` 实现；若实现证据要求改变 owner、binding、关联方向、continue 并发或恢复合同，必须先修订设计并重新独立评审。

本阶段只新增/修订上述三份设计文档，没有修改生产代码，也没有执行归档。

## 8. 任务三实施回链

任务三没有重新打开本记录已经通过的产品裁决。实现单元、双阶段评审、真实第一集 artifact、manifest/revision、浏览器和诚实遗留统一见：

`2026-08-05-drama-forge-ep01-task3-implementation-and-acceptance-record.md`

最终证据仍符合第三轮 PASS 的边界：Shot→Prompt 与 Shot→Render Queue 分开；Review 只读；REST 是 artifact 恢复事实；真实媒体和外部 runtime 未被 UI fixture 或文件存在性冒充成功。
