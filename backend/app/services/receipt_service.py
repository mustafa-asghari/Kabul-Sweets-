"""
PDF receipt generation service.
Generates professional receipts with tax breakdown using ReportLab.
"""

import io
from datetime import datetime, timezone
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.logging import get_logger

logger = get_logger("receipt_service")

# Brand colors
BRAND_PURPLE = colors.HexColor("#7C3AED")
BRAND_DARK = colors.HexColor("#1a1a2e")
LIGHT_GRAY = colors.HexColor("#f8f8f8")


def generate_receipt_pdf(order_data: dict) -> bytes:
    """
    Generate a professional PDF receipt for an order.
    Returns the PDF as bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "ReceiptTitle",
        parent=styles["Title"],
        fontSize=24,
        textColor=BRAND_DARK,
        spaceAfter=5,
    )
    subtitle_style = ParagraphStyle(
        "ReceiptSubtitle",
        parent=styles["Normal"],
        fontSize=12,
        textColor=BRAND_PURPLE,
        spaceAfter=15,
    )
    normal_style = ParagraphStyle(
        "ReceiptNormal",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.black,
    )
    small_style = ParagraphStyle(
        "ReceiptSmall",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.gray,
    )

    elements = []

    # Header
    elements.append(Paragraph("Kabul Sweets", title_style))
    elements.append(Paragraph("Authentic Afghan Bakery", subtitle_style))
    elements.append(Spacer(1, 5 * mm))

    # Receipt label
    elements.append(Paragraph("<b>RECEIPT</b>", ParagraphStyle(
        "Label", parent=styles["Normal"], fontSize=14, textColor=BRAND_PURPLE,
    )))
    elements.append(Spacer(1, 5 * mm))

    # Order details
    order_number = order_data.get("order_number", "N/A")
    customer_name = order_data.get("customer_name", "N/A")
    customer_email = order_data.get("customer_email", "N/A")
    paid_at = order_data.get("paid_at", datetime.now(timezone.utc).isoformat())

    details_data = [
        ["Order Number:", order_number],
        ["Customer:", customer_name],
        ["Email:", customer_email],
        ["Date:", paid_at[:10] if paid_at else "N/A"],
    ]
    details_table = Table(details_data, colWidths=[100, 350])
    details_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(details_table)
    elements.append(Spacer(1, 8 * mm))

    # Items table
    items = order_data.get("items", [])
    table_data = [["Item", "Qty", "Unit Price", "Total"]]

    for item in items:
        name = item.get("product_name", "")
        variant = item.get("variant_name")
        if variant:
            name += f" ({variant})"
        qty = str(item.get("quantity", 1))
        unit = f"${item.get('unit_price', '0.00')}"
        total = f"${item.get('line_total', '0.00')}"
        table_data.append([name, qty, unit, total])

    items_table = Table(table_data, colWidths=[250, 50, 80, 80])
    items_table.setStyle(TableStyle([
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_PURPLE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        # Data rows
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        # Alternating row colors
        *[("BACKGROUND", (0, i), (-1, i), LIGHT_GRAY)
          for i in range(2, len(table_data), 2)],
        # Grid
        ("LINEBELOW", (0, 0), (-1, 0), 1, BRAND_PURPLE),
        ("LINEBELOW", (0, -1), (-1, -1), 1, BRAND_DARK),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 5 * mm))

    # Totals
    subtotal = order_data.get("subtotal", "0.00")
    tax_amount = order_data.get("tax_amount", "0.00")
    discount = order_data.get("discount_amount", "0.00")
    total = order_data.get("total", "0.00")

    totals_data = [
        ["", "", "Subtotal:", f"${subtotal}"],
        ["", "", "GST (10%):", f"${tax_amount}"],
    ]
    if discount and Decimal(str(discount)) > 0:
        totals_data.append(["", "", "Discount:", f"-${discount}"])
    totals_data.append(["", "", "TOTAL PAID:", f"${total} AUD"])

    totals_table = Table(totals_data, colWidths=[250, 50, 80, 80])
    totals_table.setStyle(TableStyle([
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("FONTNAME", (2, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (2, -1), (-1, -1), 12),
        ("TEXTCOLOR", (2, -1), (-1, -1), BRAND_DARK),
        ("LINEABOVE", (2, -1), (-1, -1), 2, BRAND_DARK),
        ("TOPPADDING", (0, -1), (-1, -1), 8),
    ]))
    elements.append(totals_table)
    elements.append(Spacer(1, 15 * mm))

    # Footer
    elements.append(Paragraph(
        "Thank you for choosing Kabul Sweets!",
        ParagraphStyle("Footer", parent=styles["Normal"], fontSize=11,
                       textColor=BRAND_PURPLE, alignment=1),
    ))
    elements.append(Spacer(1, 3 * mm))
    elements.append(Paragraph(
        "This is your official receipt. Please keep for your records.",
        ParagraphStyle("FooterSmall", parent=styles["Normal"], fontSize=8,
                       textColor=colors.gray, alignment=1),
    ))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    logger.info("Receipt PDF generated for order %s (%d bytes)", order_number, len(pdf_bytes))
    return pdf_bytes
