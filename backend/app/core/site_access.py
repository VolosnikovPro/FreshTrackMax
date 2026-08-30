"""Single, auditable resolution of a request's effective object."""
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.site import Site
from app.models.user import User, UserRole


ADMINISTRATIVE_SITE_ROLES = {UserRole.superadmin, UserRole.admin}


async def resolve_site_id(
    db: AsyncSession,
    user: User,
    requested_site_id: Optional[int] = None,
) -> int:
    """Return the accessible active site or raise a structured HTTP error.

    Only the two administrative roles can select another object.  A supplied
    foreign site for every other role is an authorization failure rather than
    an implicit fallback to the user's site.
    """
    if user.site_id is None:
        raise HTTPException(403, detail={"code": "SITE_REQUIRED", "message": "Не назначен объект пользователя"})

    if requested_site_id is not None and requested_site_id != user.site_id:
        if user.role not in ADMINISTRATIVE_SITE_ROLES:
            raise HTTPException(403, detail={"code": "SITE_ACCESS_DENIED", "message": "Нет доступа к выбранному объекту"})
        effective_site_id = requested_site_id
    else:
        effective_site_id = requested_site_id or user.site_id

    site = await db.get(Site, effective_site_id)
    if site is None:
        raise HTTPException(404, detail={"code": "SITE_NOT_FOUND", "message": "Объект не найден"})
    if not site.is_active:
        raise HTTPException(409, detail={"code": "SITE_INACTIVE", "message": "Объект отключен"})
    return effective_site_id
