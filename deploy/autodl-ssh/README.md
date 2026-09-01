# Ink & Memory AutoDL 启动
<!--
[Input] Existing AutoDL Admin/Dream releases and the standalone stack launcher.
[Output] Explain the application, discover AutoDL public mappings, and provide a minimal one-command startup workflow.
[Pos] User-facing README for an already deployed AutoDL Ink & Memory stack.
[Sync] 2026-08-26: document root Dream runtime and isolated Admin/PostgreSQL ownership.
[Sync] 2026-08-30: document the qualified 2.1.88 local-core and restored on-disk apply-seccomp passthrough.
[Sync] 2026-08-30: document the deployment-owned disabled Bash sandbox profile and its root-service consequence.
[Sync] 2026-08-31: document the explicit Vite allow-all host override for dynamic AutoDL mappings.
[Sync] 2026-08-31: document safe discovery of AutoDL-injected 6006/6008 public service URLs.
[Sync] 2026-08-31: require all three backend-generated crawler files to pass
                   MIME, content-marker, and non-HTML checks on every release.
[Sync] 2026-09-01: require production skill-creator discovery on every release
                   and document recovery without replacing the Claude session.
[Sync] 2026-09-01: require a full FastAPI import before release switching so
                   missing locked runtime dependencies cannot stop Dream.
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

Vite 默认只接受 Dream 公网 origin 的精确主机。AutoDL 服务地址会动态变化时，可在 `platform.env` 显式设置 `AUTODL_VITE_ALLOWED_HOSTS=*`；`prepare-env.sh` 会投影 `VITE_ALLOWED_HOSTS=*`，Vite 将其解释为 `allowedHosts: true`。该设置会关闭 Vite 的 Host 校验，只应由部署者明确启用。

Dream 的 Thread workspace、共享 Artifact、本地文件、运行用户 home 与 Claude plugin runtime 默认统一位于 `/root/autodl-tmp/ink-memory`。Admin 的 PostgreSQL 数据独立位于服务用户拥有的 `/root/ink-autodl/data/postgres`；启动器不会迁移、恢复或删除数据库。

Dream 前后端及 Claude Runtime 由 `root` 启动，使 `.dream/runtime` 的安全目录协议能够逐级打开 `/root` 下的 workspace；Admin 与内嵌 PostgreSQL 继续使用独立非 root 用户。启动脚本不会用 `setpriv` 将 Dream 降权为其他账户。

AutoDL 发布不再安装 clean-room npm Runtime 作为 Agent 主路径。通用 `ink-claude-code-dream` 构建流程从授权的 2.1.88 源码生成 Runtime `0.1.4` Linux x64 local-core，并在具备 bubblewrap 所需权限的 Docker 中完成 SDK/Bash/MCP 资格化；`deploy.sh sync` 只同步 verifier 合同与这份已资格化制品。制品内恢复了 `vendor/seccomp/x64/apply-seccomp` Docker-style passthrough，并由 receipt/checksum 绑定；它属于 Linux Runtime，不是 AutoDL 专用模式。Dream 通过绝对 `CLAUDE_CODE_CLI_PATH` 使用该 local-core。

AutoDL 的外层容器禁止 Claude Code/bubblewrap 创建所需 namespace，因此 `prepare-env.sh` 会忽略来源 env 中的同名值，并在 Dream 运行环境固定写入 `INK_AGENT_SANDBOX_ENABLED=false`。这不会关闭 Workspace Mode：Thread cwd、上下文、文件侧栏、内置文件边界、hooks 与可见工具确认继续工作；只是已批准的 Bash 不再经过 bubblewrap 文件系统/网络 sandbox，而是直接以 Dream 的 `root` 服务账号在 AutoDL 外层容器内执行。恢复的 `apply-seccomp` 仍保留在通用 Runtime 中，但 sandbox 关闭时不会进入该链路。

## 获取当前公网映射

