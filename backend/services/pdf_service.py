"""
Renders the quote as a one-page PDF to attach to the email.

ReportLab was chosen over WeasyPrint because it is pure Python: "pip install
reportlab" works on Windows without installing GTK, Cairo or Pango first, and
the team is split across Windows and macOS.

The import is guarded. If a teammate pulls the branch and forgets to re-run
pip install, build_quote_pdf returns None and the email still goes out with the
full quote in its body — a missing attachment is a much smaller failure than a
send that dies with ImportError during the demo.
"""

import io

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    )
    PDF_AVAILABLE = True
except ImportError:  # pragma: no cover - depends on the local environment
    PDF_AVAILABLE = False


FC_RED = "#D50118"
INK = "#1D1D1F"
DIM = "#6E6E73"
RULE = "#D8D8DC"
SUNK = "#F5F5F7"


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "qTitle", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=20, leading=24, textColor=colors.HexColor(INK),
            alignment=0, spaceAfter=2,
        ),
        "kicker": ParagraphStyle(
            "qKicker", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=8, leading=11, textColor=colors.HexColor(FC_RED),
            spaceAfter=6,
        ),
        "meta": ParagraphStyle(
            "qMeta", parent=base["Normal"], fontName="Helvetica",
            fontSize=9, leading=13, textColor=colors.HexColor(DIM),
        ),
        "metaRight": ParagraphStyle(
            "qMetaRight", parent=base["Normal"], fontName="Helvetica",
            fontSize=9, leading=13, textColor=colors.HexColor(DIM),
            alignment=TA_RIGHT,
        ),
        "h2": ParagraphStyle(
            "qH2", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=11, leading=15, textColor=colors.HexColor(INK),
            spaceBefore=14, spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "qBody", parent=base["Normal"], fontName="Helvetica",
            fontSize=9.5, leading=14, textColor=colors.HexColor(INK),
        ),
        "fine": ParagraphStyle(
            "qFine", parent=base["Normal"], fontName="Helvetica",
            fontSize=7.5, leading=10.5, textColor=colors.HexColor(DIM),
        ),
    }


def package_meta_line(package):
    """destination - nights - category, skipping whatever the row is missing."""
    parts = []
    if package.get("destination"):
        parts.append(str(package["destination"]))
    if package.get("duration_nights"):
        parts.append(f"{package['duration_nights']} nights")
    if package.get("category"):
        parts.append(str(package["category"]).title())
    return " · ".join(parts) if parts else "Details to be confirmed"


def _summary_table(quote, width):
    """The price breakdown — the same five lines the summary rail shows."""
    money = quote["money"]
    totals = quote["totals"]

    rows = [
        ["Per person (twin share)", money["per_person"]],
        [f"Travellers x {totals['travellers']}", money["subtotal"]],
        ["Booking fee", money["booking_fee"]],
        ["Total", money["total"]],
        ["Deposit due on acceptance (20%)", money["deposit"]],
    ]

    table = Table(rows, colWidths=[width * 0.62, width * 0.38])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 2), "Helvetica"),
        ("FONTNAME", (0, 3), (-1, 3), "Helvetica-Bold"),
        ("FONTNAME", (0, 4), (-1, 4), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, 2), 9.5),
        ("FONTSIZE", (0, 3), (-1, 3), 12),
        ("FONTSIZE", (0, 4), (-1, 4), 9),
        ("TEXTCOLOR", (0, 0), (0, 2), colors.HexColor(DIM)),
        ("TEXTCOLOR", (0, 3), (-1, 3), colors.HexColor(INK)),
        ("TEXTCOLOR", (0, 4), (-1, 4), colors.HexColor(DIM)),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEABOVE", (0, 3), (-1, 3), 0.75, colors.HexColor(RULE)),
        ("TOPPADDING", (0, 3), (-1, 3), 10),
    ]))
    return table


