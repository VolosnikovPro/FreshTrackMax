from sqlalchemy import Float, Date, ForeignKey, DateTime, func, Text, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base
import datetime


class RawMaterialCost(Base):
    """Manual cost per unit for a product (entered by nutrition_manager)."""
    __tablename__ = "raw_material_costs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    cost_per_unit: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(default="RUB")
    effective_date: Mapped[datetime.date] = mapped_column(Date, index=True)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    product = relationship("Product", back_populates="costs")
    site = relationship("Site", back_populates="costs", lazy="select")
    updated_by_user = relationship("User", back_populates="costs")


class DailyConsumption(Base):
    """Daily manual consumption entry for a product."""
    __tablename__ = "daily_consumptions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    date: Mapped[datetime.date] = mapped_column(Date, index=True)
    quantity_used: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(default="kg")
    entered_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    import_run_id: Mapped[int | None] = mapped_column(ForeignKey("import_runs.id"), nullable=True, index=True)
    is_cancelled: Mapped[bool] = mapped_column(default=False, index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    product = relationship("Product", back_populates="consumptions")
    site = relationship("Site", back_populates="consumptions", lazy="select")
    entered_by_user = relationship("User", back_populates="consumptions")


class DailyHeadcount(Base):
    """Daily number of people being fed (entered by manager)."""
    __tablename__ = "daily_headcounts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    date: Mapped[datetime.date] = mapped_column(Date, index=True)
    count: Mapped[int]
    entered_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    site = relationship("Site", back_populates="headcounts", lazy="select")
    entered_by_user = relationship("User", back_populates="headcounts")


class DailyFinancialExpense(Base):
    """Contractual daily invoice amount excluding VAT."""
    __tablename__ = "daily_financial_expenses"
    __table_args__ = (UniqueConstraint("site_id", "date", name="uq_financial_expense_site_date"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    date: Mapped[datetime.date] = mapped_column(Date, index=True)
    invoice_amount_net: Mapped[float] = mapped_column(Numeric(18, 4, asdecimal=True))
    entered_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    site = relationship("Site", back_populates="financial_expenses", lazy="select")
