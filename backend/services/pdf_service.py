"""Zoho-style simple PDF generation service for backend invoices."""

from __future__ import annotations

import logging
from typing import Any

from flask import send_file
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.pdfgen import canvas

from models.company_model import get_company
from models.invoice_model import get_invoice_payment_by_id, update_invoice_pdf_path
from utils.helpers import INVOICE_OUTPUT_DIR, ensure_directories, format_currency

logger = logging.getLogger(__name__)

PAGE_WIDTH, PAGE_HEIGHT = A4
LEFT = 19 * mm
RIGHT = PAGE_WIDTH - 19 * mm
TOP = PAGE_HEIGHT - 26 * mm
INK = colors.HexColor("#222222")
MUTED = colors.HexColor("#666666")
HEADER = colors.HexColor("#3D403B")
LIGHT = colors.HexColor("#F3F3F3")
LINE = colors.HexColor("#BDBDBD")

ONES = [
    "",
    "One",
    "Two",
    "Three",
    "Four",
    "Five",
    "Six",
    "Seven",
    "Eight",
    "Nine",
    "Ten",
    "Eleven",
    "Twelve",
    "Thirteen",
    "Fourteen",
    "Fifteen",
    "Sixteen",
    "Seventeen",
    "Eighteen",
    "Nineteen",
]
TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _clean(value: Any) -> str:
    """Return a safe printable string."""
    return str(value or "").replace("\r", "").strip()


def _draw_wrapped(
    pdf: canvas.Canvas,
    text: Any,
    x: float,
    y: float,
    width: float,
    *,
    font: str = "Helvetica",
    size: float = 9,
    leading: float = 11,
    color: colors.Color = INK,
    max_lines: int | None = None,
) -> float:
    """Draw wrapped text and return the next y coordinate."""
    pdf.setFont(font, size)
    pdf.setFillColor(color)
    lines: list[str] = []
    for raw_line in _clean(text).split("\n"):
        words = raw_line.split()
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if pdf.stringWidth(candidate, font, size) <= width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        elif raw_line == "":
            lines.append("")
    if max_lines is not None:
        lines = lines[:max_lines]
    for line in lines:
        pdf.drawString(x, y, line)
        y -= leading
    return y


def _right(
    pdf: canvas.Canvas,
    text: Any,
    x: float,
    y: float,
    *,
    font: str = "Helvetica",
    size: float = 9,
    color: colors.Color = INK,
) -> None:
    """Draw right-aligned text."""
    pdf.setFont(font, size)
    pdf.setFillColor(color)
    pdf.drawRightString(x, y, _clean(text))


def _center(
    pdf: canvas.Canvas,
    text: Any,
    x: float,
    y: float,
    *,
    font: str = "Helvetica",
    size: float = 9,
    color: colors.Color = INK,
) -> None:
    """Draw centered text."""
    pdf.setFont(font, size)
    pdf.setFillColor(color)
    pdf.drawCentredString(x, y, _clean(text))


def _under_100(number: int) -> str:
    """Convert numbers below 100 into words."""
    if number < 20:
        return ONES[number]
    return f"{TENS[number // 10]} {ONES[number % 10]}".strip()


def _under_1000(number: int) -> str:
    """Convert numbers below 1000 into words."""
    if number < 100:
        return _under_100(number)
    suffix = _under_100(number % 100)
    return f"{ONES[number // 100]} Hundred {suffix}".strip()


def _indian_number_words(number: int) -> str:
    """Convert an integer amount into Indian numbering words."""
    if number == 0:
        return "Zero"
    parts: list[str] = []
    crore = number // 10000000
    number %= 10000000
    lakh = number // 100000
    number %= 100000
    thousand = number // 1000
    number %= 1000
    if crore:
        parts.append(f"{_under_1000(crore)} Crore")
    if lakh:
        parts.append(f"{_under_1000(lakh)} Lakh")
    if thousand:
        parts.append(f"{_under_1000(thousand)} Thousand")
    if number:
        parts.append(_under_1000(number))
    return " ".join(parts)


def _amount_in_words(amount: float) -> str:
    """Return the total amount in Indian rupee words."""
    rupees = int(round(float(amount)))
    return f"Indian Rupee {_indian_number_words(rupees)} Only"


