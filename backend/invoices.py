"""Invoice/PDF generation using reportlab."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

import models


def generate_invoice_pdf(order: models.Order, business_name: str = "Shopping Assistant") -> BytesIO:
    """
    Generate a professional invoice PDF for an order.

    Args:
        order: Order model instance with items and user info
        business_name: Name of the business (for letterhead)

    Returns:
        BytesIO object containing the PDF
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=0.5 * inch, leftMargin=0.5 * inch,
                           topMargin=0.75 * inch, bottomMargin=0.75 * inch)

    # Container for the 'Flowable' objects
    elements = []

    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2E6B4A'),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=11,
        textColor=colors.HexColor('#2E6B4A'),
        spaceAfter=6,
        fontName='Helvetica-Bold'
    )

    normal_style = styles['Normal']
    normal_style.fontSize = 10

    # Header
    elements.append(Paragraph(business_name, title_style))
    elements.append(Spacer(1, 0.15 * inch))

    # Invoice details
    invoice_info = f"""
    <b>INVOICE</b><br/>
    Invoice #: {order.id:06d}<br/>
    Date: {order.created_at.strftime('%B %d, %Y')}<br/>
    """
    elements.append(Paragraph(invoice_info, normal_style))
    elements.append(Spacer(1, 0.2 * inch))

    # Customer info
    customer_info = f"""
    <b>Bill To:</b><br/>
    {order.user.full_name}<br/>
    {order.user.email}<br/>
    """
    elements.append(Paragraph(customer_info, normal_style))
    elements.append(Spacer(1, 0.2 * inch))

    # Items table
    elements.append(Paragraph("Order Items", heading_style))

    table_data = [
        ['Item', 'Quantity', 'Unit', 'Price', 'Subtotal']
    ]

    for item in order.items:
        table_data.append([
            item.name,
            f"{item.quantity:.2f}",
            item.unit or '—',
            f"${item.price:.2f}",
            f"${item.subtotal:.2f}"
        ])

    table_data.append(['', '', '', 'TOTAL', f"${order.total_amount:.2f}"])

    table = Table(table_data, colWidths=[2.5 * inch, 1 * inch, 0.8 * inch, 1 * inch, 1 * inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E6B4A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, -1), (-1, -1), colors.beige),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('TOPPADDING', (0, -1), (-1, -1), 12),
        ('BOTTOMPADDING', (0, -1), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -2), 1, colors.lightgrey),
        ('GRID', (0, -1), (-1, -1), 2, colors.HexColor('#2E6B4A')),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 0.3 * inch))

    # Footer
    footer_style = ParagraphStyle(
        'Footer',
        parent=normal_style,
        fontSize=9,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    footer_text = f"Thank you for your purchase! Generated on {datetime.utcnow().strftime('%B %d, %Y at %I:%M %p UTC')}"
    elements.append(Paragraph(footer_text, footer_style))

    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer
