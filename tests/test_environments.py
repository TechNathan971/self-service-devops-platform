VALID = {"name": "dev-alice", "kind": "dev", "owner": "alice"}


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_environment_succeeds(client):
    response = client.post("/environments", json=VALID)
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "dev-alice"
    assert body["status"] == "ready"

def test_duplicate_environment_is_rejected(client):
    client.post("/environments", json=VALID)
    response = client.post("/environments", json=VALID)
    assert response.status_code == 409


def test_reserved_name_is_rejected(client):
    payload = {**VALID, "name": "kube-system"}
    response = client.post("/environments", json=payload)
    assert response.status_code == 403


def test_badly_formed_name_is_rejected(client):
    payload = {**VALID, "name": "Bad Name!"}
    response = client.post("/environments", json=payload)
    assert response.status_code == 422


def test_unknown_kind_is_rejected(client):
    payload = {**VALID, "kind": "banana"}
    response = client.post("/environments", json=payload)
    assert response.status_code == 422


def test_audit_log_records_success_and_denials(client):
    client.post("/environments", json=VALID)
    client.post("/environments", json=VALID)
    client.post("/environments", json={**VALID, "name": "kube-system"})

    events = client.get("/audit-events").json()
    results = [event["result"] for event in events]

    assert len(events) == 3
    assert results.count("success") == 1
    assert results.count("denied") == 2