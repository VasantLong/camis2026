# 五大道景区活动与审批MIS（CAMIS） — 系统分析与设计

> 基于面向服务架构（SOA）的 Web 应用。本章进行系统分析（参与者识别、用例建模、领域类图、状态图），后续章节完成系统设计与实现描述。

## 第 2 章 系统分析

### 2.1 需求分析

#### 2.1.1 参与者识别

系统涉及七类参与者，按职责划分为三个层级：

| 层级 | 角色 | 职责 |
|------|------|------|
| 主办方 | Promoter（宣策部人员） | 立项、编制活动方案 |
| 安保方 | SecurityOfficer（安保部编制人员） | 编制安保方案与备案材料 |
| 安保方 | SecurityManager（安保部负责人） | 签署安保材料、审核方案 |
| 政府方 | GovLiaison（政府对接人员） | 审查备案材料、上传批文、做出审批决策 |
| 行政方 | AdminStaff（行政部人员） | 监控活动进展、标记活动结束、强制变更 |
| 管理方 | AdminManager（行政部负责人） | 管理用户与角色分配 |
| 系统方 | SuperAdmin（超级管理员） | 全局管理 |

各参与者的权限映射详见 `docs/rbac.md`。系统通过 14 项细粒度权限控制各角色对 23 个 API 端点的访问。

#### 2.1.2 用例图

系统包含 6 个核心用例（原 UC6 登记审批结果已移除，审批通过后系统自动流转）。

> **此处插入 StarUML 绘制的用例图（见图 2-1）。**

```mermaid
graph TD
    Promoter[Promoter<br>宣策部人员] --> UC1[UC1 立项]
    Promoter --> UC2[UC2 编制活动方案]

    SecurityOfficer[SecurityOfficer<br>安保部编制人员] --> UC3[UC3 编制安保方案<br>含签署]
    SecurityOfficer --> UC4[UC4 备案打包与交接]

    GovLiaison[GovLiaison<br>政府对接人员] --> UC5[UC5 审批安保方案<br>审查材料+批文+决策]

    AdminStaff[AdminStaff<br>行政部人员] --> UC6[UC6 活动实施监控<br>面板+标记结束+强制变更]

    UC2 -.-> |方案最终确定后| UC3
    UC3 -.-> |签署完成后| UC4
    UC4 -.-> |交接完成后| UC5
    UC5 -.-> |审批通过<br>系统自动流转| UC6
```

| 用例 | 参与者 | 前置条件 | 后置条件 |
|------|--------|----------|----------|
| UC1 立项 | Promoter | 无 | 生成活动记录，状态为"待设计方案" |
| UC2 编制活动方案 | Promoter | 活动状态为"待设计方案" | 方案最终确定，状态变更为"待安保方案设计" |
| UC3 编制安保方案 | SecurityOfficer, SecurityManager | 方案已确定 | 签署完成，状态变更为"待备案申请" |
| UC4 备案打包与交接 | SecurityOfficer | 全部材料已签署 | ZIP 包生成，线下交接，状态变更为"备案材料已交接" |
| UC5 审批安保方案 | GovLiaison | 备案材料已交接 | 审批通过后系统自动流转至"审批通过-待举办"；补件则进入"待补充备案材料"回路 |
| UC6 活动实施监控 | AdminStaff | 活动进入举办阶段 | 活动正常结束，或被强制取消/延期 |

> UC5 的备选流程包括"要求补充材料"（进入补件回路）和"驳回"（进入不通过/已终止）。原 UC6（登记审批结果）已移除：GovLiaison 审批通过后系统自动流转至"审批通过-待举办"，不再需要 Manager 手动确认。详见 `docs/camis-UML.md` UC5 用例规约。

### 2.2 领域类图

系统采用面向服务架构（SOA）[ADR 0001]，实体为纯数据载体，不包含业务方法。Activity 作为聚合根，通过组合关系关联子实体。

**核心实体说明**：

- **Activity**（活动）：聚合根。记录活动基本信息（名称、类型、时间、地点、主办方）和当前状态
- **ActivityPlan**（活动方案）：Promoter 编制，含表单数据与版本管理
- **SecurityPlan**（安保方案）：SecurityOfficer 编制，按风险等级（高/中低/低）条件显隐字段，含驳回追溯
- **FilingDoc**（备案文档包）：打包 5 项材料形成的 ZIP 归档，记录合格状态与交接状态
- **KeyMaterial**（关键备案材料）：supertype/subtype 模型，覆盖 5 种类型（活动方案、安保方案、风险评估报备表、安全消防责任确认书、备案承诺书）
- **ApprovalRecord**（审批记录）：GovLiaison 审批决策的独立记录，含批文附件与整改意见
- **ImplementationRecord**（实施记录）：活动进入举办阶段后的跟踪记录
- **MaterialAudit**（材料审核记录）：逐条材料的审核/签署追踪
- **ActivityRule**（活动规则）：场地冲突检测等业务规则

以下为 StarUML 兼容的 Mermaid 领域类图（实体为纯数据载体，无业务方法）：

