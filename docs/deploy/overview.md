# 部署指南：Google Cloud Run

本文档描述 Ink & Memory 的 Cloud Run 部署架构与操作步骤。

---

## 整体架构

```
用户浏览器
    │
    ▼
┌─────────────────────────────────────┐
│  Cloud Run: ink-frontend            │
│  nginx 1.27-alpine                  │
│  · 服务 /ink-and-memory/ 静态资源   │
│  · 反向代理 /api/ /polycli/ → 后端  │
└─────────────────────┬───────────────┘
                      │ HTTPS (BACKEND_URL)
                      ▼
┌─────────────────────────────────────┐
│  Cloud Run: ink-backend             │
│  python:3.9-slim + uvicorn:8765     │
│  · REST / SSE / WebSocket API       │
│  · Secret Manager refs (API keys)   │
└─────────────────────┬───────────────┘
                      │ GCS FUSE 挂载
                      ▼
┌─────────────────────────────────────┐
│  Cloud Storage: ink-memory-data-*   │
│  /app/data/                         │
│  ├── ink-and-memory.db   (SQLite)   │
│  ├── file-storage/                  │
│  └── agent-workspace/               │
└─────────────────────────────────────┘
```

---

## 脚本说明

所有部署脚本位于项目根目录下的 `deploy/` 文件夹。

| 脚本 | 执行时机 | 作用 |
|------|---------|------|
| `deploy/setup-storage.sh` | **首次部署前**（一次性） | 创建 GCS bucket、服务账号、IAM 授权 |
| `deploy/setup-env.sh` | **首次部署前及 secrets 变更时** | 配置 Secret Manager secrets 和 Cloud Run 环境变量 |
| `deploy/deploy.sh` | **每次发版** | 并行构建镜像、推送到 Artifact Registry、顺序部署两个服务 |

---

## 前置条件

