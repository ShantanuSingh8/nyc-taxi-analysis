-- Q1 Demand: top 20 pickup zones, with share of all trips.
SELECT pu_zone,
       pu_borough,
       count(*)                                           AS trips,
       round(100.0 * count(*) / sum(count(*)) OVER (), 2) AS pct_of_trips
FROM trips
WHERE NOT flag_unknown_zone
GROUP BY ALL
ORDER BY trips DESC
LIMIT 20;
