from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CounterpartyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    dni_cif: str | None = Field(default=None, max_length=32)
    address: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=40)
    email: EmailStr | None = None


class CounterpartyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=180)
    dni_cif: str | None = Field(default=None, max_length=32)
    address: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=40)
    email: EmailStr | None = None


class CounterpartyRead(BaseModel):
    id: int
    name: str
    normalized_name: str
    dni_cif: str | None
    address: str | None
    phone: str | None
    email: EmailStr | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
