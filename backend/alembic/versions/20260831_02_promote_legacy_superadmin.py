"""Promote the legacy primary administrator to superadmin once."""
from alembic import op


revision = "20260831_02"
down_revision = "20260830_01"
branch_labels = None
depends_on = None


def upgrade():
    # FreshTrack historically had one top-level `admin` account. After adding
    # `superadmin`, promote it only if an explicit superadmin does not exist.
    op.execute("""
        WITH legacy_admin AS (
            SELECT id
            FROM users
            WHERE role = 'admin' AND is_active = true
            ORDER BY id
            LIMIT 1
        )
        UPDATE users
        SET role = 'superadmin'
        WHERE id = (SELECT id FROM legacy_admin)
          AND NOT EXISTS (
              SELECT 1 FROM users WHERE role = 'superadmin'
          )
    """)


def downgrade():
    # The migration cannot safely infer whether a superadmin was promoted or
    # subsequently assigned deliberately, so its data change is irreversible.
    pass
