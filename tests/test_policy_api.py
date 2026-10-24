GOOD_CHECK = {
    "deployment": {
        "service": "demo-api",
        "image": "ghcr.io/technathan971/demo-api:1.0.0",
        "port": 8080,
        "cpu_limit": "500m",
        "memory_limit": "256Mi",
        "run_as_non_root": True,
    },
    "env_kind": "dev",
    "requested_by": "alice",
}


def test_good_request_is_allowed_and_logged(client):
    response = client.post("/policy-checks", json=GOOD_CHECK)
    assert response.status_code == 200
    assert response.json() == {"allowed": True, "violations": []}

    event = client.get("/audit-events").json()[0]
    assert event["action"] == "policy.check"
    assert event["result"] == "allowed"


def test_bad_request_lists_every_broken_rule(client):
    bad = {**GOOD_CHECK, "deployment": {**GOOD_CHECK["deployment"], "image": "nginx:latest", "port": 80}}
    response = client.post("/policy-checks", json=bad)
    assert response.status_code == 200

    body = response.json()
    assert body["allowed"] is False
    rules = {v["rule"] for v in body["violations"]}
    assert rules == {"image-tag-pinned", "image-registry-allowed", "unprivileged-port"}

    event = client.get("/audit-events").json()[0]
    assert event["result"] == "denied"


def test_malformed_request_is_rejected(client):
    bad = {**GOOD_CHECK, "deployment": {**GOOD_CHECK["deployment"], "service": "Bad Name!"}}
    response = client.post("/policy-checks", json=bad)
    assert response.status_code == 422