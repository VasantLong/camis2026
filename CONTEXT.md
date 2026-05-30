# CONTEXT

活动合规与审批 MIS 的领域术语表。仅包含领域概念，不涉及实现细节。

## 核心领域对象

### Activity（活动项目）

企业承接的主办方活动请求的完整生命周期记录。从立项到审批结束，由多个部门在不同阶段协作处理。

**状态流转**: `待设计方案` → `待安保方案设计` → `待备案申请` → `备案材料已交接` → `审批通过` → `审批通过-待举办` → `举办中` → `已结束`；另有 `待补充备案材料` `不通过/已终止` `已取消` `已延期`（12 状态，详见 `docs/state-machine.md`）

**关联单据**: ActivityPlan, SecurityPlan, FilingDoc, ApprovalRecord, ImplementationRecord

### ActivityPlan（活动方案）

宣策部编制的活动策划文档。包含活动内容描述和图文附件（PDF/JPG/PNG，≤50MB）。

### SecurityPlan（安保方案）

安保部根据活动风险等级编制的安保预案。包含人员配置、动线、风险评估表、安全责任确认书。需负责人电子签名。

### FilingDoc（备案材料包）

每次打包生成一个材料包快照。一个活动可有多轮打包（政府审查后打回修正，安保部重新打包提交）。包含合规证明材料集合、打包时间、交接状态。

### ApprovalRecord（政府批文）

政府相关部门（公安/交管等）出具的正式批文。由对接人员扫描上传，标注通过/驳回/需补充材料。

### KeyMaterial（关键材料）

各类关键文件（风险评估表、责任确认书、备案承诺书等）。每条材料有合规状态（待审核/合格/不合格）和最新审查意见。状态由 GovLiaison 逐一审查后设定。

### MaterialAudit（材料审核记录，新增）

每次对材料的审核/签署操作产生一条记录。含操作人、时间、动作类型（审核/签署）、结论、意见。is_qualified 和 opinion 在每个 KeyMaterial 上做最新状态的快照冗余。

### ImplementationRecord（活动实施记录）

行政部维护的活动落地台账。含实施进度、异常变更（不可抗力取消/延期）、归档记录。

### User（用户）

系统的操作主体。以 UUID 为不可变唯一标识。`email` 为登录凭据（唯一），`display_name` 为 UI 展示名称（必填），`contact_phone` 为联系方式（可选，用于活动表单快速导入）。JWT 携带 `sub`（用户 UUID）和 `email`（用于邮箱变更后即时拦截）。支持 `is_active` 禁用和 `is_archived` 归档（替代硬删除，保留关联数据）。登录尝试以 `login_id` 为标识记录，支持后续二维码等非邮箱登录方式。

## 角色（Role）

使用 RBAC 模型：一个 **User** 拥有多个 **Role**，Role 关联 Permission。

| 角色 | 所属部门 | 核心职责 |
|------|----------|----------|
| SuperAdmin | 系统 | 管理用户、审批角色申请 |
| Promoter | 宣策部 | 创建立项、编制活动方案、提交安保审核 (submit_plan) |
| SecurityOfficer | 安保部 | 编制安保方案、上传安保材料、审核备案材料 |
| SecurityManager | 安保部 | 继承 SecurityOfficer 全部 + 驳回（内部循环/逆向流转）、确认政府审批结果 |
| AdminStaff | 行政部 | 监控活动面板、强制变更状态、归档 |
| AdminManager | 行政部 | 继承 AdminStaff 全部 + 审批角色申请 |
| GovLiaison | 政府对接 | 上传批文、审查关键材料合规性、标注审批结果 |

## 架构决策

- **模块化单体**: 所有服务运行在同一 FastAPI 进程内，同步调用，ACID 事务。详见 `docs/design-process.md`
- **服务导向架构**: 业务逻辑归属服务层，实体是纯数据载体。ADR: `docs/adr/0001.md`
- **RBAC 用户模型**: User + Role + Permission 替代类继承。ADR: `docs/adr/0002.md`
- **活动状态机**: `docs/state-machine.md`
- **服务内部设计**: `docs/service-design.md`
- **API 路由设计**: `docs/api-routes.md`
- **UML 用例/顺序图/类图**: `docs/camis-UML.md`
- **前端技术选型**: `docs/adr/0003.md`
- **AI 嵌入方向**: `docs/adr/0004.md`
- **OO→SO 设计方法论**: `docs/oo-so.md`
