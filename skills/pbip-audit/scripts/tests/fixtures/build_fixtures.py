#!/usr/bin/env python3
"""Regenerate the synthetic PBIP fixtures used by the tests.

    python build_fixtures.py

Creates four tiny projects next to this file:

* ``clean/``   a small, well-built project that should produce no findings
* ``defects/`` the same domain with one seeded defect per implemented rule
* ``legacy/``  a PBIR-Legacy report (report.json only)
* ``thin/``    a thin report bound by connection string
* ``tmsl/``    a project whose model is stored as model.bim
* ``imports/`` synthetic Tabular Editor BPA and Fab Inspector result files,
  an external-usage list and a config file used by the adapter/config tests

All names and data are invented. The generated files are committed so tests do
not depend on this script, but contributors can edit and re-run it.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
VC = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.4.0/schema.json"
PG = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.0.0/schema.json"


def write(path: Path, content: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, (dict, list)):
        content = json.dumps(content, indent=2) + "\n"
    path.write_text(content, encoding="utf-8", newline="\n")


def lit(v: str) -> Dict[str, Any]:
    return {"expr": {"Literal": {"Value": v}}}


def field(kind: str, entity: str, prop: str) -> Dict[str, Any]:
    return {kind: {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}


def visual(name: str, vtype: str, pos: Tuple[float, float, float, float], tab: int,
           fields: List[Tuple[str, str, str, str]] = (), alt: Optional[str] = None,
           title: Optional[str] = None, sync: Optional[str] = None, hidden: bool = False,
           filters: Optional[List[Dict[str, Any]]] = None, objects: Optional[Dict[str, Any]] = None,
           container: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    x, y, w, h = pos
    qs: Dict[str, Any] = {}
    for role, kind, ent, prop in fields:
        qs.setdefault(role, {"projections": []})["projections"].append(
            {"field": field(kind, ent, prop), "queryRef": f"{ent}.{prop}", "nativeQueryRef": prop})
    v: Dict[str, Any] = {"visualType": vtype}
    if qs:
        v["query"] = {"queryState": qs}
    vco: Dict[str, Any] = dict(container or {})
    if alt is not None:
        vco["general"] = [{"properties": {"altText": lit(f"'{alt}'")}}]
    if title is not None:
        vco["title"] = [{"properties": {"show": lit("true"), "text": lit(f"'{title}'")}}]
    if vco:
        v["visualContainerObjects"] = vco
    if objects:
        v["objects"] = objects
    if sync:
        v["syncGroup"] = {"groupName": sync, "fieldChanges": True, "filterChanges": True}
    data: Dict[str, Any] = {"$schema": VC, "name": name,
                            "position": {"x": x, "y": y, "z": tab * 1000, "width": w, "height": h, "tabOrder": tab * 1000},
                            "visual": v}
    if filters:
        data["filterConfig"] = {"filters": filters}
    if hidden:
        data["isHidden"] = True
    return data


def page(name: str, display: str, **extra: Any) -> Dict[str, Any]:
    d = {"$schema": PG, "name": name, "displayName": display, "displayOption": "FitToPage", "height": 720, "width": 1280}
    d.update(extra)
    return d


def back_button(name: str, tab: int) -> Dict[str, Any]:
    v = visual(name, "actionButton", (20, 20, 80, 32), tab)
    v["visual"]["visualContainerObjects"] = {"visualLink": [{"properties": {"show": lit("true"), "type": lit("'Back'")}}]}
    return v


def scaffold(root: Path, name: str, model: bool = True) -> Tuple[Path, Path]:
    if root.exists():
        shutil.rmtree(root)
    rep = root / f"{name}.Report"
    sm = root / f"{name}.SemanticModel"
    write(root / f"{name}.pbip", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
        "version": "1.0", "artifacts": [{"report": {"path": f"{name}.Report"}}], "settings": {"enableAutoRecovery": True}})
    write(rep / "definition.pbir", {"version": "4.0", "datasetReference": {"byPath": {"path": f"../{name}.SemanticModel"}}})
    if model:
        write(sm / "definition.pbism", {"version": "4.2", "settings": {}})
    return rep, sm


def report_common(rep: Path, page_order: List[str], custom_theme: Optional[Dict[str, Any]] = None,
                  base_theme: Optional[Dict[str, Any]] = None) -> None:
    d = rep / "definition"
    write(d / "version.json", {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json", "version": "2.0.0"})
    report: Dict[str, Any] = {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.0.0/schema.json",
                              "themeCollection": {"baseTheme": {"name": "CY24SU10", "type": "SharedResources"}}}
    packages = []
    if base_theme is not None:
        write(rep / "StaticResources" / "SharedResources" / "BaseThemes" / "CY24SU10.json", base_theme)
        packages.append({"name": "SharedResources", "type": "SharedResources",
                         "items": [{"name": "CY24SU10", "path": "BaseThemes/CY24SU10.json", "type": "BaseTheme"}]})
    if custom_theme is not None:
        write(rep / "StaticResources" / "RegisteredResources" / "BrandTheme.json", custom_theme)
        report["themeCollection"]["customTheme"] = {"name": "BrandTheme.json", "type": "RegisteredResources"}
        packages.append({"name": "RegisteredResources", "type": "RegisteredResources",
                         "items": [{"name": "BrandTheme.json", "path": "BrandTheme.json", "type": "CustomTheme"}]})
    if packages:
        report["resourcePackages"] = packages
    write(d / "report.json", report)
    write(d / "pages" / "pages.json", {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
                                       "pageOrder": page_order, "activePageName": page_order[0]})


def add_visual(rep: Path, page_name: str, data: Dict[str, Any], mobile: bool = False) -> None:
    vdir = rep / "definition" / "pages" / page_name / "visuals" / data["name"]
    write(vdir / "visual.json", data)
    if mobile:
        write(vdir / "mobile.json", {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainerMobileState/2.0.0/schema.json",
                                     "position": {"x": 0, "y": 0, "z": 0, "width": 300, "height": 120, "tabOrder": 0}})


# ---------------------------------------------------------------------------
# clean
# ---------------------------------------------------------------------------

CLEAN_MODEL = """model Model
\tculture: en-US
\tdiscourageImplicitMeasures
\tdefaultPowerBIDataSourceVersion: powerBI_V3

