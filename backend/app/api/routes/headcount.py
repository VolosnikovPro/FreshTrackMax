from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import datetime
from app.db.database import get_db
from app.models.consumption import DailyHeadcount
from app.schemas import HeadcountCreate, HeadcountUpdate, HeadcountOut
from app.core.security import get_current_user, require_roles
from app.models.user import UserRole, User
from app.core.site_access import resolve_site_id

router = APIRouter()
_writer = require_roles(UserRole.manager)
_reader = require_roles(UserRole.superadmin, UserRole.admin, UserRole.manager, UserRole.nutrition_manager)


@router.get("/", response_model=List[HeadcountOut])
async def list_headcounts(
    start_date: Optional[datetime.date] = None,
    end_date: Optional[datetime.date] = None,
    site_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_reader),
):
    site_id = await resolve_site_id(db, current_user, site_id)
    q = select(DailyHeadcount).where(DailyHeadcount.site_id == site_id)
    if start_date:
        q = q.where(DailyHeadcount.date >= start_date)
    if end_date:
        q = q.where(DailyHeadcount.date <= end_date)
    result = await db.execute(q.order_by(DailyHeadcount.date.desc()))
    return result.scalars().all()


@router.get("/today", response_model=Optional[HeadcountOut])
async def today_headcount(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_reader),
):
    site_id = await resolve_site_id(db, current_user)
    today = datetime.date.today()
    result = await db.execute(
        select(DailyHeadcount).where(
            DailyHeadcount.site_id == site_id,
            DailyHeadcount.date == today
        )
    )
    return result.scalar_one_or_none()


@router.post("/", response_model=HeadcountOut, status_code=201)
async def create_headcount(
    data: HeadcountCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_writer),
):
    site_id = await resolve_site_id(db, current_user, data.site_id)
    # Upsert for today
    existing = await db.execute(
        select(DailyHeadcount).where(
            DailyHeadcount.site_id == site_id,
            DailyHeadcount.date == data.date
        )
    )
    entry = existing.scalar_one_or_none()
    if entry:
        entry.count = data.count
        entry.notes = data.notes
        entry.entered_by = current_user.id
        await db.commit()
        await db.refresh(entry)
        return entry

    entry = DailyHeadcount(**data.model_dump(), site_id=site_id, entered_by=current_user.id)
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


@router.put("/{entry_id}", response_model=HeadcountOut)
async def update_headcount(
    entry_id: int,
    data: HeadcountUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_writer),
):
    site_id = await resolve_site_id(db, current_user)
    entry = await db.get(DailyHeadcount, entry_id)
    if not entry or entry.site_id != site_id:
        raise HTTPException(404, "Entry not found")
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(entry, f, v)
    await db.commit()
    await db.refresh(entry)
    return entry
