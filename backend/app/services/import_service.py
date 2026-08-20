"""
Import service for FreshTrack MVP.

Supports two file formats:
  1. Risk Report (Риск-Отчет) — products + batches + expiry dates
     Columns: Склад | Наименование товаров | Ед. Изм. | Количество |
              Срок годности | Текущая дата | Осталось дней | Комментарии

  2. Cost/Consumption sheet (Себестоимость расхода сырья)
     Row 5 header: Код | Товар | Ед. изм. | Цена | (balance) | day1 | day2 ...
     Data starts at row 7.

Also supports Google Sheets import via public export URL or service account.
"""

from __future__ import annotations

import io
import datetime
import logging
from dataclasses import dataclass, field
from typing import Optional

import openpyxl
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.product import Product
from app.models.batch import Batch
from app.models.site import Site
from app.models.consumption import RawMaterialCost, DailyConsumption

log = logging.getLogger(__name__)

_EXCEL_EPOCH = datetime.date(1899, 12, 30)


# ─── Result container ─────────────────────────────────────────────────────────

@dataclass
class ImportResult:
    imported: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)

    def add_error(self, msg: str) -> None:
        log.warning(msg)
        if len(self.errors) < 50:
            self.errors.append(msg)
        self.skipped += 1

    def to_dict(self) -> dict:
        return {
            "imported": self.imported,
            "updated": self.updated,
            "skipped": self.skipped,
            "errors": self.errors,
        }


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _excel_serial_to_date(value) -> Optional[datetime.date]:
    """Convert Excel serial number, datetime, or date object → date. Returns None on failure."""
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    # openpyxl with data_only=True may return serial int/float
    try:
        n = int(float(str(value)))
        if 1000 < n < 100000:   # sanity range: ~1902–2173
            return _EXCEL_EPOCH + datetime.timedelta(days=n)
    except (ValueError, TypeError, OverflowError):
        pass
    return None


def _clean_str(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _clean_float(value) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if float(value) >= 0 else None
    try:
        f = float(str(value).replace(",", ".").replace("\xa0", "").replace(" ", ""))
        return f if f >= 0 else None
    except (ValueError, TypeError):
        return None


async def _get_or_create_product(
    db: AsyncSession,
    site_id: int,
    name: str,
    unit: str,
    sku: Optional[str] = None,
) -> Product:
    """Find existing product by name (case-insensitive) within site or create new."""
    name = name.strip()
    unit = unit.strip() or "шт"

    result = await db.execute(
        select(Product).where(
            Product.site_id == site_id,
            Product.name.ilike(name)
        )
    )
    product = result.scalar_one_or_none()

    if product is None:
        product = Product(site_id=site_id, name=name, unit=unit, sku=sku, is_active=True)
        db.add(product)
        await db.flush()  # assign ID within transaction

    return product


# ─── Format 1: Risk Report ────────────────────────────────────────────────────

async def import_risk_report(
    db: AsyncSession,
    wb: openpyxl.Workbook,
    updated_by: Optional[int] = None,
) -> ImportResult:
    """
    Parse Риск-Отчет xlsx.

    Header row contains: Наименование товаров | Ед. Изм. | Количество | Срок годности
    Expiry date is stored as an Excel serial date (datetime or int).
    Rows with no name are skipped; rows with no expiry still create the product.
    """
    result = ImportResult()
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))

    if not rows:
        result.add_error("Файл пустой")
        return result

    # Locate header row — find the row with "Наименование"
    header_idx = None
    for i, row in enumerate(rows):
        if any("наименование" in _clean_str(c).lower() for c in row if c):
            header_idx = i
            break

    if header_idx is None:
        result.add_error("Строка заголовков не найдена (ожидается 'Наименование товаров')")
        return result

    header = [_clean_str(c).lower() for c in rows[header_idx]]

    def find_col(*keywords: str) -> Optional[int]:
        for kw in keywords:
            for i, h in enumerate(header):
                if kw in h:
                    return i
        return None

    c_name   = find_col("наименование")
    c_unit   = find_col("ед. изм", "ед.изм", "единиц")
    c_qty    = find_col("количество")
    c_expiry = find_col("срок годности", "срок год")
    c_notes  = find_col("комментари", "решение")

    if c_name is None:
        result.add_error("Колонка 'Наименование товаров' не найдена")
        return result

    def get(row, col) -> any:
        return row[col] if col is not None and col < len(row) else None

    for row_num, row in enumerate(rows[header_idx + 1:], start=header_idx + 2):
        name = _clean_str(get(row, c_name))
        if not name:
            continue

        unit       = _clean_str(get(row, c_unit)) or "шт"
        qty        = _clean_float(get(row, c_qty))
        expiry_raw = get(row, c_expiry)
        notes      = _clean_str(get(row, c_notes)) or None
        expiry_date = _excel_serial_to_date(expiry_raw)

        try:
            product = await _get_or_create_product(db, name, unit)

            if expiry_date is not None and qty is not None and qty > 0:
                # Upsert: one batch per product+expiry_date
                res = await db.execute(
                    select(Batch).where(
                        Batch.product_id == product.id,
                        Batch.expiry_date == expiry_date,
                    )
                )
                batch = res.scalar_one_or_none()
                if batch:
                    batch.quantity = qty
                    batch.unit     = unit
                    if notes:
                        batch.notes = notes
                    result.updated += 1
                else:
                    db.add(Batch(
                        product_id=product.id,
                        quantity=qty,
                        unit=unit,
                        expiry_date=expiry_date,
                        notes=notes,
                    ))
                    result.imported += 1
            else:
                # Product with no valid expiry/qty — just ensure it exists
                result.imported += 1

        except Exception as e:
            result.add_error(f"Строка {row_num} ({name!r}): {e}")

    await db.flush()
    return result