def _details_table(quote, width):
    """Who, when, and against which package."""
    package = quote["package"]
    rows = [
        ["Traveller", quote["customer"]["name"]],
        ["Travellers", str(quote["totals"]["travellers"])],
        ["Departure", quote["departure_display"]],
        ["Destination", str(package.get("destination") or "-")],
        ["Duration", f"{package.get('duration_nights') or '-'} nights"],
        ["Quote valid until", quote["valid_until_display"]],
    ]

    table = Table(rows, colWidths=[width * 0.34, width * 0.66])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor(DIM)),
        ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor(INK)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(SUNK)),
        ("LEFTPADDING", (0, 0), (0, -1), 10),
        ("RIGHTPADDING", (1, 0), (1, -1), 10),
    ]))
    return table


def build_quote_pdf(quote):
    """
    Returns the PDF as bytes, or None when ReportLab is not installed.

    Callers treat None as "send without an attachment" rather than as an error.
    """
    if not PDF_AVAILABLE:
        return None

    styles = _styles()
    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title=f"Travel quote {quote['reference']}",
        author="Flight Centre Trip Bridge",
        subject=str(quote["package"].get("name") or "Travel quote"),
    )
    width = document.width
    package = quote["package"]
    story = []

    # ---- masthead ----
    header = Table(
        [[
            Paragraph("FLIGHT CENTRE &middot; TRIP BRIDGE", styles["kicker"]),
            Paragraph(
                f"Quote {quote['reference']}<br/>Issued {quote['issued_on_display']}",
                styles["metaRight"],
            ),
        ]],
        colWidths=[width * 0.55, width * 0.45],
    )
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(header)
    story.append(HRFlowable(
        width="100%", thickness=2, color=colors.HexColor(FC_RED),
        spaceBefore=6, spaceAfter=14,
    ))

    # ---- the package ----
    story.append(Paragraph(_escape(package.get("name") or "Your trip"), styles["title"]))
    # 83 of the 194 rows in packages.db have no destination, so the meta line is
    # joined from whatever is actually present. Otherwise those packages print a
    # stray leading separator.
    story.append(Paragraph(_escape(package_meta_line(package)), styles["meta"]))

    if package.get("summary"):
        story.append(Spacer(1, 10))
        story.append(Paragraph(_escape(package["summary"]), styles["body"]))

    # ---- trip details ----
    story.append(Paragraph("Trip details", styles["h2"]))
    story.append(_details_table(quote, width))

    # ---- what is included ----
    inclusions = [item for item in (package.get("inclusions") or []) if item][:8]
    if inclusions:
        story.append(Paragraph("What's included", styles["h2"]))
        for item in inclusions:
            story.append(Paragraph(f"&bull;&nbsp;&nbsp;{_escape(item)}", styles["body"]))
            story.append(Spacer(1, 2))

    # ---- the numbers ----
    story.append(Paragraph("Your quote", styles["h2"]))
    story.append(_summary_table(quote, width))

    # ---- the agent's note ----
    if quote.get("agent_message"):
        story.append(Paragraph("A note from your consultant", styles["h2"]))
        story.append(Paragraph(_escape(quote["agent_message"]), styles["body"]))

    # ---- fine print ----
    story.append(Spacer(1, 18))
    story.append(HRFlowable(
        width="100%", thickness=0.75, color=colors.HexColor(RULE), spaceAfter=8,
    ))
    story.append(Paragraph(
        "Prices are indicative, per person, twin share, in AUD, and are subject to "
        "availability at the time of booking. Airfares are excluded unless listed "
        "in the inclusions above. This quote is valid until "
        f"{quote['valid_until_display']}. "
        "Generated by Trip Bridge, a Flight Centre in-store concept.",
        styles["fine"],
    ))

    document.build(story)
    return buffer.getvalue()


def _escape(value):
    """ReportLab paragraphs read a small HTML dialect, so & < > must be escaped."""
    return (str(value or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))


def quote_pdf_filename(quote):
    return f"Flight-Centre-Quote-{quote['reference']}.pdf"
