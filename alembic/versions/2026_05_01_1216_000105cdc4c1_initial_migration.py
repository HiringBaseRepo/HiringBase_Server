"""Initial migration — all tables for Smart Resume Screening System

Revision ID: 000105cdc4c1
Revises:
Create Date: 2026-05-01T12:16:02.964865

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '000105cdc4c1'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # companies
    op.create_table(
        'companies',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('logo_url', sa.String(length=500), nullable=True),
        sa.Column('website', sa.String(length=255), nullable=True),
        sa.Column('industry', sa.String(length=100), nullable=True),
        sa.Column('size_range', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_suspended', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    op.create_index('ix_companies_slug', 'companies', ['slug'], unique=False)

    # users
    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('company_id', sa.BigInteger(), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=True),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('role', sa.Enum('SUPER_ADMIN', 'HR', 'APPLICANT', name='userrole'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_users_company_id', 'users', ['company_id'], unique=False)
    op.create_index('ix_users_email', 'users', ['email'], unique=False)

    # jobs
    op.create_table(
        'jobs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('company_id', sa.BigInteger(), nullable=False),
        sa.Column('created_by', sa.BigInteger(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('department', sa.String(length=100), nullable=True),
        sa.Column('employment_type', sa.Enum('FULL_TIME', 'PART_TIME', 'CONTRACT', 'FREELANCE', 'INTERN', name='employmenttype'), nullable=False),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('salary_min', sa.Integer(), nullable=True),
        sa.Column('salary_max', sa.Integer(), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('responsibilities', sa.Text(), nullable=True),
        sa.Column('benefits', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('DRAFT', 'SCHEDULED', 'PUBLISHED', 'CLOSED', 'PRIVATE', name='jobstatus'), nullable=False),
        sa.Column('apply_code', sa.String(length=50), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scheduled_publish_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('allow_multiple_apply', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('apply_code')
    )
    op.create_index('ix_jobs_company_id', 'jobs', ['company_id'], unique=False)
    op.create_index('ix_jobs_status_published', 'jobs', ['status', 'published_at'], unique=False)
    op.create_index('ix_jobs_title', 'jobs', ['title'], unique=False)

    # job_requirements
    op.create_table(
        'job_requirements',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('job_id', sa.BigInteger(), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('is_required', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # job_scoring_templates
    op.create_table(
        'job_scoring_templates',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('job_id', sa.BigInteger(), nullable=False),
        sa.Column('skill_match_weight', sa.Integer(), nullable=False, server_default='40'),
        sa.Column('experience_weight', sa.Integer(), nullable=False, server_default='20'),
        sa.Column('education_weight', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('portfolio_weight', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('soft_skill_weight', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('administrative_weight', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('custom_rules', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_id')
    )

    # job_form_fields
    op.create_table(
        'job_form_fields',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('job_id', sa.BigInteger(), nullable=False),
        sa.Column('field_key', sa.String(length=100), nullable=False),
        sa.Column('field_type', sa.Enum('TEXT', 'TEXTAREA', 'NUMBER', 'SELECT', 'RADIO', 'CHECKBOX', 'DATE', 'URL', 'FILE', name='formfieldtype'), nullable=False),
        sa.Column('label', sa.String(length=255), nullable=False),
        sa.Column('placeholder', sa.String(length=255), nullable=True),
        sa.Column('help_text', sa.Text(), nullable=True),
        sa.Column('options', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('is_required', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('validation_rules', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_id', 'field_key', name='uq_job_form_field_key')
    )

    # job_knockout_rules
    op.create_table(
        'job_knockout_rules',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('job_id', sa.BigInteger(), nullable=False),
        sa.Column('rule_name', sa.String(length=255), nullable=False),
        sa.Column('rule_type', sa.String(length=50), nullable=False),
        sa.Column('field_key', sa.String(length=100), nullable=True),
        sa.Column('operator', sa.String(length=20), nullable=False),
        sa.Column('target_value', sa.Text(), nullable=False),
        sa.Column('action', sa.String(length=20), nullable=False, server_default='auto_reject'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # applications
    op.create_table(
        'applications',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('job_id', sa.BigInteger(), nullable=False),
        sa.Column('applicant_id', sa.BigInteger(), nullable=False),
        sa.Column('status', sa.Enum('APPLIED', 'DOC_CHECK', 'DOC_FAILED', 'AI_PROCESSING', 'AI_PASSED', 'UNDER_REVIEW', 'INTERVIEW', 'OFFERED', 'HIRED', 'REJECTED', 'KNOCKOUT', name='applicationstatus'), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['applicant_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_id', 'applicant_id', name='uq_application_job_applicant')
    )
    op.create_index('ix_applications_job_id', 'applications', ['job_id'], unique=False)
    op.create_index('ix_applications_applicant_id', 'applications', ['applicant_id'], unique=False)
    op.create_index('ix_applications_status', 'applications', ['status'], unique=False)
    op.create_index('ix_applications_status_created', 'applications', ['status', 'created_at'], unique=False)

    # application_answers
    op.create_table(
        'application_answers',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('application_id', sa.BigInteger(), nullable=False),
        sa.Column('form_field_id', sa.BigInteger(), nullable=False),
        sa.Column('value_text', sa.Text(), nullable=True),
        sa.Column('value_number', sa.Float(), nullable=True),
        sa.Column('value_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['form_field_id'], ['job_form_fields.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # application_documents
    op.create_table(
        'application_documents',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('application_id', sa.BigInteger(), nullable=False),
        sa.Column('document_type', sa.Enum('CV', 'IJAZAH', 'KTP', 'SKCK', 'SURAT_SEHAT', 'SERTIFIKAT', 'PORTFOLIO', 'LAINNYA', name='documenttype'), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_url', sa.String(length=500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('ocr_text', sa.Text(), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # candidate_scores
    op.create_table(
        'candidate_scores',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('application_id', sa.BigInteger(), nullable=False),
        sa.Column('skill_match_score', sa.Float(), nullable=False, server_default='0'),
        sa.Column('experience_score', sa.Float(), nullable=False, server_default='0'),
        sa.Column('education_score', sa.Float(), nullable=False, server_default='0'),
        sa.Column('portfolio_score', sa.Float(), nullable=False, server_default='0'),
        sa.Column('soft_skill_score', sa.Float(), nullable=False, server_default='0'),
        sa.Column('administrative_score', sa.Float(), nullable=False, server_default='0'),
        sa.Column('final_score', sa.Float(), nullable=False, server_default='0'),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('red_flags', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('risk_level', sa.String(length=20), nullable=True),
        sa.Column('is_manual_override', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('manual_override_reason', sa.Text(), nullable=True),
        sa.Column('manual_override_by', sa.BigInteger(), nullable=True),
        sa.Column('computed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['manual_override_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('application_id')
    )

    # application_status_logs
    op.create_table(
        'application_status_logs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('application_id', sa.BigInteger(), nullable=False),
        sa.Column('from_status', sa.String(length=50), nullable=True),
        sa.Column('to_status', sa.String(length=50), nullable=False),
        sa.Column('changed_by', sa.BigInteger(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('metadata_snapshot', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['changed_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_status_logs_app_created', 'application_status_logs', ['application_id', 'created_at'], unique=False)

    # tickets
    op.create_table(
        'tickets',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('application_id', sa.BigInteger(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('status', sa.Enum('OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED', name='ticketstatus'), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index('ix_tickets_code', 'tickets', ['code'], unique=False)

    # interviews
    op.create_table(
        'interviews',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('application_id', sa.BigInteger(), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('meeting_link', sa.String(length=500), nullable=True),
        sa.Column('interview_type', sa.String(length=50), nullable=False, server_default='in_person'),
        sa.Column('interviewer_ids', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('feedback', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('result', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_interviews_application_id', 'interviews', ['application_id'], unique=False)

    # notifications
    op.create_table(
        'notifications',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('type', sa.Enum('APPLY_CONFIRMED', 'AI_SCREENING_PASSED', 'INTERVIEW_INVITE', 'OFFER_SENT', 'HIRED', 'REJECTED', 'DOC_MISSING', 'KNOCKOUT_FAIL', name='notificationtype'), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('link', sa.String(length=500), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'], unique=False)

    # audit_logs
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('company_id', sa.BigInteger(), nullable=True),
        sa.Column('user_id', sa.BigInteger(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('entity_type', sa.String(length=100), nullable=False),
        sa.Column('entity_id', sa.BigInteger(), nullable=False),
        sa.Column('old_values', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('new_values', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_logs_company_id', 'audit_logs', ['company_id'], unique=False)
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'], unique=False)
    op.create_index('ix_audit_logs_entity', 'audit_logs', ['entity_type', 'entity_id', 'created_at'], unique=False)


def downgrade():
    op.drop_index('ix_audit_logs_entity', table_name='audit_logs')
    op.drop_index('ix_audit_logs_user_id', table_name='audit_logs')
    op.drop_index('ix_audit_logs_company_id', table_name='audit_logs')
    op.drop_table('audit_logs')
    op.drop_index('ix_notifications_user_id', table_name='notifications')
    op.drop_table('notifications')
    op.drop_index('ix_interviews_application_id', table_name='interviews')
    op.drop_table('interviews')
    op.drop_index('ix_tickets_code', table_name='tickets')
    op.drop_table('tickets')
    op.drop_index('ix_status_logs_app_created', table_name='application_status_logs')
    op.drop_table('application_status_logs')
    op.drop_table('candidate_scores')
    op.drop_table('application_documents')
    op.drop_table('application_answers')
    op.drop_index('ix_applications_status_created', table_name='applications')
    op.drop_index('ix_applications_status', table_name='applications')
    op.drop_index('ix_applications_applicant_id', table_name='applications')
    op.drop_index('ix_applications_job_id', table_name='applications')
    op.drop_table('applications')
    op.drop_table('job_knockout_rules')
    op.drop_table('job_form_fields')
    op.drop_table('job_scoring_templates')
    op.drop_table('job_requirements')
    op.drop_index('ix_jobs_title', table_name='jobs')
    op.drop_index('ix_jobs_status_published', table_name='jobs')
    op.drop_index('ix_jobs_company_id', table_name='jobs')
    op.drop_table('jobs')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_index('ix_users_company_id', table_name='users')
    op.drop_table('users')
    op.drop_index('ix_companies_slug', table_name='companies')
    op.drop_table('companies')
