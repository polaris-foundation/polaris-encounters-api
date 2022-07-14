"""Added merge_history

Revision ID: db9023dbf02a
Revises: d6b859f01555
Create Date: 2020-07-24 16:01:08.199016

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "dc5025dbf02b"
down_revision = "db9023dbf02a"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(
        """
            CREATE INDEX open_idx
                ON encounter USING btree
                (patient_uuid, admitted_at DESC )
            where 
                parent_uuid is null
                AND discharged_at is null
                AND deleted_at is null
                AND (epr_encounter_id is null or epr_encounter_id='');
        """
    )
    conn.execute(
        """
            CREATE INDEX location_idx
            ON encounter USING btree (location_uuid);
        """
    )


def downgrade():
    conn = op.get_bind()
    conn.execute(
        """
            DROP INDEX IF EXISTS open_idx; 
            DROP INDEX IF EXISTS location_idx;
        """
    )
