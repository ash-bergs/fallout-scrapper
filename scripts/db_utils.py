import re
import sqlite3, pathlib

SCHEMA = pathlib.Path(__file__).resolve().parents[1] / "sql" / "schema.sql"
FOOTNOTE_RE = re.compile(r"\[\d+\]")

def ensure_schema(conn: sqlite3.Connection):
    # PRAGMA context - https://www.sqlite.org/pragma.html
    conn.execute("PRAGMA foreign_keys=ON;")
    with open(SCHEMA, "r", encoding="utf-8") as f:
        conn.executescript(f.read())

def upsert_item(cur, name: str, url: str | None) -> int:
    # Look up if already exists by name - parameterized query
    # fetchone() returns a single row or `None`
    row = cur.execute("SELECT id FROM item WHERE name = ?", (name,)).fetchone()
    if row:
        if url:
            # If the row exists but it doesn't have a URL and the new one does, add it
            # COALESCE - Returns the first non-null value in the arguments list 
            cur.execute("UPDATE item SET url = COALESCE(url, ?) WHERE id = ?", (url, row[0]))
        return row[0]
    cur.execute("INSERT INTO item(name, url) VALUES (?,?)", (name, url))
    return cur.lastrowid

def upsert_component(cur, name: str) -> int:
    # Insert component if it doesn't already exist
    row = cur.execute("SELECT id FROM component WHERE name = ?", (name,)).fetchone()
    if row: return row[0]
    cur.execute("INSERT INTO component(name) VALUES (?)", (name,))
    return cur.lastrowid

def set_item_scrap(cur, item_id: int, component_id: int, qty: int):
    cur.execute("""
        INSERT INTO item_scraps(item_id, component_id, quantity)
        VALUES (?,?,?)
        ON CONFLICT(item_id, component_id) DO UPDATE SET quantity = excluded.quantity
    """, (item_id, component_id, qty))
