-- Weekly basket cost by scenario, geography and month.
-- A month counts only if every basket item has a price there (complete = 1).

DROP VIEW IF EXISTS v_basket_cost;
CREATE VIEW v_basket_cost AS
WITH lines AS (
    SELECT b.scenario, f.geo_key, f.date_key, f.product_key,
           f.price * b.qty_per_week AS line_cost
    FROM basket b
    JOIN fact_price f ON f.product_key = b.product_key
),
items AS (
    SELECT scenario, COUNT(*) AS n_items FROM basket GROUP BY scenario
)
SELECT l.scenario, g.geo_name, l.date_key,
       ROUND(SUM(l.line_cost), 4) AS weekly_cost,
       COUNT(*) AS n_priced,
       CASE WHEN COUNT(*) = i.n_items THEN 1 ELSE 0 END AS complete
FROM lines l
JOIN dim_geo g USING (geo_key)
JOIN items i USING (scenario)
GROUP BY l.scenario, g.geo_name, l.date_key;
