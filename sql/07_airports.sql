-- Q4 Airport economics vs city trips, split by direction.
SELECT coalesce(airport, 'City') AS trip_type,
       CASE WHEN airport IS NULL THEN 'n/a'
            WHEN (airport = 'JFK' AND PULocationID = 132) OR (airport = 'LGA' AND PULocationID = 138)
              OR (airport = 'EWR' AND PULocationID = 1) THEN 'From airport'
            ELSE 'To airport' END                                      AS direction,
       count(*)                                                        AS trips,
       round(avg(trip_distance), 1)                                    AS avg_distance_mi,
       round(avg(duration_min), 1)                                     AS avg_duration_min,
       round(avg(fare_amount + extra + tip_amount), 2)                 AS avg_earnings_per_trip,
       round(sum(fare_amount + extra + tip_amount) / sum(duration_min / 60), 2) AS earnings_per_meter_hour,
       round(avg(total_amount), 2)                                     AS avg_rider_total,
       round(avg(tip_pct), 1)                                          AS avg_card_tip_pct
FROM trips
GROUP BY ALL
ORDER BY trips DESC;
