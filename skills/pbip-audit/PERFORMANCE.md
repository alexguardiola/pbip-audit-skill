# Performance

Offline you can only see the shape of the work (visuals per page, fields per visual, storage modes, refresh policies). Real timings and model size need Performance Analyzer, VertiPaq Analyzer or the Service, so those rules are R and are listed as not assessable offline. Thresholds are configurable (`--max-visuals`, `--max-fields`); there is no official Microsoft number for visuals per page.

## Rules

<!-- BEGIN GENERATED RULES -->

<!-- Generated from scripts/pbip_audit/catalog.py by scripts/render_catalog.py. Do not edit by hand. -->

| ID | Title | Severity | Check | Who checks | Type |
|---|---|---|---|---|---|
| PERF-01 | Too many data visuals on one page | Medium | D | scan.py | defect |
| PERF-02 | Too many fields in one visual | Low | D | scan.py | defect |
| PERF-03 | DirectQuery page with many single-value cards | Medium | J | agent | defect |
| PERF-04 | Large fact table without incremental refresh | Medium | R | not offline | defect |
| PERF-05 | Model size, column cardinality, visual query timings | Info | R | not offline | defect |

### PERF-01 Too many data visuals on one page

- **Severity:** Medium. **Check:** D (scan.py). **Type:** defect.
- **Why:** Each data visual sends at least one query; busy pages render slowly and overload the reader. There is no official limit; the default threshold is 12 data-bound visuals.
- **How to verify:** Count visible, data-bound visuals per page (`--max-visuals`); visuals inside a hidden group are hidden.
- **Fix:** Split the page, use a multi-row card or a small multiple, or move detail to drillthrough.
- **Source:** <https://learn.microsoft.com/power-bi/guidance/power-bi-optimization>

### PERF-02 Too many fields in one visual

- **Severity:** Low. **Check:** D (scan.py). **Type:** defect.
- **Why:** Wide visuals generate heavy queries and are hard to read (hard limit is far higher).
- **How to verify:** More than 20 projections in one visual.
- **Fix:** Split the visual or use drillthrough for detail.
- **Source:** <https://github.com/NatVanG/fab-inspector>

### PERF-03 DirectQuery page with many single-value cards

- **Severity:** Medium. **Check:** J (agent). **Type:** defect.
- **Why:** In DirectQuery every card is a separate source query.
- **How to verify:** Partitions with `mode: directQuery` plus pages with many cards.
- **Fix:** Use a multi-row card or table; enable query reduction.
- **Source:** <https://learn.microsoft.com/power-bi/guidance/directquery-model-guidance>

### PERF-04 Large fact table without incremental refresh

- **Severity:** Medium. **Check:** R (not offline). **Type:** defect.
- **Why:** Presence of `refreshPolicy` can be read from files, but whether a table is large needs runtime data.
- **How to verify:** Check row counts in the Service or with DMVs; check `refreshPolicy` blocks in TMDL.
- **Fix:** Add an incremental refresh policy with RangeStart/RangeEnd.
- **Source:** <https://learn.microsoft.com/power-bi/connect-data/incremental-refresh-overview>

### PERF-05 Model size, column cardinality, visual query timings

- **Severity:** Info. **Check:** R (not offline). **Type:** defect.
- **Why:** Only measurable with Performance Analyzer, VertiPaq Analyzer or the Service.
- **How to verify:** Not assessable offline.
- **Fix:** Run Performance Analyzer on the slowest pages.
- **Source:** <https://learn.microsoft.com/power-bi/guidance/power-bi-optimization>

<!-- END GENERATED RULES -->
