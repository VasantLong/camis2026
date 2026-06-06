from pathlib import Path

from app.templates.activity_plan.schema import ActivityPlanForm, SCHEMA as ACTIVITY_PLAN_SCHEMA
from app.templates.security_plan.schema import SecurityPlanForm, SCHEMA as SECURITY_PLAN_SCHEMA
from app.templates.risk_assessment.schema import RiskAssessmentForm, SCHEMA as RISK_ASSESSMENT_SCHEMA
from app.templates.responsibility_letter.schema import (
    ResponsibilityLetterForm,
    SCHEMA as RESPONSIBILITY_LETTER_SCHEMA,
)
from app.templates.filing_commitment.schema import (
    FilingCommitmentForm,
    SCHEMA as FILING_COMMITMENT_SCHEMA,
)

TEMPLATES_ROOT = Path(__file__).parent

FORM_MODELS = {
    "activity_plan": ActivityPlanForm,
    "security_plan": SecurityPlanForm,
    "risk_assessment": RiskAssessmentForm,
    "responsibility_letter": ResponsibilityLetterForm,
    "filing_commitment": FilingCommitmentForm,
}

SCHEMAS = {
    "activity_plan": ACTIVITY_PLAN_SCHEMA,
    "security_plan": SECURITY_PLAN_SCHEMA,
    "risk_assessment": RISK_ASSESSMENT_SCHEMA,
    "responsibility_letter": RESPONSIBILITY_LETTER_SCHEMA,
    "filing_commitment": FILING_COMMITMENT_SCHEMA,
}

TEMPLATE_DISPLAY_NAMES = {
    "activity_plan": "活动方案",
    "security_plan": "安保方案",
    "risk_assessment": "风险评估报备表",
    "responsibility_letter": "安全消防责任确认书",
    "filing_commitment": "备案承诺书",
}

# template_type to entity target for draft/generation routing
TEMPLATE_ENTITY_MAP = {
    "activity_plan": "activity_plan",
    "security_plan": "security_plan",
    "risk_assessment": "key_material",
    "responsibility_letter": "key_material",
    "filing_commitment": "key_material",
}

__all__ = [
    "FORM_MODELS", "SCHEMAS", "TEMPLATES_ROOT",
    "TEMPLATE_DISPLAY_NAMES", "TEMPLATE_ENTITY_MAP",
]
