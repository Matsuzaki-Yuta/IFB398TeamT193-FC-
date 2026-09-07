"""
Shared test setup.

Nothing here touches the network. The SMTP settings below are fake and the one
test that exercises the send path replaces the transport, so the suite can run
on a laptop with no internet and in a marking environment with no .env file.
"""

import os
import sys

import pytest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from app import create_app

@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        "TESTING": True
    })
    return app
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

FAKE_SMTP = {
    "SMTP_HOST": "localhost",
    "SMTP_PORT": "1025",
    "SMTP_USERNAME": "tests@example.com",
    "SMTP_PASSWORD": "not-a-real-password",
    "MAIL_FROM_EMAIL": "tests@example.com",
    "MAIL_FROM_NAME": "Trip Bridge Tests",
}


@pytest.fixture
def smtp_env(monkeypatch):
    """Puts fake SMTP settings in the environment for the duration of a test."""
    for key, value in FAKE_SMTP.items():
        monkeypatch.setenv(key, value)
    return FAKE_SMTP


@pytest.fixture
def app():
    from app import create_app
    application = create_app()
    application.config.update(TESTING=True)
    return application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def package_id():
    """A real id from packages.db, so the tests exercise the real query."""
    from backend.models.database import get_connection
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id FROM packages WHERE price_from_aud > 0 LIMIT 1"
        ).fetchone()
    return row["id"]
