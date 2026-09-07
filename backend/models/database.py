import os
import sqlite3

# database.py sits at backend/models/, which is two folders below the repo root
# where packages.db actually lives. Walking up from __file__ means the path is
# right no matter which directory "python app.py" was run from.
#
# Previously this joined packages.db onto backend/models/, which does not exist.
# sqlite3.connect() creates a missing file instead of failing, so the app came
# up cleanly and then threw "no such table: packages" on the first match.
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

# The override exists so tests can point at a throwaway copy of the database.
DB_PATH = os.environ.get("PACKAGES_DB_PATH") or os.path.join(
    PROJECT_ROOT, "packages.db"
)


def get_connection():
    """
    Opens the package database.

    Raises FileNotFoundError when the database is missing rather than letting
    sqlite3 create an empty one, so a wrong path fails loudly and immediately
    instead of surfacing later as a confusing "no such table" error.
    """
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            f"Package database not found at {DB_PATH}. "
            "packages.db should sit in the project root beside app.py."
        )

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection
