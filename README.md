## Fallout Scrapper

A personal Fallout 76 scrap reference. Created to support my own in-game role-play and trading: I'm a wasteland junk seller, and I wanted a fast, offline way to answer "What can I scrap for Lead?" without clicking through wiki pages and scanning long tables.

---

### Why I Built This

If you trade in scrap you know:

- It's a constant struggle to know what's worth picking up, scrapping, or selling
- Online wikis are great, but they're slow to search and usually have a lot of data on one page
- I wanted a personal, queryable database to check "items → components" or "components -> items" quickly

This project:

- Scrapes the Fallout 76 [Nukapedia Fallout Wiki](https://fallout.fandom.com/wiki/Fallout_76_junk_items) specifically
- Stores the data found on the Junk Items table in 3 normalize tables:
  - `item` - all the junk items in the game
  - `component` - all scrap components
  - `item_scraps` - the mapping (item → component(s), with quantity)

#### Why store queries in SQL files

This project is also part of my personal SQL learning journey.

I’m keeping **SQL query files** in `sql/` because:

- **Practice** — building a library of joins, groupings, and filters on a real dataset.
- **Documentation** — each query tells a “story” about how I solved a lookup problem.
- **Reusability** — I can run them anytime without rewriting in the CLI.
- **Learning joins** — the schema forces me to join `item` ↔ `item_scraps` ↔ `component` for nearly every question.

---

### Where this is Going

The plan is to evolve this into a **cross-platform CLI tool** that:

- Lets me run lookups from the terminal:

```bash
scrapper items-for Lead
scrapper components-of "Acoustic Guitar"
```

- Works offline once the data is scraped.
- Can refresh the database on demand with a `scrape` command.
- Is installable via `pipx` on Mac, Windows, or Linux.
- Plans to add scrap from the other fallout games, and allow switching between datasets

#### Current Status

- ✅ **Scraper** — fetches and parses the wiki’s junk items table into SQLite.
- ✅ **Schema** — normalized tables for clean joins and queries.
- ✅ **Basic queries** — `.sql` files in `sql/` for common lookups.
- ✅ **CLI tool** — using Typer for commands.
- 🚧 **Intermediate/Advanced queries** - todo - LEFT JOIN? No problem, once we refresh some basics let's get our hands dirty with:
  - Left Joins
  - Self Joins
  - Aggregate functions
  - Common Table Expressions
  - Co-occurence analysis
  - Ranking & window function

---

### CLI Setup & Usage

The Fallout 76 scrap lookup tool now includes a command-line interface powered by [Typer](https://typer.tiangolo.com/).

#### Install locally

1. Clone the repository

```bash
git clone https://github.com/<your-username>/fallout76-scrapper.git
cd fallout76-scrapper
```

2. Create virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
```

3. Install the package in editable mode:

```bash
pip install -e .
```

#### First-time setup

Run the `init` function to begin, this will populate your local database:

```bash
f76 init
```

By default, the database will be stored at:

- `data/fallout.sqlite` (if running from repo)
- `~/.local/share/f76/fallout.sqlite` (if installed globally)

#### Commands

Input for each command is case insensitive.

1. Show components from an item

```bash
f76 components-of "Acoustic Guitar"
```

Example output:
| Component | Qty |
|-----------|-----|
| Wood | 4 |
| Steel | 2 |

2. Show items for a component

```bash
f76 items-for "cloth"
```

Lists items sorted by the amount of the component they yield.

Example output:
| Item | Qty |
|-----------|-----|
| Cigar Box | 2 |
| Bumblebear| 1 |

---

### ⚠️ Disclaimer

This project uses publicly available data from the Nukapedia Fallout Wiki under the Creative Commons license.
It is not affiliated with or endorsed by Bethesda Softworks or the Fallout franchise.
