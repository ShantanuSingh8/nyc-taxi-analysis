-- Q2 Driver earnings by hour of day, weekday vs weekend.
-- driver_earnings = fare + extra (rush/overnight surcharge) + tip. Taxes, congestion fees,
-- airport fee and tolls are pass-throughs, so they are excluded.
-- Earnings per hour uses metered time only (no time spent cruising empty), so it is an upper bound.
SELECT CASE WHEN is_weekend THEN 'Weekend' ELSE 'Weekday' END AS day_type,
       pickup_hour,
       count(*)                                                        AS trips,
       round(avg(fare_amount + extra + tip_amount), 2)                 AS avg_earnings_per_trip,
       round(sum(fare_amount + extra + tip_amount) / sum(duration_min / 60), 2) AS earnings_per_meter_hour,
       round(avg(speed_mph), 1)                                        AS avg_speed_mph
FROM trips
GROUP BY ALL
ORDER BY day_type, pickup_hour;