SSH 登录目标实例后，可从 AutoDL 注入的只读服务变量获取当前 `6006` 和 `6008` 公网映射：

```bash
source /etc/profile.d/autodl.env.sh
printf 'Dream: %s\nAdmin: %s\n' \
  "${AutoDLService6006URL}" \
  "${AutoDLService6008URL}"
```

`AutoDLService6006URL` 对应 Dream 前端，`AutoDLService6008URL` 对应 Admin。不要输出整份环境变量，也不要直接展示 `/etc/profile.d/autodl.env.sh` 的完整内容；同一文件还包含 AutoDL 面板令牌等敏感变量。

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

## 每次发布的 SEO 必检项

AutoDL 使用 Vite Preview，而不是 frontend Docker 镜像内的 Nginx。因此 Vite
必须把 `/robots.txt`、`/sitemap.xml` 和 `/llms.txt` 同源代理到私有 FastAPI
`127.0.0.1:8765`；缺少这些代理时，Vite 会返回 `index.html`，HTTP 仍是 200，
但搜索引擎与 AI crawler 实际拿到的是错误的 SPA HTML。

`deploy.sh` 的 `start`、`deploy`、`verify` 和 `rollback` 统一执行以下硬门禁：

- `robots.txt` 必须是 `text/plain` 且包含 `User-agent:`；
- `sitemap.xml` 必须是 `application/xml` 且包含 `<urlset`；
- `llms.txt` 必须是 `text/plain` 且包含 `# Ink & Memory`；
- 三个响应都不得包含 `<html`，任一失败即判定发布失败。

人工复核可执行：

```bash
for path in robots.txt sitemap.xml llms.txt; do
  curl -fsS -D - "${AutoDLService6006URL%/}/${path}" -o /dev/null
done
```

禁止只检查 HTTP 200；必须同时检查 MIME 与正文标记。

## 每次发布的内置 Skill 必检项

AutoDL release 只把 `backend/` 复制进运行目录，因此生产 Skill 必须位于
`backend/builtin_skills/`，不能只存在于仓库根目录的 `.agents/skills/` 或
`.claude/skills/`。否则 Runtime 会把 `/Skill-Name ...` 解析成未知本地命令，
返回合成的 `No response requested.`；旧实现会将它误记为空 assistant，页面表现为
发起对话后立即停止。

`deploy.sh` 的 `start`、`deploy`、`verify` 和 `rollback` 会创建一个隔离临时
workspace，并硬性检查：

- release 中存在 `builtin_skills/skill-creator/SKILL.md`，frontmatter 的 canonical ID 为 `skill-creator`；
- workspace 初始化后存在 `skills/skill-creator/SKILL.md`；
- `.claude/skills/skill-creator` 是指向该 workspace Skill 的发现链接。
- 用户输入 `/Skill-Creator` 时会按 workspace 中唯一匹配项归一化为 `/skill-creator`，兼容 Runtime 的大小写敏感查找。

检查失败即发布失败。恢复既有 Thread 时不要删除 transcript，也不需要新建 Claude
session；正常 workspace 初始化会修复内置 Skill，随后在原 Thread 重发即可。若
Runtime 仍收到未知 Skill，本轮必须返回可见错误，不能保存空 assistant 消息。

build 在切换 `current` 之前还会加载生成的 Dream env 并导入完整 FastAPI `server`。
源码使用的模块必须声明在 `backend/pyproject.toml`、`uv.lock` 与导出的
`requirements.txt` 中；例如 YAML 路径统一依赖锁定的 PyYAML。导入失败时旧 release
继续服务，禁止先停服务再临时 `pip install`。

查看日志：

```bash
tail -f /root/ink-autodl/start-ink-memory.log
tail -f /root/ink-autodl/admin/logs/admin.log
tail -f /root/ink-autodl/dream/logs/dream.log
```

默认路径和端口可通过 `INK_AUTODL_*` 环境变量覆盖；正常 AutoDL 发布无需设置这些变量。
