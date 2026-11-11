# Model and report-to-model binding

Rules about the semantic model's structure (relationships, date tables, keys, data types, unused objects) and about whether the report still binds to it. Binding failures are the highest-value deterministic findings: no other local tool detects them offline.

Review order: run `scan.py`, read every BIND finding first (they can invalidate the rest of the audit for the affected pages), then the MOD findings, then the J rules below using `relationships.tmdl` and the table files.

## Rules

<!-- BEGIN GENERATED RULES -->

<!-- Generated from scripts/pbip_audit/catalog.py by scripts/render_catalog.py. Do not edit by hand. -->

| ID | Title | Severity | Check | Who checks | Type |
|---|---|---|---|---|---|
| BIND-01 | Report field references a model object that does not exist | Critical | D | scan.py | defect |
| BIND-02 | Thin report: model binding cannot be verified offline | Info | D | scan.py | recommendation |
| BIND-03 | Bookmark stores state for a model object that no longer exists | High | D | scan.py | defect |
| MOD-01 | Bidirectional relationship | Medium | D | scan.py | defect |
| MOD-02 | One-to-one relationship | Low | D | scan.py | recommendation |
| MOD-03 | Inactive relationship never activated with USERELATIONSHIP | Medium | D | scan.py | defect |
| MOD-04 | Time-intelligence DAX without a marked date table | High | D | scan.py | defect |
| MOD-05 | Auto date/time is enabled | Medium | D | scan.py | defect |
| MOD-06 | Date table is contiguous, covers full years and has no blanks | Medium | R | not offline | defect |
| MOD-07 | Foreign-key column is visible | Low | D | scan.py | recommendation |
| MOD-08 | Floating-point (double) data type | Low | D | scan.py | recommendation |
| MOD-09 | Implicit measures are not discouraged | Low | D | scan.py | recommendation |
| MOD-10 | Unused columns or measures | Low | D | scan.py | recommendation |
| MOD-11 | Single-attribute dimension | Low | J | agent | defect |
| MOD-12 | High-cardinality text keys or columns | Medium | R | not offline | defect |
| MOD-13 | Role-playing date tables with generic column names | Low | J | agent | defect |

### BIND-01 Report field references a model object that does not exist

- **Severity:** Critical. **Check:** D (scan.py). **Type:** defect.
- **Why:** A visual, filter or bookmark that points at a missing table, column, measure or hierarchy renders as an error (or silently drops a filter) for every viewer. No local tool checks this offline.
- **How to verify:** Index every `SourceRef.Entity` + `Property` in visual.json, page.json, report.json and bookmarks (resolving `Source` aliases through `From`) and look each one up in the TMDL tables, columns, measures, hierarchies and reportExtensions.json. Severity follows the location: Critical when the missing object is in a visual's query (`queryState`), a filter with a condition or any other place; Medium when every reference is only a stale leftover in a `sortDefinition`, a formatting selector (`visual.objects.*[].selector`) or a filter card without a condition, because the visual itself still has its fields.
- **Fix:** Rebind the field in Desktop (or edit the JSON) to the renamed object, or restore the object in the model.
- **Source:** <https://learn.microsoft.com/power-bi/developer/projects/projects-report>

### BIND-02 Thin report: model binding cannot be verified offline

- **Severity:** Info. **Check:** D (scan.py). **Type:** recommendation.
- **Why:** `definition.pbir` uses `byConnection`, so the semantic model is not in the project and report-to-model checks cannot run.
- **How to verify:** Read `datasetReference` in `definition.pbir`.
- **Fix:** Audit the model project separately, or point `byPath` at a local copy of the model when auditing.
- **Source:** <https://learn.microsoft.com/power-bi/developer/projects/projects-report>

### BIND-03 Bookmark stores state for a model object that no longer exists

- **Severity:** High. **Check:** D (scan.py). **Type:** defect.
- **Why:** Bookmarks snapshot visual query state. After a measure or column is renamed or deleted, applying the bookmark can restore a broken field list.
- **How to verify:** Model references inside `bookmarks/*.bookmark.json` that do not resolve against the TMDL. Medium instead of High when every stale reference of the bookmark is only in a sort definition, a formatting selector or a filter without a condition.
- **Fix:** Re-capture (update) the bookmark after fixing the page, or delete it if unused.
- **Source:** <https://learn.microsoft.com/power-bi/create-reports/desktop-bookmarks>

### MOD-01 Bidirectional relationship

- **Severity:** Medium. **Check:** D (scan.py). **Type:** defect.
- **Why:** Both-direction cross filtering creates ambiguous filter paths, slows queries and can give unexpected totals. It is justified mainly for bridge tables and some one-to-one cases.
- **How to verify:** `crossFilteringBehavior: bothDirections` in relationships.tmdl.
- **Fix:** Set the relationship to single direction; use `CROSSFILTER` inside the specific measures that need it.
- **Source:** <https://learn.microsoft.com/power-bi/guidance/relationships-bidirectional-filtering>

### MOD-02 One-to-one relationship

- **Severity:** Low. **Check:** D (scan.py). **Type:** recommendation.
- **Why:** One-to-one relationships usually mean two tables that should be merged; they also make filter direction harder to reason about.
- **How to verify:** `fromCardinality: one` and `toCardinality: one` on the same relationship.
- **Fix:** Merge the tables in Power Query, or document why they stay separate.
- **Source:** <https://learn.microsoft.com/power-bi/guidance/star-schema>

### MOD-03 Inactive relationship never activated with USERELATIONSHIP

