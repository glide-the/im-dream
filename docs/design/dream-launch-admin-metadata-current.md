<!-- [Sync] 2026-09-15: default Workspace is now registered76 and consumed; production launch composition stays pending. -->
<!-- [Input] Registered launch75/77 metadata contracts and original Dream source/application/dispatch code. -->
<!-- [Output] Current typed consumer and source seam rules, states, failures and wiring gaps. -->
<!-- [Pos] Metadata migration preparation; original production launch design remains applicable. -->
<!-- [Sync] 2026-09-15: prepare source/claim/finish without claiming old endpoint SQL has migrated. -->
<!-- [Sync] 2026-09-15: record released launch75 component acceptance while retaining production wiring gaps. -->
<!-- [Sync] 2026-09-15: prepare independent failed-envelope DTO/receipt, preserving original production SQL gaps. -->

# Dream launch Admin metadata 消费现行设计

## 背景与问题

Admin目录75已注册source.ensure、dispatch.claim和dispatch.finish。Dream原application在prepare后计算source fingerprint与UUIDv5，确保source后执行PF/Run，最后dispatcher先提交claim、再读Voice并调用Runtime、独立finish。旧endpoint目前只传actor/Workspace字符串，未将当前OAuth actor交给新消费者；prepare、failure recorder及其他metadata仍依赖SQL。

## 目标与边界

准备[类型消费者与原source Protocol adapter](../../backend/services/admin_data/launch_metadata_data.py)，供后续生产composition root接线复用。原三个operation使用OAuth dream:write、identity/unified两项exact schema与实际版本/hash；新注册77 failure envelope另见下方授权规则。HTTP service credential和user token继续分别传输。

当前仅完成类型与seam技术准备：新adapter尚未被生产endpoint/builder选择。原公开launch、source、claim/finish SQL仍存在；不能把注册或MockHTTP用例当作生产迁移、隔离PG全链通过或正常模型验收。default Workspace已注册76并接入公开Workflow ingress，不以Preferences五字段替代SystemConfig。完整prepare/Agent/model/binding、Voice prompt读取、failure recorder和Runtime配置所有权继续追踪。

## 概念与规则

### 正常流程与状态

source输入只含Workspace/Deck、required nullable Agent、goal和业务key，复用原command字段约束与边界空白validator，不normalize。adapter只允许服务端immutable AdminRequestActor/dream:write；原ensure_source Protocol签名保持，actor必须等于当前canonical user。它把原callsite给定的expected thread/message/fingerprint用于回复匹配，不向Admin发送caller provenance。HTTP调用经worker thread，结果转为原DreamLaunchSource；不伪造message time。原application仍执行conditional Agent fingerprint和UUIDv5校验，先prepare后source/PF/Run顺序不改。

claim只传owned Run lookup与原Dream instruction_text；保留instruction原文。输出claimed=false只含Run/thread/message；claimed=true还含issued claim ID、完整10字段context以及raw parts_json/metadata_json。Context复用原冻结模型、Pydantic trim和正安全整数，nullable Agent必须提供。消费者匹配Run/source IDs和全部原Context字段；parts等于原instruction text，metadata匹配actor/Workspace/Run/thread/context及Runtime dispatched状态，不含claim lease字段。JSON使用标准parser拒绝非有限数，不重序列化原文本，不复制Runtime parser/state machine。

finish只传Run lookup、issued claim ID和accepted boolean；回复匹配Run/source并保留finished=false。pending/dispatched状态、lease/CAS和数据库提交由Admin处理，Dream不生成claim ID、不设置TTL、不检查当前clock，不调用Voice/Runtime。后续接线必须保持原claim COMMIT→Voice/Runtime→独立finish顺序以及before_claim callback位置。

### 失败反馈与原请求回执

缺少schema/hash或actor scope时在operation前拒绝。已发出的timeout、DTO或来源/上下文错配保留原UUID/outcome_unknown=true，不重发；原source usecase立即停止，不能继续PF/Run/dispatch。Goal/instruction/parts/metadata从repr排除，异常只含安全code/status。

