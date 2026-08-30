"""
Notification service for MAX messenger.

MVP implementation:
- Sends messages via MAX Bot API (placeholder HTTP call)
- Triggered manually or by scheduler
- Logs sent notifications to database for audit/history
"""
import datetime
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from typing import List, Optional
from app.db.database import get_db
from app.models.batch import Batch
from app.models.user import User, UserRole
from app.models.site import Site
from app.models.notification import NotificationLog, NotificationRecipientLog, NotificationType
from app.schemas import NotificationTriggerResponse, NotificationLogOut
from app.core.security import require_roles
from app.core.config import settings
from app.core.site_access import resolve_site_id

router = APIRouter()
_notification_sender = require_roles(UserRole.superadmin, UserRole.admin, UserRole.storekeeper, UserRole.manager, UserRole.nutrition_manager)
_admin_only = require_roles(UserRole.superadmin, UserRole.admin)


NOTIFICATION_ROLES = {UserRole.superadmin, UserRole.admin, UserRole.manager, UserRole.storekeeper, UserRole.nutrition_manager}


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
    triggered_by: Optional[int] = None,
    period_key: Optional[str] = None,
) -> NotificationTriggerResponse:
    threshold = datetime.date.today() + datetime.timedelta(days=threshold_days)
    result = await db.execute(
        select(Batch).options(selectinload(Batch.product))
        .where(
            Batch.site_id == site_id,
            Batch.status == "active",
            Batch.quantity > 0,
            Batch.expiry_date <= threshold,
            *([] if threshold_days == settings.EXPIRY_URGENT_THRESHOLD else [Batch.expiry_date > datetime.date.today() + datetime.timedelta(days=settings.EXPIRY_URGENT_THRESHOLD)])
        )
        .order_by(Batch.expiry_date)
    )
    batches = result.scalars().all()

    if not batches:
        return NotificationTriggerResponse(sent=0, recipients=[], products_included=0)

    message = _format_batch_list(batches, title)
    notification_type = NotificationType.urgent if threshold_days == settings.EXPIRY_URGENT_THRESHOLD else NotificationType.planned

    users_result = await db.execute(
        select(User).where(
            ((User.site_id == site_id) | (User.role.in_({UserRole.superadmin, UserRole.admin}))),
            User.role.in_(NOTIFICATION_ROLES),
            User.is_active == True,
            User.max_user_id.is_not(None),
        )
    )
    users = users_result.scalars().all()

    # Claim a scheduled period before sending. A unique DB key makes this safe
    # when several backend instances reach the same scheduled minute.
    if period_key:
        claim = NotificationLog(
            site_id=site_id,
            notification_type=notification_type,
            products_count=len(batches),
            recipients_count=len(users),
            sent_count=0,
            message_text=message,
            triggered_by=triggered_by,
            period_key=period_key,
            status="processing",
        )
        db.add(claim)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            existing = (await db.execute(select(NotificationLog).where(NotificationLog.site_id == site_id, NotificationLog.notification_type == notification_type, NotificationLog.period_key == period_key))).scalar_one()
            return NotificationTriggerResponse(sent=existing.sent_count, recipients=[], products_included=existing.products_count)
        log_entry = claim
    else:
        log_entry = NotificationLog(
            site_id=site_id,
            notification_type=notification_type,
            products_count=len(batches),
            recipients_count=len(users),
            sent_count=0,
            message_text=message,
            triggered_by=triggered_by,
            status="processing",
        )
        db.add(log_entry)
        await db.flush()

    sent_count = 0
    recipients = []
    for user in users:
        ok = await _send_max_message(str(user.max_user_id), message)
        db.add(NotificationRecipientLog(
            notification_id=log_entry.id,
            user_id=user.id,
            status="sent" if ok else "failed",
            reason=None if ok else "MAX delivery failed",
        ))
        if ok:
            sent_count += 1
            recipients.append(user.display_name or user.username)

    log_entry.sent_count = sent_count
    log_entry.status = "sent" if sent_count == len(users) else ("failed" if sent_count == 0 else "partial")
    log_entry.reason = None if sent_count == len(users) else "Часть получателей недоступна"
    await db.commit()

    return NotificationTriggerResponse(
        sent=sent_count,
        recipients=recipients,
        products_included=len(batches),
    )


@router.post("/trigger/urgent", response_model=NotificationTriggerResponse)
async def trigger_urgent(
    site_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_notification_sender),
):
    """Manually trigger urgent notifications (< 16 days) for current user's site."""
    site_id = await resolve_site_id(db, current_user, site_id)
    return await trigger_notifications(
        db,
        settings.EXPIRY_URGENT_THRESHOLD,
        f"⚠️ СРОЧНО: Истекает срок годности (менее {settings.EXPIRY_URGENT_THRESHOLD} дней)",
        site_id,
        triggered_by=current_user.id,
    )


@router.post("/trigger/planned", response_model=NotificationTriggerResponse)
async def trigger_planned(
    site_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_notification_sender),
):
    """Manually trigger planned notifications (< 46 days) for current user's site."""
    site_id = await resolve_site_id(db, current_user, site_id)
    return await trigger_notifications(
        db,
        settings.EXPIRY_PLANNED_THRESHOLD,
        f"📋 Плановое уведомление: Истекает срок годности (менее {settings.EXPIRY_PLANNED_THRESHOLD} дней)",
        site_id,
        triggered_by=current_user.id,
    )


@router.get("/logs", response_model=List[NotificationLogOut])
async def list_notification_logs(
    site_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_admin_only),
):
    """Get notification logs (admin only)."""
    query = select(NotificationLog).order_by(desc(NotificationLog.created_at)).limit(limit).offset(offset)

    effective_site_id = await resolve_site_id(db, current_user, site_id)
    query = query.where(NotificationLog.site_id == effective_site_id)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/config")
async def get_config(_: object = Depends(_notification_sender)):
    return {
        "urgent_threshold_days": settings.EXPIRY_URGENT_THRESHOLD,
        "planned_threshold_days": settings.EXPIRY_PLANNED_THRESHOLD,
        "notification_time": settings.NOTIFICATION_TIME,
        "base_day": settings.NOTIFICATION_BASE_DAY,
        "max_per_week": settings.NOTIFICATION_MAX_PER_WEEK,
    }
