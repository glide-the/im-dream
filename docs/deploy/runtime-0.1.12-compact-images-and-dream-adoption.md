<!-- [Sync] 2026-10-11: public exact 0.1.12 and normal Dream adoption verified; fresh normal-account two-chain image and reopened-file verification observed. -->
<!-- [Input] Runtime PR31/32 source-bound compact repairs and same-source CI/npm qualification. -->
<!-- [Output] Exact Runtime 0.1.12 publication, installation, normal adoption and real image acceptance record. -->
<!-- [Pos] Current release/adoption record; immutable 0.1.11 history is retained separately. -->
<!-- [Sync] 2026-10-11: exact public release and normal adoption passed; fresh normal-account flows and reopened-file verification observed; final document/release closure recorded separately. -->

# Runtime 0.1.12 图片历史压缩与 Dream 采用

## 背景与问题

此前图片生成/编辑交付成功，但累计图片历史使后续请求超限；原headless构建没有注册原`/compact`，不能把原源码存在该命令当作已发布Runtime可用。新版本恢复原non-interactive命令，在原compact中仅把历史内置图片协议副本转换为保留真实调用ID的文字，保持当前素材绑定、原boundary/恢复/取消与历史文件。原完成文字通过原SDK mapper展示。

## 目标与边界、概念与规则

Runtime `0.1.12`、SDK `0.2.145`、CLI compatibility `2.1.241`。原1902文件库存SHA `40269454cd690c74d129a31699935d6db713f2958aabe4787e01617e1c92a906`保持。不增加schema、部署分支、Gateway控制通道、图片重放或预算上调。

[0.1.11历史](runtime-0.1.11-image-native-and-dream-adoption.md)不覆盖；[专项正式稿](../design/claude-agent/image-model-call-division.md)拥有正常、异常及状态图，[专项执行记录](../exec/image-model-call-division-20261010.md)记录本轮实际命令与失败修订。

## 当前交付状态

| 阶段 | 当前证据与限制 |
|---|---|
| 独立实际稿/源码复审 | compact三轮修订及npm收据门修订无剩余P1/P2 |
| 隔离实际CLI资格 | R8 exit0：大图真实cached413/fallback200、生产素材校验、实际boundary/完成输出、Bash/恢复/取消；属于技术验证 |
| 源码交付 | PR31和PR32已合入，当前main `826de9672a4b5540513c2cdfa097e52ff221ebed` |
| 同源四平台资格 | 38149158758全部success；旧失败流程不计通过 |
| 五包公开与精确安装 | 38149958179 success；public五integrity与qualification一致；clean host安装和native探针exit0 |
| 正常Dream采用 | 实际0.1.12/SDK0.2.145；backend59234（Runtime采用24109，compact消费修订受控采用后为59234）；manifest与启动identity通过；其他监听器保持 |
| 新Runtime真实业务重验 | 本轮五项生成/编辑及额外手动恢复均成功；原13+新6=19重开恢复，6新图重新下载SHA一致；控制与精确边界见末节 |

Admin计量修订与本次pending恢复资格/正常应用采用单独记入专项执行记录；CLI平台资格或HTTP前检不代替正常账户、图片和账本验收。历史三条可恢复reported总163709，但缓存分项/金额未知，预留保持、不估算补账。

本轮正常compact已新增同CLI session manual boundary，原7条native图片和13张UI图片保留；但Chat partial模式下未显示Compacted完成文字，此项不计可见反馈通过。该缺口现已通过严格synthetic完成文字消费修订，Luna协议回归和正常空闲后端受控采用完成；第二次同会话真实反馈已唯一可见，新的manual boundary和原9条native图保持核对exit0。额外压缩状态交互仍由既有任务负责。

## round30 当前真实验收（2026-10-12）

