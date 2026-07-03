from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import datetime
from app.db.database import get_db
from app.models.batch import Batch
from app.models.product import Product
from app.models.consumption import RawMaterialCost, DailyConsumption, DailyHeadcount
from app.models.user import User, UserRole
from app.schemas import AdminSummary, UserCreate, UserOut, UserUpdate
from app.core.security import require_roles, get_current_user, hash_password
from app.core.config import settings
from fastapi import HTTPException
from typing import List

router = APIRouter()
_admin = require_roles(UserRole.admin)
_admin_or_manager = require_roles(UserRole.admin, UserRole.manager)


@router.get("/summary", response_model=AdminSummary)
async def admin_summary(
    db: AsyncSession = Depends(get_db),
    _: object = Depends(_admin_or_manager),
):
    today = datetime.date.today()
    urgent_threshold = today + datetime.timedelta(days=settings.EXPIRY_URGENT_THRESHOLD)
    planned_threshold = today + datetime.timedelta(days=settings.EXPIRY_PLANNED_THRESHOLD)

    total_products = (await db.execute(
        select(func.count()).select_from(Product).where(Product.is_active == True)
    )).scalar_one()

    total_batches = (await db.execute(
        select(func.count()).select_from(Batch)
    )).scalar_one()

    expiring_urgent = (await db.execute(
        select(func.count()).select_from(Batch).where(Batch.expiry_date <= urgent_threshold)
    )).scalar_one()

    expiring_planned = (await db.execute(
        select(func.count()).select_from(Batch).where(Batch.expiry_date <= planned_threshold)
    )).scalar_one()

    products_with_cost = (await db.execute(
        select(func.count(func.distinct(RawMaterialCost.product_id)))
    )).scalar_one()

    today_hc = (await db.execute(
        select(DailyHeadcount).where(DailyHeadcount.date == today)
    )).scalar_one_or_none()

    today_consumption = (await db.execute(
        select(func.count()).select_from(DailyConsumption).where(DailyConsumption.date == today)
    )).scalar_one()

    return AdminSummary(
        total_products=total_products,
        total_batches=total_batches,
        expiring_soon_urgent=expiring_urgent,
        expiring_soon_planned=expiring_planned,
        total_products_with_cost=products_with_cost,
        today_headcount=today_hc.count if today_hc else None,
        today_consumption_entries=today_consumption,
    )


# ─── User management (admin only) ────────────────────────────────────────────

@router.get("/users", response_model=List[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: object = Depends(_admin),
):
    result = await db.execute(select(User).order_by(User.username))
    return result.scalars().all()


@router.post("/users", response_model=UserOut, status_code=201)
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(_admin),
):
    user = User(
        username=data.username,
        display_name=data.display_name,
        role=data.role,
        max_user_id=data.max_user_id,
        hashed_password=hash_password(data.password) if data.password else None,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.put("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(_admin),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    for f, v in data.model_dump(exclude_unset=True).items():
        if f == "password" and v is not None:
            setattr(user, "hashed_password", hash_password(v))
        else:
            setattr(user, f, v)
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db), _: object = Depends(_admin)):
    await db.delete(await db.get(User, user_id))
    await db.commit()


@router.get("/me", response_model=UserOut)
async def me(current_user=Depends(get_current_user)):
    return current_user
