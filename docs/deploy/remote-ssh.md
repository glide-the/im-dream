# Remote SSH Docker Compose 部署

本文档描述把 Ink & Memory 部署到一台已安装 Docker 与 `docker-compose` 的远程服务器。该路径通过 SSH/rsync 同步仓库文件，在远端执行专用 Compose 文件，不依赖 Google Cloud、Artifact Registry 或 Secret Manager。

## 适用场景

- 远程服务器已有 Docker 服务和 `docker-compose`。
- 希望用单机 Compose 托管前端 nginx 与后端 FastAPI。
- 不需要 Cloud Run、GCS FUSE、Secret Manager。
- 希望保留远端 `backend/data/`，避免每次发布覆盖数据库。
- 希望资源规格与 Google Cloud Run 发布保持一致。

## 前置条件

本地机器：

- 可通过 SSH 登录远程服务器。
- 已安装 `ssh` 和 `rsync`。
- 仓库内存在 `backend/.env` 与 `backend/models.json`。

远程服务器：

- 已安装并启动 Docker。
- 已安装 `docker-compose` 命令。
- 部署用户有权限运行 `docker-compose` 和访问 Docker daemon。
- 防火墙放行前端端口，默认 `80`。

## 主机 Nginx 反向代理

当使用域名对外提供服务时（如 `ink-backend.suoxya.com` 和 `ink-frontend.suoxya.com`），需要在远程服务器上额外部署一层主机级 nginx 作为反向代理：

```
互联网 → :80/:443 (主机 nginx) → 按域名路由:
  ink-backend.suoxya.com  → 127.0.0.1:8765  (Docker 后端容器)
  ink-frontend.suoxya.com → 127.0.0.1:8080  (Docker 前端容器)
```

由于主机 nginx 会占用 80 端口，Docker 前端容器需要改用其他端口（默认改为 8080），且建议将两个容器端口都绑定到 `127.0.0.1` 而非 `0.0.0.0`，避免绕过主机 nginx 直接暴露容器。

### 一键安装

将 `deploy/remote-ssh/nginx/` 目录下的文件复制到远程服务器后执行：

```bash
# 在远程服务器上
sudo ./deploy/remote-ssh/nginx/setup-nginx.sh
```

脚本会自动完成：
1. 检测操作系统并安装 nginx
2. 配置站点文件到 `/etc/nginx/sites-available/ink-and-memory`
3. 移除默认站点
4. 配置防火墙放行 80/443 端口
5. 测试配置并 reload nginx
6. 设置 nginx 开机自启

### 手动配置

```bash
# 复制 nginx 配置
sudo cp deploy/remote-ssh/nginx/ink-and-memory.conf /etc/nginx/sites-available/

# 启用站点
sudo ln -s /etc/nginx/sites-available/ink-and-memory.conf /etc/nginx/sites-enabled/ink-and-memory
sudo rm -f /etc/nginx/sites-enabled/default

# 测试并重载
sudo nginx -t && sudo systemctl reload nginx
sudo systemctl enable nginx
```

### HTTPS (Let's Encrypt)

DNS 解析生效后，使用 certbot 自动获取 SSL 证书：

```bash
# 安装 certbot (Ubuntu/Debian)
sudo apt-get install -y certbot python3-certbot-nginx

# 获取证书（certbot 会自动修改 nginx 配置）
sudo certbot --nginx -d ink-backend.suoxya.com -d ink-frontend.suoxya.com

# 验证自动续期
sudo systemctl status certbot.timer
```

certbot 会自动添加 systemd timer 实现证书自动续期。

## 配置项

必须显式设置远程主机和部署目录，避免把服务器、用户名或路径写死到脚本中：

```bash
export REMOTE_SSH_HOST=<server-host-or-ip>
export REMOTE_SSH_USER=<ssh-user>          # 可选；若 SSH config 已配置可省略
export REMOTE_APP_DIR=/srv/ink-and-memory  # 必须是远端绝对路径
```

常用可选项：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `REMOTE_SSH_PORT` | `22` | SSH 端口 |
| `REMOTE_SSH_KEY` | 空 | SSH 私钥路径 |
| `REMOTE_DOCKER_COMPOSE_BIN` | `docker-compose` | 远端 Compose 命令 |
| `REMOTE_FRONTEND_PORT` | `80` | 远端前端端口；使用主机 nginx 时改为 `8080` |
| `REMOTE_FRONTEND_BIND_HOST` | `0.0.0.0` | 使用主机 nginx 时改为 `127.0.0.1` |
| `REMOTE_BACKEND_PORT` | `8765` | 远端后端端口 |
| `REMOTE_BACKEND_BIND_HOST` | `127.0.0.1` | 默认只让远端本机访问后端端口 |
| `REMOTE_BACKEND_CPUS` | `1.0` | 对齐 Cloud Run backend `--cpu=1` |
| `REMOTE_BACKEND_MEMORY` | `1g` | 对齐 Cloud Run backend `--memory=1Gi` |
| `REMOTE_FRONTEND_CPUS` | `1.0` | 对齐 Cloud Run frontend `--cpu=1` |
| `REMOTE_FRONTEND_MEMORY` | `256m` | 对齐 Cloud Run frontend `--memory=256Mi` |
| `REMOTE_AGENT_CWD` | `/app/data/agent-workspace` | 容器内 Agent 工作区，挂载自远端文件系统 |
| `REMOTE_FILE_STORAGE_LOCAL_DIR` | `/app/data/file-storage` | 容器内文件存储目录，挂载自远端文件系统 |
| `REMOTE_API_BASE_URL` | 空 | 空值表示前端走 nginx 同源代理 fallback |
| `REMOTE_CORS_ALLOW_ORIGINS` | 本地 origin 列表 | 使用域名时需包含 `https://ink-frontend.suoxya.com` |
| `REMOTE_SYNC_DATA` | `0` | 默认不 rsync `backend/data/`，保护远端数据库 |

