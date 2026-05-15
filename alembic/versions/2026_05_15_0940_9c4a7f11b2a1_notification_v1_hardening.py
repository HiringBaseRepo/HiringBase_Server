"""notification_v1_hardening

Revision ID: 9c4a7f11b2a1
Revises: 1f2b09dda015
Create Date: 2026-05-15 09:40:00.000000+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "9c4a7f11b2a1"
down_revision = "1f2b09dda015"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "notifications",
        sa.Column("entity_type", sa.String(length=100), nullable=False, server_default="application"),
    )
    op.add_column(
        "notifications",
        sa.Column("entity_id", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "notifications",
        sa.Column("message_params", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )
    op.alter_column("notifications", "entity_type", server_default=None)

    op.create_index(
        "ix_notifications_user_unread_created_at",
        "notifications",
        ["user_id", "is_read", "created_at"],
        unique=False,
    )

    op.execute("ALTER TYPE notificationtype RENAME TO notificationtype_old")
    op.execute(
        """
        CREATE TYPE notificationtype AS ENUM (
            'NEW_APPLICATION',
            'SCREENING_PASSED',
            'SCREENING_UNDER_REVIEW',
            'SCREENING_REJECTED',
            'DOCUMENT_FAILED',
            'INTERVIEW_SCHEDULED',
            'APPLICATION_OFFERED',
            'APPLICATION_HIRED',
            'APPLICATION_REJECTED'
        )
        """
    )
    op.execute(
        """
        ALTER TABLE notifications
        ALTER COLUMN type TYPE notificationtype
        USING (
            CASE type::text
                WHEN 'APPLY_CONFIRMED' THEN 'NEW_APPLICATION'
                WHEN 'AI_SCREENING_PASSED' THEN 'SCREENING_PASSED'
                WHEN 'INTERVIEW_INVITE' THEN 'INTERVIEW_SCHEDULED'
                WHEN 'OFFER_SENT' THEN 'APPLICATION_OFFERED'
                WHEN 'HIRED' THEN 'APPLICATION_HIRED'
                WHEN 'REJECTED' THEN 'APPLICATION_REJECTED'
                WHEN 'DOC_MISSING' THEN 'DOCUMENT_FAILED'
                WHEN 'KNOCKOUT_FAIL' THEN 'SCREENING_REJECTED'
                ELSE 'NEW_APPLICATION'
            END
        )::notificationtype
        """
    )
    op.execute("DROP TYPE notificationtype_old")


def downgrade():
    op.execute("ALTER TYPE notificationtype RENAME TO notificationtype_new")
    op.execute(
        """
        CREATE TYPE notificationtype AS ENUM (
            'APPLY_CONFIRMED',
            'AI_SCREENING_PASSED',
            'INTERVIEW_INVITE',
            'OFFER_SENT',
            'HIRED',
            'REJECTED',
            'DOC_MISSING',
            'KNOCKOUT_FAIL'
        )
        """
    )
    op.execute(
        """
        ALTER TABLE notifications
        ALTER COLUMN type TYPE notificationtype
        USING (
            CASE type::text
                WHEN 'NEW_APPLICATION' THEN 'APPLY_CONFIRMED'
                WHEN 'SCREENING_PASSED' THEN 'AI_SCREENING_PASSED'
                WHEN 'SCREENING_UNDER_REVIEW' THEN 'AI_SCREENING_PASSED'
                WHEN 'SCREENING_REJECTED' THEN 'KNOCKOUT_FAIL'
                WHEN 'DOCUMENT_FAILED' THEN 'DOC_MISSING'
                WHEN 'INTERVIEW_SCHEDULED' THEN 'INTERVIEW_INVITE'
                WHEN 'APPLICATION_OFFERED' THEN 'OFFER_SENT'
                WHEN 'APPLICATION_HIRED' THEN 'HIRED'
                WHEN 'APPLICATION_REJECTED' THEN 'REJECTED'
                ELSE 'APPLY_CONFIRMED'
            END
        )::notificationtype
        """
    )
    op.execute("DROP TYPE notificationtype_new")

    op.drop_index("ix_notifications_user_unread_created_at", table_name="notifications")
    op.drop_column("notifications", "message_params")
    op.drop_column("notifications", "entity_id")
    op.drop_column("notifications", "entity_type")
