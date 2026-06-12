# deploy

## 定位

`deploy/` 是 Ink & Memory 的平台化发布脚本入口。新入口按运行平台分目录组织，旧的 Google Cloud Run 脚本仍保留在根目录以兼容既有调用方式。

## 推荐入口

| 平台 | 入口 | 说明 |
|------|------|------|
| 本地发布 | [`local/deploy.sh`](local/deploy.sh) | 检查、构建、启动、验证、停止本地 backend/frontend 进程 |
| Docker 发布 | [`docker/deploy.sh`](docker/deploy.sh) | 包装根目录 [`../docker-compose.yml`](../docker-compose.yml) 的构建、启动、验证、清理 |
| Google Cloud 发布 | [`google-cloud/deploy.sh`](google-cloud/deploy.sh) | 包装旧 Cloud Run 脚本，提供目录化入口和 dry-run/check |

## 兼容入口

以下旧路径继续可用，供已有文档、脚本或个人习惯调用：

| 旧脚本 | 新入口中的对应命令 |
|--------|-------------------|
| [`setup-storage.sh`](setup-storage.sh) | `./deploy/google-cloud/deploy.sh setup-storage` |
| [`setup-env.sh`](setup-env.sh) | `./deploy/google-cloud/deploy.sh setup-env` |
| [`deploy.sh`](deploy.sh) | `./deploy/google-cloud/deploy.sh deploy` |
| [`sync-data.sh`](sync-data.sh) | `./deploy/google-cloud/deploy.sh sync-data` |

## 通用约定

每个平台入口都支持：

```bash
./deploy/<platform>/deploy.sh --help
./deploy/<platform>/deploy.sh --dry-run <command>
./deploy/<platform>/deploy.sh --check
```

脚本不写死项目 ID、bucket、主机、服务名或密钥。需要覆盖默认值时使用环境变量、Compose 配置或平台脚本参数。
