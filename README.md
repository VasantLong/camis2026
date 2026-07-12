# CAMIS — 活动合规审批管理系统

> **v0.31.0** — 企业部门活动合规审批 MIS。技术栈：**Python (FastAPI)** + **React SPA** + **PostgreSQL 17** + **MinIO** + **Redis 7.4**，Docker Compose 本地编排，SOA 模块化单体架构。五大道景区活动与审批全流程：立项→方案→安保→签署→打包→审查→审批→监控。含深浅主题切换、侧边栏折叠、自定义 Tab Bar、Schema 驱动动态表单、DOCX 模板引擎、Playwright PDF 渲染。

## 快速启动

> **本地环境管理使用 pixi**（v0.72.2），详见 [docs/user-guide.md](docs/user-guide.md)。
> 生产部署使用 Docker，不依赖 pixi。

### 前置条件

| 依赖 | 版本 | 验证 |
|------|------|------|
| Docker Compose | v2+ | `docker compose version` |
| pixi | 0.72+ | `pixi --version` |
| pnpm | 9+ | `pnpm --version` |

```bash
# 1. 安装 pixi 环境（首次一次性）
pixi install

# 2. 一次性完整重置（基础设施 + 数据库 + 种子数据）
pixi run db-reset

# 3. 启动后端（热重载）
pixi run dev

# 4. 另一个终端：启动前端
cd frontend && pnpm install && pnpm dev

# 5. 验证
curl http://localhost:8000/health    # 后端
open http://localhost:5173           # 前端
open http://localhost:18025          # Mailpit
```

> 详细启动说明见 [docs/user-guide.md](docs/user-guide.md)。

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
├── pixi.toml / pixi.lock           # pixi 环境声明 + 锁定（本地开发）
├── .env / .env.example             # 环境变量 (.env 不入 git)
├── requirements.txt                # 仅用于 Docker 生产构建
├── pyproject.toml                  # pytest 配置
├── CONTEXT.md                      # 领域术语表
├── migrations/                     # Alembic 数据库迁移
├── init-scripts/                   # PostgreSQL 扩展（仅 uuid-ossp）
│   └── 00-extensions.sql
├── docs/init-scripts-archive/      # 历史 DDL（已由 Alembic 替代）
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

### AI 开发规则

| 文档 | 说明 |
|------|------|
| `.claude/CLAUDE.md` | AI 助手的项目规则手册：架构约束、安全红线、编码习惯 |

### 问题回溯

| 文档 | 说明 |
|------|------|
| `docs/issues/` | 开发过程中遇到的问题与解决方案（权限、模板、认证等） |
