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

| 脚本 | 覆盖场景 | 断言数 | 说明 |
|------|---------|:-----:|------|
| `00_inspect.py` | 页面侦察 | — | 截图所有页面 + 列出交互元素，为后续脚本提供 selector |
| `01_auth.py` | 认证 | 11 | 登录(错误密码/用户名/正确)/登出/注册/重复注册/重定向 |
| `02_activity_crud.py` | 活动 CRUD | 8 | API 创建活动 → 浏览器验证列表/详情/历史/文档/筛选 |
| `03_workflow.py` | 工作流 | 8 | 状态流转→驳回→签署→强制取消→终态锁定 |
| `04_permissions.py` | 权限 | 5 | 无角色 403 + 有角色侧边栏权限项显隐 |
| `05_gov_liaison.py` | 政府审批 | 6 | 审批通过/补充材料/驳回—不通过 |
| `06_dashboard.py` | 仪表盘 | 5 | 统计卡片/状态分布/异常列表/月报导出 |
| `07_role_request.py` | 角色申请 | 9 | 注册→/profile→选角色→提交→等待审核 |
| `08_filing_materials.py` | 材料签署审查 | 10 | SecurityOfficer 签署 + GovLiaison 审查 + 审查历史 |
| `09_email_verification.py` | 邮件验证 | 7 | 注册 → Mailpit 捕获欢迎邮件 → 验证标题/内容 |
| `10_email_change.py` | 邮箱更改 | 10 | 点击编辑 → 输入新邮箱 → Mailpit 验证链接 → 新邮箱登录 |
| `11_admin_role_approval.py` | 角色审批 | 8 | 用户申请角色 → 管理员登录 → 按邮箱查找 → 批准 |
| `12_document_upload.py` | 文档上传 | 7 | 活动详情 → 文档 tab → filechooser 上传 → 验证列表 |
| `13_filing_pack.py` | 备案打包交接 | 8 | 签署材料 → 打包 → 勾选确认 → 纸质交接 |

**合计 ~101 断言。**

## 架构

```
tests/browser/
├── utils.py               # 共享模块 (CDP/BASE 常量, create_page)
├── 00_inspect.py          # 页面侦察
├── 01_auth.py             # 认证
├── 02_activity_crud.py    # 活动 CRUD
├── 03_workflow.py         # 工作流
├── 04_permissions.py      # 权限
├── 05_gov_liaison.py      # 政府审批
├── 06_dashboard.py        # 仪表盘
├── 07_role_request.py     # 角色申请
├── 08_filing_materials.py # 材料签署审查
├── 09_email_verification.py # 邮件验证
├── 10_email_change.py     # 邮箱更改验证
├── 11_admin_role_approval.py # 角色审批
├── 12_document_upload.py  # 文档上传
├── 13_filing_pack.py      # 备案打包交接
├── .gitignore              # 忽略 recordings/
├── recordings/             # 视频录制输出 (gitignored)
└── screenshots/           # 测试截图输出
```

## 视频录制

通过环境变量 `RECORD=1` 启用 CDP screencast 录制，帧合成为 MP4：

```bash
RECORD=1 python tests/browser/01_auth.py
# → tests/browser/recordings/01_auth/recording.mp4
```

所有 01~13 脚本均已集成录制支持（参见 `utils.py` 的 `ScreencastRecorder` 类）。

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
