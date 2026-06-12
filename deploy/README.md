# deploy

## 定位

`deploy/` 是 Ink & Memory 的平台化发布脚本入口。新入口按运行平台分目录组织，旧的 Google Cloud Run 根路径保留为兼容包装，实际云发布实现放在 `deploy/google-cloud/`。

## 推荐入口

| 平台 | 入口 | 说明 |
|------|------|------|
| 本地发布 | [`local/deploy.sh`](local/deploy.sh) | 检查、构建、启动、验证、停止本地 backend/frontend 进程 |
| Docker 发布 | [`docker/deploy.sh`](docker/deploy.sh) | 包装根目录 [`../docker-compose.yml`](../docker-compose.yml) 的构建、启动、验证、清理 |
| Remote SSH 发布 | [`remote-ssh/deploy.sh`](remote-ssh/deploy.sh) | 通过 SSH/rsync 同步到已安装 Docker 的远程服务器，并在远端执行 [`remote-ssh/docker-compose.yml`](remote-ssh/docker-compose.yml)；默认资源对齐 Cloud Run，数据使用远端文件系统 |
| Host 级 nginx 安装 | [`remote-ssh/setup-nginx.sh`](remote-ssh/setup-nginx.sh) | 在远端服务器安装 nginx，部署域名反向代理配置（`ink-backend.suoxya.com` / `ink-frontend.suoxya.com`）；可选 Let's Encrypt SSL |
| Google Cloud 发布 | [`google-cloud/deploy.sh`](google-cloud/deploy.sh) | 完整 Cloud Run 发布入口，默认使用 `ink-backend.suoxya.com` / `ink-frontend.suoxya.com`，提供构建、推送、部署、CORS 回写、dry-run/check/verify/rollback |

## 兼容入口

以下旧路径继续可用，供已有文档、脚本或个人习惯调用：

| 旧脚本 | 新入口中的对应命令 | 实际实现 |
|--------|-------------------|----------|
| [`setup-storage.sh`](setup-storage.sh) | `./deploy/google-cloud/deploy.sh setup-storage` | [`google-cloud/setup-storage.sh`](google-cloud/setup-storage.sh) |
| [`setup-env.sh`](setup-env.sh) | `./deploy/google-cloud/deploy.sh setup-env` | [`setup-env.sh`](setup-env.sh)，暂保留在根目录供云入口编排 |
| [`deploy.sh`](deploy.sh) | `./deploy/google-cloud/deploy.sh deploy` | [`google-cloud/deploy.sh`](google-cloud/deploy.sh) |
| [`sync-data.sh`](sync-data.sh) | `./deploy/google-cloud/deploy.sh sync-data` | [`google-cloud/sync-data.sh`](google-cloud/sync-data.sh) |

云端 SQLite 故障或停机维护前，先执行只下载备份：

```bash
./deploy/google-cloud/deploy.sh backup-data
```

该命令会把 `gs://${GCS_BUCKET}/ink-and-memory.db*` 下载到 `backend/data/bak_YYYYMMDD_HHMMSS/`，不会上传本地数据，也不会重启 Cloud Run。

## 通用约定

每个平台入口都支持：

```bash
./deploy/<platform>/deploy.sh --help
./deploy/<platform>/deploy.sh --dry-run <command>
./deploy/<platform>/deploy.sh --check
```

脚本不写死项目 ID、bucket、主机、服务名或密钥。需要覆盖默认值时使用环境变量、Compose 配置或平台脚本参数。
