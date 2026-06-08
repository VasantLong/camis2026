# 前端实现文档

React SPA，技术选型见 [ADR 0003](./adr/0003.md)。

## 快速开始

```bash
cd frontend
pnpm install
pnpm dev          # http://localhost:5173
pnpm build        # 生产构建 → dist/
```

Vite proxy 将 `/api/*` 转发至 `http://localhost:8000`，解决 refresh_token cookie 的 SameSite Lax 跨域问题。生产环境由 Nginx 反向代理替代。

## 目录结构

```
frontend/src/
├── api/                    # Axios 实例 + 各资源 API 函数
│   ├── client.ts           # 拦截器: 自动加 Bearer token, 401 refresh 队列
│   ├── auth.ts             # login, register, me, refresh, logout
│   ├── activities.ts       # CRUD + history + documents
│   ├── documents.ts        # upload (multipart), download (302)
│   ├── workflows.ts        # transition, reject, forceCancel, forcePostpone
│   ├── filings.ts          # validate, pack, handover, getStatus
│   ├── materials.ts        # list, sign, audit, auditHistory
│   ├── approval.ts         # create (GovLiaison 审批决策)
│   ├── roleRequest.ts      # submit role request
│   ├── notifications.ts    # list, unreadCount, markRead, markAllRead
│   ├── dashboard.ts        # panel, activityDetail, monthlyReport
│   └── templates.ts        # plan/security-plan/materials schema+draft+generate+versions+diff
├── stores/
│   └── authStore.ts        # Zustand: user, accessToken, permissions, isAuthenticated
├── hooks/
│   └── useActivityQueries.ts  # TanStack Query: activities, activity, history, documents
├── types/                  # TypeScript 接口（镜像后端 Pydantic schema）
│   ├── api.ts              # ApiErrorResponse { detail, code, fields? }
│   ├── auth.ts             # LoginRequest, RegisterRequest, TokenResponse, UserResponse
│   ├── activity.ts         # ActivityCreate, ActivityResponse, ActivityListParams, StatusLogEntry
│   ├── document.ts         # DocumentResponse
│   ├── workflow.ts         # StatusTransition, RejectRequest, ForceChangeRequest
│   ├── filing.ts           # MaterialValidation, FilingPackResult
│   ├── approval.ts         # ApprovalRecord, ApprovalRequest
│   ├── dashboard.ts        # PanelData, AnomalyEntry, ActivityDetail, MonthlyReportRequest
│   └── template.ts         # SchemaResponse, FieldDef, VersionItem/Detail/Diff, GenerateResponse
├── pages/
│   ├── LoginPage.tsx
│   ├── RegisterPage.tsx
│   ├── NotFoundPage.tsx
│   ├── ForbiddenPage.tsx
│   ├── activities/
│   │   ├── ActivityListPage.tsx    # 待操作/已完成 Tab + 筛选 + 分页列表
│   │   ├── ActivityCreatePage.tsx  # 新建表单
│   │   └── ActivityDetailPage.tsx  # 详情/历史/文档/备案
│   └── dashboard/
│       └── DashboardPage.tsx       # 统计卡片 + 状态分布 + 异常列表 + 月报
│   ├── profile/
│   │   └── ProfilePage.tsx         # 用户信息、角色状态、角色申请
│   ├── NotificationsPage.tsx       # 消息中心（未读/全部 Tab）
│   └── admin/
│       ├── RoleRequestsPage.tsx    # 待审批角色申请表格
│       └── UserManagementPage.tsx  # 用户列表、角色编辑、禁用/归档
├── components/
│   ├── auth/
│   │   ├── AuthInitializer.tsx     # App 启动时静默 refresh
│   │   └── ProtectedRoute.tsx      # 路由守卫（认证 + 权限）
│   ├── layout/
│   │   ├── AppLayout.tsx           # Sider + Header(铃铛+用户) + Content
│   │   ├── Sidebar.tsx             # 权限感知菜单
│   │   └── HeaderNotifications.tsx # 通知铃铛(未读badge+下拉)
│   ├── activities/
│   │   ├── ActivityFilters.tsx     # 状态/关键词/日期筛选 → URL searchParams
│   │   ├── ActivityTable.tsx       # 分页表格
│   │   ├── ActivityForm.tsx        # 可复用表单
│   │   └── StatusTimeline.tsx      # 状态流转时间线
│   ├── documents/
│   │   ├── DocumentUpload.tsx      # Ant Upload + multipart + 客户端校验
│   │   └── DocumentList.tsx        # 文件列表 + 下载按钮
│   ├── workflows/
│   │   ├── WorkflowActions.tsx     # 根据 status + permissions 动态渲染按钮
│   │   ├── StatusTransitionModal.tsx
│   │   ├── RejectModal.tsx
│   │   └── ForceChangeModal.tsx    # 强制取消/延期（含确认勾选）
│   ├── filings/
│   │   ├── FilingValidatePanel.tsx # 材料合规性表格
│   │   ├── FilingPackModal.tsx     # 打包确认
│   │   ├── HandoverConfirm.tsx     # 交接确认（不可逆）
│   │   ├── MaterialAuditModal.tsx  # 逐项审查弹窗（合格/不合格+意见）
│   │   └── GovLiaisonReviewPanel.tsx # GovLiaison 审批决策面板
│   ├── templates/
│   │   ├── TemplateForm.tsx        # Schema驱动动态表单 (8种字段类型+条件显隐)
│   │   ├── VersionTimeline.tsx     # 版本历史列表+详情/差异对比
│   │   ├── VersionSnapshot.tsx     # 只读快照展示 (供非编辑角色查看最新版本)
│   │   └── CommitmentSign.tsx      # 备案承诺书签署区（Plan B）
│   └── dashboard/
│       ├── StatusDistribution.tsx  # 状态分布 Progress 条
│       ├── AnomalyList.tsx         # 异常活动表格
│       └── ReportExport.tsx        # 月报导出
├── utils/
│   └── constants.ts          # 状态常量, 颜色映射, 状态转换矩阵
└── styles/
    └── global.css
```

