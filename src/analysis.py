"""Phase 5: run every query in sql/ against the processed trips and save results as CSV.

Each sql/NN_name.sql file holds one SELECT; the result is written to reports/tables/NN_name.csv.

Usage:  python -m src.analysis            # run all
        python -m src.analysis 04 07      # run only files starting with these prefixes
"""
import sys
import time

import duckdb

from src import config as c


def main(prefixes: list[str]) -> None:
    c.TABLES.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"CREATE VIEW trips AS SELECT * FROM '{c.FEATURE_TRIPS}'")

    for path in sorted(c.SQL_DIR.glob("*.sql")):
        if prefixes and not path.stem.startswith(tuple(prefixes)):
            continue
        t0 = time.perf_counter()
        df = con.execute(path.read_text(encoding="utf-8")).df()
        df.to_csv(c.TABLES / f"{path.stem}.csv", index=False)
        print(f"{path.stem:<28} {len(df):>5} rows  {time.perf_counter() - t0:5.1f}s")


if __name__ == "__main__":
    main(sys.argv[1:])
