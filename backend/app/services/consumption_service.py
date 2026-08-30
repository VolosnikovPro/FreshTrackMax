"""
Consumption service for FreshTrack.

Implements FEFO (First-Expired-First-Out) write-off logic:
- When writing off consumption, deduct from batches with nearest expiry date first
- When a batch is exhausted, move to the next one by expiry date
- Prevent negative stock
- Archive zero-quantity batches instead of deleting
"""
import datetime
from dataclasses import dataclass
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.models.batch import Batch
from app.models.product import Product
from app.models.consumption import DailyConsumption
from app.models.user import User


@dataclass
class WriteOffResult:
    """Result of a write-off operation."""
    success: bool
    consumed_from_batches: List[dict]  # List of {batch_id, quantity_written_off}
    errors: List[str]
    remaining_quantity: float = 0.0


@dataclass
class StockCheckResult:
    """Result of stock availability check."""
    available: float
    required: float
    sufficient: bool
    batches: List[dict]  # List of {batch_id, quantity, expiry_date}


def fefo_batches_statement(site_id: int, product_id: int):
    """Build the locked FEFO query used by stock-changing operations."""
    return (
        select(Batch)
        .where(
            Batch.site_id == site_id,
            Batch.product_id == product_id,
            Batch.status == "active",
            Batch.quantity > 0,
        )
        .order_by(Batch.expiry_date.asc(), Batch.id.asc())
        .with_for_update()
    )


async def check_stock_availability(
    db: AsyncSession,
    site_id: int,
    product_id: int,
    required_quantity: float,
) -> StockCheckResult:
    """
    Check if sufficient stock is available across all batches for a product.

    Returns StockCheckResult with available quantity and list of batches.
    """
    # Get all active batches for this product at this site, ordered by expiry date (FEFO)
    result = await db.execute(fefo_batches_statement(site_id, product_id))
    batches = result.scalars().all()

    total_available = sum(b.quantity for b in batches)
    batch_info = [
        {
            "batch_id": b.id,
            "quantity": b.quantity,
            "expiry_date": b.expiry_date.isoformat() if b.expiry_date else None,
            "batch_number": b.batch_number,
        }
        for b in batches
    ]

    return StockCheckResult(
        available=total_available,
        required=required_quantity,
        sufficient=total_available >= required_quantity,
        batches=batch_info
    )


