"""
Notification service for MAX messenger.

MVP implementation:
- Sends messages via MAX Bot API (placeholder HTTP call)
- Triggered manually or by scheduler
- No delivery log in MVP
"""
import datetime
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List
from app.db.database import get_db
from app.models.batch import Batch
from app.models.user import User, UserRole
from app.models.site import Site
from app.schemas import NotificationTriggerResponse
from app.core.security import require_roles
from app.core.config import settings

router = APIRouter()
_admin_manager = require_roles(UserRole.admin, UserRole.manager)


def _get_site_id(user: User) -> int:
    """Get site_id from user, defaulting to 1 if not set (for backward compatibility)."""
    return user.site_id or 1


NOTIFICATION_ROLES = {UserRole.admin, UserRole.manager, UserRole.storekeeper}


async def _send_max_message(max_user_id: str, text: str) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"http://max-bot/send",
                params={"user_id": max_user_id, "text": text},
            )
            return resp.status_code == 200
    except Exception as e:
        print(f"MAX send error: {e}")
        return False


def _format_batch_list(batches: List[Batch], title: str) -> str:
    lines = [f"🔔 {title}\n"]
    for b in batches:
        lines.append(
            f"• {b.product.name} | {b.quantity} {b.unit} | "
            f"Срок: {b.expiry_date.strftime('%d.%m.%Y')} ({b.days_until_expiry} д.)"
        )
    return "\n".join(lines)


async def trigger_notifications(
    db: AsyncSession,
    threshold_days: int,
    title: str,
    site_id: int,
) -> NotificationTriggerResponse:
    threshold = datetime.date.today() + datetime.timedelta(days=threshold_days)
    result = await db.execute(
        select(Batch).options(selectinload(Batch.product))
        .where(
            Batch.site_id == site_id,
            Batch.quantity > 0,
            Batch.expiry_date <= threshold
        )
        .order_by(Batch.expiry_date)
    )
    batches = result.scalars().all()

    if not batches:
        return NotificationTriggerResponse(sent=0, recipients=[], products_included=0)

    message = _format_batch_list(batches, title)

    users_result = await db.execute(
        select(User).where(
            User.site_id == site_id,
            User.role.in_(NOTIFICATION_ROLES),
            User.is_active == True,
        )
    )
    users = users_result.scalars().all()

    sent_count = 0
    recipients = []
    for user in users:
        ok = await _send_max_message(str(user.max_user_id), message)
        if ok:
            sent_count += 1
            recipients.append(user.display_name or user.username)

    return NotificationTriggerResponse(
        sent=sent_count,
        recipients=recipients,
        products_included=len(batches),
    )


@router.post("/trigger/urgent", response_model=NotificationTriggerResponse)
async def trigger_urgent(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_admin_manager),
):
    """Manually trigger urgent notifications (< 16 days) for current user's site."""
    site_id = _get_site_id(current_user)
    return await trigger_notifications(
        db,
        settings.EXPIRY_URGENT_THRESHOLD,
        f"⚠️ СРОЧНО: Истекает срок годности (менее {settings.EXPIRY_URGENT_THRESHOLD} дней)",
        site_id,
    )


@router.post("/trigger/planned", response_model=NotificationTriggerResponse)
async def trigger_planned(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_admin_manager),
):
    """Manually trigger planned notifications (< 46 days) for current user's site."""
    site_id = _get_site_id(current_user)
    return await trigger_notifications(
        db,
        settings.EXPIRY_PLANNED_THRESHOLD,
        f"📋 Плановое уведомление: Истекает срок годности (менее {settings.EXPIRY_PLANNED_THRESHOLD} дней)",
        site_id,
    )


@router.get("/config")
async def get_config(_: object = Depends(_admin_manager)):
    return {
        "urgent_threshold_days": settings.EXPIRY_URGENT_THRESHOLD,
        "planned_threshold_days": settings.EXPIRY_PLANNED_THRESHOLD,
        "notification_time": settings.NOTIFICATION_TIME,
        "base_day": settings.NOTIFICATION_BASE_DAY,
        "max_per_week": settings.NOTIFICATION_MAX_PER_WEEK,
    }