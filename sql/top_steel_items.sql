-- Top 20 items that scrap into the most steel
SELECT i.name AS item, s.quantity AS steel_quantity
FROM item_scraps s 
JOIN item i ON i.id = s.item_id
JOIN component c ON c.id = s.component_id
WHERE c.name = "Steel"
ORDER BY steel_quantity DESC, i.name
LIMIT 20;

