<!-- [Input] Actual four Admin Voice contracts and original public Voice request/response fields. -->
<!-- [Output] Current Voice creation/update/delete/collection, Memory and revision behavior. -->
<!-- [Pos] Public Voice mutation design; Deck/default/install/background migration remains separate. -->
<!-- [Sync] 2026-09-15: Admin owns durable Voice mutations; Dream preserves public projections. -->
# Voice CRUD 现行设计

## 背景与问题

原四条公开Voice路由直接访问Dream数据库，混合归属校验、Memory默认、排序和Deck draft推进。Admin成为唯一数据服务后，Dream保留原公开字段和响应，由[消费端](../../backend/services/admin_data/voice_data.py)发送闭集DTO；Admin校验当前主体并执行业务事务。

## 目标与边界

仅迁移POST `/api/voices`、PUT/DELETE `/api/voices/{voice_id}`、POST `/api/voices/{voice_id}/fork`。Admin已发布voice.create/update/delete/collect，必须匹配identity/unified/canonical-storage/content-versions四项exact schema和actual operation hash。全部用户OAuth；Runtime Thread/Run/Editor委托不能管理Voice。

Deck CRUD/default/plugin evidence、其他Voice读取/运行消费及原database内部/fixture SQL继续列入迁移清单。本阶段不改变Agent、资源、SSE、共享文件、Runtime配置或版本pins，也不删除历史程序/测试。

## 概念与规则

### 输入、Memory与配置状态

create要求deck_id/name/system_prompt，原可选name_zh/name_en/icon/color和Memory省略或null转为wire required nullable；order_index由server处理，公共body不能提供。Admin校验ownedDeck，并使用配置policy计算默认Memory和顺序；Dream不重新制造默认值。原create Memory空对象与null均采用Admin默认。

update保留原None省略规则；emptytext、emptydict、false和0仍为desired字段。Dream只发送本次提供且非None的字段。wire optional nullable允许明确null，但公共None沿用保留语义；默认None不能被序列化成更新字段。复用Editor已有present-fields serializer，Editor自身null检查保持。

Memory对象用Python JSON转rawstring，保留float、negativezero、bigint词法；update沿用sort_keys，create沿用原顺序。公开对象必须finite，NaN/Inf/错误形状在typed输入边界安全422，不回显正文。原stored Memory转换、语义比较和持久化属于Admin，不在Dream再写canonical/hash算法。

配置default来自Admin policy；desired是本次明确的公共字段；effective为Admin事务确认后的保存值，未确认不能当作生效。四mutation响应不返回独立policy revision或新CAS字段；原Deck draft_revision通过既有[版本接口](../../backend/routers/deck_versions.py)查询。不能把任意技术常量包装为产品配额。

### 正常流程与状态转换

| 操作 | Admin业务行为 | Dream原公开结果 |
| --- | --- | --- |
| create | ownedDeck锁、默认Memory/order、新Voice与draft推进、原receipt同TX | `{voice_id}` |
| update | ownedDeck/Voice锁、比较明确字段、只更新变化、同TX回执 | changed:true→`{success:true}`；false原404 |
| delete | ownedDeck/Voice锁、外键/引用检查、删除与draft推进、同TX回执 | changed:true→`{success:true}`；false原404 |
| collect | 校验target ownedDeck与source可读/可收集；锁实体并复制到target，draft与receipt同TX | `{voice_id}` |

文本内容变化设置has_local_changes；enabled/order/Memory不据此设置内容标志，但版本相关变化推进draft。thread_id只绑定当前主体可用Thread，单独变化不推进draft；值未变不刷新时间/draft。上述比较与事务仅Admin实现，Dream不拆写/读事务。

### 失败反馈与未知提交

create的closed DECK_ACCESS_DENIED保留400 `Deck not found or permission denied`；collect目标拒绝保留400 `Target deck not found or permission denied`，source拒绝保留原Voice ID not found反馈。update/delete changed:false保留404 `Voice not found or permission denied`。其他entity/reference/capability/config错误按原安全code/status返回，丢弃上游message。Admin校验thread_id归属、引用冲突不通过raw数据库异常暴露。

write timeout/断连/错误响应保留original UUID/outcome_unknown。恢复只查同operation、原UUID的status/result receipt；absent不能当rollback或触发新写，committed还原原闭集结果。无新公开恢复端点、确认、quota或重试路径。

### 影响范围与验收

[四公开路由](../../backend/routers/voices.py)、RequestAuth注册、wire/public DTO与可选序列化共享基类受影响；同模块Deck函数保持现有行为，未迁移SQL明确保留依赖。[测试](../../backend/tests/test_admin_voice_routes.py)使用实际FastAPI/RequestAuth/DTO/MockTransport、fenced Dream DB，验证nullable/省略/empty/false/zero、原rawJSON/数值、四hash/schema、safe错误/scopes、原receipt和单POST。原Editor/Session与Deck default/sharing合同同批回归。

技术PASS不代表正常本机Browser/真实账户/模型验收。真实业务仍需在普通服务与数据库中保留Run、日志及Admin可见记录供复核。