```mermaid
classDiagram
    class User {
        +UUID id
        +String email
        +String display_name
        +Boolean is_active
        +String contact_phone
    }

    class Role {
        +UUID id
        +String name
        +String description
    }

    class Permission {
        +UUID id
        +String name
        +String resource
        +String action
    }

    class Activity {
        +UUID id
        +String name
        +String type
        +DateTime estimated_time
        +String location
        +String sponsor
        +String sponsor_contact
        +String sponsor_phone
        +DateTime deadline
        +String status
    }

    class ActivityPlan {
        +UUID id
        +DateTime created_at
        +DateTime updated_at
    }

    class SecurityPlan {
        +UUID id
        +String risk_level
        +String audit_status
        +DateTime sign_time
        +String last_reject_reason
        +DateTime rejected_at
        +Integer reject_count
    }

    class FilingDoc {
        +UUID id
        +Boolean is_qualified
        +String handover_status
        +String pack_url
        +DateTime generated_at
    }

    class ApprovalRecord {
        +UUID id
        +String approval_status
        +String attachment_url
        +DateTime approval_date
        +String rectification_opinion
    }

    class ImplementationRecord {
        +UUID id
        +String change_status
        +String change_reason
        +DateTime archived_at
    }

    class KeyMaterial {
        +UUID id
        +String name
        +String material_type
        +Boolean is_qualified
        +String sign_status
        +Integer audit_round
        +String opinion
        +DateTime upload_time
    }

    class MaterialAudit {
        +UUID id
        +String action
        +String conclusion
        +String opinion
        +DateTime created_at
    }

    class ActivityRule {
        +UUID id
        +String rule_type
        +DateTime effective_time
        +String effective_reason
        +String resolve_status
    }

    class UserRole {
        +UUID user_id
        +UUID role_id
    }

    class RolePermission {
        +UUID role_id
        +UUID permission_id
    }

    User "1" -- "*" UserRole
    Role "1" -- "*" UserRole
    Role "1" -- "*" RolePermission
    Permission "1" -- "*" RolePermission

    User "1" -- "*" Activity : owner
    User "1" -- "*" ActivityPlan : designer
    User "1" -- "*" SecurityPlan : manager
    User "1" -- "*" ApprovalRecord : liaison
    User "1" -- "*" ImplementationRecord : admin

    Activity "1" *-- "1..*" ActivityPlan : 包含
    Activity "1" *-- "1..*" SecurityPlan : 包含
    Activity "1" *-- "*" FilingDoc : 多轮打包
    Activity "1" *-- "1..*" ApprovalRecord : 包含
    Activity "1" *-- "1" ImplementationRecord : 包含
    Activity "1..*" -- "1..*" ActivityRule : 受约束

    SecurityPlan "1" o-- "1..*" KeyMaterial : 包含
    FilingDoc "1" o-- "1..*" KeyMaterial : 包含
    KeyMaterial "1" *-- "*" MaterialAudit : 审核/签署记录
```

### 2.3 状态图

活动生命周期包含 **11 个状态**，状态变迁由 UC1-UC6 驱动。审批通过状态（v0.29 前为独立中间态）已移除，GovLiaison 审批通过后活动直接进入"审批通过-待举办"。

```mermaid
stateDiagram-v2
    state "审批通过-待举办" as approved
    state "不通过/已终止" as rejected

    [*] --> 待设计方案 : UC1 立项

    待设计方案 --> 待安保方案设计 : UC2 最终确定方案
    待设计方案 --> 已取消 : UC6 强制变更
    待设计方案 --> 已延期 : UC6 强制变更

    待安保方案设计 --> 待安保方案设计 : UC3 负责人驳回
    待安保方案设计 --> 待备案申请 : UC3 签署完成
    待安保方案设计 --> 已取消 : UC6 强制变更
    待安保方案设计 --> 已延期 : UC6 强制变更

    待备案申请 --> 备案材料已交接 : UC4 打包+交接
    待备案申请 --> 已取消 : UC6 强制变更
    待备案申请 --> 已延期 : UC6 强制变更

    备案材料已交接 --> approved : UC5 政府通过
    备案材料已交接 --> 待补充备案材料 : UC5 需补充材料
    备案材料已交接 --> rejected : UC5 政府驳回
    备案材料已交接 --> 已取消 : UC6 强制变更
    备案材料已交接 --> 已延期 : UC6 强制变更

    待补充备案材料 --> 备案材料已交接 : 补充后重新递交
    待补充备案材料 --> 已取消 : UC6 强制变更
    待补充备案材料 --> 已延期 : UC6 强制变更

    approved --> 举办中 : 到达预计举办时间
    approved --> 已取消 : UC6 强制变更
    approved --> 已延期 : UC6 强制变更

    举办中 --> 已结束 : UC6 标记结束
    举办中 --> 已取消 : UC6 强制变更
    举办中 --> 已延期 : UC6 强制变更

    已结束 --> [*]
    rejected --> [*]
    已取消 --> [*]
    已延期 --> [*]
```

**终态**：`已结束`、`不通过/已终止`、`已取消`、`已延期` — 进入后锁定所有后续操作。

**子状态机** — `SecurityPlan.audit_status`：

```mermaid
stateDiagram-v2
    [*] --> 待编制
    待编制 --> 待审核 : 提交审核
    待审核 --> 待签署 : 审核通过
    待审核 --> 待编制 : 驳回
    待签署 --> 已签署 : Manager 签署
    已签署 --> 已审核 : 政府审批通过
```

完整状态说明及通知规则详见 `docs/state-machine.md`。

---

> **第 3 章（系统设计）与第 4 章（系统实现）将在后续补充。**
