-- Data-quality checks. Each row returns a check name and the number of offending records (expect 0
-- unless noted). Run after loading; build_db.py fails the build if a hard check is non-zero.

SELECT 'orphan_dates' AS check_name, COUNT(*) AS n
FROM fact_price f LEFT JOIN dim_date d USING (date_key) WHERE d.date_key IS NULL
UNION ALL
SELECT 'orphan_products', COUNT(*)
FROM fact_price f LEFT JOIN dim_product p USING (product_key) WHERE p.product_key IS NULL
UNION ALL
SELECT 'non_positive_prices', COUNT(*) FROM fact_price WHERE price <= 0
UNION ALL
-- Month-over-month jumps above 50% are flagged for review, not removed (soft check).
SELECT 'mom_jumps_over_50pct_soft', COUNT(*) FROM (
    SELECT price / LAG(price) OVER (PARTITION BY geo_key, product_key ORDER BY date_key) - 1 AS mom
    FROM fact_price
) WHERE ABS(mom) > 0.5
UNION ALL
-- Province-product series with fewer months than the table covers (soft check).
SELECT 'incomplete_series_soft', COUNT(*) FROM (
    SELECT geo_key, product_key, COUNT(*) AS n
    FROM fact_price GROUP BY geo_key, product_key
    HAVING n < (SELECT COUNT(*) FROM dim_date)
)
UNION ALL
-- Soft: 4 L milk (swap basket) is not published for Newfoundland and Labrador.
SELECT 'basket_items_missing_in_a_province_soft', COUNT(*) FROM (
    SELECT b.scenario, b.product_key, g.geo_key
    FROM basket b CROSS JOIN dim_geo g
    WHERE NOT EXISTS (
        SELECT 1 FROM fact_price f
        WHERE f.product_key = b.product_key AND f.geo_key = g.geo_key
    )
);
