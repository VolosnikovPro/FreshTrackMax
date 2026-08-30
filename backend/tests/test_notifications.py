"""Tests for notification trigger + log persistence."""
from datetime import date, timedelta


def _create_product_with_urgent_batch(seeded_client, auth_header, name, days):
    p = seeded_client.post("/api/products/", headers=auth_header, json={"name": name, "unit": "кг"})
    pid = p.json()["id"]
    exp = (date.today() + timedelta(days=days)).isoformat()
    seeded_client.post(
        "/api/batches/",
        headers=auth_header,
        json={"product_id": pid, "quantity": 2, "unit": "кг", "expiry_date": exp},
    )
    return pid


def test_trigger_urgent_logs_to_db(seeded_client, auth_header, make_future_date):
    _create_product_with_urgent_batch(seeded_client, auth_header, "Сыр срочный", 5)

    resp = seeded_client.post("/api/notifications/trigger/urgent", headers=auth_header)
    assert resp.status_code in (200, 201), resp.text
    data = resp.json()
    assert data["products_included"] == 1

    logs = seeded_client.get("/api/notifications/logs", headers=auth_header).json()
    assert len(logs) >= 1
    log = logs[0]
    assert log["notification_type"] == "urgent"
    assert log["products_count"] == 1


def test_trigger_planned_logs_to_db(seeded_client, auth_header, make_future_date):
    # planned window = <= 46 days
    _create_product_with_urgent_batch(seeded_client, auth_header, "Масло плановое", 30)

    resp = seeded_client.post("/api/notifications/trigger/planned", headers=auth_header)
    assert resp.status_code in (200, 201), resp.text
    assert resp.json()["products_included"] >= 1

    logs = seeded_client.get("/api/notifications/logs", headers=auth_header).json()
    assert any(l["notification_type"] == "planned" for l in logs)


def test_logs_empty_when_no_batches(seeded_client, auth_header):
    resp = seeded_client.post("/api/notifications/trigger/urgent", headers=auth_header)
    assert resp.status_code in (200, 201)
    assert resp.json()["products_included"] == 0
    # No log row should be created when nothing to send
    logs = seeded_client.get("/api/notifications/logs", headers=auth_header).json()
    assert logs == []


def test_application_registers_notification_scheduler(seeded_client):
    """The scheduler is started with the API application, not left as a dead module."""
    from main import app

    assert app.state.notification_scheduler_task is not None
