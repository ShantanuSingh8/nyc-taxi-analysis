-- Q3 Tipping: distribution of card tip % (rounded to whole percent).
-- Spikes at round numbers would indicate riders picking the payment screen's preset buttons.
SELECT round(tip_pct)::INT                                         AS tip_pct,
       count(*)                                                    AS card_trips,
       round(100.0 * count(*) / sum(count(*)) OVER (), 2)          AS pct_of_card_trips
FROM trips
WHERE tip_pct IS NOT NULL AND tip_pct <= 40
GROUP BY 1
ORDER BY 1;
