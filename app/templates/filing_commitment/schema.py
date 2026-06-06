from pydantic import BaseModel, Field


class FilingCommitmentForm(BaseModel):
    """备案承诺书表单数据"""

    commitment_content: str = Field(default="", description="承诺书正文")
    applicant_name: str = Field(default="", description="申请人姓名")
    applicant_signature: str = Field(default="", description="申请人签字")
    filing_date: str = Field(default="", description="备案日期")


SCHEMA = {
    "display_name": "备案承诺书",
    "fields": [
        {"name": "commitment_content", "ui_label": "承诺书正文", "ui_type": "textarea", "required": True},
        {"name": "applicant_name", "ui_label": "申请人", "ui_type": "text", "required": True},
        {"name": "applicant_signature", "ui_label": "申请人签字", "ui_type": "signature", "required": True},
        {"name": "filing_date", "ui_label": "备案日期", "ui_type": "date", "required": True},
    ],
}
