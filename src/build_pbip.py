"""Phase 7: generate the Power BI project (PBIP) for the dashboard.

Writes dashboard/NYC Taxi.pbip plus its SemanticModel (TMDL: tables, relationships,
measures) and Report (PBIR JSON: 3 pages of visuals). Open the .pbip in Power BI Desktop
and refresh to load data/powerbi/*.csv (run src.export_powerbi first).

Usage:  python -m src.build_pbip
"""
import json
import shutil
import sys
import time
import uuid
from pathlib import Path

from src import config as c

NAME = "NYC Taxi"
OUT = c.ROOT / "dashboard"
SM = OUT / f"{NAME}.SemanticModel"
RPT = OUT / f"{NAME}.Report"
FABRIC = "https://developer.microsoft.com/json-schemas/fabric"
PAGE_W, PAGE_H = 1280, 720
START = time.time() - 1  # files written after this belong to the current build


def tag(*parts: str) -> str:
    """Deterministic GUID so regenerating the project produces stable diffs."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "nyc-taxi-pbip/" + "/".join(parts)))


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def write_json(path: Path, obj: dict) -> None:
    write(path, json.dumps(obj, indent=2) + "\n")


# --------------------------------------------------------------------------- semantic model

# column: (name, tmdl dataType, extra properties)
M_TYPES = {"dateTime": "type date", "int64": "Int64.Type", "double": "type number",
           "string": "type text", "boolean": "type logical"}

TABLES = {
    "fact_trips": [
        ("pickup_date", "dateTime", {"hidden": True}),
        ("pickup_hour", "int64", {"hidden": True}),
        ("PULocationID", "int64", {"hidden": True}),
        ("pricing", "string", {}),
        ("payment_label", "string", {}),
        ("trip_type", "string", {}),
        ("airport_direction", "string", {}),
        ("trip_segment", "string", {}),
        *[(col, "int64" if col in ("trip_count", "tip_eligible_trips") else "double", {"hidden": True, "sum": True})
          for col in ("trip_count", "distance_mi", "duration_min", "fare_amount", "extra", "tip_amount",
                      "tolls_amount", "total_amount", "driver_earnings", "tip_eligible_trips",
                      "tip_eligible_tips", "tip_eligible_base")],
    ],
    "dim_date": [
        ("date", "dateTime", {"key": True}),
        ("year", "int64", {}),
        ("month_num", "int64", {"hidden": True}),
        ("month_label", "string", {"sortBy": "month_num"}),
        ("weekday_num", "int64", {"hidden": True}),
        ("weekday_name", "string", {"sortBy": "weekday_num"}),
        ("weekday_short", "string", {"sortBy": "weekday_num"}),
        ("day_type", "string", {}),
        ("is_holiday", "boolean", {}),
        ("holiday_name", "string", {}),
    ],
    "dim_hour": [
        ("hour", "int64", {}),
        ("hour_label", "string", {"sortBy": "hour"}),
        ("time_of_day", "string", {"sortBy": "time_of_day_order"}),
        ("time_of_day_order", "int64", {"hidden": True}),
    ],
    "dim_zone": [
        ("LocationID", "int64", {"hidden": True}),
        ("borough", "string", {}),
        ("zone", "string", {}),
        ("service_zone", "string", {}),
        ("is_airport", "boolean", {}),
        ("latitude", "double", {"category": "Latitude"}),
        ("longitude", "double", {"category": "Longitude"}),
    ],
}

RELATIONSHIPS = [
    ("fact_trips", "pickup_date", "dim_date", "date"),
    ("fact_trips", "pickup_hour", "dim_hour", "hour"),
    ("fact_trips", "PULocationID", "dim_zone", "LocationID"),
]

# (name, DAX, format string). Every KPI is a ratio of sums, so it holds at any filter level.
MEASURES = [
    ("Trips", "SUM ( fact_trips[trip_count] )", "#,0"),
    ("Avg Trips per Day", "DIVIDE ( [Trips], DISTINCTCOUNT ( dim_date[date] ) )", "#,0"),
    ("Trips PM", "CALCULATE ( [Trips], DATEADD ( dim_date[date], -1, MONTH ) )", "#,0"),
    ("Trips MoM %", "DIVIDE ( [Trips] - [Trips PM], [Trips PM] )", "+0.0%;-0.0%;0.0%"),
    ("Gross Revenue", "SUM ( fact_trips[total_amount] )", "\\$#,0"),
    ("Driver Earnings", "SUM ( fact_trips[driver_earnings] )", "\\$#,0"),
    ("Meter Hours", "SUM ( fact_trips[duration_min] ) / 60", "#,0"),
    ("Earnings per Meter-Hour", "DIVIDE ( [Driver Earnings], [Meter Hours] )", "\\$#,0.00"),
    ("Earnings per Trip", "DIVIDE ( [Driver Earnings], [Trips] )", "\\$#,0.00"),
    ("Avg Fare", "DIVIDE ( SUM ( fact_trips[fare_amount] ), [Trips] )", "\\$#,0.00"),
    ("Avg Distance (mi)", "DIVIDE ( SUM ( fact_trips[distance_mi] ), [Trips] )", "0.00"),
    ("Avg Speed (mph)", "DIVIDE ( SUM ( fact_trips[distance_mi] ), [Meter Hours] )", "0.0"),
    ("Earnings vs City %",
     "VAR CityRate =\n"
     "    CALCULATE (\n"
     "        [Earnings per Meter-Hour],\n"
     "        REMOVEFILTERS ( fact_trips[trip_type], fact_trips[airport_direction], fact_trips[trip_segment] ),\n"
     "        fact_trips[trip_type] = \"City\"\n"
     "    )\n"
     "RETURN\n"
     "    DIVIDE ( [Earnings per Meter-Hour], CityRate ) - 1", "+0%;-0%;0%"),
    ("Card Tip %", "DIVIDE ( SUM ( fact_trips[tip_eligible_tips] ), SUM ( fact_trips[tip_eligible_base] ) )", "0.0%"),
    ("Flex Fare Share", "DIVIDE ( CALCULATE ( [Trips], fact_trips[pricing] = \"Flex Fare\" ), [Trips] )", "0.0%"),
    ("Airport Trip Share", "DIVIDE ( CALCULATE ( [Trips], fact_trips[trip_type] <> \"City\" ), [Trips] )", "0.0%"),
    # Zone-table helpers: blank for zones under 10k pickups and for the Unknown / Outside-NYC zones,
    # so those rows drop out of the table
    ("Is Ranked Zone", "IF ( [Trips] >= 10000 && SELECTEDVALUE ( dim_zone[service_zone] ) <> \"N/A\", 1, 0 )", "0"),
    ("Trips (10k+ zones)", "IF ( [Is Ranked Zone] = 1, [Trips] )", "#,0"),
    ("Earnings per Trip (10k+ zones)", "IF ( [Is Ranked Zone] = 1, [Earnings per Trip] )", "\\$#,0.00"),
    ("Earnings per Meter-Hour (10k+ zones)", "IF ( [Is Ranked Zone] = 1, [Earnings per Meter-Hour] )", "\\$#,0.00"),
    # Segment chart helper: hides segments too small to trust (e.g. 113 trips from Newark)
    ("Earnings per Meter-Hour (1k+ trips)", "IF ( [Trips] >= 1000, [Earnings per Meter-Hour] )", "\\$#,0.00"),
    # Coordinates for the zone bubble map (scatter of longitude x latitude)
    ("Zone Latitude", "MIN ( dim_zone[latitude] )", "0.0000"),
    ("Zone Longitude", "MIN ( dim_zone[longitude] )", "0.0000"),
]


def q(name: str) -> str:
    """Quote a TMDL object name when it has anything beyond letters, digits and underscore."""
    return name if name.replace("_", "").isalnum() else "'" + name.replace("'", "''") + "'"


def table_tmdl(table: str, columns: list) -> str:
    lines = [f"table {table}"]
    if table == "dim_date":
        lines.append("\tdataCategory: Time")
    lines += [f"\tlineageTag: {tag(table)}", ""]

    if table == "fact_trips":
        for name, dax, fmt in MEASURES:
            if "\n" in dax:
                lines.append(f"\tmeasure {q(name)} =")
                lines += [f"\t\t\t{line}" for line in dax.split("\n")]
            else:
                lines.append(f"\tmeasure {q(name)} = {dax}")
            lines += [f"\t\tformatString: {fmt}", f"\t\tlineageTag: {tag(table, 'measure', name)}", ""]

    for name, dtype, props in columns:
        lines.append(f"\tcolumn {q(name)}")
        lines.append(f"\t\tdataType: {dtype}")
        if props.get("key"):
            lines.append("\t\tisKey")
        if dtype == "dateTime":
            lines.append("\t\tformatString: yyyy-mm-dd")
        elif dtype == "double" and not props.get("category"):
            lines.append("\t\tformatString: #,0.00")
        elif dtype == "int64":
            lines.append("\t\tformatString: 0")
        if props.get("hidden"):
            lines.append("\t\tisHidden")
        if props.get("category"):
            lines.append(f"\t\tdataCategory: {props['category']}")
        lines.append(f"\t\tlineageTag: {tag(table, name)}")
        lines.append(f"\t\tsummarizeBy: {'sum' if props.get('sum') else 'none'}")
        lines.append(f"\t\tsourceColumn: {name}")
        if props.get("sortBy"):
            lines.append(f"\t\tsortByColumn: {props['sortBy']}")
        lines.append("")
        lines.append("\t\tannotation SummarizationSetBy = Automatic")
        if dtype == "dateTime":
            lines.append("")
            lines.append("\t\tannotation UnderlyingDateTimeDataType = Date")
        lines.append("")

    types = ", ".join(f'{{"{name}", {M_TYPES[dtype]}}}' for name, dtype, _ in columns)
    m = [
        "let",
        f'    Source = Csv.Document(File.Contents(DataFolder & "{table}.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),',
        "    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),",
        f'    Typed = Table.TransformColumnTypes(Promoted, {{{types}}}, "en-US")',
        "in",
        "    Typed",
    ]
    lines += [f"\tpartition {table} = m", "\t\tmode: import", "\t\tsource ="]
    lines += [f"\t\t\t\t{line}" for line in m]
    lines += ["", "\tannotation PBI_ResultType = Table", ""]
    return "\n".join(lines)


def build_semantic_model() -> None:
    write_json(SM / "definition.pbism", {
        "$schema": f"{FABRIC}/item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "4.2",
        "settings": {},
    })
    write(SM / "definition" / "database.tmdl", "database\n\tcompatibilityLevel: 1600\n")
    write(SM / "definition" / "model.tmdl", "\n".join([
        "model Model",
        "\tculture: en-US",
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
        "\tsourceQueryCulture: en-US",
        "\tdataAccessOptions",
        "\t\tlegacyRedirects",
        "\t\treturnErrorValuesAsNull",
        "",
        "annotation __PBI_TimeIntelligenceEnabled = 0",
        "",
        "annotation PBI_QueryOrder = " + json.dumps(["DataFolder", *TABLES]),
        "",
        *[f"ref table {t}" for t in TABLES],
        "",
    ]))
    folder = str(c.POWERBI) + "\\"
    write(SM / "definition" / "expressions.tmdl", "\n".join([
        f'expression DataFolder = "{folder}" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]',
        f"\tlineageTag: {tag('DataFolder')}",
        "",
        "\tannotation PBI_ResultType = Text",
        "",
    ]))
    rel = []
    for f_tbl, f_col, t_tbl, t_col in RELATIONSHIPS:
        rel += [f"relationship {tag('rel', f_tbl, f_col)}"]
        if t_col == "date":
            rel += ["\tjoinOnDateBehavior: datePartOnly"]
        rel += [f"\tfromColumn: {f_tbl}.{f_col}", f"\ttoColumn: {t_tbl}.{t_col}", ""]
    write(SM / "definition" / "relationships.tmdl", "\n".join(rel))
    for table, columns in TABLES.items():
        write(SM / "definition" / "tables" / f"{table}.tmdl", table_tmdl(table, columns))


# --------------------------------------------------------------------------- report

def lit(value) -> dict:
    """Literal formatting value: strings single-quoted, ints as L (e.g. precision), floats as D (sizes, units)."""
    if isinstance(value, bool):
        v = "true" if value else "false"
    elif isinstance(value, int):
        v = f"{value}L"
    elif isinstance(value, float):
        v = f"{value:g}D"
    else:
        v = "'" + value.replace("'", "''") + "'"
    return {"expr": {"Literal": {"Value": v}}}


def color(hex_: str) -> dict:
    return {"solid": {"color": lit(hex_)}}


INK, INK_2, MUTED = "#0b0b0b", "#52514e", "#898781"
MILLIONS = 1000000.0


def measure(name: str) -> tuple:
    return ({"Measure": {"Expression": {"SourceRef": {"Entity": "fact_trips"}}, "Property": name}},
            f"fact_trips.{name}", name)


def column(table: str, name: str) -> tuple:
    return ({"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": name}},
            f"{table}.{name}", name)


def projection(field: tuple, display: str | None = None) -> dict:
    expr, ref, native = field
    p = {"field": expr, "queryRef": ref, "nativeQueryRef": native}
    if display:
        p["displayName"] = display
    return p


def container(name: str, x: int, y: int, w: int, h: int, v: dict) -> dict:
    return {
        "$schema": f"{FABRIC}/item/report/definition/visualContainer/1.4.0/schema.json",
        "name": name,
        "position": {"x": x, "y": y, "z": 0, "width": w, "height": h, "tabOrder": 0},
        "visual": v,
    }


def visual(name: str, vtype: str, x: int, y: int, w: int, h: int, roles: dict, title: str | None = None,
           subtitle: str | None = None, sort: tuple | None = None, objects: dict | None = None,
           sync_group: str | None = None, frame: dict | None = None) -> dict:
    v = {
        "visualType": vtype,
        "query": {"queryState": {role: {"projections": [projection(*f) if isinstance(f, list) else projection(f)
                                                         for f in fields]}
                                 for role, fields in roles.items()}},
        "drillFilterOtherVisuals": True,
    }
    if sort:
        v["query"]["sortDefinition"] = {"sort": [{"field": sort[0][0], "direction": sort[1]}], "isDefaultSort": False}
    if objects:
        v["objects"] = objects
    frame = dict(frame or {})
    frame["title"] = [{"properties": {"show": lit(bool(title)), **({"text": lit(title)} if title else {})}}]
    if subtitle:
        frame["subTitle"] = [{"properties": {"show": lit(True), "text": lit(subtitle)}}]
    v["visualContainerObjects"] = frame
    if sync_group:
        v["syncGroup"] = {"groupName": sync_group, "fieldChanges": True, "filterChanges": True}
    return container(name, x, y, w, h, v)


def textbox(name: str, x: int, y: int, w: int, h: int, paragraphs: list) -> dict:
    """paragraphs: list of (text, font size pt, color, bold)."""
    return container(name, x, y, w, h, {
        "visualType": "textbox",
        "objects": {"general": [{"properties": {"paragraphs": [
            {"textRuns": [{"value": text, "textStyle": {
                "fontFamily": "Segoe UI Semibold" if bold else "Segoe UI",
                "fontSize": f"{size}pt", "color": col}}]}
            for text, size, col, bold in paragraphs]}}]},
        "visualContainerObjects": {
            "background": [{"properties": {"show": lit(False)}}],
            "border": [{"properties": {"show": lit(False)}}],
        },
        "drillFilterOtherVisuals": True,
    })


SLICERS = [("dim_date", "month_label", "Month"), ("dim_date", "day_type", "Weekday / weekend"),
           ("dim_zone", "borough", "Pickup borough"), ("fact_trips", "pricing", "Pricing type")]
CONTENT_Y = 84  # top of the content area, below the header band


def header(page: str, title: str, takeaway: str) -> list:
    """Page header: title + one-line takeaway on the left, synced dropdown slicers on the right."""
    out = [textbox(f"{page}_header", 16, 6, 540, 72, [
        (title, 18, INK, True),
        (takeaway, 10, INK_2, False),
    ])]
    x0, gap = 568, 8
    w = (PAGE_W - 16 - x0 - 3 * gap) // 4
    for i, (table, col, label) in enumerate(SLICERS):
        out.append(visual(
            f"{page}_slicer_{col}", "slicer", x0 + i * (w + gap), 12, w, 60,
            {"Values": [[column(table, col), label]]},
            objects={
                "data": [{"properties": {"mode": lit("Dropdown")}}],
                "header": [{"properties": {"show": lit(True), "fontColor": color(INK_2), "textSize": lit(9.0)}}],
                "items": [{"properties": {"textSize": lit(10.0)}}],
            },
            sync_group=f"sync_{col}"))
    return out


def labels(**props) -> dict:
    return {"labels": [{"properties": {"show": lit(True), **{k: lit(v) for k, v in props.items()}}}]}


def series_colors(field: tuple, colors: dict) -> dict:
    """Fixed color per series value, so identity never depends on sort order."""
    return {"dataPoint": [
        {"properties": {"fill": color(hex_)},
         "selector": {"data": [{"scopeId": {"Comparison": {
             "ComparisonKind": 0, "Left": field[0], "Right": {"Literal": {"Value": f"'{value}'"}}}}}]}}
        for value, hex_ in colors.items()]}


def legend(show_title: bool = False) -> dict:
    return {"legend": [{"properties": {"show": lit(True), "showTitle": lit(show_title), "position": lit("Top")}}]}


PRICING_COLORS = {"Flex Fare": "#2a78d6", "Metered": "#b7d3f6"}


def gradient(field: tuple, low: str = "#f4f8fd", high: str = "#0d366b") -> dict:
    return {"solid": {"color": {"expr": {"FillRule": {
        "Input": field[0],
        "FillRule": {"linearGradient2": {
            "min": {"color": {"Literal": {"Value": f"'{low}'"}}},
            "max": {"color": {"Literal": {"Value": f"'{high}'"}}},
            "nullColoringStrategy": {"strategy": {"Literal": {"Value": "'asZero'"}}},
        }},
    }}}}}


def page_overview() -> list:
    # (measure, label, display units, decimals)
    cards = [("Trips", "Trips", MILLIONS, 2), ("Gross Revenue", "Gross revenue", MILLIONS, 1),
             ("Earnings per Meter-Hour", "Driver earnings / meter-hour", 1.0, 2),
             ("Card Tip %", "Avg card tip", 1.0, 1), ("Flex Fare Share", "Flex Fare (upfront) share", 1.0, 1),
             ("Airport Trip Share", "Airport trip share", 1.0, 1)]
    gap = 10
    w = (PAGE_W - 32 - 5 * gap) // 6
    vis = header("overview", "NYC Yellow Taxi · Jan–Jun 2026",
                 "21.5M cleaned trips. A quarter are upfront-priced Flex Fares, mostly booked via Uber.")
    for i, (m, label, units, decimals) in enumerate(cards):
        vis.append(visual(f"overview_card_{i}", "card", 16 + i * (w + gap), CONTENT_Y, w, 92,
                          {"Values": [[measure(m), label]]},
                          objects={"labels": [{"properties": {"fontSize": lit(24.0), "color": color(INK),
                                                              "labelDisplayUnits": lit(units),
                                                              "labelPrecision": lit(decimals)}}],
                                   "categoryLabels": [{"properties": {"fontSize": lit(10.0), "color": color(INK_2)}}]}))
    y2 = CONTENT_Y + 92 + 12
    vis += [
        visual("overview_trips_by_month", "clusteredColumnChart", 16, y2, 618, 250,
               {"Category": [column("dim_date", "month_label")], "Y": [measure("Trips")],
                "Tooltips": [measure("Trips MoM %"), measure("Avg Trips per Day")]},
               title="Trips by month", subtitle="May was the busiest month; hover for month-over-month change",
               objects=labels(labelDisplayUnits=MILLIONS, labelPrecision=2)),
        visual("overview_pricing_mix", "hundredPercentStackedColumnChart", 646, y2, 618, 250,
               {"Category": [column("dim_date", "month_label")], "Y": [measure("Trips")],
                "Series": [column("fact_trips", "pricing")]},
               title="Flex Fare vs metered trips", subtitle="Share of each month's trips by pricing type",
               objects={**labels(labelPrecision=0), **legend(),
                        **series_colors(column("fact_trips", "pricing"), PRICING_COLORS)}),
        visual("overview_trips_by_day", "lineChart", 16, y2 + 262, 1248, PAGE_H - (y2 + 262) - 12,
               {"Category": [column("dim_date", "date")], "Y": [measure("Trips")],
                "Tooltips": [measure("Earnings per Meter-Hour")]},
               title="Daily trips",
               subtitle="Steady weekly rhythm. The biggest drops (23 Feb, 25–26 Jan) are not holidays, so likely severe weather"),
    ]
    return vis


def page_demand() -> list:
    avg = measure("Avg Trips per Day")
    heat = {
        "values": [{
            "properties": {"backColor": gradient(avg), "fontColor": gradient(avg)},
            "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}], "metadata": avg[1]},
        }],
        "subTotals": [{"properties": {"rowSubtotals": lit(False), "columnSubtotals": lit(False)}}],
        "columnHeaders": [{"properties": {"fontColor": color(MUTED), "fontSize": lit(10.0)}}],
        "rowHeaders": [{"properties": {"fontColor": color(INK_2), "fontSize": lit(11.0)}}],
        "grid": [{"properties": {"rowPadding": lit(3), "gridHorizontal": lit(False), "gridVertical": lit(False)}}],
    }
    heat["values"][0]["properties"]["fontSize"] = lit(13.0)  # sets the cell size; text is hidden by matching colors
    hide_axes = {
        "categoryAxis": [{"properties": {"show": lit(False), "showAxisTitle": lit(False), "gridlineShow": lit(False)}}],
        "valueAxis": [{"properties": {"show": lit(False), "showAxisTitle": lit(False), "gridlineShow": lit(False)}}],
        "bubbles": [{"properties": {"bubbleSize": lit(-12.0)}}],
    }
    heat_h = 300
    lower_y = CONTENT_Y + heat_h + 12
    lower_h = PAGE_H - lower_y - 12
    map_w = 400  # ~square plot area keeps NYC's real proportions (lon degrees are ~0.76x lat degrees here)
    return header("demand", "When and where riders hail",
                  "Demand peaks on weekday evenings; pickups dip 6–10% at 16:00 every weekday.") + [
        visual("demand_heatmap", "pivotTable", 16, CONTENT_Y, 1248, heat_h,
               {"Rows": [[column("dim_date", "weekday_short"), "Day"]],
                "Columns": [[column("dim_hour", "hour_label"), "Hour"]],
                "Values": [[avg, "Avg trips per hour"]]},
               title="Average pickups per hour, by weekday and hour",
               subtitle="Darker = busier; hover any cell for the value. Busiest slot: Thursday 21:00 (~8,900 trips/hr)",
               objects=heat),
        visual("demand_zone_map", "scatterChart", 16, lower_y, map_w, lower_h,
               {"Category": [column("dim_zone", "zone")], "X": [measure("Zone Longitude")],
                "Y": [measure("Zone Latitude")], "Size": [measure("Trips")]},
               title="Pickup map", subtitle="Each bubble is a taxi zone, sized by pickups",
               objects=hide_axes),
        visual("demand_top_zones", "clusteredBarChart", 16 + map_w + 12, lower_y, PAGE_W - 32 - map_w - 12, lower_h,
               {"Category": [column("dim_zone", "zone")], "Y": [measure("Trips")],
                "Tooltips": [measure("Earnings per Meter-Hour")]},
               title="Top pickup zones", subtitle="Upper East Side South + North out-pick Midtown; scroll for more",
               sort=(measure("Trips"), "Descending"),
               objects=labels(labelDisplayUnits=1000.0, labelPrecision=0)),
    ]


def page_earnings() -> list:
    lower_y = CONTENT_Y + 312
    lower_h = PAGE_H - lower_y - 12
    return header("earnings", "What drivers earn, and what riders tip",
                  "Midday traffic cuts earnings ~30%; airports pay more; most riders tip exactly 20%.") + [
        visual("earnings_by_hour", "lineChart", 16, CONTENT_Y, 760, 300,
               {"Category": [[column("dim_hour", "hour"), "Pickup hour"]], "Y": [measure("Earnings per Meter-Hour")],
                "Series": [column("dim_date", "day_type")], "Tooltips": [measure("Avg Speed (mph)")]},
               title="Driver earnings per meter-hour, by pickup hour",
               subtitle="Fare + extra + tip per hour with a passenger aboard. Weekday low: ~$72 at 15:00 (8 mph traffic)",
               objects=legend()),
        visual("earnings_by_segment", "clusteredBarChart", 788, CONTENT_Y, 476, 300,
               {"Category": [column("fact_trips", "trip_segment")],
                "Y": [[measure("Earnings per Meter-Hour (1k+ trips)"), "Earnings / meter-hour"]],
                "Tooltips": [measure("Earnings vs City %"), measure("Earnings per Trip"), measure("Trips")]},
               title="Airport vs city: earnings per meter-hour",
               subtitle="City in light blue. Before airport queue time, which the data doesn't record",
               sort=(measure("Earnings per Meter-Hour (1k+ trips)"), "Descending"),
               objects={**labels(labelPrecision=0),
                        **series_colors(column("fact_trips", "trip_segment"), {"City": "#b7d3f6"})}),
        visual("earnings_zone_table", "tableEx", 16, lower_y, 530, lower_h,
               {"Values": [[column("dim_zone", "zone"), "Pickup zone"], [measure("Trips (10k+ zones)"), "Trips"],
                           [measure("Earnings per Trip (10k+ zones)"), "Earnings / trip"],
                           [measure("Earnings per Meter-Hour (10k+ zones)"), "Earnings / meter-hour"]]},
               title="Best-paying pickup zones", subtitle="Zones with 10,000+ pickups, ranked by earnings per meter-hour",
               sort=(measure("Earnings per Meter-Hour (10k+ zones)"), "Descending"),
               objects={"values": [{"properties": {"fontSize": lit(9.0)}}],
                        "columnHeaders": [{"properties": {"fontSize": lit(9.0), "fontColor": color(INK_2)}}],
                        "total": [{"properties": {"fontSize": lit(9.0)}}]}),
        visual("earnings_tip_by_time", "clusteredBarChart", 558, lower_y, 360, lower_h,
               {"Category": [column("dim_hour", "time_of_day")], "Y": [measure("Card Tip %")]},
               title="Card tip % by time of day", subtitle="Flat all day: the payment screen's preset buttons set tips",
               objects={**labels(labelPrecision=1),
                        "categoryAxis": [{"properties": {"maxMarginFactor": lit(45.0), "showAxisTitle": lit(False)}}],
                        "valueAxis": [{"properties": {"showAxisTitle": lit(False)}}]}),
        visual("earnings_flex_by_month", "clusteredColumnChart", 930, lower_y, 334, lower_h,
               {"Category": [column("dim_date", "month_label")], "Y": [measure("Flex Fare Share")]},
               title="Flex Fare share by month", subtitle="Upfront-priced trips; in June 92% were booked via Uber",
               objects=labels(labelPrecision=0)),
    ]


PAGES = [("overview", "Overview", page_overview), ("demand", "Demand", page_demand),
         ("earnings", "Earnings & Tips", page_earnings)]
ACTIVE_PAGE = PAGES[0][0]  # page the report opens on; override with: python -m src.build_pbip demand


def build_report() -> None:
    write_json(RPT / "definition.pbir", {
        "$schema": f"{FABRIC}/item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0",
        "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}},
    })
    d = RPT / "definition"
    write_json(d / "version.json", {
        "$schema": f"{FABRIC}/item/report/definition/versionMetadata/1.0.0/schema.json",
        "version": "2.0.0",
    })
    theme = "NYCTaxiTheme.json"
    write_json(d / "report.json", {
        "$schema": f"{FABRIC}/item/report/definition/report/1.2.0/schema.json",
        "themeCollection": {"customTheme": {"name": theme, "reportVersionAtImport": "5.55", "type": "RegisteredResources"}},
        "layoutOptimization": "None",
        "resourcePackages": [{"name": "RegisteredResources", "type": "RegisteredResources",
                              "items": [{"name": theme, "path": theme, "type": "CustomTheme"}]}],
        "settings": {"useStylableVisualContainerHeader": True, "defaultDrillFilterOtherVisuals": True},
    })
    res = RPT / "StaticResources" / "RegisteredResources" / theme
    res.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(OUT / "theme.json", res)

    write_json(d / "pages" / "pages.json", {
        "$schema": f"{FABRIC}/item/report/definition/pagesMetadata/1.0.0/schema.json",
        # Desktop opens on the first page in pageOrder, so a review build moves ACTIVE_PAGE to the front.
        "pageOrder": [ACTIVE_PAGE] + [p for p, _, _ in PAGES if p != ACTIVE_PAGE],
        "activePageName": ACTIVE_PAGE,
    })
    for page, display, build in PAGES:
        write_json(d / "pages" / page / "page.json", {
            "$schema": f"{FABRIC}/item/report/definition/page/1.3.0/schema.json",
            "name": page, "displayName": display, "displayOption": "FitToPage",
            "height": PAGE_H, "width": PAGE_W,
        })
        for z, vis in enumerate(build()):
            vis["position"]["z"] = vis["position"]["tabOrder"] = z * 1000
            write_json(d / "pages" / page / "visuals" / vis["name"] / "visual.json", vis)


def check_names() -> None:
    """Power BI names are case-insensitive and a measure may not share a name with any column."""
    columns = {name.lower() for cols in TABLES.values() for name, _, _ in cols}
    clashes = [m for m, _, _ in MEASURES if m.lower() in columns]
    assert not clashes, f"measure names clash with columns: {clashes}"


def main() -> None:
    global ACTIVE_PAGE
    if len(sys.argv) > 1:
        ACTIVE_PAGE = sys.argv[1]
    check_names()
    # Remove stale generated files rather than whole folders: OneDrive often denies rmdir.
    # Desktop's own .pbi/ state (cache, local settings) is left alone.
    before = {p for folder in (SM, RPT) if folder.exists() for p in folder.rglob("*")
              if p.is_file() and ".pbi" not in p.parts}
    build_semantic_model()
    build_report()
    after = {p for folder in (SM, RPT) for p in folder.rglob("*") if p.is_file() and p.stat().st_mtime_ns > 0}
    generated = {p for p in after if p not in before or p.stat().st_mtime >= START}
    for stale in before - generated:
        stale.unlink()
    for d in sorted((p for folder in (SM, RPT) for p in folder.rglob("*") if p.is_dir()), key=lambda p: -len(p.parts)):
        try:
            d.rmdir()  # only succeeds when empty
        except OSError:
            pass
    write_json(OUT / f"{NAME}.pbip", {
        "$schema": f"{FABRIC}/pbip/pbipProperties/1.0.0/schema.json",
        "version": "1.0",
        "artifacts": [{"report": {"path": f"{NAME}.Report"}}],
        "settings": {"enableAutoRecovery": True},
    })
    write(OUT / ".gitignore", "**/.pbi/localSettings.json\n**/.pbi/cache.abf\n")
    write(OUT / "measures.dax", "\n".join(
        ["// DAX measures in the NYC Taxi semantic model (all defined on fact_trips).",
         "// Generated by src/build_pbip.py; edit MEASURES there, not this file.", ""]
        + [f"{name} =\n{dax}\n// format: {fmt}\n" for name, dax, fmt in MEASURES]))
    n = sum(1 for _ in RPT.rglob("visual.json"))
    print(f"wrote {OUT / (NAME + '.pbip')}  ({len(TABLES)} tables, {len(MEASURES)} measures, {len(PAGES)} pages, {n} visuals)")


if __name__ == "__main__":
    main()