annotation __PBI_TimeIntelligenceEnabled = 0

ref table Calendar
ref table Product
ref table Orders
"""

CLEAN_CALENDAR = """/// Shared calendar, one row per day.
table Calendar
\tdataCategory: Time

\t/// Calendar day.
\tcolumn Date
\t\tdataType: dateTime
\t\tisKey
\t\tformatString: yyyy-mm-dd
\t\tsummarizeBy: none
\t\tsourceColumn: [Date]

\t/// Calendar year.
\tcolumn Year = YEAR('Calendar'[Date])
\t\tdataType: int64
\t\tformatString: 0
\t\tsummarizeBy: none

\t/// Month number.
\tcolumn Month = MONTH('Calendar'[Date])
\t\tdataType: int64
\t\tformatString: 0
\t\tsummarizeBy: none

\tpartition Calendar = calculated
\t\tmode: import
\t\tsource = CALENDAR(DATE(2020, 1, 1), DATE(2025, 12, 31))
"""

CLEAN_PRODUCT = """/// Product dimension.
table Product

\tcolumn ProductKey
\t\tdataType: int64
\t\tisHidden
\t\tisKey
\t\tsummarizeBy: none
\t\tsourceColumn: ProductKey

\t/// Product category.
\tcolumn Category
\t\tdataType: string
\t\tsummarizeBy: none
\t\tsourceColumn: Category

\t/// Product colour.
\tcolumn Color
\t\tdataType: string
\t\tsummarizeBy: none
\t\tsourceColumn: Color

\tpartition Product = m
\t\tmode: import
\t\tsource =
\t\t\t\tlet
\t\t\t\t    Source = #table({"ProductKey", "Category", "Color"}, {{1, "Bikes", "Red"}})
\t\t\t\tin
\t\t\t\t    Source
"""

CLEAN_ORDERS = """/// Order lines.
table Orders

