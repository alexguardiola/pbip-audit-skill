# Interaction integrity

Rules about slicers, sync groups, filters, drillthrough, bookmarks and visual interactions. These are the defects that make numbers silently wrong for a reader, and most are invisible in Desktop until someone clicks the right combination. Sync groups (IN-03, IN-04) and unlabelled rolling windows (IN-05) are the clearest examples: both are detectable from files alone.

IN-05 is a heuristic. It pairs a DAX pattern (TODAY/NOW plus REMOVEFILTERS/ALL on the date table, or DATESBETWEEN/DATESINPERIOD) with the absence of window words in the title, field display name and measure name. Confirm by reading the measure.

## Rules

<!-- BEGIN GENERATED RULES -->

<!-- Generated from scripts/pbip_audit/catalog.py by scripts/render_catalog.py. Do not edit by hand. -->

| ID | Title | Severity | Check | Who checks | Type |
|---|---|---|---|---|---|
| IN-01 | Hidden filter (may carry business logic) | Medium | D | scan.py | recommendation |
| IN-02 | Hidden slicer in a sync group | High | D | scan.py | defect |
| IN-03 | Sync group mixes different fields | High | D | scan.py | defect |
| IN-04 | Same field sliced in different sync groups | Medium | D | scan.py | defect |
| IN-05 | Rolling-window measure shown without a window label | Medium | D | scan.py | defect |
| IN-06 | KPI cards cross-filtered by detail visuals | Medium | J | agent | defect |
| IN-07 | Drillthrough page without a back button | Medium | D | scan.py | defect |
| IN-08 | Tooltip page carries unique information | Medium | J | agent | defect |
| IN-10 | Navigation bookmarks capture data | Medium | J | agent | defect |
| IN-13 | Year slicer exposes future years | Medium | D | scan.py | defect |

### IN-01 Hidden filter (may carry business logic)

- **Severity:** Medium. **Check:** D (scan.py). **Type:** recommendation.
- **Why:** Filters hidden from the filter pane change numbers without the reader knowing. Often legitimate (scope), so confirm intent.
- **How to verify:** `isHiddenInViewMode: true` on a report, page or visual filter.
- **Fix:** Lock instead of hide, or state the scope in the title / description.
- **Source:** <https://learn.microsoft.com/power-bi/create-reports/power-bi-report-filter>

### IN-02 Hidden slicer in a sync group

- **Severity:** High. **Check:** D (scan.py). **Type:** defect.
- **Why:** A hidden synced slicer filters the page invisibly; the reader sees the effect but not the control.
- **How to verify:** Slicer with `isHidden: true` and a `syncGroup`, with no visible slicer on the same field on that page.
- **Fix:** Show the slicer, or show the active selection in a title/card.
- **Source:** <https://learn.microsoft.com/power-bi/visuals/power-bi-visualization-slicers>

### IN-03 Sync group mixes different fields

- **Severity:** High. **Check:** D (scan.py). **Type:** defect.
- **Why:** Slicers on different fields sharing one sync group push selections onto the wrong field, silently filtering the wrong dimension.
- **How to verify:** `visual.syncGroup.groupName` shared by slicers bound to different fields.
- **Fix:** Give each field its own sync group.
- **Source:** <https://learn.microsoft.com/power-bi/visuals/power-bi-visualization-slicers>

### IN-04 Same field sliced in different sync groups

- **Severity:** Medium. **Check:** D (scan.py). **Type:** defect.
- **Why:** Slicers on the same field across pages that are in different sync groups keep separate selections, so pages disagree.
- **How to verify:** One field bound to slicers whose `syncGroup.groupName` differ.
- **Fix:** Use one sync group per field unless independence is intended.
- **Source:** <https://learn.microsoft.com/power-bi/visuals/power-bi-visualization-slicers>

### IN-05 Rolling-window measure shown without a window label

- **Severity:** Medium. **Check:** D (scan.py). **Type:** defect.
- **Why:** A measure that rebuilds its own date window from TODAY() and removes date filters ignores the date slicer. If the visual title does not say so, readers assume it follows the slicer. Heuristic.
- **How to verify:** Measure with TODAY/NOW plus REMOVEFILTERS/ALL on a date table (or DATESBETWEEN/DATESINPERIOD), bound in a visual whose title, display name, measure name and measure description contain no window words (last N, rolling, trailing, YTD, 12M, L3M, R12...).
- **Fix:** Say the window in the title ("Revenue, last 3 closed months") or in a subtitle.
- **Source:** <https://learn.microsoft.com/power-bi/guidance/model-date-tables>

### IN-06 KPI cards cross-filtered by detail visuals

- **Severity:** Medium. **Check:** J (agent). **Type:** defect.
- **Why:** Unreviewed default interactions make headline KPIs change when a detail visual is clicked.
- **How to verify:** Read `visualInteractions` in page.json.
- **Fix:** Set interactions to None where KPIs must stay stable.
- **Source:** <https://learn.microsoft.com/power-bi/create-reports/service-reports-visual-interactions>

### IN-07 Drillthrough page without a back button

- **Severity:** Medium. **Check:** D (scan.py). **Type:** defect.
- **Why:** Users land on the drillthrough page and cannot return without knowing the Ctrl/Alt shortcut.
- **How to verify:** `pageBinding.type: Drillthrough` page with no actionButton of type Back.
- **Fix:** Add a Back button (Insert > Buttons > Back).
- **Source:** <https://learn.microsoft.com/power-bi/create-reports/desktop-drillthrough>

### IN-08 Tooltip page carries unique information

- **Severity:** Medium. **Check:** J (agent). **Type:** defect.
- **Why:** Information only available in a tooltip is invisible on touch and to keyboard users.
- **How to verify:** Compare tooltip page content with the host pages.
- **Fix:** Surface key figures on the page itself.
- **Source:** <https://learn.microsoft.com/power-bi/create-reports/desktop-tooltips>

### IN-10 Navigation bookmarks capture data

- **Severity:** Medium. **Check:** J (agent). **Type:** defect.
- **Why:** Bookmarks used as navigation that also capture data reset the reader's filters.
- **How to verify:** Bookmark `options` without `suppressData` used by navigation buttons.
- **Fix:** Untick Data on navigation bookmarks.
- **Source:** <https://learn.microsoft.com/power-bi/create-reports/desktop-bookmarks>

### IN-13 Year slicer exposes future years

- **Severity:** Medium. **Check:** D (scan.py). **Type:** defect.
- **Why:** When the date table extends past the current year (for forecasts), a year slicer lists empty future years and users pick them by mistake.
- **How to verify:** Slicer on a year column of a date table whose definition reaches beyond the current year, with no visual, page or report filter on the date table.
- **Fix:** Add a visual-level filter (e.g. an `Is Past or Current Year` flag) or trim the slicer values.
- **Source:** <https://learn.microsoft.com/power-bi/guidance/model-date-tables>

<!-- END GENERATED RULES -->
