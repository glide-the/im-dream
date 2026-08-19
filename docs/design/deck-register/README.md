<!-- [Input] Deferred market-distribution sections of the Deck requirement PDF. -->
<!-- [Output] Explicit non-current Deck market boundary. -->
<!-- [Pos] Single deferred-scope record for Deck distribution. -->

# Deck 市场分发：延期

以下需求没有进入当前实现：Deck 市场注册、发布到社区、他人引用、安装、分发审核、治理、下架和
跨账号升级。当前 Deck 页面和 Settings / Work 不得出现 Community、发布市场、安装市场 Deck 或
相应占位状态。

未来启动该模块前，需要先明确平台身份、内容许可、版本兼容、审核、撤回、计费和跨账号数据边界，
并由 Admin 发布所需 Schema 与权限 capability。当前 Deck 的系统内建能力不等同于市场分发：平台
`is_system` Deck 与产品为账号初始化的默认副本都在 System Decks 分组只读展示，不存在用户从市场
安装或启停的流程。

当前后端仍保留 `/api/decks?published=true`、`/fork`、`/publish` 和 `/sync` 等遗留兼容 transport，
`voiceApi.ts` 也保留部分未被当前 Deck 页面调用的 helper。它们没有进入当前导航和 Work 交互，不能
作为市场功能已实现的依据，也不得被新页面重新接入；后续应在独立兼容性变更中删除或正式迁移。
