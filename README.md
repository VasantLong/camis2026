# CAMIS — 活动合规审批管理系统

> **v0.31.0** — 企业部门活动合规审批 MIS。技术栈：**Python (FastAPI)** + **React SPA** + **PostgreSQL 17** + **MinIO** + **Redis 7.4**，Docker Compose 本地编排，SOA 模块化单体架构。五大道景区活动与审批全流程：立项→方案→安保→签署→打包→审查→审批→监控。含深浅主题切换、侧边栏折叠、自定义 Tab Bar、Schema 驱动动态表单、DOCX 模板引擎、Playwright PDF 渲染。

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
├── docs/fonts/                     # 文档渲染字体（楷体、仿宋附赠）
├── playwright-svc/                 # Playwright PDF 渲染微服务 (独立 Docker 容器)
├── scripts/
│   ├── db-reset.sh                 # 一键重建数据库 (down -v + 迁移 + seed)
│   ├── check.sh                    # Python 语法 + 前端构建验证
│   ├── seed_test_users.py          # 单角色测试用户 (8 users)
│   ├── seed_test_activities.py     # 23 种子活动 (4 个月跨度)
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

### 新手上路

| 文档 | 说明 |
|------|------|
| `docs/user-guide.md` | 从零部署 → 启动 → 测试场景 → 日志调试，操作全流程 |
| `CONTEXT.md` | 领域术语表：7 角色、11 状态、核心对象定义 |
| `docs/fonts/` | 文档渲染所需中文字体（楷体、仿宋附赠，小标宋需自行获取） |

### 领域与架构

| 文档 | 说明 |
|------|------|
| `docs/state-machine.md` | 活动 11 状态生命周期 + 安保方案审核子状态 |
| `docs/api-routes.md` | 全部 REST 端点：方法、路径、权限、请求/响应体 |
| `docs/rbac.md` | 7 角色权限矩阵，角色继承关系 |
| `docs/service-design.md` | 服务层设计：11 个 Service 的职责与交互 |
| `docs/data-layer.md` | 数据模型：表结构、关联、审计字段 |
| `docs/design-process.md` | 设计流程文档 + 云迁移兼容性分析 |
| `docs/camis-UML.md` | UML 用例图、顺序图、类图 |
| `docs/oo-so.md` | OO→SO 设计方法论：从面向对象到服务导向的转型 |

### 前端

| 文档 | 说明 |
|------|------|
| `docs/frontend.md` | 技术栈（React 19 + Ant Design 6 + Zustand + TanStack Query）、导航设计、组件约定 |
| `docs/ui-design-report.md` | 界面设计报告：用户分析、线框图、高保真原型 |

### 测试

| 文档 | 说明 |
|------|------|
| `docs/browser-tests.md` | Playwright 浏览器测试手册：CDP 连接、选择器规范、常见陷阱 |

### 分析与报告

| 文档 | 说明 |
|------|------|
| `docs/analysis-design-report.md` | 系统分析与设计综合报告 |
| `docs/data-layer-report.md` | 数据层专题报告：存储三原则、审计追踪 |
| `docs/report-references.md` | 月报/报表参考数据与口径说明 |

### 架构决策记录

| ADR | 决策 |
|-----|------|
| `docs/adr/0001.md` | 模块化单体 + 服务导向架构 |
| `docs/adr/0002.md` | RBAC 用户模型替代类继承 |
| `docs/adr/0003.md` | 前端技术选型（React + Vite + Ant Design） |
| `docs/adr/0004.md` | AI 嵌入方向 |
| `docs/adr/0005-task-driven-navigation.md` | 任务驱动导航设计 |
| `docs/adr/0006-document-template-system.md` | DOCX 模板引擎 + 版本管理 + 跨模板同步 |

### 字体资源

| 文档 | 说明 |
|------|------|
| `docs/fonts/README.md` | 文档渲染所需中文字体获取与安装说明 |
