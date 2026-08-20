from sqlalchemy import String, Boolean, BigInteger, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base
import enum


class UserRole(str, enum.Enum):
    admin = "admin"
    manager = "manager"           # Управляющий
    storekeeper = "storekeeper"   # Кладовщик
    nutrition_manager = "nutrition_manager"  # Управляющий по питанию


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    max_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str] = mapped_column(String(128), unique=True)
    display_name: Mapped[str] = mapped_column(String(256), default="")
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.storekeeper)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Password is optional — primary auth is via MAX OAuth
    hashed_password: Mapped[str | None] = mapped_column(String(256), nullable=True)

    site = relationship("Site", back_populates="users", lazy="select")
    costs = relationship("RawMaterialCost", back_populates="updated_by_user", lazy="select")
    consumptions = relationship("DailyConsumption", back_populates="entered_by_user", lazy="select")
    headcounts = relationship("DailyHeadcount", back_populates="entered_by_user", lazy="select")