## 通知系统

- 后端 `notifications` 表含 `reference_id`、`reference_type`，LEFT JOIN activities 取活动名
- 前端 `HeaderNotifications`：铃铛 badge → 下拉面板（活动名加粗 + 消息灰色）→ 点击跳活动详情或下载报告
- 通知由工作流状态变更时 `NotificationService.notify_role()` 自动生成，带 `reference_id` 和 `reference_type`
- 打开下拉自动标记全部已读，已读 30 天自动过滤

## Dashboard 月报

- `ReportExport.tsx`：月份选择器 → POST `/dashboard/reports/monthly`
- 后端 `BackgroundTasks` 异步生成 PDF 上传 MinIO，完成后推送通知（`reference_type="report"`）
- 前端收到 toast "报表生成中…"，用户通过铃铛通知点击下载 PDF
- `GET /dashboard/reports/{month}` 下载端点

## 文档模板系统 (P1/P2)

模板系统提供 schema 驱动的动态表单，生成标准化的活动方案、安保方案和关键材料 DOCX/PDF 文档。

### 架构

```
用户打开活动详情页 → 点击"活动方案"/"安保方案" Tab
  → 按角色显示不同视图:
     · 编辑角色 (Promoter/SecurityOfficer): TemplateForm + VersionTimeline
     · 管理角色 (AdminStaff): VersionTimeline (全部版本)
     · 其他角色: VersionSnapshot (只读快照)
  → GET /activities/{id}/plan/schema (获取字段定义+草稿+快照数据)
  → TemplateForm 根据 schema.fields 动态渲染表单
  → 保存草稿: PUT /activities/{id}/plan/draft
  → 提交生成: 确认弹窗 → POST → 活动方案立即生成 DOCX / 安保方案仅存快照
  → 活动方案"最终确定": 方案B校验 → 确认弹窗 → 流转
  → 安保方案"提交审核": 校验 → SecurityManager 签署（两步）→ 批量生成 DOCX → 流转
  → VersionTimeline 展示版本历史 → 支持详情查看和两版本差异对比
```