服务器显式用同operation/input/UUID读取原通用两态receipt。absent无result、不表示rollback；committed完整result重做对应来源/Context检查。Admin只在当前stored lease匹配且fresh时返回原claimed=true；stale receipt返回409 DREAM_LAUNCH_CLAIM_STALE，Dream不自动reclaim、resume或dispatch。PF独立三态reader和其他领域的generic两态parser保持。没有新增公开恢复路由或Runtime控制通道。

### 影响范围与验收

修改范围为新类型消费者/source adapter、request-auth注册及受影响文档。原application、endpoint、builder、路由、source/dispatcher SQL实现、Runtime/资源LKG/共享文件和TMPDIR协议保持。

[技术测试](../../backend/tests/test_admin_launch_metadata.py) 使用实际client/DTO/HTTP和原application usecase source seam，fence Dream SQL；覆盖normal/replay/无Agent fingerprint、unknown停在PF前、claim真假/10Context/raw JSON/错配、finish accepted/false、同UUID receipt/stale/no resend、schema/hash/actor及原codepoint约束。它不证明真实OAuth签名、公开endpoint接线、实际Admin COMMIT/权限或普通账户/模型业务。

主协调已释放launch75隔离组件验收：remaining37/accepted1只读跳过、21原GET与974断言exit0；11事务故障/3实际final COMMIT丢响应308断言exit0；SELECT-only保留检查19断言exit0。Root只读核对命令回执和聚合计数，未重跑；原首轮命令exit1及已提交source保持。它们证明各自组件范围，不等于Dream旧endpoint接线、完整prepare/Runtime或正常数据库/账户/模型验收。
### 独立 failure envelope 类型准备

背景与问题：原 DreamLaunchFailureRecorder 在 Run FAILED 提交后，以独立事务写 source message 的 dispatchStatus=failed、dispatchErrorCode，并移除 claim 字段。Admin77 只增加 dream-launch-failure.envelope；Run fail 仍是 lifecycle authority，不存在合并提交或失败时补建 schema。

目标与边界：新增的闭集 typed input 只含服务器 Workspace/Run/error_code，error 保留原 truthy text，不发送 actor/source/context/metadata/status/codec 路径。消费者不生成 metadata，也不调用 Runtime。新操作 v1/write/dream:write/background=null、实际 hash5967ae40f60858553f27f43dd83f021f93928e7c25c582d2e711d68df4d4e042，复用 identity/unified exact schema；Admin 从 current owned FAILED Run 推导 source 和微秒时间后执行固定 codec 与独立 receipt/audit UOW。

概念与规则：原服务器 source IDs 存于 immutable LaunchFailureExpectation，用于匹配完整 updated/Run/thread/message/error 五字段回复；nullable IDs 与 empty/raw strings 不 trim 或猜测 UUID。updated=false 是完整结果，updated=true 必须含两个非 null source ID。Run/error/source 错配或 malformed reply 保留原 UUID/unknown，不能继续假定 metadata 已提交；显式原两态 receipt 只查同 operation/request/input 并重做绑定，absent 不重发。Admin 允许 OAuth 或同 Thread/Run server-persistence 执行该写；original GET 只允许 current-owner OAuth dream:write，不增加 Runtime recovery authority。历史 original receipt 恢复不覆盖后续 claim lease。

影响与验收：仅准备现有 typed domain 与 request owner 注册，原 dispatcher/failure recorder 仍缺 Admin turn owner，生产 SQL 尚未替换。后续必须保持 Run fail COMMIT → 独立 failure envelope 的顺序和后台异常隔离，不用 user ID/shared service key 代替授权。[技术套件](../../backend/tests/test_admin_launch_failure.py)覆盖原 failed replay/raw text、full nullable reply/source mismatch、schemas/hash/errors、unknown 与 original receipt；它不证明 primary77 尚待完成的隔离 fault/COMMIT-loss 验收，也不证明正常用户/model/Runtime 路径。
