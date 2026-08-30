"""Database-idempotent notification scheduling primitives."""
import asyncio
import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.routes.notifications import trigger_notifications
from app.core.config import settings
from app.db.database import AsyncSessionLocal
from app.models.site import Site


async def run_daily_urgent(db: AsyncSession, site_id: int) -> object:
    period = datetime.date.today().isoformat()
    return await trigger_notifications(db, settings.EXPIRY_URGENT_THRESHOLD, "⚠️ СРОЧНО", site_id, period_key=period)


async def run_weekly_planned(db: AsyncSession, site_id: int) -> object:
    today = datetime.date.today()
    period = f"{today.isocalendar().year}-W{today.isocalendar().week:02d}"
    return await trigger_notifications(db, settings.EXPIRY_PLANNED_THRESHOLD, "📋 Плановое уведомление", site_id, period_key=period)


def _is_planned_day(today: datetime.date) -> bool:
    weekdays = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6,
    }
    return today.weekday() == weekdays.get(settings.NOTIFICATION_BASE_DAY.lower(), 6)


async def run_due_notifications(now: datetime.datetime | None = None) -> None:
    """Run the scheduled notifications once when the configured minute is reached."""
    now = now or datetime.datetime.now()
    if now.strftime("%H:%M") != settings.NOTIFICATION_TIME:
        return

    async with AsyncSessionLocal() as db:
        sites = (await db.execute(select(Site.id).where(Site.is_active == True))).scalars().all()
        for site_id in sites:
            await run_daily_urgent(db, site_id)
            if _is_planned_day(now.date()):
                await run_weekly_planned(db, site_id)


async def notification_scheduler_loop() -> None:
    """Keep scheduler wiring small; database period keys prevent duplicate sends."""
    while True:
        try:
            await run_due_notifications()
        except Exception:
            # A failed site must not terminate all future scheduled runs.
            pass
        await asyncio.sleep(60)
