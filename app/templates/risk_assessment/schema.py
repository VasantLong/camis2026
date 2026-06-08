from pydantic import BaseModel, Field


class RiskAssessmentForm(BaseModel):
    """风险评估报备表表单数据"""

    reporting_unit: str = Field(default="", description="填报单位")
    report_date: str = Field(default="", description="填报日期")
    project_name: str = Field(default="", description="项目名称")
    activity_type: str = Field(default="", description="活动类型")
    sponsor: str = Field(default="", description="主办方")
    organizer: str = Field(default="", description="承办方")
    participants: str = Field(default="", description="活动参与方")
    activity_start: str = Field(default="", description="活动开始时间")
    activity_end: str = Field(default="", description="活动结束时间")
    activity_location: str = Field(default="", description="活动地点")
    is_indoor: str = Field(default="", description="室内/户外")
    location_type: str = Field(default="", description="场所类型")
    activity_content: str = Field(default="", description="活动内容")
    crowd_scale: str = Field(default="", description="预计参与人数规模")
    staff_count: int = Field(default=0, description="工作人员数量")
    security_count: int = Field(default=0, description="安保人员数量")
    has_tickets: str = Field(default="", description="是否销售门票")
    has_media: str = Field(default="", description="是否有媒体直播或采录")
    media_channel: str = Field(default="", description="媒体采录方式")
    media_name: str = Field(default="", description="媒体名称")
    media_type: str = Field(default="", description="媒体类型")
    risk_factors: list[str] = Field(default_factory=list, description="主要风险因素", min_length=4)
    mitigation_measures: list[str] = Field(default_factory=list, description="防范化解措施", min_length=4)
    contact_person: str = Field(default="", description="联系人")
    contact_phone: str = Field(default="", description="联系电话")
    assessor_signature: str = Field(default="", description="评估主体负责人签名")
    manager_signature: str = Field(default="", description="安保负责人审核签名")


SCHEMA = {
    "display_name": "风险评估报备表",
    "fields": [
        {"name": "reporting_unit", "ui_label": "填报单位（盖章）", "ui_type": "text", "required": True},
        {"name": "report_date", "ui_label": "填报日期", "ui_type": "date", "required": True},
        {"name": "project_name", "ui_label": "项目名称", "ui_type": "autofill", "autofill_from": "activity.name", "required": True},
        {"name": "activity_type", "ui_label": "活动类型", "ui_type": "autofill", "autofill_from": "activity.type"},
        {"name": "sponsor", "ui_label": "主办方", "ui_type": "autofill", "autofill_from": "activity.sponsor", "required": True},
        {"name": "organizer", "ui_label": "承办方", "ui_type": "text"},
        {"name": "participants", "ui_label": "活动参与方", "ui_type": "text"},
        {"name": "activity_start", "ui_label": "开始时间", "ui_type": "autofill", "autofill_from": "plan.start_time", "required": True},
        {"name": "activity_end", "ui_label": "结束时间", "ui_type": "autofill", "autofill_from": "plan.end_time", "required": True},
        {"name": "activity_location", "ui_label": "活动地点（具体地址）", "ui_type": "text", "required": True},
        {"name": "is_indoor", "ui_label": "室内/户外", "ui_type": "select",
         "options": ["室内", "户外"]},
        {"name": "location_type", "ui_label": "场所类型", "ui_type": "autofill", "autofill_from": "activity.location"},
        {"name": "activity_content", "ui_label": "活动内容", "ui_type": "autofill", "autofill_from": "plan.activity_content", "required": True},
        {"name": "crowd_scale", "ui_label": "预计参与人数规模", "ui_type": "select",
         "options": ["1000以下", "1000-3000", "3000-5000", "5000-10000", "10000以上"]},
        {"name": "staff_count", "ui_label": "工作人员数量", "ui_type": "autofill", "autofill_from": "plan.staff_count", "min": 0},
        {"name": "security_count", "ui_label": "安保人员数量", "ui_type": "number", "min": 0},
        {"name": "has_tickets", "ui_label": "是否销售门票", "ui_type": "select", "options": ["是", "否"]},
        {"name": "has_media", "ui_label": "是否有媒体直播或采录", "ui_type": "select", "options": ["是", "否"]},
        {"name": "media_channel", "ui_label": "媒体采录方式", "ui_type": "select",
         "options": ["直播", "录音录像", "其他"], "condition": "has_media == '是'"},
        {"name": "media_name", "ui_label": "媒体名称", "ui_type": "text",
         "condition": "has_media == '是'"},
        {"name": "media_type", "ui_label": "媒体类型", "ui_type": "select",
         "options": ["官方", "网络", "自媒体"], "condition": "has_media == '是'"},
        {"name": "risk_factors", "ui_label": "主要风险因素", "ui_type": "repeater",
         "min_items": 4, "required": True,
         "hint": "请从决策合法性、合理性、可行性、可控性四个维度进行分析，每个维度至少列出1条风险因素"},
        {"name": "mitigation_measures", "ui_label": "防范化解措施", "ui_type": "repeater",
         "min_items": 4, "required": True,
         "hint": "针对上述风险因素逐条制定防范化解措施。示例：1. 制定详细安保方案明确各岗位职责；2. 配备专业安保人员负责现场秩序维护；3. 设置安检通道对入场人员进行安全检查"},
        {"name": "contact_person", "ui_label": "联系人", "ui_type": "text", "required": True},
        {"name": "contact_phone", "ui_label": "联系电话", "ui_type": "text", "required": True,
         "validate": {"pattern": r"^1[3-9]\d{9}$", "message": "须为11位手机号码"}},
        {"name": "assessor_signature", "ui_label": "评估主体负责人签字", "ui_type": "signature", "required": True},
        # manager_signature is NOT in fields — injected at Manager signing time
    ],
}
