# CLAUDE.md

## 项目概述

这是一个基于三层存储架构的文档管理系统后端，技术栈为 Python (FastAPI) + PostgreSQL 17 + MinIO + Redis 7.4，全部通过 Docker Compose 进行本地编排部署，设计目标是从本地开发平滑迁移至云服务器。

**Python 环境**: miniforge3 (mamba) 管理，项目环境名 `camis2026`，Python 3.12。依赖通过 `pip install -r requirements.txt` 安装。

## 开发环境架构

### 环境配置

- **开发终端**: WSL2 Ubuntu，所有命令在此执行
- **Docker 引擎**: Windows 端的 Docker Desktop，已开启 WSL2 Integration
- **代码位置**: 所有项目文件必须存放在 WSL2 Linux 文件系统内 (如 `/home/用户名/your-project/`)，禁止放在 `/mnt/c/` 下，以保证文件挂载性能
- **端口映射**: 容器通过 Docker 端口映射暴露到 `localhost`，Windows 和 WSL2 均可直接访问

### 核心服务

| 服务          | 镜像                  | 端口                      | 凭据                        | 用途                       |
| ------------- | --------------------- | ------------------------- | --------------------------- | -------------------------- |
| PostgreSQL 17 | `postgres:17`         | 5432                      | `docapp` / `secret_pg_pwd`  | 结构化业务数据与文档元数据 |
| MinIO         | `quay.io/minio/minio` | 9000 (API), 9001 (控制台) | `minioadmin` / `minioadmin` | 文档文件本体对象存储       |
| Redis 7.4     | `redis:7.4-alpine`    | 6379                      | 密码: `secret_redis_pwd`    | 热点缓存、Session、队列    |
| Mailpit       | `axllent/mailpit`     | 1025 (SMTP), 8025 (Web)  | 无                          | 开发环境邮件捕获           |

### 版本选择说明

- **PostgreSQL 17**：当前最新稳定大版本，18.0 刚发布尚不稳定；17 相比 16 有显著性能提升，且阿里云/腾讯云/AWS 均已提供托管支持，确保上云时版本完全兼容。
- **Redis 7.4**：7.x 系列最新稳定版，所有云厂商托管服务普遍支持。Redis 8.0 云上托管支持尚不普遍，暂不采用，待上云时再视情况升级。

## 架构设计核心约束

### 数据存储三原则

1. **PostgreSQL 只存元数据，不存文件内容**：文档本体存入 MinIO，数据库只记录路径、大小、类型等元信息
2. **MinIO 只存文件，不存业务逻辑**：权限校验、文档归属等逻辑由后端应用负责
3. **Redis 只做缓存和队列，不做持久主存储**：所有缓存数据丢失后必须能从 PostgreSQL 恢复

### 文件上传流程 (写入)

1. 后端接收文件流和业务参数（活动ID、标签等）
2. 调用 MinIO SDK 将文件流式直传至 `company-docs` 存储桶
3. 文件路径规则：`activities/{activity_id}/{uuid}.{ext}`
4. 在 PostgreSQL `documents` 表中插入元数据记录，必须包含 `minio_path`、`file_size`、`content_type`、`uploader_id` 字段
5. 删除 Redis 中相关缓存键 (如 `activity:{id}:docs`)

### 文件访问流程 (读取)

1. 后端校验用户权限
2. 从 PostgreSQL 查询文档的 `minio_path`
3. 用 MinIO SDK 生成有效期为 15-30 分钟的预签名 URL (Presigned URL)
4. 302 重定向至该 URL，严禁后端代理文件流
5. 将查询到的元数据写入 Redis 缓存

### 安全约束

- 所有服务运行在 `doc_network` 内部 Docker 网络，生产环境严禁对外暴露 MinIO 和 PostgreSQL 端口
- 凭据通过 `.env` 文件注入，禁止硬编码
- MinIO 不直接对外暴露，只有后端应用可访问
- 文件访问权限由后端应用在生成预签名 URL 前完成校验

### 云迁移兼容性

- 代码使用 S3 兼容 SDK 与 MinIO 交互，上云时仅需替换 Endpoint 即可切换到阿里云 OSS 或腾讯云 COS
- PostgreSQL、Redis 可直接使用云厂商托管服务，无需代码改动

## 初始化检查清单

Docker 服务启动后，需验证以下项目：

- [ ] MinIO 控制台可访问: `http://localhost:9001`，Bucket `company-docs` 由 minio-init 容器自动创建
- [ ] PostgreSQL 可连接: `localhost:5432`，数据库 `doc_metadata` 存在，3 张表已建
- [ ] Redis 可连接: `localhost:6379`，使用 `AUTH secret_redis_pwd` 认证通过
- [ ] Mailpit 可访问: `http://localhost:8025`，开发邮件在此查看
- [ ] 安装 Python 依赖: `mamba activate camis2026 && pip install -r requirements.txt`
- [ ] 初始化测试数据: `python scripts/seed_test_activities.py && python scripts/create_devtest_user.py`
- [ ] 启动后端: `uvicorn app.main:app --reload --port 8000`
- [ ] 验证后端: `curl http://localhost:8000/health`（三项均为 `ok`）

