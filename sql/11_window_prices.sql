-- Average price of each product in each geography over a window of months.
-- Parameters: :start and :end ('YYYY-MM'). Used for the base, latest and pre-pandemic windows.

SELECT g.geo_name, p.product, p.category,
       AVG(f.price) AS avg_price,
       COUNT(*)     AS n_months
FROM fact_price f
JOIN dim_geo g     USING (geo_key)
JOIN dim_product p USING (product_key)
WHERE f.date_key BETWEEN :start AND :end
GROUP BY g.geo_name, p.product, p.category;
