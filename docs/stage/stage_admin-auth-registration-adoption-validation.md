<!-- [Input] Frozen Admin0056 controlled registration and explicit legacy adoption runners; limited ACL roles. -->
<!-- [Output] Actual isolated credential/subject/rollback validation plan and receipts. -->
<!-- [Pos] Primary-owned credential/migration fixtures; Luna deterministic public stages remain separate. -->
<!-- [Sync] 2026-09-14: start after exact DDL, actual ACL and all14 restricted Thread contracts pass. -->

# Admin 注册与历史主体关联验证

## 背景与问题

catalog及EXECUTE权限通过不能证明canonical注册的触发器、Free订阅、主体绑定或既有密码登录可以运行。0056受控函数固定search_path，必须验证真实嵌套触发器和失败回滚。历史关联runner显式manifest pin源fingerprint；不得因为同邮箱自行合并。

## 目标与边界

主任务拥有隔离fixture、私有随机凭据和注册/adoption运行验证；Admin任务拥有注册、密码适配、受控SQL、adoption代码及版本；Dream消费稳定主体。只在本轮自有ink_auth_data_codex_test_*、51534和已证明data_directory执行。正常账户、真实Google和用户密码不进入fixture或日志。冻结54–56不改；缺陷由Admin前向迁移。

## 概念与规则

公共密码注册/登录调用Admin真实handler；受限Auth只EXECUTE受控函数，无canonical/账本直接写权。注册成功必须canonical+platform+Free active+current allowance+activation event+subject/account/session一致。缺少配置、已有邮箱/link、错误provider/hash或下游失败必须回滚canonical关系。Adoption按显式ID、source SHA和google provider_sub执行；inspect/defaultdry不持久化、apply单事务、repeat无重复、新冲突整批回滚，保持所有历史PK/hash/body/subscription不变。使用随机隔离bcrypt/scrypt测试密码，私有0600配置/manifest和redacted回执。

## Optimized Prompt:

You are the primary owner of isolated credential and migration-fixture validation for Admin unified authentication. Evidence: frozen0056 migration replay/catalog pass; limited Auth/Data roles enforce actual privilege denial; full Thread contracts pass. Read Admin server/password/subjectRepository, controlled SQL and original canonical provisioning triggers, adoption runner/core/strict manifest and source fingerprint queries. Generate explicit disposable fixtures and private random credentials only, save scripts before running, prove database/port/datadir/current actor before writes. Exercise controlled register successful credential and Google-source registration without external-provider impersonation, repeat/email/provider failure and missing Free setup rollback; then real public password sign-up/sign-in handler and session/subject permission under limited Auth. Exercise explicit legacy canonical/Admin/Google adoption inspect, dry-run, apply, repeat, source-fingerprint conflict and common-password proof including mismatched source credentials; assert no legacy PK/hash/body/billing changes and no batch partial commits. Do not output passwords/hashes/tokens/private keys or touch normal PostgreSQL; retain sanitized actual command/cwd/exit/SQLSTATE/assertions. Diagnose product vs fixture/harness separately, have Admin fix forward only if needed, update docs and route provider-free repeatable stages to Luna. No claim of real Google/model or overall production DB closure.

USER REQUIREMENT:
验证统一Admin认证的新旧主体、账户关联、Session与受限数据库职责，保持历史身份和业务初始化的事务语义。

## 验收与风险

验收：真实函数和公共handler回执、正确canonical关系和Free初始化、失败零部分提交、显式adoption所有模式和源数据不变、真实密码适配+Session权限；SQLSTATE和fixture身份记录。风险：baseline隔离库Free version仍draft/无model，成功场景必须先准备合法隔离model/entitlement而不能降低生产检查；trigger函数自身search_path必须按实际定义证明。状态：规划完成，立即执行。

## 实际结果

主任务执行 `node --import tsx /private/tmp/ink-auth-migration-validation/registration-adoption-validation.mts`，cwd为Admin729f worktree，退出0，共37断言。canonical/platform/Free active/current allowance/event/link与公开credential account/Session一致；错误密码401、缺初始化/重复/不支持provider23514、显式manifest conflict整批回滚；canonical bcrypt和Admin scrypt同私有随机密码证明、既有Google provider_sub、inspect/defaultdry/apply/repeat和所有源PK/hash/time保持均通过。首次fixture缺Provider base_url属于harness数据准备错误，真实SQLSTATE保留，补充已配置隔离拓扑URL后成功；生产SQL、constraint和54–56冻结migration未改。Google来源fn不是实际Google登录，未调用外部Provider或模型，正常数据库未修改。回执：[37断言](../exec/admin-auth-data-verification/registration-adoption-proof.json)。

## Optimized Prompt: Session/Editor 与 purpose 公共合同

You are the primary owner of isolated fixture/credential/fault preparation. Evidence: complete frozen58 replay, exact18/7columns and3purpose+6denial+cascade checks pass; Admin owns actual public8Session/Editor operation harness and narrowgrant receipt/renew/revoke. Upgrade only the named owned ACL clone through58 using its proven owner DSN/port/datadir, refresh explicitlimited ACL and create fresh5minute ES256 publicverification fixtures includingeditor/Gatewayscopes and independentotheractor; neverplaceownerURLinproductionenv. Configure explicitprivateAEAD/ttl/service-to-Gatewaybindings and onlycanonical_subject isolatedGateway-keymetadata, no realProvider/models. PreservestandardDTO/routes, originalrequestID and samebearer/entity/purpose/maxbindings. Primary owns credentials and directownSession/grant corruption/expiry mutation; Luna owns deterministic and non-destructive public-only contractvalidation with exactscope. Verifyall8operations/owner/Session/NULL/microseconds/concurrentreceipt/audit/encryption; runfullprimaryfaultmatrixfor expiredoriginalreceiptwithoutauthorityresurrection/corruption503/revoke/exactdeletecascade. Keepallactualcommand/cwd/exit/rawsanitizedreceiptsanddonotclaimnormalGoogle/modelbusiness.

USER REQUIREMENT:
验证Editor/Session持久化接口与server-persistence/gateway-cli/editor-stdio隔离、恢复与撤销，所有DB访问由Admin执行，保留原业务状态。
