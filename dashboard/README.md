# Power BI dashboard

`NYC Taxi.pbip` is a complete Power BI Project: data model, relationships, 24 DAX measures, theme, and three report pages. It loads a pre-aggregated star schema (1.5M rows) instead of 21M raw trips.

![Overview](screenshots/overview.png)

## Open it
1. Install [Power BI Desktop](https://www.microsoft.com/power-bi/desktop) (free; Windows). Tested on version 2.159 (Oct 2026).
2. Generate the data and the project:
   ```powershell
   .\.venv\Scripts\python -m src.export_powerbi   # data/powerbi/*.csv
   .\.venv\Scripts\python -m src.build_pbip       # dashboard/NYC Taxi.pbip
   ```
3. Double-click **`NYC Taxi.pbip`**, then **Home → Refresh**. The first load of the 165 MB fact table takes a minute or two. Press **Ctrl+S** afterwards so the loaded data is cached for the next open.
4. If you moved the project, update the data path: **Home → Transform data → Edit parameters → DataFolder** (must end with `\`).

`src/build_pbip.py` is the source of truth for the model, measures, pages and visuals. Edit it and regenerate. `python -m src.build_pbip demand` opens the report on a different page, which is useful for reviewing layout changes.

## Pages
All pages share a header with the page title, a one-line takeaway, and synced dropdown filters: **Month · Weekday / weekend · Pickup borough · Pricing type**.

| Page | Visuals |
|---|---|
| **Overview** | 6 KPI cards · Trips by month (MoM % in tooltip) · Flex Fare vs metered mix · Daily trips |
| **Demand** | Weekday × hour heatmap (hover for values) · Pickup bubble map · Top pickup zones |
| **Earnings & Tips** | Earnings per meter-hour by hour (weekday vs weekend) · Airport vs city earnings · Best-paying zones table · Card tip % by time of day · Flex Fare share by month |

Design choices:
- **Bubble map:** a scatter chart of zone centroids (longitude × latitude) in a near-square tile, so NYC keeps its real shape. It needs no Azure Maps/Bing tenant setting, which many company tenants disable.
- **Small samples are hidden** rather than shown misleadingly. The airport chart drops segments under 1,000 trips (e.g. 113 trips *from* Newark). The zone table lists only zones with 10,000+ pickups and excludes Unknown/Outside-NYC.
- **Color carries meaning, not decoration.** Flex Fare is strong blue against light-blue Metered, and City is light blue as the baseline against the airport bars. Each series has a fixed color, independent of sort order.

## Model
| Table | Grain | Notes |
|---|---|---|
| `fact_trips` | date × hour × pickup zone × pricing × payment × trip type | additive sums only; holds all measures |
| `dim_date` | 181 days | marked date table; month/weekday labels sort correctly |
| `dim_hour` | 0–23 | time-of-day bands sort chronologically |
| `dim_zone` | 265 taxi zones | borough, zone, lat/lon centroids |

Relationships: `fact_trips` → each dimension, many-to-one, single direction. All measures are listed in [measures.dax](measures.dax), which is generated.

## Check it against the Python results
With no filters applied (verified in Power BI Desktop):

| Measure | Expected |
|---|---|
| Trips | 21,478,858 |
| Gross revenue | $649.3M |
| Earnings per Meter-Hour | $84.17 |
| Earnings per Meter-Hour, City / LGA from airport | $79 / $112 |
| Avg card tip | 17.4% |
| Flex Fare share | 24.6% |

`Avg card tip` (17.4%) is total tips ÷ total pre-tip charges. The main README's figure (17.6%) averages each trip's tip %, so the two differ slightly.
