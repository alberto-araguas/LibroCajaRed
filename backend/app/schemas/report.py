from datetime import date

from pydantic import BaseModel, EmailStr, Field

from app.models import TransactionType


class CashbookReportFilters(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    account_id: int | None = None
    account_code: str | None = None
    type: TransactionType | None = None
    counterparty: str | None = None
    concept: str | None = None


class CashbookEmailRequest(BaseModel):
    recipient: EmailStr
    subject: str = Field(default="Libro de caja", min_length=1, max_length=180)
    message: str | None = Field(default=None, max_length=2000)
    filters: CashbookReportFilters = Field(default_factory=CashbookReportFilters)


class EmailReportResponse(BaseModel):
    status: str
    detail: str
