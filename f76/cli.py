import os, pathlib, sqlite3, typer
from rich.console import Console
from rich.table import Table
from .scripts.scrape.junk_items_table import main as scrape_junk_items

# TODO: break this file up as commands grow 
# CLI directory? With Utils?

app = typer.Typer(help="Fallout 76 scrap lookup")
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

def get_conn(db_path: pathlib.Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

@app.command("components-of")
def components_of(item: str, db: str | None = typer.Option(None, help="Path to fallout.sqlite")):
    """
    Look up what components a Junk Item will scrap into (e.g., "Giddyup Buttercup")
    """
    db_path = resolve_db_path(db)
    q = """
    SELECT c.name, s.quantity
    FROM item i
    JOIN item_scraps s ON s.item_id = i.id
    JOIN component   c ON c.id = s.component_id
    WHERE i.name = ? COLLATE NOCASE
    ORDER BY c.name;
    """
    with get_conn(db_path) as cx:
        rows = cx.execute(q, (item,)).fetchall()
    if not rows:
        console.print(f"[bold]No scraps found for:[/bold] {item} (DB: {db_path})")
        raise typer.Exit(1)
    t = Table(title=f'"{item}" scraps for:')
    t.add_column("Component"); t.add_column("Qty", justify="right")
    for comp, qty in rows:
        t.add_row(comp, str(qty))
    console.print(t)

@app.command("items-for")
def items_for(component: str, db: str | None = typer.Option(None, help="Path to fallout.sqlite")):
    """
    Look up what Junk Items yield the most of a given component (e.g., "Lead")
    """
    db_path = resolve_db_path(db)
    q = """
    SELECT i.name, s.quantity
    FROM component c
    JOIN item_scraps s ON s.component_id = c.id
    JOIN item        i ON i.id = s.item_id
    WHERE c.name = ? COLLATE NOCASE
    ORDER BY s.quantity DESC, i.name;
    """
    with get_conn(db_path) as cx:
        rows = cx.execute(q, (component,)).fetchall()
    if not rows:
        console.print(f"[bold]No items found for component:[/bold] {component} (DB: {db_path})")
        raise typer.Exit(1)
    t = Table(title=f'Items that yield "{component}"')
    t.add_column("Item"); t.add_column("Qty", justify="right")
    for item_name, qty in rows:
        t.add_row(item_name, str(qty))
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
    scrape_junk_items()
    console.print("[green]Done.[/green]")
