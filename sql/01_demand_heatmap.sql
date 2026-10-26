-- Q1 Demand: average trips per hour, by weekday x hour of day.
-- Divides by the number of calendar days of each weekday so months with 5 Mondays don't skew it.
WITH days AS (
    SELECT pickup_dow, count(DISTINCT pickup_date) AS n_days
    FROM trips GROUP BY 1
)
SELECT t.pickup_dow,
       any_value(t.pickup_dayname)               AS pickup_dayname,
       t.pickup_hour,
       count(*)                                   AS trips,
       round(count(*) / any_value(d.n_days), 0)   AS avg_trips_per_hour
FROM trips t
JOIN days d USING (pickup_dow)
GROUP BY t.pickup_dow, t.pickup_hour
ORDER BY t.pickup_dow, t.pickup_hour;
