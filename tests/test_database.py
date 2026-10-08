import sqlite3

from . import database


def test_database_connection(
    tmp_path,
    monkeypatch
):
    db_path = tmp_path / "test_packages.db"

    connection = sqlite3.connect(db_path)

    connection.execute(
        """
        CREATE TABLE packages (
            id TEXT PRIMARY KEY,
            destination TEXT
        )
        """
    )

    connection.execute(
        """
        INSERT INTO packages (
            id,
            destination
        )
        VALUES (?, ?)
        """,
        (
            "package-001",
            "Bali, Indonesia"
        )
    )

    connection.commit()
    connection.close()

    monkeypatch.setattr(
        database,
        "DB_PATH",
        str(db_path)
    )

    connection = database.get_connection()

    package = connection.execute(
        """
        SELECT *
        FROM packages
        WHERE id = ?
        """,
        ("package-001",)
    ).fetchone()

    connection.close()

    assert package is not None
    assert package["id"] == "package-001"
    assert package["destination"] == "Bali, Indonesia"