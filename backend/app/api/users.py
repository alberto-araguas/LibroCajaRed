from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.auth import require_admin
from app.db.session import get_db
from app.models import Transaction, User
from app.schemas.auth import MovementUserLookup, UserCreate, UserRead, UserUpdate
from app.services.security import hash_password

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(require_admin)])


@router.get("", response_model=list[UserRead])
def list_users(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[User]:
    query = select(User).order_by(User.username).limit(limit).offset(offset)
    return list(db.scalars(query))


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    username = payload.username.strip()
    if db.scalar(select(User).where(User.username == username)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con ese nombre.",
        )

    user = User(
        username=username,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name.strip() if payload.full_name else None,
        is_admin=payload.is_admin,
        is_active=payload.is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserRead)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db)) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado.",
        )

    if payload.username is not None:
        username = payload.username.strip()
        existing = db.scalar(select(User).where(User.username == username, User.id != user.id))
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe un usuario con ese nombre.",
            )
        user.username = username
    if "full_name" in payload.model_fields_set:
        user.full_name = payload.full_name.strip() if payload.full_name else None
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
    if payload.is_admin is not None:
        user.is_admin = payload.is_admin
    if payload.is_active is not None:
        user.is_active = payload.is_active

    db.commit()
    db.refresh(user)
    return user


@router.get("/movement-lookup/{transaction_id}", response_model=MovementUserLookup)
def lookup_movement_user(transaction_id: int, db: Session = Depends(get_db)) -> MovementUserLookup:
    transaction = db.scalar(
        select(Transaction)
        .options(
            selectinload(Transaction.counterparty),
            selectinload(Transaction.concept),
            selectinload(Transaction.created_by),
        )
        .where(Transaction.id == transaction_id),
    )
    if transaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movimiento no encontrado.",
        )

    return MovementUserLookup(
        transaction_id=transaction.id,
        transaction_date=transaction.transaction_date,
        counterparty_name=transaction.counterparty.name,
        concept_name=transaction.concept.name,
        amount=str(transaction.amount),
        username=transaction.created_by.username if transaction.created_by else None,
        full_name=transaction.created_by.full_name if transaction.created_by else None,
    )
