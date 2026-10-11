"""
The real package catalogue that ships with the app.

Every other test builds its own temporary database, so if packages.db were
moved or renamed those tests would still pass while the running app failed.
This test opens the shipped file from the place the app looks for it.
"""
import os
import sqlite3

from backend.models import database


def test_shipped_catalogue_is_where_the_app_looks():
    default_path = os.path.join(database.PROJECT_ROOT, "packages.db")

    assert os.path.isfile(default_path), (
        "packages.db must sit in the project root beside app.py"
    )

    connection = sqlite3.connect(default_path)
    try:
        count = connection.execute("SELECT COUNT(*) FROM packages").fetchone()[0]
    finally:
        connection.close()

    assert count > 0