def _currency_number(value: float) -> str:
    """Format a plain amount like the old invoice layout."""
    return f"{float(value):,.2f}"


def _draw_company(pdf: canvas.Canvas, company: dict[str, Any]) -> None:
    """Draw the seller details block."""
    y = TOP
    logo_path = _clean(company.get("logo_path"))
    if logo_path:
        try:
            reader = ImageReader(logo_path)
            pdf.drawImage(reader, LEFT, y - 22, width=30 * mm, height=18 * mm, preserveAspectRatio=True, mask="auto")
            y -= 28
        except Exception:
            logger.warning("Configured logo could not be rendered: %s", logo_path)
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(LEFT, y, _clean(company.get("name")) or "Your Business Name")
    y -= 11
    if _clean(company.get("legal_name")) and _clean(company.get("legal_name")) != _clean(company.get("name")):
        y = _draw_wrapped(pdf, company.get("legal_name"), LEFT, y, 72 * mm, size=8.5, leading=10, max_lines=1)
    lines = [
        company.get("address", ""),
        company.get("state", ""),
        "India",
        company.get("email", ""),
        company.get("phone", ""),
        company.get("website", ""),
        f"GSTIN: {company.get('gstin', '')}" if company.get("gstin") else "",
        f"PAN: {company.get('pan', '')}" if company.get("pan") else "",
    ]
    for line in lines:
        if _clean(line):
            y = _draw_wrapped(pdf, line, LEFT, y, 72 * mm, size=9, leading=10, max_lines=2)


def _draw_invoice_title(pdf: canvas.Canvas, invoice: dict[str, Any], symbol: str, template: str = "simple") -> None:
    """Draw invoice title, number, and balance due."""
    balance_due = float(invoice.get("balance_due", invoice.get("total", 0)))
    if str(invoice.get("status", "")).lower() == "void":
        balance_due = 0.0
    pdf.setFillColor(colors.black)
    title = "TAX INVOICE"
    if template == "compact":
        pdf.setFont("Helvetica-Bold", 20)
    elif template == "modern":
        pdf.setFont("Helvetica-Bold", 28)
    else:
        pdf.setFont("Helvetica", 27)
    pdf.drawRightString(RIGHT, TOP - 2, title)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawRightString(RIGHT, TOP - 18, f"# {_clean(invoice.get('invoice_number'))}")
    pdf.setFont("Helvetica-Bold", 8)
    pdf.setFillColor(colors.HexColor("#444444"))
    pdf.drawRightString(RIGHT, TOP - 43, "Balance Due")
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawRightString(RIGHT, TOP - 58, format_currency(balance_due, symbol))
    if str(invoice.get("status", "")).lower() == "void":
        pdf.setFont("Helvetica-Bold", 20)
        pdf.setFillColor(colors.HexColor("#777777"))
        pdf.drawRightString(RIGHT, TOP - 78, "VOID")


def _draw_bill_to(pdf: canvas.Canvas, invoice: dict[str, Any]) -> None:
    """Draw client billing details."""
    y = PAGE_HEIGHT - 88 * mm
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica", 10)
    pdf.drawString(LEFT, y, "Bill To")
    y -= 11
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(LEFT, y, _clean(invoice.get("client_name", "")))
    y -= 11
    y = _draw_wrapped(pdf, invoice.get("client_address", ""), LEFT, y, 74 * mm, size=9, leading=10, max_lines=5)
    if _clean(invoice.get("client_gstin")):
        _draw_wrapped(pdf, f"GSTIN: {invoice.get('client_gstin')}", LEFT, y, 74 * mm, size=9, leading=10, max_lines=1)


def _draw_invoice_meta(pdf: canvas.Canvas, invoice: dict[str, Any]) -> None:
    """Draw date, terms, and due date fields."""
    company = get_company(invoice.get("owner_user_id"))
    label_x = PAGE_WIDTH - 82 * mm
    value_x = RIGHT
    y = PAGE_HEIGHT - 90 * mm
    rows = [
        ("Invoice Date :", invoice.get("date", "")),
        ("Terms :", invoice.get("payment_terms", "") or company.get("default_payment_terms") or "Due on Receipt"),
        ("Due Date :", invoice.get("due_date", "")),
    ]
    for label, value in rows:
        _right(pdf, label, label_x, y, size=10)
        _right(pdf, value, value_x, y, size=10)
        y -= 19


