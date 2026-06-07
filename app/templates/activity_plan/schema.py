from pydantic import BaseModel, Field

CROWD_OPTIONS = ["1000以下", "1000-3000", "3000-5000", "5000-10000", "10000以上"]


class ActivityPlanForm(BaseModel):
    """活动方案表单数据"""

    activity_content: str = Field(default="", description="活动主要内容")
    start_time: str = Field(default="", description="活动开始时间")
    end_time: str = Field(default="", description="活动结束时间")
    total_days: int = Field(default=0, description="共计天数（自动计算）")
    has_opening: str = Field(default="否", description="是否有开幕式")
    opening_start: str = Field(default="", description="开幕式开始时间")
    opening_end: str = Field(default="", description="开幕式结束时间")
    has_performers: str = Field(default="否", description="是否有演员嘉宾")
    staff_count: int = Field(default=0, description="工作人员数量")
    performer_count: int = Field(default=0, description="演员数量")
    guest_count: int = Field(default=0, description="嘉宾数量")
    opening_crowd: str = Field(default="", description="主要活动日人数范围")
    regular_crowd: str = Field(default="", description="平日人数范围")
    construction_plan: str = Field(default="", description="搭建方案（含材料明细、平面图、效果图）")
    contact_phone: str = Field(default="", description="负责人联系方式")
    remarks: str = Field(default="", description="备注")


SCHEMA = {
    "display_name": "活动方案",
    "fields": [
        {"name": "activity_content", "ui_label": "活动主要内容", "ui_type": "textarea", "required": True},
        {"name": "start_time", "ui_label": "开始时间", "ui_type": "date", "required": True},
        {"name": "end_time", "ui_label": "结束时间", "ui_type": "date", "required": True},
        {"name": "total_days", "ui_label": "共计天数", "ui_type": "number", "auto_calc": "end_time - start_time"},
        {"name": "has_opening", "ui_label": "是否有开幕式", "ui_type": "select", "options": ["是", "否"], "required": True},
        {"name": "opening_start", "ui_label": "开幕式开始", "ui_type": "date", "condition": "has_opening == '是'"},
        {"name": "opening_end", "ui_label": "开幕式结束", "ui_type": "date", "condition": "has_opening == '是'"},
        {"name": "has_performers", "ui_label": "是否有演员嘉宾", "ui_type": "select", "options": ["是", "否"], "required": True},
        {"name": "staff_count", "ui_label": "工作人员数量", "ui_type": "number", "min": 0},
        {"name": "performer_count", "ui_label": "演员数量", "ui_type": "number", "min": 0, "condition": "has_performers == '是'"},
        {"name": "guest_count", "ui_label": "嘉宾数量", "ui_type": "number", "min": 0, "condition": "has_performers == '是'"},
        {"name": "opening_crowd", "ui_label": "主要活动日人数", "ui_type": "select", "options": CROWD_OPTIONS, "condition": "has_opening == '是'"},
        {"name": "regular_crowd", "ui_label": "平日人数", "ui_type": "select", "options": CROWD_OPTIONS, "required": True},
        {"name": "construction_plan", "ui_label": "搭建方案", "ui_type": "textarea", "required": True},
        {"name": "contact_phone", "ui_label": "负责人联系方式", "ui_type": "text", "required": True, "validate": {"pattern": "^1[3-9]\\d{9}$", "message": "须为11位手机号码"}},
        {"name": "remarks", "ui_label": "备注", "ui_type": "text"},
    ],
}
