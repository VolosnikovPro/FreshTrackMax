from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import datetime
from app.db.database import get_db
from app.models.batch import Batch
from app.models.product import Product
from app.models.consumption import RawMaterialCost, DailyConsumption, DailyHeadcount
from app.models.user import User, UserRole
from app.models.site import Site
from app.schemas import AdminSummary, UserCreate, UserOut, UserUpdate, SiteCreate, SiteUpdate, SiteOut
from app.core.security import require_roles, get_current_user, hash_password
from app.core.config import settings
from typing import List

router = APIRouter()
_admin = require_roles(UserRole.admin)
_admin_or_manager = require_roles(UserRole.admin, UserRole.manager)


def _get_site_id(user: User) -> int:
    """Get site_id from user, defaulting to 1 if not set (for backward compatibility)."""
    return user.site_id or 1


@router.get("/summary", response_model=AdminSummary)
async def admin_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_admin_or_manager),
):
    site_id = _get_site_id(current_user)
    today = datetime.date.today()
    urgent_threshold = today + datetime.timedelta(days=settings.EXPIRY_URGENT_THRESHOLD)
    planned_threshold = today + datetime.timedelta(days=settings.EXPIRY_PLANNED_THRESHOLD)

    total_products = (await db.execute(
        select(func.count()).select_from(Product).where(
            Product.site_id == site_id,
            Product.is_active == True
        )
    )).scalar_one()

    total_batches = (await db.execute(
        select(func.count()).select_from(Batch).where(
            Batch.site_id == site_id,
            Batch.quantity > 0
        )
    )).scalar_one()

    expiring_urgent = (await db.execute(
        select(func.count()).select_from(Batch).where(
            Batch.site_id == site_id,
            Batch.quantity > 0,
            Batch.expiry_date <= urgent_threshold
        )
    )).scalar_one()

    expiring_planned = (await db.execute(
        select(func.count()).select_from(Batch).where(
            Batch.site_id == site_id,
            Batch.quantity > 0,
            Batch.expiry_date <= planned_threshold
        )
    )).scalar_one()

    products_with_cost = (await db.execute(
        select(func.count(func.distinct(RawMaterialCost.product_id)))
        .where(RawMaterialCost.site_id == site_id)
    )).scalar_one()

    today_hc = (await db.execute(
        select(DailyHeadcount).where(
            DailyHeadcount.site_id == site_id,
            DailyHeadcount.date == today
        )
    )).scalar_one_or_none()

    today_consumption = (await db.execute(
        select(func.count()).select_from(DailyConsumption).where(
            DailyConsumption.site_id == site_id,
            DailyConsumption.date == today
        )
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


# ─── Site management (admin only) ──────────────────────────────────────────────

@router.get("/sites", response_model=List[SiteOut])
async def list_sites(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_admin),
):
    result = await db.execute(select(Site).order_by(Site.name))
    return result.scalars().all()


@router.post("/sites", response_model=SiteOut, status_code=201)
async def create_site(
    data: SiteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_admin),
):
    site = Site(**data.model_dump())
    db.add(site)
    await db.commit()
    await db.refresh(site)
    return site


@router.put("/sites/{site_id}", response_model=SiteOut)
async def update_site(
    site_id: int,
    data: SiteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_admin),
):
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(404, "Site not found")
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(site, f, v)
    await db.commit()
    await db.refresh(site)
    return site


@router.delete("/sites/{site_id}", status_code=204)
async def delete_site(
    site_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_admin),
):
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(404, "Site not found")
    # Soft delete - just deactivate
    site.is_active = False
    await db.commit()


# ─── User management (admin only) ──────────────────────────────────────────────

@router.get("/users", response_model=List[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_admin),
):
    site_id = _get_site_id(current_user)
    result = await db.execute(select(User).where(User.site_id == site_id).order_by(User.username))
    return result.scalars().all()


@router.post("/users", response_model=UserOut, status_code=201)
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_admin),
):
    site_id = data.site_id or _get_site_id(current_user)
    user = User(
        username=data.username,
        display_name=data.display_name,
        role=data.role,
        max_user_id=data.max_user_id,
        hashed_password=hash_password(data.password) if data.password else None,
        site_id=site_id,
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
    current_user: User = Depends(_admin),
):
    site_id = _get_site_id(current_user)
    user = await db.get(User, user_id)
    if not user or user.site_id != site_id:
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
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(_admin)):
    site_id = _get_site_id(current_user)
    user = await db.get(User, user_id)
    if not user or user.site_id != site_id:
        raise HTTPException(404, "User not found")
    await db.delete(user)
    await db.commit()


@router.get("/me", response_model=UserOut)
async def me(current_user=Depends(get_current_user)):
    return current_user