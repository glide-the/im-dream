<!-- [Input] Dream frontend surfaces and story_workspace Dream services. -->
<!-- [Output] Current Dream launch, runtime, artifact, and re-entry behavior. -->
<!-- [Pos] Canonical Dream business design. -->

# Dream

## 业务目标

Dream 将一句创作目标交给 DreamAgent，在独立创作工作台中持续对话、构建人物/场景/分镜/Episode
产物，并允许用户刷新或离开后回到同一 Run。

## 当前需求与结果

- 只有 DreamAgent 类型的 Deck 从预览示例进入 Dream；ChatAgent 始终进入普通 Chat。
- 启动时服务端校验用户、Deck、Agent 类型、版本和运行资格，创建 Run 并绑定 actor-owned Thread。
- Dream 与 Chat 共享消息、Claude Session、SSE、工具确认、Stop 和重连协议。
- 首轮提供项目目标和工作区上下文；之后每轮继续读取同一实际工作区，不创建第二套 Session。
- 根 Agent turn 成功后，`DreamArtifactTurnHook` 校验并原子同步人物、场景、分镜、Project/Episode 与 manifest。
- failed、cancelled 或 Stop 不发布本轮半成品；同步失败不伪造第二个 Chat 终态。
- Dream 首页列出可重入 Run；进入后恢复同一 Thread、当前产物和最近活动时间。
- Execution 默认展示人物、场景和分镜初稿；“同步”视图展示 Episode Artifact、Story Index、审阅和辅助产物。
- Agent 可自由调用已安装 Skill；产品不维护固定命令顺序、next-action 状态机或 Workflow 编排工作台。

## 生产接口

- 启动与列表：`POST /api/story-workspace/dream-runs/start`、`GET /api/story-workspace/dream-runs`
- Run：`/api/story-workspace/workflow-runs/{run_id}`、`/dream-files`、`/episode-artifacts`、`/story-index`
- 运行控制：`/retry`、`/cancel`、`/guidance`
- Thread：复用 `/api/claude-agent/threads/**`

## 代码所有权

- 前端：`frontend/src/pages/story-workspace/StoryWorkspaceDreamPage.tsx`、`frontend/src/components/story-workspace/dream/`
- 启动/重入：`backend/services/story_workspace/dream_launch_*`、`backend/services/story_workspace/dream_reentry_service.py`
- 产物：`backend/services/story_workspace/dream_artifact_turn_hook.py`、`backend/services/story_workspace/dream_file_service.py`、`backend/services/story_workspace/episode_artifact_service.py`
- Thread 绑定：`backend/services/story_workspace/dream_thread_binding.py`
