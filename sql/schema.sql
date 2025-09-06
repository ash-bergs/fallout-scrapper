PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS item (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  url  TEXT
);

CREATE TABLE IF NOT EXISTS component (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS item_scraps (
  item_id INTEGER NOT NULL REFERENCES item(id) ON DELETE CASCADE,
  component_id INTEGER NOT NULL REFERENCES component(id) ON DELETE RESTRICT,
  quantity INTEGER NOT NULL,
  PRIMARY KEY (item_id, component_id)
);

CREATE TABLE IF NOT EXISTS region (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  url TEXT
);

CREATE TABLE IF NOT EXISTS location (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  region_id INTEGER NOT NULL REFERENCES region(id) ON DELETE RESTRICT,
  url TEXT,
  UNIQUE(name, region_id)
);

-- A many-to-many table - an item can appear in many locations
-- and a location can contain many items - which is why we included 2 Foreign Keys
CREATE TABLE IF NOT EXISTS item_locations (
  item_id INTEGER NOT NULL REFERENCES item(id) ON DELETE CASCADE,
  location_id INTEGER NOT NULL REFERENCES location(id) ON DELETE RESTRICT,
  description TEXT,
  quantity INTEGER,
  PRIMARY KEY (item_id, location_id, description)
);

-- Helpful indexes for common lookups
-- These are performance helpers - they don't change the data, but speed up certain queries
-- Without an index SQL will scan the whole table, row by row - e.g. "full table scan"
-- In a table with 10K rows, a query like `SELECT * FROM item_locations WHERE item_id = 42`
-- will have to check all 10,000 rows one by one, asking: "Does this row's item_id equal 42?"
-- An index is like the index at the back of a book: instead of flipping through every page,
-- the database jumps straight to the rows matching the search value. This makes lookups
-- by item_id or location_id much faster, especially as the table grows. 

-- SQLite builds a separate lookup structure (B-tree) for item_id(or other given id)
-- then it sorts the values of item_id, storing pointers to the rows in the main table
-- Now when we query for item_id = 42 SQL can perform a binary search instead of a full table scan (linear search)
-- Binary search is logarithmic time - 0(log n) 
-- much faster than a linear time (full table scan) - 0(n)

-- Speed up queries like "What locations does this item spawn in?"
CREATE INDEX IF NOT EXISTS idx_item_locations_item     ON item_locations(item_id);
-- Speed up queries like "What items spawn in this location?"
CREATE INDEX IF NOT EXISTS idx_item_locations_location ON item_locations(location_id);
-- Speeds up queries for details about items by name
CREATE INDEX IF NOT EXISTS idx_item_name ON item(name);
-- Speeds up queries for details about items by component name
CREATE INDEX IF NOT EXISTS idx_component_name ON component(name);
