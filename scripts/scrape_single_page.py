import re, sqlite3, pathlib, requests
from bs4 import BeautifulSoup, Tag, NavigableString

URL = "https://fallout.fandom.com/wiki/Fallout_76_junk_items"
HEADERS = {"User-Agent": "ash-sql-learning/0.1 (personal, low-traffic)"}

DB = pathlib.Path(__file__).resolve().parents[1] / "data" / "fallout.sqlite"
SCHEMA = pathlib.Path(__file__).resolve().parents[1] / "sql" / "schema.sql"

QTY_RE = re.compile(r"^\s*(\d+)\s*(?:x|×)?\s*(.+?)\s*$", re.I)
FOOTNOTE_RE = re.compile(r"\[\d+\]")
QTY_AFTER_LINK = re.compile(r"\b(?:x|×)\s*(\d+)\b", re.I)
def clean_text(s: str) -> str:
    s = FOOTNOTE_RE.sub("", s or "")
    return " ".join(s.replace("\xa0", " ").split())

def parse_components_cell(cell: Tag):
    """
    Parse a components <td> that looks like:
    <a>Steel</a><br><a>Lead</a>
    or:
    <a>Steel</a> x2<br><a>Lead</a> x3
    Returns: list[(qty:int, name:str)]
    """
    groups, current = [], []
    for child in cell.children:
        if getattr(child, "name", None) == "br":
            if current:
                groups.append(current); current = []
            continue
        current.append(child)
    if current: # last group
        groups.append(current)

    results = []
    for nodes in groups:
        # Find the component link
        link = next((n for n in nodes if isinstance(n, Tag) and n.name == "a"), None)
        if not link:
            # fallback to plain text
            text = " ".join(str(n).strip() for n in nodes if isinstance(n, (NavigableString,)))
            text = re.sub(r"\s+", " ", text).strip(" .;")
            if text:
                # try "Name x2" pattern
                m = QTY_AFTER_LINK.search(text)
                qty = int(m.group(1)) if m else 1
                name = QTY_AFTER_LINK.sub("", text).strip()
                if name:
                    results.append((qty, name))
            continue
        
        name = link.get_text(strip=True)
        # Look for qty in the text immediately after the link (e.g., " x2")
        qty = 1
        sib = link.next_sibling
        if isinstance(sib, NavigableString):
            m = QTY_AFTER_LINK.search(str(sib))
            if m:
                qty = int(m.group(1))

        if name:
            results.append((qty, name))
    return results

def ensure_schema(conn: sqlite3.Connection):
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

TARGET = {"va-table", "va-table-center", "va-table-full"}

# Tag - bs4 type - has things like tag.name, tag.attrs, etc 
def has_all_classes(tag: Tag) -> bool:
    return (
        tag.name == "table"
        # issubset - return `True` if all elements of TARGET are present in passed set
        # set - converts the list into Python `set`
        # tag.get(attr_name, default) - return the attr value if exists - otherwise default 
        and TARGET.issubset(set(tag.get("class", [])))
    )

def main():
    DB.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB) as conn:
        ensure_schema(conn)

        html = requests.get(URL, headers=HEADERS, timeout=30)
        html.raise_for_status()
        soup = BeautifulSoup(html.text, "html.parser")
        # print("soup:", soup)
        # ---- Only the "Junk items" table ----
        anchor = soup.select_one("#Junk_items")  # <span id="Junk_items">
        if not anchor:
            raise SystemExit("Couldn't find #Junk_items anchor")
        # Walk forward to the first wikitable after the heading
        h3 = anchor.find_parent("h3")
        if not h3:
            raise RuntimeError("Could not find parent <h3> for #Junk_items")
        # From here find the next <table> with all the target classes
        table = h3.find_next(has_all_classes)
        #print("Table", table)
        
        if not table:
            raise RuntimeError("Couldn't find the va-table/center/full table")

        # map header indexes (Name + Components columns)
        header_cells = table.select("tr")[0].find_all(["th","td"])
        # Review note: List Comprehension (with a function call and method chaining)
        headers = [clean_text(h.get_text(" ", strip=True)).lower() for h in header_cells]
        try:
            name_idx = next(i for i,h in enumerate(headers) if h.startswith("name"))
            comp_idx = next(i for i,h in enumerate(headers) if "component" in h)
        except StopIteration:
            raise SystemExit(f"Unexpected headers: {headers}")

        # parse rows
        total_items, total_links = 0, 0
        for row in table.select("tr")[1:]:
            tds = row.find_all(["td","th"])
            if len(tds) <= max(name_idx, comp_idx): 
                continue

            name_cell = tds[name_idx]
            comp_cell = tds[comp_idx]

            a = name_cell.find("a")
            name = clean_text(a.get_text() if a else name_cell.get_text())
            if not name:
                continue
            url = None
            if a and a.has_attr("href"):
                url = a["href"]
                if url.startswith("/"):
                    url = "https://fallout.fandom.com" + url

            comps = parse_components_cell(comp_cell)
            print("Comps", comps)
            if not comps:
                continue

            with conn:
                cur = conn.cursor()
                item_id = upsert_item(cur, name, url)
                for qty, comp_name in comps:
                    comp_id = upsert_component(cur, comp_name)
                    set_item_scrap(cur, item_id, comp_id, qty)
                    total_links += 1
            total_items += 1

        print(f"Loaded {total_items} junk items with {total_links} component links.")

if __name__ == "__main__":
    main()
