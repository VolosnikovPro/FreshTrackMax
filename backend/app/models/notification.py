from sqlalchemy import String, Text, ForeignKey, DateTime, func, Enum as SAEnum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base
import datetime
import enum


class NotificationType(str, enum.Enum):
    urgent = "urgent"
    planned = "planned"


class NotificationLog(Base):
    """Log of sent notifications for audit/history."""
    __tablename__ = "notification_logs"
    __table_args__ = (UniqueConstraint("site_id", "notification_type", "period_key", name="uq_notification_period"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    notification_type: Mapped[NotificationType] = mapped_column(SAEnum(NotificationType), index=True)
    products_count: Mapped[int] = mapped_column(default=0)
    recipients_count: Mapped[int] = mapped_column(default=0)
    sent_count: Mapped[int] = mapped_column(default=0)
    message_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    triggered_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    period_key: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(16), default="sent")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    site = relationship("Site", back_populates="notifications", lazy="select")
    triggered_by_user = relationship("User", lazy="select")


class NotificationRecipientLog(Base):
    """Delivery result for one recipient of a notification run."""
    __tablename__ = "notification_recipient_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    notification_id: Mapped[int] = mapped_column(ForeignKey("notification_logs.id"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(16))
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
