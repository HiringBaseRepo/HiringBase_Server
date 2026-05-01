"""
Database Models — Smart Resume Screening System
All models use SQLAlchemy 2.0 declarative style with asyncpg.
"""
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base
from app.shared.enums.user_roles import UserRole
from app.shared.enums.application_status import ApplicationStatus
from app.shared.enums.job_status import JobStatus
from app.shared.enums.employment_type import EmploymentType
from app.shared.enums.field_type import FormFieldType
from app.shared.enums.document_type import DocumentType
from app.shared.enums.ticket_status import TicketStatus
from app.shared.enums.notification_type import NotificationType


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ============================================================
# 1. COMPANIES
# ============================================================
class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    size_range: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_suspended: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    users: Mapped[List["User"]] = relationship("User", back_populates="company")
    jobs: Mapped[List["Job"]] = relationship("Job", back_populates="company")
    audit_logs: Mapped[List["AuditLog"]] = relationship("AuditLog", back_populates="company")


# ============================================================
# 2. USERS
# ============================================================
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, default=UserRole.APPLICANT)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    company: Mapped[Optional["Company"]] = relationship("Company", back_populates="users")
    jobs_created: Mapped[List["Job"]] = relationship("Job", back_populates="created_by_user")
    applications: Mapped[List["Application"]] = relationship("Application", back_populates="applicant")
    notifications: Mapped[List["Notification"]] = relationship("Notification", back_populates="user")
    audit_logs: Mapped[List["AuditLog"]] = relationship("AuditLog", back_populates="user")


# ============================================================
# 3. JOBS (Vacancies)
# ============================================================
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


# ============================================================
# 4. JOB REQUIREMENTS
# ============================================================
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


# ============================================================
# 5. JOB SCORING TEMPLATES
# ============================================================
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


# ============================================================
# 6. JOB FORM FIELDS (Custom Applicant Form Builder)
# ============================================================
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


# ============================================================
# 7. JOB KNOCKOUT RULES
# ============================================================
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


# ============================================================
# 8. APPLICATIONS
# ============================================================
class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    applicant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus), nullable=False, default=ApplicationStatus.APPLIED, index=True
    )
    source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # public, referral, internal
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    job: Mapped["Job"] = relationship("Job", back_populates="applications")
    applicant: Mapped["User"] = relationship("User", back_populates="applications")
    answers: Mapped[List["ApplicationAnswer"]] = relationship("ApplicationAnswer", back_populates="application", cascade="all, delete-orphan")
    documents: Mapped[List["ApplicationDocument"]] = relationship("ApplicationDocument", back_populates="application", cascade="all, delete-orphan")
    scores: Mapped[Optional["CandidateScore"]] = relationship("CandidateScore", back_populates="application", uselist=False, cascade="all, delete-orphan")
    status_logs: Mapped[List["ApplicationStatusLog"]] = relationship("ApplicationStatusLog", back_populates="application", cascade="all, delete-orphan")
    ticket: Mapped[Optional["Ticket"]] = relationship("Ticket", back_populates="application", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("job_id", "applicant_id", name="uq_application_job_applicant"),
        Index("ix_applications_status_created", "status", "created_at"),
    )


# ============================================================
# 9. APPLICATION ANSWERS
# ============================================================
class ApplicationAnswer(Base):
    __tablename__ = "application_answers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    form_field_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("job_form_fields.id", ondelete="CASCADE"), nullable=False)
    value_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    value_number: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    value_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    application: Mapped["Application"] = relationship("Application", back_populates="answers")
    form_field: Mapped["JobFormField"] = relationship("JobFormField", back_populates="answers")


# ============================================================
# 10. APPLICATION DOCUMENTS
# ============================================================
class ApplicationDocument(Base):
    __tablename__ = "application_documents"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    document_type: Mapped[DocumentType] = mapped_column(Enum(DocumentType), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    ocr_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    application: Mapped["Application"] = relationship("Application", back_populates="documents")


# ============================================================
# 11. CANDIDATE SCORES
# ============================================================
class CandidateScore(Base):
    __tablename__ = "candidate_scores"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, unique=True)
    skill_match_score: Mapped[float] = mapped_column(Float, default=0.0)
    experience_score: Mapped[float] = mapped_column(Float, default=0.0)
    education_score: Mapped[float] = mapped_column(Float, default=0.0)
    portfolio_score: Mapped[float] = mapped_column(Float, default=0.0)
    soft_skill_score: Mapped[float] = mapped_column(Float, default=0.0)
    administrative_score: Mapped[float] = mapped_column(Float, default=0.0)
    final_score: Mapped[float] = mapped_column(Float, default=0.0)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    red_flags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    risk_level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_manual_override: Mapped[bool] = mapped_column(Boolean, default=False)
    manual_override_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    manual_override_by: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    application: Mapped["Application"] = relationship("Application", back_populates="scores")


# ============================================================
# 12. APPLICATION STATUS LOGS
# ============================================================
class ApplicationStatusLog(Base):
    __tablename__ = "application_status_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    from_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    to_status: Mapped[str] = mapped_column(String(50), nullable=False)
    changed_by: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_snapshot: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    application: Mapped["Application"] = relationship("Application", back_populates="status_logs")

    __table_args__ = (
        Index("ix_status_logs_app_created", "application_id", "created_at"),
    )


# ============================================================
# 13. TICKETS
# ============================================================
class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, unique=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    status: Mapped[TicketStatus] = mapped_column(Enum(TicketStatus), default=TicketStatus.OPEN)
    subject: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    application: Mapped["Application"] = relationship("Application", back_populates="ticket")


# ============================================================
# 14. INTERVIEWS
# ============================================================
class Interview(Base):
    __tablename__ = "interviews"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    meeting_link: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    interview_type: Mapped[str] = mapped_column(String(50), default="in_person")  # in_person, video, phone
    interviewer_ids: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    feedback: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    result: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # passed, failed, pending
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ============================================================
# 15. NOTIFICATIONS
# ============================================================
class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    link: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="notifications")


# ============================================================
# 16. AUDIT LOGS
# ============================================================
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)  # job, application, user, score
    entity_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    old_values: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    new_values: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company: Mapped[Optional["Company"]] = relationship("Company", back_populates="audit_logs")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_logs_entity", "entity_type", "entity_id", "created_at"),
    )
