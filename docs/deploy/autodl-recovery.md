<!-- [Input] AutoDL direct-host topology, versioned release scripts, and persistent Admin/Dream data boundaries. -->
<!-- [Output] Safe restart, diagnosis, redeploy, and failure-recovery procedure. -->
<!-- [Pos] AutoDL recovery appendix linked from the user-first root README. -->
<!-- [Sync] 2026-09-18: define restart-first recovery without SSH tunnels or long-lived application rollback releases. -->

# AutoDL 恢复与维护

## 背景与问题

AutoDL 实例重启后，数据盘、应用 release 与配置仍可能存在，但 `screen` 中的 Admin 和 Dream 进程不会自动恢复。此时 WebUI-6006/6008 可能显示 404，Dream 也可能记录 `ADMIN_SERVICE_AUTH_UNAVAILABLE`、`ADMIN_TIMEOUT` 或 Session 检查失败。

## 目标与边界

恢复顺序固定为 Admin → Dream。Admin 拥有 PostgreSQL、认证、Gateway 和数据库接口；Dream 只在 Admin 验证通过后启动。恢复不得删除 `/root/ink-autodl/data`、`/root/autodl-tmp/ink-memory` 或运行中的业务数据，不建立 SSH 隧道，也不把当前公网域名写死到仓库。

成功发布只保留当前应用 release，不保留长期旧 release。候选切换失败时，发布脚本可在本轮临时 `previous` 存在期间恢复应用；migration 只前向执行，不能靠应用 rollback 反向迁移数据库。

## 概念与规则

| 路径或端口 | 责任 |
| --- | --- |
| `/root/ink-autodl/admin/current` | 当前 Admin 不可变 release |
| `/root/ink-autodl/dream/current` | 当前 Dream 不可变 release |
| `/root/ink-autodl/data/postgres` | Admin 管理的 PostgreSQL 持久数据 |
| `/root/autodl-tmp/ink-memory` | Dream workspace、artifact、文件与 Runtime 持久目录 |
| `6008` | Admin 私有监听，由 WebUI-6008 映射 |
| `6006` / `8765` | Dream Next 公网入口 / 私有 FastAPI |

只输出 `/etc/profile.d/autodl.env.sh` 中的 `AutoDLService6006URL` 与 `AutoDLService6008URL`。该文件还含面板 token，不得整体打印或复制到回执。

## 快速恢复

在本机两个干净仓库中确认 gitignored `platform.env` 指向当前 SSH 主机、端口、ControlPath 与下面动态发现的公网 origin，然后重新投影配置：

```bash
# 远端只读取两个服务地址
source /etc/profile.d/autodl.env.sh
printf 'Dream: %s
Admin: %s
'   "${AutoDLService6006URL}" "${AutoDLService6008URL}"
```

```bash
# Admin 先启动并验证
cd /Users/dmeck/project/ink-admin-memory
./deploy/autodl-ssh/prepare-env.sh
./deploy/autodl-ssh/deploy.sh check
./deploy/autodl-ssh/deploy.sh start

# Dream 后启动并验证
cd /Users/dmeck/project/ink-dream-memory
./deploy/autodl-ssh/prepare-env.sh
./deploy/autodl-ssh/deploy.sh check
./deploy/autodl-ssh/deploy.sh start
```

`start` 复用已经资格化的 `current` release，不构建新版本、不执行 Dream migration，也不删除持久目录。设备重启后优先使用这一流程。

## 状态与日志

```bash
# Admin
cd /Users/dmeck/project/ink-admin-memory
./deploy/autodl-ssh/deploy.sh status
./deploy/autodl-ssh/deploy.sh logs
./deploy/autodl-ssh/deploy.sh verify

# Dream
cd /Users/dmeck/project/ink-dream-memory
./deploy/autodl-ssh/deploy.sh status
./deploy/autodl-ssh/deploy.sh logs
./deploy/autodl-ssh/deploy.sh verify
```

判断顺序：

1. Admin `6008` 与 PostgreSQL `54329` 是否运行，真实 service-token/capability 是否为 200。
2. Dream `8765` 与 `6006` 是否运行，`/api/health` 是否为 200。
3. 当前实例 WebUI-6008、WebUI-6006 是否分别返回 Admin 登录页和 Dream 页面。
4. Session 或 callback 失败时，重新从当前实例公网映射生成两端 env；不要只改浏览器地址。

## 完整发布

源代码、Runtime、配置合同或 release 需要更新时，使用完整候选发布：

```bash
cd /Users/dmeck/project/ink-admin-memory
./deploy/autodl-ssh/prepare-env.sh
./deploy/autodl-ssh/test-topology.sh
./deploy/autodl-ssh/deploy.sh deploy

cd /Users/dmeck/project/ink-dream-memory
./deploy/autodl-ssh/prepare-env.sh
./deploy/autodl-ssh/test-topology.sh
./deploy/autodl-ssh/deploy.sh deploy
```

Admin 在 16008 验证候选后执行唯一 Drizzle 前向 migration、OAuth catalog 协调与原子切换。Dream 在 16006/18765 验证 Next/FastAPI 候选后切换 6006/8765。每个发布只有在本机与公网验证全部通过后才清理旧应用 release；PostgreSQL、workspace、artifact 与共享文件不在清理范围。

## 失败处理

- **Admin 候选失败：** 停止 Dream 发布；保留当前 Admin 和数据库，修复候选后重试。
- **Admin migration 后应用失败：** 恢复本轮旧 Admin 应用仅用于继续服务；数据库保持前向状态，通过兼容版本或 forward fix 修复。
- **Dream 候选失败：** Admin 保持当前版本，Dream `current` 不切换。
- **Dream 切换后验证失败：** 发布脚本在临时 `previous` 尚存在时恢复旧 Dream；不修改 Admin、PostgreSQL 或共享文件。
- **`ADMIN_TIMEOUT`：** 检查 Admin 服务和调用延迟，不提高并发重试、不启用 Dream 直连数据库。
- **公网 404：** 先验证本机 listener，再确认 AutoDL 当前端口映射；复制代码而未启动 screen supervisor 不算部署完成。

恢复完成后记录精确 commit、release 目录、端口、公开 HTTP 状态、migration/capability 结果与未执行的真实业务验收。secret、cookie、token、正文和数据库 DSN 不进入回执。
