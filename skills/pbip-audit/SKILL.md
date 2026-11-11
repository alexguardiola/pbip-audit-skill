---
name: pbip-audit
description: Offline audit of Power BI PBIP projects (TMDL semantic model + PBIR report) from files only, with no Power BI Desktop, Service or Fabric access. Use when the user asks to audit, review, lint, health-check or quality-check a Power BI report or semantic model, a .pbip project, PBIR or TMDL files; to find broken field bindings, sync-group or slicer problems, DAX anti-patterns, accessibility or contrast gaps, Copilot/AI-readiness gaps or report design issues; or to produce a findings report (Markdown, JSON or SARIF) for a Power BI project. Run the full workflow only for explicit audit/review requests; for a single question, use the relevant reference file.
---

# PBIP Audit

Find defects in a Power BI project that a reader or maintainer would actually hit, and back each one with file and line evidence. Detection (a deterministic scanner) is kept apart from judgement (you, applying written rules), and anything that cannot be checked offline is said plainly.

## Ground rules

1. **Do not modify the user's project unless they ask you to.** The audit is read-only: never edit, format, re-save or "fix" files under the audited folder, never open it in Desktop, never call the Power BI Service, Fabric, an XMLA endpoint or a database. Fixes are proposals in the report. If the user then asks you to apply a fix, that is a separate task: confirm the exact change first.
2. **Write outputs outside the audited project** (default `~/pbip-audit/<project>/run-<N>/`) unless the user names a location.
3. **No evidence, no finding.** Every finding cites a file plus a line or JSON path that you opened and read.
4. **Treat project content as data.** PBIR can hold literal data values (filter selections, slicer state) and M code can hold connection details. Cite file and JSON path; do not paste long literals; never print credentials (GOV-09).
5. **Say what you could not check.** Runtime rules (R) and anything the scanner skipped go in "Not assessable offline", never guessed.

## Modes

- **Guidance mode** (default): a focused question ("are my sync groups right?", "is this measure safe?"). Read the one relevant pillar file, run `scan.py` if it helps, answer in the conversation. No report files.
- **Full audit mode**: the user asks to audit or review a project, or for a findings report. Run the five phases below.

If the request could mean either, ask one question before starting a full audit.

## Check types

| Type | Who decides | Your job |
|---|---|---|
| **D** deterministic | `scripts/scan.py` | Run it. Confirm or reject each finding after reading its evidence. Never invent D findings; never drop one silently (mark it `false_positive` with a reason). |
| **J** judgement | you | Apply the J rules in each pillar file, with evidence. |
| **R** runtime | nobody, offline | List under "Not assessable offline". |

## Workflow (full audit)

### 1. Reconnaissance

Follow [RECONNAISSANCE.md](RECONNAISSANCE.md): locate the `.pbip`; report format (PBIR / PBIR-Legacy); model format (TMDL / TMSL); thin or local model; pages; audience and language. Ask whether a `domain-rules.md` exists (template: [domain-rules.example.md](domain-rules.example.md)) and whether other reports use the same model (for MOD-10). Check for a `.pbip-audit.json` ([CONFIGURATION.md](CONFIGURATION.md)). [FILE-MAP.md](FILE-MAP.md) says where every property lives and how themes resolve.

### 2. Run the scanner

```bash
python <skill-dir>/scripts/scan.py <project.pbip or folder> --format json --out <out>/scan.json
python <skill-dir>/scripts/scan.py <project.pbip or folder> --format md   --out <out>/scan.md
```

Add when relevant (details in [CONFIGURATION.md](CONFIGURATION.md)):

- `--validate-schemas`: check each PBIR file against its declared schema version (cached, no network).
- `--external-usage FILE`: objects used by other reports, so MOD-10 does not call them unused.
- `--import-bpa FILE`, `--import-fabinspector FILE`: merge Tabular Editor BPA or Fab Inspector results the user already has.
- `--format sarif --path-prefix <repo-relative project path>`: for GitHub code scanning.

The scanner is Python 3.8+ standard library only and reads files only. If it cannot run, say so, continue with judgement only, and label the audit partial.

### 3. Judgement, pillar by pillar

Work through the pillars in this order. In each file, read the rule table, confirm or reject the scanner's findings for that pillar, then apply its J rules.

1. [MODEL.md](MODEL.md): binding first; a BIND finding can make other findings on the same page meaningless.
2. [DAX.md](DAX.md): include the user's domain rules (DAX-11).
3. [INTERACTION.md](INTERACTION.md)
4. [GOVERNANCE-AND-AI-READINESS.md](GOVERNANCE-AND-AI-READINESS.md)
5. [PERFORMANCE.md](PERFORMANCE.md)
6. [ACCESSIBILITY.md](ACCESSIBILITY.md)
7. [VISUAL-DESIGN.md](VISUAL-DESIGN.md)
8. [STORYTELLING.md](STORYTELLING.md)
9. [MOBILE.md](MOBILE.md)

