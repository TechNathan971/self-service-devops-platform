from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from api import models, schemas
from api.cluster import ClusterError, KubernetesCluster
from api.database import Base, engine, get_db

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Self-Service DevOps Platform", version="0.2.0")

# Names that belong to Kubernetes itself. The platform must never touch them.
RESERVED_NAMES = {"default", "kube-system", "kube-public", "kube-node-lease"}

_cluster = None


def get_cluster():
    global _cluster
    if _cluster is None:
        try:
            _cluster = KubernetesCluster()
        except ClusterError as exc:
            raise HTTPException(status_code=503, detail=f"Cluster unavailable: {exc}")
    return _cluster


def record(db: Session, actor: str, action: str, target: str, result: str, detail: str = ""):
    db.add(models.AuditEvent(actor=actor, action=action, target=target, result=result, detail=detail))
    db.commit()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/environments", response_model=schemas.EnvironmentOut, status_code=201)
def create_environment(
    payload: schemas.EnvironmentCreate,
    db: Session = Depends(get_db),
    cluster=Depends(get_cluster),
):
    if payload.name in RESERVED_NAMES or payload.name.startswith("kube-"):
        record(db, payload.owner, "environment.create", payload.name, "denied", "reserved name")
        raise HTTPException(status_code=403, detail="This name is reserved and cannot be used.")

    existing = db.scalar(select(models.Environment).where(models.Environment.name == payload.name))
    if existing:
        record(db, payload.owner, "environment.create", payload.name, "denied", "already exists")
        raise HTTPException(status_code=409, detail="An environment with this name already exists.")

    env = models.Environment(**payload.model_dump(), status="provisioning")
    db.add(env)
    db.commit()
    db.refresh(env)

    try:
        cluster.create_namespace(payload.name, payload.kind, payload.owner)
    except ClusterError as exc:
        db.delete(env)  # no phantom bookings: the room was never built
        db.commit()
        record(db, payload.owner, "environment.create", payload.name, "failed", str(exc))
        raise HTTPException(status_code=502, detail=f"Provisioning failed: {exc}")

    env.status = "ready"
    db.commit()
    db.refresh(env)
    record(db, payload.owner, "environment.create", payload.name, "success")
    return env


@app.delete("/environments/{name}")
def delete_environment(
    name: str,
    actor: str = Query(min_length=2, max_length=50),
    db: Session = Depends(get_db),
    cluster=Depends(get_cluster),
):
    env = db.scalar(select(models.Environment).where(models.Environment.name == name))
    if env is None:
        record(db, actor, "environment.delete", name, "denied", "unknown environment")
        raise HTTPException(status_code=404, detail="No such environment.")

    try:
        existed = cluster.delete_namespace(name)
    except ClusterError as exc:
        record(db, actor, "environment.delete", name, "failed", str(exc))
        raise HTTPException(status_code=502, detail=f"Teardown failed: {exc}")

    db.delete(env)
    db.commit()
    record(db, actor, "environment.delete", name, "success", "" if existed else "namespace was already gone")
    return {"name": name, "status": "deleted"}


@app.get("/environments", response_model=list[schemas.EnvironmentOut])
def list_environments(db: Session = Depends(get_db)):
    return db.scalars(select(models.Environment).order_by(models.Environment.id)).all()


@app.get("/audit-events", response_model=list[schemas.AuditEventOut])
def list_audit_events(db: Session = Depends(get_db)):
    return db.scalars(select(models.AuditEvent).order_by(models.AuditEvent.id.desc()).limit(50)).all()