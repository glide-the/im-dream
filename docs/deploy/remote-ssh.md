# Remote SSH 一键部署

Remote SSH 用于把 Ink & Memory 部署到一台已有 Docker 与 `docker-compose` 的远程服务器。主入口是：

```bash
./deploy/remote-ssh/deploy.sh deploy
```

`deploy.sh` 会统一判断并执行：主机 nginx 反向代理安装/更新、远端持久化目录初始化、代码同步、Compose 构建启动和健康检查。通常不需要再单独阅读“先装 nginx、再建目录、再部署 Docker”的多段流程。

## 一键安装与部署

设置远端 SSH 和部署目录后直接执行：

```bash
export REMOTE_SSH_HOST=<server-host-or-ip>
export REMOTE_SSH_USER=<ssh-user>          # 可选；SSH config 已配置时可省略
export REMOTE_APP_DIR=/srv/ink-and-memory  # 必须是远端绝对路径

./deploy/remote-ssh/deploy.sh deploy
```

首次部署和后续更新都使用同一条命令。默认行为：

1. 检查本地 `ssh` / `rsync`、仓库必需文件、远端 Docker 与 `docker-compose`。
2. 当 `REMOTE_SETUP_NGINX=auto` 且容器端口仅绑定 localhost 时，自动安装或刷新主机 nginx 配置。
3. 自动创建/修复 `${REMOTE_APP_DIR}/backend/data`、`file-storage`、`agent-workspace`、`backups`。
4. rsync 代码到 `${REMOTE_APP_DIR}`；默认不覆盖远端 `backend/data/`。
5. 给当前远端镜像打 rollback tag。
6. 显式执行 `docker-compose build --no-cache`，每次重新打包镜像。
7. 执行 `docker-compose up -d --force-recreate`，每次用新镜像重建容器。
8. 在远端执行后端 health 与前端 HTML 验证。

Remote SSH Docker 默认使用 Claude Code 的 nested Bash sandbox 兼容路径：
后端检测到 Linux 容器运行时后，会在每个 thread 的 `.claude/settings.json`
写入 `sandbox.enableWeakerNestedSandbox=true`。不需要额外环境变量；外层
Docker 容器仍是主隔离边界。

如需只预览流程：

```bash
./deploy/remote-ssh/deploy.sh plan
./deploy/remote-ssh/deploy.sh --dry-run deploy
```

## 默认线上拓扑

默认使用“双域名 + 主机 nginx + localhost 容器端口”模式：

```text
Internet :80/:443
  └─ host nginx
      ├─ ink-backend.suoxya.com  → 127.0.0.1:8765  → backend FastAPI
      └─ ink-frontend.suoxya.com → 127.0.0.1:8080  → frontend nginx
```

关键默认值：

- 前端容器绑定 `127.0.0.1:8080`，避免占用主机 nginx 的 80 端口。
- 后端容器绑定 `127.0.0.1:8765`，避免绕过主机 nginx 暴露到公网。
- 主机 nginx 上游由 `setup-nginx` 根据 `REMOTE_BACKEND_PORT` / `REMOTE_FRONTEND_PORT` 渲染，端口覆盖时不会继续使用静态默认值。
- 后端容器内部 `PORT` 默认固定为 `REMOTE_BACKEND_CONTAINER_PORT=8765`，避免 `backend/.env` 中的 `PORT` 让 uvicorn 监听端口与 Compose 映射脱节。
- 前端 runtime `API_BASE_URL` 默认为 `https://ink-backend.suoxya.com`。
- 浏览器登录请求会访问 `https://ink-backend.suoxya.com/api/login`，不会访问 Docker 内部地址 `http://ink-backend:${REMOTE_BACKEND_CONTAINER_PORT}/api/login`。
- `BACKEND_URL=http://ink-backend:${REMOTE_BACKEND_CONTAINER_PORT}` 只保留给前端容器内部 nginx fallback 使用。

