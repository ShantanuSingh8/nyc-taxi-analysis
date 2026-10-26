-- Q5 Flex Fare (upfront price) vs metered trips, by month.
SELECT file_month,
       CASE WHEN is_flex_fare THEN 'Flex Fare' ELSE 'Metered' END     AS pricing,
       count(*)                                                        AS trips,
       round(100.0 * count(*) / sum(count(*)) OVER (PARTITION BY file_month), 1) AS pct_of_month,
       round(avg(trip_distance), 2)                                    AS avg_distance_mi,
       round(median(trip_distance), 2)                                 AS median_distance_mi,
       round(avg(fare_amount), 2)                                      AS avg_fare,
       round(median(fare_per_mile), 2)                                 AS median_fare_per_mile,
       round(sum(fare_amount + extra + tip_amount) / sum(duration_min / 60), 2) AS earnings_per_meter_hour
FROM trips
GROUP BY 1, 2
ORDER BY file_month, pricing;
