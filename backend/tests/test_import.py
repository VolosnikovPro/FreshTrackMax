"""Tests for Google-Sheets / xlsx import (risk_report and cost_sheet)."""
from openpyxl import Workbook
from datetime import date, timedelta

# Excel serial date = days since 1899-12-30
_EXCEL_EPOCH = date(1899, 12, 30)


def _to_excel_serial(d: date) -> int:
    return (d - _EXCEL_EPOCH).days


def _make_risk_xlsx(path):
    wb = Workbook()
    ws = wb.active
    ws.append(["", "Риск-Отчет"])
    ws.append(["Наименование товаров", "Ед. Изм.", "Количество", "Срок годности", "Комментарий"])
    ws.append(["Сыр Гауда", "кг", 5, _to_excel_serial(date.today() + timedelta(days=10)), "проверить"])
    ws.append(["Масло сливочное", "кг", 3, _to_excel_serial(date.today() + timedelta(days=30)), ""])
    wb.save(path)


def _make_cost_xlsx(path):
    wb = Workbook()
    ws = wb.active
    ws.append(["Склад Асача"])
    ws.append(["Себестоимость"])
    ws.append(["Сумма перемещения"])
    ws.append(["Кол-во человек"])
    ws.append(["Код", "Товар", "Ед. изм.", "Цена", "Остаток", "1", "2"])
    ws.append([""])  # separator
    ws.append(["1", "Сахар", "кг", 120, 50])
    ws.append(["2", "Мука", "кг", 80, 30])
    wb.save(path)


def test_import_risk_report_creates_products_and_batches(seeded_client, auth_header, tmp_path):
    _make_risk_xlsx(tmp_path / "risk.xlsx")
    with open(tmp_path / "risk.xlsx", "rb") as f:
        resp = seeded_client.post(
            "/api/sheets/import/file?import_type=risk_report",
            headers=auth_header,
            files={"file": ("risk.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
    assert resp.status_code in (200, 201), resp.text
    data = resp.json()
    assert data["imported"] == 2
    assert data["errors"] == []

    products = seeded_client.get("/api/products/?active_only=false", headers=auth_header).json()
    names = {p["name"] for p in products}
    assert "Сыр Гауда" in names and "Масло сливочное" in names

    batches = seeded_client.get("/api/batches/?include_archived=true", headers=auth_header).json()
    assert len(batches) >= 2  # Молоко from elsewhere + 2 here


def test_import_cost_sheet_creates_costs(seeded_client, auth_header, tmp_path):
    _make_cost_xlsx(tmp_path / "cost.xlsx")
    with open(tmp_path / "cost.xlsx", "rb") as f:
        resp = seeded_client.post(
            "/api/sheets/import/file?import_type=cost_sheet",
            headers=auth_header,
            files={"file": ("cost.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
    assert resp.status_code in (200, 201), resp.text
    data = resp.json()
    assert data["imported"] == 2
    assert data["errors"] == []

    costs = seeded_client.get("/api/costs/", headers=auth_header).json()
    names = {c["product_name"] for c in costs}
    assert "Сахар" in names and "Мука" in names


def test_import_invalid_type_rejected(seeded_client, auth_header, tmp_path):
    _make_risk_xlsx(tmp_path / "risk.xlsx")
    with open(tmp_path / "risk.xlsx", "rb") as f:
        resp = seeded_client.post(
            "/api/sheets/import/file?import_type=bogus",
            headers=auth_header,
            files={"file": ("risk.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
    assert resp.status_code == 400
