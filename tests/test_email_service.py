"""
Message assembly. No connection is opened anywhere in this file.
"""

import pytest

from backend.services.email_service import (
    EmailConfigurationError, build_message, load_settings,
)


def test_missing_settings_name_every_missing_key(monkeypatch):
    for key in ("SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "MAIL_FROM_EMAIL"):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(EmailConfigurationError) as caught:
        load_settings()
    message = str(caught.value)
    assert "SMTP_HOST" in message and "MAIL_FROM_EMAIL" in message


def test_a_from_address_that_gmail_would_rewrite_is_flagged(smtp_env, monkeypatch):
    monkeypatch.setenv("MAIL_FROM_EMAIL", "noreply@flightcentre.com")
    assert load_settings().get("from_mismatch") is not None


def test_message_carries_both_a_text_and_an_html_part(smtp_env):
    message = build_message(
        "customer@example.com", "Your quote", "plain text", "<p>html</p>"
    )
    types = {part.get_content_type() for part in message.walk()}
    assert "text/plain" in types
    assert "text/html" in types


def test_attachment_is_carried_with_its_filename(smtp_env):
    message = build_message(
        "customer@example.com", "Your quote", "text", "<p>html</p>",
        attachments=[("Quote-FC-1.pdf", "application/pdf", b"%PDF-1.4 fake")],
    )
    attachments = [
        part for part in message.walk()
        if part.get_filename() == "Quote-FC-1.pdf"
    ]
    assert len(attachments) == 1
    assert attachments[0].get_content_type() == "application/pdf"


def test_headers_are_set(smtp_env):
    message = build_message("customer@example.com", "Your quote", "t", "<p>h</p>")
    assert message["To"] == "customer@example.com"
    assert "Trip Bridge Tests" in message["From"]
    assert message["Message-ID"]
