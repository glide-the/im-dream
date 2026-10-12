<!-- [Input] 2026-10-10 图片工具实施合同、PRD、正式交互设计及 Admin delegationContracts.ts。 -->
<!-- [Output] 独立可实施性评审、具体合同门槛、只读 hash 回执与验证边界。 -->
<!-- [Pos] 图片工具实施前独立设计评审回执；不替代代码或真实业务验收。 -->
<!-- [Sync] 2026-10-10: 现行稿可开始实施；四项链路合同门槛已明确，Admin hash 已只读核对。 -->

# 图片工具实施前独立评审：2026-10-10

## 结论

现行 PRD、正式设计和 2026-10-10 实施合同**可开始实施**。产品目的、入口、生成/编辑、查看下载、重开继续、失败/停止边界一致；主对话 Responses 适配与独立 Images 工具被明确分开；没有新增画布、媒体中心、后台控制通道、图像数据库表或第二套 SSE 生命周期。

完整链路在代码交付后才可判定通过。以下四项是实现和技术验收必须关闭的合同门槛；它们不是要求改变产品方案。

## 具体门槛

1. **Delegation 合同必须固定并回归。** 实施说明 §2026-10-10（第 163 行）要求重新计算 Admin 通用 delegation hash，同时保留 Story/scheduled 冻结合同。当前 Admin `app/lib/auth/delegationContracts.ts` 的只读结果如下；Dream 侧应按名称和 hash 更新通用合同测试，不能手写猜测值，也不能把 `images:create` 扩散到普通文本 turn。

   | capability | `contract_sha256` |
   |---|---|
   | `runtime-delegation.create` | `e2aa6eac5c34d090c013755270bc9363e2e79b9a05902dfef73ab54494fb5091` |
   | `runtime-delegation.renew` | `bfcd929e88f4a44b7353446cfb80c410e9a363ede0c94f7f6db4aad7269e4284` |
   | `runtime-delegation.revoke` | `0c4c315146fb80dff05db14eed0ac7b301db1d85827f6a651cc1e1d7b25152f9` |
   | `runtime-delegation.receipt` | `ee6832f6ca1f6e23562c04507ada9fe2c58d8bc7928591d6a4bc116fa559e02e` |

   当前 `gateway-cli` purpose 的 scope 集合已包含 `images:create`；这支持图片调用沿用当前 actor/thread/run delegation。若代码改变 DTO 或新增 capability，必须重新取 hash 并单独记录，不得修改冻结 Story/scheduled 合同。

2. **Host 到 Admin Images 的调用边界必须落到实际公开合同。** 实施说明第 161、163、169 行只描述“当前 grant”“选图模型”和主模型图片转换。Admin 现有源码入口为 `POST /v1/images/generations`（JSON）与 `POST /v1/images/edits`（multipart），两者都要求 `images:create`，并经过现有 model capability、计费 reservation、idempotency 和安全错误路径。Host 必须通过当前 gateway-cli delegation 取得服务器侧授权并调用这些入口，不能使用 Provider key、用户环境变量、前端凭证或新增 Dream HTTP 服务。

   最小验收应覆盖：无 `images:create` 不注册图片工具；普通文本仍可运行；generation/edit 分别命中 `image_generation`/`image_edit` catalog；多图模型无明确 alias 时 fail closed；上游 request id、toolCallId 和文件 URI 保持分离。

3. **参考图 URI 映射必须是可验证的单一规则。** 实施说明第 165、169 行要求只接受当前 Thread 的 `workspace://files/`，同时要求上传附件补齐同 Thread 工作区引用；PRD 第 105 行也把参考图映射列为实施前置。实现需要明确 `UploadedFile`/历史图片如何得到规范 workspace URI、如何校验 Thread 所有权和 Workspace Mode、映射缺失或跨 Thread 时返回哪一类安全错误。不能把 storage key、外部 URL、绝对路径或模型自报图片 ID 直接当成参考图。

4. **完整图片补齐需要明确登记对象和生命周期。** 实施说明第 87、91、161、167 行要求“本轮 Host 发布集合 + 已登记内部 Tool 调用”同时成立，且停止后丢弃迟到回包。实现前应在 `ClaudeAgentService`/Runner 现有 turn 作用域中固定登记键（Thread、Run、真实 toolCallId），规定成功、拒绝、取消、partial 保存和 turn 结束时的清理边界；Service 只补齐本轮匹配的内部图片结果，同 URI 不重复，不能依靠通用 auto-register fallback。缺少这一登记对象会使图片归属和迟到结果无法安全判断。

## 一致性核对

- PRD 的用户目标和桌面/窄屏骨架与正式稿的正常、异常、状态图一致；正式稿明确图片功能当前待实现，2026-10-10 实施范围再声明进入代码交付。
- 2026-10-10 段将 Admin Images 源码能力与本机运行/真实账户能力分开，未把现有端点写成真实业务验收；生成与编辑仍是一条内部工具流程下的两个 Admin 操作。
- 主模型图片转换被列为本轮最小 Admin 修订（实施说明第 169 行）。完成后必须验证文字与图片顺序、非图片类型 fail closed、tool result 的 call ID 关联；不能保留旧的“图片块待补”状态并宣称 V12 完成。
- Workspace Mode、授权拒绝、停止、断线、文件发布失败和消息保存失败均沿用原生命周期；没有引入新表或新控制通道。`Pillow`、O_NOFOLLOW、临时文件和原子不覆盖是执行保护，不应出现在用户页面或被写成产品配额。
- 现行稿前半部分仍保留实施前“建议/未实现”语句，这是历史状态；代码交付后应按正式稿第 254–256 行和实施记录同步状态，保留历史文件，不覆盖旧图。

## 只读命令回执

命令（cwd `/Users/dmeck/project/ink-admin-memory`）：

```text
pnpm exec tsx -e 'import { delegationContracts } from "./app/lib/auth/delegationContracts.ts"; console.log(JSON.stringify(delegationContracts.map(({capability}) => ({name: capability.name, contract_sha256: capability.contract_sha256})), null, 2));'
```

退出码：`0`。输出仅包含上述 4 个 capability 名称和 SHA-256，没有读取数据库、启动服务、读取凭证或执行 Provider 请求。原始 stdout/exit 保留在本轮临时回执 `/tmp/image-tool-delegation-hashes-20261010.out` 与 `.exit`；hash 已复制到本文件供主执行者更新 Dream 合同。

## 范围与未验证项

本评审只读核对现行 PRD、正式设计、实施说明、Admin delegation DTO/registry 和现有 Images route 入口。未修改应用源码、测试、PRD、正式设计或 Admin 文件；未运行数据库、服务、Provider、真实账户或模型。实现后的 host、stdio、Runner、catalog、完整图片补齐、主模型图片转换和真实业务验收仍需主执行者按本合同另行验证。
