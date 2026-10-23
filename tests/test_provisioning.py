VALID = {"name": "dev-alice", "kind": "dev", "owner": "alice"}


def test_create_builds_a_real_namespace(client, cluster):
    response = client.post("/environments", json=VALID)
    assert response.status_code == 201
    assert response.json()["status"] == "ready"
    assert "dev-alice" in cluster.namespaces
    assert cluster.namespaces["dev-alice"]["owner"] == "alice"


def test_failed_provisioning_leaves_no_phantom_environment(client, cluster):
    cluster.fail_on_create = True
    response = client.post("/environments", json=VALID)
    assert response.status_code == 502

    assert client.get("/environments").json() == []
    events = client.get("/audit-events").json()
    assert events[0]["result"] == "failed"

    cluster.fail_on_create = False
    retry = client.post("/environments", json=VALID)
    assert retry.status_code == 201


def test_delete_removes_the_namespace(client, cluster):
    client.post("/environments", json=VALID)
    response = client.delete("/environments/dev-alice", params={"actor": "alice"})
    assert response.status_code == 200
    assert "dev-alice" not in cluster.namespaces
    assert client.get("/environments").json() == []


def test_delete_unknown_environment_returns_404(client):
    response = client.delete("/environments/ghost", params={"actor": "alice"})
    assert response.status_code == 404


def test_kube_prefix_and_reserved_names_never_reach_the_cluster(client, cluster):
    for name in ["kube-anything", "default"]:
        response = client.post("/environments", json={**VALID, "name": name})
        assert response.status_code == 403
    assert cluster.namespaces == {}