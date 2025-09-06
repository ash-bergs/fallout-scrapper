
import pathlib
from bs4 import BeautifulSoup, Tag

from .infra import db_conn, fetch_soup
from ..parsing_utils import clean_text

BASE = "https://fallout.fandom.com"

_NUM_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20,
}

def _parse_quantity(text:str) -> int | None:
    """
    If the description starts with a clear count word ('One', 'Two', ...),
    return that integer, else None (e.g., 'Over twenty', 'Sometimes', etc).
    """
    if not text:
        return None
    first = text.strip().lower().split()[0]
    return _NUM_WORDS.get(first)

def _first_location_link(li: Tag) -> Tag | None:
    """
    Heuristic: pick the first <a> in the top-level LI (not in a nested <ul>),
    skipping image links. If none, fall back to any <a>.
    """
    # Top-level anchors = descendants of li but not under its first nested <ul>
    direct_sub_ul = li.find("ul", recursive=False)
    for a in li.find_all("a", href=True):
        if a.find("img"): # sometimes these are imgs - skip
            continue
        parent_ul = a.find_parent("ul")
        if parent_ul is direct_sub_ul:
            # anchor is inside nested UL → skip for the "main" place
            continue
        return a
    return li.find("a", href=True)

def _iter_sub_points(li: Tag):
    sub_ul = li.find("ul", recursive=False)
    if not sub_ul:
        return
    for sub_li in sub_ul.find_all("li", recursive=False):
        yield sub_li

def _location_name_from_link(a: Tag) -> str:
    # Prefer title attribute, fallback to text
    title = a.get("title")
    return clean_text(title or a.get_text(" ", strip=True))

# DB Helpers

def _lookup_item(cur, item_name:str):
    row = cur.execute(
        "SELECT id, url FROM item WHERE name = ? COLLATE NOCASE",
        (item_name,)
    ).fetchone()
    return row

def _has_item_location(cur, item_id: int) -> bool:
    (cnt,) = cur.execute(
        "SELECT COUNT(*) FROM item_locations WHERE item_id = ?",
        (item_id,)
    ).fetchone()
    return cnt > 0

def _lookup_location_id_by_name(cur, name: str) -> int | None:
    row = cur.execute(
        "SELECT id FROM location WHERE name = ? COLLATE NOCASE",
        (name,)
    ).fetchone()
    return row[0] if row else None

def _insert_item_location(cur, item_id: int, location_id: int, description: str | None, quantity: int | None):
    cur.execute(
        """
        INSERT OR IGNORE INTO item_locations(item_id, location_id,description, quantity)
        VALUES (?, ?, ?, ?)
        """,
        (item_id, location_id, description, quantity)
    )


# Convenience wrapper - resolve item by name -> call scrape_item_locations
def scrape_item_locations_by_name(item_name:str, db_path:str | pathlib.Path | None = None) -> int:

    inserted = 0
    with db_conn(db_path) as conn:
        cur = conn.cursor()
        # Lookup the item, and get its ID and URL for search
        row = _lookup_item(cur, item_name)
        if not row:
            return 0
        item_id, item_url = row
    inserted = scrape_item_locations(item_id, item_url, db_path)

    return inserted

def scrape_item_locations(item_id: int, item_url: str, db_path: str | pathlib.Path | None = None) -> int:
    inserted = 0

    # See if we already have rows, skip if we do
    with db_conn(db_path) as conn:
        cur = conn.cursor()
        if _has_item_location(cur, item_id):
            return 0
        
    #Otherwise get the HTML
    soup: BeautifulSoup = fetch_soup(item_url)

    # Fine the LOCATIONS heading 
    span = soup.select_one("span.mw-headline#Locations")
    if not span:
        return 0
    h2 = span.find_parent("h2")
    if not h2:
        return 0
    
    # The first UL after the heading should be the list of places
    ul = h2.find_next("ul")
    if not ul:
        return 0
    
    # Parse the LIs and nested LIs
    with db_conn(db_path) as conn:
        cur = conn.cursor()
        for li in ul.find_all("li", recursive=False):
            a = _first_location_link(li)
            if not a:
                continue
            
            loc_name = _location_name_from_link(a)
            desc_text = clean_text(li.get_text(" ", strip=True))
            qty = _parse_quantity(desc_text)
        
            loc_id = _lookup_location_id_by_name(cur, loc_name)
            if loc_id is not None:
                _insert_item_location(cur, item_id, loc_id, desc_text, qty)
                inserted += 1

                # nested sub-points share the same location context
                for sub in _iter_sub_points(li):
                    sub_desc = clean_text(sub.get_text(" ", strip=True))
                    sub_qty = _parse_quantity(sub_desc)
                    _insert_item_location(cur, item_id, loc_id, sub_desc, sub_qty)
                    inserted += 1

    return inserted





