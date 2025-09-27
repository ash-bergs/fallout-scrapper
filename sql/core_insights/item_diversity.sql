/*

❔ What do we mean by "item diversity by region"?
- The number of unique junk items that can be found in a region of the map.
- "Diversity" means variety, not quantity of spawns.

❔ Why would we want to know this?
- Regions with a wider collection of items offer a wider range of scrap resources.
- This can help players plan farming routes

‼📝 Important note - This query is only as good as the database contents
This query is only as good as the database contents.  
The `item_locations` table is populated **on-demand** when you run `f76 where <item>`.  
- If you’ve never asked for an item, its locations won’t exist in the DB.  
- So results will always be incomplete unless you’ve scraped broadly.
*/

-- To understand how many items are in a region we first need to look at locations
-- Items are linked to regions only indirectly:
-- item → item_locations → location → region
-- To start we'll look at locations per region:
-- SELECT r.name as region,
-- -- TODO: a note on COUNT and DISTINCT 
-- COUNT(DISTINCT l.id) as locations
-- FROM region r
-- JOIN location l on l.region_id = r.id
-- GROUP BY r.id;

/* example result:

Ash Heap|63
Cranberry Bog|48 
The Forest|132 → I anticipated this region to have the most locations
The Mire|74
Savage Divide|137 → Makes sense for the middle on the map to have the most
Skyline Valley|41 → We know this area is still growing
Toxic Valley|37 → The lowest in the game

This gives us a baseline for beginning to understand a region's item diversity.
We can extend that baseline to understand distinct known items per region
*/

-- We know we can get the locations for each region through region id
-- Now we need to apply location id to get items from item_locations
--
-- This gives us "diversity of items" in each region (unique items).
-- SELECT r.name as region,
-- -- COUNT & DISTINCT
-- --   - Each row in item_locations represents "this item spawns at this location"
-- --   - A single item can appear in multiple locations within a region.
-- --   - DISTINCT ensures we only count that item once per region.
-- COUNT(DISTINCT il.item_id) as unique_items
-- FROM region r
-- JOIN location l ON l.region_id = r.id
-- JOIN item_locations il ON il.location_id = l.id
-- GROUP BY r.id
-- ORDER BY unique_items DESC;

/* example result:

The Forest|6
Savage Divide|5
The Mire|5
Ash Heap|5
Cranberry Bog|4
Skyline Valley|3
Toxic Valley|2
*/

-- Drill-down → Item diversity per location
-- Which specific locations host the greatest variety of junk items?
SELECT l.name as location,
COUNT(DISTINCT il.item_id) as unique_items
FROM location l
JOIN item_locations il ON il.location_id = l.id
GROUP BY l.id
ORDER BY unique_items DESC;

/* example result:

The Burrows|5
Garrahan Estate|3
Eta Psi house|3
Hornwright Estate|2
Red Rocket filling station|2
Rollins Labor Camp|2
Big Al's Tattoo Parlor|2
Blue Ridge Bunkhouse|2
Flatwoods lookout|2
Kanawha Nuka-Cola plant|2
*/