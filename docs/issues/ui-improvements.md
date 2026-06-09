# UI 改进

分支: `feat/workflow-enhance` → `feat/collapsible-sidebar`

## 已完成 (v0.31.0)

### 1. 侧边栏展开/收起优化 ✅

已实施：默认折叠（72px 图标模式），悬停展开显示完整菜单标签。antd `Sider` 原生 `collapsible` 属性 + `onMouseEnter/Leave`。

### 2. 消息中心——登录注册相关消息 ✅

已实施：
- 新用户注册欢迎消息：`AuthService.register_user()` 调用 `NotificationService.send_reminder()`
- 角色审批通过/驳回通知：`AdminService.approve/reject_role_request()` 发送通知

### 3. 登录后默认进入工作台 ✅

已确认：现有逻辑已正确——`LoginPage` 取 `state.from || "/index"`，`ProtectedRoute` 传递 `state.from`。无需改动。

### 4. 表单样式与排列优化 ✅

已实施：`TemplateForm` 和 `ActivityForm` 均使用 `Row` + `Col` 布局。窄字段（date/number/select）`span={8}` 三列同行，宽字段（textarea）`span={24}` 独占一行。

## 已完成（额外）

### 5. 深浅主题切换 ✅

`useTheme` React Context + antd `ConfigProvider` theme algorithm + localStorage 持久化。Header 灯泡按钮切换太阳/月亮图标。

### 6. 活动标题与 Tab 同行 ✅

自定义 Tab Bar：标题行显示返回按钮+活动名+状态标签+5 个 Tab 切换按钮（flex-wrap），下方 `<Tabs tabBarStyle={{ display: "none" }}>` 仅渲染内容。

### 7. Tab 显隐按状态+角色 ✅

- 基本信息/状态历史：始终可见
- 活动方案：`canViewPlan`
- 安保方案：`canViewSecurity` + status ≠ 待设计方案
- 备案：`showFiling`（FILING_STATUSES）
- 文档：非 GovLiaison 可见
- GovLiaison：仅基本信息+历史+备案

### 8. 其他优化 ✅

- 活动方案锁定提示（所有非待设计方案状态显示"方案已锁定"）
- 已结束活动展示结束时间+操作人+原因
- 状态历史空态统一图标
- 标记结束必填原因
- 活动列表排序（创建时间/最近操作）
- Logo 三处部署（侧边栏/登录页/favicon）
- 侧边栏暖灰色背景 + Menu theme="dark"
- 权限中文化显示
- antd v6 兼容修复（message/Statistic）
- 侧边栏高亮修复（URL 参数解析）
