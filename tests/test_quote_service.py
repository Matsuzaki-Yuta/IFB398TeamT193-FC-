"""
The pricing and validation rules.

These are the tests that matter most: they cover the figures that end up in a
customer's inbox, and they run in milliseconds because quote_service never
opens a socket.
"""

from datetime import date

import pytest

from backend.services.quote_service import (
    BOOKING_FEE_AUD, QuoteValidationError, build_quote, build_reference,
    calculate_totals, format_money,
)


def payload(package_id, **overrides):
    body = {
        "customer": {"name": "Jordan Lee", "email": "jordan@example.com",
                     "travellers": 2},
        "quote": {"departure": "2026-12-01", "valid_days": 14, "message": ""},
        "selected_package_id": package_id,
    }
    body.update(overrides)
    return body


# ── the arithmetic ────────────────────────────────────────────────────────────

def test_booking_fee_is_charged_once_not_per_traveller():
    one = calculate_totals(1000, 1)
    four = calculate_totals(1000, 4)
    assert one["booking_fee"] == BOOKING_FEE_AUD
    assert four["booking_fee"] == BOOKING_FEE_AUD
    assert four["subtotal"] == 4000


def test_deposit_is_twenty_percent_of_the_total_including_the_fee():
    totals = calculate_totals(1000, 2)
    assert totals["total"] == 2000 + BOOKING_FEE_AUD
    assert totals["deposit"] == round(totals["total"] * 0.20)
    assert totals["deposit"] + totals["balance"] == totals["total"]


def test_money_is_formatted_for_australian_dollars():
    assert format_money(12319) == "A$12,319"
    assert format_money(715.0) == "A$715"


def test_reference_is_dated_and_unique():
    first = build_reference(date(2026, 8, 27))
    second = build_reference(date(2026, 8, 27))
    assert first.startswith("FC-20260827-")
    assert first != second


# ── what the browser sends is not trusted ─────────────────────────────────────

def test_price_sent_by_the_browser_is_ignored(package_id):
    """
    The headline security rule for this feature.

    A customer can edit anything the page posts. The quote must be rebuilt from
    the database, so a price smuggled into the request body changes nothing.
    """
    honest = build_quote(payload(package_id))
    tampered_body = payload(package_id)
    tampered_body["package"] = {"price_from_aud": 1}
    tampered_body["totals"] = {"total": 1}
    tampered_body["price_from_aud"] = 1

    tampered = build_quote(tampered_body)
    assert tampered["totals"]["total"] == honest["totals"]["total"]
    assert tampered["totals"]["total"] > 1


# ── validation ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("email", ["", "   ", "not-an-email", "jordan@", "@example.com"])
def test_bad_email_is_rejected(package_id, email):
    body = payload(package_id)
    body["customer"]["email"] = email
    with pytest.raises(QuoteValidationError) as caught:
        build_quote(body)
    assert caught.value.code in {"MISSING_EMAIL", "INVALID_EMAIL"}


def test_unknown_package_is_rejected(package_id):
    with pytest.raises(QuoteValidationError) as caught:
        build_quote(payload("package-that-does-not-exist"))
    assert caught.value.code == "UNKNOWN_PACKAGE"


@pytest.mark.parametrize("travellers", [0, -3, 99])
def test_traveller_count_must_be_sensible(package_id, travellers):
    body = payload(package_id)
    body["customer"]["travellers"] = travellers
    with pytest.raises(QuoteValidationError):
        build_quote(body)


def test_malformed_departure_date_is_rejected(package_id):
    body = payload(package_id)
    body["quote"]["departure"] = "01/12/2026"
    with pytest.raises(QuoteValidationError) as caught:
        build_quote(body)
    assert caught.value.code == "INVALID_DATE"


def test_missing_departure_date_is_allowed(package_id):
    body = payload(package_id)
    body["quote"]["departure"] = ""
    quote = build_quote(body)
    assert quote["departure"] is None
    assert quote["departure_display"] == "To be confirmed"


def test_agent_message_is_capped(package_id):
    body = payload(package_id)
    body["quote"]["message"] = "x" * 5000
    assert len(build_quote(body)["agent_message"]) == 1000


# ── dates ─────────────────────────────────────────────────────────────────────

def test_validity_window_is_counted_from_the_issue_date(package_id):
    body = payload(package_id)
    body["quote"]["valid_days"] = 14
    quote = build_quote(body, today=date(2026, 8, 27))
    assert quote["valid_until"] == "2026-09-10"
    assert quote["valid_until_display"] == "10 Sep 2026"