def _draw_items(pdf: canvas.Canvas, invoice: dict[str, Any]) -> float:
    """Draw a wrapped item table and return the y position below it."""
    table_w = RIGHT - LEFT
    start_y = PAGE_HEIGHT - 124 * mm
    bottom_margin = 78 * mm
    col_widths = [10 * mm, 90 * mm, 18 * mm, 22 * mm, 20 * mm, table_w - (10 + 90 + 18 + 22 + 20) * mm]
    item_style = ParagraphStyle(
        "InvoiceItem",
        fontName="Helvetica-Bold",
        fontSize=8.8,
        leading=10.5,
        textColor=INK,
        spaceAfter=2,
    )
    meta_style = ParagraphStyle(
        "InvoiceItemMeta",
        fontName="Helvetica",
        fontSize=7.8,
        leading=9.2,
        textColor=MUTED,
    )

    def item_description(item: dict[str, Any]) -> Paragraph:
        meta_parts = []
        if _clean(item.get("description")):
            meta_parts.append(_clean(item.get("description")))
        if _clean(item.get("hsn_sac")):
            meta_parts.append(f"HSN/SAC: {_clean(item.get('hsn_sac'))}")
        if float(item.get("gst_rate", 0)):
            meta_parts.append(f"GST: {float(item.get('gst_rate', 0)):g}%")
        body = Paragraph(_clean(item.get("item_name", "")), item_style).getPlainText()
        meta = "<br/>".join(meta_parts)
        html = body.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if meta:
            html += "<br/><font name='Helvetica' size='7.8' color='#666666'>" + meta.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") + "</font>"
        return Paragraph(html, item_style)

    rows: list[list[Any]] = [["#", "Item & Description", "Qty", "Rate", "GST", "Amount"]]
    for index, item in enumerate(invoice.get("items", []), start=1):
        rows.append(
            [
                str(index),
                item_description(item),
                f"{float(item.get('quantity', 0)):g}",
                _currency_number(float(item.get("price", 0))),
                _currency_number(float(item.get("line_gst", 0))),
                _currency_number(float(item.get("line_total", 0))),
            ]
        )

    table = Table(rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), HEADER),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, 0), 8.5),
                ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 9),
                ("TOPPADDING", (0, 0), (-1, 0), 9),
                ("TOPPADDING", (0, 1), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, LINE),
                ("LINEBELOW", (0, 1), (-1, -1), 0.35, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("FONTNAME", (0, 1), (0, -1), "Helvetica"),
                ("FONTNAME", (2, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 8.5),
            ]
        )
    )

    y = start_y
    remaining = table
    while remaining:
        available_height = y - bottom_margin
        pieces = remaining.split(table_w, available_height)
        if not pieces:
            pdf.showPage()
            y = TOP
            continue
        chunk = pieces[0]
        width, height = chunk.wrapOn(pdf, table_w, available_height)
        chunk.drawOn(pdf, LEFT, y - height)
        y -= height
        remaining = pieces[1] if len(pieces) > 1 else None
        if remaining:
            pdf.showPage()
            y = TOP

    return y - 12


def _draw_totals(pdf: canvas.Canvas, invoice: dict[str, Any], symbol: str, y: float) -> float:
    """Draw subtotal, GST, total, balance due, and amount in words."""
    label_x = PAGE_WIDTH - 76 * mm
    amount_x = RIGHT - 3 * mm
    row_gap = 24
    amount_paid = float(invoice.get("amount_paid", 0))
    balance_due = float(invoice.get("balance_due", invoice.get("total", 0)))
    if str(invoice.get("status", "")).lower() == "void":
        balance_due = 0.0

    rows = [("Sub Total", invoice.get("subtotal", 0), False)]
    if float(invoice.get("gst_amount", 0)):
        rows.append(("GST Total", invoice.get("gst_amount", 0), False))
    if amount_paid > 0:
        rows.append(("Payment Made", amount_paid, False))
    rows.extend(
        [
            ("Total", invoice.get("total", 0), True),
            ("Balance Due", balance_due, True),
        ]
    )

    for label, value, bold in rows:
        if label == "Balance Due":
            pdf.setFillColor(LIGHT)
            pdf.rect(label_x - 38 * mm, y - 14, RIGHT - (label_x - 38 * mm), 24, stroke=0, fill=1)
        pdf.setFillColor(colors.black)
        pdf.setFont("Helvetica-Bold" if bold else "Helvetica", 10)
        pdf.drawRightString(label_x, y, label)
        amount = format_currency(float(value), symbol) if bold else _currency_number(float(value))
        pdf.drawRightString(amount_x, y, amount)
        y -= row_gap

    words = _amount_in_words(float(invoice.get("total", 0)))
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica", 9)
    pdf.drawRightString(label_x, y + 6, "Total In Words:")
    y = _draw_wrapped(pdf, words, label_x + 8, y + 6, RIGHT - label_x - 8, font="Helvetica-BoldOblique", size=9, leading=11, max_lines=2)
    return y - 24