async def write_off_consumption_fefo(
    db: AsyncSession,
    site_id: int,
    product_id: int,
    quantity_to_write_off: float,
    consumption_id: Optional[int] = None,
    notes: str = "",
) -> WriteOffResult:
    """
    Write off consumption using FEFO (First-Expired-First-Out) logic.

    Deducts from batches with nearest expiry date first.
    When a batch is exhausted, moves to the next one.
    Archives zero-quantity batches.
    Prevents negative stock.
    """
    errors = []
    consumed_from_batches = []
    remaining = quantity_to_write_off

    # Get all active batches for this product at this site, ordered by expiry date (FEFO)
    result = await db.execute(
        select(Batch).where(
            Batch.site_id == site_id,
            Batch.product_id == product_id,
            Batch.quantity > 0
        ).order_by(Batch.expiry_date.asc())
    )
    batches = result.scalars().all()

    if not batches:
        errors.append(f"Нет доступных партий для продукта ID {product_id} на объекте ID {site_id}")
        return WriteOffResult(
            success=False,
            consumed_from_batches=[],
            errors=errors,
            remaining_quantity=quantity_to_write_off
        )

    total_available = sum(b.quantity for b in batches)
    if total_available < quantity_to_write_off:
        errors.append(
            f"Недостаточно остатков для списания: требуется {quantity_to_write_off}, "
            f"доступно {total_available} (продукт ID {product_id}, объект ID {site_id})"
        )
        return WriteOffResult(
            success=False,
            consumed_from_batches=[],
            errors=errors,
            remaining_quantity=quantity_to_write_off - total_available
        )

    # FEFO: consume from batches with nearest expiry first
    for batch in batches:
        if remaining <= 0:
            break

        if batch.quantity <= 0:
            continue

        write_off_qty = min(batch.quantity, remaining)
        batch.quantity -= write_off_qty
        remaining -= write_off_qty

        consumed_from_batches.append({
            "batch_id": batch.id,
            "quantity_written_off": write_off_qty,
            "remaining_quantity": batch.quantity,
            "expiry_date": batch.expiry_date.isoformat() if batch.expiry_date else None,
            "batch_number": batch.batch_number,
        })

        # If batch is now zero, archive it (don't delete)
        if batch.quantity <= 0:
            batch.quantity = 0
            batch.status = "archived"

    if remaining > 0:
        # This shouldn't happen if we checked total_available first
        errors.append(f"Неожиданная ошибка: остаток {remaining} после списания всех партий")
        return WriteOffResult(
            success=False,
            consumed_from_batches=consumed_from_batches,
            errors=errors,
            remaining_quantity=remaining
        )

    # If we have a consumption_id, update the consumption record with notes about batches
    if consumption_id:
        result = await db.execute(
            select(DailyConsumption).where(DailyConsumption.id == consumption_id)
        )
        consumption = result.scalar_one_or_none()
        if consumption:
            batch_details = "; ".join([
                f"Партия {b['batch_number'] or b['batch_id']}: {b['quantity_written_off']} {b['expiry_date']}"
                for b in consumed_from_batches
            ])
            if notes:
                consumption.notes = f"{notes}\nСписание FEFO: {batch_details}"
            else:
                consumption.notes = f"Списание FEFO: {batch_details}"

    await db.flush()

    return WriteOffResult(
        success=True,
        consumed_from_batches=consumed_from_batches,
        errors=[],
        remaining_quantity=0.0
    )


async def process_daily_consumption_import(
    db: AsyncSession,
    site_id: int,
    product_id: int,
    date: datetime.date,
    quantity_used: float,
    unit: str,
    entered_by: Optional[int] = None,
    notes: Optional[str] = None,
    import_run_id: Optional[int] = None,
) -> WriteOffResult:
    """
    Process a daily consumption entry with FEFO write-off.

    Creates the consumption record and performs the write-off atomically.
    """
    # Create consumption record
    consumption = DailyConsumption(
        site_id=site_id,
        product_id=product_id,
        date=date,
        quantity_used=quantity_used,
        unit=unit,
        entered_by=entered_by,
        notes=notes,
        import_run_id=import_run_id,
    )
    db.add(consumption)
    await db.flush()  # Get the ID

    # Perform FEFO write-off
    result = await write_off_consumption_fefo(
        db=db,
        site_id=site_id,
        product_id=product_id,
        quantity_to_write_off=quantity_used,
        consumption_id=consumption.id,
        notes=notes or "",
    )

    if not result.success:
        # Rollback: delete the consumption record
        await db.delete(consumption)

    return result


async def get_batches_fefo_order(
    db: AsyncSession,
    site_id: int,
    product_id: int,
) -> List[Batch]:
    """
    Get all active batches for a product ordered by expiry date (FEFO).

    Useful for displaying stock levels in FEFO order.
    """
    result = await db.execute(
        select(Batch).where(
            Batch.site_id == site_id,
            Batch.product_id == product_id,
            Batch.quantity > 0
        ).order_by(Batch.expiry_date.asc())
    )
    return result.scalars().all()


async def get_archived_batches(
    db: AsyncSession,
    site_id: int,
    product_id: Optional[int] = None,
) -> List[Batch]:
    """
    Get all archived (zero-quantity) batches for a site/product.

    These are batches with quantity == 0 that are kept for history/audit.
    """
    query = select(Batch).where(
        Batch.site_id == site_id,
        Batch.quantity == 0
    )
    if product_id:
        query = query.where(Batch.product_id == product_id)

    result = await db.execute(query.order_by(Batch.expiry_date.desc()))
    return result.scalars().all()
