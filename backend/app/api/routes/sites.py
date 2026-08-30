from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.db.database import get_db
from app.models.site import Site
from app.schemas import SiteCreate, SiteUpdate, SiteOut
from app.core.security import get_current_user, require_roles
from app.models.user import UserRole, User

router = APIRouter()
_admin = require_roles(UserRole.superadmin)
_admin_or_manager = require_roles(UserRole.superadmin, UserRole.admin)


def _get_site_id(user: User) -> int:
    """Get site_id from user, defaulting to 1 if not set (for backward compatibility)."""
    return user.site_id or 1


@router.get("/", response_model=List[SiteOut])
async def list_sites(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    site_id = _get_site_id(current_user)
    q = select(Site)
    if current_user.role in (UserRole.superadmin, UserRole.admin):
        if active_only:
            q = q.where(Site.is_active == True)
    else:
        # Non-admin users only see their own site
        q = q.where(Site.id == site_id)
    result = await db.execute(q.order_by(Site.name))
    return result.scalars().all()


@router.get("/{site_id}", response_model=SiteOut)
async def get_site(
    site_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_site_id = _get_site_id(current_user)
    if current_user.role not in (UserRole.superadmin, UserRole.admin) and site_id != user_site_id:
        raise HTTPException(403, "Access denied")
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(404, "Site not found")
    return site


@router.post("/", response_model=SiteOut, status_code=201)
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


@router.put("/{site_id}", response_model=SiteOut)
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


@router.delete("/{site_id}", status_code=204)
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
