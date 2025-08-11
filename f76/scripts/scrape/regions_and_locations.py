import os, sqlite3, pathlib, requests
from bs4 import BeautifulSoup
from ..parsing_utils import clean_text
from ..db_utils import ensure_schema

BASE = "https://fallout.fandom.com"
URL = "https://fallout.fandom.com/wiki/Fallout_76_locations"
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

        # Anchor will be REGIONS heading 
        anchor = soup.select_one("#Regions")  
        if not anchor:
            raise SystemExit("Couldn't find #Regions anchor")
        
        h2 = anchor.find_parent("h2")
        #print("H2: ", h2)
        if not h2:
            raise RuntimeError("Could not find parent <h2> for #Regions")
        
        table = h2.find_next("table")
        # print("Table: ", table)      
        if not table:
            raise RuntimeError("Couldn't find the Regions table")
        
        # parse regions from the Regions table
        regions = []
        for td in table.select("td"):
          print("TD: ", td)
          # pick the text link (skip the image link)
          links = [a for a in td.find_all("a", href=True) if not a.find("img")]
          if not links:
            continue
          print(regions)
          
          a = links[-1]  
          name = clean_text(a.get_text(" ", strip=True))
          if not name:
            continue
          
          url = a["href"]
          if url.startswith("/"):
            url = BASE + url
          
          regions.append((name, url))

        # upsert into region(name, url)
        with conn:
          cur = conn.cursor()
        for name, url in regions:
        # Insert if missing
          cur.execute("INSERT OR IGNORE INTO region(name, url) VALUES (?, ?)", (name, url))
        # If it existed without a url, fill it in (keeps existing non-null urls)
        cur.execute("UPDATE region SET url = COALESCE(url, ?) WHERE name = ?", (url, name))

        print(f"Loaded {len(regions)} regions")

if __name__ == "__main__":
    main()
