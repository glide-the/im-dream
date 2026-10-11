<!-- [Input] Runtime PR31/32, same-source qualification/publication and identified normal Dream adoption. -->
<!-- [Output] Exact release identity, source pin and strict compact completion consumption scope. -->
<!-- [Pos] Current Runtime0.1.12 adoption receipt; image-feature working-tree acceptance is recorded separately. -->
<!-- [Sync] 2026-10-11: exact public release and normal adoption verified; scoped consumer tests passed. -->

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

真实图片专项在原本机账户、Thread、服务与业务数据库进行；新生成/上传编辑已成功并按 Responses 报告Token结算，其余可见操作继续验收。完整上游图片费用没有报告时保持未知，历史三条缺少缓存分项，不估算写账。普通Dream凭证不能登录独立Admin管理身份，管理页面可见验收存在具体限制。

本文件交付受保护工作区之外的精确Runtime pin和必要消费修订，不把当前工作区其他未提交图片、认证和资源改动打包发布。最终真实业务回执保存在本任务现行专项执行记录，独立于制品资格。
