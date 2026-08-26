# Ink & Memory AutoDL 启动
<!--
[Input] Existing AutoDL Admin/Dream releases and the standalone stack launcher.
[Output] Explain the application and provide a minimal one-command startup workflow.
[Pos] User-facing README for an already deployed AutoDL Ink & Memory stack.
[Sync] 2026-08-26: document the standalone no-GPU startup script.
-->

## 应用介绍

Ink & Memory 是一款面向长篇故事、剧本和创意写作的 AI 创作工作台。应用将项目资料、角色设定、故事结构、写作工作区和 AI Agent 集成在统一界面中，帮助创作者从灵感整理逐步推进到内容创作、分析与修改。

主要功能包括：

- 创建和管理故事、剧本等创作项目；
- 整理角色、世界观、情节和创作资料；
- 使用 AI Agent 进行构思、续写、分析和润色；
- 通过 Deck 组合不同的创作角色与工作流程；
- 接入 MCP Server，扩展外部工具和资源；
- 支持多轮对话、任务取消和会话恢复；
- 自动保存创作内容和历史记录。

AutoDL 版本不依赖 Docker 或 Nginx：Admin 与内嵌 PostgreSQL 监听 `127.0.0.1:6008`，Dream 前端监听 `127.0.0.1:6006`，Dream 后端监听 `127.0.0.1:8765`。公网服务映射只需要暴露前端 `6006` 和 Admin `6008`。

## 快速开始

本脚本只启动已经发布完成的 release，不下载代码、不构建、不执行数据库 migration、不恢复数据库，也不检测 GPU。

首次准备脚本：

```bash
install -m 0755 \
  /root/ink-autodl/dream/source/deploy/autodl-ssh/runtime/start-ink-memory.sh \
  /root/LaunchTool311/start_ink_memory.sh
```

之后启动 Ink & Memory：

```bash
bash /root/LaunchTool311/start_ink_memory.sh
```

脚本按以下顺序工作：

1. 检查必要命令、release、runtime env 和运行用户；
2. 若 Admin `6008` 已健康则保留现有进程，否则启动 Admin 和内嵌 PostgreSQL；
3. 等待 Admin 健康后，检查 Dream 的 `6006/8765`；
4. Dream 已健康时保留现有进程，否则启动 Vite Preview 和 FastAPI；
5. 验证默认 Deck 的 Claude plugin artifact；
6. 输出启动结果，服务通过 `screen` 在 SSH 断开后继续运行。

脚本遇到已被未知或不健康进程占用的端口时会停止并报错，不会自动杀死或覆盖该进程。

查看运行状态：

```bash
screen -ls
curl -fsS http://127.0.0.1:6008/admin/login >/dev/null && echo "Admin OK"
curl -fsS http://127.0.0.1:6006/api/health && echo
```

查看日志：

```bash
tail -f /root/ink-autodl/start-ink-memory.log
tail -f /root/ink-autodl/admin/logs/admin.log
tail -f /root/ink-autodl/dream/logs/dream.log
```

默认路径和端口可通过 `INK_AUTODL_*` 环境变量覆盖；正常 AutoDL 发布无需设置这些变量。
