"""Shared paths and constants for the NYC Taxi pipeline."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW_YELLOW = DATA / "raw" / "yellow"
REFERENCE = DATA / "reference"
INTERIM = DATA / "interim"
PROCESSED = DATA / "processed"
POWERBI = DATA / "powerbi"
REPORTS = ROOT / "reports"
TABLES = REPORTS / "tables"
FIGURES = REPORTS / "figures"
SQL_DIR = ROOT / "sql"

RAW_GLOB = (RAW_YELLOW / "*.parquet").as_posix()
ZONE_LOOKUP = (REFERENCE / "taxi_zone_lookup.csv").as_posix()
CLEAN_TRIPS = (INTERIM / "trips_clean.parquet").as_posix()
FEATURE_TRIPS = (PROCESSED / "trips.parquet").as_posix()
CLEANING_LOG = REPORTS / "cleaning_log.csv"

# Taxi zone IDs
NEWARK, JFK, LGA = 1, 132, 138
UNKNOWN_ZONES = (264, 265)  # "Unknown" / "Outside of NYC"

PAYMENT_TYPES = {
    0: "Flex Fare", 1: "Credit card", 2: "Cash", 3: "No charge",
    4: "Dispute", 5: "Unknown", 6: "Voided",
}
RATE_CODES = {
    1: "Standard", 2: "JFK", 3: "Newark", 4: "Nassau/Westchester",
    5: "Negotiated", 6: "Group ride", 99: "Unknown",
}

# Plausibility thresholds used by the cleaning rules
MAX_DISTANCE_MI = 100
MAX_DURATION_MIN = 24 * 60
MIN_DURATION_SEC = 60
MAX_FARE = 1000
MAX_SPEED_MPH = 80