\t/// Revenue of the order lines in context.
\tmeasure Revenue = SUM(Orders[Amount])
\t\tformatString: #,0
\t\tdisplayFolder: Sales

\t/// Units sold.
\tmeasure Units = SUM(Orders[Quantity])
\t\tformatString: #,0

\t/// Revenue per unit.
\tmeasure 'Avg Price' = DIVIDE([Revenue], [Units])
\t\tformatString: #,0.00

\t/// Revenue of the same period one year earlier.
\tmeasure 'Revenue PY' = CALCULATE([Revenue], SAMEPERIODLASTYEAR('Calendar'[Date]))
\t\tformatString: #,0

\t/// Revenue of the last 12 months up to today; ignores the date selection.
\tmeasure 'Revenue Last 12M' =
\t\t\tCALCULATE(
\t\t\t    [Revenue],
\t\t\t    REMOVEFILTERS('Calendar'),
\t\t\t    DATESINPERIOD('Calendar'[Date], TODAY(), -12, MONTH)
\t\t\t)
\t\tformatString: #,0

\tcolumn OrderDate
\t\tdataType: dateTime
\t\tisHidden
\t\tsummarizeBy: none
\t\tsourceColumn: OrderDate

\tcolumn ProductKey
\t\tdataType: int64
\t\tisHidden
\t\tsummarizeBy: none
\t\tsourceColumn: ProductKey

\tcolumn Amount
\t\tdataType: decimal
\t\tisHidden
\t\tsummarizeBy: none
\t\tsourceColumn: Amount

\tcolumn Quantity
\t\tdataType: int64
\t\tisHidden
\t\tsummarizeBy: none
\t\tsourceColumn: Quantity

\tpartition Orders = m
\t\tmode: import
\t\tsource =
\t\t\t\tlet
\t\t\t\t    Source = #table({"OrderDate", "ProductKey", "Amount", "Quantity"}, {{#date(2024, 1, 1), 1, 10, 1}})
\t\t\t\tin
\t\t\t\t    Source
"""

CLEAN_RELS = """relationship rel_orders_date
\tfromColumn: Orders.OrderDate
\ttoColumn: Calendar.Date

