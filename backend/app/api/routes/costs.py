"""costs.py – Raw material cost routes (nutrition_manager role)"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from app.db.database import get_db
from app.models.consumption import RawMaterialCost, DailyFinancialExpense, DailyHeadcount
from app.models.product import Product
from app.schemas import CostCreate, CostUpdate, CostOut, FinancialEntryCreate, FinancialEntryOut
from app.core.security import get_current_user, require_roles
from app.models.user import UserRole, User
from app.core.site_access import resolve_site_id
from app.core.site_access import resolve_site_id
from decimal import Decimal, ROUND_HALF_UP
import datetime

router = APIRouter()
_writer = require_roles(UserRole.superadmin, UserRole.admin, UserRole.nutrition_manager)
_reader = require_roles(UserRole.superadmin, UserRole.admin, UserRole.nutrition_manager)


def _enrich(c: RawMaterialCost) -> CostOut:
    out = CostOut.model_validate(c)
    out.product_name = c.product.name if c.product else ""
    return out


@router.get("/", response_model=List[CostOut])
async def list_costs(
    product_id: Optional[int] = None,
    site_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_reader),
):
    site_id = await resolve_site_id(db, current_user, site_id)
    q = select(RawMaterialCost).options(selectinload(RawMaterialCost.product)).where(
        RawMaterialCost.site_id == site_id
    )
    if product_id:
        q = q.where(RawMaterialCost.product_id == product_id)
    result = await db.execute(q.order_by(RawMaterialCost.effective_date.desc()))
    return [_enrich(c) for c in result.scalars().all()]


@router.post("/", response_model=CostOut, status_code=201)
async def create_cost(
    data: CostCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_writer),
):
    site_id = await resolve_site_id(db, current_user, data.site_id)
    product = await db.get(Product, data.product_id)
    if not product or product.site_id != site_id:
        raise HTTPException(404, "Product not found")
    cost = RawMaterialCost(**data.model_dump(), site_id=site_id, updated_by=current_user.id)
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
    current_user: User = Depends(_writer),
):
    site_id = await resolve_site_id(db, current_user)
    result = await db.execute(
        select(RawMaterialCost).options(selectinload(RawMaterialCost.product))
        .where(RawMaterialCost.id == cost_id, RawMaterialCost.site_id == site_id)
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
    current_user: User = Depends(require_roles(UserRole.superadmin, UserRole.admin)),
):
    site_id = await resolve_site_id(db, current_user)
    cost = await db.get(RawMaterialCost, cost_id)
    if not cost or cost.site_id != site_id:
        raise HTTPException(404, "Cost entry not found")
    await db.delete(cost)
    await db.commit()


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@router.post("/financial", response_model=FinancialEntryOut, status_code=201)
async def enter_financial_expense(
    data: FinancialEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.manager)),
):
    site_id = await resolve_site_id(db, current_user, data.site_id)
    expense = (await db.execute(select(DailyFinancialExpense).where(
        DailyFinancialExpense.site_id == site_id, DailyFinancialExpense.date == data.date
    ))).scalar_one_or_none()
    if expense:
        expense.invoice_amount_net = data.invoice_amount_net
        expense.entered_by = current_user.id
    else:
        expense = DailyFinancialExpense(site_id=site_id, date=data.date,
            invoice_amount_net=data.invoice_amount_net, entered_by=current_user.id)
        db.add(expense)
    hc = (await db.execute(select(DailyHeadcount).where(
        DailyHeadcount.site_id == site_id, DailyHeadcount.date == data.date
    ))).scalar_one_or_none()
    if hc:
        hc.count = data.headcount
        hc.entered_by = current_user.id
    else:
        db.add(DailyHeadcount(site_id=site_id, date=data.date, count=data.headcount, entered_by=current_user.id))
    await db.commit()
    daily = _money(Decimal(str(data.invoice_amount_net)) / data.headcount) if data.headcount else None
    return FinancialEntryOut(date=data.date, invoice_amount_net=Decimal(str(data.invoice_amount_net)), headcount=data.headcount, daily_cost=daily)


@router.get("/financial")
async def list_financial_expenses(
    month: Optional[str] = None,
    site_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.superadmin, UserRole.admin, UserRole.manager, UserRole.nutrition_manager)),
):
    effective_site = await resolve_site_id(db, current_user, site_id)
    query = select(DailyFinancialExpense, DailyHeadcount).outerjoin(
        DailyHeadcount, (DailyHeadcount.site_id == DailyFinancialExpense.site_id) & (DailyHeadcount.date == DailyFinancialExpense.date)
    ).where(DailyFinancialExpense.site_id == effective_site)
    if month:
        start = datetime.date.fromisoformat(f"{month}-01")
        end = datetime.date(start.year + (start.month == 12), (start.month % 12) + 1, 1)
        query = query.where(DailyFinancialExpense.date >= start, DailyFinancialExpense.date < end)
    rows = (await db.execute(query.order_by(DailyFinancialExpense.date))).all()
    values = []
    for expense, hc in rows:
        count = hc.count if hc else 0
        daily = Decimal(str(expense.invoice_amount_net)) / count if count else None
        values.append({"date": expense.date, "invoice_amount_net": Decimal(str(expense.invoice_amount_net)), "headcount": count, "daily_cost": _money(daily) if daily is not None else None})
    raw = [Decimal(str(expense.invoice_amount_net)) / hc.count for expense, hc in rows if hc and hc.count]
    average = _money(sum(raw, Decimal(0)) / len(raw)) if raw else None
    return {"rows": values, "average": average}
