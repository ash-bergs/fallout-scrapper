import pathlib
from bs4 import BeautifulSoup

from .infra import db_conn, fetch_soup
from ..parsing_utils import clean_text, has_all_classes, parse_components_cell
from ..db_utils import ensure_schema, upsert_enemy_groups

URL = "https://fallout.fandom.com/wiki/Fallout_76_creatures"

# We know there are 3 categories, so we'll just hardcode them
ENEMY_CATEGORIES = ["Humans", "Creatures", "Robots"]

def parse_enemy_groups(soup: BeautifulSoup, category: str) -> list[tuple[str, str | None]]:
    """
    Given a category, finds the next available table under that heading.
    Returns a list of (group_name, url).

    Excludes "Other"
    """
    # TODO: Broaden, single use for now
    anchor = soup.select_one(f"span.mw-headline#{category}")
    if not anchor:
        raise RuntimeError(f"Couldn't find {category} anchor")
    
    h2 = anchor.find_parent("h2")
    table = h2.find_next("table", class_="va-table")
    if not table:
        raise RuntimeError(f"Couldn't {category} find table")
    
    groups: list[tuple[str, str | None]] = []
    for row in table.select("tr"):
        th = row.find("th", colspan="3")
        if not th:
            continue
        # Table row has a link with the enemy group name
        a = th.find("a")
        if a:
            name = clean_text(a.get_text(" ", strip=True))
            url = a.get("href")
            if url and url.startswith("/"):
                url = "https://fallout.fandom.com" + url
        else:
            name = clean_text(th.get_text(" ", strip=True))
            url = None
        # Other doesn't really help us, but will have to decide how to handle these couple of enemies
        if name and name.lower() != "other":
            groups.append((name, url))
    return groups

def main(db_path: str | pathlib.Path | None = None):
    soup: BeautifulSoup = fetch_soup(URL)

    #print("Soup 🍲: ", soup)    
    # Make sure enemy categories present in HTML
    for category in ENEMY_CATEGORIES:
        anchor = soup.select_one(f"span.mw-headline#{category}")
        if not anchor:
            raise SystemExit(f"Couldn't find {category} anchor")

    # We can go ahead and load these into the database
    with db_conn(db_path, ensure_schema_fn=ensure_schema) as conn:
        with conn:
            cur = conn.cursor()
            for category in ENEMY_CATEGORIES:
                cur.execute(
                    """
                    INSERT INTO enemy_category (name)
                    VALUES (?)
                    ON CONFLICT(name) DO NOTHING
                    """,
                    (category,),
                )
    print(f"Loaded {len(ENEMY_CATEGORIES)} enemy categories.")
    
    human_groups = parse_enemy_groups(soup, "Humans")
    robot_groups = parse_enemy_groups(soup, "Robots")
    
    with db_conn(db_path, ensure_schema_fn=ensure_schema) as conn:
        with conn:
            cur = conn.cursor()
            upsert_enemy_groups(cur, "Humans", human_groups) 
            upsert_enemy_groups(cur, "Robots", robot_groups)

    # TODO: Creatures 
    # Sometimes, in the case of Creatures, we find various subheadings:
    # <span class="mw-headline" id="Animals">Animals</span> - these are h3's
    # There is animals, Bugs and insects, cryptids, etc. 
    # It's the only one structured like this

if __name__ == "__main__":
    main()
