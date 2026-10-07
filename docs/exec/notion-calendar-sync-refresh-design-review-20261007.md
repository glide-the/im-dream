<!-- [Input] 当前 Calendar PRD/正式交互稿、四阶段增量、公开 DTO 与同步源码，以及主 Agent 的正常服务恢复观察。 -->
<!-- [Output] Notion 可见快照发现和简约正文的独立设计门禁、必修项、验收边界及实施技术结果复核。 -->
<!-- [Pos] 独立评审证据；不替代 PRD/正式稿、实现或实际测试回执。 -->
<!-- [Sync] 2026-10-07: 保留R1–R4及设置恢复准入；追加实际71/11/旧overview通过，正常发布与新UI真实验收边界保持。 -->
# Notion 同日快照发现与简约正文独立设计评审

**最终门禁：可实施。R1–R4 已同步并通过独立复核，批准本仓可见版本发现、请求恢复及简约正文增量；永久跨进程自动恢复仍阻塞，未批准接管。** 已通过的浮空外壳设计保持；本评审未修改生产代码、未执行自动化测试，也不将 Admin 依赖提案作已通过合同。下文保留首轮“修改后可实施”的原因和要求，最终复核见 §5。

## 1. 评审输入与允许范围

Optimized Prompt：独立核对现行正文、真实 DTO、请求提交检查和同步机制；明确最小可见版本发现、数量/恢复反馈及并发边界，保留原业务和历史证据；只交付设计门禁。

- [现行 PRD](../prd/calendar/calendar-right-panel-tabs-prd.md) §3.1、正文骨架与验收矩阵。
- [正式交互稿](../design/claude-agent/calendar-right-panel-tabs-ui-design.md) §4.5–4.7及正常/异常/状态图。
- [影响评估](./notion-calendar-sync-refresh-20261007.md)及[四阶段过程](../design/claude-agent/calendar-sync-refresh-workflow-20261007/README.md)。
- `frontend/app/_dream/components/CalendarNotionPanel.tsx`、`frontend/app/_dream/api/resourceConnectorApi.ts`、`backend/notion/{factory,sync_policy,sync_scheduler}.py`；只读核对 Admin `app/lib/dream/notionConnectorRepository.ts`。

方向合理：复用公开 GET connectors 的已有版本字段和 Calendar 的具名日期检查周期；仅 active、登录且页面可见时检查；同上下文且已成功加载的同版本不重读；后台成功后重新投影当前日期。正文保留非空分组、标题、上游时间、单一安全外链及必要恢复入口，不扩 API、schema、选择/同步/正文读取权限或调度框架。

## 2. 实施前必修