## 常用配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `REMOTE_SSH_HOST` | 空 | 必填，远端 SSH host 或 IP |
| `REMOTE_SSH_USER` | 空 | 可选；为空时使用本机 SSH 默认配置 |
| `REMOTE_SSH_PORT` | `22` | SSH 端口 |
| `REMOTE_SSH_KEY` | 空 | SSH 私钥路径 |
| `REMOTE_APP_DIR` | 空 | 必填，远端绝对部署目录 |
| `REMOTE_DOCKER_COMPOSE_BIN` | `docker-compose` | 远端 Compose 命令 |
| `REMOTE_SETUP_NGINX` | `auto` | `deploy` 自动判断是否安装/刷新主机 nginx；设为 `0` 可跳过 |
| `REMOTE_SETUP_STORAGE` | `1` | `deploy` 自动创建/修复远端持久化目录；设为 `0` 可跳过 |
| `REMOTE_SETUP_SSL` | `0` | 设为 `1` 时让 nginx setup 尝试执行 certbot |
| `REMOTE_BUILD_PULL` | `0` | 设为 `1` 时构建前拉取更新的基础镜像；重新打包本身默认每次执行，无需开关 |
| `REMOTE_FRONTEND_PORT` | `8080` | 前端容器映射到远端 localhost 的端口 |
| `REMOTE_FRONTEND_NGINX_HOST` | 空 | 可选 nginx 前端上游 host；为空时从 `REMOTE_FRONTEND_BIND_HOST` 推导 |
| `REMOTE_FRONTEND_BIND_HOST` | `127.0.0.1` | 默认仅允许主机 nginx 访问前端容器 |
| `REMOTE_BACKEND_PORT` | `8765` | 后端容器映射到远端 localhost 的端口 |
| `REMOTE_BACKEND_CONTAINER_PORT` | `8765` | 后端容器内部 uvicorn `PORT`，Compose 映射和 healthcheck 使用同一值 |
| `REMOTE_BACKEND_NGINX_HOST` | 空 | 可选 nginx 后端上游 host；为空时从 `REMOTE_BACKEND_BIND_HOST` 推导 |
| `REMOTE_BACKEND_BIND_HOST` | `127.0.0.1` | 默认仅允许主机 nginx/本机访问后端容器 |
| `REMOTE_BACKEND_PUBLIC_ORIGIN` | `https://ink-backend.suoxya.com` | 浏览器访问后端的公网 origin |
| `REMOTE_FRONTEND_PUBLIC_ORIGIN` | `https://ink-frontend.suoxya.com` | 前端公网 origin |
| `REMOTE_API_BASE_URL` | `REMOTE_BACKEND_PUBLIC_ORIGIN` | 前端 runtime API base URL |
| `REMOTE_CORS_ALLOW_ORIGINS` | 前后端公网域名 + localhost | 后端 CORS allowlist |
| `REMOTE_SYNC_DATA` | `0` | 代码部署默认不上传本地 `backend/data/` |

如果部署到其他域名，通常只需覆盖公网 origin：

```bash
export REMOTE_BACKEND_PUBLIC_ORIGIN=https://api.example.com
export REMOTE_FRONTEND_PUBLIC_ORIGIN=https://app.example.com
export REMOTE_API_BASE_URL=${REMOTE_BACKEND_PUBLIC_ORIGIN}
export REMOTE_CORS_ALLOW_ORIGINS=${REMOTE_FRONTEND_PUBLIC_ORIGIN}
./deploy/remote-ssh/deploy.sh deploy
```

如果服务器已由其他系统管理 nginx，可跳过自动 nginx 步骤：

```bash
REMOTE_SETUP_NGINX=0 ./deploy/remote-ssh/deploy.sh deploy
```

`setup-nginx` 会在安装或启动 nginx 前检查主机 `80` 端口：

