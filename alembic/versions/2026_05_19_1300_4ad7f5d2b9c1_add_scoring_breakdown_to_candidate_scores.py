"""add_scoring_breakdown_to_candidate_scores

Revision ID: 4ad7f5d2b9c1
Revises: 9c4a7f11b2a1
Create Date: 2026-05-19 13:00:00.000000+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "4ad7f5d2b9c1"
down_revision = "9c4a7f11b2a1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "candidate_scores",
        sa.Column(
            "scoring_breakdown",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade():
    op.drop_column("candidate_scores", "scoring_breakdown")