| 编号 | 当前缺口与事实 | 最小修正及接受标准 |
| --- | --- | --- |
| R1 数量 | PRD §3.1.6、正式稿 §4.5及过程/exec明确删除正常 total；原用户验收要求数量展示和双命中只计一次 | 正常保留**一次**简短实际唯一总数，如标题旁“2 篇”；分组不重复数量，不渲染空组。partial 只报告实际已知数量，已知 0 仍为部分结果，不能冒充正常空。DTO counts 保持。正文、骨架、过程与矩阵一致。 |
| R2 恢复事实 | 现行稿反复写“502 尚未恢复”，已被后续正常服务观察更新 | 保留首次公开立即同步 HTTP 502 和未推进快照的失败原文/时间顺序，再追加自动 worker 后续成功：`snap-20261006T214820Z-dc9ee898`，last_success `2026-10-06T21:48:20Z`（本地 10-07 05:48），status applied；观察的 next_sync `22:03:20Z`（06:03）不是保证执行时间。不能改称手动请求返回成功、不能改称永久 crash 恢复已实现。现行正文记录已创建 Admin 依赖任务及后续 Dream 集成门禁，历史稿不覆盖。 |
| R3 updatedAt 所有权 | 正式稿要求 updatedAt 变化即清空重读，同时承诺同步状态变化只提示/版本更新保留列表。Admin `patch` 每次无条件更新 `updated_at`，`saveSnapshot` 同样更新；factory.sync 的 started/succeeded/failed 都经过这些操作 | 保留现有 updatedAt 强提交检查。当前 DTO 没有授权/选择独立 revision，不能凭同版本或 sync 状态猜测 changed updatedAt 仅来自同步，也不能直接保留旧授权数据。最小合同明确：**updatedAt 未变且 actor/connector/auth/选择/date/zone 全一致，才允许保留列表；任一变化按未知上下文取消、清空并重读，即使由同步 patch 引起。** 同步提示更新与零 documents 规则仅在全部上下文未变时成立；不承诺未知上下文转换期间列表/滚动不变，原同日页签状态 owner 不卸载。若另提区分机制，须先有服务器可验证字段及独立门禁。 |
| R4 失败后同版本恢复 | “观察到新版本→读取”及“同版本不再读取”未区分已观察与已成功加载；409 和第一次读取失败后的下一次检查可被同版本去重吞掉。现有 requestedRef/verifiedRef 也是发起时记录，不能直接复用为成功标志 | 明确分别记录 latest observed 和 last successfully loaded context/version；仅成功投影可推进 loaded 标志。读取失败或快照 409 后仍需读取，下一正常检查周期/显式刷新恢复，不紧循环；以实际 documents 响应版本提交。已接受快照的远程校验去重与显式 refresh nonce 独立，临时校验失败不因每次 probe 自动重跑同版本远程调用。补齐异常图/状态图与验收：首次读取失败后同版本恢复、V1→V2 读取冲突后探测仍 V2、probe V2 而实际响应 V3。 |

版本为不透明身份，不排序或用 last_synced_at 替代。缺失/非法版本字段不能当作已确认的相同版本，也不能写入成功加载标志；实现须沿现有 DTO 校验/恢复语义处理，不虚构版本或正常空列表。

## 3. 保留的安全门禁

`factory.today_pages` 在提交前核对当前授权、updated_at、选中范围、凭证文件身份、快照版本及日期上下文。新增前端 probe 不能降低这些服务器检查；probe/read/verify 都须取消与 generation/context 提交检查，A→B→A、关闭、登出和页面隐藏不允许旧响应覆盖新状态。隐藏不开始新阶段，允许原已开始读取只向仍相同上下文提交。未改变的轻量检查不取消有效的在途读取/校验；Retry-After 冷却覆盖 probe/read/verify。

`sync_policy_is_due` 仍跳过 persisted syncing；进程内 `_SYNC_LOCKS` 和每次 CLI timeout 不能证明跨进程旧 writer 已停止。永久自动恢复仍依赖 Admin 原子 owner/lease/fencing 和快照/状态条件提交，Dream 只能消费已发布 capability。已创建依赖任务 `01a11331-2830-7220-bf91-4a144acfd62f`；本次真实同步成功仅闭合本次恢复观察，未闭合该依赖。禁止按 age、PID 时间或本机无锁抢占，也不新增 Dream DDL。

日历只投影已同步且在当前选择范围内的索引；选中数据库包括同步 query 得到的子 page。新 page 必须由成功同步发现，版本 probe 和今天已有更新项的 metadata 校验都不能枚举尚未索引的新 page。历史日期仅按上游创建时间；保留半开区间、夏令时和双命中单计数，不复制正文读取路径。

## 4. 必须执行的验收

独立设计批准后由 Luna 执行实际命令，回执保存首次失败/修复/退出码；本评审不预判通过：

