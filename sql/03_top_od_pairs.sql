-- Q1 Demand: top 20 origin-destination zone pairs.
SELECT pu_zone,
       do_zone,
       count(*)                          AS trips,
       round(avg(duration_min), 1)       AS avg_duration_min,
       round(avg(fare_amount), 2)        AS avg_fare
FROM trips
WHERE NOT flag_unknown_zone
GROUP BY ALL
ORDER BY trips DESC
LIMIT 20;
