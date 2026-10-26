-- Q3 Tipping: card tip % across several dimensions, stacked into one long table.
-- tip_pct is only populated for Vendor 2 credit-card trips (cash tips are not recorded, and
-- Vendor 1 under-records card tips outside Manhattan; see src/features.py).
WITH card AS (
    SELECT *,
           CASE WHEN trip_distance < 1  THEN '1: <1 mi'
                WHEN trip_distance < 3  THEN '2: 1-3 mi'
                WHEN trip_distance < 7  THEN '3: 3-7 mi'
                WHEN trip_distance < 15 THEN '4: 7-15 mi'
                ELSE '5: 15+ mi' END AS distance_band
    FROM trips
    WHERE tip_pct IS NOT NULL
)
SELECT 'pickup_borough' AS dimension, pu_borough AS value, count(*) AS card_trips,
       round(avg(tip_pct), 2) AS avg_tip_pct, round(median(tip_pct), 2) AS median_tip_pct,
       round(100.0 * avg((tip_amount = 0)::INT), 2) AS pct_no_tip
FROM card GROUP BY ALL
UNION ALL
SELECT 'time_of_day', time_of_day, count(*), round(avg(tip_pct), 2), round(median(tip_pct), 2),
       round(100.0 * avg((tip_amount = 0)::INT), 2)
FROM card GROUP BY ALL
UNION ALL
SELECT 'distance_band', distance_band, count(*), round(avg(tip_pct), 2), round(median(tip_pct), 2),
       round(100.0 * avg((tip_amount = 0)::INT), 2)
FROM card GROUP BY ALL
UNION ALL
SELECT 'trip_type', coalesce(airport, 'City'), count(*), round(avg(tip_pct), 2), round(median(tip_pct), 2),
       round(100.0 * avg((tip_amount = 0)::INT), 2)
FROM card GROUP BY ALL
ORDER BY dimension, value;
