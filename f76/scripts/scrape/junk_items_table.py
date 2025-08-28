import os, sqlite3, pathlib, requests
from bs4 import BeautifulSoup
# Note: when Python runs a file, it will compile it into bytecode (.pyc files)
# This makes it faster to load these modules next time. Compiled files live in `__pycache__`
from ..parsing_utils import clean_text, has_all_classes, parse_components_cell
from ..db_utils import ensure_schema, upsert_component, upsert_item, set_item_scrap

URL = "https://fallout.fandom.com/wiki/Fallout_76_junk_items"
HEADERS = {"User-Agent": "ash-sql-learning/0.1 (personal, low-traffic)"}

def default_repo_db() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[3] / "data" / "fallout.sqlite"

def main(db_path: str | pathlib.Path | None = None):
    # 1) CLI arg > 2) env var > 3) repo default
    DB = pathlib.Path(db_path) if db_path else pathlib.Path(
        os.environ.get("F76_DB_TARGET") or default_repo_db()
    )
    
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
        # Is there a better strategy for getting the right table? It has no unique ID 
        table = h3.find_next(has_all_classes)
        # print("Table", table)
        
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
            # print("Comps", comps)
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