## 资源规格

Remote SSH 默认使用与 Google Cloud Run 发布相同的主要资源约束：

| 服务 | Remote SSH 默认值 | Cloud Run 对应值 |
|------|-------------------|------------------|
| backend | `REMOTE_BACKEND_CPUS=1.0`、`REMOTE_BACKEND_MEMORY=1g` | `--cpu=1`、`--memory=1Gi` |
| frontend | `REMOTE_FRONTEND_CPUS=1.0`、`REMOTE_FRONTEND_MEMORY=256m` | `--cpu=1`、`--memory=256Mi` |

Cloud Run 的 `min-instances`、`max-instances`、`cpu-boost` 不直接映射到单机 `docker-compose`；Remote SSH 通过单机容器和 `restart: unless-stopped` 保持服务运行。

## 默认请求模式

默认不设置 `REMOTE_API_BASE_URL`。前端运行时配置为空，浏览器请求会回退到 `/ink-and-memory` 同源路径，再由远端 nginx 代理到 `http://ink-backend:8765`。

如果需要浏览器直接跨域请求后端，需要同时暴露后端端口并配置 CORS：

```bash
export REMOTE_BACKEND_BIND_HOST=0.0.0.0
export REMOTE_API_BASE_URL=http://<server-host-or-domain>:8765
export REMOTE_CORS_ALLOW_ORIGINS=http://<server-host-or-domain>
```

## 部署流程

使用主机 nginx 反向代理时，推荐的环境变量配置：

```bash
export REMOTE_SSH_HOST=39.97.252.88
export REMOTE_SSH_USER=root
export REMOTE_APP_DIR=/srv/ink-and-memory

# 使用主机 nginx 时，前端端口改到 8080 并仅绑定 localhost
export REMOTE_FRONTEND_PORT=8080
export REMOTE_FRONTEND_BIND_HOST=127.0.0.1
export REMOTE_BACKEND_BIND_HOST=127.0.0.1

# CORS 允许前端域名
export REMOTE_CORS_ALLOW_ORIGINS=https://ink-frontend.suoxya.com,https://ink-backend.suoxya.com
```

然后执行：

```bash
./deploy/remote-ssh/deploy.sh plan
./deploy/remote-ssh/deploy.sh --check
./deploy/remote-ssh/deploy.sh deploy
```

脚本会执行：

1. 检查本地 `ssh` / `rsync` 和必需配置文件。
2. 检查远端 `docker-compose` 与 Docker daemon。
3. 使用 `rsync --delete` 同步仓库到 `REMOTE_APP_DIR`。
4. 默认排除 `backend/data/`，保留远端数据库。
5. 给当前远端镜像打 rollback tag。
6. 在远端运行 `docker-compose -f deploy/remote-ssh/docker-compose.yml up --build -d`。
7. 在远端用 `curl` 验证后端 health 和前端 HTML。

## 验证、日志与状态

```bash
./deploy/remote-ssh/deploy.sh verify
./deploy/remote-ssh/deploy.sh ps
./deploy/remote-ssh/deploy.sh logs
```

默认验证地址在远端本机执行：

- `http://127.0.0.1:8765/api/health`
- `http://127.0.0.1:80/ink-and-memory/`

可用 `REMOTE_VERIFY_BACKEND_URL` / `REMOTE_VERIFY_FRONTEND_URL` 覆盖。

## 数据与回滚

Remote SSH 的后端 `/app/data` 来自远端服务器的 `${REMOTE_APP_DIR}/backend/data`。脚本会在远端创建：

```text
${REMOTE_APP_DIR}/backend/data/
├── ink-and-memory.db
├── file-storage/
└── agent-workspace/
```

Compose 会覆盖 `backend/.env` 里可能存在的本机路径，将容器内路径固定为：

```text
AGENT_CWD=/app/data/agent-workspace
FILE_STORAGE_LOCAL_DIR=/app/data/file-storage
FILE_STORAGE_TYPE=local
```

默认 `REMOTE_SYNC_DATA=0`，不会同步本地 `backend/data/` 到服务器，避免覆盖远端 SQLite 数据。只有明确要用本地数据覆盖远端时才设置：

```bash
export REMOTE_SYNC_DATA=1
./deploy/remote-ssh/deploy.sh deploy
```

部署前脚本会把当前远端镜像打成 rollback image。回滚只切回上一版镜像，不回滚数据库文件：

```bash
./deploy/remote-ssh/deploy.sh rollback
```

停止或清理：

```bash
./deploy/remote-ssh/deploy.sh stop
./deploy/remote-ssh/deploy.sh clean
```

`clean` 默认不删镜像或卷。需要更彻底清理时：

```bash
REMOTE_CLEAN_IMAGES=1 REMOTE_CLEAN_VOLUMES=1 ./deploy/remote-ssh/deploy.sh clean
```

## 边界

- Remote SSH 复用 Dockerfile 和前端 runtime-config 机制，但不使用根目录本地 `docker-compose.yml`，因为本地 Compose 默认把浏览器 API 指向 `127.0.0.1:8765`。
- Remote SSH 不创建云资源，不读取 `.cloud-env` / `.storage-env`，不管理 GCS 或 Secret Manager。
- 远端部署目录、端口、域名、SSH 用户都必须通过环境变量配置。
