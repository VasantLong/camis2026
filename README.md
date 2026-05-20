# CAMIS 文档管理系统

基于三层存储架构的文档管理系统后端。技术栈：**Python (FastAPI)** + **PostgreSQL 17** + **MinIO** + **Redis 7.4**，Docker Compose 本地编排，设计目标是从本地开发平滑迁移至云服务器。

## 快速启动

```bash
# 1. 启动基础设施 (PostgreSQL + MinIO + Redis)
docker compose up -d

# 2. 激活 Python 环境并安装依赖
mamba activate camis2026
pip install -r requirements.txt

# 3. 启动后端
uvicorn app.main:app --reload --port 8000

# 4. 验证
curl http://localhost:8000/health
# {"status":"ok","checks":{"postgres":"ok","minio":"ok","redis":"ok"}}
```

## 架构

| 层 | 技术 | 职责 |
|----|------|------|
| 应用 | FastAPI | 业务逻辑、权限校验 |
| 元数据 | PostgreSQL 17 | 文档元信息（路径、大小、类型） |
| 文件存储 | MinIO (S3 兼容) | 文档文件本体 |
| 缓存 | Redis 7.4 | 热点缓存、会话 |

详见 `.claude/CLAUDE.md` 获取完整架构说明和常用命令。