- 公开真实 DTO：后台 V1→V2，无浏览器事件也能显示同日新行；相同有效 context/已加载 version 零 documents/remote；实际响应 V3 覆盖 probe V2。
- 初次 documents 失败、快照 409 后同版本下一周期恢复；probe 临时失败保留允许结果；401/归属/选择/updatedAt 变化清空；429 冷却且不忙循环。sync-only patch 的 updatedAt 变化按明确合同验证。
- active/page-visible、切走返回、A→B→A、日期/时区/午夜、关闭/登出迟到响应；隐藏零新查询；自动检查与手动刷新分代，未变版本不反复远程验证。
- 正常一次总数、非空组、双命中单计数/双标识、partial 已知 0、URL 无效、单标题外链完整可访问名称；syncing 不伪造运行进度，必要提示/管理入口去重。明暗/系统主题及 390/430/1024/1440 布局、焦点和短长高度。
- 原 Calendar、任务、日记、Notion 完整三份旅程保持；计数/版本发现不能替代原权限、异常和无写调用断言。相关静态检查、Markdown 清单/引用、Mermaid、diff check，清理仅本轮自建资源。

本轮只读命令用于核对源码/文档，未调用真实 select/sync/body，未读取凭证或正文，未启停服务。设计资料的链接和 Mermaid 等机械验证须纳入后续实际回执，不能称为功能或真实业务验收。

## 5. 修正后独立复核与最终门禁

复核 Optimized Prompt：逐项检查冻结的 PRD §3.1/骨架/矩阵、正式稿 §4.5–4.7与三幅业务图、四阶段过程和影响记录 §9，确认首轮缺口闭合；仅裁决设计，不预判实现或测试结果。

| 首轮项 | 已复核的现行合同 | 裁决 |
| --- | --- | --- |
| R1 | 正常标题旁一次 `counts.total`，partial 标“已知数量”；组计数/空组/重复 Open 移除。PRD 窄屏骨架、正常时序及阶段2/4均一致；双命中仍单计数 | 通过 |
| R2 | PRD 和正式稿保留首次手动502，并追加本地05:48后台成功、今日正常UI命中；exec §8保存对应快照/数量与安全回执位置；记录已创建 Admin 依赖并明确未闭合永久接管 | 通过；真实恢复观察由主 Agent 正常服务回执提供，本 reviewer 未重复真实操作 |
| R3 | updatedAt 变化（包括 sync patch）按未知上下文取消、清空和重读；只完整相同 context 允许 LKG/滚动保留，不能凭相同 snapshotVersion 放宽。原面板和业务状态 owner 不卸载 | 通过 |
| R4 | observed、成功 loaded、读取 in-flight、needsRead 与 verification 完成键分开；失败/409不推进 loaded；下一正常60秒周期/显式刷新才恢复，Retry-After 抑制新阶段，不因 error effect 紧循环。同版本临时远程校验失败仍按原显式 Refresh 恢复 | 通过；异常/状态图已覆盖 needsRead、无允许LKG的 NeedsRetry 与成功提交 |

**开放实施范围**：既有前端公开 DTO 的严格版本投影、active/authenticated/page-visible 的串行轻量检查、上述请求所有权与恢复、单次总数/非空分组/单标题外链及必要反馈。无新增后端 API、schema、同步动作或正文权限。缺失/非法 connector 版本不能充当“已确认不变”；documents 返回的合法 partial/无快照状态仍需按原 DTO 展示，不伪造正常空。

§4 的完整旅程和实际机械检查仍全部待执行；背景同步成功的旧观察不证明新 probe 已实现。Admin 所有权 capability、Dream 接入及跨进程故障旅程仍是另一个明确门禁，未获本评审通过。保留本文件首轮缺口和所有历史稿；仅由其他负责 Agent 登记相邻 `.folder.md`，不覆盖其工作区改动。

## 6. 主任务实施技术复核

以上 §5 末段保留设计批准当时的待执行状态。本节记录后续实际结果：Luna 在冻结副本执行新增 focused 9/9、完整三份 spec 63/63，均退出 0；构建、TypeScript 与 ESLint 退出 0。精确命令、三轮失败/修复时序及限制见[执行记录 §11–13](./notion-calendar-sync-refresh-20261007.md)，不覆盖设计历史。

