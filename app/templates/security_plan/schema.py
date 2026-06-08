from pydantic import BaseModel, Field


class SecurityPlanForm(BaseModel):
    """安保方案表单数据"""

    security_staff_config: str = Field(default="", description="安保人员配置")
    security_staff_count: int = Field(default=0, description="安保人员数量")
    movement_plan: str = Field(default="", description="动线设计")
    equipment_list: str = Field(default="", description="安保设备清单")
    emergency_plan: str = Field(default="", description="应急预案")
    medical_plan: str = Field(default="", description="医疗救护措施")
    fire_plan: str = Field(default="", description="消防措施")
    crowd_control: str = Field(default="", description="人流管控方案")
    manager_signature: str = Field(default="", description="安保负责人审核签名")


# 条件段定义：risk_level 决定哪些字段可见
CONDITIONAL_FIELDS = {
    "高风险": ["medical_plan", "fire_plan", "crowd_control"],
    "中低风险": ["fire_plan"],
    "低风险": [],
}

SCHEMA = {
    "display_name": "安保方案",
    "risk_level_first": True,
    "conditional_fields": CONDITIONAL_FIELDS,
    "fields": [
        {"name": "security_staff_config", "ui_label": "安保人员配置", "ui_type": "textarea", "required": True},
        {"name": "security_staff_count", "ui_label": "安保人员数量", "ui_type": "number", "min": 0, "required": True},
        {"name": "movement_plan", "ui_label": "动线设计", "ui_type": "textarea", "required": True},
        {"name": "equipment_list", "ui_label": "安保设备清单", "ui_type": "textarea", "required": True},
        {"name": "emergency_plan", "ui_label": "应急预案", "ui_type": "textarea", "required": True},
        {"name": "medical_plan", "ui_label": "医疗救护措施", "ui_type": "textarea", "condition": "risk_level == '高风险'"},
        {"name": "fire_plan", "ui_label": "消防措施", "ui_type": "textarea", "condition": "risk_level != '低风险'"},
        {"name": "crowd_control", "ui_label": "人流管控方案", "ui_type": "textarea", "condition": "risk_level == '高风险'"},
        # manager_signature is NOT in fields — injected at Manager signing time, not shown in form
    ],
}
