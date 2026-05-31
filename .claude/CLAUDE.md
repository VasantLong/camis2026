# CLAUDE.md

## 技术栈

Python 3.12 (FastAPI) + PostgreSQL 17 + MinIO + Redis 7.4，Docker Compose 编排。
mamba 环境 `camis2026`，`pip install -r requirements.txt`。

## 核心服务

| 服务 | 端口 | 凭据 | 用途 |
|------|------|------|------|
| PostgreSQL 17 | 5432 | `docapp` / `secret_pg_pwd` | 业务数据与元数据 |
| MinIO | 9000 (API), 9001 (控制台) | `minioadmin` / `minioadmin` | 文件对象存储 |
| Redis 7.4 | 6379 | `secret_redis_pwd` | 缓存、Session、队列 |
| Mailpit | 11025 (SMTP), 18025 (Web) | 无 | 开发邮件捕获 |

开发环境：`docker compose up -d postgres minio redis mailpit minio-init`

## Docker 端口问题排查

当 `docker compose up -d` 后容器显示 Running 但 `curl localhost:<port>` 拒绝连接时：

**1. 确认端口是否真正发布**
```bash
docker ps --filter "name=<name>" --format "{{.Ports}}"

docker inspect <name> --format '{{json .NetworkSettings.Ports}}' | python3 -m json.tool
```

**2. 检查容器内部监听地址**
```bash
docker exec <name> netstat -tlnp | grep <port>
```
- `0.0.0.0:<port>` + `:::<port>` → 双栈，正常
- 仅 `:::<port>` → 纯 IPv6，Docker Desktop WSL2 端口转发可能失效 → 添加环境变量强制 IPv4

**3. 修复方式**
- IPv6-only 监听：给容器加 `environment` 指定 `0.0.0.0:<port>` 绑定地址（参考 Mailpit 的 `MP_UI_BIND_ADDR` / `MP_SMTP_BIND_ADDR`）
- 宿主机端口冲突：换一个宿主机端口（如 `18025:8025`），同步更新 `app/config.py`、浏览器测试脚本和文档中的端口引用
- 重建容器：`docker compose stop <svc> && docker compose rm -f <svc> && docker compose up -d <svc>`

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
- **测试邮箱必须有标准 TLD**：Ant Design email 验证器拒绝 `@localhost`
- **DOM 变更后重新查询元素**：`.all()` 返回的引用在 render 后过期，用 `while` 循环 + 重新查询
- **`docker compose down -v` 后重跑 seed**：`seed_test_users.py` + `seed_test_activities.py` + `create_devtest_user.py`
- **文件上传用 filechooser 模式**：antd Upload 组件需 `page.expect_file_chooser()` + 点击上传按钮，不能用 `set_input_files()`；文件必须为允许类型（pdf/jpg/png/doc/docx）
- **CDP 模式不覆盖视口/DPR**：用 `browser.contexts[0]` 已有 context，不调 `set_viewport_size` 或 `new_context(viewport=...)`。CDP 截图按实际窗口像素截取，视图模拟不改变截图尺寸。详见 `tests/browser/utils.py` 和 `docs/browser-tests.md#cdp-视口与截图`
- **备案打包依赖 seed 材料**：打包测试需已有 key_materials 的活动（如 `社区志愿服务日`），不能从空活动开始

## PR 提交规范

- **提交 PR 前必须跑 pr-check**：参照 `.github/workflows/pr-checks.yml` 的 6 项检查，逐项验证：
  1. 分支命名：`feat|fix|test|docs|chore|refactor[/-]...`
  2. Python 语法：`python -m py_compile <changed.py>`
  3. 密钥扫描：`git diff main...HEAD` 检查无硬编码凭据
  4. SQL 迁移安全：无 `DROP` 不加 `IF EXISTS`、无破坏性 `ALTER`
  5. 依赖变更审查：`requirements.txt` / `package.json` 变更需人工确认
  6. 前端构建：`cd frontend && pnpm exec vite build`
- 全部通过后再 `git push` + `gh pr create`

## 文档同步

- 功能完成后同步 `docs/` 下相关文件
- 定期运行 `/neat-freak` 做全局文档审查
- CLAUDE.md 是规则手册，不写历史叙事和实现细节
