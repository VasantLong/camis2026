# CAMIS — 活动合规审批管理系统

企业部门活动合规审批 MIS。技术栈：**Python (FastAPI)** + **React SPA** + **PostgreSQL 17** + **MinIO** + **Redis 7.4**，Docker Compose 本地编排，模块化单体架构。

## 快速启动

```bash
# 1. 仅启动基础设施 (PostgreSQL + MinIO + Redis)，不启动 Docker 里的 app 避免端口冲突
docker compose up -d postgres minio redis minio-init

# 2. 后端 (Python 3.12, mamba env: camis2026)
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 3. 前端 (React + Vite)
cd frontend && pnpm install && pnpm dev

# 4. 验证
curl http://localhost:8000/health    # 后端
open http://localhost:5173           # 前端
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

## 文档

| 文档                     | 内容                                        |
| ------------------------ | ------------------------------------------- |
| `.claude/CLAUDE.md`      | 开发环境、常用命令、架构约束                |
| `CONTEXT.md`             | 领域术语表                                  |
| `docs/api-routes.md`     | 22 个 REST 端点详细契约                     |
| `docs/state-machine.md`  | 活动 10 状态生命周期                        |
| `docs/frontend.md`       | 前端实现文档（48 TS 文件）                  |
| `docs/browser-tests.md`  | Playwright 浏览器测试手册（7 脚本 37 断言） |
| `docs/user-guide.md`     | 用户操作手册（5 个测试场景）                |
| `docs/rbac.md`           | RBAC 权限配置：4 角色、17 权限、路由映射    |
| `docs/design-process.md` | 设计流程与进度                              |
| `docs/adr/`              | 架构决策记录 (4 篇)                         |
