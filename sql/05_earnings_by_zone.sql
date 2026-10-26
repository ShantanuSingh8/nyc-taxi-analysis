-- Q2 Driver earnings by pickup zone (zones with >= 10,000 pickups).
-- Same earnings definition as 04_earnings_by_hour.sql.
SELECT pu_zone,
       pu_borough,
       count(*)                                                        AS trips,
       round(avg(trip_distance), 2)                                    AS avg_distance_mi,
       round(avg(fare_amount + extra + tip_amount), 2)                 AS avg_earnings_per_trip,
       round(sum(fare_amount + extra + tip_amount) / sum(duration_min / 60), 2) AS earnings_per_meter_hour
FROM trips
WHERE NOT flag_unknown_zone
GROUP BY ALL
HAVING count(*) >= 10000
ORDER BY earnings_per_meter_hour DESC;
