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
from app.core.site_access import resolve_site_id
from app.services.consumption_service import (
    process_daily_consumption_import,
    check_stock_availability,
    WriteOffResult,
)

router = APIRouter()
_reader = require_roles(UserRole.superadmin, UserRole.admin, UserRole.storekeeper, UserRole.nutrition_manager)
_admin_reader = require_roles(UserRole.superadmin, UserRole.admin)


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
    current_user: User = Depends(_reader),
):
    site_id = await resolve_site_id(db, current_user, site_id)
    q = select(DailyConsumption).options(selectinload(DailyConsumption.product)).where(
        DailyConsumption.site_id == site_id, DailyConsumption.is_cancelled == False
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
    site_id = await resolve_site_id(db, current_user)
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
    current_user: User = Depends(_admin_reader),
):
    raise HTTPException(409, detail={"code": "CONSUMPTION_IMPORT_ONLY", "message": "Расход сырья фиксируется только импортом файла Кладовщика"})


@router.put("/{entry_id}", response_model=ConsumptionOut)
async def update_consumption(
    entry_id: int,
    data: ConsumptionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_admin_reader),
):
    raise HTTPException(409, detail={"code": "CONSUMPTION_IMMUTABLE", "message": "Запись расхода нельзя редактировать; отмените импорт"})


@router.delete("/{entry_id}", status_code=204)
async def delete_consumption(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_admin_reader),
):
    raise HTTPException(409, detail={"code": "CONSUMPTION_IMMUTABLE", "message": "Запись расхода нельзя удалять; отмените импорт"})
