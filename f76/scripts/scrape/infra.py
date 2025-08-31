import os
import pathlib
import sqlite3
from contextlib import contextmanager
from typing import Iterator, Optional

import requests
from bs4 import BeautifulSoup

DEFAULT_USER_AGENT = "ash-sql-learning/0.1 (personal, low-traffic)"
DEFAULT_HEADERS = {"User-Agent": DEFAULT_USER_AGENT}
DEFAULT_TIMEOUT = 30

# --- DB Path Resolution --- 
# This path will change if we move this module
# Establish a good place and update 
def default_repo_db() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[3] / "data" / "fallout.sqlite"

# New - Does some of the work we did early on in the scripts
# Before connecting to sqlite
def resolve_db_path(db_path: str | pathlib.Path | None) -> pathlib.Path:
    if db_path:
        return pathlib.Path(db_path)
    env = os.environ.get("F76_DB_TARGET")
    return pathlib.Path(env) if env else default_repo_db()

# --- DB Connection + Schema bootstrapping ---
# What is this? 👇
@contextmanager
def db_conn(db_path: str | pathlib.Path | None = None, *, ensure_schema_fn=None) -> Iterator[sqlite3.Connection]:
    """
    Opens SQLite connection at the resolved path & ensures parent dir exists.
    Calls ensure_schema (opt) before yielding
    """
    path = resolve_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path)

    try:
        if ensure_schema_fn is not None:
            ensure_schema_fn(conn)
        yield conn
    finally:
        conn.close()

# --- HTTP Helpers ---
def make_session(headers: Optional[dict] = None) -> requests.Session:
    s = requests.Session()
    s.headers.update(DEFAULT_HEADERS if headers is None else headers)
    return s

def fetch_soup(url: str, *, session: Optional[requests.Session] = None, timeout: int = DEFAULT_TIMEOUT, parser: str = "html.parser") -> BeautifulSoup:
    # allow passed active session, or create a new one
    s = session or make_session()
    resp = s.get(url, timeout=timeout)
    resp.raise_for_status()
    # Return HTML for parsing 
    return BeautifulSoup(resp.text, parser)
