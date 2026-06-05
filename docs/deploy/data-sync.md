# 数据同步指南：本地 ↔ Cloud Storage

后端运行时数据存储在 GCS bucket（通过 Cloud Storage FUSE 挂载到 `/app/data/`）。本文说明如何在本地和云端之间同步数据。

---

## 数据目录结构

```
本地：backend/data/                    云端：gs://ink-memory-data-<PROJECT_ID>/
├── ink-and-memory.db   (SQLite DB)    ├── ink-and-memory.db
├── file-storage/                      ├── file-storage/
└── agent-workspace/                   └── agent-workspace/
```

---

## 前置条件

```bash
# 确认 .storage-env 存在（由 setup-storage.sh 生成）
source .storage-env
echo $GCS_BUCKET   # 应输出 bucket 名称
```

---

## 上传本地数据到云端

```bash
source .storage-env

# 上传数据库
gsutil cp backend/data/ink-and-memory.db \
  gs://${GCS_BUCKET}/ink-and-memory.db

# 上传 file-storage 和 agent-workspace
gsutil -m rsync -r backend/data/file-storage/    gs://${GCS_BUCKET}/file-storage/
gsutil -m rsync -r backend/data/agent-workspace/ gs://${GCS_BUCKET}/agent-workspace/
```

> **注意**：Cloud Run 后端写入数据时，直接操作 GCS bucket。如果服务正在运行，上传数据库前最好先停止服务，避免写入冲突。

---

## 从云端下载数据到本地

```bash
source .storage-env

# 下载数据库
gsutil cp gs://${GCS_BUCKET}/ink-and-memory.db \
  backend/data/ink-and-memory.db

# 下载所有数据（完整备份）
gsutil -m rsync -r gs://${GCS_BUCKET}/file-storage/    backend/data/file-storage/
gsutil -m rsync -r gs://${GCS_BUCKET}/agent-workspace/ backend/data/agent-workspace/
```

---

## 查看云端数据

```bash
source .storage-env

# 查看 bucket 内容和大小
gsutil ls -l gs://${GCS_BUCKET}/
gsutil du -sh gs://${GCS_BUCKET}/

# 只查看数据库文件信息
gsutil ls -l gs://${GCS_BUCKET}/ink-and-memory.db
```

---

## 查看数据库内容

下载到本地后，用命令行或图形工具查看：

```bash
# 查看所有表
sqlite3 backend/data/ink-and-memory.db ".tables"

# 查看会话数量
sqlite3 backend/data/ink-and-memory.db \
  "SELECT COUNT(*) as total FROM user_sessions;"

# 查看最近 5 条会话
sqlite3 backend/data/ink-and-memory.db \
  "SELECT id, created_at FROM user_sessions ORDER BY created_at DESC LIMIT 5;"
```

图形工具推荐 [DB Browser for SQLite](https://sqlitebrowser.org)（免费），直接打开 `.db` 文件即可浏览表结构和数据。

---

## 手动备份

```bash
source .storage-env

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
gsutil cp gs://${GCS_BUCKET}/ink-and-memory.db \
  gs://${GCS_BUCKET}/backups/ink-and-memory_${TIMESTAMP}.db

echo "Backup saved: gs://${GCS_BUCKET}/backups/ink-and-memory_${TIMESTAMP}.db"
```

GCS bucket 已开启版本控制，每次覆盖写入都会保留历史版本，可在 Cloud Console 的 bucket 详情页恢复。

---

## SQLite WAL 模式说明

后端使用 WAL（Write-Ahead Logging）模式，运行时会产生三个文件：

| 文件 | 说明 |
|------|------|
| `ink-and-memory.db` | 主数据库文件 |
| `ink-and-memory.db-wal` | WAL 日志（活跃写入时存在） |
| `ink-and-memory.db-shm` | 共享内存文件（活跃写入时存在） |

**下载时**：如果服务正在运行，`-wal` 和 `-shm` 文件也需要一起下载，否则本地打开的数据库可能不完整。

```bash
source .storage-env

# 完整下载（含 WAL 文件）
gsutil cp "gs://${GCS_BUCKET}/ink-and-memory.db*" backend/data/
```
