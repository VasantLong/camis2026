from pydantic import BaseModel, Field


class ResponsibilityLetterForm(BaseModel):
    """主办单位安全和消防责任确认书表单数据"""

    sponsor_unit: str = Field(default="", description="活动主办单位")
    security_leader_name: str = Field(default="", description="安全负责人姓名")
    security_leader_signature: str = Field(default="", description="安全负责人签字")
    # sponsor_seal omitted — physical stamp applied offline after DOCX printing
    manager_signature: str = Field(default="", description="安保负责人审核签名")
    confirm_date: str = Field(default="", description="确认日期")
    confirm_location: str = Field(default="", description="确认地点")


DECLARATION_ITEMS = [
    "已具体制订活动安全工作方案和安全责任制度，明确各项安全措施、落实安全工作人员岗位职责，事先开展活动安全宣传教育",
    "保证临时搭建和使用的设施安全，沒有安全隐患",
    "已按照负责许可的公安机关的要求，配备必要的安全检查设备，对参加活动的人员进行安全检查，对拒不接受安全检查的，有权拒绝进入",
    "严格按照核准的活动场所容纳人员数量、划定的区域组织活动",
    "已落实医疗救护、灭火、应急疏散等应急救援措施并组织演练",
    "对妨碍活动安全的行为及时予以制止，发现违法犯罪行为及时向公安机关报告",
    "已配备与活动安全工作需要相适应的专业保安人员或其他安全工作人员",
    "已为活动的安全工作提供必要的保障。临时用电按规范采取安全措施",
]


SCHEMA = {
    "display_name": "安全消防责任确认书",
    "fields": [
        {"name": "sponsor_unit", "ui_label": "活动主办单位", "ui_type": "autofill", "autofill_from": "default", "required": True},
        {"name": "declarations", "ui_label": "安全消防责任确认", "ui_type": "declarations",
         "declaration_items": DECLARATION_ITEMS,
         "hint": "依据国务院《大型群众性活动安全管理条例》《安全生产法》《消防法》等法律法规。以下声明由主办单位公章及安全负责人签字确认，依法承担相应法律责任。"},
        {"name": "security_leader_name", "ui_label": "活动安全负责人", "ui_type": "text", "required": True},
        {"name": "security_leader_signature", "ui_label": "安全负责人签字", "ui_type": "signature", "required": True},
        {"name": "confirm_date", "ui_label": "确认日期", "ui_type": "autofill", "autofill_from": "default", "required": True},
        {"name": "confirm_location", "ui_label": "确认地点", "ui_type": "autofill", "autofill_from": "default", "required": True},
        # manager_signature is NOT in fields — injected at Manager signing time
    ],
}
