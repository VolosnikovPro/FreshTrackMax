"""FreshTrack roles, UPD, financials, imports and audit history."""
from alembic import op
from alembic import context
import sqlalchemy as sa

revision = "20260830_01"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'superadmin'")
    op.add_column("batches", sa.Column("upd_number", sa.String(64), nullable=True))
    op.add_column("batches", sa.Column("status", sa.String(16), nullable=False, server_default="active"))
    op.add_column("daily_consumptions", sa.Column("import_run_id", sa.Integer, nullable=True))
    op.add_column("daily_consumptions", sa.Column("is_cancelled", sa.Boolean, nullable=False, server_default=sa.false()))
    op.execute("UPDATE batches SET upd_number = batch_number WHERE upd_number IS NULL")
    op.execute("UPDATE batches SET status = 'archived' WHERE quantity <= 0")
    op.create_index("uq_batch_site_product_upd_expiry", "batches", ["site_id", "product_id", "upd_number", "expiry_date"], unique=True)
    op.create_table("daily_financial_expenses", sa.Column("id", sa.Integer, primary_key=True), sa.Column("site_id", sa.Integer, sa.ForeignKey("sites.id"), nullable=False), sa.Column("date", sa.Date, nullable=False), sa.Column("invoice_amount_net", sa.Numeric(18, 4), nullable=False), sa.Column("entered_by", sa.Integer, sa.ForeignKey("users.id")), sa.Column("created_at", sa.DateTime), sa.Column("updated_at", sa.DateTime))
    op.create_index("uq_financial_expense_site_date", "daily_financial_expenses", ["site_id", "date"], unique=True)
    op.create_table("import_fingerprints", sa.Column("id", sa.Integer, primary_key=True), sa.Column("site_id", sa.Integer, sa.ForeignKey("sites.id"), nullable=False), sa.Column("import_type", sa.String(64), nullable=False), sa.Column("sha256", sa.String(64), nullable=False), sa.Column("active_import_id", sa.Integer))
    op.create_index("uq_import_fingerprint", "import_fingerprints", ["site_id", "import_type", "sha256"], unique=True)
    op.create_table("import_runs", sa.Column("id", sa.Integer, primary_key=True), sa.Column("fingerprint_id", sa.Integer, sa.ForeignKey("import_fingerprints.id")), sa.Column("site_id", sa.Integer, sa.ForeignKey("sites.id"), nullable=False), sa.Column("import_type", sa.String(64), nullable=False), sa.Column("attempt", sa.Integer, nullable=False, server_default="1"), sa.Column("replay_of", sa.Integer), sa.Column("filename", sa.String(256)), sa.Column("sha256", sa.String(64), nullable=False), sa.Column("status", sa.String(16), nullable=False), sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id")), sa.Column("created_at", sa.DateTime), sa.Column("rows_read", sa.Integer, server_default="0"), sa.Column("rows_applied", sa.Integer, server_default="0"), sa.Column("result", sa.JSON), sa.Column("cancelled_by", sa.Integer, sa.ForeignKey("users.id")), sa.Column("cancelled_at", sa.DateTime), sa.Column("cancellation_reason", sa.Text))
    if context.get_context().dialect.name != "sqlite":
        op.create_foreign_key("fk_daily_consumption_import_run", "daily_consumptions", "import_runs", ["import_run_id"], ["id"])
    if context.get_context().dialect.name != "sqlite":
        op.create_foreign_key("fk_fingerprint_active_import", "import_fingerprints", "import_runs", ["active_import_id"], ["id"])
    op.create_table("import_changes", sa.Column("id", sa.Integer, primary_key=True), sa.Column("import_run_id", sa.Integer, sa.ForeignKey("import_runs.id"), nullable=False), sa.Column("entity_type", sa.String(64), nullable=False), sa.Column("entity_id", sa.Integer, nullable=False), sa.Column("operation", sa.String(32), nullable=False), sa.Column("before_value", sa.JSON), sa.Column("after_value", sa.JSON), sa.Column("sequence", sa.Integer, nullable=False), sa.Column("version", sa.Integer))
    op.create_table("consumption_allocations", sa.Column("id", sa.Integer, primary_key=True), sa.Column("import_run_id", sa.Integer, sa.ForeignKey("import_runs.id")), sa.Column("consumption_id", sa.Integer, sa.ForeignKey("daily_consumptions.id"), nullable=False), sa.Column("batch_id", sa.Integer, sa.ForeignKey("batches.id"), nullable=False), sa.Column("quantity", sa.Float, nullable=False), sa.Column("batch_before", sa.JSON), sa.Column("batch_after", sa.JSON))
    op.create_table("audit_logs", sa.Column("id", sa.Integer, primary_key=True), sa.Column("subject_id", sa.Integer, sa.ForeignKey("users.id")), sa.Column("subject_role", sa.String(32)), sa.Column("site_id", sa.Integer, sa.ForeignKey("sites.id")), sa.Column("action", sa.String(64), nullable=False), sa.Column("entity_type", sa.String(64), nullable=False), sa.Column("entity_id", sa.Integer), sa.Column("before_value", sa.JSON), sa.Column("after_value", sa.JSON), sa.Column("request_context", sa.JSON), sa.Column("import_run_id", sa.Integer, sa.ForeignKey("import_runs.id")), sa.Column("notification_id", sa.Integer, sa.ForeignKey("notification_logs.id")), sa.Column("created_at", sa.DateTime))
    op.add_column("notification_logs", sa.Column("period_key", sa.String(32), nullable=True))
    op.add_column("notification_logs", sa.Column("status", sa.String(16), nullable=False, server_default="sent"))
    op.add_column("notification_logs", sa.Column("reason", sa.Text, nullable=True))
    op.create_index("uq_notification_period", "notification_logs", ["site_id", "notification_type", "period_key"], unique=True)
    op.create_table("notification_recipient_logs", sa.Column("id", sa.Integer, primary_key=True), sa.Column("notification_id", sa.Integer, sa.ForeignKey("notification_logs.id"), nullable=False), sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True), sa.Column("status", sa.String(16), nullable=False), sa.Column("reason", sa.Text, nullable=True), sa.Column("sent_at", sa.DateTime))

def downgrade():
    if context.get_context().dialect.name != "sqlite":
        op.drop_constraint("fk_daily_consumption_import_run", "daily_consumptions", type_="foreignkey")
    op.drop_table("notification_recipient_logs")
    for table in ("audit_logs", "consumption_allocations", "import_changes", "import_runs", "import_fingerprints", "daily_financial_expenses"):
        op.drop_table(table)
    op.drop_index("uq_notification_period", table_name="notification_logs")
    op.drop_column("notification_logs", "reason")
    op.drop_column("notification_logs", "status")
    op.drop_column("notification_logs", "period_key")
    op.drop_column("daily_consumptions", "is_cancelled")
    op.drop_column("daily_consumptions", "import_run_id")
    op.drop_index("uq_batch_site_product_upd_expiry", table_name="batches")
    op.drop_column("batches", "status")
    op.drop_column("batches", "upd_number")
