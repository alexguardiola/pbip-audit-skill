# Validation and reporting

## Outputs (full audit mode)

Write to a directory outside the audited project (default `~/pbip-audit/<project>/run-<N>/`):

| File | Content |
|---|---|
| `scan.json` | Raw `scan.py --format json` output, untouched |
| `findings.json` | Reviewed findings: scanner D findings (with `status`) plus your J findings; must pass `validate_findings.py` |
| `REPORT.md` | Human report (template below); `scan.py --format md` gives a starting point with summary, scorecard and the R list |
| `scan.sarif` | Optional: `scan.py --format sarif` for GitHub code scanning (`--path-prefix` makes paths repository-relative) |

## Building findings.json

1. Copy `scan.json` to `findings.json`.
2. For each D finding add `status`:
   - `confirmed`: evidence re-read, the problem is real.
   - `false_positive`: keep the finding and add `reviewer_note` with the reason. Do not delete it; it documents the scanner's limits.
   - `needs_validation`: depends on intent or runtime data; add the question in `reviewer_note`.
3. Append J findings with `check_type: "J"`, an `id` of `<RULE>#<n>` (continue numbering per rule), and at least one evidence item with `file` and `line` or `json_path`. Use pillar `domain` for domain-rule findings that do not fit DAX-11.
4. Recompute `summary.total` and `summary.by_severity` (count every finding in the list, including `false_positive` ones).
5. Validate:

```bash
python <skill-dir>/scripts/validate_findings.py findings.json
```

The validator checks the JSON schema (types, enums, required fields, id format, evidence present) and consistency (unique ids, id prefix matches `rule_id`, summary counts match). Exit code 0 means valid.

## Evidence rules

- `file` is relative to the folder that contains the `.pbip`, with forward slashes.
- `line` is 1-based. For TMDL objects it is the declaration line. For JSON, the scanner locates the exact node with a line-tracking parser (the line of the key, e.g. the `syncGroup` of that visual, not the first `syncGroup` in the file) and adds `json_path`. Give J findings the same precision.
- `detail` is a short label (object name, page name). Never paste credentials or long data literals.

## REPORT.md template

```markdown
# Power BI audit: <project>

<context block from reconnaissance>

## Executive summary
Three to five sentences: overall state, the one or two things to fix first, and what was not assessable.

## Scorecard

| Pillar | Critical | High | Medium | Low | Info | Comment |
|---|---|---|---|---|---|---|
| Model | | | | | | |
| DAX | | | | | | |
| Interaction | | | | | | |
| Governance & AI readiness | | | | | | |
| Performance | | | | | | |
| Accessibility | | | | | | |
| Visual design | | | | | | |
| Storytelling | | | | | | |
| Mobile | | | | | | |

Count only `confirmed` and `needs_validation` findings.

`scan.py --format md` prints a scorecard with a score per pillar. The formula is deliberately simple and printed in the report:

- pillar score = max(0, 100 - sum of the severity weights of its findings), weights Critical 25, High 10, Medium 4, Low 1, Info 0;
- a finding counts once however many locations it lists (findings are already aggregated per root cause);
- `false_positive` findings are excluded;
- overall = mean of the nine pillar scores, or of the assessed ones only: a pillar whose files are missing or not readable offline (report pillars when the report is not PBIR, Model and DAX when the model is not TMDL) shows "not assessed" (`score: null`, `assessed: false` in the JSON) instead of a free 100.

Use the score to rank where to look; do not present it as a certification, and do not compare scores between projects of very different size. If you add J findings, recompute with the same formula (or leave the scores out and say so).

## Findings

### Critical
#### <ID> <title>  (D|J, confidence, defect|recommendation)
What is wrong and who is affected.
Evidence: `path:line` (json path)
Fix: concrete change.

### High ... ### Info

## Not assessable offline
R rules, one line each, with what would be needed to check them.

## Scanner false positives
D findings marked false_positive, with the reason (helps improve the scanner).
```

## Quality bar before handing over

- Every finding has evidence that you opened and read.
- No recommendation is labelled as a defect.
- Severity changes from the scanner default carry a reason.
- The R list is present.
- `validate_findings.py` passes.
