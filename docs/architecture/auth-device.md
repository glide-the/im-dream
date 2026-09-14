<!-- [Input] Admin OAuth Device Token contract and Dream navigation consumers. -->
<!-- [Output] Device interaction, state/failure rules and acceptance gates. -->
<!-- [Pos] Dream Device consumer; Admin owns device/refresh authority and persistence. -->
<!-- [Sync] 2026-09-14: migrate the target authority and preserve original history. -->

# Dream Device OAuth 接入

## 背景与问题

baseline `routers/device_oauth.py`自存短码、轮询/approve/deny/consume并签用户token。迁移目标是Admin OAuth Device Token flow，不能替换成Better Auth session flow。[旧Device原文](history/pre-admin-auth-data-20260914/auth-device.md)完整保留；实现状态见[执行计划](../exec/dream-admin-auth-data-plan.md)。

## 目标与边界

Admin是唯一device authorization/token/refresh authority、状态数据库与授权页。Dream提供必要登录导航与返回；CLI是public OAuth client，不持secret。Admin唯一规范在其`docs/architecture/admin-dream-auth-data-contract.md`，实际包核验后冻结路径、DTO、scope/resource、client注册与状态字段；此稿不创造另一套endpoint或第三方状态名。

## 概念与规则

| 参与方 | 职责 |
| --- | --- |
| CLI/Device | 申请短码，显示Admin返回verification URI，按interval轮询OAuth token端点 |
| Admin授权页 | 校验短码，登录后恢复原device上下文，显示client/scopes/resource并执行approve/deny |
| Admin OAuth | 保存状态、expiry、节流、单次兑换、refresh轮转与撤销 |
| Dream | 登录导航与返回、消费目标资源API；不存code、不签token、不改变状态机 |

短码是授权上下文，不能证明用户身份；Admin session不能当CLI access token。同邮箱不自动合并。登录前后device context必须匹配且未过期，return URI受限，伪造client/scopes/resource不得改变授权内容。token/code不写公开日志或业务正文。

## 正常流程与失败状态

申请 → pending → 用户登录查看client/scopes/resource → approve或deny → CLI轮询 → 单次兑换token。状态/错误直接遵循Admin/provider冻结字段，`authorization_pending`、`slow_down`、`access_denied`、`expired_token`等保留官方原名。

pending继续等待；slow_down按返回interval退避；deny终止；expire重新申请。重复/并发兑换由Admin单事务与请求恢复保证，不能在Dream先读approved再另一个HTTP写consumed。refresh使用OAuth refresh grant，不使用网页登录session API，保护scope/resource、撤销与并发轮转。

## 页面失败、影响范围与验收

错码可重新输入，过期提示重新申请；未登录先登录再恢复上下文；权限不足不approve。Admin unavailable/timeout提示稍后重试，不能本地批准或fallback PG。页面显示client/scopes/resource，不加技术配额、内部说明或重复确认。

验收覆盖pending/approve/deny/slow_down/expire、兑换、重复并发、错误client/scope/resource、登录上下文恢复、refresh成功/轮转/撤销/未知结果。实际CLI公开OAuth协议与Dream API一起验证，session建立不能替代。全部生产device/refresh SQL迁Admin，保留现有用户PK/关系。技术fixture不能当真实用户验收。
