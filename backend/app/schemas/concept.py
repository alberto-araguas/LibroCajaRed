from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConceptCreate(BaseModel):
    name: str = Field(min_length=1, max_length=180)


class ConceptUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=180)


class ConceptRead(BaseModel):
    id: int
    name: str
    normalized_name: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