### 支持的字段类型

| ui_type | 组件 | 说明 |
|---------|------|------|
| `text` | Input | 单行文本 |
| `textarea` | Input.TextArea | 多行文本 |
| `number` | InputNumber | 数值输入 |
| `date` | DatePicker | 日期选择 |
| `select` | Select | 下拉选择 (options 定义) |
| `checkbox` | Checkbox | 布尔勾选 |
| `repeater` | Form.List | 可增删的动态列表 |
| `signature` | Button+Input | 签名图片上传 (P3 手写板) |

### 条件字段

字段可定义 `condition` 属性（如 `"risk_level == '高风险'"`），根据表单其他字段值动态显隐。安保方案的 `CONDITIONAL_FIELDS` 按风险等级（高风险/中低风险/低风险）控制专属字段显隐。

### 安保方案流程

SecurityOfficer 首次进入时，若 `risk_level` 为空则先弹风险等级选择器（高风险/中低风险/低风险），写入 `PUT /activities/{id}/security-plan` 后加载对应条件的表单。

Manager 签署分两步：
1. **签署三文件**：Manager 在安保方案 tab 上传签名 → 确认签署 → 系统生成安保方案+双表 DOCX → 备案承诺书签署区出现
2. **签署备案承诺书**：全部字段 autofill（从 Activity + ActivityPlan + SecurityPlan 预填），Manager 复用已上传签名 → 确认 → 生成承诺书 DOCX → 流转至「待备案申请」

**跨模板同步**：安保方案的 `security_staff_count` 变更后重新生成版本时，若风险评估表或备案承诺书已有版本，系统弹窗确认后自动为它们创建新版本（同步更新对应字段）。变更检测在前端 onSubmit 中判断，后端在 `generate()` 同一事务中完成同步。

**草稿自动保存**：表单 2s 防抖自动保存草稿，确保切换到双表子 tab 时 autofill 能读取安保方案最新的未提交数据。

**驳回重提校验**：Manager 驳回的预设原因按风险等级过滤（不含该等级不适用的字段）。Officer 重新提交时校验 highlighted 字段值是否与被驳回版本不同，未修改则阻止提交。

### 备案 Tab 阶段分段

备案 tab 根据活动状态和角色分段渲染：

| 状态 | 角色 | 可见内容 |
|------|------|---------|
| 待备案申请 | SecurityOfficer | 5 项材料列表（签署状态+版本）、打包按钮、纸质交接确认 |
| 待补充备案材料 | SecurityOfficer | 同上 + GovLiaison 补件意见横幅 |
| 备案材料已交接 | GovLiaison | 材料列表+逐项审查(合格/不合格+意见)、审核记录、批文上传(可选)、审批决策(通过/补件/驳回) |
| 审批通过 | SecurityManager | 页顶横幅：批文信息 + 确认审批结果/驳回至安保方案设计 |
| 审批通过-待举办+ | 全部角色 | 材料列表只读 + 审核记录 |

5 项备案材料统一来自 `key_materials` 表：活动方案、安保方案、风险评估报备表、安全消防责任确认书、活动备案承诺书。

## 路由

| 路径 | 页面 | 权限 | 布局 |
| ---- | ---- | ---- | ---- |
| `/login` | LoginPage | 公开 | 无 |
| `/register` | RegisterPage | 公开 | 无 |
| `/403` | ForbiddenPage | 公开 | 无 |
| `/` | → HomeRedirect | — | AppLayout |
| `/activities` | ActivityListPage | `view_owned_activity` or `view_dashboard` | AppLayout |
| `/activities/new` | ActivityCreatePage | `create_activity` | AppLayout |
| `/activities/:id` | ActivityDetailPage | `view_owned_activity` or `view_dashboard` | AppLayout |
| `/dashboard` | DashboardPage | `view_dashboard` | AppLayout |
| `/notifications` | NotificationsPage | 登录即可 | AppLayout |
| `/profile` | ProfilePage | 登录即可 | AppLayout |
| `/admin/role-requests` | RoleRequestsPage | `manage_users` | AppLayout |
| `/admin/users` | UserManagementPage | `administer_users` | AppLayout |
| `*` | NotFoundPage | 公开 | 无 |

