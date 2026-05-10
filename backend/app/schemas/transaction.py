from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import TransactionType
from app.schemas.account import AccountRead


class NamedReferenceRead(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class TransactionCreate(BaseModel):
    account_id: int | None = None
    account_code: str | None = None
    counterparty_name: str = Field(min_length=1, max_length=180)
    concept_name: str = Field(min_length=1, max_length=180)
    type: TransactionType
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    transaction_date: date
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_account_reference(self) -> "TransactionCreate":
        if self.account_id is None and self.account_code is None:
            raise ValueError("Indica account_id o account_code.")
        return self


class TransactionUpdate(BaseModel):
    account_id: int | None = None
    account_code: str | None = None
    counterparty_name: str | None = Field(default=None, min_length=1, max_length=180)
    concept_name: str | None = Field(default=None, min_length=1, max_length=180)
    type: TransactionType | None = None
    amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    transaction_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)


class TransactionRead(BaseModel):
    id: int
    account_id: int
    counterparty_id: int
    concept_id: int
    type: TransactionType
    amount: Decimal
    transaction_date: date
    notes: str | None
    created_at: datetime
    updated_at: datetime
    account: AccountRead
    counterparty: NamedReferenceRead
    concept: NamedReferenceRead

    model_config = ConfigDict(from_attributes=True)
