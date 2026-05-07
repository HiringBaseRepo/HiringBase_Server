"""rename_document_type_enum_values

Revision ID: f57f72ae1e12
Revises: 7fcb11ddebc6
Create Date: 2026-05-06 19:46:35.298113+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f57f72ae1e12'
down_revision = '7fcb11ddebc6'
branch_labels = None
depends_on = None


def upgrade():
    # Rename enum values in PostgreSQL to match member names (uppercase)
    op.execute("ALTER TYPE documenttype RENAME VALUE 'KTP' TO 'IDENTITY_CARD'")
    op.execute("ALTER TYPE documenttype RENAME VALUE 'IJAZAH' TO 'DEGREE'")
    op.execute("ALTER TYPE documenttype RENAME VALUE 'SKCK' TO 'CRIMINAL_RECORD'")
    op.execute("ALTER TYPE documenttype RENAME VALUE 'SURAT_SEHAT' TO 'HEALTH_CERTIFICATE'")
    op.execute("ALTER TYPE documenttype RENAME VALUE 'SERTIFIKAT' TO 'CERTIFICATE'")
    op.execute("ALTER TYPE documenttype RENAME VALUE 'LAINNYA' TO 'OTHERS'")


def downgrade():
    # Revert rename enum values in PostgreSQL
    op.execute("ALTER TYPE documenttype RENAME VALUE 'IDENTITY_CARD' TO 'KTP'")
    op.execute("ALTER TYPE documenttype RENAME VALUE 'DEGREE' TO 'IJAZAH'")
    op.execute("ALTER TYPE documenttype RENAME VALUE 'CRIMINAL_RECORD' TO 'SKCK'")
    op.execute("ALTER TYPE documenttype RENAME VALUE 'HEALTH_CERTIFICATE' TO 'SURAT_SEHAT'")
    op.execute("ALTER TYPE documenttype RENAME VALUE 'CERTIFICATE' TO 'SERTIFIKAT'")
    op.execute("ALTER TYPE documenttype RENAME VALUE 'OTHERS' TO 'LAINNYA'")
