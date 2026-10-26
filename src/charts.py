"""Phase 5: render README/memo charts from the CSVs in reports/tables/.

Colors follow a validated reference palette: categorical slots in fixed order, one-hue
sequential ramp for magnitude, recessive gridlines, text in ink colors (never series colors).

Usage:  python -m src.charts
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

from src import config as c

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]  # categorical slots 1-3
HIGHLIGHT, BASE = SERIES[0], "#b7d3f6"     # emphasised bar vs context bars (blue ramp)
SEQUENTIAL = LinearSegmentedColormap.from_list(
    "blue", ["#f4f8fd", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"])

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 10,
    "text.color": INK, "axes.labelcolor": INK_2, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.edgecolor": AXIS, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "axes.titlesize": 13, "axes.titleweight": "bold", "axes.titlelocation": "left",
})


def table(name: str) -> pd.DataFrame:
    return pd.read_csv(c.TABLES / f"{name}.csv")


def finish(fig, ax, title: str, subtitle: str, name: str) -> None:
    ax.set_title(title, pad=28)
    ax.text(0, 1.02, subtitle, transform=ax.transAxes, color=INK_2, fontsize=9.5, va="bottom")
    fig.text(0.01, 0.01, "Source: NYC TLC Yellow Taxi trip records, Jan-Jun 2026 (cleaned)",
             color=MUTED, fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(c.FIGURES / f"{name}.png", dpi=150)
    plt.close(fig)
    print(f"wrote reports/figures/{name}.png")


def demand_heatmap() -> None:
    df = table("01_demand_heatmap")
    grid = df.pivot(index="pickup_dow", columns="pickup_hour", values="avg_trips_per_hour")
    days = df.drop_duplicates("pickup_dow").set_index("pickup_dow")["pickup_dayname"].str[:3]
    fig, ax = plt.subplots(figsize=(11, 4.2))
    im = ax.imshow(grid.values, cmap=SEQUENTIAL, aspect="auto")
    ax.set_xticks(range(24), [f"{h}" for h in range(24)])
    ax.set_yticks(range(7), days.loc[grid.index])
    ax.set_xlabel("Pickup hour")
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    peak = df.loc[df.avg_trips_per_hour.idxmax()]
    r, col = grid.index.get_loc(peak.pickup_dow), int(peak.pickup_hour)
    ax.add_patch(plt.Rectangle((col - 0.5, r - 0.5), 1, 1, fill=False, ec="#fcfcfb", lw=2))
    cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.01)
    cb.outline.set_visible(False)
    cb.ax.tick_params(colors=MUTED, labelsize=8)
    cb.set_label("Avg trips per hour", color=INK_2)
    finish(fig, ax, "Demand peaks on weekday evenings, not the morning commute",
           f"Average yellow-taxi pickups per hour. Outlined: busiest slot, {peak.pickup_dayname} "
           f"{col}:00 ({peak.avg_trips_per_hour:,.0f} trips/hr)", "01_demand_heatmap")


def earnings_by_hour() -> None:
    df = table("04_earnings_by_hour")
    fig, ax = plt.subplots(figsize=(10, 4.6))
    for color, (day_type, g) in zip(SERIES, df.groupby("day_type")):
        ax.plot(g.pickup_hour, g.earnings_per_meter_hour, color=color, lw=2, label=day_type)
    wk = df[df.day_type == "Weekday"]
    low = wk.loc[wk.earnings_per_meter_hour.idxmin()]
    ax.annotate(f"Weekday low: ${low.earnings_per_meter_hour:.0f}/hr at {int(low.pickup_hour)}:00\n(avg speed {low.avg_speed_mph} mph)",
                xy=(low.pickup_hour, low.earnings_per_meter_hour), xytext=(low.pickup_hour - 6, 62),
                fontsize=9, color=INK, arrowprops=dict(arrowstyle="-", color=INK_2, lw=0.8))
    ax.set_xlim(0, 23)
    ax.set_ylim(55, 120)
    ax.set_xticks(range(0, 24, 3), [f"{h}:00" for h in range(0, 24, 3)])
    ax.yaxis.set_major_formatter("${x:.0f}")
    ax.set_ylabel("Driver earnings per meter-hour")
    ax.legend(frameon=False, loc="upper right", labelcolor=INK_2, ncols=2)
    finish(fig, ax, "Midday traffic cuts hourly earnings by ~30% versus late night",
           "Fare + extra + tip per hour the meter is running (excludes empty cruising, so an upper bound)",
           "02_earnings_by_hour")


def top_zones() -> None:
    df = table("02_top_pickup_zones").head(15).iloc[::-1]
    colors = [HIGHLIGHT if "Airport" in z else BASE for z in df.pu_zone]
    fig, ax = plt.subplots(figsize=(9, 5.6))
    ax.barh(df.pu_zone, df.trips / 1e6, color=colors, height=0.72)
    for y, (v, p) in enumerate(zip(df.trips / 1e6, df.pct_of_trips)):
        ax.text(v + 0.01, y, f"{v:.2f}M  ({p:.1f}%)", va="center", fontsize=8.5, color=INK_2)
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", colors=INK_2, length=0)
    ax.set_xlabel("Pickups (millions)")
    ax.set_xlim(0, 1.25)
    finish(fig, ax, "The Upper East Side, not Midtown, is the busiest pickup area",
           "Top 15 pickup zones, Jan-Jun 2026. Airports highlighted.", "03_top_pickup_zones")


def airports() -> None:
    df = table("07_airports")
    df = df[df.trips > 1000].copy()
    df["label"] = df.apply(lambda r: "City (non-airport)" if r.trip_type == "City" else f"{r.trip_type} {r.direction.lower()}", axis=1)
    df = df.sort_values("earnings_per_meter_hour")
    colors = [BASE if t == "City" else HIGHLIGHT for t in df.trip_type]
    fig, ax = plt.subplots(figsize=(9, 4.4))
    ax.barh(df.label, df.earnings_per_meter_hour, color=colors, height=0.66)
    for y, (v, f) in enumerate(zip(df.earnings_per_meter_hour, df.avg_earnings_per_trip)):
        ax.text(v + 1.5, y, f"\\${v:.0f}/hr  (\\${f:.0f}/trip)", va="center", fontsize=8.5, color=INK_2)
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", colors=INK_2, length=0)
    ax.xaxis.set_major_formatter("${x:.0f}")
    ax.set_xlabel("Driver earnings per meter-hour")
    ax.set_xlim(0, 200)
    finish(fig, ax, "JFK and LGA trips earn 25-55% more per meter-hour than city trips",
           "Excludes time waiting in the airport taxi queue, which can erase the advantage for pickups",
           "04_airport_earnings")


def tip_distribution() -> None:
    df = table("11_tip_distribution")
    presets = {0, 10, 15, 20, 25, 30}
    colors = [HIGHLIGHT if t in presets else BASE for t in df.tip_pct]
    fig, ax = plt.subplots(figsize=(10, 4.4))
    ax.bar(df.tip_pct, df.pct_of_card_trips, color=colors, width=0.8)
    for t in sorted(presets):
        v = df.loc[df.tip_pct == t, "pct_of_card_trips"].iloc[0]
        ax.text(t, v + 1, f"{v:.0f}%" if v >= 1 else f"{v:.1f}%", ha="center", fontsize=8.5, color=INK_2)
    ax.grid(axis="x", visible=False)
    ax.set_xticks(range(0, 41, 5), [f"{t}%" for t in range(0, 41, 5)])
    ax.yaxis.set_major_formatter("{x:.0f}%")
    ax.set_xlabel("Tip as % of fare (card trips, rounded)")
    ax.set_ylabel("Share of card trips")
    finish(fig, ax, "Over half of card riders tip exactly 20%: the default button sets the tip",
           "Distribution of card tip %, Vendor 2 trips (Vendor 1 under-records tips outside Manhattan)",
           "05_tip_distribution")


def flex_share() -> None:
    df = table("08_flex_fare_by_month")
    flex = df[df.pricing == "Flex Fare"].reset_index(drop=True)
    src = table("09_request_source")
    uber_pct = src.loc[src.request_source == "HV0003", "pct_of_june_trips"].sum()
    uber_share_of_flex = 100 * src.loc[src.request_source == "HV0003", "trips"].sum() / src.loc[src.pricing == "Flex Fare", "trips"].sum()
    fig, ax = plt.subplots(figsize=(9, 4.2))
    months = pd.to_datetime(flex.file_month).dt.strftime("%b")
    ax.bar(months, flex.pct_of_month, color=HIGHLIGHT, width=0.6)
    for x, v in enumerate(flex.pct_of_month):
        ax.text(x, v + 0.6, f"{v:.0f}%", ha="center", fontsize=9, color=INK_2)
    ax.annotate(f"June: {uber_share_of_flex:.0f}% of Flex trips ({uber_pct:.0f}% of all\nyellow trips) were booked via Uber (HV0003)",
                xy=(5, flex.pct_of_month.iloc[5]), xytext=(2.6, 33), fontsize=9, color=INK,
                arrowprops=dict(arrowstyle="-", color=INK_2, lw=0.8))
    ax.grid(axis="x", visible=False)
    ax.set_ylim(0, 40)
    ax.yaxis.set_major_formatter("{x:.0f}%")
    ax.set_ylabel("Share of trips")
    finish(fig, ax, "A quarter of yellow-cab trips are upfront-priced, mostly sold through Uber",
           "Flex Fare (payment_type 0) share of yellow taxi trips by month, 2026. Booking channel is recorded from June only.",
           "06_flex_fare_share")


def main() -> None:
    c.FIGURES.mkdir(parents=True, exist_ok=True)
    demand_heatmap()
    earnings_by_hour()
    top_zones()
    airports()
    tip_distribution()
    flex_share()


if __name__ == "__main__":
    main()