relationship rel_orders_product
\tfromColumn: Orders.ProductKey
\ttoColumn: Product.ProductKey
"""


BASE_THEME = {
    "name": "CY24SU10",
    "dataColors": ["#118DFF", "#12239E", "#E66C37", "#6B007B", "#E044A7", "#744EC2", "#D9B300", "#D64550"],
    "foreground": "#252423", "foregroundNeutralSecondary": "#605E5C", "background": "#FFFFFF",
    "backgroundLight": "#F3F2F1", "tableAccent": "#118DFF", "good": "#1AAB40", "neutral": "#D9B300", "bad": "#D64554",
    "textClasses": {"callout": {"fontSize": 45, "color": "#252423"}, "title": {"fontSize": 12, "color": "#252423"},
                    "label": {"fontSize": 10, "color": "#252423"}},
}

# Custom theme with seeded colour problems: low-contrast foreground (A11Y-05 text),
# a pale series colour (A11Y-05 graphics) and a red/green pair (A11Y-07).
DEFECT_THEME = {
    "name": "Brand",
    "dataColors": ["#D62728", "#2CA02C", "#1F77B4", "#FFE600", "#9467BD", "#8C564B", "#17BECF", "#7F7F7F"],
    "foreground": "#9A9A9A",
    "background": "#FFFFFF",
}


def theme_color(color_id: int, percent: float = 0) -> Dict[str, Any]:
    return {"solid": {"color": {"expr": {"ThemeDataColor": {"ColorId": color_id, "Percent": percent}}}}}


def build_clean() -> None:
    root = HERE / "clean"
    rep, sm = scaffold(root, "Clean")
    d = sm / "definition"
    write(d / "database.tmdl", "database Clean\n\tcompatibilityLevel: 1600\n")
    write(d / "model.tmdl", CLEAN_MODEL)
    write(d / "tables" / "Calendar.tmdl", CLEAN_CALENDAR)
    write(d / "tables" / "Product.tmdl", CLEAN_PRODUCT)
    write(d / "tables" / "Orders.tmdl", CLEAN_ORDERS)
    write(d / "relationships.tmdl", CLEAN_RELS)

    report_common(rep, ["overview", "productDetail", "categoryDrill"], base_theme=BASE_THEME)
    pages = rep / "definition" / "pages"
    write(pages / "overview" / "page.json", page("overview", "Overview"))
    cards = [("Revenue", "Revenue"), ("Units", "Units"), ("Revenue PY", "Revenue, prior year"),
             ("Revenue Last 12M", "Revenue, last 12 months")]
    for i, (m, title) in enumerate(cards):
        add_visual(rep, "overview", visual(f"card{i}", "card", (20 + 310 * i, 20, 290, 110), i,
                                           [("Values", "Measure", "Orders", m)], alt=f"{title} card", title=title),
                   mobile=(i == 0))
    add_visual(rep, "overview", visual("slicerYear", "slicer", (20, 150, 290, 90), 4,
                                       [("Values", "Column", "Calendar", "Year")], sync="Year"))
    add_visual(rep, "overview", visual("slicerColor", "slicer", (330, 150, 290, 90), 5,
                                       [("Values", "Column", "Product", "Color")], sync="Color"))
    price = visual("priceByMonth", "clusteredColumnChart", (20, 260, 1240, 440), 6,
                   [("Category", "Column", "Calendar", "Month"), ("Y", "Measure", "Orders", "Avg Price")],
                   alt="Average price by month", title="Average price by month")
    price["visual"]["visualContainerObjects"]["title"][0]["properties"]["fontColor"] = theme_color(1)
    add_visual(rep, "overview", price)

    write(pages / "productDetail" / "page.json", page("productDetail", "Product Detail"))
    add_visual(rep, "productDetail", visual("slicerYear2", "slicer", (20, 20, 290, 90), 0,
                                            [("Values", "Column", "Calendar", "Year")], sync="Year"))
    add_visual(rep, "productDetail", visual("tbl", "tableEx", (20, 130, 1240, 560), 1,
                                            [("Values", "Column", "Product", "Category"), ("Values", "Measure", "Orders", "Revenue"),
                                             ("Values", "Measure", "Orders", "Units")],
                                            alt="Revenue and units by category", title="Revenue and units by category"))

    drill = page("categoryDrill", "Category Drill", visibility="HiddenInViewMode",
                 pageBinding={"name": "a1b2c3d4e5f6a7b8c9d0", "type": "Drillthrough",
                              "parameters": [{"name": "p1", "boundFilter": "f1",
                                              "fieldExpr": field("Column", "Product", "Category")}]})
    write(pages / "categoryDrill" / "page.json", drill)
    add_visual(rep, "categoryDrill", back_button("backBtn", 0))
    add_visual(rep, "categoryDrill", visual("drillTbl", "tableEx", (20, 70, 1240, 620), 1,
                                            [("Values", "Column", "Product", "Color"), ("Values", "Measure", "Orders", "Revenue")],
                                            alt="Revenue by colour for the selected category", title="Revenue by colour"))


# ---------------------------------------------------------------------------
# defects
# ---------------------------------------------------------------------------

DEF_MODEL = """model Model
\tculture: en-US

annotation __PBI_TimeIntelligenceEnabled = 1

ref table Calendar
ref table Product
ref table 'Product Extra'
ref table Orders
"""

DEF_CALENDAR = """table Calendar

\tcolumn Date
\t\tdataType: dateTime
\t\tisKey
\t\tsummarizeBy: none
\t\tsourceColumn: [Date]

\tcolumn Year = YEAR('Calendar'[Date])
\t\tdataType: int64
\t\tsummarizeBy: none

\tpartition Calendar = calculated
\t\tmode: import
\t\tsource = CALENDAR(DATE(2020, 1, 1), DATE(2031, 12, 31))
"""

DEF_PRODUCT = """table Product

