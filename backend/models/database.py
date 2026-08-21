import os
import sqlite3


DB_PATH = os.path.join(os.path.dirname(__file__), "packages.db")


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection