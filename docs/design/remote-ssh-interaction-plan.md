# Remote SSH 双域名与数据脚本交互方案设计稿

## 目标

本方案用于修复 Remote SSH 部署中的两个问题：

1. 远端访问应采用两个主机 nginx 转发路由：
   - `ink-backend.suoxya.com` → 后端容器 `127.0.0.1:8765`
   - `ink-frontend.suoxya.com` → 前端容器 `127.0.0.1:8080`
2. 前端浏览器端登录接口不能再默认访问 Docker 内部地址 `http://ink-backend:8765/api/login`，而应访问 `https://ink-backend.suoxya.com/api/login`。
3. Remote SSH 发布路径需要补齐 `setup-storage.sh` 与 `sync-data.sh`，分别负责远端持久化目录初始化与远端数据备份/同步。

## 处理判断

- `http://ink-backend:8765` 只能在 Docker 网络或前端容器内部 nginx 中解析，浏览器无法解析该主机名，因此不能作为浏览器 runtime API base URL。
- Remote SSH 面向公网域名发布时，应默认走“浏览器 → 后端公网域名 → 主机 nginx → 后端容器”的链路。
- `BACKEND_URL=http://ink-backend:8765` 可以继续保留，作为前端容器内部 nginx 的 fallback 代理上游。
- `API_BASE_URL` 必须默认写入公网后端 origin：`https://ink-backend.suoxya.com`。
- 前端容器不应默认占用主机 `80`，否则会与主机 nginx 冲突；默认应绑定 `127.0.0.1:8080`。
- 后端容器继续默认绑定 `127.0.0.1:8765`，只允许主机 nginx 或本机运维命令访问。

## 交互流程

### 首次部署

1. 运维设置 SSH 与远端目录：
   ```bash
   export REMOTE_SSH_HOST=<server-host-or-ip>
   export REMOTE_SSH_USER=<ssh-user>
   export REMOTE_APP_DIR=/srv/ink-and-memory
   ```
2. 安装或刷新主机 nginx 配置：
   ```bash
   ./deploy/remote-ssh/setup-nginx.sh
   ```
3. 初始化远端持久化目录：
   ```bash
   ./deploy/remote-ssh/deploy.sh setup-storage
   ```
4. 检查并发布：
   ```bash
   ./deploy/remote-ssh/deploy.sh --check
   ./deploy/remote-ssh/deploy.sh deploy
   ```
5. 验证浏览器登录请求指向：
   ```text
   https://ink-backend.suoxya.com/api/login
   ```

### 数据维护

- 仅备份远端数据：
  ```bash
  ./deploy/remote-ssh/deploy.sh backup-data
  ```
- 用本地 `backend/data/` 覆盖/同步远端前，先自动备份远端：
  ```bash
  ./deploy/remote-ssh/deploy.sh sync-data
  ```
- 为降低 SQLite 热复制风险，可在同步前后自动停启 Compose：
  ```bash
  REMOTE_SYNC_STOP_CONTAINERS=1 ./deploy/remote-ssh/deploy.sh sync-data
  ```

## 验收标准

- Remote SSH Compose 默认前端端口为 `127.0.0.1:8080`。
- Remote SSH Compose 默认 `API_BASE_URL=https://ink-backend.suoxya.com`。
- 后端 CORS 默认允许 `https://ink-frontend.suoxya.com`。
- `deploy/remote-ssh/deploy.sh plan` 明确描述双域名 nginx 路由和公网后端 API URL。
- `deploy/remote-ssh/setup-storage.sh` 可创建远端数据、文件存储、Agent workspace 与备份目录。
- `deploy/remote-ssh/sync-data.sh` 可执行远端备份、下载和先备份后上传。
