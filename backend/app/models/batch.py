from sqlalchemy import String, Float, Date, ForeignKey, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base
import datetime


class Batch(Base):
    """A batch of a product with its own expiry date and quantity."""
    __tablename__ = "batches"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    batch_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    quantity: Mapped[float] = mapped_column(Float, default=0.0)
    unit: Mapped[str] = mapped_column(String(32), default="kg")
    expiry_date: Mapped[datetime.date] = mapped_column(Date, index=True)
    received_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    product = relationship("Product", back_populates="batches")
    site = relationship("Site", back_populates="batches", lazy="select")

    @property
    def days_until_expiry(self) -> int:
        return (self.expiry_date - datetime.date.today()).days