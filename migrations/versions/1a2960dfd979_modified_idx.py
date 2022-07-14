"""modified_idx

Revision ID: 1a2960dfd979
Revises: d0983d7e3954
Create Date: 2021-02-17 14:58:02.471817

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "1a2960dfd979"
down_revision = "d0983d7e3954"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("modified_idx", "encounter", ["modified"], unique=False)


def downgrade():
    op.drop_index("modified_idx", table_name="encounter")