def _draw_notes_and_signature(pdf: canvas.Canvas, invoice: dict[str, Any]) -> None:
    """Draw bottom notes and the old left-aligned authorized signature line."""
    company = get_company(invoice.get("owner_user_id"))
    y = 88 * mm
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica", 11)
    pdf.drawString(LEFT, y, "Notes")
    note = _clean(invoice.get("notes")) or "Thanks for your business."
    _draw_wrapped(pdf, note, LEFT, y - 17, 100 * mm, size=8.5, leading=11, max_lines=4)

    sig_y = y - 55
    signature_path = _clean(company.get("signature_path"))
    if signature_path:
        try:
            reader = ImageReader(signature_path)
            pdf.drawImage(
                reader,
                LEFT + 44 * mm,
                sig_y + 4,
                width=40 * mm,
                height=15 * mm,
                preserveAspectRatio=True,
                mask="auto",
            )
        except Exception:
            logger.warning("Configured signature could not be rendered: %s", signature_path)
    pdf.setFont("Helvetica", 11)
    pdf.drawString(LEFT, sig_y, "Authorized Signature")
    pdf.setStrokeColor(INK)
    pdf.line(LEFT + 42 * mm, sig_y, LEFT + 106 * mm, sig_y)
    signatory_name = _clean(company.get("authorized_signatory_name"))
    if signatory_name:
        pdf.setFont("Helvetica", 8)
        pdf.setFillColor(MUTED)
        pdf.drawString(LEFT + 42 * mm, sig_y - 11, signatory_name[:45])


def _draw_footer(pdf: canvas.Canvas) -> None:
    """Draw a small footer."""
    pdf.setStrokeColor(LINE)
    pdf.line(LEFT - 3 * mm, 20 * mm, RIGHT + 3 * mm, 20 * mm)
    _center(pdf, "Generated by Smart Invoice + GST Tool", PAGE_WIDTH / 2, 13 * mm, size=8, color=colors.HexColor("#4B5563"))
    _center(pdf, "Professional GST invoices for Indian freelancers and small businesses", PAGE_WIDTH / 2, 8 * mm, size=8, color=colors.HexColor("#4B5563"))
    _right(pdf, "1", RIGHT, 8 * mm, size=8, color=colors.HexColor("#4B5563"))


def generate_invoice_pdf(invoice: dict[str, Any]) -> str:
    """Generate and save a Zoho-style invoice PDF."""
    ensure_directories()
    company = get_company(invoice.get("owner_user_id"))
    symbol = str(company.get("currency_symbol") or "Rs.")
    template = str(company.get("pdf_template") or "simple").lower()
    output_path = INVOICE_OUTPUT_DIR / f"{invoice['invoice_number']}.pdf"
    pdf = canvas.Canvas(str(output_path), pagesize=A4)

    if template == "letterhead":
        pdf.setFillColor(colors.HexColor("#F7F7F7"))
        pdf.rect(0, PAGE_HEIGHT - 38 * mm, PAGE_WIDTH, 38 * mm, stroke=0, fill=1)
    _draw_company(pdf, company)
    _draw_invoice_title(pdf, invoice, symbol, template)
    _draw_bill_to(pdf, invoice)
    _draw_invoice_meta(pdf, invoice)
    y = _draw_items(pdf, invoice)
    if y < 132 * mm:
        pdf.showPage()
        y = TOP
    _draw_totals(pdf, invoice, symbol, y)
    _draw_notes_and_signature(pdf, invoice)
    _draw_footer(pdf)

    pdf.save()
    update_invoice_pdf_path(int(invoice["id"]), str(output_path))
    logger.info("Generated Zoho-style PDF for invoice %s", invoice.get("invoice_number"))
    return str(output_path)