\tcolumn ProductKey
\t\tdataType: int64
\t\tisKey
\t\tsummarizeBy: none
\t\tsourceColumn: ProductKey

\tcolumn Category
\t\tdataType: string
\t\tsummarizeBy: none
\t\tsourceColumn: Category

\tcolumn Color
\t\tdataType: string
\t\tsummarizeBy: none
\t\tsourceColumn: Color

\tcolumn Weight
\t\tdataType: double
\t\tsummarizeBy: none
\t\tsourceColumn: Weight

\tcolumn 'Unused Attr'
\t\tdataType: string
\t\tsummarizeBy: none
\t\tsourceColumn: UnusedAttr

\t%%% this line is not valid TMDL

\tpartition Product = m
\t\tmode: import
\t\tsource =
\t\t\t\tlet
\t\t\t\t    Source = Sql.Database("db.example.invalid", "demo", [Query="select 1", ConnectionString="Uid=demo;Password=hunter2"])
\t\t\t\tin
\t\t\t\t    Source
"""

DEF_EXTRA = """table 'Product Extra'

\tcolumn ProductKey
\t\tdataType: int64
\t\tisHidden
\t\tsummarizeBy: none
\t\tsourceColumn: ProductKey

\tcolumn Notes
\t\tdataType: string
\t\tsummarizeBy: none
\t\tsourceColumn: Notes
"""

LONG = "Units sold in the current filter context. " * 6

DEF_ORDERS = f"""table Orders

\tmeasure Revenue = SUM(Orders[Amount])

\t/// {LONG.strip()}
\tmeasure Units = SUM(Orders[Quantity])
\t\tformatString: #,0

\t/// Average price.
\tmeasure 'Avg Price' = [Revenue] / [Units]
\t\tformatString: #,0.00

\t/// Ratio with an error trap.
\tmeasure 'Safe Ratio' = IFERROR(DIVIDE([Revenue], [Units]), BLANK())
\t\tformatString: 0.00

\t/// Ratio that turns blanks into zero.
\tmeasure 'Margin Pct' = DIVIDE([Revenue], [Units], 0)
\t\tformatString: 0.0%

\t/// Work in progress.
\tmeasure Draft =
\t\t\t// TODO replace with the real rule
\t\t\t[Revenue] * 2
\t\tformatString: #,0

\t/// Revenue for the prior year.
\tmeasure 'Revenue PY' = CALCULATE([Revenue], SAMEPERIODLASTYEAR('Calendar'[Date]))
\t\tformatString: #,0

\t/// Revenue shown on the first page.
\tmeasure 'Recent Revenue' =
\t\t\tCALCULATE(
\t\t\t    [Revenue],
\t\t\t    REMOVEFILTERS('Calendar'),
\t\t\t    DATESBETWEEN('Calendar'[Date], TODAY() - 90, TODAY())
\t\t\t)
\t\tformatString: #,0

\t/// Revenue of the rolling 3 months up to today (documented window).
\tmeasure 'Revenue Pulse' =
\t\t\tCALCULATE([Revenue], DATESINPERIOD('Calendar'[Date], TODAY(), -3, MONTH))
\t\tformatString: #,0

\t/// Nobody uses this.
\tmeasure 'Orphan Measure' = 1
\t\tformatString: 0

\tcolumn OrderDate
\t\tdataType: dateTime
\t\tsummarizeBy: none
\t\tsourceColumn: OrderDate

\tcolumn ShipDate
\t\tdataType: dateTime
\t\tisHidden
\t\tsummarizeBy: none
\t\tsourceColumn: ShipDate

\tcolumn ProductKey
\t\tdataType: int64
\t\tisHidden
\t\tsummarizeBy: none
\t\tsourceColumn: ProductKey

\tcolumn Amount
\t\tdataType: decimal
\t\tisHidden
\t\tsummarizeBy: none
\t\tsourceColumn: Amount