主 Agent 已查看当前源码实际运行生成的 `output/notion-calendar-sync-refresh-20261007/visual/calendar-notion-light-1440-natural-short.png` 和 `calendar-notion-dark-390-normal.png`：桌面右侧保持圆角浮空外壳并自然短于月历；内部没有重复容器边框，数量只显示一次，非空分组与单一标题链接保持。窄屏暗色的长标题压力截图仍处于视口内，滚动与长内容由完整旅程验证。

这是隔离技术验证与结果复核。正常账户今日文档先前已实际恢复；新精简界面的正常 Chrome 复核受诊断 harness 超时限制，未以此冒充真实业务验收。永久同步恢复、正常后台 capability 发布、旧 writer drain 及服务切换仍由后端集成和发布门禁所有，本前端通过结论不关闭它们。

## 7. R2 设置页恢复实现复核

主 Agent 对 `ConnectorNotionDetailPage.tsx` 的冻结源码及新增完整旅程进行了独立只读复核。仅 `ResourceConnectorApiError.context.selection_saved === true` 表示已确认保存；此后使用现有唯一 Notion 解析器回读同一连接器 ID，读取失败不会改称未保存。无确认标记的失败保留本页草稿并说明保存状态未确认。手动同步的 busy 反馈不声明范围保存结果。

请求提交检查绑定账户、连接器、请求代号和 AbortController；账户或连接器变化、卸载会失效旧请求及旧冷却。合法 Retry-After 只使现有按钮在等待结束后恢复可用，定时器不发送请求或自动重试。目录发现和保存后的回读也检查当前请求上下文。新测试覆盖公开设置入口的选择、保存失败、回读、返回重开、手动忙碌、等待及显式成功，以及严格标记、非法等待时间、迟到响应与账户切换。

上述实现允许交给 Luna 验证；这项源码复核不代表新设置旅程、构建或真实业务验收已通过。原日历 63 项技术验证不能代替本轮设置页验证，结果须追加实际命令和回执。

## 8. R2 最终技术结果复核

专属Luna实际新Settings8/8、Calendar异常恢复7/7、完整四spec71/71、最后Scheduled诊断调整后完整11/11、旧Settings overview1/1全部exit0；freshbuild、TypeScript和focusedESLint均exit0。主Agent读取实际71/11输出及退出码，复核handoff过滤只匹配具名导航阶段的精确列表GET与取消错误，取消可有可无，其他网络错误继续失败；没有放宽目标Thread/URL/隐藏/无unexpected业务断言。完整命令与首次失败保存在[执行记录§14.5](./notion-calendar-sync-refresh-20261007.md#145-r2-完整旅程最终实际回执)及其指定原始回执目录。

源码/技术门禁通过。Calendar现行三个Mermaid与既有实际parse/render回执的内容SHA一致；本轮未重复启动浏览器。正常新UI的Chrome复核限制、Admin精确capability尚未发布、旧writer drain及服务切换缺口保持，不能将本评审结论写为整体真实业务验收或永久恢复已生效。

## 9. 当前后端状态与四图同步复核

主Agent独立读取后续PRD§3.1、正式稿§4.7及当前正常/异常图：已与实际Admin四精确操作、先接受后缓存、只读接受identity恢复和updatedAt强提交检查一致；旧进程锁/跳过流程明确为旧正常服务的历史事实。保存两份pre-backend-status完整历史，旧异常和state图字节保持。Luna对现行总四图实际parse/render全部通过，122作用域引用0缺失、历史与diff检查exit0，详见[执行记录§15](./notion-calendar-sync-refresh-20261007.md#15-calendar-当前正文与后端状态同步纯文档新四图已实际检查通过)。§8三图结论保留原时点，不替代当前四图回执。生产/业务测试没有新增变更；正常发布缺口和整体未完成状态保持。
