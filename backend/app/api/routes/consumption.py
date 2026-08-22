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
from app.services.consumption_service import (
    process_daily_consumption_import,
    check_stock_availability,
    WriteOffResult,
)

router = APIRouter()
_writer = require_roles(UserRole.admin, UserRole.manager, UserRole.nutrition_manager)


def _get_site_id(user: User, request_site_id: Optional[int] = None) -> int:
    """Resolve the effective site_id.

    Admin/manager may pass `request_site_id` to view another site's data
    (e.g. via the frontend site switcher). Other roles are always scoped to
    their own `user.site_id`.
    """
    if request_site_id is not None and user.role in (UserRole.admin, UserRole.manager):
        return request_site_id
    return user.site_id or 1


def _enrich(c: DailyConsumption) -> ConsumptionOut:
    out = ConsumptionOut.model_validate(c)
    out.product_name = c.product.name if c.product else ""
    return out


@router.get("/", response_model=List[ConsumptionOut])
async def list_consumption(
    date: Optional[datetime.date] = None,
    product_id: Optional[int] = None,
    site_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    site_id = _get_site_id(current_user, site_id)
    q = select(DailyConsumption).options(selectinload(DailyConsumption.product)).where(
        DailyConsumption.site_id == site_id
    )
    if date:
        q = q.where(DailyConsumption.date == date)
    if product_id:
        q = q.where(DailyConsumption.product_id == product_id)
    result = await db.execute(q.order_by(DailyConsumption.date.desc()))
    return [_enrich(c) for c in result.scalars().all()]


@router.get("/stock-check/{product_id}", response_model=dict)
async def check_stock(
    product_id: int,
    quantity: float,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check if sufficient stock is available for a product (FEFO)."""
    site_id = _get_site_id(current_user)
    result = await check_stock_availability(db, site_id, product_id, quantity)
    return {
        "available": result.available,
        "required": result.required,
        "sufficient": result.sufficient,
        "batches": result.batches,
    }


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

    # Use FEFO write-off service
    result = await process_daily_consumption_import(
        db=db,
        site_id=site_id,
        product_id=data.product_id,
        date=data.date,
        quantity_used=data.quantity_used,
        unit=data.unit,
        entered_by=current_user.id,
        notes=data.notes,
    )

    if not result.success:
        await db.rollback()
        error_msg = "; ".join(result.errors)
        raise HTTPException(400, f"Ошибка списания: {error_msg}")

    await db.commit()

    # Return the created consumption entry
    result_q = await db.execute(
        select(DailyConsumption).options(selectinload(DailyConsumption.product))
        .where(DailyConsumption.site_id == site_id)
        .order_by(DailyConsumption.created_at.desc())
        .limit(1)
    )
    entry = result_q.scalar_one()
    return _enrich(entry)


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