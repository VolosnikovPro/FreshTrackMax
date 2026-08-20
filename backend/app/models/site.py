from sqlalchemy import String, Text, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base
import datetime


class Site(Base):
    """Site/Object entity for multi-object support."""
    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)  # Short code like "ASACH"
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    users = relationship("User", back_populates="site", lazy="select")
    products = relationship("Product", back_populates="site", lazy="select")
    batches = relationship("Batch", back_populates="site", lazy="select")
    costs = relationship("RawMaterialCost", back_populates="site", lazy="select")
    consumptions = relationship("DailyConsumption", back_populates="site", lazy="select")
    headcounts = relationship("DailyHeadcount", back_populates="site", lazy="select")
    notifications = relationship("NotificationLog", back_populates="site", lazy="select")