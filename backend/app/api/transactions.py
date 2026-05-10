from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models import Account, Concept, Counterparty, Transaction, TransactionType
from app.schemas.transaction import TransactionCreate, TransactionRead, TransactionUpdate
from app.services.normalization import normalize_name

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _transaction_options() -> tuple:
    return (
        selectinload(Transaction.account),
        selectinload(Transaction.counterparty),
        selectinload(Transaction.concept),
    )


def _get_transaction_or_404(transaction_id: int, db: Session) -> Transaction:
    transaction = db.scalar(
        select(Transaction)
        .options(*_transaction_options())
        .where(Transaction.id == transaction_id),
    )
    if transaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movimiento no encontrado.",
        )
    return transaction


def _get_account(account_id: int | None, account_code: str | None, db: Session) -> Account:
    if account_id is None and account_code is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Indica account_id o account_code.",
        )

    query = select(Account)
    if account_id is not None:
        query = query.where(Account.id == account_id)
    else:
        query = query.where(Account.code == account_code)

    account = db.scalar(query)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cuenta no encontrada.",
        )
    return account


def _get_or_create_counterparty(name: str, db: Session) -> Counterparty:
    normalized_name = normalize_name(name)
    counterparty = db.scalar(
        select(Counterparty).where(Counterparty.normalized_name == normalized_name),
    )
    if counterparty is not None:
        return counterparty

    counterparty = Counterparty(name=name.strip(), normalized_name=normalized_name)
    db.add(counterparty)
    db.flush()
    return counterparty


def _get_or_create_concept(name: str, db: Session) -> Concept:
    normalized_name = normalize_name(name)
    concept = db.scalar(select(Concept).where(Concept.normalized_name == normalized_name))
    if concept is not None:
        return concept

    concept = Concept(name=name.strip(), normalized_name=normalized_name)
    db.add(concept)
    db.flush()
    return concept


def _apply_filters(
    query: Select[tuple[Transaction]],
    date_from: date | None,
    date_to: date | None,
    account_id: int | None,
    account_code: str | None,
    transaction_type: TransactionType | None,
    counterparty: str | None,
    concept: str | None,
) -> Select[tuple[Transaction]]:
    if date_from is not None:
        query = query.where(Transaction.transaction_date >= date_from)
    if date_to is not None:
        query = query.where(Transaction.transaction_date <= date_to)
    if account_id is not None:
        query = query.where(Transaction.account_id == account_id)
    if account_code is not None:
        query = query.join(Transaction.account).where(Account.code == account_code)
    if transaction_type is not None:
        query = query.where(Transaction.type == transaction_type.value)
    if counterparty:
        query = query.join(Transaction.counterparty).where(
            or_(
                Counterparty.name.ilike(f"%{counterparty}%"),
                Counterparty.normalized_name.ilike(f"%{normalize_name(counterparty)}%"),
            ),
        )
    if concept:
        query = query.join(Transaction.concept).where(
            or_(
                Concept.name.ilike(f"%{concept}%"),
                Concept.normalized_name.ilike(f"%{normalize_name(concept)}%"),
            ),
        )
    return query


@router.get("", response_model=list[TransactionRead])
def list_transactions(
    date_from: date | None = None,
    date_to: date | None = None,
    account_id: int | None = None,
    account_code: str | None = None,
    transaction_type: TransactionType | None = Query(default=None, alias="type"),
    counterparty: str | None = None,
    concept: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[Transaction]:
    query = select(Transaction).options(*_transaction_options())
    query = _apply_filters(
        query,
        date_from,
        date_to,
        account_id,
        account_code,
        transaction_type,
        counterparty,
        concept,
    )
    query = query.order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
    query = query.limit(limit).offset(offset)
    return list(db.scalars(query))


@router.post("", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
) -> Transaction:
    account = _get_account(payload.account_id, payload.account_code, db)
    counterparty = _get_or_create_counterparty(payload.counterparty_name, db)
    concept = _get_or_create_concept(payload.concept_name, db)

    transaction = Transaction(
        account_id=account.id,
        counterparty_id=counterparty.id,
        concept_id=concept.id,
        type=payload.type.value,
        amount=payload.amount,
        transaction_date=payload.transaction_date,
        notes=payload.notes,
    )
    db.add(transaction)
    db.commit()
    return _get_transaction_or_404(transaction.id, db)


@router.get("/{transaction_id}", response_model=TransactionRead)
def get_transaction(transaction_id: int, db: Session = Depends(get_db)) -> Transaction:
    return _get_transaction_or_404(transaction_id, db)


@router.put("/{transaction_id}", response_model=TransactionRead)
def update_transaction(
    transaction_id: int,
    payload: TransactionUpdate,
    db: Session = Depends(get_db),
) -> Transaction:
    transaction = _get_transaction_or_404(transaction_id, db)

    if payload.account_id is not None or payload.account_code is not None:
        transaction.account_id = _get_account(payload.account_id, payload.account_code, db).id
    if payload.counterparty_name is not None:
        transaction.counterparty_id = _get_or_create_counterparty(payload.counterparty_name, db).id
    if payload.concept_name is not None:
        transaction.concept_id = _get_or_create_concept(payload.concept_name, db).id
    if payload.type is not None:
        transaction.type = payload.type.value
    if payload.amount is not None:
        transaction.amount = payload.amount
    if payload.transaction_date is not None:
        transaction.transaction_date = payload.transaction_date
    if payload.notes is not None:
        transaction.notes = payload.notes

    db.commit()
    return _get_transaction_or_404(transaction.id, db)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)) -> None:
    transaction = _get_transaction_or_404(transaction_id, db)
    db.delete(transaction)
    db.commit()
