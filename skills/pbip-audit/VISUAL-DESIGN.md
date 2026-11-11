# Visual design

Rules about chart choice, colour handling and layout. Only structural facts are deterministic (visual type, literal colours, positions). Everything that depends on the rendered pixels (contrast, clutter, axis perception) is J and must be stated as provisional until someone looks at the rendered report.

## Rules

<!-- BEGIN GENERATED RULES -->

<!-- Generated from scripts/pbip_audit/catalog.py by scripts/render_catalog.py. Do not edit by hand. -->

| ID | Title | Severity | Check | Who checks | Type |
|---|---|---|---|---|---|
| VD-01 | Pie or donut chart | Low | D | scan.py | recommendation |
| VD-02 | Gauge without a target | Medium | D | scan.py | defect |
| VD-05 | KPI without comparison | High | J | agent | defect |
| VD-06 | Hard-coded hex colours | Low | D | scan.py | recommendation |
| VD-07 | Bar/column value axis not starting at zero | High | J | agent | defect |
| VD-08 | Mixed time frames or magnitudes on one page | Medium | J | agent | defect |
| VD-10 | Visual outside the page canvas | Medium | D | scan.py | defect |
| VD-16 | Titles state no message / unexplained acronyms | Medium | J | agent | defect |

### VD-01 Pie or donut chart

- **Severity:** Low. **Check:** D (scan.py). **Type:** recommendation.
- **Why:** Angles are hard to compare and the charts break down beyond a handful of categories. The type is deterministic, the category count is runtime.
- **How to verify:** `visualType` pieChart / donutChart.
- **Fix:** Prefer a sorted bar chart; keep pies to 2-5 categories.
- **Source:** <https://learn.microsoft.com/power-bi/visuals/power-bi-visualization-best-practices>

### VD-02 Gauge without a target

- **Severity:** Medium. **Check:** D (scan.py). **Type:** defect.
- **Why:** A gauge without a target has no reference point, so the reader cannot judge the value.
- **How to verify:** `gauge` visual with no `TargetValue` projection.
- **Fix:** Bind a target measure or replace with a card plus comparison.
- **Source:** <https://learn.microsoft.com/power-bi/visuals/power-bi-visualization-radial-gauge-charts>

### VD-05 KPI without comparison

- **Severity:** High. **Check:** J (agent). **Type:** defect.
- **Why:** A number without prior period, target or variance carries no message.
- **How to verify:** Check cards/KPIs for a comparison series or reference label.
- **Fix:** Add PY, target or variance.
- **Source:** <https://learn.microsoft.com/power-bi/create-reports/service-dashboards-design-tips>

### VD-06 Hard-coded hex colours

- **Severity:** Low. **Check:** D (scan.py). **Type:** recommendation.
- **Why:** Literal colours bypass the theme, so rebranding and accessibility fixes must be done visual by visual.
- **How to verify:** `'#RRGGBB'` literals in visual.json, compared with the resolved report theme (base + custom). Low when a literal is outside the theme palette; Info when every literal equals a theme colour (it still will not follow a theme change). Counted per page.
- **Fix:** Use theme colours (`ThemeDataColor`) or define the colour in the theme JSON.
- **Source:** <https://learn.microsoft.com/power-bi/create-reports/desktop-report-themes>

### VD-07 Bar/column value axis not starting at zero

- **Severity:** High. **Check:** J (agent). **Type:** defect.
- **Why:** Truncated bar axes exaggerate differences.
- **How to verify:** Check `valueAxis` start properties and rendered charts.
- **Fix:** Start bar axes at zero; use a line chart for small variations.
- **Source:** <https://learn.microsoft.com/power-bi/visuals/power-bi-visualization-best-practices>

### VD-08 Mixed time frames or magnitudes on one page

- **Severity:** Medium. **Check:** J (agent). **Type:** defect.
- **Why:** Comparing a YTD card with a monthly chart misleads.
- **How to verify:** Read titles and measure windows per page.
- **Fix:** Align windows or label them.
- **Source:** <https://www.ibcs.com/ibcs-standards-1-2/>

### VD-10 Visual outside the page canvas

- **Severity:** Medium. **Check:** D (scan.py). **Type:** defect.
- **Why:** Visuals beyond the page bounds are cut off or force scrolling.
- **How to verify:** `position.x + width` or `y + height` beyond the page size.
- **Fix:** Move or resize the visual, or change the page size deliberately.
- **Source:** <https://github.com/NatVanG/fab-inspector>

### VD-16 Titles state no message / unexplained acronyms

- **Severity:** Medium. **Check:** J (agent). **Type:** defect.
- **Why:** Titles that only name the measure leave interpretation to the reader.
- **How to verify:** Read titles.
- **Fix:** Write action titles; expand acronyms in tooltips or descriptions.
- **Source:** <https://learn.microsoft.com/power-bi/create-reports/service-dashboards-design-tips>

<!-- END GENERATED RULES -->
