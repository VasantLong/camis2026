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
│   ├── filings.ts          # validate, pack, handover
│   └── dashboard.ts        # panel, activityDetail, monthlyReport
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
│   └── dashboard.ts        # PanelData, AnomalyEntry, ActivityDetail, MonthlyReportRequest
├── pages/
│   ├── LoginPage.tsx
│   ├── RegisterPage.tsx
│   ├── NotFoundPage.tsx
│   ├── ForbiddenPage.tsx
│   ├── activities/
│   │   ├── ActivityListPage.tsx    # 筛选 + 分页列表
│   │   ├── ActivityCreatePage.tsx  # 新建表单
│   │   └── ActivityDetailPage.tsx  # 详情/历史/文档/备案
│   └── dashboard/
│       └── DashboardPage.tsx       # 统计卡片 + 状态分布 + 异常列表 + 月报
├── components/
│   ├── auth/
│   │   ├── AuthInitializer.tsx     # App 启动时静默 refresh
│   │   └── ProtectedRoute.tsx      # 路由守卫（认证 + 权限）
│   ├── layout/
│   │   ├── AppLayout.tsx           # Sider + Header + Content
│   │   └── Sidebar.tsx             # 权限感知菜单
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
│   │   └── HandoverConfirm.tsx     # 交接确认（不可逆）
│   └── dashboard/
│       ├── StatusDistribution.tsx  # 状态分布 Progress 条
│       ├── AnomalyList.tsx         # 异常活动表格
│       └── ReportExport.tsx        # 月报导出
├── utils/
│   └── constants.ts          # 状态常量, 颜色映射, 状态转换矩阵
└── styles/
    └── global.css
```

## 路由

| 路径              | 页面                     | 权限                  | 布局      |
| ----------------- | ------------------------ | --------------------- | --------- |
| `/login`          | LoginPage                | 公开                  | 无        |
| `/register`       | RegisterPage             | 公开                  | 无        |
| `/403`            | ForbiddenPage            | 公开                  | 无        |
| `/`               | → redirect `/activities` | —                     | AppLayout |
| `/activities`     | ActivityListPage         | `view_owned_activity` | AppLayout |
| `/activities/new` | ActivityCreatePage       | `create_activity`     | AppLayout |
| `/activities/:id` | ActivityDetailPage       | `view_owned_activity` | AppLayout |
| `/dashboard`      | DashboardPage            | `view_dashboard`      | AppLayout |
| `*`               | NotFoundPage             | 公开                  | 无        |

## 认证流程

```
登录 POST /api/auth/login
  → access_token 存 Zustand authStore
  → refresh_token 由浏览器自动管理 (httpOnly cookie, path=/auth, 7 天)

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

4 个角色 16 个权限的完整映射见 [API 路由设计](./api-routes.md)。

## 状态转换矩阵

工作流按钮由 `getAvailableTransitions(status, permissions)` 函数计算：

| 当前状态       | 可用操作                              | 权限                                  |
| -------------- | ------------------------------------- | ------------------------------------- |
| 待设计方案     | 提交→待安保方案设计                   | `manage_security`                     |
| 待安保方案设计 | 驳回（内部循环）、签署完成→待备案申请 | `reject_approval`, `manage_security`  |
| 待备案申请     | （备案 tab 中操作）                   | `pack_filing`                         |
| 备案材料已交接 | 通过/补件/驳回                        | `manage_security`                     |
| 待补充备案材料 | 重新递交                              | `manage_security`                     |
| 审批通过       | 确认通过、驳回（逆向流转）            | `confirm_approval`, `reject_approval` |
| 任意非终态     | 强制取消、强制延期                    | `force_cancel`, `force_postpone`      |

终态（审批通过-待举办/不通过/已终止/已取消/已延期）不显示操作按钮。

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

## 待补充

- [ ] E2E 测试（Playwright/Cypress）
- [ ] 消息中心页面（Notification 列表，后端需新增 `GET /notifications` 端点）
- [ ] 用户选择器组件（创活动时选 designer，目前 designer_id 未在表单中暴露）
- [ ] `@ant-design/charts` 图表库（当前用 Progress 条替代饼图）
