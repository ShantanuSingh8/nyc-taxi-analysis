-- Q5 Booking channel (request_source exists from Jun 2026 only).
-- HV0003 = Uber, HV0005 = Lyft (TLC high-volume license numbers).
SELECT coalesce(request_source, '(null)')                              AS request_source,
       CASE WHEN is_flex_fare THEN 'Flex Fare' ELSE 'Metered' END     AS pricing,
       count(*)                                                        AS trips,
       round(100.0 * count(*) / sum(count(*)) OVER (), 2)              AS pct_of_june_trips,
       round(avg(fare_amount), 2)                                      AS avg_fare,
       round(avg(trip_distance), 2)                                    AS avg_distance_mi
FROM trips
WHERE file_month = '2026-06'
GROUP BY ALL
ORDER BY trips DESC;
