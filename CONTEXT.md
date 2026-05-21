# CONTEXT

活动合规与审批 MIS 的领域术语表。仅包含领域概念，不涉及实现细节。

## 核心领域对象

### Activity（活动项目）

企业承接的主办方活动请求的完整生命周期记录。从立项到审批结束，由多个部门在不同阶段协作处理。

**状态流转**: `待设计方案` → `待安保方案设计` → `待备案申请` → `审批通过-待举办` | `不通过/已终止` | `已取消` | `已延期`

**关联单据**: ActivityPlan, SecurityPlan, FilingDoc, ApprovalRecord, ImplementationRecord

### ActivityPlan（活动方案）

宣策部编制的活动策划文档。包含活动内容描述和图文附件（PDF/JPG/PNG，≤50MB）。

### SecurityPlan（安保方案）

安保部根据活动风险等级编制的安保预案。包含人员配置、动线、风险评估表、安全责任确认书。需负责人电子签名。

### FilingDoc（备案材料）

合规证明材料集合。《备案承诺书》+ 已签署的风险评估表 + 安全责任书。打包后线下打印交接给政府对接人员。

### ApprovalRecord（政府批文）

政府相关部门（公安/交管等）出具的正式批文。由对接人员扫描上传，标注通过/驳回/需补充材料。

### ImplementationRecord（活动实施记录）

行政部维护的活动落地台账。含实施进度、异常变更（不可抗力取消/延期）、归档记录。

### KeyMaterial（关键材料）

各类关键文件（风险评估表、责任确认书、备案承诺书等）。含电子签名和合规性校验。

## 角色（Role）

使用 RBAC 模型：一个 **User** 拥有多个 **Role**，Role 关联 Permission。

| 角色 | 所属部门 | 核心职责 |
|------|----------|----------|
| Promoter | 宣策部 | 创建立项、编制活动方案 |
| SecurityOfficer | 安保部 | 编制安保方案、审核材料、确认审批结果 |
| AdminStaff | 行政部 | 监控活动面板、强制变更状态、归档 |
| GovLiaison | 政府对接 | 上传批文、标注审批结果、反馈整改意见 |

## 架构决策

- **模块化单体**: 所有服务运行在同一 FastAPI 进程内，同步调用，ACID 事务。详见 `docs/design-process.md`
- **服务导向架构**: 业务逻辑归属服务层，实体是纯数据载体。ADR: `docs/adr/0001.md`
- **RBAC 用户模型**: User + Role + Permission 替代类继承。ADR: `docs/adr/0002.md`
- **活动状态机**: `docs/state-machine.md`
- **服务内部设计**: `docs/service-design.md`
- **API 路由设计**: `docs/api-routes.md`
- **UML 用例/顺序图/类图**: `docs/camis-UML.md`
- **OO→SO 设计方法论**: `docs/oo-so.md`