# ─── Format 2: Cost / Consumption sheet ───────────────────────────────────────

async def import_cost_sheet(
    db: AsyncSession,
    wb: openpyxl.Workbook,
    updated_by: Optional[int] = None,
    effective_date: Optional[datetime.date] = None,
) -> ImportResult:
    """
    Parse Себестоимость расхода сырья xlsx.

    Layout:
      Row 1 — location / empty
      Row 2 — Себестоимость (computed totals)
      Row 3 — Сумма перемещения
      Row 4 — Кол-во человек
      Row 5 — Код | Товар | Ед. изм. | Цена | (opening balance) | day1 ... day31
      Row 6 — empty separator
      Row 7+ — data

    We import:
      - Cost per unit (Цена column) → RawMaterialCost
      - Opening balance (column right after Цена) → Batch with placeholder expiry
    """
    result = ImportResult()
    today = effective_date or datetime.date.today()

    # Find the right sheet
    sheet_name = next(
        (s for s in wb.sheetnames if "расход" in s.lower()),
        wb.sheetnames[0]
    )
    ws = wb[sheet_name]
    rows = list(ws.iter_rows(values_only=True))

    # Find header row with "Товар" or "Код"
    header_idx = None
    for i, row in enumerate(rows):
        cells = [_clean_str(c).lower() for c in row if c is not None]
        if "товар" in cells or "код" in cells:
            header_idx = i
            break

    if header_idx is None:
        result.add_error("Строка заголовков не найдена (ожидается 'Товар' / 'Код')")
        return result

    header = [_clean_str(c).lower() for c in rows[header_idx]]

    c_name    = next((i for i, h in enumerate(header) if h in ("товар", "наименование")), None)
    c_unit    = next((i for i, h in enumerate(header) if "ед" in h and "изм" in h), None)
    c_price   = next((i for i, h in enumerate(header) if "цена" in h), None)
    c_balance = (c_price + 1) if c_price is not None else None  # opening balance column

    if c_name is None:
        result.add_error("Колонка 'Товар' не найдена")
        return result

    def get(row, col) -> any:
        return row[col] if col is not None and col < len(row) else None

    placeholder_expiry = today + datetime.timedelta(days=365)

    for row_num, row in enumerate(rows[header_idx + 1:], start=header_idx + 2):
        if not row or all(v is None for v in row):
            continue

        name = _clean_str(get(row, c_name))
        if not name:
            continue

        unit    = _clean_str(get(row, c_unit)) or "кг"
        price   = _clean_float(get(row, c_price))
        balance = _clean_float(get(row, c_balance))

        try:
            product = await _get_or_create_product(db, name, unit)

            # Upsert cost
            if price is not None and price > 0:
                res = await db.execute(
                    select(RawMaterialCost).where(
                        RawMaterialCost.product_id == product.id,
                        RawMaterialCost.effective_date == today,
                    )
                )
                cost_row = res.scalar_one_or_none()
                if cost_row:
                    cost_row.cost_per_unit = price
                    cost_row.updated_by    = updated_by
                    result.updated += 1
                else:
                    db.add(RawMaterialCost(
                        product_id=product.id,
                        cost_per_unit=price,
                        currency="RUB",
                        effective_date=today,
                        updated_by=updated_by,
                    ))
                    result.imported += 1

            # Upsert opening balance batch
            if balance is not None and balance > 0:
                res = await db.execute(
                    select(Batch).where(
                        Batch.product_id == product.id,
                        Batch.expiry_date == placeholder_expiry,
                    )
                )
                batch = res.scalar_one_or_none()
                if batch:
                    batch.quantity = balance
                    batch.unit     = unit
                else:
                    db.add(Batch(
                        product_id=product.id,
                        quantity=balance,
                        unit=unit,
                        expiry_date=placeholder_expiry,
                        notes="Импортировано из файла себестоимости (остаток)",
                    ))

        except Exception as e:
            result.add_error(f"Строка {row_num} ({name!r}): {e}")

    await db.flush()
    return result


