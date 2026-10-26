"""Phase 7: export a small star schema for the Power BI dashboard.

fact_trips  one row per pickup date x hour x pickup zone x pricing x payment x trip type
            (~1.5M rows) holding additive sums only, so every KPI is a DAX ratio of sums.
dim_date, dim_hour, dim_zone (with lat/lon centroids for map visuals).

Usage:  python -m src.export_powerbi
"""
import time

import duckdb
import pandas as pd
import shapefile
from pyproj import Transformer

from src import config as c


def zone_centroids() -> pd.DataFrame:
    """Area-weighted centroid of each zone polygon, converted from NY State Plane (ft) to WGS84."""
    to_wgs84 = Transformer.from_crs("EPSG:2263", "EPSG:4326", always_xy=True)
    rows = []
    with shapefile.Reader(str(c.REFERENCE / "taxi_zones" / "taxi_zones.shp")) as shp:
        for rec, shape in zip(shp.records(), shp.shapes()):
            # Shoelace over every ring; holes wind the opposite way so they subtract.
            bounds = list(shape.parts) + [len(shape.points)]
            area = cx = cy = 0.0
            for start, end in zip(bounds[:-1], bounds[1:]):
                ring = shape.points[start:end]
                for (x0, y0), (x1, y1) in zip(ring, ring[1:]):
                    cross = x0 * y1 - x1 * y0
                    area += cross
                    cx += (x0 + x1) * cross
                    cy += (y0 + y1) * cross
            lon, lat = to_wgs84.transform(cx / (3 * area), cy / (3 * area))
            rows.append({"LocationID": rec["LocationID"], "latitude": round(lat, 6), "longitude": round(lon, 6)})
    # A few zones are split across several shapefile records; average them.
    return pd.DataFrame(rows).groupby("LocationID", as_index=False).mean()


def main() -> None:
    t0 = time.perf_counter()
    c.POWERBI.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"CREATE VIEW trips AS SELECT * FROM '{c.FEATURE_TRIPS}'")
    con.register("centroids", zone_centroids())

    exports = {
        "fact_trips": f"""
            SELECT pickup_date,
                   pickup_hour,
                   PULocationID,
                   CASE WHEN is_flex_fare THEN 'Flex Fare' ELSE 'Metered' END AS pricing,
                   payment_label,
                   coalesce(airport, 'City')                                  AS trip_type,
                   -- same rule as sql/07_airports.sql
                   CASE WHEN airport IS NULL THEN 'n/a'
                        WHEN (airport = 'JFK' AND PULocationID = {c.JFK}) OR (airport = 'LGA' AND PULocationID = {c.LGA})
                          OR (airport = 'EWR' AND PULocationID = {c.NEWARK}) THEN 'From airport'
                        ELSE 'To airport' END                                  AS airport_direction,
                   CASE WHEN airport IS NULL THEN 'City'
                        ELSE airport || ' ' || lower(airport_direction) END    AS trip_segment,
                   count(*)                                     AS trip_count,
                   round(sum(trip_distance), 2)                 AS distance_mi,
                   round(sum(duration_min), 2)                  AS duration_min,
                   round(sum(fare_amount), 2)                   AS fare_amount,
                   round(sum(extra), 2)                         AS extra,
                   round(sum(tip_amount), 2)                    AS tip_amount,
                   round(sum(tolls_amount), 2)                  AS tolls_amount,
                   round(sum(total_amount), 2)                  AS total_amount,
                   round(sum(fare_amount + extra + tip_amount), 2) AS driver_earnings,
                   -- tip % inputs: Vendor 2 card trips only (see src/features.py)
                   count(tip_pct)                               AS tip_eligible_trips,
                   round(coalesce(sum(tip_amount) FILTER (WHERE tip_pct IS NOT NULL), 0), 2)   AS tip_eligible_tips,
                   round(coalesce(sum(total_ex_tip) FILTER (WHERE tip_pct IS NOT NULL), 0), 2) AS tip_eligible_base
            FROM trips
            GROUP BY ALL
            ORDER BY pickup_date, pickup_hour, PULocationID""",
        "dim_date": """
            SELECT DISTINCT pickup_date                    AS date,
                   year(pickup_date)                       AS year,
                   month(pickup_date)                      AS month_num,
                   strftime(pickup_date, '%b %Y')          AS month_label,
                   isodow(pickup_date)                     AS weekday_num,
                   dayname(pickup_date)                    AS weekday_name,
                   left(dayname(pickup_date), 3)           AS weekday_short,
                   CASE WHEN is_weekend THEN 'Weekend' ELSE 'Weekday' END AS day_type,
                   is_holiday,
                   holiday_name
            FROM trips
            ORDER BY 1""",
        "dim_hour": """
            SELECT DISTINCT pickup_hour                    AS hour,
                   lpad(pickup_hour::VARCHAR, 2, '0') || ':00' AS hour_label,
                   time_of_day,
                   CASE time_of_day WHEN 'Overnight (0-6)' THEN 1 WHEN 'AM peak (6-10)' THEN 2
                        WHEN 'Midday (10-16)' THEN 3 WHEN 'PM peak (16-20)' THEN 4 ELSE 5 END AS time_of_day_order
            FROM trips
            ORDER BY 1""",
        "dim_zone": f"""
            SELECT z.LocationID, z.Borough AS borough, z.Zone AS zone, z.service_zone,
                   z.LocationID IN ({c.JFK}, {c.LGA}, {c.NEWARK}) AS is_airport,
                   ct.latitude, ct.longitude
            FROM read_csv('{c.ZONE_LOOKUP}') z
            LEFT JOIN centroids ct USING (LocationID)
            ORDER BY 1""",
    }
    for name, sql in exports.items():
        path = c.POWERBI / f"{name}.csv"
        con.execute(f"COPY ({sql}) TO '{path.as_posix()}' (HEADER, DELIMITER ',')")
        n = con.execute(f"SELECT count(*) FROM '{path.as_posix()}'").fetchone()[0]
        print(f"{name:<11} {n:>9,} rows  {path.stat().st_size / 1e6:6.1f} MB")

    # Reconcile: the aggregate must sum back to the trip-level data.
    trips, earnings = con.execute(f"SELECT sum(trip_count), sum(driver_earnings) FROM '{(c.POWERBI / 'fact_trips.csv').as_posix()}'").fetchone()
    src_trips, src_earnings = con.execute("SELECT count(*), sum(fare_amount + extra + tip_amount) FROM trips").fetchone()
    assert trips == src_trips and abs(earnings - src_earnings) < 1000, "fact_trips does not reconcile"
    print(f"reconciled {trips:,} trips  ({time.perf_counter() - t0:.0f}s)")


if __name__ == "__main__":
    main()
