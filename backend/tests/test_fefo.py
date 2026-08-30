"""
Tests for FEFO (First-Expired-First-Out) consumption write-off.

Confirms:
- write-off deducts from the batch with the nearest expiry first
- when a batch hits 0 it is archived (quantity == 0), not deleted
- remainder spills into the next-nearest batch
- insufficient stock returns an error (no negative stock)
"""
from datetime import date
from openpyxl import Workbook
import pytest


def _create_product(seeded_client, auth_header, name="Молоко"):
    resp = seeded_client.post(
        "/api/products/",
        headers=auth_header,
        json={"name": name, "unit": "л", "is_active": True},
    )
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["id"]


def _create_batch(seeded_client, auth_header, pid, qty, expiry):
    resp = seeded_client.post(
        "/api/batches/",
        headers=auth_header,
        json={"product_id": pid, "quantity": qty, "unit": "л", "expiry_date": expiry},
    )
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["id"]


def _batches(seeded_client, auth_header):
    resp = seeded_client.get("/api/batches/?include_archived=true", headers=auth_header)
    return resp.json()


def _consume_from_file(seeded_client, admin_header, product_name, quantity, tmp_path):
    seeded_client.post("/api/admin/users", headers=admin_header, json={"username": "klad-fefo", "role": "storekeeper", "password": "pass"})
    token = seeded_client.post("/api/auth/login", json={"username": "klad-fefo", "password": "pass"}).json()["access_token"]
    wb = Workbook()
    ws = wb.active
    ws.append(["Дата", "Товар", "Ед. изм.", "Количество"])
    ws.append([date.today(), product_name, "л", quantity])
    path = tmp_path / "fefo-consumption.xlsx"
    wb.save(path)
    with path.open("rb") as stream:
        return seeded_client.post(
            "/api/sheets/import/file?import_type=consumption_file",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": (path.name, stream, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )


def test_fefo_deducts_nearest_expiry_first(seeded_client, auth_header, make_future_date, tmp_path):
    pid = _create_product(seeded_client, auth_header)
    # near batch (10), far batch (10)
    _create_batch(seeded_client, auth_header, pid, 10, make_future_date(5))
    _create_batch(seeded_client, auth_header, pid, 10, make_future_date(60))

    resp = _consume_from_file(seeded_client, auth_header, "Молоко", 4, tmp_path)
    assert resp.status_code == 200, resp.text

    batches = sorted(_batches(seeded_client, auth_header), key=lambda b: b["expiry_date"])
    # near batch should be 6, far still 10
    assert batches[0]["quantity"] == 6.0
    assert batches[1]["quantity"] == 10.0


def test_fefo_spills_into_next_batch_and_archives(seeded_client, auth_header, make_future_date, tmp_path):
    pid = _create_product(seeded_client, auth_header)
    _create_batch(seeded_client, auth_header, pid, 6, make_future_date(5))   # near
    _create_batch(seeded_client, auth_header, pid, 10, make_future_date(60))  # far

    # consume 8 -> near 6->0 (archived), far 10->8
    resp = _consume_from_file(seeded_client, auth_header, "Молоко", 8, tmp_path)
    assert resp.status_code == 200, resp.text

    batches = sorted(_batches(seeded_client, auth_header), key=lambda b: b["expiry_date"])
    assert batches[0]["quantity"] == 0.0      # archived, not deleted
    assert batches[0]["status"] == "archived"
    assert batches[1]["quantity"] == 8.0


def test_batch_is_immutable_after_creation(seeded_client, auth_header, make_future_date):
    pid = _create_product(seeded_client, auth_header)
    batch_id = _create_batch(seeded_client, auth_header, pid, 6, make_future_date(5))

    response = seeded_client.put(
        f"/api/batches/{batch_id}", headers=auth_header, json={"quantity": 2},
    )

    assert response.status_code == 409, response.text


def test_same_upd_and_expiry_adds_to_existing_batch(seeded_client, auth_header, make_future_date):
    pid = _create_product(seeded_client, auth_header)
    expiry = make_future_date(20)
    _create_batch(seeded_client, auth_header, pid, 4, expiry)
    response = seeded_client.post(
        "/api/batches/", headers=auth_header,
        json={"product_id": pid, "quantity": 3, "unit": "л", "expiry_date": expiry},
    )
    assert response.status_code == 201, response.text
    assert response.json()["quantity"] == 7


def test_fefo_no_negative_stock(seeded_client, auth_header, make_future_date, tmp_path):
    pid = _create_product(seeded_client, auth_header)
    _create_batch(seeded_client, auth_header, pid, 3, make_future_date(5))

    resp = _consume_from_file(seeded_client, auth_header, "Молоко", 99, tmp_path)
    # Should fail with 400 (insufficient stock), not create negative quantity
    assert resp.status_code == 400, resp.text

    batches = _batches(seeded_client, auth_header)
    assert batches[0]["quantity"] == 3.0  # unchanged, no write-off happened


def test_fefo_consumption_record_created(seeded_client, auth_header, make_future_date, tmp_path):
    pid = _create_product(seeded_client, auth_header)
    _create_batch(seeded_client, auth_header, pid, 5, make_future_date(5))

    response = _consume_from_file(seeded_client, auth_header, "Молоко", 2, tmp_path)
    assert response.status_code == 200, response.text
    resp = seeded_client.get("/api/consumption/", headers=auth_header)
    assert resp.status_code in (200, 201)
    entries = resp.json()
    assert len(entries) == 1
    assert entries[0]["quantity_used"] == 2.0
    assert entries[0]["product_name"] == "Молоко"


def test_fefo_writeoff_statement_locks_candidate_batches():
    """PostgreSQL write-offs must lock the FEFO rows before checking stock."""
    from app.services.consumption_service import fefo_batches_statement

    statement = fefo_batches_statement(site_id=1, product_id=1)

    assert statement._for_update_arg is not None