- **Severity:** Medium. **Check:** D (scan.py). **Type:** defect.
- **Why:** An inactive relationship that no measure activates is dead weight and often a forgotten modelling mistake.
- **How to verify:** `isActive: false` with no `USERELATIONSHIP(...)` call in any DAX expression that names both columns.
- **Fix:** Delete the relationship, or add the measures that use it.
- **Source:** <https://learn.microsoft.com/power-bi/guidance/star-schema>

### MOD-04 Time-intelligence DAX without a marked date table

- **Severity:** High. **Check:** D (scan.py). **Type:** defect.
- **Why:** Functions such as SAMEPERIODLASTYEAR or DATESYTD require a contiguous date column. Without a marked date table they can return wrong results when the relationship is not on a date-typed column.
- **How to verify:** Any measure using a time-intelligence function while no table has `dataCategory: Time`, unless every date column it passes to those functions is joined by an active relationship between two dateTime columns.
- **Fix:** Mark the calendar table as a date table (Table tools > Mark as date table).
- **Source:** <https://learn.microsoft.com/power-bi/guidance/model-date-tables>

### MOD-05 Auto date/time is enabled

- **Severity:** Medium. **Check:** D (scan.py). **Type:** defect.
- **Why:** Auto date/time creates a hidden LocalDateTable per date column, inflating model size and producing inconsistent time intelligence.
- **How to verify:** `annotation __PBI_TimeIntelligenceEnabled = 1` in model.tmdl or `LocalDateTable_*` tables.
- **Fix:** Disable Auto date/time in the file options and use one shared, marked date table.
- **Source:** <https://learn.microsoft.com/power-bi/guidance/auto-date-time>

### MOD-06 Date table is contiguous, covers full years and has no blanks

- **Severity:** Medium. **Check:** R (not offline). **Type:** defect.
- **Why:** Time intelligence silently misbehaves on gaps; this depends on the data, not the definition.
- **How to verify:** Requires querying the data (DAX query or refresh).
- **Fix:** Generate the date table with CALENDAR over full years.
- **Source:** <https://learn.microsoft.com/power-bi/guidance/model-date-tables>

### MOD-07 Foreign-key column is visible

- **Severity:** Low. **Check:** D (scan.py). **Type:** recommendation.
- **Why:** Visible key columns invite users to slice by the fact-side key instead of the dimension attribute, which bypasses the dimension.
- **How to verify:** Columns used on the many side of a relationship without `isHidden`.
- **Fix:** Hide foreign-key columns in the fact table.
- **Source:** <https://learn.microsoft.com/power-bi/guidance/star-schema>

### MOD-08 Floating-point (double) data type

- **Severity:** Low. **Check:** D (scan.py). **Type:** recommendation.
- **Why:** Double can introduce rounding differences in sums; fixed decimal (`decimal`) or whole numbers are exact and compress better.
- **How to verify:** `dataType: double` on columns.
- **Fix:** Use Fixed decimal number for currency, whole number for counts.
- **Source:** <https://github.com/TabularEditor/BestPracticeRules>

### MOD-09 Implicit measures are not discouraged

- **Severity:** Low. **Check:** D (scan.py). **Type:** recommendation.
- **Why:** Without `discourageImplicitMeasures`, users drag raw numeric columns and get default sums that bypass business logic and confuse Copilot.
- **How to verify:** `discourageImplicitMeasures` missing from model.tmdl.
- **Fix:** Enable it (it is required for calculation groups anyway) and expose explicit measures.
- **Source:** <https://github.com/TabularEditor/BestPracticeRules>

### MOD-10 Unused columns or measures

- **Severity:** Low. **Check:** D (scan.py). **Type:** recommendation.
- **Why:** Objects referenced by no visual, filter, measure, relationship, sort or RLS rule cost memory and maintenance.
- **How to verify:** Join the report reference index with every DAX text (measures, calculated columns and tables, RLS, calculation items, format string expressions, KPIs and user-defined functions), relationship, sortByColumn and hierarchy level. Field parameter columns (`relatedColumnDetails groupByColumn`, `extendedProperty ParameterMetadata`) count as used, and so does every column of a table that a calculated table copies whole (`source = OtherTable`) or names in `sourceColumn: OtherTable[Column]`. Objects listed in an `--external-usage` file (used by other reports, Excel or paginated reports on the same model) count as used.
- **Fix:** Remove them after checking that no other report bound to this model uses them; record known external consumers in an external-usage file.
- **Source:** <https://learn.microsoft.com/power-bi/guidance/import-modeling-data-reduction>

### MOD-11 Single-attribute dimension

- **Severity:** Low. **Check:** J (agent). **Type:** defect.
- **Why:** A dimension with one attribute can usually be folded into the fact or another dimension.
- **How to verify:** Look for small tables with one visible column and judge whether they add value.
- **Fix:** Merge it, or document why it exists (e.g. a shared slicer table).
- **Source:** <https://learn.microsoft.com/power-bi/guidance/star-schema>

### MOD-12 High-cardinality text keys or columns

- **Severity:** Medium. **Check:** R (not offline). **Type:** defect.
- **Why:** Cardinality drives model size; it can only be measured with VertiPaq statistics.
- **How to verify:** Requires VertiPaq Analyzer or DMVs.
- **Fix:** Split, round or remove high-cardinality columns.
- **Source:** <https://learn.microsoft.com/power-bi/guidance/import-modeling-data-reduction>

### MOD-13 Role-playing date tables with generic column names

- **Severity:** Low. **Check:** J (agent). **Type:** defect.
- **Why:** Copies of the date table with identical column names make fields ambiguous in visuals and for Copilot.
- **How to verify:** Look for several date-like tables with the same column names.
- **Fix:** Prefix columns (`Ship Year`, `Order Year`) or use USERELATIONSHIP with one date table.
- **Source:** <https://learn.microsoft.com/power-bi/guidance/star-schema>

<!-- END GENERATED RULES -->
