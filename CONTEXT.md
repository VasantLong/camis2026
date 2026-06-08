# CONTEXT

活动合规与审批 MIS 的领域术语表。仅包含领域概念，不涉及实现细节。

## 核心领域对象

### Activity（活动项目）

企业承接的主办方活动请求的完整生命周期记录。从立项到审批结束，由多个部门在不同阶段协作处理。

**状态流转**: `待设计方案` → `待安保方案设计` → `待备案申请` → `备案材料已交接` → `审批通过`（GovLiaison批准，系统自动→审批通过-待举办，UC6已移除）→ `审批通过-待举办` → `举办中`（自动）→ `已结束`（AdminStaff标记）；另有 `待补充备案材料` `不通过/已终止` `已取消` `已延期`（12 状态，详见 `docs/state-machine.md`）

**关联单据**: ActivityPlan, SecurityPlan, FilingDoc, ApprovalRecord, ImplementationRecord

### ActivityPlan（活动方案）

宣策部编制的活动策划文档。通过调取系统内置的**活动方案文档模板**（DocumentTemplate），在线填写结构化表单后生成。包含活动主要内容、时间、人数范围、搭建方案、联系方式等字段。支持"是否有开幕式"/"是否有演员嘉宾"选择器驱动条件字段显隐，共计天数由起止日期自动计算。支持草稿暂存和版本生成，驳回后重新生成产生新版本。最终确定前需通过完整性校验弹窗，不合规字段逐条列出并可点击跳转高亮。**最终确定后活动方案锁定**，Promoter 只能查看只读快照。

### SecurityPlan（安保方案）

安保部根据活动风险等级编制的安保预案。填写前先确定风险等级（高风险/中低风险/低风险），系统根据风险等级条件显隐：高风险需医疗救护+消防+人流管控，中低风险仅消防，低风险无额外字段。包含人员配置与数量、动线、设备清单、应急预案等。应急预案保留可编辑，初始按风险等级提供默认模板文本。

需负责人电子签名。三表（安保方案+风险评估表+责任确认书）在子 tab 中并行填写，提交审核前全字段校验。

签署分两步：(1) Manager 确认签署三个文件，生成含签名的安保方案+双表 DOCX；(2) 备案承诺书签署区出现，Manager 确认后生成承诺书 DOCX，活动流转至「待备案申请」。

文件延迟生成：SecurityOfficer 提交生成时仅保存数据快照，Manager 签署确认后才一次性生成含签名的 DOCX。

审核状态流转：待编制 → 待签署 → 已签署 → 已审核（详见 `docs/state-machine.md`）。Manager 驳回后 `audit_status` 回到"待编制"，`last_reject_reason` 记录驳回原因，SecurityOfficer 表单显示驳回横幅。

### FilingDoc（备案材料包）

每次打包生成一个材料包快照，包含全部 5 项备案材料（活动方案、安保方案、风险评估报备表、安全消防责任确认书、活动备案承诺书）。一个活动可有多轮打包（政府审查后打回修正，安保部重新打包提交）。包含合规证明材料集合（通过 `filing_doc_materials` 关联 KeyMaterial）、打包时间、交接状态。打包时生成 ZIP 压缩包（含备案清单 PDF + 各材料 DOCX 文件），存入 MinIO。

### ApprovalRecord（政府批文）

GovLiaison 审批决策的正式记录，独立数据库表。字段：`approval_status`（通过/补件/驳回）、`attachment_url`（批文扫描件，可选）、`liaison_id`（操作人）、`rectification_opinion`（补件/驳回时的整改意见）、`approval_date`。GovLiaison 在活动详情页备案 tab 审查面板中操作：逐条审查材料合格性 → 全部材料审查完毕后可"审批通过"或"要求补件"（驳回不受限）→ 生成 ApprovalRecord。

### KeyMaterial（备案材料）

备案材料包的统一超类型（supertype），一个活动下每种 `material_type` 唯一。覆盖全部 5 项备案材料：

| material_type | name | 扩展表 |
|---------------|------|--------|
| `activity_plan` | 活动方案 | `activity_plans`（designer_id、submit_time 等） |
| `security_plan` | 安保方案 | `security_plans`（risk_level、audit_status、manager_id 等） |
| `risk_assessment` | 风险评估报备表 | 无（数据全在 FilledDocument snapshot） |
| `responsibility_letter` | 安全消防责任确认书 | 无 |
| `filing_commitment` | 活动备案承诺书 | 无 |

共享属性：`is_qualified`（合规状态）、`sign_status`（签署状态）、`audit_round`（审查轮次）、`opinion`（最新审查意见）、`current_filled_document_id`（当前版本）。ActivityPlan 和 SecurityPlan 通过 `material_id` FK 引用各自 KeyMaterial 行，实现 supertype/subtype 模式。合规状态由 GovLiaison 逐一审查后设定。

### MaterialAudit（材料审核记录，新增）

每次对材料的审核/签署操作产生一条记录。含操作人、时间、动作类型（审核/签署）、结论、意见。is_qualified 和 opinion 在每个 KeyMaterial 上做最新状态的快照冗余。

### DocumentTemplate（文档模板）

系统内置的标准化文档框架。每种模板对应一种业务文件类型（activity_plan / security_plan / risk_assessment / responsibility_letter / filing_commitment），定义表单字段结构和 DOCX 渲染规则。模板文件存储在代码仓库中，随应用部署，不由普通用户增删。安保方案模板根据风险等级包含条件内容段。

### FilledDocument（生成文件）

用户通过填写模板表单后提交生成的正式文件。每个生成文件是 immutable 的版本记录，包含提交时的表单数据快照（data_snapshot）、渲染产物（DOCX + PDF）和模板 hash（用于审计追溯）。同一活动下同一模板类型的多个版本通过 `version_number` 递增区分。当前活跃版本由所属实体（ActivityPlan / SecurityPlan / KeyMaterial）的 `current_filled_document_id` 指向。驳回修正、政府要求补充材料等场景产生新版本，原版本保留为历史审计记录。

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
| AdminStaff | 行政部 | 监控活动面板、强制变更状态、标记活动结束、归档 |
| AdminManager | 行政部 | 继承 AdminStaff 全部 + 审批角色申请 |
| GovLiaison | 政府对接 | 上传批文、审查关键材料合规性、标注审批结果 |

### 角色行为特征（UI 设计输入）

| 角色 | 行为特征 | 设计影响 |
|------|---------|---------|
| Promoter | 单向流程（立项→提交方案→完成），方案不会被驳回。同时管 2-3 个活动 | 列表无需复杂搜索/分页 |
| SecurityOfficer | 编制安保方案+签署，SecurityManager 驳回罕见 | 主路径优化，驳回为异常路径 |
| SecurityManager | 双表电子签名（风险评估表+安全消防责任确认书）+确认安保方案。驳回用预设选项+简短自由文本 | 签名界面+驳回快捷选项 |
| GovLiaison | 企业内人员，每天集中跑政府窗口后集中登记。全量审查所有材料，不合格则整轮重审。政府批文为纸质扫描上传 | 审查轮次可视化、批量登记 |
| AdminStaff | 强制变更需提交凭证（不可抗力场景），AdminManager 二次确认后生效 | 凭证提交+二次确认流程 |
| Dashboard | 用于"向上汇报"（汇总经验、可视化），非问题处理 | 侧重可视化/汇总，降权异常清单 |
| 多角色用户 | 生产环境不存在多角色用户（devtest 调试角色除外） | 无需多角色切换功能 |

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
- **任务驱动导航**: `docs/adr/0005.md`
- **OO→SO 设计方法论**: `docs/oo-so.md`
