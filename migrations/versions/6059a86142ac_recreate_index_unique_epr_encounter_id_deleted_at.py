"""PLAT-575 recreate index epr_encounter_id_deleted_at making it unique

Revision ID: 6059a86142ac
Revises: dc5025dbf02b
Create Date: 2020-10-08 14:41:00.724410

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "6059a86142ac"
down_revision = "dc5025dbf02b"
branch_labels = None
depends_on = None


def upgrade():
    recreate(unique=True)


def downgrade():
    recreate(unique=False)


def recreate(unique=False):
    epr_encounter_id_name = "epr_encounter_id"
    index_name = "epr_encounter_id_deleted_at"
    table_name = "encounter"
    unique = "UNIQUE" if unique else ""

    conn = op.get_bind()
    conn.execute(
        f"DROP INDEX IF EXISTS {index_name};"
        f"CREATE {unique} INDEX {index_name} ON {table_name}({epr_encounter_id_name}, COALESCE(deleted_at, '1970-01-01 00:00:00+00'::timestamp with time zone));"
    )
