from pydantic import BaseModel, Field


class RiskAssessmentForm(BaseModel):
    """风险评估报备表表单数据"""

    reporting_unit: str = Field(default="", description="填报单位")
    report_date: str = Field(default="", description="填报日期")
    project_name: str = Field(default="", description="项目名称")
    activity_type: str = Field(default="", description="活动类型")
    activity_name: str = Field(default="", description="活动名称")
    sponsor: str = Field(default="", description="主办方")
    organizer: str = Field(default="", description="承办方")
    participants: str = Field(default="", description="活动参与方")
    activity_start: str = Field(default="", description="活动开始时间")
    activity_end: str = Field(default="", description="活动结束时间")
    activity_location: str = Field(default="", description="活动地点")
    is_indoor: str = Field(default="", description="室内/户外")
    location_type: str = Field(default="", description="场所类型")
    activity_content: str = Field(default="", description="活动内容")
    crowd_scale: int = Field(default=0, description="活动规模人数")
    staff_count: int = Field(default=0, description="工作人员数量")
    security_count: int = Field(default=0, description="安保人员数量")
    has_tickets: str = Field(default="", description="是否销售门票")
    has_media: str = Field(default="", description="媒体直播情况")
    media_name: str = Field(default="", description="媒体名称")
    media_type: str = Field(default="", description="媒体类型")
    risk_factors: list[str] = Field(default_factory=list, description="主要风险因素", min_length=4)
    mitigation_measures: list[str] = Field(default_factory=list, description="防范化解措施", min_length=4)
    contact_person: str = Field(default="", description="联系人")
    contact_phone: str = Field(default="", description="联系电话")
    assessor_signature: str = Field(default="", description="评估主体负责人签名")


SCHEMA = {
    "display_name": "风险评估报备表",
    "fields": [
        {"name": "reporting_unit", "ui_label": "填报单位（盖章）", "ui_type": "text", "required": True},
        {"name": "report_date", "ui_label": "填报日期", "ui_type": "date", "required": True},
        {"name": "project_name", "ui_label": "项目名称", "ui_type": "text", "required": True},
        {"name": "activity_type", "ui_label": "活动类型", "ui_type": "select",
         "options": ["文艺汇演", "民俗活动", "体育赛事"]},
        {"name": "activity_name", "ui_label": "活动名称", "ui_type": "text", "required": True},
        {"name": "sponsor", "ui_label": "主办方", "ui_type": "text", "required": True},
        {"name": "organizer", "ui_label": "承办方", "ui_type": "text"},
        {"name": "participants", "ui_label": "活动参与方", "ui_type": "text"},
        {"name": "activity_start", "ui_label": "开始时间", "ui_type": "date", "required": True},
        {"name": "activity_end", "ui_label": "结束时间", "ui_type": "date", "required": True},
        {"name": "activity_location", "ui_label": "活动地点", "ui_type": "text", "required": True},
        {"name": "is_indoor", "ui_label": "室内/户外", "ui_type": "select",
         "options": ["室内", "户外"]},
        {"name": "location_type", "ui_label": "场所类型", "ui_type": "select",
         "options": ["中心广场", "商业区域", "娱乐场所", "寺观教堂", "旅游景区", "其他"]},
        {"name": "activity_content", "ui_label": "活动内容", "ui_type": "textarea", "required": True},
        {"name": "crowd_scale", "ui_label": "活动规模（人数）", "ui_type": "number", "min": 0},
        {"name": "staff_count", "ui_label": "工作人员数量", "ui_type": "number", "min": 0},
        {"name": "security_count", "ui_label": "安保人员数量", "ui_type": "number", "min": 0},
        {"name": "has_tickets", "ui_label": "是否销售门票", "ui_type": "select", "options": ["是", "否"]},
        {"name": "has_media", "ui_label": "媒体直播", "ui_type": "select",
         "options": ["无", "直播", "录音录像", "其他"]},
        {"name": "media_name", "ui_label": "媒体名称", "ui_type": "text",
         "condition": "has_media != '无'"},
        {"name": "media_type", "ui_label": "媒体类型", "ui_type": "select",
         "options": ["官方", "网络", "自媒体"], "condition": "has_media != '无'"},
        {"name": "risk_factors", "ui_label": "主要风险因素", "ui_type": "repeater",
         "min_items": 4, "required": True},
        {"name": "mitigation_measures", "ui_label": "防范化解措施", "ui_type": "repeater",
         "min_items": 4, "required": True},
        {"name": "contact_person", "ui_label": "联系人", "ui_type": "text", "required": True},
        {"name": "contact_phone", "ui_label": "联系电话", "ui_type": "text", "required": True},
        {"name": "assessor_signature", "ui_label": "评估主体负责人签字", "ui_type": "signature", "required": True},
    ],
}
