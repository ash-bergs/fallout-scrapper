import os, pathlib, typer
from rich.console import Console

from .cli_utils.cli_presentation import make_pipboy_table
from .scripts.scrape.junk_items_table import main as scrape_junk_items
from .scripts.scrape.regions_and_locations import main as scrape_regions_and_locations
from .scripts.scrape.junk_locations import scrape_item_locations_by_name
from .scripts.scrape.enemies import main as scrape_enemy_categories
from .scripts.db_utils import fetch_all
from rich import box

app = typer.Typer(help="Fallout 76 Personal Data Assistant")
# Create sub app for registering our different items that can be acted on
enemy_app = typer.Typer(help="Explore & analyze enemies")
junk_app = typer.Typer(help="Explore & analyze junk items")
location_app = typer.Typer(help="Explore & analyze locations")
region_app = typer.Typer(help="Explore and analyze regions of Appalachia")
scrap_app = typer.Typer(help="Explore & analyze scrap/components")

app.add_typer(enemy_app, name="enemy")
app.add_typer(junk_app, name="junk")
app.add_typer(location_app, name="location")
app.add_typer(region_app, name="region")
app.add_typer(scrap_app, name="scrap")

console = Console()

def default_data_dir() -> pathlib.Path:
    base = pathlib.Path.home() / ".local" / "share" / "f76"  # fine on mac/Linux
    # on Windows can use: Path(os.environ.get("APPDATA", "~")) / "f76"
    return base

def resolve_db_path(db_opt: str | None = None) -> pathlib.Path:
    # CLI flag
    if db_opt:
        return pathlib.Path(db_opt)

    # env var
    env = os.environ.get("F76_DB")
    if env:
        return pathlib.Path(env)

    # Repo dev path (works when running in the repo)
    repo_db = pathlib.Path(__file__).resolve().parents[1] / "data" / "fallout.sqlite"
    if repo_db.exists():
        return repo_db

    # user data dir fallback
    return default_data_dir() / "fallout.sqlite"

# ---- Junk Commands ⏰ ----
@junk_app.command("scrap")
def scrap(item: str, db: str | None = typer.Option(None, help="Path to fallout.sqlite")):
    """
    Look up what components a Junk Item will scrap into (example: `f76 junk scrap 'soap'`)
    """
    q = """
    SELECT c.name, s.quantity
    FROM item i
    JOIN item_scraps s ON s.item_id = i.id
    JOIN component   c ON c.id = s.component_id
    WHERE i.name = ? COLLATE NOCASE
    ORDER BY c.name;
    """
    db_path = resolve_db_path(db)
    rows, _ = fetch_all(db_path, q, (item,))
    if not rows:
        console.print(f"[bold]No scraps found for:[/bold] {item} (DB: {db_path})")
        raise typer.Exit(1)
    t = make_pipboy_table(f'"{item}" scraps for:')
    t.add_column(f"{item.title()} components", no_wrap=True); t.add_column("Qty", justify="right", no_wrap=True)
    for comp, qty in rows:
        t.add_row(comp, str(qty))
    console.print(t)

@junk_app.command("find")
def where(item: str, db: str | None = typer.Option(None, help="Path to fallout.sqlite")):
    """
    List locations where a junk item can be found (example `f76 junk find 'soap'`)
    """
    db_path = resolve_db_path(db)
    # lazy pop: scrape if we have no rows
    q_check = "SELECT COUNT(*) FROM item_locations il JOIN item i ON i.id = il.item_id WHERE i.name = ? COLLATE NOCASE"
    rows, _ = fetch_all(db_path, q_check, (item,))
    if rows[0][0] == 0:
        scrape_item_locations_by_name(item, db_path)

    # run the search now that we know we have the data
    q = """
    SELECT l.name, il.quantity, il.description
    FROM item_locations il
    JOIN item i ON i.id = il.item_id
    JOIN location l ON l.id = il.location_id
    WHERE i.name = ? COLLATE NOCASE
    ORDER BY l.name, il.quantity IS NULL, COALESCE(il.quantity, 0) DESC;
    """
    results, _ = fetch_all(db_path, q, (item,))
    if not results:
        console.print(f"[bold]No locations for {item}.[/bold]")
        raise typer.Exit(1)
    t = make_pipboy_table(f'You will find {item} in the following locations:')
    # Build table columns
    t.add_column("Location")
    t.add_column("Qty", justify="right")
    t.add_column("Description", overflow="fold")
    # Populate the rows
    for (loc_name, qty, desc) in results:
        t.add_row(loc_name, str(qty) if qty is not None else "-", desc)
    console.print(t)
        
# ---- Scrap Commands 🛠️ ----
@scrap_app.command("sources")
def sources(component: str, db: str | None = typer.Option(None, help="Path to fallout.sqlite")):
    """
    Look up what Junk Items are a source of a given component (example: `f76 scrap sources 'lead'`)
    """
    q = """
    SELECT i.name, s.quantity
    FROM component c
    JOIN item_scraps s ON s.component_id = c.id
    JOIN item        i ON i.id = s.item_id
    WHERE c.name = ? COLLATE NOCASE
    ORDER BY s.quantity DESC, i.name;
    """
    db_path = resolve_db_path(db)
    rows, _ = fetch_all(db_path, q, (component,)) 
    if not rows:
        console.print(f"[bold]No items found for component:[/bold] {component} (DB: {db_path})")
        raise typer.Exit(1)
    t = make_pipboy_table(f'Items that yield "{component}":')
    t.add_column("Item"); t.add_column("Qty", justify="right")
    for item_name, qty in rows:
        t.add_row(item_name, str(qty))
    console.print(t)

