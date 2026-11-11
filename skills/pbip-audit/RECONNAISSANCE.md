# Reconnaissance

Goal: know what you are auditing before you judge it. Spend a few minutes here; it decides which rules apply.

## Checklist

1. **Locate the project.** Find the `*.pbip` file. Read `artifacts[].report.path`. One folder can hold several projects; audit one at a time.
2. **Report format.**
   - `<Name>.Report/definition/` exists: **PBIR**. All report rules apply.
   - Only `<Name>.Report/report.json`: **PBIR-Legacy**. Raise GOV-13 and skip report rules; the legacy blob is not a documented format.
3. **Model location.** Read `<Name>.Report/definition.pbir`:
   - `datasetReference.byPath.path`: local model (relative path). Binding checks run.
   - `datasetReference.byConnection`: **thin report**. Binding checks cannot run (BIND-02). Ask whether the model project is available to audit separately.
4. **Model format.** `<Model>.SemanticModel/definition/` = TMDL (supported). Only `model.bim` = TMSL (GOV-16; model rules are skipped by the scanner, you may still read the JSON by hand).
5. **Inventory.** Count pages (`definition/pages/pages.json` for order), visuals, bookmarks, tables, measures, relationships. `scan.py` prints these under `stats`.
6. **Purpose and audience.** Read page names, the first text boxes and titles, measure descriptions. Write two sentences: who uses this report and which decisions it supports. Ask the user if it is unclear; storytelling and mobile rules depend on it.
7. **Language and culture.** `culture:` in `model.tmdl`, the language of object names and page names. Note it; do not penalise it (GOV-07 is Info).
8. **Domain rules.** Look for `domain-rules.md` (or similar) next to the project, or ask the user. Without it, DAX-11 is limited to "measure contradicts its own name or description".
9. **Storage mode and refresh.** Partition `mode:` (import / directQuery / dual), `refreshPolicy` blocks, `expressions.tmdl` parameters. These change which performance rules matter.
10. **Version skew.** Different `$schema` versions across visual.json files are normal (Desktop rewrites only the files it touches). Do not report skew by itself. `--validate-schemas` checks each file against its own declared version.
11. **Version control state.** If the project is a git repository, note the commit and whether the working tree is dirty. Findings refer to the files as read.

## Output of this phase

A short context block for the report:

```
Project: <name>.pbip  (commit <sha>, dirty: yes/no)
Report: PBIR, N pages (M hidden), V visuals, B bookmarks
Model: TMDL, T tables, X measures, R relationships, culture xx-XX, storage import
Binding: local model | thin report
Audience / purpose: ...
Domain rules: <path> | none supplied
```