# ─── Google Sheets downloader ─────────────────────────────────────────────────

async def _fetch_google_sheet(url_or_id: str, sheet_name: str = "") -> bytes:
    """
    Download a Google Sheet as xlsx bytes.

    Accepts:
      - Full URL: https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit...
      - Bare spreadsheet ID

    For public sheets (shared as "anyone with link can view") — works with no auth.
    For private sheets — requires GOOGLE_SERVICE_ACCOUNT_JSON in .env and
    the service account email added as a viewer to the spreadsheet.
    """
    import httpx
    from app.core.config import settings

    # Extract spreadsheet ID
    if "spreadsheets/d/" in url_or_id:
        sheet_id = url_or_id.split("spreadsheets/d/")[1].split("/")[0].split("?")[0]
    else:
        sheet_id = url_or_id.strip()

    if not sheet_id:
        raise ValueError("Не удалось извлечь ID таблицы из URL")

    export_url = (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
        + (f"&sheet={sheet_name}" if sheet_name else "")
    )

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        resp = await client.get(export_url)

        # Valid xlsx starts with PK (zip magic bytes)
        if resp.status_code == 200 and resp.content[:2] == b"PK":
            return resp.content

        if resp.status_code in (401, 403):
            if not settings.GOOGLE_SERVICE_ACCOUNT_JSON:
                raise PermissionError(
                    "Таблица закрыта для публичного доступа. "
                    "Откройте её ('Все, у кого есть ссылка — просмотр') "
                    "или добавьте GOOGLE_SERVICE_ACCOUNT_JSON в .env."
                )

            # Private sheet — service account token flow
            # Uncomment after: pip install google-auth
            #
            # import json
            # from google.oauth2 import service_account
            # from google.auth.transport.requests import Request as GRequest
            #
            # info = json.loads(settings.GOOGLE_SERVICE_ACCOUNT_JSON)
            # creds = service_account.Credentials.from_service_account_info(
            #     info,
            #     scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
            # )
            # creds.refresh(GRequest())
            # resp = await client.get(
            #     export_url,
            #     headers={"Authorization": f"Bearer {creds.token}"},
            # )
            # if resp.status_code == 200 and resp.content[:2] == b"PK":
            #     return resp.content

            raise NotImplementedError(
                "Авторизация через сервисный аккаунт пока не активирована. "
                "Раскомментируйте код в app/services/import_service.py "
                "и добавьте google-auth в requirements.txt."
            )

        raise RuntimeError(
            f"Не удалось загрузить таблицу (HTTP {resp.status_code}). "
            "Проверьте, что таблица открыта для просмотра по ссылке."
        )


# ─── Public API ───────────────────────────────────────────────────────────────

async def import_from_bytes(
    db: AsyncSession,
    xlsx_bytes: bytes,
    import_type: str,
    updated_by: Optional[int] = None,
) -> ImportResult:
    """Parse xlsx bytes and import. import_type: 'risk_report' | 'cost_sheet'"""
    try:
        wb = openpyxl.load_workbook(
            io.BytesIO(xlsx_bytes),
            read_only=True,
            data_only=True,   # read cell values, not formulas
        )
    except Exception as e:
        r = ImportResult()
        r.add_error(f"Не удалось открыть файл как xlsx: {e}")
        return r

    if import_type == "risk_report":
        return await import_risk_report(db, wb, updated_by=updated_by)
    elif import_type == "cost_sheet":
        return await import_cost_sheet(db, wb, updated_by=updated_by)
    else:
        r = ImportResult()
        r.add_error(
            f"Неизвестный тип импорта: {import_type!r}. "
            "Допустимые значения: risk_report, cost_sheet"
        )
        return r


async def import_from_google_sheets(
    db: AsyncSession,
    url_or_id: str,
    import_type: str,
    sheet_name: str = "",
    updated_by: Optional[int] = None,
) -> ImportResult:
    """Download a Google Sheet as xlsx and import it."""
    try:
        xlsx_bytes = await _fetch_google_sheet(url_or_id, sheet_name)
    except Exception as e:
        r = ImportResult()
        r.add_error(str(e))
        return r

    return await import_from_bytes(db, xlsx_bytes, import_type, updated_by=updated_by)