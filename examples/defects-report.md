# PBIP audit: Defects.pbip

Scanner 0.2.0 at 2026-11-10T15:21:57+00:00. Report format: PBIR; model format: TMDL; thin report: False.

Scanned 4 pages, 25 visuals, 4 tables, 10 measures, 4 relationships.
Theme: base `built-in default`, custom `Defects.Report/StaticResources/RegisteredResources/BrandTheme.json`.

## Executive summary

51 deterministic finding(s): 3 Critical, 10 High, 21 Medium, 15 Low, 2 Info. Overall score 70/100 (fair). Weakest pillars: Model and binding (14), Governance and AI readiness (40).

Fix first (Critical):

- **BIND-01#1** Report field references a model object that does not exist: Missing table: 'Missing'[Thing] is referenced in 1 place(s) but is not defined in the semantic model.
- **BIND-01#2** Report field references a model object that does not exist: Missing measure: 'Orders'[Ghost Measure] is referenced in 1 place(s) but is not defined in the semantic model.
- **GOV-09#1** Credential in M or shared expression: A password-like key/value pair appears in M source code.

These are scanner findings only. Each one should be confirmed by reading its evidence; judgement rules are not covered by this file.

## Score per pillar

| Pillar | Score | Critical | High | Medium | Low | Info |
|---|---|---|---|---|---|---|
| Model and binding | 14 | 2 | 2 | 2 | 8 | 0 |
| DAX | 86 | 0 | 0 | 3 | 2 | 0 |
| Performance | 95 | 0 | 0 | 1 | 1 | 0 |
| Governance and AI readiness | 40 | 1 | 3 | 1 | 1 | 0 |
| Visual design | 90 | 0 | 0 | 2 | 2 | 1 |
| Storytelling | 88 | 0 | 0 | 3 | 0 | 0 |
| Interaction | 52 | 0 | 2 | 7 | 0 | 0 |
| Accessibility | 61 | 0 | 3 | 2 | 1 | 0 |
| Mobile | 100 | 0 | 0 | 0 | 0 | 1 |
| **Overall** | **70** | 3 | 10 | 21 | 15 | 2 |

Formula: pillar score = max(0, 100 - sum of severity weights of its findings); weights Critical 25, High 10, Medium 4, Low 1, Info 0; a finding counts once however many locations it lists; false positives are excluded; overall = mean of the nine pillars. Use it to rank work, not to certify.

## Findings

### Critical (3)

#### Model and binding

##### BIND-01#1 Report field references a model object that does not exist

Missing table: 'Missing'[Thing] is referenced in 1 place(s) but is not defined in the semantic model.

Check: D. Confidence: high. Type: defect.

- `Defects.Report/definition/pages/page1/visuals/broken/visual.json:40` $.visual.query.queryState.Values.projections[1].field.Column

