# 用户操作手册

## 服务器架构：Uvicorn vs Gunicorn

FastAPI 应用本身不直接处理网络请求，需要 ASGI 服务器来运行：

```
请求 → ASGI 服务器 → FastAPI 应用 → 响应
```

| 服务器   | 定位     | 说明                                              |
| -------- | -------- | ------------------------------------------------- |
| Uvicorn  | 开发引擎 | 单进程 ASGI 服务器，支持 `--reload` 热重载        |
| Gunicorn | 生产总管 | 进程管理器，通过 `UvicornWorker` 管理多个 Uvicorn |

**关系**：Gunicorn 本身不理解 ASGI 协议，必须通过 Uvicorn worker 运行 FastAPI。开发时直接 uvicorn，足够快；生产时 Gunicorn 包一层，提供多进程管理、优雅重启和超时控制。

---

## 启动系统

### 开发环境（日常使用）

Docker 只跑基础设施，FastAPI 和前端在本地跑，支持热重载：

```bash
# 终端 1：仅启动基础设施服务（数据库 + 存储 + 缓存）
docker compose up -d postgres minio redis mailpit playwright-svc

# 终端 2：后端 API（热重载，改代码自动重启）
cd /home/vasant/projects/work/camis2026
mamba activate camis2026
alembic upgrade head    # 创建/更新数据库表（Alembic 替代了原来的 init-scripts）
uvicorn app.main:app --reload --port 8000

# 终端 3：前端开发服务器
cd /home/vasant/projects/work/camis2026/frontend
pnpm dev
```

> **注意**：不要用 `docker compose up -d` 全部启动，因为 Docker 里的 `app` 服务也会占用 8000 端口，会导致 uvicorn 启动失败（`Address already in use`）。如已启动全部，先 `docker compose stop app` 释放端口。

### 生产验证（提交前/上线前）

完整 Docker 栈启动，使用 Gunicorn + 4 个 Uvicorn worker：

```bash
# 启动全部服务（含 app）
docker compose up -d

# 查看 app 服务日志
docker compose logs -f app

# 验证健康检查
curl http://localhost:8000/health

# 停止全部
docker compose down
```

> Gunicorn 配置见 `gunicorn.conf.py`：4 workers、120s 超时、`uvicorn.workers.UvicornWorker`。

浏览器打开 **http://localhost:5173**

---

## 常用命令

```bash
# 启动所有服务 (在项目根目录执行)
docker compose up -d

# 停止所有服务
docker compose down

# 查看服务运行状态
docker compose ps

# 查看所有容器日志
docker compose logs -f

# 查看单个服务日志
docker compose logs -f postgres
docker compose logs -f minio
docker compose logs -f redis

# 重启某个服务
docker compose restart postgres

# 重新构建并启动 (修改 Dockerfile 后使用)
docker compose up -d --build

# 清除所有数据重新开始 (包括数据库卷)
docker compose down -v
docker compose up -d

# 激活 Python 环境并安装依赖
mamba activate camis2026
pip install -r requirements.txt

# 创建/更新数据库表
alembic upgrade head

# 启动后端 (确认 Docker 服务已运行)
uvicorn app.main:app --reload --port 8000

# 健康检查
curl http://localhost:8000/health
```

---

## 测试帐号

用以下脚本创建测试帐号（幂等，可重复执行）：

```bash
python scripts/seed_test_users.py       # 创建 8 个单角色测试用户
python scripts/seed_test_activities.py  # 创建 23 个种子活动（含 promoter/security/liaison 用户）
python scripts/create_devtest_user.py   # 创建 devtest（全角色全能用户）
```

| 邮箱 | 密码 | 角色 | 可访问页面 |
|------|------|------|-----------|
| `devtest@test.com` | `pass123` | 全部 7 角色 | 所有页面 |
| `promoter@test.com` | `pass123` | Promoter | 工作台、新建立项、我的活动 |
| `security@test.com` | `pass123` | SecurityOfficer | 待编制安保方案、待打包备案 |
| `security_mgr@test.com` | `pass123` | SecurityManager | 待签署确认、备案申请 |
| `liaison@test.com` | `pass123` | GovLiaison | 待审查材料、审批记录 |
| `admin@test.com` | `pass123` | AdminStaff | 工作台、活动面板、全部活动 |
| `admin_mgr@test.com` | `pass123` | AdminManager | 工作台、活动面板、角色审批 |

## 种子活动

用 `python scripts/seed_test_activities.py` 创建 23 个测试活动，覆盖全状态：

| 状态 | 活动示例 |
|------|---------|
| 待设计方案 | 2026 校园文化节、国际音乐节筹备 |
| 待安保方案设计 | 安全生产月启动仪式、消防应急演练、非遗手工艺展 |
| 待备案申请 | 社区志愿服务日、农产品展销会、元宵灯会 |
| 备案材料已交接 | 年度总结表彰大会、科技周开幕式 |
| 审批通过 | 网络安全培训讲座 |
| 审批通过-待举办 | 职工运动会、端午龙舟赛 |
| 举办中 | 春节联欢晚会 |
| 已结束 | 科普进社区活动、中秋游园会 |
| 待补充备案材料 | 法治宣传周活动 |
| 不通过/已终止 | 青年创新创业大赛、马拉松赛事报批 |
| 已取消 | 绿色环保公益行、庙会活动 |
| 已延期 | 全民读书月活动、行业博览会 |

每个活动附有对应的方案文件（PDF）、安保方案（PDF）、政府批文（PDF）、备案清单（XLSX）、工作安排（CSV）等附件。

---

## 角色申请流程

