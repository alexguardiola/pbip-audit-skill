# Mobile

Rules about the phone layout. `mobile.json` next to a visual.json means the visual is placed on the mobile canvas. Whether a mobile layout is needed at all depends on the audience, so MOB-01 is Info: ask before raising it.

## Rules

<!-- BEGIN GENERATED RULES -->

<!-- Generated from scripts/pbip_audit/catalog.py by scripts/render_catalog.py. Do not edit by hand. -->

| ID | Title | Severity | Check | Who checks | Type |
|---|---|---|---|---|---|
| MOB-01 | No page has a mobile layout | Info | D | scan.py | recommendation |
| MOB-02 | Mobile layout does not put KPIs and slicers first | Medium | J | agent | defect |
| MOB-03 | Table or matrix drill relies on header clicks | Low | J | agent | defect |

### MOB-01 No page has a mobile layout

- **Severity:** Info. **Check:** D (scan.py). **Type:** recommendation.
- **Why:** Phone users get the scaled desktop canvas, which is hard to read.
- **How to verify:** No `mobile.json` files in the report.
- **Fix:** Create a mobile layout for the pages that mobile users open.
- **Source:** <https://learn.microsoft.com/power-bi/create-reports/power-bi-create-mobile-optimized-report-mobile-layout-view>

### MOB-02 Mobile layout does not put KPIs and slicers first

- **Severity:** Medium. **Check:** J (agent). **Type:** defect.
- **Why:** Mobile readers scroll; the first screen should carry the headline.
- **How to verify:** Read `mobile.json` positions.
- **Fix:** Reorder the mobile layout.
- **Source:** <https://learn.microsoft.com/power-bi/create-reports/power-bi-create-mobile-optimized-report-mobile-layout-view>

### MOB-03 Table or matrix drill relies on header clicks

- **Severity:** Low. **Check:** J (agent). **Type:** defect.
- **Why:** Header interactions are hard to hit on touch screens.
- **How to verify:** Check matrices on mobile pages.
- **Fix:** Add explicit drill buttons or drillthrough.
- **Source:** <https://learn.microsoft.com/power-bi/create-reports/power-bi-create-mobile-optimized-report-mobile-layout-view>

<!-- END GENERATED RULES -->