- [Google Cloud SDK (gcloud CLI)](https://cloud.google.com/sdk/docs/install) 已安装
- Docker 已安装并运行
- 已创建 Google Cloud 项目并开启计费
- 已执行 `gcloud auth login`

---

## 首次部署步骤

### 1. 初始化存储

```bash
export GCP_PROJECT_ID=your-project-id
./deploy/setup-storage.sh
```

执行内容：
- 启用 `storage.googleapis.com`、`run.googleapis.com`、`iam.googleapis.com` API
- 在指定区域（默认 `asia-east1`）创建 GCS bucket `ink-memory-data-<PROJECT_ID>`
- 开启 bucket 版本控制（防止数据意外覆盖）
- 预建 `file-storage/`、`agent-workspace/` 目录占位符
- 创建专用服务账号 `ink-backend-sa`，授予 `Storage Object Admin`
- 将 bucket 名和 SA 邮箱写入根目录 `.storage-env`（已加入 `.gitignore`）

### 2. 配置环境变量

```bash
./deploy/setup-env.sh
```

脚本会交互式询问配置项，从 `backend/.env` 读取已有值作为默认（直接回车确认）：

**敏感值 → Secret Manager**

| 变量 | Secret 名称 | 说明 |
|------|------------|------|
| `TEXT_API_KEY` | `ink-text-api-key` | LLM API 密钥 |
| `INK_IMAGE_API_KEY` | `ink-image-api-key` | 图片生成 API 密钥 |
| `JWT_SECRET_KEY` | `ink-jwt-secret-key` | JWT 签名密钥（≥32 位） |

**配置值 → Cloud Run 环境变量**

| 变量 | 默认值 | 说明 |
|------|-------|------|
| `TEXT_API_ENDPOINT` | — | LLM API 地址 |
| `INK_TEXT_MODEL_DEFAULT` | — | 默认 LLM 模型名 |
| `INK_IMAGE_API_ENDPOINT` | — | 图片生成 API 地址 |
| `INK_PUBLIC_BASE_URL` | — | 公开访问基础路径 |
| `INK_AGENT_MAX_TURNS` | `100` | Agent 最大对话轮数 |
| `INK_AGENT_TTL_S` | `600` | Agent 会话 TTL（秒） |
| `INK_AGENT_CONTEXT_SESSIONS` | — | Agent 上下文会话数 |
| `FILE_STORAGE_LOCAL_DIR` | `/app/data/file-storage` | 文件存储路径（GCS 挂载子目录） |
| `AGENT_CWD` | `/app/data/agent-workspace` | Agent 工作区路径（GCS 挂载子目录） |

输出写入根目录 `.cloud-env`（已加入 `.gitignore`）。

### 3. 部署

```bash
./deploy/deploy.sh
```

执行流程：

```
Step 1  设置 GCP 项目
Step 2  启用 Cloud Run / Artifact Registry / Cloud Build API
Step 3  确认 Artifact Registry 仓库存在（idempotent）
Step 4  配置 Docker 认证
Step 5  并行构建后端镜像 + 前端镜像
Step 6  并行推送两个镜像
Step 7  部署后端服务 → 获取 BACKEND_URL
        部署前端服务（注入 BACKEND_URL）
```

部署完成后输出：
```
Frontend : https://ink-frontend-xxxx-uc.a.run.app/ink-and-memory/
Backend  : https://ink-backend-xxxx-uc.a.run.app
```

---

## 后续发版

只需重新执行第 3 步：

```bash
./deploy/deploy.sh
```

- secrets 更新时重跑第 2 步：`./deploy/setup-env.sh`
- 存储结构无需重建（bucket 和 SA 已存在，脚本幂等）

---

## 环境变量覆盖

所有可选覆盖项均通过 `export` 设置：

```bash
export GCP_PROJECT_ID=my-project
export GCP_REGION=us-central1        # 默认 asia-east1
export REPO_NAME=my-registry-repo    # 默认 ink-and-memory
export BACKEND_SERVICE=my-backend    # 默认 ink-backend
export FRONTEND_SERVICE=my-frontend  # 默认 ink-frontend
export BUCKET_NAME=my-bucket         # 默认 ink-memory-data-<PROJECT_ID>
export SA_NAME=my-sa                 # 默认 ink-backend-sa
```

---

## 数据持久化

后端使用 **Cloud Storage FUSE** 将 GCS bucket 挂载到容器的 `/app/data/`，三类数据的路径映射：

| 数据 | 容器路径 | GCS bucket 路径 |
|------|---------|----------------|
| SQLite 数据库 | `/app/data/ink-and-memory.db` | `ink-memory-data-<project>/` |
| 文件存储 | `/app/data/file-storage/` | `ink-memory-data-<project>/file-storage/` |
| Agent 工作区 | `/app/data/agent-workspace/` | `ink-memory-data-<project>/agent-workspace/` |

> **注意：** SQLite 使用 WAL 模式（`.db-wal`、`.db-shm` 辅助文件）。后端服务限制为 `max-instances=1`，避免多实例并发写入同一 GCS 路径导致数据损坏。

---

## 容器镜像构建

### 后端（`backend/Dockerfile`）

基于 `python:3.9-slim`，安装系统依赖（gcc、libffi、openssl、libjpeg、zlib），安装带 hash 校验的 Python 依赖，暴露端口 8765。

### 前端（`frontend/Dockerfile`）

两阶段构建：
1. **构建阶段**：`node:22-alpine`，执行 `npm ci && npm run build`，输出到 `dist/`
2. **服务阶段**：`nginx:1.27-alpine`，拷贝 `dist/` 到 `/usr/share/nginx/html/ink-and-memory/`，使用 `nginx.conf.template` 在启动时通过 `envsubst` 注入 `BACKEND_URL`

nginx 配置要点：
- 使用 `resolver 8.8.8.8` + 变量赋值方式代理，确保运行时动态解析 Cloud Run 域名
- SSE/WebSocket 路径关闭 `proxy_buffering`，超时设为 3600s
- 静态资源设置 1 年强缓存（`immutable`）

---

## 本地 Docker Compose 运行

```bash
# 复制并填写后端配置
cp backend/models.json.example backend/models.json

docker compose up --build
# 访问 http://localhost/ink-and-memory/
```

`docker-compose.yml` 中前端的 `BACKEND_URL=http://ink-backend:8765`，与 Cloud Run 部署共用同一套 nginx 模板机制。