Fix: Rebind the field in Desktop (or edit the JSON) to the renamed object, or restore the object in the model. ([source](https://learn.microsoft.com/power-bi/developer/projects/projects-report))

##### BIND-01#2 Report field references a model object that does not exist

Missing measure: 'Orders'[Ghost Measure] is referenced in 1 place(s) but is not defined in the semantic model.

Check: D. Confidence: high. Type: defect.

- `Defects.Report/definition/pages/page1/visuals/broken/visual.json:26` $.visual.query.queryState.Values.projections[0].field.Measure

Fix: Rebind the field in Desktop (or edit the JSON) to the renamed object, or restore the object in the model. ([source](https://learn.microsoft.com/power-bi/developer/projects/projects-report))

#### Governance and AI readiness

##### GOV-09#1 Credential in M or shared expression

A password-like key/value pair appears in M source code.

Check: D. Confidence: high. Type: defect.

- `Defects.SemanticModel/definition/tables/Product.tmdl:31` partition Product

Fix: Remove the secret, rotate it and use gateway / data-source credentials. ([source](https://learn.microsoft.com/analysis-services/tmdl/tmdl-overview))

### High (10)

#### Model and binding

##### BIND-03#1 Bookmark stores state for a model object that no longer exists

Bookmark 'Old view' stores state for 1 model object(s) that no longer exist; applying it can break visuals.

Check: D. Confidence: medium. Type: defect.

- `Defects.Report/definition/bookmarks/bm1.bookmark.json:27` $.explorationState.sections.page1.visualContainers.card00.singleVisual.query.queryState.Values.projections[0].field.Measure Missing measure: 'Orders'[Deleted Measure]

Fix: Re-capture (update) the bookmark after fixing the page, or delete it if unused. ([source](https://learn.microsoft.com/power-bi/create-reports/desktop-bookmarks))

##### MOD-04#1 Time-intelligence DAX without a marked date table

1 measure(s) use time-intelligence functions but no table is marked as a date table (dataCategory: Time).

Check: D. Confidence: medium. Type: defect.

- `Defects.SemanticModel/definition/tables/Orders.tmdl:28` Revenue PY

Fix: Mark the calendar table as a date table (Table tools > Mark as date table). ([source](https://learn.microsoft.com/power-bi/guidance/model-date-tables))

#### Governance and AI readiness

##### GOV-14#1 Page or visual folder name ignored by Desktop

The page folder name is not word characters or hyphens, so Desktop ignores it.

Check: D. Confidence: high. Type: defect.

- `Defects.Report/definition/pages/bad page!`

Fix: Rename the folder to letters, digits, underscores or hyphens. ([source](https://learn.microsoft.com/power-bi/developer/projects/projects-report))

##### GOV-15#1 Unparseable JSON or TMDL

Invalid JSON: Expecting property name enclosed in double quotes: line 1 column 34 (char 33)

Check: D. Confidence: high. Type: defect.

- `Defects.Report/definition/pages/page2/visuals/corrupt/visual.json`

Fix: Fix the file (usually a merge conflict or manual edit). ([source](https://learn.microsoft.com/power-bi/developer/projects/projects-report))

##### GOV-15#2 Unparseable JSON or TMDL

1 TMDL line(s) were not recognised by the tolerant parser. They may be valid syntax this parser does not know, or real errors.

Check: D. Confidence: low. Type: defect.

- `Defects.SemanticModel/definition/tables/Product.tmdl:29` unrecognised TMDL line: %%% this line is not valid TMDL

Fix: Fix the file (usually a merge conflict or manual edit). ([source](https://learn.microsoft.com/power-bi/developer/projects/projects-report))

#### Interaction

##### IN-02#1 Hidden slicer in a sync group

Hidden slicer on 'Product'[Color] in sync group 'Hidden' filters page 'Page 1' invisibly.

Check: D. Confidence: medium. Type: defect.

- `Defects.Report/definition/pages/page1/visuals/slicerHidden/visual.json:42` $.isHidden

Fix: Show the slicer, or show the active selection in a title/card. ([source](https://learn.microsoft.com/power-bi/visuals/power-bi-visualization-slicers))

##### IN-03#1 Sync group mixes different fields

Sync group 'Mixed' mixes 2 different fields: 'Product'[Category] | 'Product'[Color].

Check: D. Confidence: high. Type: defect.

- `Defects.Report/definition/pages/page1/visuals/slicerCat/visual.json:36` $.visual.syncGroup page 'Page 1', field 'Product'[Category]
- `Defects.Report/definition/pages/page2/visuals/slicerColor/visual.json:36` $.visual.syncGroup page 'Duplicate of Page 1', field 'Product'[Color]

Fix: Give each field its own sync group. ([source](https://learn.microsoft.com/power-bi/visuals/power-bi-visualization-slicers))

#### Accessibility

##### A11Y-01#1 Visuals without alt text

Page 'Page 1': 14 of 14 non-decorative visuals have no alt text.

Check: D. Confidence: high. Type: defect.

- `Defects.Report/definition/pages/page1/visuals/broken/visual.json:13` $.visual.visualType card
- `Defects.Report/definition/pages/page1/visuals/card00/visual.json:13` $.visual.visualType card
- `Defects.Report/definition/pages/page1/visuals/card01/visual.json:13` $.visual.visualType card
- `Defects.Report/definition/pages/page1/visuals/card02/visual.json:13` $.visual.visualType card
- `Defects.Report/definition/pages/page1/visuals/card03/visual.json:13` $.visual.visualType card
- `Defects.Report/definition/pages/page1/visuals/card04/visual.json:13` $.visual.visualType card
- `Defects.Report/definition/pages/page1/visuals/card05/visual.json:13` $.visual.visualType card
- `Defects.Report/definition/pages/page1/visuals/card06/visual.json:13` $.visual.visualType card
- `Defects.Report/definition/pages/page1/visuals/card07/visual.json:13` $.visual.visualType card
- `Defects.Report/definition/pages/page1/visuals/card08/visual.json:13` $.visual.visualType card
- ... and 4 more

Fix: Add alt text that states the insight, or bind it to a measure for dynamic text. ([source](https://learn.microsoft.com/power-bi/create-reports/desktop-accessibility-creating-reports))

##### A11Y-05#1 Insufficient text or graphics contrast

The report theme sets 1 text colour(s) below the WCAG contrast minimum against the theme background.

Check: D. Confidence: high. Type: defect.

- `Defects.Report/StaticResources/RegisteredResources/BrandTheme.json:13` $.foreground foreground #9A9A9A on background #FFFFFF = 2.81:1

Fix: Adjust the theme palette or the visual's font/background colours. ([source](https://www.w3.org/TR/WCAG22/))

##### A11Y-05#3 Insufficient text or graphics contrast

Page 'Duplicate of Page 1': 1 text colour(s) fall below the WCAG contrast minimum against every plausible background.

Check: D. Confidence: medium. Type: defect.

- `Defects.Report/definition/pages/page2/visuals/pulse/visual.json:54` $.visual.visualContainerObjects.title[0].properties.fontColor card: text #FFFFFF (theme) on #FFFFFF = 1.00:1, needs 4.5:1

Fix: Adjust the theme palette or the visual's font/background colours. ([source](https://www.w3.org/TR/WCAG22/))

### Medium (21)

#### Model and binding

##### MOD-01#1 Bidirectional relationship

Relationship Orders.ProductKey -> Product.ProductKey filters in both directions.

Check: D. Confidence: high. Type: defect.

- `Defects.SemanticModel/definition/relationships.tmdl:10` crossFilteringBehavior: bothDirections

Fix: Set the relationship to single direction; use `CROSSFILTER` inside the specific measures that need it. ([source](https://learn.microsoft.com/power-bi/guidance/relationships-bidirectional-filtering))

##### MOD-03#1 Inactive relationship never activated with USERELATIONSHIP

Inactive relationship Orders.ShipDate -> Calendar.Date is not activated by any USERELATIONSHIP call.

Check: D. Confidence: medium. Type: defect.

- `Defects.SemanticModel/definition/relationships.tmdl:5` isActive: false

Fix: Delete the relationship, or add the measures that use it. ([source](https://learn.microsoft.com/power-bi/guidance/star-schema))

#### DAX

##### DAX-01#1 Division operator instead of DIVIDE

Measure 'Avg Price' uses the / operator with a non-constant denominator.

Check: D. Confidence: medium. Type: defect.

- `Defects.SemanticModel/definition/tables/Orders.tmdl:10` Avg Price

Fix: Use `DIVIDE(numerator, denominator)`. ([source](https://learn.microsoft.com/dax/best-practices/dax-divide-function-operator))

##### DAX-03#1 IFERROR / ISERROR

A measure expression uses IFERROR/ISERROR.

Check: D. Confidence: high. Type: defect.

- `Defects.SemanticModel/definition/tables/Orders.tmdl:14`

Fix: Use DIVIDE, defensive conditions, or fix the data. ([source](https://learn.microsoft.com/dax/best-practices/dax-error-functions))

##### DAX-07#1 Visible measure without a format string

Table 'Orders' has 1 visible measure(s) without a format string: Revenue.

Check: D. Confidence: medium. Type: defect.

- `Defects.SemanticModel/definition/tables/Orders.tmdl:3` Revenue

Fix: Set a format string on every visible measure. ([source](https://github.com/TabularEditor/BestPracticeRules))

#### Performance

##### PERF-01#1 Too many data visuals on one page

Page 'Page 1' has 16 data-bound visuals (threshold 12).

Check: D. Confidence: high. Type: defect.

- `Defects.Report/definition/pages/page1/page.json`
- ... and 15 more

Fix: Split the page, use a multi-row card or a small multiple, or move detail to drillthrough. ([source](https://learn.microsoft.com/power-bi/guidance/power-bi-optimization))

#### Governance and AI readiness

##### GOV-01#1 Visible measure without a description

Table 'Orders' has 1 visible measure(s) without a description: Revenue.

Check: D. Confidence: high. Type: defect.

- `Defects.SemanticModel/definition/tables/Orders.tmdl:3` Revenue

Fix: Add a one-sentence description that says what the measure counts and any window or exclusion. ([source](https://learn.microsoft.com/power-bi/create-reports/copilot-prepare-data-ai))

#### Visual design

##### VD-02#1 Gauge without a target

Gauge on page 'Duplicate of Page 1' has no target value.

Check: D. Confidence: high. Type: defect.

- `Defects.Report/definition/pages/page2/visuals/gauge/visual.json:13` $.visual.visualType

Fix: Bind a target measure or replace with a card plus comparison. ([source](https://learn.microsoft.com/power-bi/visuals/power-bi-visualization-radial-gauge-charts))

##### VD-10#1 Visual outside the page canvas

A card on page 'Page 1' extends outside the 1280x720 canvas (x=1200, y=400, w=200, h=100).

Check: D. Confidence: high. Type: defect.

- `Defects.Report/definition/pages/page1/visuals/windowCard/visual.json:4` $.position

Fix: Move or resize the visual, or change the page size deliberately. ([source](https://github.com/NatVanG/fab-inspector))

#### Storytelling

##### ST-01#1 Default page names

Page 'Page 1' has a default name.

Check: D. Confidence: high. Type: defect.

- `Defects.Report/definition/pages/page1/page.json:4` $.displayName

Fix: Name pages after the question they answer. ([source](https://learn.microsoft.com/power-bi/create-reports/service-dashboards-design-tips))

##### ST-01#2 Default page names

Page 'Duplicate of Page 1' has a default name.

Check: D. Confidence: high. Type: defect.

- `Defects.Report/definition/pages/page2/page.json:4` $.displayName

Fix: Name pages after the question they answer. ([source](https://learn.microsoft.com/power-bi/create-reports/service-dashboards-design-tips))

##### ST-05#1 Hidden page that is not a drillthrough, tooltip or navigation target

Page 'Scratch' is hidden, is not a drillthrough or tooltip page, and no button or bookmark references it.

Check: D. Confidence: high. Type: defect.

- `Defects.Report/definition/pages/scratch/page.json:7` $.visibility

Fix: Delete it or wire it to a button/bookmark. ([source](https://learn.microsoft.com/power-bi/create-reports/desktop-drillthrough))

#### Interaction

##### IN-01#1 Hidden filter (may carry business logic)

1 filter(s) are hidden from the filter pane; confirm none changes the meaning of the numbers.

Check: D. Confidence: medium. Type: recommendation.

- `Defects.Report/definition/pages/page1/visuals/slicerCat/visual.json:57` $.filterConfig.filters[0].isHiddenInViewMode visual on page 'Page 1': 'Product'[Category]

Fix: Lock instead of hide, or state the scope in the title / description. ([source](https://learn.microsoft.com/power-bi/create-reports/power-bi-report-filter))

##### IN-04#1 Same field sliced in different sync groups

Field 'Calendar'[Year] is sliced in 2 different sync groups: YearA, YearB.

Check: D. Confidence: medium. Type: defect.

- `Defects.Report/definition/pages/page1/visuals/slicerYearA/visual.json:36` $.visual.syncGroup group 'YearA', page 'Page 1'
- `Defects.Report/definition/pages/page2/visuals/slicerYearB/visual.json:36` $.visual.syncGroup group 'YearB', page 'Duplicate of Page 1'

Fix: Use one sync group per field unless independence is intended. ([source](https://learn.microsoft.com/power-bi/visuals/power-bi-visualization-slicers))

##### IN-04#2 Same field sliced in different sync groups

Field 'Product'[Color] is sliced in 2 different sync groups: Hidden, Mixed.

Check: D. Confidence: medium. Type: defect.

- `Defects.Report/definition/pages/page1/visuals/slicerHidden/visual.json:36` $.visual.syncGroup group 'Hidden', page 'Page 1'
- `Defects.Report/definition/pages/page2/visuals/slicerColor/visual.json:36` $.visual.syncGroup group 'Mixed', page 'Duplicate of Page 1'

Fix: Use one sync group per field unless independence is intended. ([source](https://learn.microsoft.com/power-bi/visuals/power-bi-visualization-slicers))

##### IN-05#1 Rolling-window measure shown without a window label

Visual on page 'Page 1' shows [Recent Revenue], which builds its own date window from TODAY() (direct), but neither the title ('Revenue'), the field names nor the measure description say so.

Check: D. Confidence: medium. Type: defect.

- `Defects.Report/definition/pages/page1/visuals/windowCard/visual.json:26` $.visual.query.queryState.Values.projections[0]
- `Defects.SemanticModel/definition/tables/Orders.tmdl:32` Recent Revenue

Fix: Say the window in the title ("Revenue, last 3 closed months") or in a subtitle. ([source](https://learn.microsoft.com/power-bi/guidance/model-date-tables))

##### IN-07#1 Drillthrough page without a back button

Drillthrough page 'Category Drill' has no Back button.

Check: D. Confidence: high. Type: defect.

- `Defects.Report/definition/pages/drill/page.json:9` $.pageBinding

Fix: Add a Back button (Insert > Buttons > Back). ([source](https://learn.microsoft.com/power-bi/create-reports/desktop-drillthrough))

##### IN-13#1 Year slicer exposes future years

Slicer on 'Calendar'[Year] (page 'Page 1') has no filter limiting years, while the date table extends to 2031.

Check: D. Confidence: medium. Type: defect.

- `Defects.Report/definition/pages/page1/visuals/slicerYearA/visual.json:26` $.visual.query.queryState.Values.projections[0].field.Column
- `Defects.SemanticModel/definition/tables/Calendar.tmdl:13` date table definition

Fix: Add a visual-level filter (e.g. an `Is Past or Current Year` flag) or trim the slicer values. ([source](https://learn.microsoft.com/power-bi/guidance/model-date-tables))

##### IN-13#2 Year slicer exposes future years

Slicer on 'Calendar'[Year] (page 'Duplicate of Page 1') has no filter limiting years, while the date table extends to 2031.

Check: D. Confidence: medium. Type: defect.

- `Defects.Report/definition/pages/page2/visuals/slicerYearB/visual.json:26` $.visual.query.queryState.Values.projections[0].field.Column
- `Defects.SemanticModel/definition/tables/Calendar.tmdl:13` date table definition

Fix: Add a visual-level filter (e.g. an `Is Past or Current Year` flag) or trim the slicer values. ([source](https://learn.microsoft.com/power-bi/guidance/model-date-tables))

#### Accessibility

##### A11Y-05#2 Insufficient text or graphics contrast

2 of the first 8 theme data colours have less than 3:1 contrast with the background (WCAG 1.4.11, graphical objects).

Check: D. Confidence: medium. Type: defect.

- `Defects.Report/StaticResources/RegisteredResources/BrandTheme.json:7` $.dataColors[3] series colour 4 #FFE600 on #FFFFFF = 1.27:1
- `Defects.Report/StaticResources/RegisteredResources/BrandTheme.json:10` $.dataColors[6] series colour 7 #17BECF on #FFFFFF = 2.26:1

Fix: Adjust the theme palette or the visual's font/background colours. ([source](https://www.w3.org/TR/WCAG22/))

##### A11Y-07#1 Series colours confusable under colour-vision deficiency

2 pair(s) among the first 8 theme data colours are hard to tell apart with red-green colour-vision deficiency.

Check: D. Confidence: medium. Type: defect.

- `Defects.Report/StaticResources/RegisteredResources/BrandTheme.json:5` $.dataColors[1] series 1 #D62728 vs series 2 #2CA02C: delta E 7.3 under deuteranopia (normal vision 120)
- `Defects.Report/StaticResources/RegisteredResources/BrandTheme.json:8` $.dataColors[4] series 3 #1F77B4 vs series 5 #9467BD: delta E 5.3 under protanopia (normal vision 38)

Fix: Replace one colour of each pair (vary lightness, not only hue), or add markers, patterns or direct labels. ([source](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html))

### Low (15)

#### Model and binding

##### MOD-02#1 One-to-one relationship

Relationship Product.ProductKey -> Product Extra.ProductKey is one-to-one.

Check: D. Confidence: high. Type: recommendation.

- `Defects.SemanticModel/definition/relationships.tmdl:15`

Fix: Merge the tables in Power Query, or document why they stay separate. ([source](https://learn.microsoft.com/power-bi/guidance/star-schema))

##### MOD-05#1 Auto date/time is enabled

The Auto date/time option is on (model annotation), although no LocalDateTable table exists yet; new date columns will get one.

Check: D. Confidence: high. Type: defect.

- `Defects.SemanticModel/definition/model.tmdl:4` __PBI_TimeIntelligenceEnabled = 1

Fix: Disable Auto date/time in the file options and use one shared, marked date table. ([source](https://learn.microsoft.com/power-bi/guidance/auto-date-time))

##### MOD-07#1 Foreign-key column is visible

Table 'Orders' has 1 visible foreign-key column(s): OrderDate.

Check: D. Confidence: high. Type: recommendation.

- `Defects.SemanticModel/definition/tables/Orders.tmdl:49` OrderDate

Fix: Hide foreign-key columns in the fact table. ([source](https://learn.microsoft.com/power-bi/guidance/star-schema))

##### MOD-08#1 Floating-point (double) data type

Table 'Product' has 1 double (floating-point) column(s): Weight.

Check: D. Confidence: high. Type: recommendation.

- `Defects.SemanticModel/definition/tables/Product.tmdl:19` Weight

Fix: Use Fixed decimal number for currency, whole number for counts. ([source](https://github.com/TabularEditor/BestPracticeRules))

##### MOD-09#1 Implicit measures are not discouraged

model.tmdl does not set discourageImplicitMeasures.

Check: D. Confidence: high. Type: recommendation.

- `Defects.SemanticModel/definition/model.tmdl:1`

Fix: Enable it (it is required for calculation groups anyway) and expose explicit measures. ([source](https://github.com/TabularEditor/BestPracticeRules))

##### MOD-10#1 Unused columns or measures

Table 'Orders' has 1 object(s) not referenced by this report, any DAX, relationship, sort-by or hierarchy: measure Orphan Measure. Other reports, Excel or paginated reports bound to the same model may use them; pass --external-usage to allowlist those.

Check: D. Confidence: medium. Type: recommendation.

- `Defects.SemanticModel/definition/tables/Orders.tmdl:46` measure Orphan Measure

Fix: Remove them after checking that no other report bound to this model uses them; record known external consumers in an external-usage file. ([source](https://learn.microsoft.com/power-bi/guidance/import-modeling-data-reduction))

##### MOD-10#2 Unused columns or measures

Table 'Product' has 2 object(s) not referenced by this report, any DAX, relationship, sort-by or hierarchy: column Weight, column Unused Attr. Other reports, Excel or paginated reports bound to the same model may use them; pass --external-usage to allowlist those.

Check: D. Confidence: medium. Type: recommendation.

- `Defects.SemanticModel/definition/tables/Product.tmdl:19` column Weight
- `Defects.SemanticModel/definition/tables/Product.tmdl:24` column Unused Attr

Fix: Remove them after checking that no other report bound to this model uses them; record known external consumers in an external-usage file. ([source](https://learn.microsoft.com/power-bi/guidance/import-modeling-data-reduction))

##### MOD-10#3 Unused columns or measures

Table 'Product Extra' has 1 object(s) not referenced by this report, any DAX, relationship, sort-by or hierarchy: column Notes. Other reports, Excel or paginated reports bound to the same model may use them; pass --external-usage to allowlist those.

Check: D. Confidence: medium. Type: recommendation.

- `Defects.SemanticModel/definition/tables/Product Extra.tmdl:9` column Notes

Fix: Remove them after checking that no other report bound to this model uses them; record known external consumers in an external-usage file. ([source](https://learn.microsoft.com/power-bi/guidance/import-modeling-data-reduction))

#### DAX

##### DAX-04#1 BLANK converted to zero

Table 'Orders' has 1 measure(s) that turn BLANK into 0 via DIVIDE(..., ..., 0): Margin Pct.

Check: D. Confidence: medium. Type: recommendation.

- `Defects.SemanticModel/definition/tables/Orders.tmdl:18` Margin Pct

Fix: Return BLANK, or apply the zero only in the visual (show items with no data). ([source](https://learn.microsoft.com/dax/best-practices/dax-avoid-converting-blank))

##### DAX-08#1 TODO / FIXME left in DAX

A measure expression contains a TODO/FIXME/HACK marker.

Check: D. Confidence: high. Type: defect.

- `Defects.SemanticModel/definition/tables/Orders.tmdl:22`

Fix: Resolve or move the note to the issue tracker. ([source](https://github.com/TabularEditor/BestPracticeRules))

#### Performance

##### PERF-02#1 Too many fields in one visual

A tableEx on page 'Duplicate of Page 1' has 21 fields (threshold 20).

Check: D. Confidence: high. Type: defect.

- `Defects.Report/definition/pages/page2/visuals/wideTable/visual.json:15` $.visual.query.queryState
- ... and 20 more

Fix: Split the visual or use drillthrough for detail. ([source](https://github.com/NatVanG/fab-inspector))

#### Governance and AI readiness

##### GOV-02#1 Description longer than 200 characters

1 description(s) are longer than 200 characters.

Check: D. Confidence: high. Type: defect.

- `Defects.SemanticModel/definition/tables/Orders.tmdl:6` Units (251 chars)

Fix: Keep the first sentence self-contained; move detail to documentation. ([source](https://learn.microsoft.com/power-bi/create-reports/copilot-semantic-models))

#### Visual design

##### VD-01#1 Pie or donut chart

Page 'Duplicate of Page 1' uses a pieChart; check the number of categories.

Check: D. Confidence: medium. Type: recommendation.

- `Defects.Report/definition/pages/page2/visuals/pie/visual.json:13` $.visual.visualType

Fix: Prefer a sorted bar chart; keep pies to 2-5 categories. ([source](https://learn.microsoft.com/power-bi/visuals/power-bi-visualization-best-practices))

##### VD-06#1 Hard-coded hex colours

Page 'Page 1': 1 visual(s) use 1 hard-coded colour literal(s) that are not in the report theme.

Check: D. Confidence: high. Type: recommendation.

- `Defects.Report/definition/pages/page1/visuals/card00/visual.json:67` $.visual.objects.labels[0].properties.color.solid.color.expr.Literal.Value 1 off-theme literal(s): #FF0000

Fix: Use theme colours (`ThemeDataColor`) or define the colour in the theme JSON. ([source](https://learn.microsoft.com/power-bi/create-reports/desktop-report-themes))

#### Accessibility

##### A11Y-04#1 Tab order does not follow reading order

Page 'Page 1': tab order disagrees with reading order for 56% of visual pairs (tolerance 40%, row band 40px).

Check: D. Confidence: medium. Type: recommendation.

- `Defects.Report/definition/pages/page1/visuals/card11/visual.json:10` $.position.tabOrder first in tab order: card at x=950, y=260

Fix: Set the tab order in the Selection pane. ([source](https://learn.microsoft.com/power-bi/create-reports/desktop-accessibility-creating-reports))

### Info (2)

#### Visual design

##### VD-06#2 Hard-coded hex colours

Page 'Duplicate of Page 1': 1 visual(s) hard-code 1 colour literal(s) that equal theme colours; they look right today but will not follow a theme change.

Check: D. Confidence: high. Type: recommendation.

- `Defects.Report/definition/pages/page2/visuals/pulse/visual.json:92` $.visual.objects.labels[0].properties.color.solid.color.expr.Literal.Value 1 literal(s) equal to theme colours

Fix: Use theme colours (`ThemeDataColor`) or define the colour in the theme JSON. ([source](https://learn.microsoft.com/power-bi/create-reports/desktop-report-themes))

#### Mobile

##### MOB-01#1 No page has a mobile layout

No visual has a mobile layout (no mobile.json files).

Check: D. Confidence: high. Type: recommendation.

- `Defects.Report/definition/pages`

Fix: Create a mobile layout for the pages that mobile users open. ([source](https://learn.microsoft.com/power-bi/create-reports/power-bi-create-mobile-optimized-report-mobile-layout-view))

## Not assessable offline

These runtime (R) rules need the Power BI Service, a running model or usage data. They were not checked:

- **MOD-06** Date table is contiguous, covers full years and has no blanks: Requires runtime or Service data; not assessable offline.
- **MOD-12** High-cardinality text keys or columns: Requires runtime or Service data; not assessable offline.
- **PERF-04** Large fact table without incremental refresh: Requires runtime or Service data; not assessable offline.
- **PERF-05** Model size, column cardinality, visual query timings: Requires runtime or Service data; not assessable offline.
- **GOV-12** Sensitivity label, endorsement, Copilot approval, Prep data for AI: Requires runtime or Service data; not assessable offline.

## Scanner notes

- base theme 'CY24SU10' not found in StaticResources; using the built-in default palette

