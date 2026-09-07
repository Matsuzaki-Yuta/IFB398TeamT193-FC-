"""
Joins the three halves together: render the templates, build the PDF, send.

Kept apart from email_service.py (which knows only about SMTP) and from
quote_service.py (which knows only about pricing) so each of the three can be
tested on its own. This is the only module that needs a Flask application
context, because render_template does.
"""

from flask import render_template

from backend.services.email_service import build_message, send_message, load_settings
from backend.services.pdf_service import (
    build_quote_pdf, package_meta_line, quote_pdf_filename,
)

# Long inclusion lists come straight from the scraped package data and can run
# to a dozen entries. Six is enough to sell the trip without turning the email
# into a wall of text; the attached PDF carries up to eight.
MAX_INCLUSIONS_IN_EMAIL = 6


def build_subject(quote):
    return (
        f"Your Flight Centre quote: {quote['package']['name']} "
        f"({quote['reference']})"
    )


def render_bodies(quote, has_attachment):
    """
    Renders both halves of the email from the same values.

    Returns (text_body, html_body). Jinja autoescaping is on for .html and off
    for .txt, which is the behaviour we want: the customer name and the agent's
    free-text message are escaped in the HTML part and left alone in the text
    part, where there is no markup to break.
    """
    context = {
        "quote": quote,
        "package_meta": package_meta_line(quote["package"]),
        "inclusions": [
            item for item in (quote["package"].get("inclusions") or []) if item
        ][:MAX_INCLUSIONS_IN_EMAIL],
        "has_attachment": has_attachment,
    }
    return (
        render_template("emails/quote.txt", **context),
        render_template("emails/quote.html", **context),
    )


def send_quote_email(quote, attach_pdf=True):
    """
    Sends the finished quote to the customer.

    Returns a small dictionary describing what was actually sent, so the API
    response can tell the frontend whether the PDF made it on.

    Raises EmailConfigurationError or EmailSendError from email_service; the
    route turns those into 503 and 502 respectively.
    """
    settings = load_settings()

    pdf_bytes = build_quote_pdf(quote) if attach_pdf else None
    attachments = []
    if pdf_bytes:
        attachments.append(
            (quote_pdf_filename(quote), "application/pdf", pdf_bytes)
        )

    text_body, html_body = render_bodies(quote, has_attachment=bool(pdf_bytes))

    message = build_message(
        to_email=quote["customer"]["email"],
        subject=build_subject(quote),
        text_body=text_body,
        html_body=html_body,
        attachments=attachments,
        settings=settings,
    )
    send_message(message, settings)

    return {
        "message_id": message["Message-ID"],
        "attached_pdf": bool(pdf_bytes),
        # Gmail replaces the From header with the account that authenticated, so
        # this is what the customer will actually see, not necessarily what
        # MAIL_FROM_EMAIL said.
        "from_email": settings["from_email"],
    }
