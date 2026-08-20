from sqlalchemy import String, Text, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    name: Mapped[str] = mapped_column(String(256), index=True)
    sku: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    unit: Mapped[str] = mapped_column(String(32), default="kg")
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    site = relationship("Site", back_populates="products", lazy="select")
    batches = relationship("Batch", back_populates="product", lazy="select")
    costs = relationship("RawMaterialCost", back_populates="product", lazy="select")
    consumptions = relationship("DailyConsumption", back_populates="product", lazy="select")