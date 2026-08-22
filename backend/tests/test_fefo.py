"""
Tests for FEFO (First-Expired-First-Out) consumption write-off.

Confirms:
- write-off deducts from the batch with the nearest expiry first
- when a batch hits 0 it is archived (quantity == 0), not deleted
- remainder spills into the next-nearest batch
- insufficient stock returns an error (no negative stock)
"""
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


def test_fefo_deducts_nearest_expiry_first(seeded_client, auth_header, make_future_date):
    pid = _create_product(seeded_client, auth_header)
    # near batch (10), far batch (10)
    _create_batch(seeded_client, auth_header, pid, 10, make_future_date(5))
    _create_batch(seeded_client, auth_header, pid, 10, make_future_date(60))

    resp = seeded_client.post(
        "/api/consumption/",
        headers=auth_header,
        json={"product_id": pid, "quantity_used": 4, "unit": "л", "date": make_future_date(0)},
    )
    assert resp.status_code in (200, 201), resp.text

    batches = sorted(_batches(seeded_client, auth_header), key=lambda b: b["expiry_date"])
    # near batch should be 6, far still 10
    assert batches[0]["quantity"] == 6.0
    assert batches[1]["quantity"] == 10.0


def test_fefo_spills_into_next_batch_and_archives(seeded_client, auth_header, make_future_date):
    pid = _create_product(seeded_client, auth_header)
    _create_batch(seeded_client, auth_header, pid, 6, make_future_date(5))   # near
    _create_batch(seeded_client, auth_header, pid, 10, make_future_date(60))  # far

    # consume 8 -> near 6->0 (archived), far 10->8
    resp = seeded_client.post(
        "/api/consumption/",
        headers=auth_header,
        json={"product_id": pid, "quantity_used": 8, "unit": "л", "date": make_future_date(0)},
    )
    assert resp.status_code in (200, 201), resp.text
    notes = resp.json()["notes"]
    assert "Партия 1" in notes and "Партия 2" in notes

    batches = sorted(_batches(seeded_client, auth_header), key=lambda b: b["expiry_date"])
    assert batches[0]["quantity"] == 0.0      # archived, not deleted
    assert batches[1]["quantity"] == 8.0


def test_fefo_no_negative_stock(seeded_client, auth_header, make_future_date):
    pid = _create_product(seeded_client, auth_header)
    _create_batch(seeded_client, auth_header, pid, 3, make_future_date(5))

    resp = seeded_client.post(
        "/api/consumption/",
        headers=auth_header,
        json={"product_id": pid, "quantity_used": 99, "unit": "л", "date": make_future_date(0)},
    )
    # Should fail with 400 (insufficient stock), not create negative quantity
    assert resp.status_code == 400, resp.text

    batches = _batches(seeded_client, auth_header)
    assert batches[0]["quantity"] == 3.0  # unchanged, no write-off happened


def test_fefo_consumption_record_created(seeded_client, auth_header, make_future_date):
    pid = _create_product(seeded_client, auth_header)
    _create_batch(seeded_client, auth_header, pid, 5, make_future_date(5))

    seeded_client.post(
        "/api/consumption/",
        headers=auth_header,
        json={"product_id": pid, "quantity_used": 2, "unit": "л", "date": make_future_date(0)},
    )
    resp = seeded_client.get("/api/consumption/", headers=auth_header)
    assert resp.status_code in (200, 201)
    entries = resp.json()
    assert len(entries) == 1
    assert entries[0]["quantity_used"] == 2.0
    assert entries[0]["product_name"] == "Молоко"
