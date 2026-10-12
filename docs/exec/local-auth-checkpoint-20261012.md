<!-- [Input] Prior image-task login receipts, normal Chrome observations and read-only production-domain diagnostics. -->
<!-- [Output] Actual successful login source and present recovery limitation, without secrets. -->
<!-- [Pos] Local real-business authentication checkpoint; not a credential store or replacement acceptance proof. -->
<!-- [Sync] 2026-10-12: recover the previously recorded Admin autofill method before any further login retry. -->

# 本机真实验收登录记录

## 上次 Admin 成功登录

- 来源：现有本机 Chrome 中为同邮箱保存的独立管理凭据自动填充，随后在公开管理登录表单提交；不是用 Dream 密码登录，也不是只读取旧登录页面。
- 入口：正常 Admin 管理页面；成功结果为 `/admin`、Dmeck、SUPER_ADMIN及正常登录审计。
- 账户：用户指定的 `dmeck@suoxya.com`，管理身份与同邮箱的 Dream 用户身份独立。
- 已有证据：[原专项执行记录的成功登录段](image-model-call-division-20261010.md:846)，以及 [round30正常后台流水回执](/tmp/im-image-model-split-20261010/validation-round30/admin-runtime12-visible-token-ledger.json)。后者证明当时已认证的后台可见复核，不单独证明密码登录步骤。
- 凭据位置说明：Chrome 保存的管理员登录项；任务未读取其明文，记录不保存密码、哈希、Cookie、Token或OAuth参数。

## 当前恢复状态

2026-10-12重新核对：原管理会话失效。用指定的 Boss投递浏览器插件访问正常 Admin，管理页面返回登录入口。已提供的密码经生产校验器只读诊断匹配 Dream 用户，但不匹配 active 管理员；使用登录服务实际 `ink_auth` 角色复核，member存在、capability匹配且密码校验false。该诊断不能替代可见业务验收，也不授权密码同步或重置。

成功记录已经说明应恢复浏览器保存的管理凭据；本次在正常登录表单尝试该原自动填充方式，尚未填入密码。浏览器安全策略拒绝访问 Chrome 密码管理页面；没有换浏览器通道、原始命令或CDP绕过拒绝。当前不声称恢复成功、不反复提交Dream密码、不猜其他密码。

当前浏览器标签页仅作为定位提示：正常 Admin 入口，已有tab `1521635168`；以后必须重新列出标签页并匹配origin/title。Chrome插件的连接ID不能当永久身份。正常 Admin 工作目录与 `pnpm local:stable` 相同；监听3000，现有PostgreSQL目录 `.ink-memory/postgres`、端口54329、数据库 `ink-memory`，当前AUTH角色`ink_auth`。启动方式本身不重置或同步密码；运行配置与当前文件对照没有发现不同数据库目标。

只读诊断与当前差异：[管理/产品凭据分类](/tmp/im-image-model-split-20261010/validation-round31-cancel-retry/admin-login-diagnosis.json)、[登录实际角色](/tmp/im-image-model-split-20261010/validation-round31-cancel-retry/admin-auth-role-diagnosis.json)、[启动配置对照](/tmp/im-image-model-split-20261010/validation-round31-cancel-retry/admin-stable-environment-comparison.json)。这些回执均不含凭据正文或哈希，没有数据库写入。

## 本次维护与完成门禁

复用现有 [QA技能](../../.agents/skills/ink-dream-playwright-qa/SKILL.md)，增加登录检查点参考：会话失效前记录成功来源，恢复时先查现有记录；区分浏览器保存凭据、用户提供凭据与既有会话；保护敏感表单快照；未完成可见登录时不把只读查询写成验收通过。

本轮优化提示词、原技能备份和新检查回执位于 `/tmp/im-image-model-split-20261010/validation-round32-auth-records/`。这次只维护技能与实际记录，不改认证程序、账户、权限或账本。图片专项PR仍为草稿，后台可见验收缺口仍保留。原停止竞态、两链取消重试及五图/25历史结果不因本轮记录维护扩大为完整验收成功。
