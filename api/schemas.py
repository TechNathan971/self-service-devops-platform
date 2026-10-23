from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EnvironmentCreate(BaseModel):
    # lowercase letters, digits, hyphens; starts with a letter; 4-30 characters
    name: str = Field(pattern=r"^[a-z][a-z0-9-]{2,28}[a-z0-9]$")
    kind: Literal["dev", "staging", "prod"]
    owner: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,48}[a-z0-9]$")


class EnvironmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    kind: str
    owner: str
    status: str
    created_at: datetime


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor: str
    action: str
    target: str
    result: str
    detail: str
    created_at: datetime