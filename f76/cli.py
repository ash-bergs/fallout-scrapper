import os, pathlib, typer
from rich.console import Console
from rich.table import Table
from .scripts.scrape.junk_items_table import main as scrape_junk_items
from .scripts.scrape.regions_and_locations import main as scrape_regions_and_locations
from .scripts.db_utils import fetch_all

app = typer.Typer(help="Fallout 76 Personal Data Assistant")
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

@app.command("scrap")
def scrap(item: str, db: str | None = typer.Option(None, help="Path to fallout.sqlite")):
    """
    Look up what components a Junk Item will scrap into (example: `f76 scrap 'Giddyup Buttercup'`)
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
    t = Table(title=f'"{item}" scraps for:', expand=True)
    t.add_column("Component"); t.add_column("Qty", justify="right")
    for comp, qty in rows:
        t.add_row(comp, str(qty))
    console.print(t)

@app.command("sources")
def sources(component: str, db: str | None = typer.Option(None, help="Path to fallout.sqlite")):
    """
    Look up what Junk Items are a source of a given component (example: `f76 sources 'Lead'`)
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
    t = Table(title=f'Items that yield "{component}"', expand=True)
    t.add_column("Item"); t.add_column("Qty", justify="right")
    for item_name, qty in rows:
        t.add_row(item_name, str(qty))
    console.print(t)

@app.command("whereis")
def region_for(location: str,db: str | None = typer.Option(None, help="Path to fallout.sqlite")):
    """
    Look up what region a location exists in. (example: `f76 whereis 'Wade Airport'`)
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
    t = Table(title=f'{location.title()} is located in:', expand=True)
    t.add_column("Region");
    # fetchall returns a list of tuples - even for one col
    for (region,) in rows:
        t.add_row(region)
    console.print(t)

@app.command("places")
def locations_in(region: str,db: str | None = typer.Option(None, help="Path to fallout.sqlite")):
    """
    Look up what locations are in a region of the map (example: `f76 places 'Cranberry Bog'`)
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
    t = Table(title=f'{region.title()} is home to the following locations:', expand=True)
    t.add_column("Locations");
    for (location_name,) in rows:
        t.add_row(location_name)
    console.print(t)

@app.command("regions")
def locations_in(db: str | None = typer.Option(None, help="Path to fallout.sqlite")):
    """
    List all the regions of the map (example: `f76 regions`)
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
    t = Table(title=f'You will find the following Regions in Appalachia:', expand=True)
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
    console.print(f"Preparing to initialize Scrap & Junk Items")
    scrape_junk_items(db_path)
    console.print(f"Preparing to initialize Regions & Locations")
    scrape_regions_and_locations(db_path)
    console.print("[green]Done.[/green]")