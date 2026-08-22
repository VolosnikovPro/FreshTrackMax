from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
import datetime
from app.db.database import get_db
from app.models.batch import Batch
from app.models.product import Product
from app.schemas import BatchCreate, BatchUpdate, BatchOut
from app.core.security import get_current_user, require_roles
from app.models.user import UserRole, User
from app.core.config import settings

router = APIRouter()
_storekeeper_plus = require_roles(
    UserRole.admin, UserRole.manager,
    UserRole.storekeeper, UserRole.nutrition_manager
)


def _get_site_id(user: User, request_site_id: Optional[int] = None) -> int:
    """Resolve the effective site_id.

    Admin/manager may pass `request_site_id` to view another site's data
    (e.g. via the frontend site switcher). Other roles are always scoped to
    their own `user.site_id`.
    """
    if request_site_id is not None and user.role in (UserRole.admin, UserRole.manager):
        return request_site_id
    return user.site_id or 1


def _enrich(batch: Batch) -> BatchOut:
    out = BatchOut.model_validate(batch)
    out.product_name = batch.product.name if batch.product else ""
    out.days_until_expiry = batch.days_until_expiry
    return out


@router.get("/", response_model=List[BatchOut])
async def list_batches(
    product_id: Optional[int] = None,
    expiring_within_days: Optional[int] = None,
    include_archived: bool = False,
    filter: Optional[str] = None,
    site_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    site_id = _get_site_id(current_user, site_id)
    q = select(Batch).options(selectinload(Batch.product)).where(Batch.site_id == site_id)
    if not include_archived:
        q = q.where(Batch.quantity > 0)
    if product_id:
        q = q.where(Batch.product_id == product_id)
    if filter == "urgent":
        threshold = datetime.date.today() + datetime.timedelta(days=settings.EXPIRY_URGENT_THRESHOLD)
        q = q.where(Batch.expiry_date <= threshold)
    elif filter == "planned":
        threshold = datetime.date.today() + datetime.timedelta(days=settings.EXPIRY_PLANNED_THRESHOLD)
        q = q.where(Batch.expiry_date <= threshold)
    elif expiring_within_days is not None:
        threshold = datetime.date.today() + datetime.timedelta(days=expiring_within_days)
        q = q.where(Batch.expiry_date <= threshold)
    result = await db.execute(q.order_by(Batch.expiry_date))
    return [_enrich(b) for b in result.scalars().all()]


@router.get("/expiring/urgent", response_model=List[BatchOut])
async def expiring_urgent(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Products expiring within EXPIRY_URGENT_THRESHOLD days."""
    site_id = _get_site_id(current_user)
    threshold = datetime.date.today() + datetime.timedelta(days=settings.EXPIRY_URGENT_THRESHOLD)
    q = select(Batch).options(selectinload(Batch.product)).where(
        Batch.site_id == site_id,
        Batch.quantity > 0,
        Batch.expiry_date <= threshold
    )
    result = await db.execute(q.order_by(Batch.expiry_date))
    return [_enrich(b) for b in result.scalars().all()]


@router.get("/expiring/planned", response_model=List[BatchOut])
async def expiring_planned(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Products expiring within EXPIRY_PLANNED_THRESHOLD days."""
    site_id = _get_site_id(current_user)
    threshold = datetime.date.today() + datetime.timedelta(days=settings.EXPIRY_PLANNED_THRESHOLD)
    q = select(Batch).options(selectinload(Batch.product)).where(
        Batch.site_id == site_id,
        Batch.quantity > 0,
        Batch.expiry_date <= threshold
    )
    result = await db.execute(q.order_by(Batch.expiry_date))
    return [_enrich(b) for b in result.scalars().all()]


@router.get("/{batch_id}", response_model=BatchOut)
async def get_batch(
    batch_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    site_id = _get_site_id(current_user)
    result = await db.execute(
        select(Batch).options(selectinload(Batch.product)).where(
            Batch.id == batch_id,
            Batch.site_id == site_id
        )
    )
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(404, "Batch not found")
    return _enrich(batch)


@router.post("/", response_model=BatchOut, status_code=201)
async def create_batch(
    data: BatchCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_storekeeper_plus),
):
    site_id = data.site_id or _get_site_id(current_user)
    product = await db.get(Product, data.product_id)
    if not product or product.site_id != site_id:
        raise HTTPException(404, "Product not found")
    batch_data = data.model_dump()
    batch_data["site_id"] = site_id
    batch = Batch(**batch_data)
    db.add(batch)
    await db.commit()
    result = await db.execute(
        select(Batch).options(selectinload(Batch.product)).where(Batch.id == batch.id)
    )
    return _enrich(result.scalar_one())


@router.put("/{batch_id}", response_model=BatchOut)
async def update_batch(
    batch_id: int,
    data: BatchUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_storekeeper_plus),
):
    site_id = _get_site_id(current_user)
    result = await db.execute(
        select(Batch).options(selectinload(Batch.product)).where(
            Batch.id == batch_id,
            Batch.site_id == site_id
        )
    )
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(404, "Batch not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(batch, field, value)
    await db.commit()
    await db.refresh(batch)
    result2 = await db.execute(
        select(Batch).options(selectinload(Batch.product)).where(Batch.id == batch_id)
    )
    return _enrich(result2.scalar_one())


@router.delete("/{batch_id}", status_code=204)
async def delete_batch(
    batch_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.manager)),
):
    site_id = _get_site_id(current_user)
    batch = await db.get(Batch, batch_id)
    if not batch or batch.site_id != site_id:
        raise HTTPException(404, "Batch not found")
    await db.delete(batch)
    await db.commit()