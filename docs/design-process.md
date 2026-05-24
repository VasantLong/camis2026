# 设计流程：从 OO 到面向服务（模块化单体）

本文档将 `docs/oo-so.md` 中的通用框架应用到本项目的**模块化单体**架构上。

核心定位：服务边界清晰，但所有服务运行在同一进程内，不涉及微服务部署、异步事件总线、Saga 分布式事务。

## 三阶段设计流程

```
输入: OO 设计资产（用例图、类图、顺序图）
  │
  ├─ 第一步：服务识别与边界规划
  │   输入：用例图 + 类图
  │   输出：服务蓝图（服务清单 + 类归属）
  │   状态：⚠ 进行中
  │
  ├─ 第二步：服务契约与交互设计
  │   输入：顺序图 + 状态机
  │   输出：API 路由清单 + 服务间调用关系
  │   与微服务版差异：同步方法调用替代异步事件，状态机描述单体内流转而非 Saga
  │   状态：❌ 未开始
  │
  └─ 第三步：服务内部精细化
      输入：服务蓝图 + API 契约
      输出：每个服务内部的领域模型、数据访问层、单元测试
      在单个服务内部，继续使用类图、顺序图进行 OO 设计
      状态：❌ 未开始
```

## 第一步详情：服务识别与边界规划

### 从用例图识别业务能力

将 UC1-7 按业务能力聚类：

| 业务能力 | 关联用例 | 候选服务 |
|----------|---------|----------|
| 活动项目管理 | UC1 立项 | ActivityService |
| 文档管理 | UC2 上传方案、UC3 上传安保材料、UC4 打包备案、UC5 上传批文 | DocumentService |
| 审批工作流 | UC3 签署确认、UC5 标注审批结果、UC6 确认/驳回 | WorkflowService |
| 通知 | UC1 发待办、UC2 逾期预警、UC3 推送审批、UC5 补件通知 | NotificationService |
| 活动监控面板 | UC7 面板、报表导出 | DashboardService |

**服务识别策略：业务能力聚类**

本项目的服务拆分采用**业务能力聚类**而非 DDD 子领域划分。理由：

| 策略 | 方法 | 适用场景 | 本项目 |
|------|------|---------|--------|
| 业务能力聚类 | 审视用例图，将紧密相关的用例归组，每组对应一个候选服务 | 模块化单体，领域复杂度中等 | ✅ **采用** |
| DDD 子领域划分 | 区分核心域（竞争优势）、支撑域（辅助核心）、通用域（现成方案） | 微服务架构，需决定哪些自研、哪些外包/采购 | 不适合当前规模 |

> 两种策略不互斥。当项目未来拆分为微服务时，可在当前业务能力聚类基础上叠加子领域分析，将通用域（如 DocumentService 的文件存储）抽离为独立基础设施服务。

### 从类图识别聚合边界

现已完成类图更新（`docs/camis-UML.md` §实体模型）。核心聚合：

| 聚合根 | 内部实体 | 理由 |
|--------|---------|------|
| Activity | ActivityPlan, SecurityPlan, FilingDoc, ApprovalRecord, ImplementationRecord | 所有单据生命周期绑定于同一个活动 |
| KeyMaterial | — | 独立生命周期，被安保方案和备案材料引用 |

### 输出：服务蓝图（初稿）

```
ActivityService     → 管理 Activity 聚合（CRUD + 状态查询）
DocumentService     → 文件上传/下载、MinIO 存储、预签名 URL
WorkflowService     → 状态变迁校验、驳回逆向流转
FilingService       → 材料打包、合规校验、电子签名
NotificationService → 系统内消息、邮件通知、逾期预警
DashboardService    → 数据聚合查询、报表导出
```

## 第二步差异说明

微服务版的第二步强调"异步事件 + Saga + 补偿"。本项目不采用。

**替代方案**：
- 服务间交互 → 同步方法调用（在同一个 FastAPI 进程中）
- 状态机 → `docs/state-machine.md` 已描述单活动生命周期
- 跨服务事务 → PostgreSQL 事务（ACID，无需最终一致性）

## 第三步说明

服务内部设计继续使用 OO 方法——类图、顺序图用于建模单个服务内部的领域对象交互。此部分按服务逐一推进，不需要一次性完成。

## 当前进度

| 阶段 | 状态 | 产出 |
|------|------|------|
| 领域建模 | ✅ | CONTEXT.md, state-machine.md, ADR 0001/0002 |
| 用例规约 | ✅ | camis-UML.md UC1-7 |
| 第一步：服务蓝图 | ✅ | 本文档 §服务蓝图（初稿），camis-UML.md §服务层 |
| 第一步：更新类图 | ✅ | camis-UML.md §实体模型（纯数据载体） |
| 第二步：更新顺序图 | ✅ | camis-UML.md §面向服务顺序图（UC1-7） |
| 第二步：API 路由设计 | ✅ | docs/api-routes.md (20 端点) |
| 第三步：数据库设计（DDL） | ✅ | init-scripts/02 + 03 (13 新表, 16 权限种子) |
| 第三步：文档表适配 | ✅ | documents.project_id → activity_id |
| 第三步：服务内部设计 | ✅ | docs/service-design.md (6 服务) |
| 第四步：服务代码实现 | ✅ | 7 服务全部实现 (含 NotificationService) |
| 待补齐：RBAC 权限接入路由 | ✅ | 所有受保护端点已接入 require_permission |
| 待补齐：文档表适配 | ✅ | upload/list 已切换为 activity_id |
| 待补齐：新服务测试 | ✅ | 28 测试全部通过 |
| 待补齐：剩余 ORM 模型 | ✅ | 11 个新模型已补齐 |
| 待补齐：文件格式/大小校验 | ✅ | PDF/JPG/PNG/DOC, ≤50MB |
| 待补齐：PDF 生成 | ✅ | reportlab pack_materials + monthly report |
| 待补齐：交接触发状态变更 | ✅ | confirm_handover → ws.transition |
| 待补齐：强制变更写归档 | ✅ | _force_terminal INSERT implementation_records |
| 待补齐：驳回多角色通知 | ✅ | Reject 通知 AdminStaff + SecurityOfficer |
| 待补齐：并发冲突保护 | ✅ | 原子 UPDATE WHERE status=old_status |
| 部署：.env.example 补全 | ✅ | JWT_SECRET + ALLOW_ORIGINS 已添加 |
| 部署：Dockerfile | ✅ | python:3.12-slim + app service |
| 部署：生产 ASGI (gunicorn) | ✅ | 4 workers, 120s timeout |
| 部署：CORS 收窄 | ✅ | 从 ALLOW_ORIGINS 环境变量读取 |
| 质量：统一错误响应格式 | ✅ | AppError hierarchy + exception handler |
| 质量：请求追踪 middleware | ✅ | RequestIDMiddleware + X-Request-ID |
| 质量：审计日志 | ⏳ | 操作日志、下载日志、越权拦截日志，待功能完成后实施 |
| 安全：JWT refresh token + 登录保护 | ✅ | refresh + logout + login brute force 5→15min |
| 安全：越权访问保护 (IDOR) | ✅ | list/get 按 owner_id 过滤 |
| 安全：默认凭据清理 | ✅ | JWT_SECRET 必填 + field_validator |
| 安全：输入长度限制 | ✅ | comment/reason capped at 2000 chars |
| 安全：文件内容检查 | ✅ | 魔数校验 PDF/JPG/PNG/DOC 文件头 |
| 待补齐：DocumentService 类 | ✅ | app/services/document_service.py |
| 待补齐：电子签名跟踪 | ✅ | has_signature 字段已添加 |
