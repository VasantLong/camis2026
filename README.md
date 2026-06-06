# CAMIS — 活动合规审批管理系统

> **v0.22.0** — 企业部门活动合规审批 MIS。技术栈：**Python (FastAPI)** + **React SPA** + **PostgreSQL 17** + **MinIO** + **Redis 7.4**，Docker Compose 本地编排，模块化单体架构。新增文档模板生成系统（DOCX 渲染 + 版本管理）。

## 快速启动

```bash
# 1. 一次性完整重置（含数据库、种子数据、PDF 渲染服务）
bash scripts/db-reset.sh

# 2. 后端 (Python 3.12, mamba env: camis2026)
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 3. 前端 (React + Vite)
cd frontend && pnpm install && pnpm dev

# 4. 验证
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
├── migrations/                     # Alembic 数据库迁移
├── migrations/                     # Alembic 数据库迁移（Python）
├── init-scripts/                   # PostgreSQL 扩展（仅 uuid-ossp）
│   └── 00-extensions.sql
├── docs/init-scripts-archive/      # 历史 DDL（已由 Alembic 替代）
├── playwright-svc/                 # Playwright PDF 渲染微服务 (独立 Docker 容器)
├── scripts/
│   ├── db-reset.sh                 # 一键重建数据库 (down -v + 迁移 + seed)
│   ├── check.sh                    # Python 语法 + 前端构建验证
│   ├── seed_test_users.py          # 单角色测试用户 (8 users)
│   ├── seed_test_activities.py     # 47 种子活动 (4 个月跨度)
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
│   └── templates/                  # 文档模板 (DOCX + Pydantic schema)
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
