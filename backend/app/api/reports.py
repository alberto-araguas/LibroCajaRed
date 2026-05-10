from datetime import date, datetime
from email.message import EmailMessage
from io import BytesIO
from pathlib import Path
import smtplib
import ssl

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape, portrait
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models import Account, Concept, Counterparty, Transaction, TransactionType
from app.schemas.report import CashbookEmailRequest, EmailReportResponse, MovementEmailRequest
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


def _format_optional(value: str | None) -> str:
    return value or "Sin indicar"


def _movement_type_label(transaction: Transaction) -> str:
    return "Entrada" if transaction.type == TransactionType.INCOME.value else "Retirada"


def _get_report_transaction(transaction_id: int, db: Session) -> Transaction:
    transaction = db.scalar(
        select(Transaction)
        .options(
            selectinload(Transaction.account),
            selectinload(Transaction.counterparty),
            selectinload(Transaction.concept),
        )
        .where(Transaction.id == transaction_id),
    )
    if transaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movimiento no encontrado.",
        )
    return transaction


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


def _draw_movement_header_footer(canvas, document, settings: Settings) -> None:
    width, height = portrait(A4)
    canvas.saveState()

    header_y = height - 22 * mm
    logo_size = 16 * mm
    logo_x = document.leftMargin
    logo_y = height - 24 * mm

    if settings.report_logo_path and Path(settings.report_logo_path).exists():
        canvas.drawImage(
            settings.report_logo_path,
            logo_x,
            logo_y,
            width=logo_size,
            height=logo_size,
            preserveAspectRatio=True,
            mask="auto",
        )
    else:
        canvas.setFillColor(colors.HexColor("#1976c9"))
        canvas.roundRect(logo_x, logo_y, logo_size, logo_size, 3, fill=True, stroke=False)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 14)
        canvas.drawCentredString(logo_x + logo_size / 2, logo_y + 5 * mm, "LC")

    canvas.setFillColor(colors.HexColor("#12304c"))
    canvas.setFont("Helvetica-Bold", 15)
    canvas.drawString(logo_x + logo_size + 6 * mm, header_y, settings.report_company_name)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#4f6e89"))
    canvas.drawString(
        logo_x + logo_size + 6 * mm,
        header_y - 5 * mm,
        f"Informe emitido el {datetime.now().strftime('%d/%m/%Y %H:%M')}",
    )

    canvas.setStrokeColor(colors.HexColor("#c3d8ea"))
    canvas.line(document.leftMargin, height - 31 * mm, width - document.rightMargin, height - 31 * mm)

    footer_y = 17 * mm
    canvas.line(document.leftMargin, footer_y + 9 * mm, width - document.rightMargin, footer_y + 9 * mm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#4f6e89"))
    text = canvas.beginText(document.leftMargin, footer_y + 3 * mm)
    text.setLeading(8)
    footer_width = width - document.leftMargin - document.rightMargin - 20 * mm
    text.textLines(simpleSplit(settings.report_privacy_footer, "Helvetica", 7, footer_width))
    canvas.drawText(text)
    canvas.drawRightString(width - document.rightMargin, footer_y + 2 * mm, f"Página {document.page}")
    canvas.restoreState()


def _section_title(text: str, styles) -> Paragraph:
    return Paragraph(text, styles["SectionHeading"])


def _info_table(rows: list[tuple[str, str]], styles) -> Table:
    data = [[Paragraph(label, styles["FieldLabel"]), Paragraph(value, styles["BodyText"])] for label, value in rows]
    table = Table(data, colWidths=[42 * mm, 112 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e7f1fa")),
                ("BACKGROUND", (1, 0), (1, -1), colors.white),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#12304c")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c3d8ea")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ],
        ),
    )
    return table


def _build_movement_pdf(transaction: Transaction, settings: Settings) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=portrait(A4),
        rightMargin=22 * mm,
        leftMargin=22 * mm,
        topMargin=42 * mm,
        bottomMargin=34 * mm,
        title=f"Movimiento {transaction.id}",
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            "SectionHeading",
            parent=styles["Heading2"],
            textColor=colors.HexColor("#0f5ea5"),
            fontSize=11,
            leading=14,
            spaceBefore=8,
            spaceAfter=7,
        ),
    )
    styles.add(
        ParagraphStyle(
            "FieldLabel",
            parent=styles["BodyText"],
            textColor=colors.HexColor("#12304c"),
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
        ),
    )

    amount = _money(transaction.amount)
    if transaction.type == TransactionType.EXPENSE.value:
        amount = f"-{amount}"

    story = [
        Paragraph("Informe de movimiento", styles["Title"]),
        Paragraph(f"Movimiento Nº {transaction.id}", styles["Normal"]),
        Spacer(1, 9),
        _section_title("Datos del movimiento", styles),
        _info_table(
            [
                ("Fecha", transaction.transaction_date.strftime("%d/%m/%Y")),
                ("Tipo", _movement_type_label(transaction)),
                ("Cuenta", transaction.account.name),
                ("Cantidad", amount),
                ("Concepto", transaction.concept.name),
                ("Notas", transaction.notes or "Sin notas"),
            ],
            styles,
        ),
        Spacer(1, 10),
        _section_title("Nombre o empresa", styles),
        _info_table(
            [
                ("Nombre", transaction.counterparty.name),
                ("DNI/CIF", _format_optional(transaction.counterparty.dni_cif)),
                ("Dirección", _format_optional(transaction.counterparty.address)),
                ("Teléfono", _format_optional(transaction.counterparty.phone)),
                ("Email", _format_optional(transaction.counterparty.email)),
            ],
            styles,
        ),
    ]

    document.build(
        story,
        onFirstPage=lambda canvas, doc: _draw_movement_header_footer(canvas, doc, settings),
        onLaterPages=lambda canvas, doc: _draw_movement_header_footer(canvas, doc, settings),
    )
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
    filename: str = "libro-de-caja.pdf",
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
        filename=filename,
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


@router.get("/movements/{transaction_id}/pdf")
def export_movement_pdf(
    transaction_id: int,
    download: bool = True,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    transaction = _get_report_transaction(transaction_id, db)
    pdf_bytes = _build_movement_pdf(transaction, settings)
    disposition = "attachment" if download else "inline"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'{disposition}; filename="movimiento-{transaction.id}.pdf"'},
    )


@router.post("/movements/{transaction_id}/email", response_model=EmailReportResponse)
def email_movement_report(
    transaction_id: int,
    payload: MovementEmailRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> EmailReportResponse:
    transaction = _get_report_transaction(transaction_id, db)
    pdf_bytes = _build_movement_pdf(transaction, settings)
    body = payload.message or "Adjunto encontrarás el informe del movimiento en PDF."
    body = f"{body}\n\nMovimiento Nº {transaction.id}: {transaction.counterparty.name} - {transaction.concept.name}"
    _send_office365_email(
        settings,
        str(payload.recipient),
        payload.subject,
        body,
        pdf_bytes,
        filename=f"movimiento-{transaction.id}.pdf",
    )
    return EmailReportResponse(status="ok", detail="Email enviado correctamente.")


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
