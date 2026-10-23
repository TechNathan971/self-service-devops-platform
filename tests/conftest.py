import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.cluster import ClusterError
from api.database import Base, get_db
from api.main import app, get_cluster


class FakeCluster:
    """A pretend Kubernetes cluster that lives in memory."""

    def __init__(self):
        self.namespaces = {}
        self.fail_on_create = False

    def create_namespace(self, name, env_kind, owner):
        if self.fail_on_create:
            raise ClusterError("simulated cluster outage")
        if name in self.namespaces:
            raise ClusterError("a namespace with this name already exists in the cluster")
        self.namespaces[name] = {"kind": env_kind, "owner": owner}

    def delete_namespace(self, name):
        return self.namespaces.pop(name, None) is not None


@pytest.fixture()
def cluster():
    return FakeCluster()


@pytest.fixture()
def client(cluster):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_cluster] = lambda: cluster
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()