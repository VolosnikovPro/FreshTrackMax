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
from app.models.user import UserRole
from app.services.import_service import (
    import_from_bytes,
    import_from_google_sheets,
    ImportResult,
)

router = APIRouter()
_writer = require_roles(UserRole.admin, UserRole.manager)

IMPORT_TYPES = {
    "risk_report": "Риск-Отчет (продукты + партии + сроки годности)",
    "cost_sheet":  "Себестоимость расхода сырья (цены + остатки)",
}


class ImportResultOut(BaseModel):
    imported: int
    updated: int
    skipped: int
    errors: list[str]
    import_type: str
    source: str


class SheetsImportRequest(BaseModel):
    url_or_id: str
    import_type: str = "risk_report"
    sheet_name: str = ""


def _result_out(result: ImportResult, import_type: str, source: str) -> ImportResultOut:
    return ImportResultOut(
        imported=result.imported,
        updated=result.updated,
        skipped=result.skipped,
        errors=result.errors,
        import_type=IMPORT_TYPES.get(import_type, import_type),
        source=source,
    )


@router.post("/import/file", response_model=ImportResultOut)
async def import_from_file(
    import_type: str = "risk_report",
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(_writer),
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

    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(400, "Принимаются только файлы .xlsx / .xlsm")

    content = await file.read()
    if len(content) > 20 * 1024 * 1024:  # 20 MB guard
        raise HTTPException(413, "Файл слишком большой (макс. 20 МБ)")

    result = await import_from_bytes(
        db, content, import_type, updated_by=current_user.id
    )
    await db.commit()
    return _result_out(result, import_type, source=file.filename)


@router.post("/import/sheets", response_model=ImportResultOut)
async def import_from_sheets(
    body: SheetsImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(_writer),
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

    result = await import_from_google_sheets(
        db,
        url_or_id=body.url_or_id,
        import_type=body.import_type,
        sheet_name=body.sheet_name,
        updated_by=current_user.id,
    )
    await db.commit()
    return _result_out(result, body.import_type, source=body.url_or_id)


@router.get("/import/types")
async def list_import_types(_=Depends(get_current_user)):
    """List supported import types with descriptions."""
    return [{"key": k, "label": v} for k, v in IMPORT_TYPES.items()]