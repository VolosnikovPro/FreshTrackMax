"""Immutable import and audit history records."""
import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base


class ImportFingerprint(Base):
    __tablename__ = "import_fingerprints"
    __table_args__ = (UniqueConstraint("site_id", "import_type", "sha256", name="uq_import_fingerprint"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    import_type: Mapped[str] = mapped_column(String(64), index=True)
    sha256: Mapped[str] = mapped_column(String(64))
    active_import_id: Mapped[int | None] = mapped_column(ForeignKey("import_runs.id", use_alter=True, name="fk_fingerprint_active_import"), nullable=True)


class ImportRun(Base):
    __tablename__ = "import_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    fingerprint_id: Mapped[int | None] = mapped_column(ForeignKey("import_fingerprints.id"), nullable=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    import_type: Mapped[str] = mapped_column(String(64), index=True)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    replay_of: Mapped[int | None] = mapped_column(ForeignKey("import_runs.id"), nullable=True)
    filename: Mapped[str | None] = mapped_column(String(256), nullable=True)
    sha256: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="processing", index=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=__import__('sqlalchemy').func.now())
    rows_read: Mapped[int] = mapped_column(Integer, default=0)
    rows_applied: Mapped[int] = mapped_column(Integer, default=0)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    cancelled_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    cancelled_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class ImportChange(Base):
    __tablename__ = "import_changes"
    id: Mapped[int] = mapped_column(primary_key=True)
    import_run_id: Mapped[int] = mapped_column(ForeignKey("import_runs.id"), index=True)
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[int] = mapped_column(Integer)
    operation: Mapped[str] = mapped_column(String(32))
    before_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    sequence: Mapped[int] = mapped_column(Integer)
    version: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ConsumptionAllocation(Base):
    __tablename__ = "consumption_allocations"
    id: Mapped[int] = mapped_column(primary_key=True)
    import_run_id: Mapped[int | None] = mapped_column(ForeignKey("import_runs.id"), nullable=True, index=True)
    consumption_id: Mapped[int] = mapped_column(ForeignKey("daily_consumptions.id"), index=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id"), index=True)
    quantity: Mapped[float] = mapped_column()
    batch_before: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    batch_after: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    subject_role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    site_id: Mapped[int | None] = mapped_column(ForeignKey("sites.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    before_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    request_context: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    import_run_id: Mapped[int | None] = mapped_column(ForeignKey("import_runs.id"), nullable=True)
    notification_id: Mapped[int | None] = mapped_column(ForeignKey("notification_logs.id"), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=__import__('sqlalchemy').func.now(), index=True)
