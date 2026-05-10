from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=128)


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=6, max_length=128)
    full_name: str | None = Field(default=None, max_length=160)
    is_admin: bool = False
    is_active: bool = True


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=80)
    password: str | None = Field(default=None, min_length=6, max_length=128)
    full_name: str | None = Field(default=None, max_length=160)
    is_admin: bool | None = None
    is_active: bool | None = None


class UserRead(BaseModel):
    id: int
    username: str
    full_name: str | None
    is_admin: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class MovementUserLookup(BaseModel):
    transaction_id: int
    transaction_date: date
    counterparty_name: str
    concept_name: str
    amount: str
    username: str | None
    full_name: str | None
