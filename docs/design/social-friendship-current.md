<!-- [Input] Actual nine Admin social contracts and original Dream public routes. -->
<!-- [Output] Current social policy/relationship state, failures and acceptance boundaries. -->
<!-- [Pos] Friend invitations, recipient decisions and authorized historical picture reads. -->
<!-- [Sync] 2026-09-15: Admin owns durable social operations; Dream preserves public behavior. -->
# 好友与邀请码现行设计

## 背景与问题

原Dream路由直接读取PostgreSQL，邀请码消费、好友关系检查与更新缺少完整并发保护。认证与生产数据归Admin后，Dream保留页面、九条公开路径及图片展示；Admin校验当前OAuth主体、实体权限，并执行业务事务。旧[十模块时序原文](history/pre-admin-user-preferences-20260915/sequence-diagrams.md)完整保存，直接SQL不再是本域现行规范。

## 目标与边界

Dream使用[统一客户端](../../backend/services/admin_data/social_data.py)消费确切DTO、operation hash与identity/unified schema；不接收acting user_id，不持有本域数据库连接。Admin的DTO→Service→Repository→Drizzle负责持久化、锁、原请求回执与审计。全部九操作仅允许用户OAuth；Thread/Run/Editor委托不能用于管理或读取好友关系。

公开响应保留整数ID、显示名/邮箱fallback的Admin结果、nullable PostgreSQL微秒时间与图片字段。Dream不重排列表、不重新选取缩略图、不加确认或额度。其他日常图片、导入、System、Agent及后台数据库入口继续单独迁移。

## 概念与规则

### 身份、配置与数据所有权

Admin从OAuth subject映射当前业务用户，不读取客户端acting user_id。URL中的friend_id/request_id仅选择目标实体；以十进制string传输，按PostgreSQL bigint校验，再还原原公开整数。timeline limit为非负JSON安全整数，原省略默认30、显式0保留；这是分页输入与序列化边界。

邀请码默认长度6、有效期604800秒沿用原行为，来自Admin显式server policy。Dream没有该配置的desired/effective/revision字段，不声称修改或应用配置；policy缺失或非法由Admin配置边界拒绝，不在Dream自签、自生成或回退数据库。生成次数配置属于Admin生成失败处理，不增加产品额度。

好友关系以pending/accepted/rejected及存在与否描述，没有revision字段或客户端CAS协议。Dream不伪造revision。邀请码状态依据expires_at、used_by、used_at判断；used_at非空的历史记录即使used_by为空也不可再消费。

### 正常流程与状态转换

| 操作 | Admin执行行为 | Dream公开结果 |
| --- | --- | --- |
| generate | 当前主体创建唯一code和expires_at，事务保存原UUID回执 | `{code,expires_at}`，微秒ISO保持 |
| use | 锁邀请码与有序用户pair，检查存在/使用/过期/自己/accepted/pending；创建pending，标记used_by/used_at，同TX回执 | `{success:true,friend_request_id,inviter_id,inviter_name}` |
| use rejected同方向关系 | 复用原rowID，将rejected→pending并刷新申请时间；邀请码仍只能消费一次 | 原整数request ID，无重复关系 |
| requests | 仅当前主体作为recipient的pending列表，Admin排序和label投影 | `{requests:[...]}`，空列表保持 |
| accept/reject | 锁pair与目标行，只有recipient能将pending→accepted/rejected；并发决策只能一个transition | `{success:true}`；其它决定返回原closed业务错误 |
| friends | accepted双方向关系，Admin投影并排序 | `{friends:[...]}`，since可null |
| remove | 删除当前主体与目标的accepted关系，单TX回执 | `{success:true}`或原错误 |
| timeline | 每次检查accepted关系；读取目标历史图片，Admin选thumbnail/image fallback与排序 | `{pictures:[...]}`；null原403 |
| picture-full | 每次检查accepted关系后读取指定date的full图 | `{image_base64}`；null/空string原404 |

同一码并发消费只能一次；accept与reject只能一个成功状态转换。原请求UUID的committed结果由Admin持久化，之后恢复返回同一结果，不再次执行关系转换。

### 失败反馈与未知提交

closed `success:false/error` 保留原HTTP400 detail，包括邀请码无效/已用/过期、自己、已是好友/申请pending、request不存在/无权限/已accepted/rejected、friendship不存在。非closed错误、错误ID/time/字段或响应shape由DTO边界返回安全错误，不显示上游message或业务正文。timeline null返回403 `Not friends or friend not found`；full falsey返回404 `Picture not found or not accessible`。

写请求timeout/断连/错误响应保持原request_id及outcome_unknown，Dream不自动重发。恢复只查同operation和原UUID的receipt：committed返回原严格output，absent仍表示无回执，不能据此认定回滚或生成新UUID重试。没有增加新的公开恢复端点或确认弹窗。所有领域写独立携带当前actor与DTO，catalog刷新失败/hash缺失在domain I/O前拒绝。

旧database九helper保留名字和签名，但在连接前抛`ADMIN_DATA_ACCESS_RETIRED/503`；不能由任意user_id获取服务权限。其余旧程序不因本域文档更新而删除。

### 影响范围与验收

影响[公开路由](../../backend/routers/friends.py)、Admin RequestAuth注册、九DTO/回执消费及旧数据库helper；页面、Agent turn、SSE、资源、Runtime、共享文件和历史正文不改。

[技术测试](../../backend/tests/test_admin_social_routes.py)走实际FastAPI入口、生产RequestAuth与DTO/MockTransport，围住Dream DB；核对九响应、原closed错误、nullable时间/整数精度、空列表、scope拒绝、actor拒绝、exact capability、unknown原回执与单POST。Admin已提供受限provider-free九操作/230断言技术回执，覆盖邀请码/pair锁和状态转换；Dream不复制该状态机作为证明。

正常本机既有账户、真实Admin可见业务记录与Browser展示另需真实业务验收。本域技术PASS不代表Google、共享FS、真实模型或全部数据库迁移完成。

当前artifact记录待修正：`friendship.timeline.input.limit.minimum`为负MAX_SAFE_INTEGER，而实际Admin Zod链`.int().nonnegative().safe()`拒绝负数，Dream同样在公开输入前拒绝。消费端保持actual原hash与运行规则；descriptor下界需要Admin后续修正并发布新hash，不能在Dream改写Admin artifact。
