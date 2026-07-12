# AGENTS.md — camis2026

## 技术栈

Python 3.12 (FastAPI) + PostgreSQL 17 + MinIO + Redis 7.4，Docker Compose 编排。
环境管理使用 **pixi**（v0.72.2）：`pixi install` 自动创建隔离环境（`.pixi/envs/default/`）。
所有 Python 命令通过 `pixi run <cmd>` 或 `pixi shell` 执行，无需手动 pip install。

## 核心服务

| 服务 | 端口 | 凭据来源 | 用途 |
|------|------|----------|------|
| PostgreSQL 17 | 5432 | `.env` (`PG_USER` / `PG_PASSWORD`) | 业务数据与元数据 |
| MinIO | 9000 (API), 9001 (控制台) | `.env` | 文件对象存储 |
| Redis 7.4 | 6379 | `.env` (`REDIS_PASSWORD`) | 缓存、Session、队列 |
| Mailpit | 11025 (SMTP), 18025 (Web) | 无 | 开发邮件捕获 |

开发环境启动：
```bash
pixi run infra-up              # 启动 postgres/minio/redis/mailpit
pixi run db-upgrade            # Alembic 迁移
# 然后开另一个终端：
pixi run dev                   # uvicorn reload
```

### pixi tasks 速查
| 命令 | 用途 |
|------|------|
| `pixi run dev` | 启动开发服务器（--reload） |
| `pixi run infra-up` | 启动 Docker 基础设施 |
| `pixi run db-upgrade` | 执行迁移 |
| `pixi run db-migrate "msg"` | 自动生成迁移脚本 |
| `pixi run test` | 运行测试 |
| `pixi run seed-all` | 灌入种子数据 |
| `pixi run db-reset` | 重建数据库（全量重置） |
| `pixi shell` | 进入 pixi 环境（可选） |

## Schema 迁移

- **改模型 = 必须生成 Alembic migration**：修改 `app/models/*.py` 中的列/表/约束后，必须 `alembic revision --autogenerate`，审查后提交
- `init-scripts/` 已归档至 `docs/init-scripts-archive/`，仅保留 `00-extensions.sql`（uuid-ossp + update_updated_at 函数）
- Docker 启动不再依赖 init-scripts；基线迁移 `642e62051696_initial_baseline` 包含全部 20+ 表 DDL + RBAC 种子数据 + `login_attempts` 表
- Docker 启动自动执行 `alembic upgrade head`
- 服务层现有 11 个 Service：ActivityService, WorkflowService, DocumentService, FilingService, NotificationService, DashboardService, **AuthService**, **AdminService**, **ReportDataService**（月报数据查询）, **ReportRenderer**（Playwright PDF 渲染，HTTP 客户端）, **TemplateService**（DOCX 渲染 + 版本管理 + 跨模板同步 + PDF 后台生成，借助 docxtpl + LibreOffice）
- Filing 补件回路：待补充备案材料 ≈ 带标记的待安保方案设计，复用编辑→提交→签署→打包→交接。Manager 重签复用已上传签名
- UC6 已移除：Liaison 审批通过后系统自动流转到审批通过-待举办，通知所有经手人。AdminStaff 可标记结束（举办中→已结束）
- 新加 Service 命名 `XxxService`，构造函数 `def __init__(self, db: AsyncSession)`
- 文档模板：`app/templates/{type}/` 含 `schema.py`（Pydantic 表单）和 `template.docx`（docxtpl Jinja2 占位符），详见 `docs/adr/0006.md`。模板字体：标题方正小标宋简体、标签楷体_GB2312、正文仿宋_GB2312（均在 `~/.local/share/fonts/`）

## Playwright PDF 渲染

- `playwright-svc/` — 独立 Docker 微服务（FastAPI + headless Chromium），`POST /render` 接收 `{month, data_key, token}` 返回 PDF bytes
- 主应用通过 `httpx` 调用 `http://localhost:3000/render`；开发环境 CDP 连接 Windows Edge (`127.0.0.1:9222`) 作为后备
- Docker 部署：`playwright-svc` 容器内 Debian Bookworm 运行 Chromium headless，Ubuntu 26.04 WSL2 不支持 Playwright Chromium
- 前端报表页 `/reports/monthly/:month` 使用 URL JWT token 自认证，渲染 `@ant-design/charts` 图表，`.chart-ready` 标记通知 Playwright 截图时机

## 脚本速查

| 脚本 / pixi task | 用途 |
|------|------|
| `pixi run db-reset` | 一键重建数据库（down -v + 迁移 + seed + 清限流） |
| `pixi run check-python` | Python 语法检查 + 前端构建验证 |
| `pixi run templates-rebuild` | 从源文件重建 5 个 DOCX 模板，设置字体格式 |
| `pixi run seed-all` | 灌入全部种子数据 |

## 数据存储三原则（红线）

