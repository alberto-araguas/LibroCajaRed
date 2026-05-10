from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Concept, Transaction
from app.schemas.concept import ConceptCreate, ConceptRead, ConceptUpdate
from app.services.normalization import normalize_name

router = APIRouter(prefix="/concepts", tags=["concepts"])


def _get_concept_or_404(concept_id: int, db: Session) -> Concept:
    concept = db.get(Concept, concept_id)
    if concept is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Concepto no encontrado.",
        )
    return concept


def _ensure_unique_name(normalized_name: str, db: Session, concept_id: int | None = None) -> None:
    query = select(Concept).where(Concept.normalized_name == normalized_name)
    if concept_id is not None:
        query = query.where(Concept.id != concept_id)

    if db.scalar(query) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un concepto con ese nombre.",
        )


@router.get("", response_model=list[ConceptRead])
def list_concepts(
    q: str | None = Query(default=None, description="Texto para buscar por nombre."),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[Concept]:
    query = select(Concept)
    if q:
        normalized_query = normalize_name(q)
        query = query.where(
            or_(
                Concept.name.ilike(f"%{q}%"),
                Concept.normalized_name.ilike(f"%{normalized_query}%"),
            ),
        )

    query = query.order_by(Concept.name).limit(limit).offset(offset)
    return list(db.scalars(query))


@router.post("", response_model=ConceptRead, status_code=status.HTTP_201_CREATED)
def create_concept(payload: ConceptCreate, db: Session = Depends(get_db)) -> Concept:
    name = payload.name.strip()
    normalized_name = normalize_name(name)
    _ensure_unique_name(normalized_name, db)

    concept = Concept(name=name, normalized_name=normalized_name)
    db.add(concept)
    db.commit()
    db.refresh(concept)
    return concept


@router.get("/{concept_id}", response_model=ConceptRead)
def get_concept(concept_id: int, db: Session = Depends(get_db)) -> Concept:
    return _get_concept_or_404(concept_id, db)


@router.put("/{concept_id}", response_model=ConceptRead)
def update_concept(
    concept_id: int,
    payload: ConceptUpdate,
    db: Session = Depends(get_db),
) -> Concept:
    concept = _get_concept_or_404(concept_id, db)

    if payload.name is not None:
        name = payload.name.strip()
        normalized_name = normalize_name(name)
        _ensure_unique_name(normalized_name, db, concept_id=concept.id)
        concept.name = name
        concept.normalized_name = normalized_name

    db.commit()
    db.refresh(concept)
    return concept


@router.delete("/{concept_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_concept(concept_id: int, db: Session = Depends(get_db)) -> None:
    concept = _get_concept_or_404(concept_id, db)
    transaction_count = db.scalar(
        select(func.count()).select_from(Transaction).where(Transaction.concept_id == concept.id),
    )
    if transaction_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar un concepto con movimientos asociados.",
        )

    db.delete(concept)
    db.commit()
