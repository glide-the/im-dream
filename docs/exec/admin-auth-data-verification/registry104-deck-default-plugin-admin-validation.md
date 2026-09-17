<!-- [Input] Immutable Admin Registry104 commit plus root test and source-oracle receipts. -->
<!-- [Output] Default-plugin resolve DTO/Service/typed Repository hashes and restricted-role evidence. -->
<!-- [Pos] Admin provider receipt; Dream create/reconcile consumer and normal Deck acceptance remain separate. -->
<!-- [Sync] 2026-09-15: freeze exact Registry104 Git and read-contract identity. -->

# Registry104 默认 Deck 插件解析 Admin 验证

## Git 与契约

- commit: `27b6fc9e3a7a42ea7329efb6e5832295d04ae346`
- tree: `50f82619703560cf676cf1c4cb1a6ca61b0a02be`
- parent Registry103: `547e89896776627b43ecaab0a5ac848891f21a94`
- subject: `feat: resolve configured default Deck plugin`
- `deck.default-plugin.resolve` hash: `9ae17f5c334a14f04363705b55701cbcc7ccd8a12070f9548adbf67746535b83`
- requirements: identity `1dc05e229d3f4147923fcdfe117c4c4930a43bf9f31439d7b4bc83d2a0d04cd3`、unified `8b71cf5687f61dee884c3e6f2fb109c7a951b0789066a0f13583a7b67757fa71`、deck canonical 与 deck-content-versions exact existing capability。
- Registry103 prefix canonical SHA: `b47e731abee6fd0a9b937333f9535817a5d7ffffe0a012440123fde6d6f6c824`
- raw Registry104 SHA: `87abe71fdba8dc7fc53599da025a3fcbcd12cdc4047f05da4f65696d0e1c5db9`
- raw implementation map SHA: `878baded1130041b5a806cf5d95319eaea774d4d7e74b9e8d45e651c29e56ed9`
- commit 29 files；`git diff-tree ... | rg ^drizzle/` 无输出，提交后 Admin worktree clean。

操作输入是 strict empty DTO；Service只接受OAuth `dream:read`并拒绝entity grant；Repository从Admin `DREAM_DECK_POLICY_JSON`的package/version使用typed Drizzle选择ready行，按`created_at DESC, id DESC`稳定返回。输出只含本地artifact/CLI verifier所需六字段，无用户、外部package selector、SQL、表列、路径或secret。

## Root 独立验证

cwd：`/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`。

```text
pnpm exec vitest run app/lib/dream/deckDefaultPluginResolve.test.ts app/lib/dream/deckDefaultPluginResolveHandler.test.ts app/lib/dream/deckDefaultPluginResolveRegistration.test.ts app/lib/dream/deckDefaultPluginResolveSource.test.ts
```

无source env时28 passed / 1 skipped；随后显式设置当前Dream source与项目venv oracle，source 1/1 passed。旧实现的 newest-first、ready exact选择、本地两个verifier、四字段evidence与close/unavailable行为均有源码对照。

```text
pnpm exec tsx tests/integration/adminDeckDefaultPluginResolve.contract.mts
```

exit0。自建回环PostgreSQL的随机DATA role只有installation/capability SELECT；exact ready、absent/unready/mismatch null、同timestamp按ID稳定排序、raw compatibility/digest、closed selectors、scope/entity/capability fail closed、row counts不变、无receipt/write与owned cluster removed均PASS。

```text
pnpm exec tsc --noEmit --incremental false
pnpm exec eslint <Registry104九个目标文件>
```

两项exit0、无输出。Admin任务文档另记录Python syntax、registry/JSON/Markdown/diff gates通过。最终全仓回归仍在跨域收口阶段统一执行。

## 范围限制

技术验证未读取Dream artifact store、未启动Claude CLI、未连接正常Admin/PostgreSQL，也没有使用指定账户创建或修复Deck。Dream必须绑定以上exact hash，完成本地verifier、existing write receipt recovery和两条公开路由后才能关闭该入口。