本节取代此前阶段记录中的“进行中”当前状态；原失败、harness修订和历史原文仍保留。Runtime0.1.12/SDK0.2.145已公开精确安装并正常采用。主执行者在用户指定现有账户、既有Thread、本机正常Dream/Admin/Gateway/PostgreSQL上实际可见操作完成五项生成/编辑及不支持模型后的手动恢复，没有替代Provider、账号、账本或存储。原AI gpt-6.1-sol已恢复并刷新确认，Image codex-gpt-image-2保持；本轮未重新保存已经选中的唯一Image候选，不将check同值说成一次新写入。

| 本轮真实操作 | Gateway request | capture Token | 结果 |
|---|---|---:|---|
| 主对话生成 | `req_b7bd0c9692a94dc7ba326bd47512294d` | 13911 | HTTP200/succeeded/settled；查看/下载/重开字节相同 |
| 上传素材主对话编辑 | `req_9994e9b84b32494d8589863a64433351` | 17581 | HTTP200/succeeded/settled；查看/下载/重开字节相同 |
| 实际草图主对话编辑 | `req_72e5392a4a6148a9a657329095b38853` | 14191 | HTTP200/succeeded/settled；查看/下载/重开字节相同 |
| 明确image_gen生成 | `req_626271420cdc405793936f72741d3b7f` | 567 | HTTP200/succeeded/settled；查看/下载/重开字节相同 |
| 明确image_gen编辑 | `req_b1617773ac2c4f6db8b25240760b3086` | 2102 | HTTP200/succeeded/settled；查看/下载/重开字节相同 |
| 手动更换AI后的重试 | `req_5045b53386d14af39c24f1844f66d233` | 29605 | HTTP200/succeeded/settled；查看/下载/重开字节相同 |

主流程五项共48,352 Token，额外恢复29,605；每个实际图片turn仅一条execution，原选择、CLI调用ID、Gateway和native真实response/imageCall身份核对一致。独立Images使用所选图片模型；普通需求没有改走Images。素材仅添加时idle，没有图片执行；上传的原生成图保留，后续引用正确识别紫圆和橙三角，草图由实际鼠标绘制后添加并发送。普通文字OK、仅解释工具名、一次Bash真实结果、运行后的停止与重试都已观察，没有新增图片。

最终刷新重开19张图片（原13+新6），6张新图逐个通过可见查看器下载，SHA-256与首次下载完全相同；唯一Compacted完成文字在历史中保留。持续6091个250ms样本未发现原图节点卸载/Blob变化/已完成图退回加载，覆盖两次实际compact、新图片SSE和后续文字；初始13图中有1个尚未加载，不能扩写为全部图片任意时刻已经decode。

正常Admin原Dmeck SUPER_ADMIN Chrome会话中已逐项看到六次图片请求的reserve/capture/release；native详情显示Responses报告Token与完整图片费用未知，Images详情显示真实text/image分项、模型与200终态，payload始终关闭。普通Dream密码在冷Admin浏览器被拒绝的记录保留，当前可见验收已由原真实会话解除，没有改变认证、权限或创建账户。

尚未真实制造的自然上游坏结果、文件访问故障、连接中断和图片Provider执行中取消仍只由隔离技术合同验证。发送后尚未实际running时第一次Stop仅断开连接、Agent随后仍执行；确认running后的同一turn停止成功。该竞态未扩大为本专项Runner/SSE/取消重构，不能称所有取消时点均通过。新标准usage结算不表示完整上游图片USD已知；旧三条缺缓存分项、reported合计163709和预留861420保持，未估算补结。

证据：[正常业务关联回执](/tmp/im-image-model-split-20261010/validation-round30/runtime12-final-business-correlations.json)、[最终重开哈希](/tmp/im-image-model-split-20261010/validation-round30/real-runtime12-final-reopen-hashes.json)、[实际Admin流水](/tmp/im-image-model-split-20261010/validation-round30/admin-runtime12-visible-token-ledger.json)、[正常服务精确采用](/tmp/im-image-model-split-20261010/validation-round30/compact-consumer-normal-backend-adoption.json)。文档/图示检查及最后Git交付状态由执行记录单列，不用业务成功替代必需交付。
