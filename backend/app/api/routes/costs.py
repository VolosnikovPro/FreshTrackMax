"""costs.py – Raw material cost routes (nutrition_manager role)"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from app.db.database import get_db
from app.models.consumption import RawMaterialCost
from app.models.product import Product
from app.schemas import CostCreate, CostUpdate, CostOut
from app.core.security import get_current_user, require_roles
from app.models.user import UserRole

router = APIRouter()
_writer = require_roles(UserRole.admin, UserRole.manager, UserRole.nutrition_manager)


def _enrich(c: RawMaterialCost) -> CostOut:
    out = CostOut.model_validate(c)
    out.product_name = c.product.name if c.product else ""
    return out


@router.get("/", response_model=List[CostOut])
async def list_costs(
    product_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(get_current_user),
):
    q = select(RawMaterialCost).options(selectinload(RawMaterialCost.product))
    if product_id:
        q = q.where(RawMaterialCost.product_id == product_id)
    result = await db.execute(q.order_by(RawMaterialCost.effective_date.desc()))
    return [_enrich(c) for c in result.scalars().all()]


@router.post("/", response_model=CostOut, status_code=201)
async def create_cost(
    data: CostCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(_writer),
):
    if not await db.get(Product, data.product_id):
        raise HTTPException(404, "Product not found")
    cost = RawMaterialCost(**data.model_dump(), updated_by=current_user.id)
    db.add(cost)
    await db.commit()
    result = await db.execute(
        select(RawMaterialCost).options(selectinload(RawMaterialCost.product))
        .where(RawMaterialCost.id == cost.id)
    )
    return _enrich(result.scalar_one())


@router.put("/{cost_id}", response_model=CostOut)
async def update_cost(
    cost_id: int,
    data: CostUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(_writer),
):
    result = await db.execute(
        select(RawMaterialCost).options(selectinload(RawMaterialCost.product))
        .where(RawMaterialCost.id == cost_id)
    )
    cost = result.scalar_one_or_none()
    if not cost:
        raise HTTPException(404, "Cost entry not found")
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(cost, f, v)
    cost.updated_by = current_user.id
    await db.commit()
    result2 = await db.execute(
        select(RawMaterialCost).options(selectinload(RawMaterialCost.product))
        .where(RawMaterialCost.id == cost_id)
    )
    return _enrich(result2.scalar_one())


@router.delete("/{cost_id}", status_code=204)
async def delete_cost(
    cost_id: int,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_roles(UserRole.admin)),
):
    cost = await db.get(RawMaterialCost, cost_id)
    if not cost:
        raise HTTPException(404, "Cost entry not found")
    await db.delete(cost)
    await db.commit()
