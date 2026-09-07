"""
Shared test setup.

Nothing here touches the network. The SMTP settings below are fake and the one
test that exercises the send path replaces the transport, so the suite can run
on a laptop with no internet and in a marking environment with no .env file.
"""
import os
import sys
import sqlite3

import pytest


PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)
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
def test_package_database(tmp_path, monkeypatch):
    db_path = tmp_path / "packages.db"

    connection = sqlite3.connect(db_path)

    connection.execute(
        """
        CREATE TABLE packages (
            id TEXT PRIMARY KEY,
            name TEXT,
            destination TEXT,
            price_from_aud REAL,
            inclusions TEXT,
            highlights TEXT,
            vibe_tags TEXT
        )
        """
    )

    connection.execute(
        """
        INSERT INTO packages (
            id,
            name,
            destination,
            price_from_aud,
            inclusions,
            highlights,
            vibe_tags
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "package-001",
            "Bali Escape",
            "Bali, Indonesia",
            2500,
            '["Hotel", "Breakfast"]',
            '["Beach", "Temple"]',
            '["Adventure", "Wellness"]',
        )
    )

    connection.commit()
    connection.close()

    monkeypatch.setattr(
        "backend.models.database.DB_PATH",
        str(db_path)
    )

    return db_path


@pytest.fixture
def package_id(test_package_database):
    return "package-001"
