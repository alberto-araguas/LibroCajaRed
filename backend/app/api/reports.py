from datetime import date
from email.message import EmailMessage
from io import BytesIO
import smtplib
import ssl

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models import Account, Concept, Counterparty, Transaction, TransactionType
from app.schemas.report import CashbookEmailRequest, EmailReportResponse
from app.services.normalization import normalize_name

router = APIRouter(prefix="/reports", tags=["reports"])


def _apply_report_filters(
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


def _money(value) -> str:
    return f"{value:,.2f} EUR".replace(",", "X").replace(".", ",").replace("X", ".")


def _filter_summary(
    date_from: date | None,
    date_to: date | None,
    account_code: str | None,
    transaction_type: TransactionType | None,
    counterparty: str | None,
    concept: str | None,
) -> str:
    parts = []
    if date_from:
        parts.append(f"Desde: {date_from.strftime('%d/%m/%Y')}")
    if date_to:
        parts.append(f"Hasta: {date_to.strftime('%d/%m/%Y')}")
    if account_code:
        parts.append(f"Cuenta: {account_code}")
    if transaction_type:
        parts.append(f"Tipo: {'Entrada' if transaction_type == TransactionType.INCOME else 'Retirada'}")
    if counterparty:
        parts.append(f"Nombre/empresa: {counterparty}")
    if concept:
        parts.append(f"Concepto: {concept}")
    return " | ".join(parts) if parts else "Sin filtros"


def _get_filtered_transactions(
    db: Session,
    date_from: date | None = None,
    date_to: date | None = None,
    account_id: int | None = None,
    account_code: str | None = None,
    transaction_type: TransactionType | None = None,
    counterparty: str | None = None,
    concept: str | None = None,
) -> list[Transaction]:
    query = (
        select(Transaction)
        .options(
            selectinload(Transaction.account),
            selectinload(Transaction.counterparty),
            selectinload(Transaction.concept),
        )
        .order_by(Transaction.transaction_date.asc(), Transaction.id.asc())
    )
    query = _apply_report_filters(
        query,
        date_from,
        date_to,
        account_id,
        account_code,
        transaction_type,
        counterparty,
        concept,
    )
    return list(db.scalars(query))


def _build_cashbook_pdf(
    transactions: list[Transaction],
    date_from: date | None = None,
    date_to: date | None = None,
    account_code: str | None = None,
    transaction_type: TransactionType | None = None,
    counterparty: str | None = None,
    concept: str | None = None,
) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title="Libro de caja",
    )
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Libro de caja", styles["Title"]),
        Paragraph(
            _filter_summary(date_from, date_to, account_code, transaction_type, counterparty, concept),
            styles["Normal"],
        ),
        Spacer(1, 8),
    ]

    data = [["Fecha", "Tipo", "Cuenta", "Nombre/empresa", "Concepto", "Cantidad"]]
    total_income = 0
    total_expense = 0
    for transaction in transactions:
        amount = float(transaction.amount)
        if transaction.type == TransactionType.INCOME.value:
            total_income += amount
        else:
            total_expense += amount
        data.append(
            [
                transaction.transaction_date.strftime("%d/%m/%Y"),
                "Entrada" if transaction.type == TransactionType.INCOME.value else "Retirada",
                transaction.account.name,
                Paragraph(transaction.counterparty.name, styles["BodyText"]),
                Paragraph(transaction.concept.name, styles["BodyText"]),
                _money(transaction.amount),
            ],
        )

    if len(data) == 1:
        data.append(["", "", "", "No hay movimientos", "", ""])

    table = Table(data, colWidths=[26 * mm, 26 * mm, 30 * mm, 72 * mm, 72 * mm, 34 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dff1ff")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#16324f")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b8d6ed")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6fbff")]),
                ("ALIGN", (-1, 1), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
            ],
        ),
    )
    story.append(table)
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"Total entradas: {_money(total_income)}", styles["Normal"]))
    story.append(Paragraph(f"Total retiradas: {_money(total_expense)}", styles["Normal"]))
    story.append(Paragraph(f"Saldo del informe: {_money(total_income - total_expense)}", styles["Normal"]))

    document.build(story)
    return buffer.getvalue()


def _ensure_smtp_config(settings: Settings) -> None:
    if not settings.smtp_host or not settings.smtp_user or not settings.smtp_password:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "SMTP no está configurado. Para Office 365 configura SMTP_HOST, "
                "SMTP_PORT, SMTP_USER, SMTP_PASSWORD y SMTP_FROM."
            ),
        )


def _send_office365_email(
    settings: Settings,
    recipient: str,
    subject: str,
    body: str,
    pdf_bytes: bytes,
) -> None:
    _ensure_smtp_config(settings)

    sender = settings.smtp_from or settings.smtp_user
    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    message.add_attachment(
        pdf_bytes,
        maintype="application",
        subtype="pdf",
        filename="libro-de-caja.pdf",
    )

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout) as smtp:
            smtp.ehlo()
            if settings.smtp_starttls:
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
            smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)
    except smtplib.SMTPAuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Office 365 rechazó la autenticación SMTP. Revisa usuario/contraseña, "
                "que la cuenta tenga SMTP AUTH habilitado y que las políticas de seguridad "
                "permitan este tipo de envío."
            ),
        ) from exc
    except (smtplib.SMTPException, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"No se pudo enviar el email mediante SMTP: {exc}",
        ) from exc


@router.get("/cashbook/pdf")
def export_cashbook_pdf(
    date_from: date | None = None,
    date_to: date | None = None,
    account_id: int | None = None,
    account_code: str | None = None,
    transaction_type: TransactionType | None = Query(default=None, alias="type"),
    counterparty: str | None = None,
    concept: str | None = None,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    transactions = _get_filtered_transactions(
        db,
        date_from,
        date_to,
        account_id,
        account_code,
        transaction_type,
        counterparty,
        concept,
    )
    pdf_bytes = _build_cashbook_pdf(
        transactions,
        date_from,
        date_to,
        account_code,
        transaction_type,
        counterparty,
        concept,
    )
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="libro-de-caja.pdf"'},
    )


@router.post("/cashbook/email", response_model=EmailReportResponse)
def email_cashbook_report(
    payload: CashbookEmailRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> EmailReportResponse:
    filters = payload.filters
    transactions = _get_filtered_transactions(
        db,
        filters.date_from,
        filters.date_to,
        filters.account_id,
        filters.account_code,
        filters.type,
        filters.counterparty,
        filters.concept,
    )
    pdf_bytes = _build_cashbook_pdf(
        transactions,
        filters.date_from,
        filters.date_to,
        filters.account_code,
        filters.type,
        filters.counterparty,
        filters.concept,
    )
    body = payload.message or "Adjunto encontrarás el informe del libro de caja en PDF."
    body = f"{body}\n\nMovimientos incluidos: {len(transactions)}"
    _send_office365_email(settings, str(payload.recipient), payload.subject, body, pdf_bytes)
    return EmailReportResponse(status="ok", detail="Email enviado correctamente.")
