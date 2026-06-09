from pydantic import BaseModel, Field


class FilingCommitmentForm(BaseModel):
    """活动备案承诺书 — 全部字段 autofill，仅 manager_signature 在签署时注入"""

    project_name: str = Field(default="", description="活动名称")
    sponsor: str = Field(default="", description="主办方")
    estimated_time: str = Field(default="", description="预计举办时间")
    location: str = Field(default="", description="活动地点")
    activity_type: str = Field(default="", description="活动类型")
    crowd_scale: str = Field(default="", description="预计参与人数")
    security_staff_count: str = Field(default="", description="安保人员数量")
    filing_date: str = Field(default="", description="备案日期")
    manager_signature: str = Field(default="", description="安全负责人签字（签署时注入）")


SCHEMA = {
    "display_name": "备案承诺书",
    "fields": [
        {
            "name": "project_name", "ui_label": "活动名称",
            "ui_type": "autofill", "required": True,
        },
        {
            "name": "sponsor", "ui_label": "主办方",
            "ui_type": "autofill", "required": True,
        },
        {
            "name": "estimated_time", "ui_label": "预计举办时间",
            "ui_type": "autofill", "required": True,
        },
        {
            "name": "location", "ui_label": "活动地点",
            "ui_type": "autofill", "required": True,
        },
        {
            "name": "activity_type", "ui_label": "活动类型",
            "ui_type": "autofill",
        },
        {
            "name": "crowd_scale", "ui_label": "预计参与人数",
            "ui_type": "autofill",
        },
        {
            "name": "security_staff_count", "ui_label": "安保人员数量",
            "ui_type": "autofill",
        },
        {
            "name": "filing_date", "ui_label": "备案日期",
            "ui_type": "autofill", "required": True,
        },
    ],
}
