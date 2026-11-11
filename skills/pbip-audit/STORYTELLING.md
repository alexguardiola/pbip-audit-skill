# Storytelling

Rules about whether pages answer a question in a sensible order. Deterministic checks catch the obvious signs of an unfinished report (default page names, unreachable hidden pages). The rest is judgement: build a page digest (page name, visual types, titles, positions, bound measures) and judge the narrative from it, citing visual.json files as evidence.

## Rules

<!-- BEGIN GENERATED RULES -->

<!-- Generated from scripts/pbip_audit/catalog.py by scripts/render_catalog.py. Do not edit by hand. -->

| ID | Title | Severity | Check | Who checks | Type |
|---|---|---|---|---|---|
| ST-01 | Default page names | Medium | D | scan.py | defect |
| ST-02 | Primary KPI not in the top-left reading position | Medium | J | agent | defect |
| ST-05 | Hidden page that is not a drillthrough, tooltip or navigation target | Medium | D | scan.py | defect |
| ST-06 | Page does not state the question it answers | Low | J | agent | defect |
| ST-07 | Chart type does not fit the analytical question | Medium | J | agent | defect |

### ST-01 Default page names

- **Severity:** Medium. **Check:** D (scan.py). **Type:** defect.
- **Why:** `Page 1` or `Duplicate of ...` tells the reader nothing and shows an unfinished report.
- **How to verify:** Page `displayName` matching default patterns (configurable).
- **Fix:** Name pages after the question they answer.
- **Source:** <https://learn.microsoft.com/power-bi/create-reports/service-dashboards-design-tips>

### ST-02 Primary KPI not in the top-left reading position

- **Severity:** Medium. **Check:** J (agent). **Type:** defect.
- **Why:** Readers scan top-left first.
- **How to verify:** Use the page digest (positions + visual types).
- **Fix:** Move headline KPIs to the top-left band.
- **Source:** <https://learn.microsoft.com/power-bi/create-reports/service-dashboards-design-tips>

### ST-05 Hidden page that is not a drillthrough, tooltip or navigation target

- **Severity:** Medium. **Check:** D (scan.py). **Type:** defect.
- **Why:** A hidden page nobody can reach is dead content or a forgotten draft.
- **How to verify:** `visibility: HiddenInViewMode` without `pageBinding`, tooltip type, or any reference to the page name in visuals/bookmarks.
- **Fix:** Delete it or wire it to a button/bookmark.
- **Source:** <https://learn.microsoft.com/power-bi/create-reports/desktop-drillthrough>

### ST-06 Page does not state the question it answers

- **Severity:** Low. **Check:** J (agent). **Type:** defect.
- **Why:** Pages without a clear question become data dumps.
- **How to verify:** Read page names, titles and text boxes.
- **Fix:** Add a page title or subtitle stating the question.
- **Source:** <https://learn.microsoft.com/power-bi/create-reports/service-dashboards-design-tips>

### ST-07 Chart type does not fit the analytical question

- **Severity:** Medium. **Check:** J (agent). **Type:** defect.
- **Why:** Trend questions need time on the x-axis, composition questions need part-to-whole, and so on.
- **How to verify:** Compare each visual type with the question it serves.
- **Fix:** Change the visual type.
- **Source:** <https://learn.microsoft.com/power-bi/visuals/power-bi-visualization-best-practices>

<!-- END GENERATED RULES -->
