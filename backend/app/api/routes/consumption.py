from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
import datetime
from app.db.database import get_db
from app.models.consumption import DailyConsumption
from app.models.product import Product
from app.schemas import ConsumptionCreate, ConsumptionUpdate, ConsumptionOut
from app.core.security import get_current_user, require_roles
from app.models.user import UserRole, User

router = APIRouter()
_writer = require_roles(UserRole.admin, UserRole.manager, UserRole.nutrition_manager)


def _get_site_id(user: User) -> int:
    """Get site_id from user, defaulting to 1 if not set (for backward compatibility)."""
    return user.site_id or 1


def _enrich(c: DailyConsumption) -> ConsumptionOut:
    out = ConsumptionOut.model_validate(c)
    out.product_name = c.product.name if c.product else ""
    return out


@router.get("/", response_model=List[ConsumptionOut])
async def list_consumption(
    date: Optional[datetime.date] = None,
    product_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    site_id = _get_site_id(current_user)
    q = select(DailyConsumption).options(selectinload(DailyConsumption.product)).where(
        DailyConsumption.site_id == site_id
    )
    if date:
        q = q.where(DailyConsumption.date == date)
    if product_id:
        q = q.where(DailyConsumption.product_id == product_id)
    result = await db.execute(q.order_by(DailyConsumption.date.desc()))
    return [_enrich(c) for c in result.scalars().all()]


@router.post("/", response_model=ConsumptionOut, status_code=201)
async def create_consumption(
    data: ConsumptionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_writer),
):
    site_id = data.site_id or _get_site_id(current_user)
    product = await db.get(Product, data.product_id)
    if not product or product.site_id != site_id:
        raise HTTPException(404, "Product not found")
    entry = DailyConsumption(
        **data.model_dump(),
        site_id=site_id,
        entered_by=current_user.id
    )
    db.add(entry)
    await db.commit()
    result = await db.execute(
        select(DailyConsumption).options(selectinload(DailyConsumption.product))
        .where(DailyConsumption.id == entry.id)
    )
    return _enrich(result.scalar_one())


@router.put("/{entry_id}", response_model=ConsumptionOut)
async def update_consumption(
    entry_id: int,
    data: ConsumptionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_writer),
):
    site_id = _get_site_id(current_user)
    result = await db.execute(
        select(DailyConsumption).options(selectinload(DailyConsumption.product))
        .where(DailyConsumption.id == entry_id, DailyConsumption.site_id == site_id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(404, "Entry not found")
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(entry, f, v)
    await db.commit()
    result2 = await db.execute(
        select(DailyConsumption).options(selectinload(DailyConsumption.product))
        .where(DailyConsumption.id == entry_id)
    )
    return _enrich(result2.scalar_one())


@router.delete("/{entry_id}", status_code=204)
async def delete_consumption(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.manager)),
):
    site_id = _get_site_id(current_user)
    entry = await db.get(DailyConsumption, entry_id)
    if not entry or entry.site_id != site_id:
        raise HTTPException(404, "Entry not found")
    await db.delete(entry)
    await db.commit()