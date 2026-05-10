from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class AccountRead(BaseModel):
    id: int
    code: str
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AccountBalanceRead(BaseModel):
    name: str
    balance: Decimal
