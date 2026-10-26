"""Phase 4: add analysis features and zone names to the cleaned trips.

Usage:  python -m src.features
"""
import time

import duckdb
import holidays
import pandas as pd

from src import config as c

DURATION_MIN = "date_diff('second', tpep_pickup_datetime, tpep_dropoff_datetime) / 60.0"


def holiday_table(years) -> pd.DataFrame:
    ny = holidays.country_holidays("US", subdiv="NY", years=years)
    return pd.DataFrame({"holiday_date": pd.to_datetime(list(ny.keys())).date,
                         "holiday_name": list(ny.values())})


def main() -> None:
    t0 = time.perf_counter()
    c.PROCESSED.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()

    years = [y for (y,) in con.execute(f"SELECT DISTINCT year(tpep_pickup_datetime) FROM '{c.CLEAN_TRIPS}'").fetchall()]
    con.register("holidays_df", holiday_table(years))
    con.register("payment_df", pd.DataFrame(list(c.PAYMENT_TYPES.items()), columns=["payment_type", "payment_label"]))
    con.register("rate_df", pd.DataFrame(list(c.RATE_CODES.items()), columns=["RatecodeID", "rate_label"]))
    con.execute(f"CREATE TEMP TABLE zones AS SELECT * FROM read_csv('{c.ZONE_LOOKUP}')")

    con.execute(f"""
        COPY (
            WITH base AS (
                SELECT t.*,
                       {DURATION_MIN}                              AS duration_min,
                       CAST(tpep_pickup_datetime AS DATE)           AS pickup_date,
                       hour(tpep_pickup_datetime)                   AS pickup_hour,
                       isodow(tpep_pickup_datetime)                 AS pickup_dow,  -- 1=Mon .. 7=Sun
                       dayname(tpep_pickup_datetime)                AS pickup_dayname
                FROM '{c.CLEAN_TRIPS}' t
            )
            SELECT
                b.*,
                round(trip_distance / (duration_min / 60.0), 2)    AS speed_mph,
                pickup_dow >= 6                                     AS is_weekend,
                h.holiday_name IS NOT NULL                          AS is_holiday,
                h.holiday_name,
                CASE WHEN pickup_hour BETWEEN 6 AND 9   THEN 'AM peak (6-10)'
                     WHEN pickup_hour BETWEEN 10 AND 15 THEN 'Midday (10-16)'
                     WHEN pickup_hour BETWEEN 16 AND 19 THEN 'PM peak (16-20)'
                     WHEN pickup_hour BETWEEN 20 AND 23 THEN 'Evening (20-24)'
                     ELSE 'Overnight (0-6)' END                    AS time_of_day,
                payment_type = 0                                    AS is_flex_fare,
                p.payment_label,
                r.rate_label,
                -- Tips are only recorded for card payments, and Vendor 1 records $0 on ~98% of
                -- outer-borough card trips (a recording gap, not rider behavior), so tip_pct is
                -- limited to Vendor 2 card trips; NULL elsewhere so averages aren't diluted.
                CASE WHEN payment_type = 1 AND VendorID = 2 AND total_amount - tip_amount > 0
                     THEN round(100 * tip_amount / (total_amount - tip_amount), 2) END AS tip_pct,
                round(fare_amount / trip_distance, 2)               AS fare_per_mile,
                round(fare_amount / duration_min, 2)                AS fare_per_min,
                round(total_amount - tip_amount, 2)                 AS total_ex_tip,
                CASE WHEN {c.JFK} IN (PULocationID, DOLocationID) OR RatecodeID = 2 THEN 'JFK'
                     WHEN {c.LGA} IN (PULocationID, DOLocationID) THEN 'LGA'
                     WHEN {c.NEWARK} IN (PULocationID, DOLocationID) OR RatecodeID = 3 THEN 'EWR'
                     END                                            AS airport,
                airport IS NOT NULL                                 AS is_airport_trip,
                pu.Borough AS pu_borough, pu.Zone AS pu_zone, pu.service_zone AS pu_service_zone,
                dz.Borough AS do_borough, dz.Zone AS do_zone, dz.service_zone AS do_service_zone
            FROM base b
            LEFT JOIN holidays_df h ON h.holiday_date = b.pickup_date
            LEFT JOIN payment_df p USING (payment_type)
            LEFT JOIN rate_df r USING (RatecodeID)
            LEFT JOIN zones pu ON pu.LocationID = b.PULocationID
            LEFT JOIN zones dz ON dz.LocationID = b.DOLocationID
        ) TO '{c.FEATURE_TRIPS}' (FORMAT parquet, COMPRESSION zstd)
    """)

    print(con.sql(f"""
        SELECT count(*) AS trips,
               round(avg(duration_min), 1)  AS avg_duration_min,
               round(avg(speed_mph), 1)     AS avg_speed_mph,
               round(avg(tip_pct), 1)       AS avg_card_tip_pct,
               round(avg(is_airport_trip::INT) * 100, 1) AS airport_pct,
               round(avg(is_flex_fare::INT) * 100, 1)    AS flex_pct,
               count(*) FILTER (WHERE pu_zone IS NULL)   AS unmatched_zones
        FROM '{c.FEATURE_TRIPS}'
    """))
    print(f"wrote {c.FEATURE_TRIPS} ({time.perf_counter() - t0:.0f}s)")


if __name__ == "__main__":
    main()