## 项目代码结构

```
camis2026/
├── pyproject.toml              # pytest asyncio 配置
├── docker-compose.yml          # 容器编排定义 (含 app 服务)
├── Dockerfile                  # 生产镜像 (python:3.12-slim + gunicorn)
├── gunicorn.conf.py            # 4 uvicorn workers, 120s timeout
├── .env / .env.example         # 环境变量 (.env 不入 git)
├── requirements.txt            # Python 依赖
├── CONTEXT.md                  # 领域术语表
├── init-scripts/               # PostgreSQL 初始化 DDL
│   ├── 01-init-tables.sql      # 骨架: users, projects, documents
│   ├── 02-activity-tables.sql  # 活动域 13 表
│   ├── 03-rbac-tables.sql      # RBAC 4 表 + 种子数据
│   ├── 04-documents-migration.sql  # documents 表迁移
│   ├── 05-notifications.sql    # 通知表
│   └── 06-refresh-tokens.sql   # refresh token + 登录保护
├── app/                        # 后端应用代码
│   ├── main.py                 # FastAPI 入口, lifespan, CORS, middleware
│   ├── config.py               # Pydantic-settings, JWT_SECRET 必填校验
│   ├── database.py             # SQLAlchemy async engine + session
│   ├── auth.py                 # bcrypt + JWT + refresh token + 登录保护
│   ├── deps.py                 # get_current_user 依赖注入 (Bearer token)
│   ├── errors.py               # AppError 层级 + FastAPI exception handler
│   ├── logging_config.py       # 统一日志: request_id + console + 文件轮转
│   ├── middleware.py            # RequestIDMiddleware (X-Request-ID)
│   ├── rbac.py                 # require_permission 依赖工厂
│   ├── models/                 # ORM: User, Project, Document, Activity + 子实体, FilingDoc, RBAC, Notification, RefreshToken
│   ├── schemas/                # Pydantic: activity, workflow, filing, dashboard
│   ├── routers/                # 20 REST 端点 (health, auth, documents, activities, workflows, filings, dashboard)
│   └── services/               # 7 服务: ActivityService, WorkflowService, DocumentService, FilingService, NotificationService, DashboardService, MinIO client
├── tests/                      # pytest (7 文件/29 用例) + browser (7 脚本/37 断言), 见 docs/browser-tests.md
├── logs/                        # 应用日志 (10MB 轮转, gitignored)
├── frontend/                   # React SPA (Vite + Ant Design + TanStack Query + Zustand)
│   └── src/                    # 48 TS 文件, 9 页面, 8 API 模块, 见 docs/frontend.md
└── docs/                       # 设计文档 (UML, 状态机, API路由, 服务设计, ADR, 前端, 测试)

## 用户协作习惯

### 开发流程

1. **先计划后动手**：任何非 trivial 改动（新增功能、调整架构、修改权限模型）必须先写计划、确认后再执行。使用 Plan Mode。
2. **分阶段实施**：大功能拆成多个分支。例如先做 SuperAdmin + 角色申请 → 再做安保部负责人 → 再做备案流程。
3. **后端先、前端后**：先完成 API 端点 + 测试通过，再写前端页面。
4. **一个分支一个主题**：分支命名 `feat/xxx`、`fix/xxx`、`test/xxx`，不混入无关改动。

### 提交习惯

- 格式严格遵循 `type(scope): English description (中文关键词)`
- 一个提交只做一件事，小而聚焦
- 提交前通常要求先验证（pytest + 前端肉眼确认）
- 不会用 `git add -A`，精确 staging 每个相关文件
- 做完一个功能或阶段后要求 review 分支目标是否达成

### 领域设计偏好

- 讨论业务术语和流程多于讨论代码实现
- 权限模型倾向角色继承（负责人 = 普通人员全部权限 + 管理权限）
- 数据表倾向于完整审计（如 material_audits 而不是在 key_materials 加字段）
- 状态机变更需要同步更新 `docs/state-machine.md` 和 `CONTEXT.md`

### 验证方式

- 后端：`pytest` 29 用例全绿是基线
- 前端：写完代码后要求"告诉我如何验证"，需要具体的操作步骤和预期效果
- DB 变更：接受 `docker compose down -v` 重建
- 开发环境：只用 `docker compose up -d postgres minio redis mailpit minio-init`，不启动 Docker 里的 app 服务

### 文档同步

- 功能完成后必须同步文档（`docs/rbac.md`、`docs/api-routes.md`、`docs/user-guide.md` 等）
- 定期运行 `/neat-freak` 做全局文档审查
- CLAUDE.md 是给 AI 的规则手册，不写历史叙事和实现细节
```
