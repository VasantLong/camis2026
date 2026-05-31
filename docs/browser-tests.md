# 浏览器测试手册

基于 Playwright + Windows Edge CDP 的前端自动化测试套件。

## 前提

- Windows 端 Edge 浏览器以调试模式运行
- Docker 服务运行（`docker compose up -d`）
- 后端运行（端口 8000）
- 前端运行（端口 5173）
- Python 环境已安装 `playwright` 包

## 启动 Edge 调试模式

在 Windows PowerShell 中（管理员）：

```powershell
taskkill /F /IM msedge.exe
& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222
```

> **无需 `--force-device-scale-factor` 参数。** 视口和 DPR 由 Playwright 自动继承已有浏览器 context，不需要手动干预。

## 执行测试

所有脚本从项目根目录运行，复用同一个 CDP 连接：

```bash
cd /home/vasant/projects/work/camis2026
python tests/browser/01_auth.py
python tests/browser/02_activity_crud.py
# ... 依次执行
```

WSL2 镜像网络模式下，`127.0.0.1:9222` 直接连通 Windows Edge。

## 测试清单

| 脚本 | 覆盖场景 | 说明 |
|------|---------|------|
| `00_inspect.py` | 页面侦察 | 截图所有页面 + 列出交互元素，为后续脚本提供 selector |
| `01_user_lifecycle.py` | 用户全生命周期 | 错误登录→正确登录→登出→注册→欢迎邮件→角色申请→改邮箱→验证→改联系方式→会话踢出 |
| `02_activity_crud.py` | 活动 CRUD | API 创建活动 → 浏览器验证列表/详情/历史/文档/筛选 |
| `03_workflow.py` | 工作流 + 通知 | 全状态流转→驳回→签署→强制取消→终态锁定→通知铃铛→点击跳转 |
| `04_permissions.py` | 权限边界 | 无角色 403 + 角色按钮显隐(SecurityOfficer/Manager 拆分) |
| `05_gov_liaison.py` | 政府审批 | 审批通过/补充材料/驳回—不通过 |
| `06_dashboard.py` | 仪表盘 | 统计卡片/状态分布/异常列表/月报导出 |
| `08_filing.py` | 备案全流程 | 签署材料→审查→打包→纸质交接 |
| `11_admin_role_approval.py` | 角色审批 | admin_mgr 审批/驳回角色申请 |
| `12_document_upload.py` | 文档上传 | 活动详情 → 文档 tab → filechooser 上传 → 验证列表 |
| `14_superadmin_users.py` | 用户管理 | 用户列表→详情抽屉→归档→取消归档→编辑角色→启/停用 |
| `16_activity_tabs.py` | 活动分类 | 待操作/已完成 Tab 切换 → 终态活动正确归类 |

## 架构

```
tests/browser/
├── utils.py                   # 共享模块 (helpers, CDP/BASE 常量, create_page)
├── 00_inspect.py              # 页面侦察
├── 01_user_lifecycle.py       # 用户全生命周期（注册/登录/角色/邮箱/联系方式）
├── 02_activity_crud.py        # 活动 CRUD
├── 03_workflow.py             # 工作流 + 通知中心
├── 04_permissions.py          # 权限边界
├── 05_gov_liaison.py          # 政府审批
├── 06_dashboard.py            # 仪表盘
├── 08_filing.py               # 备案全流程（签署/审查/打包/交接）
├── 11_admin_role_approval.py  # 角色审批（admin_mgr）
├── 12_document_upload.py      # 文档上传
├── 14_superadmin_users.py     # 用户管理（列表/详情/归档/角色/启停）
├── 16_activity_tabs.py        # 活动列表分类
├── .gitignore                 # 忽略 recordings/
├── recordings/                # 视频录制输出 (gitignored)
└── screenshots/               # 测试截图输出
```

## 视频录制

通过环境变量 `RECORD=1` 启用 CDP screencast 录制，帧合成为 MP4：

```bash
RECORD=1 python tests/browser/01_auth.py
# → tests/browser/recordings/01_auth/recording.mp4
```

所有 01~16 脚本均已集成录制支持（参见 `utils.py` 的 `ScreencastRecorder` 类）。

## 登录限流排查

后端使用 Redis 做登录失败限流（5 次失败 / 15 分钟窗口），超限返回 429 "登录尝试过多，请15分钟后再试"。登录历史仍写入 DB `login_attempts` 表做审计。

**清除限流（开发调试）：**

```bash
# 方式 1：重启 Redis（丢失所有缓存）
docker compose restart redis

# 方式 2：精确清除 devtest 限流键
docker compose exec redis redis-cli -a secret_redis_pwd DEL login_attempts:devtest@test.com

# 方式 3：清除全部限流键
docker compose exec redis redis-cli -a secret_redis_pwd --scan --pattern "login_attempts:*" | xargs -r docker compose exec redis redis-cli -a secret_redis_pwd DEL
```

Redis key TTL 为 15 分钟，届时自动过期无需手动清除。

## CDP 视口与截图

**核心原则：CDP 模式下不覆盖视口、不设 DPR、不创建新 context。截图 = 浏览器窗口所见即所得。**

### 正确做法

使用已有浏览器 context 创建页面，不加任何视口或 DPR 覆盖：

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")

    # 使用已有 context，不创建新的
    if len(browser.contexts) > 0:
        context = browser.contexts[0]
    else:
        context = browser.new_context()

    page = context.new_page()
    page.goto("http://localhost:5173/login")
    page.screenshot(path="screenshot.png")
    context.close()
