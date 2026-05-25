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
docker compose up -d postgres minio redis

# 终端 2：后端 API（热重载，改代码自动重启）
cd /home/vasant/projects/work/camis2026
mamba activate camis2026
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

# 启动后端 (确认 Docker 服务已运行)
uvicorn app.main:app --reload --port 8000

# 健康检查
curl http://localhost:8000/health
```

---

## 测试帐号

| 用户名     | 密码      | 角色                  | 可访问页面           |
| ---------- | --------- | --------------------- | -------------------- |
| `tester1`  | `pass123` | Promoter + AdminStaff | 活动管理、仪表盘     |
| `testuser` | `test123` | 无角色                | 仅登录（无功能权限） |

> 如需其他角色（SecurityOfficer、GovLiaison），可在数据库分配：
>
> ```bash
> docker exec doc_postgres psql -U docapp -d doc_metadata \
>   -c "INSERT INTO user_roles (user_id, role_id) VALUES ('<user-uuid>', '<role-uuid>');"
> ```
>
> 角色 UUID：
>
> ```
> Promoter        dc865a6e-6da6-4add-8667-885e128377ea
> SecurityOfficer 2c977316-1e85-43bf-a2fa-6bedf92b5feb
> AdminStaff      c598f8e4-361c-4296-b291-3328e38ed3a6
> GovLiaison      162c159b-cdc8-439e-89f8-9be31d88eb8b
> ```

---

## 测试场景

### 场景 A：宣策部（Promoter）— 立项 + 方案上传

1. 用 `tester1 / pass123` 登录
2. 进入「活动管理 → 创建新活动」
3. 填写活动信息并提交 → 跳转详情页，状态为「待设计方案」
4. 在文档 tab 上传方案文件（PDF/JPG/PNG/DOC，≤50MB）
5. 返回活动列表验证新建的活动出现在列表中
6. 按状态筛选、关键词搜索验证筛选功能

### 场景 B：安保部（SecurityOfficer）— 审批流转

> 前提：先在数据库给 tester1 分配 SecurityOfficer 角色（保留 Promoter）

1. 打开某个「待设计方案」的活动详情
2. 点击「提交到安保方案设计」→ 状态变为「待安保方案设计」
3. 点击「驳回（内部循环）」→ 输入驳回原因 → 状态不变，日志增加驳回记录
4. 重新提交 → 点击「签署完成—提交备案」→ 状态变为「待备案申请」
5. 在「备案」tab 中依次操作：校验材料 → 打包 → 纸质交接

### 场景 C：政府对接（GovLiaison）— 批文上传

> 前提：分配 GovLiaison 角色，活动处于「备案材料已交接」状态

1. 打开活动详情
2. 点击「审批通过」→ 状态变为「审批通过」
3. 或点击「需补充材料」→ 状态变为「待补充备案材料」
4. 或点击「驳回—不通过」→ 状态变为「不通过/已终止」

### 场景 D：行政部（AdminStaff）— 仪表盘 + 强制操作

> tester1 已有 AdminStaff 角色

1. 从侧边栏进入「活动面板」
2. 查看统计卡片（总数/合规率/已取消/已延期）
3. 查看状态分布和最近异常列表
4. 导出月报 → 提示"报表生成中"
5. 在任意非终态活动详情中点击「强制取消」或「强制延期」
6. 确认勾选框 + 填写原因 → 活动进入终态，锁定后续操作

### 场景 E：权限边界

1. 用 `testuser / test123`（无角色）登录
2. 访问 `/activities` → 重定向到 `/login`（因为无 `view_owned_activity` 权限）

---

## 实时查看系统日志

启动 uvicorn 后，终端会实时输出所有后端活动。日志同时持久化到 `logs/camis.log`（10MB 轮转，5 个备份）。

### 统一日志格式

```
2026-05-24 23:56:29 INFO  [5d9c44477528] redis GET key=doc:ca67... hit=False
2026-05-24 23:56:29 INFO  [5d9c44477528] SELECT users WHERE username = $1
2026-05-24 23:56:29 INFO  [5d9c44477528] minio put_object bucket=company-docs key=...
2026-05-24 23:56:29 WARN  [5d9c44477528] 404 NOT_FOUND: 活动不存在
2026-05-24 23:56:29 INFO  [5d9c44477528] POST /auth/login → 200 222ms
```

每条日志包含：`时间 级别 [request_id] 内容`。同一请求的所有 SQL、Redis、MinIO、HTTP 日志共享一个 `[request_id]`。

### 覆盖范围

| 层级      | 内容                       | 示例                                                    |
| --------- | -------------------------- | ------------------------------------------------------- |
| HTTP 请求 | 方法、路径、状态码、耗时   | `POST /auth/login → 200 222ms`                          |
| SQL 查询  | 完整 SQL + 参数 + 耗时     | `SELECT users WHERE ... $1::VARCHAR ('tester1',)`       |
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
| 1    | `uvicorn app.main:app --reload --port 8000` | HTTP + SQL + Redis + MinIO 全链路日志 |
| 2    | `cd frontend && pnpm dev`                   | 前端编译热更新                        |

浏览器 DevTools (F12) → Network 面板查看 API 请求详情。
