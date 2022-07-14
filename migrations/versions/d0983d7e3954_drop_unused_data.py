"""drop unused data

Revision ID: d0983d7e3954
Revises: 33edf1d1d924
Create Date: 2021-01-18 16:05:34.239022

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d0983d7e3954"
down_revision = "33edf1d1d924"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("score_system_history", "changed_by")
    op.drop_column("score_system_history", "clinician_uuid")


def downgrade():
    op.add_column(
        "score_system_history",
        sa.Column(
            "clinician_uuid", sa.VARCHAR(length=36), autoincrement=False, nullable=True
        ),
    )
    op.add_column(
        "score_system_history",
        sa.Column("changed_by", sa.VARCHAR(), autoincrement=False, nullable=True),
    )
