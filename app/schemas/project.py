from datetime import datetime

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    target_base_url: str


class ProjectOut(BaseModel):
    id: int
    name: str
    target_base_url: str
    created_at: datetime

    model_config = {"from_attributes": True}
