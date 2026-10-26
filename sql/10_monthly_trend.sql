-- Trend: monthly volume, revenue and average fare components (what the rider pays for).
SELECT file_month,
       count(*)                                         AS trips,
       round(count(*) / count(DISTINCT pickup_date), 0) AS avg_trips_per_day,
       round(sum(total_amount) / 1e6, 2)                AS gross_revenue_musd,
       round(avg(fare_amount), 2)                       AS avg_fare,
       round(avg(extra), 2)                             AS avg_extra,
       round(avg(mta_tax), 2)                           AS avg_mta_tax,
       round(avg(tip_amount), 2)                        AS avg_tip,
       round(avg(tolls_amount), 2)                      AS avg_tolls,
       round(avg(improvement_surcharge), 2)             AS avg_improvement_surcharge,
       round(avg(congestion_surcharge), 2)              AS avg_congestion_surcharge,
       round(avg(Airport_fee), 2)                       AS avg_airport_fee,
       round(avg(cbd_congestion_fee), 2)                AS avg_cbd_congestion_fee,
       round(avg(total_amount), 2)                      AS avg_total
FROM trips
GROUP BY 1
ORDER BY 1;