```

项目已封装为 `utils.create_page(browser)`，所有测试脚本通过它创建页面。

### 为什么不能覆盖视口

| 方法 | innerWidth 改变 | 截图尺寸改变 | 副作用 |
|------|:---:|:---:|------|
| `set_viewport_size()` | ✅ | ❌ | 截图仍为实际窗口尺寸 |
| CDP `Emulation.setDeviceMetricsOverride` | ✅ | ❌ | 同上 |
| `new_context(viewport=..., device_scale_factor=...)` | ✅ | ✅ | **创建新浏览器窗口**，尺寸=viewport×DPR |

CDP 模式下 `page.screenshot()` 按**实际窗口物理像素**截取。视口模拟只改变 CSS 布局（`innerWidth`），不改变截图捕获区域。唯一能改变截图尺寸的方法是 `new_context()`，但它会创建新窗口，导致窗口尺寸不一致。

### 复盘：本次调试走过的弯路

1. 误设 `device_scale_factor=1.5`（将 Windows 150% 系统缩放等同于浏览器 DPR，但 CDP 浏览器 DPR 实际为 1.0）
2. 用 `new_context(viewport=2560, dpr=1.5)` → 物理窗口 3840px 超出屏幕，内容裁切
3. 用 CDP session 手动设 device metrics → innerWidth 变了但截图尺寸不变
4. 用 `new_context(viewport=1280, dpr=2)` → 截图对但新窗口 2560px 与 Edge 窗口不一致
5. **最终方案**：`browser.contexts[0]` → 不覆盖任何参数，截图=所见

**教训：CDP 模式下先诊断、后动手。从最简方案（不用任何覆盖）开始，确认不满足再逐层加。**

## 关键设计决策

### CDP 连接而非本地浏览器

WSL2 内 Playwright 通过 `connect_over_cdp("http://127.0.0.1:9222")` 连接 Windows 端 Edge。WSL2 网络镜像模式下 `127.0.0.1` 等同 Windows localhost。优势：

- 无 Chromium 版本兼容问题（Ubuntu 26.04 无预编译包）
- 测试时可实时观察浏览器操作
- 截图分辨率等于本机显示器（2560x1600）

### API 创建数据 + 浏览器验证渲染

避免 Playwright 操作复杂的 Ant Design 组件（DatePicker showTime、Upload 拖拽），用 API 创建测试数据，浏览器端只验证渲染和交互。

### 客户端路由导航

登录后使用侧边栏点击（React Router 客户端导航）而非 `page.goto()`，避免 SPA 全量重载丢失 Zustand auth 状态。

### `:visible` 选择器

Ant Design Modal 关闭后 DOM 不销毁，使用 `.ant-modal:visible` 前缀限定当前可见 Modal 内的元素，避免选中隐藏的旧 Modal 子元素。

### 模块级 `didRefresh` 标志

React 19 StrictMode 双重挂载组件时，第一次 API 调用消耗 refresh token，第二次调用失败。`didRefresh` 模块级变量跨挂载去重，且 `setChecking(false)` 始终执行，防止 Spin 死锁。

## 已知缺口 (TODO)

以下场景尚无浏览器测试覆盖：

| 优先级 | 缺口 | 说明 |
|--------|------|------|
| **高** | 密码重置 (forgot-password) | 请求重置 → 收邮件 → 点击链接 → 设新密码 |
| **高** | 角色申请驳回 | 管理员驳回角色申请 → 用户看到驳回状态 |
| **高** | 关键词搜索 + 日期筛选 | 活动列表搜索框、日期范围筛选、组合筛选 |
| **中** | 活动编辑 | 修改活动字段（名称、日期、地点等） |
| **中** | 分页 | 超过一页时活动列表分页功能 |
| **中** | 空状态渲染 | 零活动/零通知/零角色申请时的空状态 UI |
| **中** | 排序 | 表头点击排序 |
| **中** | 文档下载 | 上传后点击下载链接 |
| **低** | 404 页面 | 访问不存在路由时的 404 页面 |
| **低** | 修改密码（已登录） | 在个人中心修改密码 |
| **低** | 并发登录 | 同一用户从两个浏览器同时登录 |
| **低** | 活动删除 | 彻底删除活动（如有此功能） |
| **低** | Token 刷新 | 访问 Token 过期后透明刷新 |
| **低** | 移动端响应式 | 窄视口下布局适配 |

## 运维管理待办

| 优先级 | 事项 | 说明 |
|--------|------|------|
| **高** | devtest 降权 | devtest 为全角色聚合"上帝账号"，仅保留为 break-glass 紧急救火；日常运维改用单角色 `admin_mgr` |
| **高** | 至少 2 个 SuperAdmin | 防止唯一管理员被误操作后无人能管理系统 |
| **中** | 同级互斥保护 | SuperAdmin 不应能修改其他 SuperAdmin 的角色/状态，防止互相削权 |
| **中** | 运维审计日志 | 记录所有 `administer_users` 操作（归档/启停/改角色），写入独立审计表 |

## 添加新测试

复制任一脚本骨架：

```python
from pathlib import Path
from playwright.sync_api import sync_playwright
from utils import CDP, BASE, create_page

OUT = Path(__file__).parent / "screenshots"
failed = 0

def check(cond, msg):
    global failed
    if cond: print(f"  OK: {msg}")
    else: failed += 1; print(f"  FAIL: {msg}")

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(CDP)
    page = create_page(browser)
    page.context.clear_cookies()

    errors = []
    page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}"))
    page.on("pageerror", lambda e: errors.append(f"PAGE_ERROR: {e}"))

    # ... test steps ...

    page.screenshot(path=f"{OUT / 'name_final.png'}", full_page=True)
    page.close()

    for e in errors:
        if "[error]" in e or "PAGE_ERROR" in e:
            print(f"  {e}")

    if failed > 0:
        raise SystemExit(1)
```
