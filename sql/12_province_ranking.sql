-- Standard-basket cost per province in the base and latest windows, with growth and rank.
-- Ranks compare the 10 provinces only; the Canada row is kept as a reference (rank NULL).
-- Parameters: :b0, :b1 (base window), :l0, :l1 (latest window).

WITH w AS (
    SELECT v.geo_name, g.is_province,
           AVG(CASE WHEN v.date_key BETWEEN :b0 AND :b1 THEN v.weekly_cost END) AS base_cost,
           AVG(CASE WHEN v.date_key BETWEEN :l0 AND :l1 THEN v.weekly_cost END) AS latest_cost
    FROM v_basket_cost v
    JOIN dim_geo g ON g.geo_name = v.geo_name
    WHERE v.scenario = 'standard' AND v.complete = 1
    GROUP BY v.geo_name, g.is_province
),
ranked AS (
    SELECT geo_name, base_cost, latest_cost,
           RANK() OVER (ORDER BY latest_cost DESC)             AS rank_most_expensive,
           RANK() OVER (ORDER BY latest_cost / base_cost DESC) AS rank_fastest_growth
    FROM w WHERE is_province = 1
)
SELECT w.geo_name,
       ROUND(w.base_cost, 2)   AS base_weekly_cost,
       ROUND(w.latest_cost, 2) AS latest_weekly_cost,
       ROUND(100.0 * (w.latest_cost / w.base_cost - 1), 1) AS pct_change,
       r.rank_most_expensive,
       r.rank_fastest_growth
FROM w LEFT JOIN ranked r USING (geo_name)
ORDER BY w.latest_cost DESC;
