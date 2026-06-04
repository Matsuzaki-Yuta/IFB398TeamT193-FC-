"""
Run this once to create / refresh packages.db from flight_centre_packages.json.
Usage: python seed_db.py
"""
import json, sqlite3, os

BASE = os.path.dirname(__file__)
JSON_PATH = os.path.join(BASE, "flight_centre_packages.json")
DB_PATH   = os.path.join(BASE, "packages.db")

conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()

cur.execute('''CREATE TABLE IF NOT EXISTS packages (
    id             TEXT PRIMARY KEY,
    category       TEXT,
    name           TEXT,
    destination    TEXT,
    duration_nights INTEGER,
    price_from_aud  REAL,
    summary        TEXT,
    inclusions     TEXT,   -- JSON array stored as text
    highlights     TEXT,   -- JSON array stored as text
    vibe_tags      TEXT,   -- JSON array stored as text
    image_url      TEXT,
    url            TEXT
)''')

with open(JSON_PATH) as f:
    packages = json.load(f)

inserted = 0
for p in packages:
    cur.execute('''INSERT OR REPLACE INTO packages VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''', (
        p.get('id'),
        p.get('category'),
        p.get('name'),
        p.get('destination'),
        p.get('duration_nights'),
        p.get('price_from_aud'),
        p.get('summary'),
        json.dumps(p.get('inclusions') or []),
        json.dumps(p.get('highlights') or []),
        json.dumps(p.get('vibe_tags') or []),
        p.get('image_url'),
        p.get('url'),
    ))
    inserted += 1

conn.commit()
conn.close()
print(f"Done — {inserted} packages written to {DB_PATH}")
