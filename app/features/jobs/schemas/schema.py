"""Job management schemas."""
from datetime import datetime
from pydantic import BaseModel, Field

from app.shared.enums.employment_type import EmploymentType
from app.shared.enums.field_type import FormFieldType
from app.shared.enums.job_status import JobStatus


class CreateJobStep1Request(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    department: str | None = None
    employment_type: EmploymentType = EmploymentType.FULL_TIME
    location: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    description: str = ""
    responsibilities: str | None = None
    benefits: str | None = None


class JobRequirementInput(BaseModel):
    category: str
    name: str
    value: str
    is_required: bool = True
    priority: int = 1


class AddJobRequirementsRequest(BaseModel):
    requirements: list[JobRequirementInput]


class JobFormFieldInput(BaseModel):
    field_key: str
    field_type: FormFieldType
    label: str
    placeholder: str | None = None
    help_text: str | None = None
    options: dict | None = None
    is_required: bool = True
    order_index: int = 0
    validation_rules: dict | None = None


class SetupJobFormRequest(BaseModel):
    fields: list[JobFormFieldInput]


class PublishJobRequest(BaseModel):
    mode: str = "public"
    scheduled_at: datetime | None = None


class JobStepResponse(BaseModel):
    job_id: int
    status: JobStatus | None = None
    requirements_added: int | None = None
    form_fields_added: int | None = None


class JobPublishResponse(BaseModel):
    job_id: int
    status: JobStatus
    apply_code: str | None
    is_public: bool


class JobListItem(BaseModel):
    id: int
    title: str
    department: str | None
    employment_type: EmploymentType
    status: JobStatus
    location: str | None
    apply_code: str | None
    published_at: str | None
    created_at: str | None


class JobRequirementItem(BaseModel):
    id: int
    category: str
    name: str
    value: str
    is_required: bool


class JobFormFieldItem(BaseModel):
    id: int
    field_key: str
    field_type: FormFieldType
    label: str
    is_required: bool


class JobKnockoutRuleItem(BaseModel):
    id: int
    rule_name: str
    rule_type: str
    action: str


class JobDetailResponse(BaseModel):
    id: int
    title: str
    description: str
    requirements: list[JobRequirementItem]
    form_fields: list[JobFormFieldItem]
    knockout_rules: list[JobKnockoutRuleItem]


class JobCloseResponse(BaseModel):
    job_id: int
    status: JobStatus