## 认证流程

```
登录 POST /api/auth/login
  → access_token 存 Zustand authStore
  → refresh_token 由浏览器自动管理 (httpOnly cookie, path=/, 7 天)

后续请求
  → axios 请求拦截器: Authorization: Bearer <token>
  → 401 响应: 进入 refresh 队列 → POST /api/auth/refresh
    → 成功: 新 token, 重放队列中的请求（用户无感）
    → 失败: 清 auth state, 跳转 /login

App 启动
  → AuthInitializer 静默调 /api/auth/refresh
    → 有效 cookie: 恢复登录态
    → 无效/不存在: 显示登录页

登出
  → POST /api/auth/logout → 清 Zustand → 跳转 /login
```

## 导航设计

ADR: [0005-task-driven-navigation.md](./adr/0005-task-driven-navigation.md)

### 当前模式（v0.18）

侧边栏按功能模块组织：活动管理、仪表盘、个人中心、管理后台。菜单项按权限显隐（见[权限模型](#权限模型)），但所有角色共用同一套菜单结构。用户登录后需先导航到列表页再筛选，缺乏角色感知和任务引导。

### 目标模式：任务驱动导航

生产环境无多角色用户（见 [CONTEXT.md](../CONTEXT.md#角色行为特征ui-设计输入)），每个角色登录后看到的菜单直接对应其工作任务，带实时计数 Badge。

**三阶段增量路线**：

| 阶段 | 交付物 | 改动范围 | 状态 |
|------|--------|---------|------|
| P1 | 菜单项计数 Badge | `Sidebar.tsx` + 后端 `GET /activities/counts` | ✅ 已实现 |
| P2 | 角色感知 HomePage | `HomePage.tsx` + `/index` 路由 | ✅ 已实现 |
| P3 | 任务驱动侧边栏 | `Sidebar.tsx` 重构 | ✅ 已实现 |

**P3 已实现各角色菜单**（与信息架构图的设计一致）：

| 角色 | 菜单项 |
|------|--------|
| Promoter | 工作台、新建立项、我的活动(N) |
| SecurityOfficer | 工作台、待编制安保方案(N)、待打包备案(N) |
| SecurityManager | 工作台、待签署确认(N)、备案申请 |
| GovLiaison | 工作台、待审查材料(N)、审批记录 |
| AdminStaff/Manager | 工作台、活动面板(N)、全部活动 |
| SuperAdmin | 工作台、用户管理、角色审批(N)、全部活动(N) |

**P3 待办：设计 vs 实现差异**

以下菜单项在设计阶段提出，但因系统当前能力限制暂未实现。作为远期增强方向：

| 角色 | 未实现项 | 原因 | 依赖 |
|------|---------|------|------|
| SecurityOfficer | 待我签署(N) | 签署状态在 `key_materials.sign_status`，无对应的 activity 级筛选端点 | 需后端 `GET /activities?needs_sign=true` |
| GovLiaison | 今日已登记(N) | 这是统计数字，不是列表筛选维度；已作为卡片在 P2 HomePage 展示 | 无（已降级为 HomePage 卡片） |
| Admin | 待确认变更(N) | AdminStaff→AdminManager 二次确认流程尚未实现 | 需后端强制变更审批工作流 |

### 信息架构图

#### 当前页面树（v0.18）

```mermaid
flowchart TB
    subgraph Public["公开页面"]
        Login["/login<br/>LoginPage"]
        Register["/register<br/>RegisterPage"]
        NF["*<br/>NotFoundPage"]
        F403["/403<br/>ForbiddenPage"]
    end

    subgraph AppLayout["AppLayout (登录后)"]
        direction TB
        Sider["侧边栏 Sidebar"]
        Header["顶部 Header<br/>铃铛通知 + 用户下拉"]
        Content["内容区"]

        Sider --> Menu["菜单项(按功能):<br/>• 活动管理 → /activities<br/>• 仪表盘 → /dashboard<br/>• 个人中心 → /profile<br/>• 管理后台 → admin/*"]
        Menu --权限感知显隐--> Sider

        Content --> Activities["/activities<br/>ActivityListPage<br/>Tab: 待操作 | 已完成"]
        Content --> ActivityNew["/activities/new<br/>ActivityCreatePage"]
        Content --> ActivityDetail["/activities/:id<br/>ActivityDetailPage<br/>Tab: 详情 | 文档 | 备案 | 材料"]
        Content --> Dashboard["/dashboard<br/>DashboardPage<br/>统计卡片 | 状态分布 | 异常清单 | 月报"]
        Content --> Profile["/profile<br/>ProfilePage<br/>用户信息 | 角色状态 | 角色申请"]
        Content --> RoleReq["/admin/role-requests<br/>RoleRequestsPage"]
        Content --> UserMgmt["/admin/users<br/>UserManagementPage"]
    end

    Login --> AppLayout
    Register --> AppLayout
```

#### 当前角色可见菜单映射

```mermaid
flowchart LR
    subgraph Promoter["Promoter"]
        P1["活动管理<br/>(我的活动)"]
    end
    subgraph SecurityOfficer["SecurityOfficer"]
        S1["活动管理<br/>(待安保方案设计)"]
    end
    subgraph SecurityManager["SecurityManager"]
        SM1["活动管理<br/>(5个状态的安保活动)"]
    end
    subgraph GovLiaison["GovLiaison"]
        G1["活动管理<br/>(备案材料已交接)"]
    end
    subgraph AdminStaff["AdminStaff"]
        A1["活动管理"]
        A2["仪表盘"]
    end
    subgraph AdminManager["AdminManager"]
        AM1["活动管理"]
        AM2["仪表盘"]
        AM3["管理后台<br/>(角色审批)"]
    end
```

#### P1 改动：菜单项计数 Badge

侧边栏菜单项 `label` 加 `<Badge count={n} />`。

新增端点 `GET /api/activities/counts`，按角色返回计数：

```json
// Promoter → { "my_activities": 3, "pending_plan": 1 }
// GovLiaison → { "pending_review": 4, "registered_today": 1 }
// SecurityOfficer → { "pending_security_draft": 2, "pending_signature": 1, "pending_pack": 2 }
```

#### P2 改动：角色感知 HomePage

`/` 路由从直接跳转 `/activities` 改为渲染 HomePage。

```mermaid
flowchart TB
    subgraph HomePage["HomePage (根据角色渲染不同模块)"]
        direction TB

        subgraph PromoterHome["Promoter 首页"]
            PH1["👋 张三 (宣策部)"]
            PH2["卡片: 待设计方案 (1) | 待安保设计 (2)"]
            PH4["按钮: + 新建立项"]
            PH5["最近活动列表 (2-3条)"]
        end

        subgraph GovLiaisonHome["GovLiaison 首页"]
            GH2["卡片: 待审查材料 (4) | 今日已登记 (1)"]
            GH4["按钮: 进入审查"]
        end

        subgraph AdminHome["Admin 首页"]
            AH2["卡片: 总活动数 | 审批通过率 | 本月新增"]
            AH3["链接: 进入仪表盘"]
            AH4["待确认强制变更 (0)"]
        end
    end
```

#### P3 改动：任务驱动侧边栏（最终态）

```mermaid
flowchart TB
    subgraph P3Sidebar["P3 侧边栏重构"]
        direction LR

        subgraph PromoterNav["Promoter"]
            PN1["🏠 工作台"]
            PN2["✏️ 新建立项"]
            PN3["📋 我的活动 ③"]
            PN4["📄 全部方案"]
        end

        subgraph SecurityOfficerNav["SecurityOfficer"]
            SN1["🏠 工作台"]
            SN2["📋 待编制安保方案 ②"]
            SN3["✍️ 待我签署 ①"]
            SN4["📦 待打包备案 ②"]
        end

        subgraph SecurityManagerNav["SecurityManager"]
            SMN1["🏠 工作台"]
            SMN2["✍️ 待签署确认 ①"]
            SMN3["📋 安保方案列表"]
            SMN4["📦 备案申请"]
        end

        subgraph GovLiaisonNav["GovLiaison"]
            GN1["🏠 工作台"]
            GN2["🔍 待审查材料 ④"]
            GN3["📤 今日已登记 ①"]
            GN4["📋 全部审批记录"]
        end

        subgraph AdminNav["Admin"]
            AN1["🏠 工作台"]
            AN2["📊 仪表盘"]
            AN3["⚠️ 待确认变更 ①"]
            AN4["📋 全部活动"]
        end
    end
```

#### 关键角色任务流

**Promoter**

```mermaid
flowchart LR
    Login[/登录/] --> Home[首页]
    Home --> |"待设计方案(1)"| NewActivity[新建立项]
    NewActivity --> |保存立项| List[我的活动]
    List --> |点击活动| Detail[活动详情]
    Detail --> |填写方案+上传附件| Submit[提交方案]
    Submit --> |状态→待安保方案设计| Done[完成]
```

**GovLiaison**

```mermaid
flowchart LR
    Login[/登录/] --> Home[首页]
    Home --> |"待审查材料(4)"| Review[审查界面]
    Review --> |逐条审材料| Check{全部合格?}
    Check --> |是| Upload[上传批文 + 标注通过]
    Check --> |否| Remediation[标注不合格<br/>→待补充备案材料]
    Upload --> Done[完成]
```

**Security（Officer + Manager）**

```mermaid
flowchart LR
    Login[/登录/] --> Home[首页]
    Home --> |"待编制"| Draft[安保方案tab]
    Draft --> SubTabs[子tab：安保方案丨风险评估表丨责任确认书]
    SubTabs --> |三表均生成版本| Submit[提交审核]
    Submit --> Sign[SecurityManager<br/>签署三文件]
    Sign --> |三文件已签| Commit[签署备案承诺书]
    Commit --> |承诺书已签| Transition[流转至待备案申请]
    Transition --> Pack[Officer 打包备案]
    Pack --> |线下交接| Handover[确认已交接]
```

**GovLiaison**

```mermaid
flowchart LR
    Login2[/登录/] --> Home2[首页]
    Home2 --> |"待审查"| Review[活动详情-备案tab]
    Review --> Audit[逐条审查5项材料<br/>合格/不合格+意见]
    Audit --> |全部审查完毕| Upload[上传批文（可选）]
    Upload --> Decision{审批决定}
    Decision --> |通过| Approved[审批通过<br/>→生成ApprovalRecord]
    Decision --> |补件| Revise[待补充备案材料<br/>→生成ApprovalRecord]
    Decision --> |驳回| Rejected[不通过/已终止<br/>→生成ApprovalRecord]
```

**TemplateForm 模式**

表单组件统一模式支持双表：
- `onValidate` prop：生成前自定义校验（`validateRiskAssessment`/`validateResponsibilityLetter`）
- `ui_type: "autofill"`：只读灰底 Input（Activity/ActivityPlan 自动填入）
- `ui_type: "declarations"`：只读法律声明块（责任确认书 8 条）
- `ui_type: "signature"`：上传+预览+删除，刷新后通过 `/documents/presign/by-path` 恢复预览
- `hint` 字段：repeater 旁 `QuestionCircleOutlined` + Tooltip
- 条件字段：`==`/`!=` 格式解析，`risk_level` 通过外部传入值判断（非表单字段）
- **草稿自动保存**：表单值变更后 2s 防抖自动保存草稿，确保跨子 tab autofill 能读取最新数据
- **跨模板同步**：安保方案 `security_staff_count` 变更后生成新版本时，弹窗确认后自动同步更新风险评估表和备案承诺书（后端同一事务创建新版本）
- **驳回字段差异校验**：被驳回后重新提交时，比较当前版本与被驳回版本的 highlighted 字段，未修改的阻止提交并提示"与被驳回版本一致"
- **驳回原因按风险等级过滤**：低风险隐藏医疗/消防/人流管控，中低风险隐藏医疗/人流管控，高风险显示全部 7 项
- **备案承诺书签署区**：下方 tab 展示安保方案/风险评估表/责任确认书 VersionSnapshot
- **承诺书地点**：`location` 取风险评估表 `activity_location`（具体地址），回退 `Activity.location`
- **补件回路**：待补充备案材料复用待安保方案设计逻辑，编辑→提交→签署→打包→交接。横幅显示不合格材料及原因，子 tab 和进度 tag 高亮不合格项
- **批量审查**：GovLiaison 审查表支持多选，批量合格/不合格；批量不合格需填写统一原因
- **Manager 重签复用签名**：补件阶段签署时自动从已有 FilledDocument 读取签名，无需重新上传

### 无多角色用户

生产环境不存在一人多角色场景，因此：
- 无需角色切换器（只 `devtest` 账号测试用）
- HomePage 按单一角色渲染，不需模块叠加
- 多角色逻辑仅为开发调试保留

## 状态管理分工

| 数据                    | 方案                 | 原因                               |
| ----------------------- | -------------------- | ---------------------------------- |
| 活动列表/详情/历史/文档 | TanStack Query       | 服务端数据，缓存/失效/后台刷新     |
| 仪表盘、备案校验        | TanStack Query       | 同上                               |
| 用户/token/权限         | Zustand `authStore`  | 客户端会话，axios 拦截器需同步读取 |
| 筛选条件                | URL `searchParams`   | 可分享链接，刷新不丢失             |
| 表单输入                | Ant Design Form 内部 | 提交时才同步到服务端               |

## 权限模型

前端通过 `/auth/me` 响应中的 `permissions: string[]` 和 `roles: string[]` 实现条件渲染：

- **ProtectedRoute**: 路由级守卫，`requiredPermissions` 中满足一个即可
- **Sidebar**: 菜单项按权限显隐
- **WorkflowActions**: 按钮按 `status + permissions` 矩阵显隐
- **页面内按钮**: 新建活动、备案操作等按权限显隐

7 个角色 21+ 个权限的完整映射见 [API 路由设计](./api-routes.md)。

## 状态转换矩阵

工作流按钮由 `getAvailableTransitions(status, permissions)` 函数计算：

| 当前状态       | 可用操作                              | 权限                                  |
| -------------- | ------------------------------------- | ------------------------------------- |
| 待设计方案     | 提交→待安保方案设计                   | `submit_plan`                         |
| 待安保方案设计 | 驳回（内部循环）、签署完成→待备案申请 | `reject_approval`, `manage_security`  |
| 待备案申请     | 打包 + 纸质交接（备案 tab 中操作）    | `pack_filing`                         |
| 待补充备案材料 | 重新打包 + 重新交接 → 备案材料已交接  | `pack_filing`                         |
| 备案材料已交接 | 逐条审查材料 + 通过/补件/驳回         | `audit_material`                      |
| 审批通过       | 确认审批结果、驳回至安保方案设计（页顶横幅） | `confirm_approval`, `reject_approval` |
| 审批通过-待举办 | —（系统自动流转至举办中）             | —                                     |
| 任意非终态     | 强制取消、强制延期                    | `force_cancel`, `force_postpone`      |

终态（举办中/已结束/不通过已终止/已取消/已延期）不显示操作按钮。

## 错误处理

后端统一错误格式 `{ detail, code, fields? }`：

- **表单级**：409 场地冲突 → 行内提示 `fields.location`
- **全局**：API 错误 → `message.error(detail)`
- **并发冲突**：409 on status transition → "已被他人修改，请刷新后重试"
- **429 登录锁定**：显示中文本地化文案

## 关键后端依赖

前端开发前，后端需满足：

- [x] `GET /auth/me` 返回 `permissions` 和 `roles` 字段（commit `047c931`）
- [x] 所有 API 端点返回统一 `{ detail, code, fields? }` 格式
- [ ] Docker 服务运行（PostgreSQL + MinIO + Redis）
- [ ] FastAPI 监听 8000 端口

## 测试种子数据

`scripts/seed_test_activities.py` 创建 48 个预设活动，覆盖全部 12 种状态，配合 `bash scripts/db-reset.sh` 使用。

### 活动主题

全部以**五大道景区**为背景：民园广场、先农大院、庆王府等具体场所。涵盖文艺汇演、体育赛事、商贸活动、民俗活动等类型。

### 多样化场景

| 维度 | 场景数 | 差异 |
|------|--------|------|
| 活动方案 | 3 种循环 | 大型(A: 开幕式+演员+3000-5000人) / 中型(B: 开幕式+无演员+1000-3000人) / 小型(C: 无开幕式+无演员+1000以下) |
| 安保方案 | 3 种循环 | 高风险(50人+医疗+消防+人流管控) / 中低风险(25人+消防) / 低风险(10人) |

两个维度独立组合，共 9 种交叉场景。

### 材料数据

| 状态 | FilledDocument | KeyMaterial | 签名 |
|------|---------------|-------------|------|
| 待安保方案设计 | 活动方案 v1 (generated) | activity_plan | — |
| 待备案申请 | 全部 5 种 (deferred, minio_path=NULL) | 全部 5 种，sign_status=unsigned | — |
| 备案材料已交接 | 全部 5 种 (generated, 含签名) | 全部 5 种，sign_status=signed | 签名1-3.jpg (MinIO) |
| 审批通过+ | 同上 + ApprovalRecord | 同上 | 同上 |

### 上传资源

- `docs/签名1-3.jpg` → MinIO `seed/signatures/sig1-3.jpg`（Manager 签名图）
- `docs/材料1-3.jpg` → MinIO `seed/materials/mat1-3.jpg`（批文附件）

## 已知问题

- [ ] 浏览器测试覆盖不完整（部分角色操作路径未验证）
- [ ] `@ant-design/charts` 图表库（当前用 Progress 条替代饼图）
- [x] F5 刷新 StrictMode 兼容（已修复，详见 `docs/issues/auth-initializer-strictmode.md`）

## 远期 Dashboard 增强指标

以下指标来自 UI 设计讨论（v0.19 规划），当前 Dashboard 尚未实现：

### 效率维度

| 指标 | 计算方式 | 意义 |
|------|---------|------|
| 审批通过率 | 审批通过+已举办+举办中+已结束 / 经历过"备案材料已交接"的活动 | 政府端通过比例 |
| 平均审批周期 | 从"备案材料已交接"到"审批通过"的平均天数 | 政府审批效率 |
| 补件率 | 进入过"待补充备案材料"的活动 / 经历过"备案材料已交接"的活动 | 材料质量问题频率 |

### 合规维度

| 指标 | 计算方式 | 意义 |
|------|---------|------|
| 材料一次合格率 | 首轮 KeyMaterial 全部合格的活动 / 总审查活动 | 安保部材料准备质量 |
| 平均审查轮次 | KeyMaterial 审查轮次平均值 | 材料需要几轮才能过 |

### 异常维度

| 指标 | 计算方式 | 意义 |
|------|---------|------|
| 异常率 | 已取消+已延期 / 全部活动 | 外部因素干扰程度 |
| 逾期率 | 超过 deadline 仍未到终态的活动 / 全部非终态活动 | 流程阻塞情况 |
