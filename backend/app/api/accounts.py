from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Account, Transaction, TransactionType
from app.schemas.account import AccountBalanceRead, AccountRead

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountRead])
def list_accounts(db: Session = Depends(get_db)) -> list[Account]:
    return list(db.scalars(select(Account).order_by(Account.id)))


@router.get("/balances", response_model=dict[str, AccountBalanceRead])
def get_account_balances(db: Session = Depends(get_db)) -> dict[str, AccountBalanceRead]:
    balance_expression = func.coalesce(
        func.sum(
            case(
                (Transaction.type == TransactionType.INCOME.value, Transaction.amount),
                else_=-Transaction.amount,
            ),
        ),
        0,
    )

    rows = db.execute(
        select(Account.code, Account.name, balance_expression)
        .outerjoin(Transaction, Transaction.account_id == Account.id)
        .group_by(Account.id, Account.code, Account.name)
        .order_by(Account.id),
    )

    return {
        code: AccountBalanceRead(name=name, balance=Decimal(balance))
        for code, name, balance in rows
    }