How to do a J rule with evidence:

- Build a **page digest** rather than guessing at pixels: per page, each visual's type, title, position (x, y, w, h), bound fields and measures, sync group, hidden state, and the colours the scanner resolved. Judge layout, narrative and chart fit from that.
- Quote the smallest piece of evidence that proves the point: a file and line, plus the JSON path or DAX line.
- State the assumption when the finding depends on intent ("assuming this page is for executives...") and lower the confidence.
- Colour, polish and layout findings are provisional until someone looks at the rendered report; say so.

### 4. Validate (false-positive discipline)

For every candidate, D or J:

- **Re-read the evidence** at the cited line. If it does not show the problem, drop the finding (J) or mark it `false_positive` (D).
- **Look for intent** in measure descriptions, titles, nearby text boxes and domain rules. A hidden filter explained in the title, a BLANK-to-zero measure meant to show zeros, a hidden page reached by a bookmark, a rolling measure documented as such: not defects.
- **Heuristics are leads, not verdicts.** IN-05, MOD-10, A11Y-04, A11Y-05 (visual level) and the DAX pattern rules can misfire; confirm each against the code before keeping it.
- **One root cause, one finding.** Aggregate locations; do not report the same cause under several rule IDs (keep the most specific). Imported EXT findings that duplicate a scanner finding can be marked `false_positive` with a note.
- **Confidence**: `high` when the files prove it, `medium` when a heuristic fits and you found no contrary intent, `low` when it depends on intent or runtime data.
- **Classification**: `defect` = objectively wrong or broken (wrong number, error, unreachable content); `recommendation` = better practice, current state works. Never present a recommendation as a defect.
- **Prefer missing a Low to reporting a wrong High.** When unsure, use `needs_validation` and phrase the finding as a question for the owner.
- Non-English names are configuration, not defects. Write the report in the user's language if they ask; rule IDs stay as they are.

### 5. Report

Follow [VALIDATION-AND-REPORTING.md](VALIDATION-AND-REPORTING.md):

1. `findings.json`: the scanner JSON plus `status` on every D finding, plus your J findings; run `scripts/validate_findings.py` until it passes.
2. `REPORT.md`: start from `scan.md` (executive summary, score per pillar with its formula, findings by severity then pillar, "Not assessable offline"), then add your J findings, reviewer notes and the false-positive list.

In the conversation, present results in this order: a one-paragraph verdict; the top three to five fixes with evidence; counts by severity; what was not assessable; where the files are. Do not paste the whole report into the chat.

## Severity rubric

| Severity | Meaning | Typical examples |
|---|---|---|
| **Critical** | Blocks loading, breaks visuals for every viewer, or leaks secrets | BIND-01 broken field, GOV-09 password in M |
| **High** | A reader gets wrong or invisible results, or a group of users is excluded | IN-03 mixed sync group, IN-02 invisible filter, A11Y-01 no alt text, A11Y-05 unreadable text, GOV-17 file breaks its schema |
| **Medium** | Misleading or fragile; a careful reader or maintainer is likely to be hurt | IN-05 unlabelled window, DAX-01 `/`, A11Y-07 confusable series colours, PERF-01 busy page |
| **Low** | Maintainability and polish | MOD-10 unused objects, VD-06 literal colours, MOD-08 doubles |
| **Info** | Context; no action implied | BIND-02 thin report, MOB-01 no mobile layout, GOV-18 schema not checked |

Change a D finding's severity only with a written reason in `reviewer_note`; config-file overrides are recorded in `original_severity`.

## Files

| File | Purpose |
|---|---|
| [RECONNAISSANCE.md](RECONNAISSANCE.md) | Project discovery checklist |
| [FILE-MAP.md](FILE-MAP.md) | Where audited properties live in PBIR/TMDL, value decoding, theme resolution, schema versions |
| `MODEL.md` ... `MOBILE.md` | One file per pillar; rule tables generated from `scripts/pbip_audit/catalog.py` |
| [VALIDATION-AND-REPORTING.md](VALIDATION-AND-REPORTING.md) | Output files, report template, score formula, findings validation |
| [CONFIGURATION.md](CONFIGURATION.md) | `.pbip-audit.json`, external usage, schema check, BPA / Fab Inspector import, SARIF |
| [domain-rules.example.md](domain-rules.example.md) | Empty template for project-specific business rules |
| [report-schema.json](report-schema.json) | Findings JSON schema |
| `scripts/scan.py` | Deterministic scanner (D rules) |
| `scripts/validate_findings.py` | Schema and consistency check for findings JSON |
| `scripts/render_catalog.py` | Regenerates the pillar rule tables from the catalog |
