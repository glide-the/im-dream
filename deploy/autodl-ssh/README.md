# Ink & Memory AutoDL 启动
<!--
[Input] Existing AutoDL Admin/Dream releases and the standalone stack launcher.
[Output] Explain the application and provide a minimal one-command startup workflow.
[Pos] User-facing README for an already deployed AutoDL Ink & Memory stack.
[Sync] 2026-08-27: document root Dream runtime, isolated Admin/PostgreSQL ownership,
                    and dedicated Admin-to-Dream diagnostics token projection.
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

Dream 的 Thread workspace、共享 Artifact、本地文件、运行用户 home 与 Claude plugin runtime 默认统一位于 `/root/autodl-tmp/ink-memory`。Admin 的 PostgreSQL 数据独立位于服务用户拥有的 `/root/ink-autodl/data/postgres`；启动器不会迁移、恢复或删除数据库。

Admin 生成的安全 env 必须包含至少 32 字符的 `DREAM_DIAGNOSTICS_TOKEN`。Dream `prepare-env.sh` 从该唯一事实来源读取，并只在 mode-0600 Dream runtime env 中映射为 `INK_AGENT_DIAGNOSTICS_TOKEN`；不会接受 Dream source env 的同名覆盖，也不会把 token 输出到日志。

Dream 前后端及 Claude Runtime 由 `root` 启动，使 `.dream/runtime` 的安全目录协议能够逐级打开 `/root` 下的 workspace；Admin 与内嵌 PostgreSQL 继续使用独立非 root 用户。启动脚本不会用 `setpriv` 将 Dream 降权为其他账户。

## 快速开始

本脚本只启动已经发布完成的 release，不下载代码、不构建、不执行数据库 migration、不恢复数据库，也不检测 GPU。

Dream 的 `sync`、`build` 和 `deploy` 命令会自动将脚本安装到 `/root/ink-autodl/start-ink-memory.sh`。若只同步脚本，可手动执行：

```bash
install -m 0755 \
  /root/ink-autodl/dream/source/deploy/autodl-ssh/runtime/start-ink-memory.sh \
  /root/ink-autodl/start-ink-memory.sh
install -m 0755 \
  /root/ink-autodl/dream/source/deploy/autodl-ssh/runtime/init-dream-data.sh \
  /root/ink-autodl/init-dream-data.sh
```

之后启动 Ink & Memory：

```bash
bash /root/ink-autodl/start-ink-memory.sh
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
