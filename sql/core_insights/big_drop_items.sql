 -- **Items that yield “big drops”**: items where the _sum of 
 -- all component quantities_ is highest.

 /*
 first - the items in the game 
a focus on the items table here 
 
 */

-- SELECT i.id, i.name AS item
-- FROM item AS i;

/* example result:
3|.308 casing
1|.44 casing
2|.50 casing
10|10lb weight
13|10mm casing
6|160lb barbell
*/

-- Now I want to add on to this, give me the name of each component it scraps into
-- SELECT i.id, i.name AS item,
-- s.component_id, s.quantity
-- FROM item AS i 
-- JOIN item_scraps AS s ON s.item_id = i.id;

/* example return
1|.44 casing|1|1
1|.44 casing|2|1
2|.50 casing|1|1
2|.50 casing|2|1
3|.308 casing|1|1
3|.308 casing|2|1
4|40lb barbell|2|5
5|80lb barbell|2|7
*/

-- Now I want to get the component name, instead of the component id

-- SELECT i.id, i.name AS item,
-- c.name, s.quantity
-- FROM item AS i 
-- JOIN item_scraps AS s ON s.item_id = i.id
-- JOIN component AS c ON c.id = s.component_id;

/*
1|.44 casing|Steel|1
1|.44 casing|Lead|1
2|.50 casing|Steel|1
2|.50 casing|Lead|1
3|.308 casing|Steel|1
3|.308 casing|Lead|1
4|40lb barbell|Lead|5
5|80lb barbell|Lead|7
*/

-- Window Expression practice
-- To more easily view the per-component rows 
-- Docs: https://sqlite.org/windowfunctions.html
-- SELECT i.name AS item,
-- c.name, s.quantity, SUM(s.quantity) OVER (PARTITION BY i.id) AS item_total
-- FROM item AS i 
-- JOIN item_scraps AS s ON s.item_id = i.id
-- JOIN component AS c ON c.id = s.component_id;

/*
.44 casing|Steel|1|2
.44 casing|Lead|1|2
.50 casing|Steel|1|2
.50 casing|Lead|1|2
.308 casing|Steel|1|2
.308 casing|Lead|1|2
40lb barbell|Lead|5|5
80lb barbell|Lead|7|7
*/

-- Return each item’s ID and name, the total quantity of all scrap it yields,
-- and a breakdown of the components that make up that total.
SELECT 
    i.id, 
    i.name AS item,
    SUM(s.quantity) AS total_drop,   -- total scrap quantity from this item
    -- Concatenate component names and amounts into a single string
    -- ex: "Steelx2, Leadx1"
    -- Docs: https://sqlite.org/lang_aggfunc.html#groupconcat
    GROUP_CONCAT(c.name || 'x' || s.quantity, ', ') AS breakdown
FROM item AS i 
JOIN item_scraps AS s ON s.item_id = i.id 
JOIN component AS c ON c.id = s.component_id
GROUP BY i.id, i.name
ORDER BY total_drop DESC;

/*
213|Large Vault-Tec supply package|210|Black titaniumx15, Leadx30, Leatherx30, Nuclear materialx15, Oilx30, Screwx30, Steelx30, Woodx30
227|Medium Vault-Tec supply package|160|Leadx20, Leatherx20, Oilx20, Plasticx20, Rubberx20, Springx20, Steelx20, Woodx20
343|Small Vault-Tec supply package|140|Adhesivex20, Leadx20, Leatherx20, Oilx20, Springx20, Steelx20, Woodx20
179|Giddyup Buttercup|12|Gearx2, Steelx5, Springx2, Screwx3
6|160lb barbell|10|Leadx10
45|Blue paint|9|Oilx2, Steelx2, Leadx5
*/