def download_invoice_pdf(invoice: dict[str, Any]):
    """Generate and return an invoice PDF as a Flask download response."""
    path = generate_invoice_pdf(invoice)
    return send_file(path, as_attachment=True, download_name=f"{invoice['invoice_number']}.pdf")


def generate_receipt_pdf(invoice: dict[str, Any], payment: dict[str, Any]) -> str:
    """Generate and save a simple payment receipt PDF."""
    ensure_directories()
    company = get_company(invoice.get("owner_user_id"))
    symbol = str(company.get("currency_symbol") or "Rs.")
    payment_id = payment.get("payment_id")
    output_path = INVOICE_OUTPUT_DIR / f"receipt_{invoice['invoice_number']}_{payment_id}.pdf"
    pdf = canvas.Canvas(str(output_path), pagesize=A4)

    _draw_company(pdf, company)
    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 27)
    pdf.drawRightString(RIGHT, TOP - 2, "PAYMENT RECEIPT")
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawRightString(RIGHT, TOP - 18, f"Receipt # R-{payment_id}")
    pdf.drawRightString(RIGHT, TOP - 34, f"Invoice # {invoice.get('invoice_number')}")

    y = PAGE_HEIGHT - 82 * mm
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(LEFT, y, "Received From")
    y -= 14
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(LEFT, y, _clean(invoice.get("client_name")))
    y -= 11
    _draw_wrapped(pdf, invoice.get("client_address", ""), LEFT, y, 82 * mm, size=9, leading=10, max_lines=4)

    box_x = PAGE_WIDTH - 90 * mm
    box_y = PAGE_HEIGHT - 94 * mm
    pdf.setFillColor(LIGHT)
    pdf.rect(box_x, box_y - 54, RIGHT - box_x, 68, stroke=0, fill=1)
    receipt_rows = [
        ("Payment Date", payment.get("date", "")),
        ("Payment Mode", payment.get("mode", "")),
        ("Reference", payment.get("reference", "") or "-"),
        ("Amount Received", format_currency(float(payment.get("amount", 0)), symbol)),
    ]
    row_y = box_y
    for label, value in receipt_rows:
        _right(pdf, f"{label} :", box_x + 36 * mm, row_y, size=9, color=MUTED)
        _right(pdf, value, RIGHT - 5, row_y, font="Helvetica-Bold" if label == "Amount Received" else "Helvetica", size=9)
        row_y -= 14

    y = PAGE_HEIGHT - 142 * mm
    pdf.setFont("Helvetica-Bold", 11)
    pdf.setFillColor(INK)
    pdf.drawString(LEFT, y, "Payment Summary")
    y -= 18
    summary = [
        ("Invoice Total", invoice.get("total", 0)),
        ("Amount Paid", invoice.get("amount_paid", 0)),
        ("Balance Due", invoice.get("balance_due", 0)),
    ]
    for label, value in summary:
        pdf.setFont("Helvetica", 10)
        pdf.drawString(LEFT, y, label)
        _right(pdf, format_currency(float(value), symbol), LEFT + 82 * mm, y, size=10)
        y -= 16

    if _clean(payment.get("notes")):
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(LEFT, y - 8, "Notes")
        _draw_wrapped(pdf, payment.get("notes"), LEFT, y - 24, 120 * mm, size=9, leading=11, max_lines=4)

    _draw_notes_and_signature(pdf, invoice)
    _draw_footer(pdf)
    pdf.save()
    logger.info("Generated receipt PDF for invoice %s payment %s", invoice.get("invoice_number"), payment_id)
    return str(output_path)


def download_receipt_pdf(invoice: dict[str, Any], payment_id: int):
    """Generate and return a payment receipt PDF."""
    payment = get_invoice_payment_by_id(int(invoice["id"]), payment_id)
    if payment is None:
        return None
    path = generate_receipt_pdf(invoice, payment)
    return send_file(path, as_attachment=True, download_name=f"receipt_{invoice['invoice_number']}_{payment_id}.pdf")
