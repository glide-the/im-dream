<!-- [Input] 已验证的Admin手动Actions、原ECS服务与Dream现有Admin访问配置。 -->
<!-- [Output] 当前双仓库发布职责、手动入口、验证／恢复与退役Compose原文。 -->
<!-- [Pos] Dream侧阿里云发布分流；Admin操作权威位于Admin仓库deploy.md。 -->
<!-- [Sync] 2026-11-08: Admin改用GitHub手动完整制品发布，保留原数据与禁交换策略，旧Compose正文归历史。 -->
# 阿里云 ECS 发布

## 当前范围与入口

| 发布单元 | 权威入口 | 当前职责 |
| --- | --- | --- |
| Admin／Gateway | [Admin发布指南](../../../ink-admin-memory/docs/deploy.md)及[GitHub手动Actions](https://github.com/glide-the/dream-im-platform/actions/workflows/deploy-admin.yml) | Linux runner打包完整制品，ECS原systemd／embedded supervisor运行，Drizzle管理共享schema |
| Dream Web／backend | [Remote SSH手册](remote-ssh.md)或当前已确认的本机／宿主部署入口 | 维护Dream应用；Admin认证、数据与Gateway仍经既有授权API访问 |
| nginx边缘入口 | [边缘转发手册](natapp-edge-relay.md) | 按显式topology维护公开路由，保留现有域名与认证身份 |

2026-11-08的Admin现用服务为`ink-memory-admin.service`，运行用户`ink-admin`，完整制品沿`pnpm run start:embedded`启动。数据库保留原PostgreSQL目录；普通发布无迁移DDL、重建、旧备份恢复或工作区文件同步。ECS保持swap／zswap禁用。原工作区、认证、权限与历史保持。

本机正常Admin与ECS按当次已核对拓扑分别维护；发布ECS代码保留Dream现有数据源、issuer、Client、service credential与BFF配置。本机3000的实际运行／传输方式归[当前执行回执](../exec/cross-platform-chat-continuation-20261104.md)，禁止从历史SSH转发或旧容器地址推断现用数据库。

## Admin手动打包发布

1. 打开上述GitHub Actions，选择 **Build and deploy Admin (manual)**，点击 **Run workflow** 并选择`main`。push／PR执行CI检查，发布由手动事件触发。
2. runner执行锁定安装、打包合同、统一`pnpm test:release-receiver`、单元／lint／完整类型与构建，上传与source SHA绑定的Linux制品。
3. deploy通过已配置专用受限SSH key执行preflight及固定deploy命令。服务器核对原实例、Node、摘要、原env、数据目录、资源及check-only迁移后切换原服务，ECS保留已验证制品作为恢复依据。
4. 核对run的部署回执、source／BUILD_ID、本机与ECS固定公网HTTP200、原数据目录／配置。失败重试及回滚沿[Admin指南](../../../ink-admin-memory/docs/deploy.md#失败后重试与恢复)，候选已创建时保留原目录并使用新run ID。

公开登录页HTTP200属于发布检查。真实账户、手机创建→Web原Thread／Claude会话继续及真实模型验收独立留证。当前成功发布与剩余本人认证前提见[Admin采用记录](../../../ink-admin-memory/docs/verification/chat-continuation-20261108.md)。公网波动按具体异常分类保留，入口策略保持。

## Dream配置与后续维护

Dream的[prepare-env.sh](../../deploy/remote-ssh/prepare-env.sh)读取已登记的HTTPS Gateway／Product origins、service Client／secret、BFF handle secret与显式磁盘预算，生成0600运行配置。它保留Admin PostgreSQL凭证在Admin边界；旧`DREAM_ADMIN_ENV_FILE`／PG alias／共享数据库网络说明归下方历史。已有正常配置按原部署入口维护，禁止从旧Admin Compose env复制数据库或认证密钥。

Admin root receiver安装版本、私有服务器配置及专用key维护归[服务手册](../../../ink-admin-memory/docs/deploy-services.md)。普通应用发布保留已安装receiver；修改接收器时单独完成测试、摘要核对、备份、原子替换与受限preflight。Dream仓库不增加Admin发布器、临时DDL或替代会话框架。

## 历史Remote SSH Compose正文（已退役）

下方原文保留2026-08～09的Admin容器、bootstrap、数据库alias及swap说明。其Admin脚本已退役；当前运维使用上方手动Actions及Admin手册。历史数值与命令退出现行发布步骤。

<details>
<summary>查看旧Admin／Dream Compose原文</summary>

<!-- BEGIN ALIYUN_COMPOSE_HISTORY -->
# 阿里云 ECS 部署
<!--
[Input] Admin/Dream Remote SSH topology, embedded PostgreSQL alias, and public HTTPS service origins.
[Output] Define Alibaba ECS release order, secure cross-repository configuration, verification, and rollback.
[Sync] 2026-08-22: route Dream Gateway and Product API through the public HTTPS
                    Admin origin while retaining the shared network only for embedded PG.
[Sync] 2026-08-22: add calibrated backend read BPS/IOPS limits after a real
                    Claude resume turn saturated the ECS system disk and blocked SSH/health.
[Sync] 2026-09-12: distinguish the edge-only NATAPP relay topology from the ECS Compose topology.
-->

## 服务与仓库边界

| 发布单元 | 权威仓库 | 服务/数据 |
|----------|----------|-----------|
| Admin 平台 | `../ink-admin-memory` | 单 Admin/Gateway 容器、内嵌 PostgreSQL、Artifact volume、Drizzle migration |
| Dream 应用 | 当前仓库 | frontend、backend、Mihomo TUN |

独立 PostgreSQL 和 MinIO 容器已经移除。Admin 镜像内的 `@ink-memory/db`
supervisor 管理 PostgreSQL 18.1；对象存储设置为 `FILE_STORAGE_TYPE=disabled`。
Dream 不发布数据库、不执行 migration，也不管理 Admin volume。

```mermaid
flowchart LR
  Internet["Internet / Cloudflare"] --> Nginx["ECS nginx :80/:443"]
  Nginx --> Frontend["Dream frontend :8080"]
  Nginx --> Backend["Dream backend :8765"]
  Nginx --> Admin["Admin/Gateway :3100"]
  subgraph AdminContainer["ink-memory-admin container"]
    Admin --> PG["embedded PostgreSQL :5432"]
  end
  Backend -->|"HTTPS Gateway + Product API"| Nginx
  Backend -->|"ink-memory-postgres:5432"| PG
```

Admin Compose 同时在 external network 发布 `ink-memory-admin` 与
`ink-memory-postgres` alias。PG 只监听容器/共享网络，不映射 ECS host port。

### NATAPP 边缘代理替代拓扑

当 ECS 不再承载 Dream/Admin 运行服务、只保留 Cloudflare 后的 nginx 边缘入口时，
不得继续运行上述 Compose 发布或从旧 AutoDL 端口猜上游。此拓扑把既有 Dream
frontend/backend 域名统一转发到一个显式 Dream origin，并把 Admin 域名单独转发到
显式 Admin origin；它不改变 Admin-owned PostgreSQL、认证、Gateway 或 Dream 数据
所有权，也不授权停止或释放 AutoDL 实例。

使用 [`switch-edge-relay.sh`](../../deploy/remote-ssh/switch-edge-relay.sh) 同时备份和
更新两份 nginx 站点。脚本仅在 `nginx -t` 通过后平滑 reload，失败自动恢复；完整
origin 身份核对、SSE/WebSocket、公开路由与回滚合同见
[`natapp-edge-relay.md`](natapp-edge-relay.md)。两种拓扑是明确选择，不应把 NATAPP
origin 写入 Compose 的内部数据库或服务地址。

## ECS 前置条件

- Docker Engine 与 `docker-compose` 兼容命令；
- nginx；
- `/dev/net/tun`（Dream Mihomo）；
- 至少 2GB swap；
- 安全组按管理方式放行 `22`、`80`、`443`，不要开放 3000/3100、5432、8080、8765。

```bash
export REMOTE_SSH_HOST=39.97.252.88
export REMOTE_SSH_USER=root
export REMOTE_PLATFORM_NETWORK=ink-memory-platform
```

## 1. 发布 Admin 与内嵌 PostgreSQL

```bash
cd ../ink-admin-memory

ADMIN_PUBLIC_ORIGIN=https://ink-admin.suoxya.com \
DREAM_PUBLIC_ORIGIN=https://ink-frontend.suoxya.com \
./deploy/remote-ssh/prepare-env.sh

export REMOTE_APP_DIR=/srv/ink-admin-memory
./deploy/remote-ssh/deploy.sh check
./deploy/remote-ssh/deploy.sh plan
```

生成的 `deploy/remote-ssh/.env` 为 mode `0600`，保留 PostgreSQL、Session、
Gateway、Provider encryption 和 Product API secrets；不包含 MinIO/S3/AWS 凭据。
ECS 内嵌 PG 默认 `shared_buffers=96MB`、`max_connections=50`。
低内存 ECS 的 Admin image build 固定为 1 个 Next worker、640MB V8 heap，并串行
安排 Next build 与系统包安装；这些是 build 配置，不改变运行时业务路径。Dream
Remote SSH 同步会排除本机 virtualenv、QA artifacts、generated output 与 vendor
worktree，避免非构建输入挤占 ECS 发布盘。

### 首次导入现有 PostgreSQL

只有目标 embedded volume 没有用户表时才使用：

```bash
./deploy/remote-ssh/deploy.sh bootstrap
```

脚本从 mode-0600 `.env.local` 验证 Admin package 管理的本机 embedded cluster，临时
启动后生成 PG18 gzip 压缩纯 SQL，上传到远端 `backups/`，再由同 major 的
`@ink-memory/db`/`psql` 流式导入空目标。目标非空会 fail closed；本机 data directory
保留，MinIO 数据不迁移。其他源配置必须通过 `LOCAL_SOURCE_ENV_FILE` 显式选择。

常规发布：

```bash
./deploy/remote-ssh/deploy.sh deploy
```

顺序固定为 image build → package migration → 38/38 check → Admin start →
embedded PG/Admin/nginx verify。`RUN_DB_MIGRATIONS=false`，应用启动不执行 DDL。

## 2. 发布 Dream frontend/backend

```bash
cd ../ink-dream-memory

DREAM_ADMIN_ENV_FILE=../ink-admin-memory/deploy/remote-ssh/.env \
DREAM_GATEWAY_ORIGIN=https://ink-admin.suoxya.com \
DREAM_PRODUCT_ORIGIN=https://ink-frontend.suoxya.com \
DREAM_BACKEND_BLOCK_DEVICE=/dev/vda \
DREAM_BACKEND_READ_BPS=32mb \
DREAM_BACKEND_READ_IOPS=400 \
./deploy/remote-ssh/prepare-env.sh

export REMOTE_APP_DIR=/srv/ink-and-memory
export REMOTE_FRONTEND_PUBLIC_ORIGIN=https://ink-frontend.suoxya.com
export REMOTE_BACKEND_PUBLIC_ORIGIN=https://ink-backend.suoxya.com
export REMOTE_API_BASE_URL=${REMOTE_BACKEND_PUBLIC_ORIGIN}
export REMOTE_CORS_ALLOW_ORIGINS=${REMOTE_FRONTEND_PUBLIC_ORIGIN}
export REMOTE_COMPOSE_OVERRIDE_FILE=deploy/remote-ssh/docker-compose.platform.yml
export REMOTE_COMPOSE_ENV_FILE=deploy/remote-ssh/.env

./deploy/remote-ssh/deploy.sh check
./deploy/remote-ssh/deploy.sh deploy
```

Dream env generator 从 Admin 的 mode-0600 env 读取生产 PG 帐号，生成指向
`ink-memory-postgres:5432` 的 DSN；该 alias 现在落在 Admin 容器内，而不是独立 PG
container。Gateway 与 Product API 都使用 HTTPS origin
`https://ink-admin.suoxya.com`，分别访问同一 Admin 容器公开的对应路由，满足两个
客户端的传输安全合同。共享 Docker network 只承载 embedded PostgreSQL alias。

`DREAM_BACKEND_BLOCK_DEVICE` 必须由 ECS 实际根磁盘解析结果显式提供，不从部署
环境名推断。当前 `39.97.252.88` 的根设备为 `/dev/vda`；真实 Claude resume 事故
采样达到约 93.9 MiB/s、1360 read IOPS、157 ms await、214 平均队列深度与
69.85% iowait，因此此 topology 先将 Dream backend 限制为 32 MB/s / 400 IOPS。
限制只约束承载 Claude 子进程的 backend 容器读取，不修改 Admin、PostgreSQL、
workspace、sandbox 或公开业务协议。调整值必须先保留 Admin/SSH 磁盘余量并重新测量
首 Token；回滚时删除 overlay 的 `blkio_config` 或恢复上一版 Compose 后只重建
Dream backend。

## 验证、备份与回滚

```bash
cd ../ink-admin-memory
./deploy/remote-ssh/deploy.sh ps
./deploy/remote-ssh/deploy.sh verify
./deploy/remote-ssh/deploy.sh backup

cd ../ink-dream-memory
./deploy/remote-ssh/deploy.sh ps
./deploy/remote-ssh/deploy.sh verify

docker inspect -f '{{json .HostConfig.BlkioDeviceReadBps}} {{json .HostConfig.BlkioDeviceReadIOps}}' ink-backend

curl -fsS https://ink-admin.suoxya.com/admin/login >/dev/null
curl -fsS https://ink-backend.suoxya.com/api/health
curl -fsS https://ink-frontend.suoxya.com/ >/dev/null
```

Admin `backup` 短暂停止单容器，归档已关闭的 PostgreSQL data volume，然后立即启动
并复验。物理备份只允许恢复到相同 embedded PostgreSQL major/runtime。

```bash
cd ../ink-admin-memory && ./deploy/remote-ssh/deploy.sh rollback
cd ../ink-dream-memory && ./deploy/remote-ssh/deploy.sh rollback
```

镜像回滚不回滚 PG/Artifact/Dream 数据。跨版本继续遵守 expand → 双版本兼容 →
backfill/validate → contract。

## Secret 与数据规则

- 两仓库 `deploy/remote-ssh/.env` 均 gitignored、mode `0600`，不得写入 issue/日志；
- Dream Product JWT secret 必须与 Admin 一致；
- Dream Gateway service key、issuer/audience 必须与 Admin 数据和 Gateway JWT 配置一致；
  `DREAM_GATEWAY_ORIGIN` 必须是 HTTPS，并同时作为 Dream Product API base origin；
- PostgreSQL volume 只由 Admin Compose 管理；Dream 不执行 restore、migration、DROP、
  TRUNCATE 或 runtime DDL；
- `bootstrap` 只用于首次空目标；后续使用物理备份与经过审核的恢复维护窗口；
- Admin object storage 当前 disabled；不得假设 MinIO URL/volume 仍然存在。
<!-- END ALIYUN_COMPOSE_HISTORY -->

</details>
