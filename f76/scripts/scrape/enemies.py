import pathlib
from bs4 import BeautifulSoup

from .infra import db_conn, fetch_soup
from ..parsing_utils import clean_text
from ..db_utils import ensure_schema, upsert_enemy_groups

URL = "https://fallout.fandom.com/wiki/Fallout_76_creatures"

# ---- Hardcoded Enemy Categories & Families ----
# Manually recorded for simplicity 
# TODO: Consider fetching dynamically 
ENEMY_CATEGORIES = ["Humans", "Creatures", "Robots"]

ENEMY_FAMILIES = [
    "Animals",
    "Bugs and insects",
    "Cryptids",
    "Mirelurks",
    "Ghouls",
    "Lost",
    "Mole miners",
    "Scorched",
    "Super mutants",
    "Other" # For some reason this is Deathclaws, Floaters, and other significant enemies - need to be captured
]
    
def parse_enemy_groups(soup: BeautifulSoup, category: str) -> list[tuple[str, str | None]]:
    """
    Given a category or family, finds the next available table under that heading.
    Returns a list of (group_name, url).

    Excludes "Other"
    """
    # Ids for multi words become: Bugs_and_insects
    anchor_id = category.replace(" ", "_")
    anchor = soup.select_one(f"span.mw-headline#{anchor_id}")
    if not anchor:
        raise RuntimeError(f"Couldn't find {category} anchor")
    
    # find_parent accepts a dictionary of filter on attr values
    h2 = anchor.find_parent(["h2", "h3"])
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

    # Validate categories and families exist as headings on the page
    for category in ENEMY_CATEGORIES:
        anchor = soup.select_one(f"span.mw-headline#{category}")
        if not anchor:
            raise SystemExit(f"Couldn't find {category} enemy category anchor")
    for family in ENEMY_FAMILIES:
        anchor = soup.select_one(f"span.mw-headline#{category}")
        if not anchor:
            raise SystemExit(f"Couldn't find {category} enemy family anchor")

    # Insert enemy categories
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

            # Insert enemy families - only for Creatures at this time
            # Get the category id for Creatures - the only one with families
            category_row = cur.execute(
                "SELECT id FROM enemy_category WHERE name = ?",
                ("Creatures",)
            ).fetchone()

            if not category_row:
                raise RuntimeError("Missing 'Creatures' category in the DB!")
            
            category_id = category_row[0]

            for family in ENEMY_FAMILIES:
                cur.execute(
                    """
                    INSERT INTO enemy_family (category_id, name)
                    VALUES (?, ?)
                    ON CONFLICT(category_id, name) DO NOTHING
                    """,
                    (category_id, family)
                )
            print(f"Loaded {len(ENEMY_FAMILIES)} enemy families for Creatures category")

            # Parse and insert enemy groups for Humans and Robots
            human_groups = parse_enemy_groups(soup, "Humans") 
            robot_groups = parse_enemy_groups(soup, "Robots")
            upsert_enemy_groups(cur, "Humans", human_groups) 
            upsert_enemy_groups(cur, "Robots", robot_groups)
            # Parse and insert the enemy groups for each Creature family
            for family in ENEMY_FAMILIES:
                groups = parse_enemy_groups(soup, family)
                upsert_enemy_groups(cur, "Creatures", groups, family)

if __name__ == "__main__":
    main()