\tcolumn Quantity
\t\tdataType: int64
\t\tisHidden
\t\tsummarizeBy: none
\t\tsourceColumn: Quantity
"""

DEF_RELS = """relationship rel_orders_date
\tfromColumn: Orders.OrderDate
\ttoColumn: Calendar.Date

relationship rel_orders_ship
\tisActive: false
\tfromColumn: Orders.ShipDate
\ttoColumn: Calendar.Date

relationship rel_orders_product
\tcrossFilteringBehavior: bothDirections
\tfromColumn: Orders.ProductKey
\ttoColumn: Product.ProductKey

relationship rel_product_extra
\tfromCardinality: one
\ttoCardinality: one
\tfromColumn: Product.ProductKey
\ttoColumn: 'Product Extra'.ProductKey
"""


def build_defects() -> None:
    root = HERE / "defects"
    rep, sm = scaffold(root, "Defects")
    d = sm / "definition"
    write(d / "database.tmdl", "database Defects\n\tcompatibilityLevel: 1600\n")
    write(d / "model.tmdl", DEF_MODEL)
    write(d / "tables" / "Calendar.tmdl", DEF_CALENDAR)
    write(d / "tables" / "Product.tmdl", DEF_PRODUCT)
    write(d / "tables" / "Product Extra.tmdl", DEF_EXTRA)
    write(d / "tables" / "Orders.tmdl", DEF_ORDERS)
    write(d / "relationships.tmdl", DEF_RELS)

    report_common(rep, ["page1", "page2", "scratch", "drill"], custom_theme=DEFECT_THEME)
    pages = rep / "definition" / "pages"

    # page1: default name, busy, no alt text, reversed tab order, hex colour, off-canvas visual,
    # unlabeled window measure, broken bindings, slicer issues, hidden filter
    write(pages / "page1" / "page.json", page("page1", "Page 1"))
    measures = ["Revenue", "Units", "Avg Price", "Safe Ratio", "Margin Pct", "Draft", "Revenue PY",
                "Revenue", "Units", "Avg Price", "Safe Ratio", "Margin Pct"]
    n = len(measures)
    for i, m in enumerate(measures):
        x, y = 20 + (i % 4) * 310, 20 + (i // 4) * 120
        objects = {"labels": [{"properties": {"color": {"solid": {"color": lit("'#FF0000'")}}}}]} if i == 0 else None
        add_visual(rep, "page1", visual(f"card{i:02d}", "card", (x, y, 290, 100), n - i,
                                        [("Values", "Measure", "Orders", m)], title=m, objects=objects))
    add_visual(rep, "page1", visual("windowCard", "card", (1200, 400, 200, 100), 20,
                                    [("Values", "Measure", "Orders", "Recent Revenue")], title="Revenue"))
    add_visual(rep, "page1", visual("broken", "card", (20, 400, 200, 100), 21,
                                    [("Values", "Measure", "Orders", "Ghost Measure"), ("Values", "Column", "Missing", "Thing")],
                                    title="Broken"))
    hidden_filter = {"name": "hf1", "field": field("Column", "Product", "Category"), "type": "Categorical",
                     "isHiddenInViewMode": True}
    add_visual(rep, "page1", visual("slicerCat", "slicer", (20, 520, 290, 90), 22,
                                    [("Values", "Column", "Product", "Category")], sync="Mixed", filters=[hidden_filter]))
    add_visual(rep, "page1", visual("slicerYearA", "slicer", (330, 520, 290, 90), 23,
                                    [("Values", "Column", "Calendar", "Year")], sync="YearA"))
    add_visual(rep, "page1", visual("slicerHidden", "slicer", (640, 520, 290, 90), 24,
                                    [("Values", "Column", "Product", "Color")], sync="Hidden", hidden=True))

    # page2: duplicate name, mixed sync group, second year group, pie, gauge, wide table
    write(pages / "page2" / "page.json", page("page2", "Duplicate of Page 1"))
    add_visual(rep, "page2", visual("slicerColor", "slicer", (20, 20, 290, 90), 0,
                                    [("Values", "Column", "Product", "Color")], sync="Mixed"))
    add_visual(rep, "page2", visual("slicerYearB", "slicer", (330, 20, 290, 90), 1,
                                    [("Values", "Column", "Calendar", "Year")], sync="YearB"))
    add_visual(rep, "page2", visual("pie", "pieChart", (20, 130, 400, 300), 2,
                                    [("Category", "Column", "Product", "Category"), ("Y", "Measure", "Orders", "Revenue")],
                                    alt="Revenue share by category"))
    add_visual(rep, "page2", visual("gauge", "gauge", (440, 130, 400, 300), 3,
                                    [("Y", "Measure", "Orders", "Margin Pct")], alt="Margin gauge"))
    wide = [("Values", "Column", "Product", "Category")] * 21
    add_visual(rep, "page2", visual("wideTable", "tableEx", (20, 450, 1240, 250), 4, wide, alt="Wide table"))
    # white title text (theme background, ThemeDataColor 0) on the default white background: A11Y-05
    pulse = visual("pulse", "card", (860, 130, 400, 140), 5, [("Values", "Measure", "Orders", "Revenue Pulse")],
                   alt="Revenue pulse",
                   container={"title": [{"properties": {"show": lit("true"), "text": lit("'Sales'"), "fontColor": theme_color(0)}}]})
    # a literal colour that equals a theme colour (VD-06 Info on this page)
    pulse["visual"]["objects"] = {"labels": [{"properties": {"color": {"solid": {"color": lit("'#1F77B4'")}}}}]}
    add_visual(rep, "page2", pulse)

    # scratch: hidden, unreachable
    scratch = page("scratch", "Scratch", visibility="HiddenInViewMode")
    del scratch["displayOption"]  # GOV-17 with --validate-schemas: required by the page schema
    write(pages / "scratch" / "page.json", scratch)
    note = visual("note", "textbox", (20, 20, 300, 60), 0)
    note["$schema"] = VC.replace("/2.4.0/", "/2.99.0/")  # GOV-18: version not in the schema cache
    add_visual(rep, "scratch", note)

    # drill: drillthrough without back button
    write(pages / "drill" / "page.json", page("drill", "Category Drill", visibility="HiddenInViewMode",
                                              pageBinding={"name": "b1c2d3e4f5a6b7c8d9e0", "type": "Drillthrough",
                                                           "parameters": [{"name": "p1", "boundFilter": "f1",
                                                                           "fieldExpr": field("Column", "Product", "Category")}]}))
    add_visual(rep, "drill", visual("drillTbl", "tableEx", (20, 20, 1240, 680), 0,
                                    [("Values", "Column", "Product", "Category"), ("Values", "Measure", "Orders", "Revenue")],
                                    alt="Detail"))

    # folder name that Desktop ignores
    write(pages / "bad page!" / "page.json", page("bad page!", "Ignored"))
    # unparseable visual.json
    write(pages / "page2" / "visuals" / "corrupt" / "visual.json", '{"name": "corrupt", "position": {')

    # bookmark with stale state
    write(rep / "definition" / "bookmarks" / "bm1.bookmark.json", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/bookmark/1.4.0/schema.json",
        "displayName": "Old view", "name": "bm1",
        "explorationState": {"version": "1.3", "activeSection": "page1", "sections": {"page1": {"visualContainers": {
            "card00": {"singleVisual": {"visualType": "card", "objects": {}, "query": {"queryState": {"Values": {"projections": [
                {"field": field("Measure", "Orders", "Deleted Measure"), "queryRef": "Orders.Deleted Measure"}]}}}}}}}}},
    })


# ---------------------------------------------------------------------------
# legacy + thin
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# imports: synthetic outputs of other tools, config and external usage
# ---------------------------------------------------------------------------


def build_imports() -> None:
    root = HERE / "imports"
    if root.exists():
        shutil.rmtree(root)
    # semantic-link-labs run_model_bpa(...) exported with DataFrame.to_json(orient="records")
    write(root / "bpa_results.json", [
        {"Category": "DAX Expressions", "Rule Name": "Use the DIVIDE function for division", "Severity": "Warning",
         "Object Type": "Measure", "Object Name": "Avg Price", "Table Name": "Orders",
         "Description": "Use DIVIDE instead of /.", "URL": "https://learn.microsoft.com/dax/best-practices/dax-divide-function-operator"},
        {"Category": "Performance", "Rule Name": "Avoid floating point data types", "Severity": "Error",
         "Object Type": "Column", "Object Name": "'Product'[Weight]", "Description": "", "URL": ""},
        {"Category": "Maintenance", "Rule Name": "Objects with no description", "Severity": "Info",
         "Object Type": "Table", "Object Name": "Nowhere", "Description": "", "URL": ""},
    ])
    # Tabular Editor 2 CLI -A output, plain and -G (GitHub) / -V (Azure DevOps) annotation styles
    write(root / "bpa_console.txt", "\n".join([
        "Loading model...",
        "Measure 'Orders'[Avg Price] violates rule \"Use the DIVIDE function for division\"",
        "::warning::Column 'Product'[Weight] violates rule \"Avoid floating point data types\"",
        "##vso[task.logissue type=error;]Table 'Product Extra' violates rule \"Remove tables without measures\"",
        "BPA analysis complete.",
    ]) + "\n")
    write(root / "fabinspector_results.json", {"Results": [
        {"RuleId": "ENSURE_THEME_COLOURS", "RuleName": "Ensure theme colours", "RuleDescription": "Avoid hard-coded hex colours.",
         "LogType": "Warning", "Pass": False, "ItemPath": "Defects.Report/definition/pages/page1/visuals/card00/visual.json",
         "Expected": [], "Actual": ["#FF0000"]},
        {"RuleId": "REDUCE_VISUALS_ON_PAGE", "RuleName": "Reduce visuals on page", "LogType": "Error", "Pass": False,
         "ParentDisplayName": "Page 1", "Expected": 20, "Actual": 25},
        {"RuleId": "ENSURE_ALTTEXT", "RuleName": "Ensure alt text", "LogType": "Warning", "Pass": True},
    ]})
    write(root / "external-usage.txt", "# objects used by other reports on the same model\n'Orders'[Orphan Measure]\nProduct[Unused Attr]\n")
    write(root / "pbip-audit.json", {
        "thresholds": {"max_visuals": 30, "tab_order_tolerance": 0.9},
        "disabled_rules": ["MOB-01"],
        "severity_overrides": {"MOD-10": "Info"},
        "naming": {"locales": ["en"], "extra_default_page_patterns": ["^Scratch$"]},
        "domain_rules": "domain-rules.md",
        "external_usage": "external-usage.txt",
    })


def build_legacy() -> None:
    root = HERE / "legacy"
    rep, _ = scaffold(root, "Legacy", model=False)
    write(rep / "definition.pbir", {"version": "1.0", "datasetReference": {"byConnection": {"connectionString": "Data Source=example"}}})
    write(rep / "report.json", {"config": "{}", "layoutOptimization": 0, "sections": []})


def build_thin() -> None:
    root = HERE / "thin"
    rep, _ = scaffold(root, "Thin", model=False)
    write(rep / "definition.pbir", {"version": "4.0", "datasetReference": {"byConnection": {"connectionString": "Data Source=example"}}})
    report_common(rep, ["main"])
    write(rep / "definition" / "pages" / "main" / "page.json", page("main", "Main"))
    add_visual(rep, "main", visual("c1", "card", (20, 20, 290, 110), 0, [("Values", "Measure", "Remote", "Anything")],
                                   alt="Remote card", title="Remote"), mobile=True)


def build_tmsl() -> None:
    root = HERE / "tmsl"
    rep, sm = scaffold(root, "Tmsl")
    write(sm / "model.bim", {"name": "Tmsl", "compatibilityLevel": 1600, "model": {"tables": []}})
    report_common(rep, ["main"])
    write(rep / "definition" / "pages" / "main" / "page.json", page("main", "Main"))


if __name__ == "__main__":
    build_clean()
    build_defects()
    build_legacy()
    build_thin()
    build_tmsl()
    build_imports()
    print("fixtures written to", HERE)
