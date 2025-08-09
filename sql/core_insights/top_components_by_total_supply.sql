/*
❔What do we mean by "top components by total supply"?
- Sum all the quantities per component and rank them
- Basically "Across *all the item* in the game, if we had one of *everything*
  which components (crafting materials) would end up being the most plentiful?"
  - Which materials are the most available via the junk in the game

❔ Why would we want to know this?
- This will tell us which crafting materials are the most abundant
  in scrappable items
- Helps us identify crafting materials that are "common" vs "rare" for game economy

- A component is a crafting material, like "steel", "lead", etc.
- We want to know how many units of that component we'd get from a given item
  - Ex. A typewriter scraps into 2 screws and 4 steel
- Then we can sum all quantities for each component across all items
  - A theoretical total supply if we had one of each item
- Finally, rank component (crafting materials) by the largest supply to the smallest
*/

-- So we'd need the component name (from components table - we'd start there?)

-- STEP 1 - The components table
-- SELECT: "When we're done joining things together, these are the fields we care about in the result"
-- The SELECT list about the OUTPUT COLUMNS

/* uncomment query below to see at this point */
-- SELECT c.id, c.name AS component
-- -- Tell SQL where c comes from above
-- FROM component AS c;
/* example result:
1|Steel
2|Lead
3|Acid
4|Antiseptic
5|Fiberglass
*/

-- STEP 2 - Joining the item_scraps table
-- "For each scrap record (in item_scraps), show which component (crafting material) it is"

/* uncomment query below to see at this point */
-- SELECT c.id AS component_id, c.name AS component_name, 
--   s.item_id, s.quantity
-- FROM component AS c
-- JOIN item_scraps AS s
--   ON c.id = s.component_id;
/* example result:
component_id, c.name, item id (junk item in game), quantity of component
1|Steel|1|1
2|Lead|1|1
1|Steel|2|1
2|Lead|2|1
1|Steel|3|1

This is the raw joined data at this point
*/

-- STEP 3: Group by component to get totals
-- "For every unique record of the component table find the records it maps to 
-- in the item_scraps table and add up the value found for the quantity there"

/* uncomment query below to see at this point */
-- SELECT c.name AS component, SUM(s.quantity) AS total_quantity
-- FROM component AS c
-- JOIN item_scraps AS s
-- -- How are they joined? i.e. "You'll know these records are linked because they'll have the same component id"
--   ON c.id = s.component_id
-- GROUP BY c.name;
/* example result:
Acid|27
Adhesive|39
Aluminum|42
Antiseptic|14
Asbestos|18
Ballistic fiber|4
Black titanium|15
*/

-- STEP 4: Rank the components 
-- Use ORDER BY on the total quantity 
SELECT c.name AS component, SUM(s.quantity) AS total_quantity
FROM component AS c
JOIN item_scraps AS s
  ON c.id = s.component_id
GROUP BY c.name
ORDER BY total_quantity DESC;
/* example result:
Steel|226
Lead|166
Leather|132
Wood|115
Oil|114
Plastic|96
Spring|60
*/

/*
We can see how much steel, lead, leather, etc. we'd get if we scrapped one of
every unique item exactly once (a supply-only baseline):
- Baseline → a starting point, the simplest possible version of the measurement.
- Supply-only → we’re looking at potential supply in an idealized situation:
    - We scrap one of every unique item in the game
    - We total up all the components yielded
    - We rank components by those totals

This does NOT tell us:
- Which items actually spawn more often (spawn/frequency bias).
- Player behavior (what people actually pick up/scrap).
- Demand (what components are used most in crafting).
- Market dynamics (trade prices, vendor caps, events).
- Weight or efficiency (qty per unit weight/space/time).

So: more does not automatically mean “less valuable.” High total supply can still
be valuable if demand is even higher. Likewise, a low total might be “rare,” but
not valuable if demand is low.

Next steps (what we’d need or approximate):
1) Frequency weighting: if we had spawn/loot frequency, weight each item’s yield.
2) Demand weighting: weight components by how many recipes use them and how much.
3) Efficiency: compute qty-per-weight or qty-per-time (farm routes).
4) Market proxy: if price data exists, compare price to supply/demand signals.

With only this dataset, we can still add helpful descriptors:
- How many *different* items yield each component (breadth of sources).
- Average and max per-item yield (depth/quality of sources).
- Share of total (component’s % of the total scrap pool).
- Pareto view (top components that make up 80% of supply).

These don’t give “value,” but they describe supply structure more richly.
*/
