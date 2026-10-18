def test_manager_can_create_daily_headcount(seeded_client, auth_header, seeded):
    created = seeded_client.post(
        "/api/admin/users",
        headers=auth_header,
        json={"username": "upp-headcount", "role": "manager", "password": "pass"},
    )
    assert created.status_code == 201, created.text

    token = seeded_client.post(
        "/api/auth/login", json={"username": "upp-headcount", "password": "pass"}
    ).json()["access_token"]
    manager_headers = {"Authorization": f"Bearer {token}"}

    response = seeded_client.post(
        "/api/headcount/",
        headers=manager_headers,
        json={"site_id": seeded["site_id"], "date": "2026-10-18", "count": 406},
    )

    assert response.status_code == 201, response.text
    assert response.json()["count"] == 406
    assert response.json()["site_id"] == seeded["site_id"]

    updated = seeded_client.post(
        "/api/headcount/",
        headers=manager_headers,
        json={"site_id": seeded["site_id"], "date": "2026-10-18", "count": 407},
    )

    assert updated.status_code == 201, updated.text
    assert updated.json()["id"] == response.json()["id"]
    assert updated.json()["count"] == 407