- `80` 未占用：继续安装/启动 nginx。
- `80` 已由 nginx 占用：继续刷新配置，并在 `nginx.service` 未激活时尝试 `nginx -s reload`。
- `80` 已由非 nginx 进程占用：中止并打印监听进程；需要先释放端口，或确认由其他反向代理管理域名后设置 `REMOTE_SETUP_NGINX=0`。

部署配置前，`setup-nginx` 还会扫描 `/etc/nginx/sites-enabled` 和 `/etc/nginx/conf.d`。如果发现其他已启用文件也声明 `ink-backend.suoxya.com` 或 `ink-frontend.suoxya.com`，会把这些旧文件移动到 `/etc/nginx/disabled-ink-and-memory-YYYYMMDDHHMMSS/` 后再执行 `nginx -t`，避免旧代理端口继续覆盖新配置。

## 重新打包策略

`deploy` 每次都会先同步代码，然后在远端显式执行 `docker-compose build --no-cache`，再执行 `docker-compose up -d --force-recreate`。因此重复运行 `./deploy/remote-ssh/deploy.sh deploy` 也会重新打包后端和前端镜像，并用新镜像重建容器。

需要同时拉取基础镜像更新时：

```bash
REMOTE_BUILD_PULL=1 ./deploy/remote-ssh/deploy.sh deploy
```

## 数据维护

`deploy` 默认保护远端数据：`REMOTE_SYNC_DATA=0` 时不会 rsync 本地 `backend/data/` 到服务器。

只备份远端数据到本地 `backend/data/bak_remote_YYYYMMDD_HHMMSS/`：

```bash
./deploy/remote-ssh/deploy.sh backup-data
```

确认要用本地 `backend/data/` 同步/覆盖远端时：

```bash
./deploy/remote-ssh/deploy.sh sync-data
```

如需降低 SQLite 热复制风险，可在同步前后自动停启 Compose：

```bash
REMOTE_SYNC_STOP_CONTAINERS=1 ./deploy/remote-ssh/deploy.sh sync-data
```

## 运维命令

```bash
./deploy/remote-ssh/deploy.sh verify
./deploy/remote-ssh/deploy.sh ps
./deploy/remote-ssh/deploy.sh logs
./deploy/remote-ssh/deploy.sh rollback
./deploy/remote-ssh/deploy.sh stop
./deploy/remote-ssh/deploy.sh clean
```

高级情况下仍可单独执行子步骤：

```bash
./deploy/remote-ssh/deploy.sh setup-nginx
./deploy/remote-ssh/deploy.sh setup-storage
./deploy/remote-ssh/deploy.sh sync
./deploy/remote-ssh/deploy.sh config
```

## Claude-agent Docker Sandbox 排障

如果后端健康检查通过但 Claude-agent 首次调用失败，优先看后端日志：

```bash
./deploy/remote-ssh/deploy.sh logs
```

常见原因：

- 镜像缺少 `bubblewrap` / `socat`：Claude Code Linux Bash sandbox 无法启动。
  当前 `backend/Dockerfile` 已安装这两个包。
- Docker nested sandbox 无法挂载新的 `/proc`：后端会自动检测 Linux 容器运行时，
  并写入 `enableWeakerNestedSandbox=true`。
- Docker 默认 seccomp profile 拦截 nested namespace syscall：Remote SSH
  Compose 对 backend 设置 `security_opt: seccomp=unconfined`。
- `ANTHROPIC_AUTH_TOKEN` 没有进入 SDK 子进程：确认远端 `backend/.env` 或
  Settings 的用户级模型配置包含该 token。

## 前置条件与边界

本地需要 `ssh`、`rsync`，仓库内需要 `backend/.env` 与 `backend/models.json`。远端需要已安装并启动 Docker、已安装 `docker-compose`，且部署用户有权限访问 Docker daemon。

Remote SSH 不创建云资源，不读取 `.cloud-env` / `.storage-env`，不管理 GCS 或 Secret Manager。云厂商安全组仍需放行主机 nginx 的 `80` / `443`。
