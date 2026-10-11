<!-- [Input] Runtime PR31/32, same-source qualification/publication and identified normal Dream adoption. -->
<!-- [Output] Exact release identity, source pin and strict compact completion consumption scope. -->
<!-- [Pos] Current Runtime0.1.12 adoption receipt; image-feature working-tree acceptance is recorded separately. -->
<!-- [Sync] 2026-10-12: exact public release, normal adoption, strict completion feedback and reopened real-image files verified. -->

# Runtime 0.1.12 与 compact 完成反馈接入

## 背景与问题

Runtime 的原 `/compact` 完成消息通过 SDK 的完整 synthetic AssistantMessage 输出。Dream 已启用 partial messages，原完整文字去重规则会跳过这条没有 StreamEvent 的本地完成文字；用户只能观察运行结束，无法看到实际完成提示。

## 目标与边界、概念与规则

精确采用 Runtime `0.1.12`、SDK `0.2.145`、CLI compatibility `2.1.241`。只在既有 Runner 文字消费路径识别 model 严格等于 `<synthetic>`，trim 后等于 `Compacted` 或以 `Compacted ` 开头的原完成文字。原文和附注沿原累积、callback、SSE、消息保存与历史路径处理；普通模型 snapshot、其他 synthetic、工具、取消、恢复和资源策略保持原语义。

不新增事件、配置、数据库、自动模型切换或控制入口。失败与取消没有原完成消息，保留原错误反馈；不会把空 success 当作已完成压缩，也不会重放图片。

## 实际发布和采用

- [Runtime PR31](https://github.com/glide-the/ink-claude-code-dream/pull/31) 与 [收据门 PR32](https://github.com/glide-the/ink-claude-code-dream/pull/32) 已合入；同源 SHA `826de9672a4b5540513c2cdfa097e52ff221ebed`。
- [四平台资格 38149158758](https://github.com/glide-the/ink-claude-code-dream/actions/runs/38149158758) 和 [五包发布 38149958179](https://github.com/glide-the/ink-claude-code-dream/actions/runs/38149958179) 成功。平台先发布，selector 后发布；五项 public integrity 与资格归档一致。
- clean host exact npm 安装、实际 Bun sharp/libvips 探针、CLI aliases/manifest/zero maps、正常 resolver 和启动身份通过。没有远程部署或 Docker 镜像构建结论。
- 正常后端 Runtime 采用99460→24109，消费修订采用24109→59234；同原环境与8765端口。Admin75238、前端381、PostgreSQL75173保持，没有DDL、替代账号或存储。
- 本机同会话第二次 compact：新 boundary `0d9cfe85-8ba7-4e55-ab1e-858527afa4ca`，原9条native图片 SHA保持，页面显示唯一 `Compacted`。第一次完成提示缺失记录保留。

## 验证与限制

本轮实际技术命令与退出码：resolver14、Docker源码合同3、startup3，Runner162 passed/1既有skip/175subtests，公开image-chat2、image-tool44、image-turn10及diff check均exit0。Provider-free回归不算真实模型验收。首轮错误callback测试失败已修订为原 `on_text_done`，失败收据保留。

真实图片专项在原本机账户、Thread、服务与业务数据库进行。本轮新 native 生成、上传编辑、草图编辑和 Images 生成、编辑五项均成功并结算，capture 分别为13911、17581、14191、567、2102 Token；原 Dmeck SUPER_ADMIN Chrome 会话已逐项可见核对正常 Token 流水，native 和 Images 请求详情也已观察。冷浏览器用普通 Dream 凭证登录独立 Admin 被拒绝的记录保留，现有管理会话已解除可见验收限制，没有新建账户或改动认证。后续引用、文字、工具名讨论、普通 Bash 与实际运行后的取消及重试均已观察。不支持模型的反馈后手动选择具备能力的 AI 重试得到新蓝圆，capture29605；每个图片turn仅一条execution，没有双链重复或自动回退。

最终设置恢复AI gpt-6.1-sol且刷新确认，Image codex-gpt-image-2保持。原13加本轮6共19图刷新重开，6新图逐项实际查看/下载，SHA256与首次下载相同，唯一Compacted持久化。6091个250ms样本未发现原图节点/Blob变化；初始1图未加载不扩写为19图始终已解码。恢复图首次计数harness在历史加载前读0、预期1而实际4，失败保留；未重发模型，修正观察时点和分页等待后核对成功。

完整上游图片费用没有报告时保持未知，历史三条缺少缓存分项，不估算写账。发送后尚未进入运行状态时的首次停止只中断了连接，随后 Agent 仍运行；确认实际运行后的同一 turn 停止成功。前一种竞态记录为既有取消边界，未扩大本次消费修订范围。正常图片Provider执行中取消、自然坏图/访问失败/断线没有主动制造，相关故障合同只由隔离技术验证覆盖。自有Chrome关闭/诊断保存后Node driver残留，精确自有PID清理的实际unified退出1单列，不宣称浏览器runner全绿退出；最终文件关联检查退出0。

本文件交付受保护工作区之外的精确Runtime pin和必要消费修订，不把当前工作区其他未提交图片、认证和资源改动打包发布。最终真实业务回执保存在本任务现行专项执行记录，独立于制品资格。
