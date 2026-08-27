"""
Turns what the browser sends into a finished, trustworthy quote.

The final quote page adds up the price in JavaScript so the total can move as
the agent changes the traveller count. That number is for display only. Anything
the browser can edit, a customer can edit, so this module ignores the price the
page sends and rebuilds every figure from the package row in packages.db.

Nothing in here talks to the network. That keeps it unit-testable without an
SMTP server, which is what makes the pricing rules cheap to cover in tests.
"""

import json
import re
import uuid
from datetime import date, datetime, timedelta

from backend.models.database import get_connection

# The commercial rules, in one place. The final quote page holds the same two
# numbers for its live preview; if either changes, change it in both.
BOOKING_FEE_AUD = 49          # per booking, not per traveller
DEPOSIT_RATE = 0.20           # 20% of the total, due on acceptance

MAX_TRAVELLERS = 12
MAX_VALID_DAYS = 90
MAX_MESSAGE_LENGTH = 1000
MAX_NAME_LENGTH = 120

# Deliberately permissive. A regex cannot decide whether an address exists, and
# a strict one mostly rejects valid addresses. This catches typing mistakes such
# as a missing "@" or a trailing comma; the send itself is the real test.
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")


class QuoteValidationError(Exception):
    """
    The request could not be turned into a quote.

    Carries the same code/message pair the API already returns to the frontend,
    so the route can hand it straight to error_response without translating.
    """

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def _money(value):
    """Whole dollars. Quotes are indicative, so cents would be false precision."""
    return int(round(float(value)))


def format_money(value):
    """A$6,135 — matches the formatting the final quote page already uses."""
    return "A$" + format(_money(value), ",")


def _long_date(value):
    """
    1 Dec 2026 — the format the final quote page already uses.

    Built from the day number rather than a %-d / %#d strftime code, because
    those two differ between macOS and Windows and the team runs both.
    """
    if not hasattr(value, "strftime"):
        return ""
    return f"{value.day} {value.strftime('%b %Y')}"


def _clean_text(value, limit):
    """Trim, drop control characters, and cap the length."""
    text = str(value or "").strip()
    text = "".join(char for char in text if char >= " " or char == "\n")
    return text[:limit]


def _require_email(value):
    email = _clean_text(value, 254)
    if not email:
        raise QuoteValidationError(
            "MISSING_EMAIL", "An email address is needed before the quote can be sent."
        )
    if not EMAIL_PATTERN.match(email):
        raise QuoteValidationError(
            "INVALID_EMAIL", f"{email} does not look like a valid email address."
        )
    return email


def _whole_number(value, field, minimum, maximum, default):
    if value in (None, ""):
        return default
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        raise QuoteValidationError("INVALID_NUMBER", f"{field} must be a number.")
    if number < minimum or number > maximum:
        raise QuoteValidationError(
            "INVALID_NUMBER", f"{field} must be between {minimum} and {maximum}."
        )
    return number


def _optional_date(value, field):
    """
    Reads a value from an <input type="date">, which always sends yyyy-mm-dd.

    An empty departure date is allowed — an agent may be quoting before the
    customer has settled on one — but a malformed date is not, because it would
    print as nonsense on a document going to a customer.
    """
    text = _clean_text(value, 32)
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        raise QuoteValidationError(
            "INVALID_DATE", f"{field} could not be read. Please pick a date again."
        )


def _load_package(package_id):
    """
    Reads the chosen package straight from the database.

    This is the point of the whole module: the price that ends up in the
    customer's inbox comes from here, never from the request body.
    """
    identifier = _clean_text(package_id, 120)
    if not identifier:
        raise QuoteValidationError(
            "MISSING_PACKAGE", "No package has been selected for this quote."
        )

    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM packages WHERE id = ?", (identifier,)
        ).fetchone()

    if row is None:
        raise QuoteValidationError(
            "UNKNOWN_PACKAGE",
            "That package is no longer available. Please choose another one.",
        )

    package = dict(row)
    # These three are stored as JSON strings, exactly as matching_service reads them.
    for field in ("inclusions", "highlights", "vibe_tags"):
        try:
            package[field] = json.loads(package.get(field) or "[]")
        except (TypeError, ValueError):
            package[field] = []
    return package


def calculate_totals(price_per_person, travellers):
    """
    The quote arithmetic, kept separate so a test can assert it directly.

    Booking fee is charged once per booking. Deposit is a share of the total,
    including the fee.
    """
    per_person = _money(price_per_person or 0)
    subtotal = per_person * travellers
    total = subtotal + BOOKING_FEE_AUD
    return {
        "per_person": per_person,
        "travellers": travellers,
        "subtotal": subtotal,
        "booking_fee": BOOKING_FEE_AUD,
        "total": total,
        "deposit": _money(total * DEPOSIT_RATE),
        "balance": total - _money(total * DEPOSIT_RATE),
    }


def build_reference(today=None):
    """
    FC-20260827-4F2A

    Readable enough for an agent to quote over the phone, and random enough
    that two quotes issued in the same second cannot collide.
    """
    stamp = (today or date.today()).strftime("%Y%m%d")
    return f"FC-{stamp}-{uuid.uuid4().hex[:4].upper()}"


def build_quote(payload, today=None):
    """
    Validates the request and returns the finished quote.

    Parameters:
        payload: The JSON body sent by the final quote page. Expected shape:
            {
                "customer": {"name": "...", "email": "...", "travellers": 2},
                "quote": {"departure": "2026-12-01", "valid_days": 14,
                          "message": "..."},
                "selected_package_id": "package-001"
            }

    Returns a dictionary the email templates, the PDF builder and the API
    response all read from. Raises QuoteValidationError on anything unusable.
    """
    if not isinstance(payload, dict):
        raise QuoteValidationError("INVALID_REQUEST", "The quote request was empty.")

    customer = payload.get("customer") if isinstance(payload.get("customer"), dict) else {}
    terms = payload.get("quote") if isinstance(payload.get("quote"), dict) else {}

    email = _require_email(customer.get("email"))
    name = _clean_text(customer.get("name"), MAX_NAME_LENGTH) or "there"
    travellers = _whole_number(
        customer.get("travellers"), "Travellers", 1, MAX_TRAVELLERS, 1
    )
    valid_days = _whole_number(
        terms.get("valid_days"), "Quote validity", 1, MAX_VALID_DAYS, 14
    )
    departure = _optional_date(terms.get("departure"), "Departure date")
    message = _clean_text(terms.get("message"), MAX_MESSAGE_LENGTH)

    package = _load_package(payload.get("selected_package_id"))
    totals = calculate_totals(package.get("price_from_aud"), travellers)

    issued_on = today or date.today()
    valid_until = issued_on + timedelta(days=valid_days)

    return {
        "reference": build_reference(issued_on),
        "issued_on": issued_on.isoformat(),
        "issued_on_display": _long_date(issued_on),
        "valid_days": valid_days,
        "valid_until": valid_until.isoformat(),
        "valid_until_display": _long_date(valid_until),
        "customer": {"name": name, "email": email, "travellers": travellers},
        "departure": departure.isoformat() if departure else None,
        "departure_display": _long_date(departure) if departure else "To be confirmed",
        "agent_message": message,
        "package": package,
        "totals": totals,
        # Pre-formatted so the email templates and the PDF cannot drift apart on
        # how a dollar figure is written.
        "money": {key: format_money(value) for key, value in totals.items()
                  if key != "travellers"},
    }