# ---- Enemy Commands 🙈 ----
@enemy_app.command("list")
def list_enemies(category: str, db: str | None = typer.Option(None, help="Path to fallout.sqlite")):
    """
    Look up what enemy groups are in each category (example: `f76 enemy list 'humans'`)
    Hint: Categories are currently: Humans, Robots, and Creatures.
    """
    db_path = resolve_db_path(db)

    # handle differently for Creatures - expanded print out
    if category.lower() == "creatures":
        q = """
        SELECT f.name AS family_name, g.name AS group_name
        FROM enemy_category c
        JOIN enemy_family f ON f.category_id = c.id
        LEFT JOIN enemy_group g ON g.family_id = f.id
        WHERE c.name = ? COLLATE NOCASE
        ORDER BY f.name, g.name
        """
        rows, _ = fetch_all(db_path, q, (category,))

        if not rows:
            console.print(f"[bold]No creature families or groups found (DB: {db_path})")
            raise typer.Exit(1)

        t = make_pipboy_table(f"Creature enemy groups by family:")
        t.add_column("Family")
        t.add_column("Group")

        for family_name, group_name in rows:
            t.add_row(family_name or "-", group_name or "-")

        console.print(t)
        return

    # Default handing for Humans/Robots
    q ="""
    SELECT g.name
    FROM enemy_category c
    JOIN enemy_group g ON g.category_id = c.id
    WHERE c.name = ? COLLATE NOCASE
    ORDER BY g.name
    """
    rows, _ = fetch_all(db_path, q, (category,)) 
    if not rows:
        console.print(f"[bold]No enemies found for category:[/bold] {category} (DB: {db_path})")
        raise typer.Exit(1)
    t = make_pipboy_table(f"Enemies in {category} category:")
    t.add_column(f"Enemies ({category})");
    for (enemy_name,) in rows:
        t.add_row(enemy_name)
    console.print(t)

# ---- Location Commands 📍 ----
@location_app.command("find")
def region_for(location: str,db: str | None = typer.Option(None, help="Path to fallout.sqlite")):
    """
    Look up what region a location exists in. (example: `f76 location find 'Wade Airport'`)
    """
    q = """
    SELECT r.name
    FROM region r
    JOIN location l ON l.region_id = r.id
    WHERE l.name = ? COLLATE NOCASE
    """
    db_path = resolve_db_path(db)
    rows, _ = fetch_all(db_path, q, (location,))
    if not rows:
        console.print(f"[bold]No region found for location:[/bold] {location.title()} (DB: {db_path})")
        raise typer.Exit(1)
    t = make_pipboy_table(f'{location.title()} is located in:')
    t.add_column("Region");
    # fetchall returns a list of tuples - even for one col
    for (region,) in rows:
        t.add_row(region)
    console.print(t)

# ---- Region Commands 🗺️ ---- 
# Conceptually different from the ones above - "find doesn't fit in as well here"
@region_app.command("locations")
def locations_in(region: str,db: str | None = typer.Option(None, help="Path to fallout.sqlite")):
    """
    Look up what locations are in a region of the map (example: `f76 region locations 'Cranberry Bog'`)
    """
    q = """
    SELECT l.name
    FROM location l
    JOIN region r ON l.region_id = r.id
    WHERE r.name = ? COLLATE NOCASE
    ORDER BY l.name
    """
    db_path = resolve_db_path(db)
    rows, _ = fetch_all(db_path, q, (region,))
    if not rows:
        console.print(f"[bold]No locations found for region:[/bold] {region.title()}")
        raise typer.Exit(1)
    t = make_pipboy_table(f'{region.title()} is home to the following locations:')
    t.add_column("Locations");
    for (location_name,) in rows:
        t.add_row(location_name)
    console.print(t)

@region_app.command("list")
def locations_in(db: str | None = typer.Option(None, help="Path to fallout.sqlite")):
    """
    List all the regions of the map (example: `f76 region list`)
    """
    q = """
    SELECT r.name
    FROM region r
    ORDER BY r.name
    """
    db_path = resolve_db_path(db)
    rows, _ = fetch_all(db_path, q)
    if not rows:
        console.print(f"[bold]No regions found.[/bold] Have you ran `f76 init`?")
        raise typer.Exit(1)
    t = make_pipboy_table(f'You will find the following Regions in Appalachia:')
    t.add_column("Regions");
    for (region_name,) in rows:
        t.add_row(region_name)
    console.print(t)

@app.command("init")
def init(db: str | None = typer.Option(None, help="Path to fallout.sqlite")):
    """
    Create/populate the database by running the scraper once.
    """
    db_path = resolve_db_path(db)
    # Pass the target path via env var 
    os.environ["F76_DB_TARGET"] = str(db_path)
    console.print(f"Initializing DB at: {db_path}")
    console.print("\n")
    console.print(f"Preparing to initialize Scrap & Junk Items")
    scrape_junk_items(db_path)
    console.print("\n")
    console.print(f"Preparing to initialize Regions & Locations")
    scrape_regions_and_locations(db_path)
    console.print("\n")
    console.print(f"Preparing to initialize Enemy data")
    scrape_enemy_categories(db_path)
    console.print("[green]Done.[/green]")