1. PostgreSQL 只存元数据，不存文件内容
2. MinIO 只存文件，不存业务逻辑
3. Redis 只做缓存和队列，不做持久主存储

## 安全

- 凭据通过 `.env` 注入，禁止硬编码
- 文件访问权限在后端校验，MinIO 不直接对外

## 领域设计偏好

- 权限模型倾向角色继承（负责人 = 普通人员全部权限 + 管理权限）
- 数据表倾向于完整审计（material_audits 而非 KeyMaterial 加字段）
- 状态机变更同步更新 `docs/state-machine.md` 和 `CONTEXT.md`

## 浏览器测试规范

- **禁止 `page.goto()` 跨页面导航**：CDP 模式下全页面刷新丢失 Zustand auth 状态，用侧边栏点击、表格链接等客户端导航
- **测试从用户行为出发**：点击 → 等待 → 观察，不绕过 UI 直接调 API
- **antd v6 选择器优先用文本/图标**：`get_by_text()`、`filter(has_text=...)`、`has(.anticon-user)`，不依赖 CSS 类名（v6 的 CSS-in-JS 生成 hash 类名）
- **antd Select 用 `keyboard.type()` 操作**：v6 Select 的 input 是 `readonly` 的 `role="combobox"`，不能用 `fill()`。先 `click()` 打开下拉，再 `keyboard.type(option)` + `Enter` 完成选择
- **测试邮箱必须有标准 TLD**：Ant Design email 验证器拒绝 `@localhost`
- **DOM 变更后重新查询元素**：`.all()` 返回的引用在 render 后过期，用 `while` 循环 + 重新查询
- **`docker compose down -v` 后重跑 seed**：`pixi run seed-all`（或 `seed_test_users.py` + `seed_test_activities.py` + `create_devtest_user.py`）
- **文件上传用 filechooser 模式**：antd Upload 组件需 `page.expect_file_chooser()` + 点击上传按钮，不能用 `set_input_files()`；文件必须为允许类型（pdf/jpg/png/doc/docx）
- **CDP 模式不覆盖视口/DPR**：用 `browser.contexts[0]` 已有 context，不调 `set_viewport_size` 或 `new_context(viewport=...)`。CDP 截图按实际窗口像素截取，视图模拟不改变截图尺寸。详见 `tests/browser/utils.py` 和 `docs/browser-tests.md#cdp-视口与截图`
- **备案打包依赖 seed 材料**：打包测试需已有 key_materials 的活动（如 `社区志愿服务日`），不能从空活动开始

## PR 提交规范

- **提交 PR 前必须跑 pr-check**：参照 `.github/workflows/pr-checks.yml` 的 6 项检查，逐项验证：
  1. 分支命名：`feat|fix|test|docs|chore|refactor[/-]...`
  2. Python 语法：`pixi run python -m py_compile <changed.py>`
  3. 密钥扫描：`git diff main...HEAD` 检查无硬编码凭据
  4. 数据库迁移安全：检查 Alembic migration 无不可逆操作（`op.drop_table`/`op.drop_column` 必须有对应 downgrade）
  5. 依赖变更审查：`requirements.txt` / `package.json` 变更需人工确认
  6. 前端构建：`cd frontend && pnpm exec vite build`
- 全部通过后再 `git push` + `gh pr create`

## 文档同步

- 功能完成后同步 `docs/` 下相关文件
- 定期做全局文档审查
- AGENTS.md 是规则手册，不写历史叙事和实现细节

## 编码习惯（高频踩坑）

- **改 SQL/后端返回字段 → 立即 grep Pydantic 模型**：`grep "class.*Response" app/routers/` 确认新字段在模型中。漏了会被 FastAPI 截断，前端拿到空值难排查。
- **查实体用 select().where()，不要 db.get()**：`db.get()` 走主键，ActivityPlan/SecurityPlan 主键是自增 id 不是 activity_id。
- **三元链分支互斥检查**：复杂条件渲染后，`grep -n "? (" file.tsx` 确认各分支不重叠。Manager 和 canEditSecurity 必须互斥（`!isManager` guard）。
- **加 debug 代码后先 compile**：`python -m py_compile` 确认语法，logger 是否已 import。
- **外部进程必须限流**：soffice/LibreOffice 用 asyncio.Semaphore(1) 串行化。
- **签名/图片跨组件共享**：blob URL（当前会话）→ presigned URL（刷新恢复）→ FilledDocument snapshot（跨会话），三层回退。

## 已知技术限制

- **Docker 端口问题**：WSL2 下容器 IPv6-only 监听可能导致端口转发失效。排查方法详见 `docs/`。如遇 `curl localhost:<port>` 拒绝连接但容器 Running，检查容器内部监听地址。
- **WSL2 端口排除**：Windows WinNAT 端口排除可能占用应用端口。`netsh interface ipv4 show excludedportrange protocol=tcp` 排查。
