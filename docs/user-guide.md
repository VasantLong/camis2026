# 用户操作手册

## 启动系统

```bash
# 终端 1：Docker 服务（如未启动）
docker compose up -d

# 终端 2：后端 API
cd /home/vasant/projects/work/camis2026
uvicorn app.main:app --reload --port 8000

# 终端 3：前端开发服务器
cd /home/vasant/projects/work/camis2026/frontend
pnpm dev
```

浏览器打开 **http://localhost:5173**

---

## 测试帐号

| 用户名 | 密码 | 角色 | 可访问页面 |
|--------|------|------|-----------|
| `tester1` | `pass123` | Promoter + AdminStaff | 活动管理、仪表盘 |
| `testuser` | `test123` | 无角色 | 仅登录（无功能权限） |

> 如需其他角色（SecurityOfficer、GovLiaison），可在数据库分配：
> ```bash
> docker exec doc_postgres psql -U docapp -d doc_metadata \
>   -c "INSERT INTO user_roles (user_id, role_id) VALUES ('<user-uuid>', '<role-uuid>');"
> ```
>
> 角色 UUID：
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

### 1. 后端 API 请求日志

后端 uvicorn 终端直接输出每一条 HTTP 请求：

```
INFO:     127.0.0.1:42888 - "POST /auth/login HTTP/1.1" 200 OK
INFO:     127.0.0.1:42900 - "GET /activities HTTP/1.1" 200 OK
INFO:     127.0.0.1:42900 - "PUT /activities/{id}/status HTTP/1.1" 200 OK
```

每条请求显示：客户端 IP、方法、路径、状态码。错误（4xx/5xx）同样在此显示。

### 2. 数据库查询日志（SQL 级别）

**方式一：临时开启（重启后失效）**

```bash
docker exec doc_postgres psql -U docapp -d doc_metadata \
  -c "ALTER SYSTEM SET log_statement = 'all';" \
  -c "SELECT pg_reload_conf();"
```

然后实时查看：

```bash
docker compose logs -f postgres
```

输出示例：
```
LOG:  execute <unnamed>: SELECT users.id, users.username, users.email ...
DETAIL:  parameters: $1 = 'tester1'
LOG:  execute <unnamed>: INSERT INTO activities (name, type, ...) VALUES ($1, $2, ...)
```

**关闭查询日志**（减少噪音）：

```bash
docker exec doc_postgres psql -U docapp -d doc_metadata \
  -c "ALTER SYSTEM SET log_statement = 'none';" \
  -c "SELECT pg_reload_conf();"
```

**方式二：应用层 SQLAlchemy 日志**（更精细，推荐开发调试用）

在 `app/database.py` 中给 engine 添加 `echo=True`：

```python
engine = create_async_engine(DATABASE_URL, echo=True)
```

修改后重启 uvicorn，所有 SQL 语句会输出在 uvicorn 终端中，与 HTTP 请求日志交织在一起，便于追踪「哪个请求触发了哪些 SQL」。

**`log_statement` 可选值**：
| 值 | 含义 |
|----|------|
| `none` | 不记录（默认） |
| `ddl` | 只记录建表/改表语句 |
| `mod` | DDL + INSERT/UPDATE/DELETE |
| `all` | 所有语句（含 SELECT） |

### 3. Docker 服务日志

```bash
docker compose logs -f postgres    # PostgreSQL 日志（含 SQL 查询，如已开启）
docker compose logs -f minio       # MinIO 对象存储操作
docker compose logs -f redis       # Redis 缓存操作

docker compose logs -f             # 全部服务汇总
```

### 4. 请求追踪

后端每个响应头带 `X-Request-ID`。浏览器 DevTools → Network → 选任一 API 请求 → Response Headers 可见。可用此 ID 在日志中关联前后端事件。

### 5. 前端浏览器日志

打开浏览器 DevTools（F12）：

| 面板 | 用途 |
|------|------|
| Console | React 渲染警告/错误、API 错误详情 |
| Network | API 请求/响应完整内容（Header、Body、状态码、耗时） |
| Application → Cookies | 查看 `refresh_token` cookie 是否存在、过期时间 |

### 6. 前端 Vite 编译日志

运行 `pnpm dev` 的终端输出：

```
[vite] (client) hmr update /src/App.tsx        ← 热更新成功
[vite] Internal server error: ...               ← 编译错误
```

---

## 推荐调试工作流

开发测试时，开 4 个终端窗口：

| 终端 | 运行内容 | 看什么 |
|------|---------|--------|
| 1 | `docker compose logs -f postgres` | 每条 SQL 查询 |
| 2 | `uvicorn app.main:app --reload --port 8000` | HTTP 请求 + SQLAlchemy echo |
| 3 | `cd frontend && pnpm dev` | 前端编译热更新 |
| 4 | 浏览器 DevTools (F12) → Network 面板 | API 请求详情 |
