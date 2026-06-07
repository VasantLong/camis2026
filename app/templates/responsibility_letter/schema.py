from pydantic import BaseModel, Field


class ResponsibilityLetterForm(BaseModel):
    """主办单位安全和消防责任确认书表单数据"""

    sponsor_unit: str = Field(default="", description="活动主办单位")
    venue_name: str = Field(default="", description="举办场所名称")
    security_measures_confirmed: bool = Field(default=False, description="已制定安全方案并明确各项安全措施")
    facilities_safe: bool = Field(default=False, description="保证临时搭建设施安全")
    security_check_equipped: bool = Field(default=False, description="已配备安全检查设备")
    capacity_compliant: bool = Field(default=False, description="严格按核准容纳人员数量组织活动")
    emergency_measures_confirmed: bool = Field(default=False, description="已落实应急救援措施并组织演练")
    misconduct_response: bool = Field(default=False, description="对妨碍活动安全行为及时制止")
    professional_security_staffed: bool = Field(default=False, description="已配备专业保安人员")
    temporary_electricity_safe: bool = Field(default=False, description="临时用电按规范采取安全措施")
    security_leader_name: str = Field(default="", description="安全负责人姓名")
    security_leader_signature: str = Field(default="", description="安全负责人签字")
    sponsor_seal: str = Field(default="", description="主办单位公章")
    manager_signature: str = Field(default="", description="安保负责人审核签名")
    confirm_date: str = Field(default="", description="确认日期")
    confirm_location: str = Field(default="", description="确认地点")


SCHEMA = {
    "display_name": "安全消防责任确认书",
    "fields": [
        {"name": "sponsor_unit", "ui_label": "活动主办单位", "ui_type": "text", "required": True},
        {"name": "venue_name", "ui_label": "举办场所名称", "ui_type": "text", "required": True},
        {"name": "security_measures_confirmed", "ui_label": "一、已制定活动安全工作方案，明确安全措施，落实岗位职责，已开展安全宣传教育", "ui_type": "checkbox", "required": True},
        {"name": "facilities_safe", "ui_label": "二、保证临时搭建和使用的设施安全，无安全隐患", "ui_type": "checkbox", "required": True},
        {"name": "security_check_equipped", "ui_label": "三、已按照公安机关要求配备安全检查设备", "ui_type": "checkbox", "required": True},
        {"name": "capacity_compliant", "ui_label": "四、严格按照核准场所容纳人员数量、划定区域组织活动", "ui_type": "checkbox", "required": True},
        {"name": "emergency_measures_confirmed", "ui_label": "五、已落实医疗救护、灭火、应急疏散等应急救援措施并组织演练", "ui_type": "checkbox", "required": True},
        {"name": "misconduct_response", "ui_label": "六、对妨碍活动安全的行为及时予以制止，报告违法犯罪行为", "ui_type": "checkbox", "required": True},
        {"name": "professional_security_staffed", "ui_label": "七、已配备与活动安全工作需要相适应的专业保安人员", "ui_type": "checkbox", "required": True},
        {"name": "temporary_electricity_safe", "ui_label": "八、已为活动的安全工作提供必要保障，临时用电按规范采取安全措施", "ui_type": "checkbox", "required": True},
        {"name": "security_leader_name", "ui_label": "活动安全负责人", "ui_type": "text", "required": True},
        {"name": "security_leader_signature", "ui_label": "安全负责人签字", "ui_type": "signature", "required": True},
        {"name": "sponsor_seal", "ui_label": "主办单位（公章）", "ui_type": "text", "required": True},
        {"name": "confirm_date", "ui_label": "确认日期", "ui_type": "date", "required": True},
        {"name": "confirm_location", "ui_label": "确认地点", "ui_type": "text", "required": True},
        # manager_signature is NOT in fields — injected at Manager signing time
    ],
}
