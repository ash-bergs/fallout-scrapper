import pathlib
from bs4 import BeautifulSoup
from ..parsing_utils import clean_text
from ..db_utils import ensure_schema
from .infra import db_conn, fetch_soup

BASE = "https://fallout.fandom.com"
URL = "https://fallout.fandom.com/wiki/Fallout_76_locations"

def main(db_path: str | pathlib.Path | None = None):
    soup: BeautifulSoup = fetch_soup(URL)
    # Anchor will be REGIONS heading 
    anchor = soup.select_one("#Regions")
    if not anchor:
        raise SystemExit("Couldn't find #Regions anchor")

    h2 = anchor.find_parent("h2")
    if not h2:
        raise RuntimeError("Could not find parent <h2> for #Regions")

    table = h2.find_next("table")
    if not table:
        raise RuntimeError("Couldn't find the Regions table")

    # parse regions from the Regions table
    regions: list[tuple[str, str]] = []
    for td in table.select("td"):
        links = [a for a in td.find_all("a", href=True) if not a.find("img")]
        if not links:
            continue
        a = links[-1]
        name = clean_text(a.get_text(" ", strip=True))
        if not name:
            continue
        url = a["href"]
        if url.startswith("/"):
            url = BASE + url
        regions.append((name, url))

    def parse_location_for_region(region_name: str) -> list[tuple[str, str]]:
        anchor_id = region_name.replace(" ", "_")
        span = soup.select_one(f"span.mw-headline#{anchor_id}")
        if not span:
            return []
        h3 = span.find_parent("h3")
        if not h3:
            return []

        def is_category_tree(tag) -> bool:
            return (
                tag.name == "div"
                and {"va-pagelist", "CategoryTreeTag"}.issubset(set(tag.get("class", [])))
            )

        tree = h3.find_next(is_category_tree)
        if not tree:
            return []

        links = [a for a in tree.find_all("a", href=True) if not a.find("img")]
        out: list[tuple[str, str]] = []
        for a in links:
            text = clean_text(a.get_text(" ", strip=True))
            if not text:
                continue
            # skip self-link
            if text.lower() == region_name.lower():  
                continue
            href = a["href"]
            if href.startswith("/"):
                href = BASE + href
            out.append((text, href))
        return out

    total_locations = 0

    # Open DB and ensure schema
    with db_conn(db_path, ensure_schema_fn=ensure_schema) as conn:
        with conn:
            cur = conn.cursor()
            # regions table upsert
            for name, url in regions:
                cur.execute("INSERT OR IGNORE INTO region(name, url) VALUES (?, ?)", (name, url))
                cur.execute("UPDATE region SET url = COALESCE(url, ?) WHERE name = ?", (url, name))

            # locations per region
            for region_name, _ in regions:
                region_id_row = cur.execute(
                    "SELECT id FROM region WHERE name = ?",
                    (region_name,),
                ).fetchone()
                if not region_id_row:
                    continue
                region_id = region_id_row[0]

                locations = parse_location_for_region(region_name)
                for location_name, location_url in locations:
                    cur.execute("""
                        INSERT INTO location(name, region_id, url)
                        VALUES (?, ?, ?)
                        ON CONFLICT(name, region_id)
                        DO UPDATE SET url = COALESCE(location.url, excluded.url)
                    """, (location_name, region_id, location_url))
                total_locations += len(locations)

    print(f"Loaded {len(regions)} regions and {total_locations} locations.")

if __name__ == "__main__":
    main()
