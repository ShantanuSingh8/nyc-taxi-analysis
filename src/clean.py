"""Phase 3: apply data-quality rules to raw Yellow taxi trips and log what was dropped.

Rules are evaluated in order; each dropped row is attributed to the FIRST rule it
fails, so the cleaning log adds up exactly to (raw rows - clean rows).

Some issues are flagged rather than dropped because the rows are still valid trips
(e.g. Flex Fare trips legitimately have no passenger count).

Usage:  python -m src.clean
"""
import time

import duckdb
import pandas as pd

from src import config as c

DURATION_SEC = "date_diff('second', tpep_pickup_datetime, tpep_dropoff_datetime)"

# (rule_name, description, SQL predicate that identifies a BAD row)
DROP_RULES = [
    ("pickup_outside_file_month",
     "Pickup timestamp not in the month the file covers",
     "strftime(tpep_pickup_datetime, '%Y-%m') <> file_month"),
    ("dropoff_not_after_pickup",
     "Dropoff time is at or before pickup time",
     "tpep_dropoff_datetime <= tpep_pickup_datetime"),
    ("duration_over_24h",
     "Trip lasted more than 24 hours",
     f"{DURATION_SEC} > {c.MAX_DURATION_MIN * 60}"),
    ("duration_under_1min",
     "Trip lasted under 1 minute (meter tests / cancellations)",
     f"{DURATION_SEC} < {c.MIN_DURATION_SEC}"),
    ("non_positive_distance",
     "Trip distance is zero, negative or missing",
     "trip_distance IS NULL OR trip_distance <= 0"),
    ("distance_over_100mi",
     f"Trip distance above {c.MAX_DISTANCE_MI} miles",
     f"trip_distance > {c.MAX_DISTANCE_MI}"),
    ("vendor_fare_not_populated",
     "Vendor 6 (Myle): fare_amount ~$3 on ~$32 trips, so the fare field is unusable",
     "VendorID = 6"),
    ("non_billable_payment",
     "No charge, dispute or voided trip (not revenue)",
     "payment_type IN (3, 4, 6)"),
    ("non_positive_amount",
     "Fare or total is zero/negative, or tip is negative",
     "fare_amount <= 0 OR total_amount <= 0 OR tip_amount < 0"),
    ("fare_over_1000",
     f"Fare above ${c.MAX_FARE}",
     f"fare_amount > {c.MAX_FARE}"),
    ("implausible_speed",
     f"Average speed above {c.MAX_SPEED_MPH} mph",
     f"trip_distance / ({DURATION_SEC} / 3600.0) > {c.MAX_SPEED_MPH}"),
]

# Kept in the data, but flagged so analyses can filter them consciously
FLAG_RULES = [
    ("flag_missing_passenger_count",
     "Passenger count null or 0 (expected for Flex Fare trips)",
     "passenger_count IS NULL OR passenger_count = 0"),
    ("flag_unknown_zone",
     "Pickup or dropoff zone is Unknown / Outside NYC (264, 265)",
     f"PULocationID IN {c.UNKNOWN_ZONES} OR DOLocationID IN {c.UNKNOWN_ZONES}"),
    ("flag_store_and_forward",
     "Record was held in vehicle memory before upload",
     "store_and_fwd_flag = 'Y'"),
]


def drop_reason_sql() -> str:
    whens = "\n".join(f"        WHEN {pred} THEN '{name}'" for name, _, pred in DROP_RULES)
    return f"CASE\n{whens}\n        ELSE NULL\n    END"


def main() -> None:
    t0 = time.perf_counter()
    c.INTERIM.mkdir(parents=True, exist_ok=True)
    c.REPORTS.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()

    con.execute(f"""
        CREATE TEMP TABLE labeled AS
        SELECT *, {drop_reason_sql()} AS drop_reason
        FROM (
            SELECT * EXCLUDE (filename),
                   regexp_extract(filename, '(\\d{{4}}-\\d{{2}})', 1) AS file_month
            FROM read_parquet('{c.RAW_GLOB}', filename = true, union_by_name = true)
        )
    """)

    raw_rows = con.execute("SELECT count(*) FROM labeled").fetchone()[0]
    dropped = dict(con.execute("SELECT drop_reason, count(*) FROM labeled WHERE drop_reason IS NOT NULL GROUP BY 1").fetchall())

    con.execute(f"""
        COPY (
            SELECT * EXCLUDE (drop_reason),
                   {", ".join(f"({pred}) AS {name}" for name, _, pred in FLAG_RULES)}
            FROM labeled WHERE drop_reason IS NULL
        ) TO '{c.CLEAN_TRIPS}' (FORMAT parquet, COMPRESSION zstd)
    """)
    flagged = con.execute(
        f"SELECT {', '.join(f'count(*) FILTER (WHERE {n})' for n, _, _ in FLAG_RULES)} FROM '{c.CLEAN_TRIPS}'"
    ).fetchone()
    clean_rows = con.execute(f"SELECT count(*) FROM '{c.CLEAN_TRIPS}'").fetchone()[0]

    rows, remaining = [], raw_rows
    for name, desc, _ in DROP_RULES:
        n = dropped.get(name, 0)
        remaining -= n
        rows.append({"step": len(rows) + 1, "rule": name, "action": "drop", "description": desc,
                     "rows_affected": n, "pct_of_raw": round(100 * n / raw_rows, 3),
                     "rows_remaining": remaining})
    for (name, desc, _), n in zip(FLAG_RULES, flagged):
        rows.append({"step": None, "rule": name, "action": "flag", "description": desc,
                     "rows_affected": n, "pct_of_raw": round(100 * n / raw_rows, 3),
                     "rows_remaining": None})
    log = pd.DataFrame(rows).astype({"step": "Int64", "rows_remaining": "Int64"})
    log.to_csv(c.CLEANING_LOG, index=False)

    assert remaining == clean_rows, "cleaning log does not reconcile with output"
    pd.set_option("display.width", 200)
    print(log[["step", "rule", "action", "rows_affected", "pct_of_raw", "rows_remaining"]].to_string(index=False))
    print(f"\nraw={raw_rows:,}  clean={clean_rows:,}  kept={100 * clean_rows / raw_rows:.2f}%  "
          f"({time.perf_counter() - t0:.0f}s)")


if __name__ == "__main__":
    main()
