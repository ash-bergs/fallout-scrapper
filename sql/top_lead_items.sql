-- Top 20 Items that scrap into the most lead

-- "I want the name of the junk item (SELECT i.name) and how much of something it gives
-- and we're going to call that 'lead_quantity'"
SELECT i.name AS item, s.quantity as lead_quantity
-- Start from scraps - Just IDs at this point, no names:
-- item_id | component_id | quantity 
-- 1       | 11           | 2 
FROM item_scraps s
-- Match the item id from scraps to the id in item so we can get the item's name:
-- item_id | component_id | quantity | item.name
-- 1       | 11           | 2        | .44 casing
-- 1       | 13           | 1        | .44 casing
JOIN item i ON i.id = s.item_id
-- Match the component id from scraps to the id in components so we can get the scrap name:
-- item.name  | component.name | quantity
-- .44 casing | Lead           | 2 
-- .44 casing | Steel          | 2 
JOIN component c ON c.id = s.component_id
-- Filter to only rows where the scrap is Lead
WHERE c.name = "Lead"
ORDER BY lead_quantity DESC, i.name;
-- LIMIT 20;

-- Refresher:
-- Think of the tables as bins
-- In one bin (items) we have all the junk items in the game, each has a unique ID
-- In another bin (component) we have all the *types* of scrap you can get - with a unique ID and name
-- The last bin (item_scraps) is the "recipe book" that says:
-- "When you take item X apart - you can get Y pieces of Z component"