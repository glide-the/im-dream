<!-- [Input] Existing public Deck Claude Plugin refs and actual Admin runtime-data DTO/Service/Repository contracts. -->
<!-- [Output] Current refs ownership, source evidence, configuration transitions, failures and acceptance. -->
<!-- [Pos] Claude Code Plugin installation refs design; logical Deck Plugin binding/Workflow remains separate. -->
<!-- [Sync] 2026-09-15: migrate public list/prepare/replace; Dream retains actual artifact and CLI checks. -->

# Deck Claude Plugin 引用现行设计

## 背景与问题

Deck引用共享Claude Code Plugin安装，保存installation ID、package/version/digest、enabled和order。原公开GET/PUT通过Dream SQL取得安装记录并替换refs。Admin现在拥有该数据与事务，Dream仍访问共享制品文件并检查Claude CLI兼容性；将前一次读取直接作为当前数据库状态会产生来源字段变化竞态。

## 目标与边界

保持`GET/PUT /api/decks/{deck_id}/claude-plugins`和`{deck_id,refs}`公开响应。当前OAuth用户管理ownedDeck，全部Thread/CLI/Editor entity grant不能管理refs。Admin list/prepare/replace唯一执行权限、schema、锁和数据库写；Dream在prepare之后、replace之前执行现有artifact/CLI检查，不执行SQL或复制摘要/版本比较算法。

本稿只覆盖公开refs管理。共享install/catalog/operation、server adapter查询、runtime packing、Thread runtime-read与Voice memory/analysis仍需各自实际消费接线；逻辑Deck Plugin binding/Workflow不由此接口变更。不增加产品配额、确认或环境行为。

## 概念与规则

| 配置状态 | 执行行为 |
| --- | --- |
| default | 没有refs时GET返回空数组；本接口不自动安装或注入默认Plugin |
| desired | PUT只接受refs中的installation ID、optional enabled/order；ID按Python strip去空白且唯一，enabled默认true，缺order按输入位置 |
| effective | Admin confirmed replace后的数据库refs，以原公开响应返回；unknown不能声明已应用 |
| revision | Admin在refs语义变化时推进Deck draft_revision；refs合同只返回changed供内部判断，不新增公开revision字段；reorder/no-op不推进 |

公开输入不接受actor ID、package、digest、compatibility或文件path。order为PostgreSQL integer技术范围`-2_147_483_648..2_147_483_647`，不是排序产品限制；已移除无产品规则依据的旧32数量常量，实际Admin合同没有该数量配额。所有typed输入校验复用scoped route class，错误返回固定422且不回显正文/input，非finite数字不能使错误响应编码失败。

[AdminDeckRefsData](../../../backend/services/admin_data/deck_refs_data.py)按以下模块边界执行：

1. list以当前OAuth、exact identity/unified capability读取ownedDeck refs。闭集DTO校验required nullable manifest与ISO offset/微秒，reply Deck必须匹配请求；公开enabled保持原整数0/1。
2. PUT先用独立read UUID执行prepare，Admin返回精确选中、唯一且ready的安装metadata。DTO没有artifact path，raw compatibility/manifest/inventory只保持原字符串。
3. Dream复用[PluginInstallService](../../../backend/services/claude_plugin/install_service.py)原两个检查方法：artifact_store.get_artifact按server metadata中的package/marketplace/digest定位并计算目录摘要；CLI SemVer检查使用原compatibility_json。两方法不依赖DB，因此以staticmethod同时供原install/ref消费者使用，算法不改。失败不发replace。
4. Dream从prepare metadata生成source evidence（package/version/digest/rawcompat）和用户选定enabled/order，使用公开operation的原UUID发送replace。Admin锁ownedDeck/installations，重新检查ready和全部source字段后，在同一事务替换refs、推进语义draft、保存receipt/audit。metadata期间变化返回409，Dream不覆盖新记录或自动再prepare/write。
5. confirmed reply校验Deck与installation IDs，再移除内部changed、按原公开投影返回。写timeout/响应不合法保留原request_id/outcome_unknown；absent不能证明rollback，不自动重发。

## 正常流程、失败与影响

空refs→selected refs、已有refs→替换、已有refs→空数组均由同一production入口执行。只改变输入顺序且语义相同，Admin返回原记录与时间；enabled/order变化属于语义修改。Dream不推断changed、draft或事务结果。

身份/scope失败拒绝；缺广告/hash/physical capability在领域I/O前503。准备缺记录/权限/状态保持404或409，损坏准备DTO安全503且不访问制品。摘要不符或CLI不兼容返回原409/安全error；未知write保留原UUID。用户不看源码、技术凭据或额外确认。

影响为两个公开refs端点、typed DTO与共同validation wrapper。原Preferences固定422 detail通过同批回归保持；其它Plugin管理端点仅复用安全validation错误编码，原领域处理与DB迁移依赖不在此阶段伪造完成。

## 验收

[公开技术测试](../../../backend/tests/test_admin_deck_refs_routes.py)走实际FastAPI/Auth/client/DTO与MockTransport，Dream DB fenced；覆盖closed fields、strip唯一IDs、defaults/空数组/disabled/负order、三operation hash与两schema、ISO/原enabled、准备及reply错配、unknown UUID/no retry、OAuth与grant拒绝。明确命名临时制品使用实际import/get/digest，并注入CLI版本执行原SemVer；摘要篡改或不兼容在replace前失败。

该技术fixture不表示正常共享制品、真实CLI执行、正常账户/模型验收。旧逻辑Deck Plugin集成设计与历史内容保留；完整迁移范围见[入口清单](../../exec/dream-admin-data-inventory.md)。
