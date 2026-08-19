<!-- [Input] Admin Product/Gateway clients, product BFF routes, model catalog, and subscription page. -->
<!-- [Output] Current subscription, allowance, model, and inference business contract. -->
<!-- [Pos] Canonical subscription-models module design. -->

# 订阅、额度与模型

## 所有权

Admin 是产品、套餐、订阅、Allowance、模型目录、Provider 凭据、定价和 Token 账本的唯一业务
所有者。Dream 只通过服务间身份调用 Admin Product API 与 Gateway，并向浏览器提供 actor-scoped BFF。

## 当前需求与结果

- 注册用户由 Admin 投影默认产品和 Free 订阅；Dream 不在本地伪造套餐或额度。
- 订阅页读取当前套餐、周期、Token 额度、已用量和可选 Plan，支持加载、空、错误与刷新状态。
- 模型设置只展示 Admin 返回且当前用户可调用的模型；浏览器保存 alias，不保存 Provider ID 或密钥。
- 每次推理由 Gateway 执行身份、entitlement、定价、reserve/capture/release 和请求日志。
- Product/Gateway 不可用、身份缺失或模型无资格时 fail closed。
- BFF 已提供订阅 command 与 payment-intent 适配入口；当前页面尚未提供完整支付、回调和订单闭环，不能把套餐卡片描述为已可购买。

## 浏览器入口

| 能力 | API |
|---|---|
| 当前订阅 | `/api/story-workspace/subscription/context` |
| 套餐目录 | `/api/story-workspace/subscription/plans` |
| 用量 | `/api/story-workspace/usage` |
| 模型目录 | `/api/story-workspace/models`、`/api/gateway/models` |
| 订阅命令 | `/api/story-workspace/subscription/commands` |
| Payment Intent 适配 | `/api/story-workspace/subscription/payment-intents` |

## 代码所有权

- 前端：`frontend/src/pages/story-workspace/StoryWorkspaceSubscriptionPage.tsx`、`frontend/src/components/dashboard/ModelConfigSection.tsx`、`frontend/src/api/productApi.ts`
- Product BFF：`backend/routers/product.py`、`backend/services/admin_product/`
- Gateway：`backend/routers/gateway_models.py`、`backend/services/admin_gateway/`
- Schema、账本与 Provider 凭据：Admin 仓库 Drizzle 和 Admin 服务
