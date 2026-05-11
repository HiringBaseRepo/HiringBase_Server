"""Application schemas."""
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Any
from datetime import datetime


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
    employment_type_label: str | None = None


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
    employment_type_label: str | None = None
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
    status_label: str | None = None


class ApplicationListItem(BaseModel):
    id: int
    job_id: int
    applicant_id: int
    status: str
    status_label: str | None = None
    created_at: str | None

    model_config = {"from_attributes": True}


class ApplicationStatusUpdateResponse(BaseModel):
    application_id: int
    old_status: str | None
    new_status: str
    new_status_label: str | None = None


class ApplicationAnswerResponse(BaseModel):
    field_key: str
    label: str
    value: Any


class ApplicationDocumentResponse(BaseModel):
    id: int
    document_type: str
    file_name: str
    file_url: str


class CandidateScoreResponse(BaseModel):
    skill_match_score: float
    experience_score: float
    education_score: float
    portfolio_score: float
    soft_skill_score: float
    administrative_score: float
    final_score: float
    explanation: Optional[str]
    red_flags: Optional[List[dict]]
    risk_level: Optional[str]


class ApplicationDetailResponse(BaseModel):
    id: int
    job_id: int
    job_title: str
    applicant_name: str
    applicant_email: str
    status: str
    status_label: str
    created_at: datetime
    answers: List[ApplicationAnswerResponse]
    documents: List[ApplicationDocumentResponse]
    score: Optional[CandidateScoreResponse] = None

    model_config = {"from_attributes": True}
