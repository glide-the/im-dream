<!-- [Sync] 2026-09-15: record complete Admin Deck list modes and remaining SQL source candidates. -->
<!-- [Sync] 2026-09-15: owned detail read is tracked in its current design. -->
<!-- [Input] Five published Admin Deck write contracts and original Dream public responses. -->
<!-- [Output] Current update/delete/publication/collection/parent-sync rules and validation. -->
<!-- [Pos] Deck write design; Admin owns durable policy and transaction execution. -->
<!-- [Sync] 2026-09-15: consume five writes and preserve closed dependency feedback. -->
# Deck 写操作现行设计

## 背景与问题

原公开 Deck 写路由直接访问 Dream PostgreSQL。发布先读取再写入，收藏复制与计数分为两次调用。迁移后，[Dream 消费端](../../backend/services/admin_data/deck_mutation_data.py)发送明确的业务 DTO，由 Admin 校验主体、锁定实体并在原请求回执的同一事务中完成操作。

## 目标与边界

迁移 PUT/DELETE `/api/decks/{deck_id}` 和 POST `/api/decks/{deck_id}/publish`、`/fork`、`/sync`，分别使用 deck.update/delete/toggle-publication/collect/sync-parent。需要当前用户 OAuth、dream:write、五项实际 operation hash，以及 identity/unified/canonical-storage/content-versions 四项 exact schema。Runtime 委托不能管理 Deck。

Deck列表/详情另按[现行读取规则](deck/deck-detail-version-history.md)迁移；Deck 创建、默认初始化/修复、全局安装目录与文件证据仍保留迁移依赖。原内部数据库函数和技术 fixture 不因本稿删除。Agent、SSE、资源准入、共享文件、Runtime 配置及版本 pins 不受本阶段影响。

## 概念与规则

### 输入与配置状态

URL 选择 Deck，Admin 从 OAuth subject 确定 actor；body 不接受 user_id 或 actor_id。更新沿用 None 省略规则，空文本、false、0 是明确更新值；只序列化提供且非 None 的字段。闭集输入拒绝错误类型、非有限数、超出 JSON/TypeScript 安全整数边界的排序值，安全 422 不回显正文。

default 由原 Admin 业务 policy 决定；desired 是本次明确更新的字段；effective 是已确认事务中的保存值。响应不新增 CAS 或 policy revision；原 draft_revision 仍通过[内容版本接口](../../backend/routers/deck_versions.py)查询。HTTP 未确认不能表示配置生效；技术数值边界不是产品配额。

### 正常流程与状态转换

| 公开操作 | Admin 执行 | Dream 保留的结果 |
| --- | --- | --- |
| update | 归属/行锁、字段比较、更新与 draft 推进、同事务回执 | changed:true → `{success:true}`；false 原 404 |
| delete | 归属/锁、派生 Deck/Chat/不可变历史/引用检查，删除可变记录与回执 | changed:true → `{success:true}`；false 原 404 |
| publish | 锁定当前 Deck 后切换 publication；发布沿用 parent detach 规则 | `{success:true,published}`，无需 Dream 预读 |
| collect | 校验系统/已发布 source 与 self 限制、复制 Deck/Voice/refs、计数和回执 | `{deck_id}`，一项 Admin 操作 |
| sync | 校验 owned fork/parent、覆盖原同步字段与 Voice、清除本地内容标志、推进 draft | `{success:true,synced_voices}` |

Dream 不复写比较、锁、复制、计数或事务算法。更新字段未变化的处理、发布/同步的状态变化由 Admin 原业务规则执行，不增加确认或重试路径。

### 失败反馈与未知提交

update/delete 不成功保留 404 `Deck not found or permission denied`。系统默认不能发布、不能收藏自身或私有 Deck 仍返回原安全 409；fork/source 不存在原 404。sync 的归属或 parent 缺失保持原 400。

DECK_DELETE_BLOCKED 的 details 只接受 reason 四枚举：child_decks、related_threads、runtime_history、referenced_records，并复用原 DeckDeletionConflict 的固定反馈。details 省略时使用原通用引用冲突反馈。统一错误边界按 code 校验 details：只有该四枚举和原 DECK_VERSION_CONFLICT 的两项 revision DTO 可保留；null、额外字段、错误 code/形状、未知 reason 均拒绝。上游 message、数据库异常和正文不返回用户。

超时、断连、错误响应保留 original request_id/outcome_unknown。恢复只查询同 operation、原 UUID 的 status/result 回执；absent 不表示 rollback，不能触发新 UUID 或自动重发，committed 只恢复原闭集结果。

### 影响范围与验收

[公开路由](../../backend/routers/voices.py)、请求 DTO、RequestAuth 注册、公共四 schema 检查与错误详情 DTO 受影响。Version/Voice 复用原四 schema 检查，原身份匹配和返回语义保持。[技术测试](../../backend/tests/test_admin_deck_mutation_routes.py)调用实际 FastAPI/Auth/DTO/MockTransport，禁止公开 Dream DB，覆盖五结果、None/空值/false/0、单次 collection、无发布预读、四删除原因、严格错误详情、malformed 结果、权限/capability 和未知原 UUID。

原 Version409、Voice、Session、Deck default/sharing/deletion 技术 fixture 同批回归，原历史稿字节保留。技术通过不等于本机普通服务、真实账户、模型或 Admin 可见业务记录的验收；该业务验收仍由协调任务执行。