1. 注册新用户 → 自动进入 `/profile` 页面
2. 选择角色并点击"提交申请"
3. 用 `devtest@test.com` 登录 → `GET /admin/role-requests` → 查看待审批
4. `POST /admin/role-requests/{id}/approve` → 批准后用户立即获得请求的角色权限

---

## 测试场景

### 场景 A：宣策部（Promoter）— 立项 + 方案上传

1. 用 `promoter@test.com / pass123` 登录 → 进入工作台首页（`/index`）
2. 查看「待设计方案」和「我的活动」计数卡片
3. 点击「新建立项」→ 填写活动信息并提交 → 跳转详情页，状态为「待设计方案」
4. 通过侧边栏「我的活动」返回列表，验证新活动出现
5. 点击活动进入详情，在文档 tab 上传方案文件（PDF/JPG/PNG/DOC，≤50MB）

### 场景 B：安保部（SecurityOfficer + SecurityManager）— 审批流转

1. 用 `promoter@test.com` 登录，打开「待设计方案」活动，点击「提交到安保方案设计」
2. 用 `security@test.com` (SecurityOfficer) 登录，侧边栏「待编制安保方案」出现该活动
3. 编制完成后点击「签署完成—提交备案」→ 状态变为「待备案申请」
4. 如需驳回，用 `security_mgr@test.com` (SecurityManager) 登录 → 点击「驳回」

### 场景 C：政府对接（GovLiaison）— 批文上传

用 `liaison@test.com / pass123` 登录，侧边栏「待审查材料」显示待处理数量。

1. 从工作台或侧边栏进入审查列表
2. 打开活动详情 → 逐条审查关键材料（合格/不合格）
3. 全部合格后上传批文 → 标注「审批通过」
4. 或标注「需补充材料」→ 状态变为「待补充备案材料」

### 场景 D：行政部（AdminStaff）— 仪表盘 + 强制操作

用 `admin@test.com / pass123` 登录。

1. 工作台展示总活动数、审批通过率、本月新增
2. 点击「进入仪表盘」→ 查看统计卡片、状态分布、异常列表
3. 导出月报 → 提示"报表生成中"
4. 在任意非终态活动详情中点击「强制取消」或「强制延期」

### 场景 E：权限边界

1. 注册新用户（无角色）→ 工作台显示引导页，提示前往个人中心申请角色
2. 点击「前往个人中心申请角色」→ 在 `/profile` 提交角色申请
3. 用 SuperAdmin 登录 → 侧边栏「角色审批(N)」→ 批准申请

---

## 实时查看系统日志

启动 uvicorn 后，终端会实时输出所有后端活动。日志同时持久化到 `logs/camis.log`（10MB 轮转，5 个备份）。

### 统一日志格式

```
2026-05-24 23:56:29 INFO  [5d9c44477528] redis GET key=doc:ca67... hit=False
2026-05-24 23:56:29 INFO  [5d9c44477528] SELECT users WHERE email = $1
2026-05-24 23:56:29 INFO  [5d9c44477528] minio put_object bucket=company-docs key=...
2026-05-24 23:56:29 WARN  [5d9c44477528] 404 NOT_FOUND: 活动不存在
2026-05-24 23:56:29 INFO  [5d9c44477528] POST /auth/login → 200 222ms
```

每条日志包含：`时间 级别 [request_id] 内容`。同一请求的所有 SQL、Redis、MinIO、HTTP 日志共享一个 `[request_id]`。

### 覆盖范围

| 层级      | 内容                       | 示例                                                    |
| --------- | -------------------------- | ------------------------------------------------------- |
| HTTP 请求 | 方法、路径、状态码、耗时   | `POST /auth/login → 200 222ms`                          |
| SQL 查询  | 完整 SQL + 参数 + 耗时     | `SELECT users WHERE email = $1::VARCHAR ('devtest@test.com',)` |
| Redis     | GET/SET/DEL + 命中状态     | `redis GET key=doc:123 hit=True`                        |
| MinIO     | put_object / presigned_url | `minio put_object bucket=company-docs key=... size=302` |
| 业务错误  | 状态码 + 错误码 + 详情     | `404 NOT_FOUND: 活动不存在`                             |

### 日志文件

```bash
# 实时查看
tail -f logs/camis.log

# 按 request_id 过滤
grep "5d9c44477528" logs/camis.log
```

### 请求追踪

后端每个响应头带 `X-Request-ID`。浏览器 DevTools → Network → 选任一 API 请求 → Response Headers 可见。用此 ID 在日志中 `grep` 即可定位该请求的完整链路。

### 前端浏览器日志

打开浏览器 DevTools（F12）：

| 面板                  | 用途                                                |
| --------------------- | --------------------------------------------------- |
| Console               | React 渲染警告/错误、API 错误详情                   |
| Network               | API 请求/响应完整内容（Header、Body、状态码、耗时） |
| Application → Cookies | 查看 `refresh_token` cookie 是否存在、过期时间      |

### 前端 Vite 编译日志

运行 `pnpm dev` 的终端输出：

```
[vite] (client) hmr update /src/App.tsx        ← 热更新成功
[vite] Internal server error: ...               ← 编译错误
```

---

## 推荐调试工作流

开发测试时，开 2 个终端窗口：

| 终端 | 运行内容                                    | 看什么                                |
| ---- | ------------------------------------------- | ------------------------------------- |
| 1    | `alembic upgrade head && uvicorn app.main:app --reload --port 8000` | 迁移 + HTTP/SQL/Redis/MinIO 全链路日志 |
| 2    | `cd frontend && pnpm dev`                   | 前端编译热更新                        |

浏览器 DevTools (F12) → Network 面板查看 API 请求详情。
