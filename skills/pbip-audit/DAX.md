# DAX

Rules about measure expressions and their metadata. D rules come from text patterns over TMDL expressions after comments and strings are stripped; they are heuristics with a stated confidence. Business correctness (DAX-11) is judged against the project's own `domain-rules.md` (copy `domain-rules.example.md`); the skill never ships domain rules.

False-positive discipline: BLANK-to-zero (DAX-04) and `/` with a guaranteed non-zero denominator can be intentional. Read the measure and its description before confirming.

## Rules

<!-- BEGIN GENERATED RULES -->

<!-- Generated from scripts/pbip_audit/catalog.py by scripts/render_catalog.py. Do not edit by hand. -->

| ID | Title | Severity | Check | Who checks | Type |
|---|---|---|---|---|---|
| DAX-01 | Division operator instead of DIVIDE | Medium | D | scan.py | defect |
| DAX-02 | FILTER over a table as a CALCULATE argument | Medium | J | agent | defect |
| DAX-03 | IFERROR / ISERROR | Medium | D | scan.py | defect |
| DAX-04 | BLANK converted to zero | Low | D | scan.py | recommendation |
| DAX-05 | Repeated sub-expressions without variables / EARLIER | Low | J | agent | defect |
| DAX-07 | Visible measure without a format string | Medium | D | scan.py | defect |
| DAX-08 | TODO / FIXME left in DAX | Low | D | scan.py | defect |
| DAX-09 | TODAY()/NOW() window measures that ignore slicers | Medium | J | agent | defect |
| DAX-11 | Measure semantically wrong for its name or for the domain rules | High | J | agent | defect |

### DAX-01 Division operator instead of DIVIDE

- **Severity:** Medium. **Check:** D (scan.py). **Type:** defect.
- **Why:** `/` raises an error or returns infinity when the denominator is zero or blank; DIVIDE handles it.
- **How to verify:** A `/` in a measure whose denominator is not a numeric constant (strings, comments and names are stripped first).
- **Fix:** Use `DIVIDE(numerator, denominator)`.
- **Source:** <https://learn.microsoft.com/dax/best-practices/dax-divide-function-operator>

### DAX-02 FILTER over a table as a CALCULATE argument

- **Severity:** Medium. **Check:** J (agent). **Type:** defect.
- **Why:** Filtering a whole table is slower and changes semantics compared to a Boolean column filter.
- **How to verify:** Find `CALCULATE(..., FILTER(Table, ...))` where a column predicate would do.
- **Fix:** Use a Boolean filter or `KEEPFILTERS`.
- **Source:** <https://learn.microsoft.com/dax/best-practices/dax-avoid-avoid-filter-as-filter-argument>

### DAX-03 IFERROR / ISERROR

- **Severity:** Medium. **Check:** D (scan.py). **Type:** defect.
- **Why:** Error functions force row-by-row evaluation and hide data problems.
- **How to verify:** `IFERROR(` or `ISERROR(` in any DAX expression.
- **Fix:** Use DIVIDE, defensive conditions, or fix the data.
- **Source:** <https://learn.microsoft.com/dax/best-practices/dax-error-functions>

### DAX-04 BLANK converted to zero

- **Severity:** Low. **Check:** D (scan.py). **Type:** recommendation.
- **Why:** Turning BLANK into 0 makes visuals show every dimension member and can slow queries; sometimes it is intended.
- **How to verify:** `DIVIDE(a, b, 0)`; confirm intent before raising severity.
- **Fix:** Return BLANK, or apply the zero only in the visual (show items with no data).
- **Source:** <https://learn.microsoft.com/dax/best-practices/dax-avoid-converting-blank>

### DAX-05 Repeated sub-expressions without variables / EARLIER

- **Severity:** Low. **Check:** J (agent). **Type:** defect.
- **Why:** Repeated expressions are evaluated more than once and are harder to read.
- **How to verify:** Read long measures for repeated sub-expressions or EARLIER.
- **Fix:** Introduce `VAR` blocks.
- **Source:** <https://learn.microsoft.com/dax/best-practices/dax-variables>

### DAX-07 Visible measure without a format string

- **Severity:** Medium. **Check:** D (scan.py). **Type:** defect.
- **Why:** Unformatted measures show raw decimals and inconsistent units across visuals and in Copilot answers.
- **How to verify:** Visible measures with no `formatString` and no `formatStringDefinition`. Measures that look textual (name suggests title/label/colour, or the expression uses FORMAT, SELECTEDVALUE, CONCATENATEX, `&` or returns string literals) are skipped.
- **Fix:** Set a format string on every visible measure.
- **Source:** <https://github.com/TabularEditor/BestPracticeRules>

### DAX-08 TODO / FIXME left in DAX

- **Severity:** Low. **Check:** D (scan.py). **Type:** defect.
- **Why:** Open work notes in production measures signal unfinished logic.
- **How to verify:** `TODO`, `FIXME` or `HACK` inside a DAX expression.
- **Fix:** Resolve or move the note to the issue tracker.
- **Source:** <https://github.com/TabularEditor/BestPracticeRules>

### DAX-09 TODAY()/NOW() window measures that ignore slicers

- **Severity:** Medium. **Check:** J (agent). **Type:** defect.
- **Why:** A measure that computes its own date window from TODAY() and removes date filters ignores the user's date selection. That is fine when labelled, misleading when not. The scanner raises the visual-level case as IN-05.
- **How to verify:** Find measures combining TODAY/NOW with REMOVEFILTERS/ALL on the date table or DATESBETWEEN/DATESINPERIOD; read their description.
- **Fix:** Document the window in the description and in every visual title that shows it.
- **Source:** <https://learn.microsoft.com/power-bi/guidance/model-date-tables>

### DAX-11 Measure semantically wrong for its name or for the domain rules

- **Severity:** High. **Check:** J (agent). **Type:** defect.
- **Why:** Business correctness cannot be checked generically. Load the project's domain-rules file and check measures against it.
- **How to verify:** Compare each measure with its name, description and the user-supplied domain rules.
- **Fix:** Fix the logic or rename the measure; add an anchor-figure regression test.
- **Source:** <https://github.com/TabularEditor/BestPracticeRules>

<!-- END GENERATED RULES -->
