import sqlite3, pathlib

# Path to the SQL schema def. file
# `pathlib.Path(__file__)` - current file location
# `.resolve().parents[1]` - go up 2 levels (current -> scripts/ -> project root)
# `/ "sql" / "schema.sql"` - append path to the schema file
# In short: Computing & storing the absolute path to the schema
# Docs: https://docs.python.org/3/library/pathlib.html
SCHEMA = pathlib.Path(__file__).resolve().parents[1] / "sql" / "schema.sql"

def ensure_schema(conn: sqlite3.Connection):
    """
    Ensure that the databse has the correct schema.
    - Enables foreign key support (disabled by default in SQLite)
    - Executes the schema.sql to create tables if they don't exist

    SQLite Pragma docs: https://www.sqlite.org/pragma.html
    """
    conn.execute("PRAGMA foreign_keys=ON;")
    with open(SCHEMA, "r", encoding="utf-8") as f:
        conn.executescript(f.read())

def upsert_item(cur, name: str, url: str | None) -> int:
    """
    Insert or Update an item by name
    - It an item with the given name exists, return the ID
    - If an item exists but does not have a record URL record, update it.
    - Or insert a new row and return the ID
    """
    # Look up if already exists by name - parameterized query
    # fetchone() returns a single row or `None`
    row = cur.execute("SELECT id FROM item WHERE name = ?", (name,)).fetchone()
    if row:
        if url:
            # COALESCE returns the first non-NULL argument 
            # Only update if `url` column is currently NULL.
            # Docs: https://sqlite.org/lang_corefunc.html#coalesce
            cur.execute("UPDATE item SET url = COALESCE(url, ?) WHERE id = ?", (url, row[0]))
        return row[0]
    cur.execute("INSERT INTO item(name, url) VALUES (?,?)", (name, url))
    return cur.lastrowid

def upsert_component(cur, name: str) -> int:
    """
    Insert a new component if it doesn't already exist
    Returns the value of the component ID column either way
    """
    row = cur.execute("SELECT id FROM component WHERE name = ?", (name,)).fetchone()
    if row: return row[0]
    cur.execute("INSERT INTO component(name) VALUES (?)", (name,))
    return cur.lastrowid

def set_item_scrap(cur, item_id: int, component_id: int, qty: int):
    """
    Set the scrap quantity for a given `item` -> `component` mapping
    - Uses SQLite's UPSERT capability, which we're implementing through:
    `INSERT .... ON CONFLICT .... DO UPDATE` syntax

    Flow:
    - `INSERT INTO item_scraps(item_id, component_id, quantity)` 
      - try to add a new row to item_scraps 
      recording a junk item and component quantity 
    - `ON CONFLICT(item_id, component_id)` 
      - There's been a conflict because of a UNIQUE or PRIMARY KEY conflict
      - i.e. if you find a record for this item and component 
      mapping already exists
    - `DO UPDATE SET quantity = excluded.quantity`
      - Set the quantity to most current data
      - 🗒️ Note on `excluded` & `UPSERT` below
    """
    
    cur.execute("""
        INSERT INTO item_scraps(item_id, component_id, quantity)
        VALUES (?,?,?)
        ON CONFLICT(item_id, component_id) 
        DO UPDATE SET quantity = excluded.quantity
    """, (item_id, component_id, qty))

"""
SQLite Fundamentals this module uses

- 🆙 `UPSERT`: 
  - Docs: https://sqlite.org/lang_upsert.html
  - "An UPSERT is an ordinary INSERT statement that is followed 
  by one or more ON CONFLICT clauses" 
  - `excluded` - a special table alias automatically available 
  inside the `DO UPDATE` clause of an `ON CONFLICT`
    - When we try to upsert a row and we find a conflict SQLite does 2 things:
    1. Keeps the existing row in the real table unchanged for now
    2. Makes the row we *tried* to insert available in a special table called `excluded`
"""