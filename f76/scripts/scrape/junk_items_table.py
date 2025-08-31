import pathlib
from bs4 import BeautifulSoup
# Note: when Python runs a file, it will compile it into bytecode (.pyc files)
# This makes it faster to load these modules next time. Compiled files live in `__pycache__`
from .infra import db_conn, fetch_soup
from ..parsing_utils import clean_text, has_all_classes, parse_components_cell
from ..db_utils import ensure_schema, upsert_component, upsert_item, set_item_scrap

URL = "https://fallout.fandom.com/wiki/Fallout_76_junk_items"

def main(db_path: str | pathlib.Path | None = None):
    soup: BeautifulSoup = fetch_soup(URL)

    # Find the "Junk Items" table 
    anchor = soup.select_one("#Junk_items")
    if not anchor:
        raise SystemExit("Couldn't find #Junk_items anchor")
    
    h3 = anchor.find_parent("h3")
    if not h3:
        raise RuntimeError("Could not find parent <h3> for #Junk_items")
    
    table = h3.find_next(has_all_classes)
    if not table:
        raise RuntimeError("Couldn't find the va-table/center/full table")
    
    header_cells = table.select("tr")[0].find_all(["th", "td"])
    headers = [clean_text(h.get_text(" ", strip=True)).lower() for h in header_cells]

    try:
        name_idx = next(i for i,h in enumerate(headers) if h.startswith("name"))
        comp_idx = next(i for i,h in enumerate(headers) if "component" in h)
    except StopIteration:
        raise SystemExit(f"Unexpected headers: {headers}")
    
    total_items, total_links = 0, 0

    # Open DB and ensure schema
    with db_conn(db_path, ensure_schema_fn=ensure_schema) as conn:
        for row in table.select("tr")[1:]:
            tds = row.find_all(["td", "th"])
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
