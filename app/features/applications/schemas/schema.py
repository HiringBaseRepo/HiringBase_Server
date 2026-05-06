"""Application schemas."""
from pydantic import BaseModel, EmailStr


class PublicJobItem(BaseModel):
    id: int
    title: str
    department: str | None
    employment_type: str
    location: str | None
    salary_min: int | None
    salary_max: int | None
    description: str
    apply_code: str | None
    company_name: str | None
    published_at: str | None


class PublicJobFormField(BaseModel):
    field_key: str
    field_type: str
    label: str
    is_required: bool


class PublicJobDetailResponse(BaseModel):
    id: int
    title: str
    description: str
    responsibilities: str | None
    benefits: str | None
    employment_type: str
    location: str | None
    company_name: str | None
    form_fields: list[PublicJobFormField]


class PublicApplyCommand(BaseModel):
    job_id: int
    email: EmailStr
    full_name: str
    phone: str | None = None
    answers_json: str | None = None


class PublicApplyResponse(BaseModel):
    application_id: int
    ticket_code: str
    status: str


class ApplicationListItem(BaseModel):
    id: int
    job_id: int
    applicant_id: int
    status: str
    created_at: str | None

    model_config = {"from_attributes": True}


class ApplicationStatusUpdateResponse(BaseModel):
    application_id: int
    old_status: str | None
    new_status: str
