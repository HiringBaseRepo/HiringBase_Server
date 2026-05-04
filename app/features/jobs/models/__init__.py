from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Index,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base
from app.shared.enums.job_status import JobStatus
from app.shared.enums.employment_type import EmploymentType
from app.shared.enums.field_type import FormFieldType

if TYPE_CHECKING:
    from app.features.companies.models import Company
    from app.features.users.models import User
    from app.features.applications.models import Application, ApplicationAnswer

class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    employment_type: Mapped[EmploymentType] = mapped_column(Enum(EmploymentType), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    salary_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    responsibilities: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    benefits: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), nullable=False, default=JobStatus.DRAFT)
    apply_code: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True, index=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_publish_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_multiple_apply: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    company: Mapped["Company"] = relationship("Company", back_populates="jobs")
    created_by_user: Mapped[Optional["User"]] = relationship("User", back_populates="jobs_created")
    requirements: Mapped[List["JobRequirement"]] = relationship("JobRequirement", back_populates="job", cascade="all, delete-orphan")
    scoring_template: Mapped[Optional["JobScoringTemplate"]] = relationship("JobScoringTemplate", back_populates="job", uselist=False, cascade="all, delete-orphan")
    form_fields: Mapped[List["JobFormField"]] = relationship("JobFormField", back_populates="job", cascade="all, delete-orphan")
    knockout_rules: Mapped[List["JobKnockoutRule"]] = relationship("JobKnockoutRule", back_populates="job", cascade="all, delete-orphan")
    applications: Mapped[List["Application"]] = relationship("Application", back_populates="job")

    __table_args__ = (
        Index("ix_jobs_status_published", "status", "published_at"),
    )

class JobRequirement(Base):
    __tablename__ = "job_requirements"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # skill, experience, education, certification, language
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)  # stored as text / json string
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=1)  # 1 = high, 2 = medium, 3 = low
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job: Mapped["Job"] = relationship("Job", back_populates="requirements")

class JobScoringTemplate(Base):
    __tablename__ = "job_scoring_templates"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, unique=True)
    skill_match_weight: Mapped[int] = mapped_column(Integer, default=40)
    experience_weight: Mapped[int] = mapped_column(Integer, default=20)
    education_weight: Mapped[int] = mapped_column(Integer, default=10)
    portfolio_weight: Mapped[int] = mapped_column(Integer, default=10)
    soft_skill_weight: Mapped[int] = mapped_column(Integer, default=10)
    administrative_weight: Mapped[int] = mapped_column(Integer, default=10)
    custom_rules: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    job: Mapped["Job"] = relationship("Job", back_populates="scoring_template")

class JobFormField(Base):
    __tablename__ = "job_form_fields"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    field_key: Mapped[str] = mapped_column(String(100), nullable=False)
    field_type: Mapped[FormFieldType] = mapped_column(Enum(FormFieldType), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    placeholder: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    help_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    options: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # for select, radio, checkbox
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    validation_rules: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # min, max, regex
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    job: Mapped["Job"] = relationship("Job", back_populates="form_fields")
    answers: Mapped[List["ApplicationAnswer"]] = relationship("ApplicationAnswer", back_populates="form_field")

    __table_args__ = (
        UniqueConstraint("job_id", "field_key", name="uq_job_form_field_key"),
    )

class JobKnockoutRule(Base):
    __tablename__ = "job_knockout_rules"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)  # document, experience, education, boolean, range
    field_key: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    operator: Mapped[str] = mapped_column(String(20), nullable=False)  # eq, neq, gt, gte, lt, lte, contains, in
    target_value: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(String(20), default="auto_reject")  # auto_reject, pending_review
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    job: Mapped["Job"] = relationship("Job", back_populates="knockout_rules")
