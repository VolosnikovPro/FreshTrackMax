"""
Sheets / file import routes.

POST /api/sheets/import/file    — upload xlsx file
POST /api/sheets/import/sheets  — import from Google Sheets URL or ID
"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.user import UserRole, User
from app.models.import_history import ImportRun, ImportFingerprint, ImportChange, ConsumptionAllocation, AuditLog
from app.models.batch import Batch
from app.models.consumption import DailyConsumption
from sqlalchemy import select
import datetime
from app.services.import_service import (
    import_from_bytes,
    import_from_google_sheets,
    ImportResult,
    ImportDuplicateError,
)
from app.core.site_access import resolve_site_id

router = APIRouter()
_writer = require_roles(UserRole.superadmin, UserRole.admin, UserRole.storekeeper)


IMPORT_TYPES = {
    "risk_report": "Риск-Отчет (продукты + партии + сроки годности)",
    "cost_sheet":  "Себестоимость расхода сырья (цены + остатки)",
    "consumption_file": "Расход сырья (атомарное FEFO-списание)",
}


def import_run_for_cancel_statement(import_id: int):
    """Lock an import before reading its status and compensating its effects."""
    return select(ImportRun).where(ImportRun.id == import_id).with_for_update()


class ImportResultOut(BaseModel):
    imported: int
    updated: int
    skipped: int
    errors: list[str]
    import_type: str
    source: str
    site_id: Optional[int] = None


class SheetsImportRequest(BaseModel):
    url_or_id: str
    import_type: str = "risk_report"
    sheet_name: str = ""
    site_id: Optional[int] = None


def _result_out(result: ImportResult, import_type: str, source: str, site_id: Optional[int] = None) -> ImportResultOut:
    return ImportResultOut(
        imported=result.imported,
        updated=result.updated,
        skipped=result.skipped,
        errors=result.errors,
        import_type=IMPORT_TYPES.get(import_type, import_type),
        source=source,
        site_id=site_id,
    )


def _check_import_role(import_type: str, current_user: User) -> None:
    if import_type == "consumption_file" and current_user.role != UserRole.storekeeper:
        raise HTTPException(403, detail={"code": "ROLE_FORBIDDEN", "message": "Расходную накладную импортирует только Кладовщик"})
    if import_type == "cost_sheet" and current_user.role not in (UserRole.superadmin, UserRole.admin):
        raise HTTPException(403, detail={"code": "ROLE_FORBIDDEN", "message": "Legacy-импорт доступен только административным ролям"})


@router.post("/import/file", response_model=ImportResultOut)
async def import_from_file(
    import_type: str = "risk_report",
    site_id: Optional[int] = None,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_writer),
):
    """
    Upload an xlsx file and import its data.

    import_type:
      - risk_report  — Риск-Отчет (продукты, партии, сроки годности)
      - cost_sheet   — Себестоимость расхода сырья (цены, остатки)
    """
    if import_type not in IMPORT_TYPES:
        raise HTTPException(
            400,
            f"Недопустимый import_type. Допустимые: {list(IMPORT_TYPES.keys())}"
        )
    _check_import_role(import_type, current_user)

    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(400, "Принимаются только файлы .xlsx / .xlsm")

    content = await file.read()
    if len(content) > 20 * 1024 * 1024:  # 20 MB guard
        raise HTTPException(413, "Файл слишком большой (макс. 20 МБ)")

    site_id = await resolve_site_id(db, current_user, site_id)
    try:
        result = await import_from_bytes(db, content, import_type, site_id, updated_by=current_user.id)
    except ImportDuplicateError as duplicate:
        await db.rollback()
        raise HTTPException(409, detail={"code": "IMPORT_DUPLICATE", "message": "Этот файл уже импортирован", "first_import_id": duplicate.first_import_id})
    if result.errors:
        await db.rollback()
        raise HTTPException(400, detail={"code": "IMPORT_FAILED", "message": "Импорт отменен: исправьте ошибки файла", "errors": result.errors})
    run = (await db.execute(select(ImportRun).where(ImportRun.site_id == site_id, ImportRun.sha256 == __import__('hashlib').sha256(content).hexdigest()).order_by(ImportRun.id.desc()))).scalars().first()
    db.add(AuditLog(subject_id=current_user.id, subject_role=current_user.role.value, site_id=site_id,
                    action="import_success", entity_type="import_run", entity_id=run.id if run else None,
                    import_run_id=run.id if run else None,
                    after_value={"import_type": import_type, "sha256": __import__('hashlib').sha256(content).hexdigest()}))
    await db.commit()
    return _result_out(result, import_type, source=file.filename, site_id=site_id)


@router.post("/import/sheets", response_model=ImportResultOut)
async def import_from_sheets(
    body: SheetsImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_writer),
):
    """
    Import from a Google Sheets URL or spreadsheet ID.

    For public sheets: share as "Все, у кого есть ссылка — просмотр".
    For private sheets: configure GOOGLE_SERVICE_ACCOUNT_JSON in .env.

    Body:
      url_or_id   — full Google Sheets URL or bare spreadsheet ID
      import_type — risk_report | cost_sheet
      sheet_name  — optional sheet tab name (empty = first sheet)
    """
    if body.import_type not in IMPORT_TYPES:
        raise HTTPException(
            400,
            f"Недопустимый import_type. Допустимые: {list(IMPORT_TYPES.keys())}"
        )

    _check_import_role(body.import_type, current_user)
    site_id = await resolve_site_id(db, current_user, body.site_id)
    try:
        result = await import_from_google_sheets(
            db,
            url_or_id=body.url_or_id,
            import_type=body.import_type,
            site_id=site_id,
            sheet_name=body.sheet_name,
            updated_by=current_user.id,
        )
    except ImportDuplicateError as duplicate:
        await db.rollback()
        raise HTTPException(409, detail={"code": "IMPORT_DUPLICATE", "message": "Этот файл уже импортирован", "first_import_id": duplicate.first_import_id})
    if result.errors:
        await db.rollback()
        raise HTTPException(400, detail={"code": "IMPORT_FAILED", "message": "Импорт отменен: исправьте ошибки файла", "errors": result.errors})
    await db.commit()
    return _result_out(result, body.import_type, source=body.url_or_id, site_id=site_id)


@router.get("/import/types")
async def list_import_types(_=Depends(get_current_user)):
    """List supported import types with descriptions."""
    return [{"key": k, "label": v} for k, v in IMPORT_TYPES.items()]


@router.get("/import/history")
async def import_history(
    site_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.superadmin, UserRole.admin)),
):
    effective_site = await resolve_site_id(db, current_user, site_id)
    rows = (await db.execute(select(ImportRun).where(ImportRun.site_id == effective_site).order_by(ImportRun.created_at.desc()))).scalars().all()
    return [{"id": r.id, "site_id": r.site_id, "import_type": r.import_type, "status": r.status, "sha256": r.sha256, "created_by": r.created_by, "created_at": r.created_at} for r in rows]


@router.post("/import/{import_id}/cancel")
async def cancel_import(
    import_id: int,
    reason: str = "",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.superadmin, UserRole.admin)),
):
    run = (await db.execute(import_run_for_cancel_statement(import_id))).scalar_one_or_none()
    if not run:
        raise HTTPException(404, detail={"code": "IMPORT_NOT_FOUND", "message": "Импорт не найден"})
    await resolve_site_id(db, current_user, run.site_id)
    if run.status == "cancelled":
        return {"id": run.id, "status": run.status, "idempotent": True}
    if run.status != "success":
        raise HTTPException(409, detail={"code": "IMPORT_NOT_SUCCESS", "message": "Отменить можно только успешный импорт"})
    allocations = (await db.execute(select(ConsumptionAllocation).where(ConsumptionAllocation.import_run_id == run.id))).scalars().all()
    batch_ids = {a.batch_id for a in allocations}
    changed_batch_ids = set((await db.execute(select(ImportChange.entity_id).where(
        ImportChange.import_run_id == run.id,
        ImportChange.entity_type == "batch",
    ))).scalars().all())
    if batch_ids:
        newer = (await db.execute(select(ImportRun).join(ConsumptionAllocation, ConsumptionAllocation.import_run_id == ImportRun.id).where(
            ImportRun.id > run.id, ImportRun.status == "success", ConsumptionAllocation.batch_id.in_(batch_ids)
        ).order_by(ImportRun.id))).scalars().unique().all()
        if newer:
            raise HTTPException(409, detail={"code": "IMPORT_DEPENDENCIES", "message": "Сначала отмените более новые зависимые импорты", "dependent_import_ids": [item.id for item in newer], "recommended_order": [item.id for item in reversed(newer)] + [run.id]})
    if changed_batch_ids:
        newer_changes = (await db.execute(select(ImportRun).join(ImportChange, ImportChange.import_run_id == ImportRun.id).where(
            ImportRun.id > run.id,
            ImportRun.status == "success",
            ImportChange.entity_type == "batch",
            ImportChange.entity_id.in_(changed_batch_ids),
        ).order_by(ImportRun.id))).scalars().unique().all()
        if newer_changes:
            raise HTTPException(409, detail={"code": "IMPORT_DEPENDENCIES", "message": "Сначала отмените более новые зависимые импорты", "dependent_import_ids": [item.id for item in newer_changes], "recommended_order": [item.id for item in reversed(newer_changes)] + [run.id]})
    for allocation in reversed(allocations):
        batch = await db.get(Batch, allocation.batch_id)
        if batch:
            batch.quantity = float(batch.quantity) + float(allocation.quantity)
            batch.status = "active"
        consumption = await db.get(DailyConsumption, allocation.consumption_id)
        if consumption:
            consumption.is_cancelled = True
            consumption.notes = (consumption.notes or "") + "\nИмпорт отменен"
    changes = (await db.execute(select(ImportChange).where(ImportChange.import_run_id == run.id).order_by(ImportChange.id.desc()))).scalars().all()
    for change in changes:
        if change.entity_type == "batch":
            batch = await db.get(Batch, change.entity_id)
            if not batch:
                continue
            if change.operation == "create":
                await db.delete(batch)
            elif change.before_value:
                for field, value in change.before_value.items():
                    setattr(batch, field, value)
        elif change.entity_type == "cost":
            from app.models.consumption import RawMaterialCost
            cost = await db.get(RawMaterialCost, change.entity_id)
            if not cost:
                continue
            if change.operation == "create":
                await db.delete(cost)
            elif change.before_value:
                for field, value in change.before_value.items():
                    setattr(cost, field, value)
        elif change.entity_type == "product" and change.operation == "create":
            from app.models.product import Product
            product = await db.get(Product, change.entity_id)
            if product:
                await db.delete(product)
    run.status = "cancelled"
    run.cancelled_by = current_user.id
    run.cancelled_at = datetime.datetime.now(datetime.timezone.utc)
    run.cancellation_reason = reason or None
    db.add(AuditLog(subject_id=current_user.id, subject_role=current_user.role.value, site_id=run.site_id,
                    action="import_cancelled", entity_type="import_run", entity_id=run.id,
                    after_value={"reason": reason or None}))
    fingerprint = await db.get(ImportFingerprint, run.fingerprint_id) if run.fingerprint_id else None
    await db.commit()
    return {"id": run.id, "status": run.status, "restored_allocations": len(allocations)}
