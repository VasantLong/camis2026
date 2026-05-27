# CLAUDE.md

## 项目概述

基于三层存储架构的活动合规审批管理系统，技术栈为 Python (FastAPI) + PostgreSQL 17 + MinIO + Redis 7.4，Docker Compose 本地编排。

**Python 环境**: miniforge3 (mamba)，环境名 `camis2026`，Python 3.12。`pip install -r requirements.txt`。

## 环境配置与核心服务

- **终端**: WSL2 Ubuntu，所有命令在此执行
- **Docker**: Windows Docker Desktop，WSL2 Integration
- **代码位置**: WSL2 Linux 文件系统 (`/home/用户名/`)，禁止 `/mnt/c/`
- **域名**: 全部通过 `localhost` 访问

| 服务 | 端口 | 凭据 | 用途 |
|------|------|------|------|
| PostgreSQL 17 | 5432 | `docapp` / `secret_pg_pwd` | 业务数据与元数据 |
| MinIO | 9000 (API), 9001 (控制台) | `minioadmin` / `minioadmin` | 文件对象存储 |
| Redis 7.4 | 6379 | `secret_redis_pwd` | 缓存、Session、队列 |
| Mailpit | 11025 (SMTP), 18025 (Web) | 无 | 开发邮件捕获 |

## 架构约束

### 数据存储三原则（红线）

1. PostgreSQL 只存元数据，不存文件内容
2. MinIO 只存文件，不存业务逻辑
3. Redis 只做缓存和队列，不做持久主存储

### 安全

- `doc_network` 内部网络，生产环境严禁对外暴露 PostgreSQL 和 MinIO
- 凭据通过 `.env` 注入，禁止硬编码
- 文件访问权限在后端校验，MinIO 不直接对外

## 用户协作习惯

### 开发流程

1. **先计划后动手**：非 trivial 改动必须 Plan Mode，确认后执行
2. **分阶段实施**：大功能拆成多个分支
3. **后端先、前端后**：API 端点 + 测试通过，再写前端
4. **一个分支一个主题**：`feat/xxx`、`fix/xxx`、`test/xxx`，不混入无关改动

### 提交习惯

- 格式：`type(scope): English description (中文关键词)`
- 一个提交只做一件事，精确 staging 每个文件
- 提交前验证：pytest + 前端确认
- 做完后 review 分支目标是否达成

### 领域设计偏好

- 权限模型倾向角色继承（负责人 = 普通人员全部权限 + 管理权限）
- 数据表倾向于完整审计（material_audits 而非 KeyMaterial 加字段）
- 状态机变更同步更新 `docs/state-machine.md` 和 `CONTEXT.md`

### 验证方式

- 后端：`pytest` 全绿是基线
- 前端：写完代码后给出具体验证步骤和预期效果
- DB 变更：接受 `docker compose down -v` 重建
- 开发环境：`docker compose up -d postgres minio redis mailpit minio-init`

## 浏览器测试规范

- **禁止 `page.goto()` 跨页面导航**：CDP 模式下全页面刷新丢失 Zustand auth 状态，用侧边栏点击、表格链接等客户端导航
- **测试从用户行为出发**：点击 → 等待 → 观察，不绕过 UI 直接调 API
- **antd v6 选择器优先用文本/图标**：`get_by_text()`、`filter(has_text=...)`、`has(.anticon-user)`，不依赖 CSS 类名（v6 的 CSS-in-JS 生成 hash 类名）
- **测试邮箱必须有标准 TLD**：Ant Design email 验证器拒绝 `@localhost`
- **DOM 变更后重新查询元素**：`.all()` 返回的引用在 render 后过期，用 `while` 循环 + 重新查询
- **`docker compose down -v` 后重跑 seed**：`seed_test_activities.py` + `create_devtest_user.py`
- **文件上传用 filechooser 模式**：antd Upload 组件需 `page.expect_file_chooser()` + 点击上传按钮，不能用 `set_input_files()`；文件必须为允许类型（pdf/jpg/png/doc/docx）
- **备案打包依赖 seed 材料**：打包测试需已有 key_materials 的活动（如 `社区志愿服务日`），不能从空活动开始

## 初始化检查清单

- [ ] MinIO: `http://localhost:9001`，Bucket `company-docs` 已创建
- [ ] PostgreSQL: `localhost:5432`，数据库 `doc_metadata` 可连接
- [ ] Redis: `localhost:6379`，`AUTH secret_redis_pwd` 通过
- [ ] Mailpit: `http://localhost:18025`
- [ ] Python 依赖：`mamba activate camis2026 && pip install -r requirements.txt`
- [ ] 测试数据：`python scripts/seed_test_activities.py && python scripts/create_devtest_user.py`
- [ ] 后端：`uvicorn app.main:app --reload --port 8000`
- [ ] 验证：`curl http://localhost:8000/health`（三项 `ok`）

## 项目代码结构

```
camis2026/
├── docker-compose.yml / .env    # 容器编排 + 环境变量
├── CONTEXT.md                   # 领域术语表
├── init-scripts/                # PostgreSQL DDL (01-08)
├── scripts/                     # seed + dev 工具
├── app/                         # FastAPI (models/ schemas/ routers/ services/)
├── tests/                       # pytest + browser (Playwright)
├── frontend/                    # React SPA
└── docs/                        # 设计文档 + ADR
```

详细结构见 README.md。

## 文档同步

- 功能完成后同步 `docs/rbac.md`、`docs/api-routes.md`、`docs/user-guide.md` 等
- 定期运行 `/neat-freak` 做全局文档审查
- CLAUDE.md 是规则手册，不写历史叙事和实现细节
