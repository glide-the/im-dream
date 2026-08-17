<!-- [Input] Deck设计需求.pdf, CozeLoop prompt draft/commit source, current Deck CRUD, and Admin schema authority. -->
<!-- [Output] Pre-implementation gap analysis and keep/delete/simplify/defer decision for Deck content versioning. -->
<!-- [Pos] Deck redesign target review and implementation gate. -->
<!-- [Sync] 2026-08-17: align Deck home with the enabled, published, clean projection and keep full inventory in Settings Work. -->

# Deck 影响范围与编码前目标审查

## 1. 需求与现状差异

CozeLoop 核对基线为官方仓库 commit `09e36aae6aa3c9275f119cc64e59d9414e6c1e0b`：

- `frontend/.../prompt-submit/index.tsx`：首次提交直接收集版本信息；后续先展示 diff 再提交。
- `frontend/.../hooks/use-prompt.ts`：`SaveDraft` 维护可变 draft/base version；提交与保存草稿分离。
- `backend/modules/prompt/infra/repo/manage.go`：commit 事务锁聚合根、读取 draft、创建不可变 commit、
  删除/推进草稿与 latest；失败整体回滚。

IM 不复制 Prompt 工作台和 semver 命名，只复用该生命周期，并以更易懂的 Deck v1/vN+1 呈现。

| 单元 | 最新要求 / CozeLoop 参考 | 当前实现 | 本期结论 |
|---|---|---|---|
| 新建后更新 | 新建后是可恢复草稿，首次显式提交才产生版本 | 只创建 Deck 并打开弹窗，无内容版本身份 | 新建为“未发布·草稿 r1”；提交后为 `Deck v1` |
| 弹窗修改 | 所有表单字段先保存草稿，显示未提交状态 | Deck/Voice/插件引用分散写入，不会产生聚合版本状态 | 同一 `deck_id` 作为草稿聚合根，任一受管变更递增 `draft_revision` |
| 版本提交 | 先预览差异，再确认版本信息 | 仅有 runtime plugin semver / binding `rN` | 增加无写 preview 和 CAS commit；首次 `v1`，后续 `vN+1` |
| 版本记录 | 主时间线是不可变 Deck 内容 snapshot | 面板主时间线是 binding history | 内容 `Deck vN` 升为主时间线；插件 semver/digest/binding 只作版本详情 |
| 并发与失败 | 不覆盖远端，失败保留草稿与原发布版 | 只有 binding CAS | commit 校验 `expected_draft_revision + expected_base_version`；409 要求重新 preview |
| 页面所有权 | Deck 快速入口；参考图是 Settings Work 管理布局 | 搜索/摘要/列表/开关曾混在 Deck 主页面 | 主页面两处只消费“已启用、已有发布版本且无草稿变更”的同一投影，快捷区最多 14 个；完整管理移入单一 Work 分类 |

## 2. 必须删除、修改、复用和新增

| 结论 | 内容 | 理由 |
|---|---|---|
| 保留 | 原 `POST /api/decks` 创建并按真实 ID 打开维护弹窗 | 这是已验证的 Deck 新增业务入口 |
| 保留 | 元数据、Chat/Dream Agent 类型、Agent CRUD/Prompt/启停/图标/颜色、Claude 插件引用、精确 runtime plugin 选择 | 都是 Deck 自有内容，必须进入 snapshot |
| 删除 | 把 `运行 v1.0.1 / 配置 r1` 当成 Deck 主版本的页头与主时间线 | 这两者只是 snapshot 内的运行事实 |
| 简化 | 不复制一套 `deck_drafts` 内容表 | 现有 `decks / voices / deck_claude_plugin_refs / active binding` 已是可变的规范草稿；只需聚合 revision 和不可变 commit |
| 新增 | Admin Drizzle `dream.deck-content-versions.v1` capability、Deck 草稿 revision 字段、append-only `deck_versions` | 不得在 Dream 中做 runtime DDL |
| 新增 | version state / preview / commit / history API 和内容版本 UI | 完成创建、更新、提交、历史闭环 |
| 删除 | Workflow、Agent 编排、Prompt/Memory 工作台 DOM/状态/接口 | 不属于 IM Deck 边界 |
| 延期 | 市场、注册、发布市场、安装和分发治理 | PDF 第 3 页明确暂缓，统一收口到 `docs/design/deck-register/` |

## 3. 数据与业务影响

- **前端**：Deck 主页面正式可用投影（已启用、已发布、无草稿变更），快捷区最多 14 个并区分系统内置；Settings / Work 三 tabs 与完整 Deck 列表；维护弹窗草稿、显式提交和折叠版本历史。
- **后端**：所有受管变更与 Deck 聚合行锁定顺序一致；变更成功后递增草稿 revision；commit 在同一事务中读取完整 snapshot、比较 CAS/hash并追加版本。
- **数据库**：Admin 前向 expand migration；不修改历史 migration，不在 Dream 启动时建表。
- **API**：旧 CRUD 保持；新增内容版本 API；Schema capability 未发布时版本 API fail closed，不伪造版本。
- **历史数据**：存量 Deck 获得默认 `draft_revision=1 / latest_version=0`，不自动生成虚假 `v1`；首次显式提交才生成真实快照。
- **Thread**：本增量先交付 Deck 内容版本；存量 Thread 仍不自动升级。Thread snapshot FK/apply receipt 需后续独立 Admin expand，不在本轮偷渡。

## 4. 风险与兼容策略

1. **部分 snapshot**：Voice/插件/binding 写入若不锁 Deck 聚合根，commit 可能读到中间态。所有受管写入统一先锁 Deck 行。
2. **假脏状态**：等价写入不得递增 revision；commit 再以 canonical hash 拒绝 `no_changes`。
3. **滚动发布**：Dream 的旧 CRUD 在 capability 缺失时继续工作；新版本功能按明确 Schema capability fail closed，不依赖环境名。
4. **误升级 Thread**：Deck 发布不改写存量 Thread；本轮不增加批量或自动更新。

## 5. 设计目标审查（编码 Gate）

| 审查项 | 结论 | 证据 / 收缩 |
|---|---|---|
| 符合最新 PDF/参考图 | 通过 | 已启用且已发布、无草稿变更的图标用于 Deck 入口；搜索、扁平行和开关只用于 Settings / Work 右侧 |
| 删除 Coze 非 IM 工作台 | 通过 | 只保留草稿/显式提交/差异预览/不可变历史思想 |
| 版本信息清晰但不过量 | 通过 | 列表固定一行 `Deck vN/未发布 + 草稿状态`；运行细节不抢主轴 |
| 版本历史不默认常驻 | 通过 | 页头触发，默认折叠，展开为布局流内侧区 |
| 历史 Thread 不自动升级 | 通过 | commit 仅产生 Deck snapshot，不写 Thread |
| 市场需求未误实现 | 通过 | 无入口、状态或占位按钮；详见 `docs/design/deck-register/` |
| 无伪后端功能 | 通过 | 先增 Admin Drizzle capability，Dream 再依赖；不复用 runtime snapshot 冒充 |
| 无重复入口/状态/组件 | 通过 | Work 复用 DeckManager、ConnectorSettingsSection、ClaudePluginAdminPage；新建和修改共用弹窗 |
| 可以用更简单结构满足 | 通过 | Settings 只新增一个 Work 项；三类是内部 tabs，不复制左栏或数据 owner |

**Gate 结论：通过。** 实施必须按上述最小聚合模型执行；不得再回退为 binding-only 版本面板。
