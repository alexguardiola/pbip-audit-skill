# Domain rules (template)

Copy this file next to your PBIP project as `domain-rules.md` and fill it in. The pbip-audit skill reads it during the DAX-11 (business correctness) review. It is never shipped with real content; keep your copy wherever your project's confidentiality rules require (often outside version control).

Write each rule so that someone who does not know the business can check a measure against it.

## Glossary

| Term | Definition | Model object(s) |
|---|---|---|
| | | |

## Business rules and gotchas

Rules that a correct measure must respect. Example shape: "Revenue excludes intercompany lines: any measure over `<Table>[<amount column>]` must filter `<flag column> = FALSE`."

| ID | Rule | Applies to | How to check in DAX/M |
|---|---|---|---|
| DR-01 | | | |

## Status and lifecycle fields

Fields whose values are commonly misread (for example a status that does not mean "final").

| Field | Value | What it really means |
|---|---|---|
| | | |

## Anchor figures

Known-good numbers to compare against when a runtime check is possible (period, filter, expected value, source of truth).

| Measure | Filter context | Expected value | Source | Last verified |
|---|---|---|---|---|
| | | | | |

## Accepted exceptions

Findings the team has reviewed and accepted, so the audit reports them as Info instead of re-raising them.

| Rule ID | Object / file | Reason | Accepted by / date |
|---|---|---|---|
| | | | |
