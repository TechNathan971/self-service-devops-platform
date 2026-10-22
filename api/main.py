from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from api import models, schemas
from api.database import Base, engine, get_db

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Self-Service DevOps Platform", version="0.1.0")

# Names that belong to Kubernetes itself. The platform must never touch them.
RESERVED_NAMES = {"default", "kube-system", "kube-system", "kube-public", "kube-node-lease"}


def record(db: Session, actor: str, action: str, target: str, result: str, detail: str = ""):
    db.add(models.AuditEvent(actor=actor, action=action, target=target, result=result, detail=detail))
    db.commit()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/environments", response_model=schemas.EnvironmentOut, status_code=201)
def create_environment(payload: schemas.EnvironmentCreate, db: Session = Depends(get_db)):
    if payload.name in RESERVED_NAMES:
        record(db, payload.owner, "environment.create", payload.name, "denied", "reserved name")
        raise HTTPException(status_code=403, detail="This name is reserved and cannot be used.")

    existing = db.scalar(select(models.Environment).where(models.Environment.name == payload.name))
    if existing:
        record(db, payload.owner, "environment.create", payload.name, "denied", "already exists")
        raise HTTPException(status_code=409, detail="An environment with this name already exists.")

    env = models.Environment(**payload.model_dump())
    db.add(env)
    db.commit()
    db.refresh(env)
    record(db, payload.owner, "environment.create", payload.name, "success")
    return env


@app.get("/environments", response_model=list[schemas.EnvironmentOut])
def list_environments(db: Session = Depends(get_db)):
    return db.scalars(select(models.Environment).order_by(models.Environment.id)).all()


@app.get("/audit-events", response_model=list[schemas.AuditEventOut])
def list_audit_events(db: Session = Depends(get_db)):
    return db.scalars(select(models.AuditEvent).order_by(models.AuditEvent.id.desc()).limit(50)).all()
