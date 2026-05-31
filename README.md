# CAMIS — 活动合规审批管理系统

> **v0.19.0** — 企业部门活动合规审批 MIS。技术栈：**Python (FastAPI)** + **React SPA** + **PostgreSQL 17** + **MinIO** + **Redis 7.4**，Docker Compose 本地编排，模块化单体架构。

## 快速启动

```bash
# 1. 仅启动基础设施 (PostgreSQL + MinIO + Redis + Mailpit)
docker compose up -d postgres minio redis mailpit minio-init

# 2. 初始化测试数据
python scripts/seed_test_users.py
python scripts/seed_test_activities.py
python scripts/create_devtest_user.py

# 3. 后端 (Python 3.12, mamba env: camis2026)
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 4. 前端 (React + Vite)
cd frontend && pnpm install && pnpm dev

# 5. 验证
curl http://localhost:8000/health    # 后端
open http://localhost:5173           # 前端
open http://localhost:18025           # Mailpit
```

> 详细启动说明（含生产模式 Gunicorn 部署）见 [docs/user-guide.md](docs/user-guide.md)。

## 架构

| 层       | 技术                                                      | 职责                         |
| -------- | --------------------------------------------------------- | ---------------------------- |
| 前端     | React 19 + Vite + Ant Design 6 + TanStack Query + Zustand | SPA 交互界面                 |
| 应用     | FastAPI (Python 3.12)                                     | REST API、权限校验、业务逻辑 |
| 元数据   | PostgreSQL 17                                             | 业务数据、文档元信息、RBAC   |
| 文件存储 | MinIO (S3 兼容)                                           | 文档文件本体                 |
| 缓存     | Redis 7.4                                                 | 热点缓存、会话               |

## 项目结构

```
camis2026/
├── docker-compose.yml              # 容器编排 (PostgreSQL + MinIO + Redis + Mailpit)
├── Dockerfile / gunicorn.conf.py   # 生产镜像
├── .env / .env.example             # 环境变量 (.env 不入 git)
├── requirements.txt                # Python 依赖
├── pyproject.toml                  # pytest 配置
├── CONTEXT.md                      # 领域术语表
├── init-scripts/                   # PostgreSQL 初始化 DDL
│   ├── 01-init-tables.sql          # users, projects, documents
│   ├── 02-activity-tables.sql      # 活动域 13 表
│   ├── 03-rbac-tables.sql          # RBAC 权限 + 种子数据
│   ├── 04-documents-migration.sql
│   ├── 05-notifications.sql
│   ├── 06-refresh-tokens.sql       # refresh token + login_attempts
│   ├── 07-superadmin.sql           # SuperAdmin + 角色申请表
│   ├── 08-filing-workflow.sql      # 备案材料 seed
│   ├── 09-user-archive.sql          # 用户归档 (is_archived)
│   ├── 10-notification-reference.sql # 通知关联引用 (reference_id/type)
│   ├── 11-activity-sponsor-fields.sql # 主办方联系人/联系方式
│   ├── 12-user-contact.sql           # 用户联系方式
│   └── 12-user-archive-reason.sql    # 归档原因 + 归档时间
├── scripts/
│   ├── seed_test_users.py          # 单角色测试用户 (8 users)
│   ├── seed_test_activities.py     # 23 种子活动 + seed 用户
│   └── create_devtest_user.py      # 全能测试用户 (devtest)
├── app/                            # FastAPI 后端
│   ├── main.py                     # 入口, lifespan, CORS
│   ├── config.py / database.py     # Pydantic-settings + async engine
│   ├── auth.py / deps.py / rbac.py # JWT + 依赖注入 + 权限
│   ├── email.py                    # SMTP 邮件 (dev: Mailpit)
│   ├── errors.py / middleware.py   # 异常处理 + RequestID
│   ├── logging_config.py           # 统一日志 (10MB 轮转)
│   ├── models/                     # SQLAlchemy ORM
│   ├── schemas/                    # Pydantic 请求/响应
│   ├── routers/                    # REST 端点 (auth, activities, filings, dashboard, admin)
│   └── services/                   # 业务逻辑层
├── tests/                          # pytest + Playwright 浏览器测试
├── frontend/                       # React SPA
│   └── src/ (pages/, api/, components/, stores/, hooks/, types/)
└── docs/                           # 设计文档 + ADR
```

## 文档

| 文档                     | 内容                                  |
| ------------------------ | ------------------------------------- |
| `.claude/CLAUDE.md`      | AI 规则手册：架构约束、开发流程、红线 |
| `CONTEXT.md`             | 领域术语表（7 角色、12 状态）         |
| `docs/api-routes.md`     | REST 端点契约                         |
| `docs/state-machine.md`  | 活动 12 状态生命周期                  |
| `docs/frontend.md`       | 前端实现 + 导航设计              |
| `docs/ui-design-report.md` | 界面设计报告（用户分析+线框图+原型） |
| `docs/browser-tests.md`  | Playwright 浏览器测试手册 |
| `docs/user-guide.md`     | 用户操作手册                          |
| `docs/rbac.md`           | 权限配置                              |
| `docs/design-process.md` | 设计流程 + 云迁移兼容性               |
| `docs/adr/`              | 架构决策记录                          |
