<!-- [Input] frontend auth context/forms and backend auth, OAuth, and Device Flow routers. -->
<!-- [Output] Current account and authentication business contract. -->
<!-- [Pos] Canonical account-auth module design. -->

# 账号与认证

## 业务目标

用户使用同一个 Ink & Memory 账号进入 Writing、Chat、Dream、Deck 和设置。服务端从 Session 或
Bearer Token 解析身份，业务请求不能由浏览器覆盖用户 ID、角色或服务主体。

## 当前需求与结果

- 支持邮箱密码注册、登录、读取当前用户和退出。
- 支持 Google OAuth 登录；是否允许 OAuth 自动注册由服务端配置决定。
- 支持 OAuth 2.0 Device Authorization Grant，供无浏览器或受限客户端请求设备码、完成验证并换取 Token。
- 首次注册由 Admin Product 服务投影默认产品、Free 订阅和平台默认能力；依赖不可用时 fail closed。
- 旧本地数据导入和首次登录完成标记仍通过认证后的生产 API 执行。
- Session Cookie 与 Bearer Token 可以进入同一身份解析边界；写请求同时执行 Origin/CSRF 约束。

## 页面与接口

| 场景 | 入口 |
|---|---|
| 注册/登录 | 登录页，`POST /api/register`、`POST /api/login` |
| 当前用户/退出 | `GET /api/me`、`POST /auth/logout` |
| Google OAuth | `/oauth/google/login` → `/oauth/google/callback` |
| Device Flow | `/oauth/device/code`、`/oauth/device/verify`、`/oauth/token` |

## 代码所有权

- 前端：`frontend/src/components/Auth/`、`frontend/src/contexts/AuthContext.tsx`
- 后端：`backend/routers/auth.py`、`backend/routers/oauth.py`、`backend/routers/device_oauth.py`
- 服务间产品身份：`backend/services/admin_product/identity.py`
