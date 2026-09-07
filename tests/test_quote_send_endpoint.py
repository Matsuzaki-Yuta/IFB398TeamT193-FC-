"""
The endpoint, end to end, with the SMTP transport replaced by a recorder.

This is the test that proves the wiring: a POST from the page produces a
message addressed to the customer, carrying the PDF, without a mail server
being involved at any point.
"""

import json

import pytest

import backend.services.email_service as email_service
import backend.services.quote_mail as quote_mail
from backend.services.email_service import EmailConfigurationError, EmailSendError


@pytest.fixture
def outbox(monkeypatch):
    """Catches whatever would have been sent."""
    sent = []
    monkeypatch.setattr(
        quote_mail, "send_message", lambda message, settings=None: sent.append(message)
    )
    return sent


def body(package_id, **quote_overrides):
    quote = {"departure": "2026-12-01", "valid_days": 14, "message": "See you soon."}
    quote.update(quote_overrides)
    return {
        "customer": {"name": "Jordan Lee", "email": "jordan@example.com",
                     "travellers": 2},
        "quote": quote,
        "selected_package_id": package_id,
    }


def test_preview_endpoint_returns_the_quote_without_sending(client, package_id, outbox):
    response = client.post("/api/quote", json=body(package_id))
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["quote"]["reference"].startswith("FC-")
    assert outbox == []


def test_send_endpoint_emails_the_customer(client, package_id, smtp_env, outbox):
    response = client.post("/api/quote/send", json=body(package_id))
    assert response.status_code == 200

    data = response.get_json()
    assert data["success"] is True
    assert data["sent_to"] == "jordan@example.com"
    assert data["quote_reference"].startswith("FC-")
    assert data["total"].startswith("A$")

    assert len(outbox) == 1
    message = outbox[0]
    assert message["To"] == "jordan@example.com"
    assert data["quote_reference"] in message["Subject"]


def test_the_email_carries_the_pdf_and_both_body_parts(client, package_id, smtp_env, outbox):
    client.post("/api/quote/send", json=body(package_id))
    message = outbox[0]

    types = {part.get_content_type() for part in message.walk()}
    assert "text/plain" in types
    assert "text/html" in types

    pdfs = [p for p in message.walk() if p.get_content_type() == "application/pdf"]
    assert len(pdfs) == 1
    assert pdfs[0].get_payload(decode=True).startswith(b"%PDF")


def test_a_bad_email_address_is_refused_before_anything_is_sent(client, package_id, smtp_env, outbox):
    payload = body(package_id)
    payload["customer"]["email"] = "not-an-email"
    response = client.post("/api/quote/send", json=payload)
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "INVALID_EMAIL"
    assert outbox == []


def test_an_unconfigured_env_returns_503_not_500(client, package_id, monkeypatch, outbox):
    for key in ("SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "MAIL_FROM_EMAIL"):
        monkeypatch.delenv(key, raising=False)
    response = client.post("/api/quote/send", json=body(package_id))
    assert response.status_code == 503
    assert response.get_json()["error"]["code"] == "EMAIL_NOT_CONFIGURED"


def test_a_relay_failure_returns_502_with_a_safe_message(client, package_id, smtp_env, monkeypatch):
    def explode(message, settings=None):
        raise EmailSendError("connection refused")
    monkeypatch.setattr(quote_mail, "send_message", explode)

    response = client.post("/api/quote/send", json=body(package_id))
    assert response.status_code == 502
    error = response.get_json()["error"]
    assert error["code"] == "EMAIL_FAILED"
    # the technical detail stays in the server log, not in the customer's face
    assert "connection refused" not in error["message"]


def test_the_send_is_throttled(client, package_id, smtp_env, outbox):
    from backend.routes import api_routes
    api_routes._send_history.clear()

    codes = [
        client.post("/api/quote/send", json=body(package_id)).status_code
        for _ in range(api_routes.SEND_LIMIT + 2)
    ]
    assert codes[:api_routes.SEND_LIMIT] == [200] * api_routes.SEND_LIMIT
    assert codes[api_routes.SEND_LIMIT:] == [429, 429]


def test_email_status_never_leaks_the_password(client, smtp_env):
    response = client.get("/api/email/status")
    assert response.status_code == 200
    assert smtp_env["SMTP_PASSWORD"] not in response.get_data(as_text=True)
    assert response.get_json()["configured"] is True
