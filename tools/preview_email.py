"""
Builds a sample quote and writes the email to preview/ — no SMTP, no App Password.

Use this while working on the wording or the layout of the email. It produces
the same HTML, plain text and PDF the real send would, so you can open them and
look at them without an inbox in the loop.

    python tools/preview_email.py

Then open preview/quote-email.html in a browser.

The one thing it cannot tell you is how the email will look inside Gmail or
Outlook, which apply their own rules to the markup. Once the wording is settled,
send one to yourself for that.
"""

import os
import sys
import webbrowser

# Run from anywhere: put the project root on the import path.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from app import create_app                                        # noqa: E402
from backend.models.database import get_connection                # noqa: E402
from backend.services.pdf_service import PDF_AVAILABLE, build_quote_pdf  # noqa: E402
from backend.services.quote_mail import build_subject, render_bodies     # noqa: E402
from backend.services.quote_service import build_quote            # noqa: E402

OUTPUT_DIR = os.path.join(PROJECT_ROOT, "preview")

SAMPLE_REQUEST = {
    "customer": {
        "name": "Jordan Lee",
        "email": "jordan@example.com",
        "travellers": 2,
    },
    "quote": {
        "departure": "2026-12-01",
        "valid_days": 14,
        "message": (
            "Here's the trip we put together from your video. Hold it with a "
            "deposit any time in the next two weeks."
        ),
    },
}


def pick_package():
    """
    Uses a real package from packages.db, so the preview shows real data.

    Prefers one with a destination and a description, because a third of the
    rows have neither and those make a poor preview.
    """
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id FROM packages
            WHERE destination IS NOT NULL AND TRIM(destination) <> ''
              AND summary IS NOT NULL AND TRIM(summary) <> ''
              AND price_from_aud > 0
            LIMIT 1
            """
        ).fetchone()

    if row is None:
        raise SystemExit(
            "No usable package found in packages.db. Is the database in the "
            "project root, beside app.py?"
        )
    return row["id"]


def main():
    application = create_app()

    request = dict(SAMPLE_REQUEST)
    request["selected_package_id"] = pick_package()

    # render_template needs an application context; a request is not required.
    with application.app_context():
        quote = build_quote(request)
        pdf_bytes = build_quote_pdf(quote)
        text_body, html_body = render_bodies(quote, has_attachment=bool(pdf_bytes))

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    html_path = os.path.join(OUTPUT_DIR, "quote-email.html")
    text_path = os.path.join(OUTPUT_DIR, "quote-email.txt")

    with open(html_path, "w", encoding="utf-8") as handle:
        handle.write(html_body)
    with open(text_path, "w", encoding="utf-8") as handle:
        handle.write(text_body)

    print("Subject:  " + build_subject(quote))
    print("To:       " + quote["customer"]["email"])
    print("Package:  " + quote["package"]["name"])
    print("Total:    " + quote["money"]["total"])
    print()
    print("HTML:     " + html_path)
    print("Text:     " + text_path)

    if pdf_bytes:
        pdf_path = os.path.join(OUTPUT_DIR, "quote-attachment.pdf")
        with open(pdf_path, "wb") as handle:
            handle.write(pdf_bytes)
        print("PDF:      " + pdf_path)
    else:
        print("PDF:      skipped — reportlab is not installed "
              "(pip install -r requirements.txt)")

    print()
    print("Opening the HTML version in your browser...")
    webbrowser.open("file://" + html_path.replace(os.sep, "/"))


if __name__ == "__main__":
    main()
