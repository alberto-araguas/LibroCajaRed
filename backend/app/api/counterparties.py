from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Counterparty, Transaction
from app.schemas.counterparty import CounterpartyCreate, CounterpartyRead, CounterpartyUpdate
from app.services.normalization import normalize_name

router = APIRouter(prefix="/counterparties", tags=["counterparties"])


def _get_counterparty_or_404(counterparty_id: int, db: Session) -> Counterparty:
    counterparty = db.get(Counterparty, counterparty_id)
    if counterparty is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nombre o empresa no encontrado.",
        )
    return counterparty


def _ensure_unique_name(
    normalized_name: str,
    db: Session,
    counterparty_id: int | None = None,
) -> None:
    query = select(Counterparty).where(Counterparty.normalized_name == normalized_name)
    if counterparty_id is not None:
        query = query.where(Counterparty.id != counterparty_id)

    if db.scalar(query) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un nombre o empresa con ese nombre.",
        )


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    clean_value = value.strip()
    return clean_value or None


@router.get("", response_model=list[CounterpartyRead])
def list_counterparties(
    q: str | None = Query(default=None, description="Texto para buscar por nombre o empresa."),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[Counterparty]:
    query = select(Counterparty)
    if q:
        normalized_query = normalize_name(q)
        query = query.where(
            or_(
                Counterparty.name.ilike(f"%{q}%"),
                Counterparty.normalized_name.ilike(f"%{normalized_query}%"),
                Counterparty.dni_cif.ilike(f"%{q}%"),
                Counterparty.phone.ilike(f"%{q}%"),
                Counterparty.email.ilike(f"%{q}%"),
            ),
        )

    query = query.order_by(Counterparty.name).limit(limit).offset(offset)
    return list(db.scalars(query))


@router.post("", response_model=CounterpartyRead, status_code=status.HTTP_201_CREATED)
def create_counterparty(
    payload: CounterpartyCreate,
    db: Session = Depends(get_db),
) -> Counterparty:
    name = payload.name.strip()
    normalized_name = normalize_name(name)
    _ensure_unique_name(normalized_name, db)

    counterparty = Counterparty(
        name=name,
        normalized_name=normalized_name,
        dni_cif=_clean_optional(payload.dni_cif),
        address=_clean_optional(payload.address),
        phone=_clean_optional(payload.phone),
        email=str(payload.email) if payload.email else None,
    )
    db.add(counterparty)
    db.commit()
    db.refresh(counterparty)
    return counterparty


@router.get("/{counterparty_id}", response_model=CounterpartyRead)
def get_counterparty(counterparty_id: int, db: Session = Depends(get_db)) -> Counterparty:
    return _get_counterparty_or_404(counterparty_id, db)


@router.put("/{counterparty_id}", response_model=CounterpartyRead)
def update_counterparty(
    counterparty_id: int,
    payload: CounterpartyUpdate,
    db: Session = Depends(get_db),
) -> Counterparty:
    counterparty = _get_counterparty_or_404(counterparty_id, db)

    if payload.name is not None:
        name = payload.name.strip()
        normalized_name = normalize_name(name)
        _ensure_unique_name(normalized_name, db, counterparty_id=counterparty.id)
        counterparty.name = name
        counterparty.normalized_name = normalized_name
    if "dni_cif" in payload.model_fields_set:
        counterparty.dni_cif = _clean_optional(payload.dni_cif)
    if "address" in payload.model_fields_set:
        counterparty.address = _clean_optional(payload.address)
    if "phone" in payload.model_fields_set:
        counterparty.phone = _clean_optional(payload.phone)
    if "email" in payload.model_fields_set:
        counterparty.email = str(payload.email) if payload.email else None

    db.commit()
    db.refresh(counterparty)
    return counterparty


@router.delete("/{counterparty_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_counterparty(counterparty_id: int, db: Session = Depends(get_db)) -> None:
    counterparty = _get_counterparty_or_404(counterparty_id, db)
    transaction_count = db.scalar(
        select(func.count())
        .select_from(Transaction)
        .where(Transaction.counterparty_id == counterparty.id),
    )
    if transaction_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar un nombre o empresa con movimientos asociados.",
        )

    db.delete(counterparty)
    db.commit()
