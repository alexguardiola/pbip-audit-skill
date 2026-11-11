# Governance and AI readiness

Rules about metadata, file-format health, secrets and Copilot/Q&A readiness. Descriptions and naming are what Copilot grounds on, so missing descriptions are reported as defects for visible measures. Service-side settings (sensitivity labels, endorsement, Prep data for AI) are not stored in PBIP files and are therefore R.

Non-English object names are a trade-off (GOV-07, Info), not a defect: report the language, do not penalise it.

## Rules

<!-- BEGIN GENERATED RULES -->

<!-- Generated from scripts/pbip_audit/catalog.py by scripts/render_catalog.py. Do not edit by hand. -->

| ID | Title | Severity | Check | Who checks | Type |
|---|---|---|---|---|---|
| GOV-01 | Visible measure without a description | Medium | D | scan.py | defect |
| GOV-02 | Description longer than 200 characters | Low | D | scan.py | defect |
| GOV-03 | Ambiguous or non-descriptive object names | Medium | J | agent | defect |
| GOV-07 | Non-English object names lower Copilot synonym quality | Info | J | agent | defect |
| GOV-09 | Credential in M or shared expression | Critical | D | scan.py | defect |
| GOV-10 | Literal data values persisted in PBIR filters | Low | J | agent | defect |
| GOV-11 | RLS roles defined and filters valid | Medium | J | agent | defect |
| GOV-12 | Sensitivity label, endorsement, Copilot approval, Prep data for AI | Info | R | not offline | defect |
| GOV-13 | Report uses the PBIR-Legacy format | Medium | D | scan.py | recommendation |
| GOV-14 | Page or visual folder name ignored by Desktop | High | D | scan.py | defect |
| GOV-15 | Unparseable JSON or TMDL | High | D | scan.py | defect |
| GOV-17 | PBIR file does not match its declared schema | High | D | scan.py | defect |
| GOV-18 | Schema not checked (version not in the local cache) | Info | D | scan.py | recommendation |
| EXT-01 | Imported Tabular Editor BPA result | Info | D | scan.py | recommendation |
| EXT-02 | Imported Fab Inspector result | Info | D | scan.py | recommendation |
| GOV-16 | Model stored as TMSL (model.bim) | Info | D | scan.py | recommendation |

### GOV-01 Visible measure without a description

- **Severity:** Medium. **Check:** D (scan.py). **Type:** defect.
- **Why:** Descriptions show in tooltips, field lists and feed Copilot/Q&A grounding. Missing descriptions are the main AI-readiness gap.
- **How to verify:** Visible measures without a `///` description line.
- **Fix:** Add a one-sentence description that says what the measure counts and any window or exclusion.
- **Source:** <https://learn.microsoft.com/power-bi/create-reports/copilot-prepare-data-ai>

### GOV-02 Description longer than 200 characters

- **Severity:** Low. **Check:** D (scan.py). **Type:** defect.
- **Why:** Copilot and tooltips truncate long descriptions.
- **How to verify:** `///` description over 200 characters on a measure, column or table.
- **Fix:** Keep the first sentence self-contained; move detail to documentation.
- **Source:** <https://learn.microsoft.com/power-bi/create-reports/copilot-semantic-models>

### GOV-03 Ambiguous or non-descriptive object names

- **Severity:** Medium. **Check:** J (agent). **Type:** defect.
- **Why:** Duplicate field names across tables and names like `Table1` confuse users and AI.
- **How to verify:** Read the field list for duplicates and placeholders.
- **Fix:** Rename to business terms.
- **Source:** <https://learn.microsoft.com/power-bi/create-reports/copilot-prepare-data-ai>

### GOV-07 Non-English object names lower Copilot synonym quality

- **Severity:** Info. **Check:** J (agent). **Type:** defect.
- **Why:** Copilot grounding works best with English names; this is a trade-off, not a defect.
- **How to verify:** Note the model language from `culture` and the names.
- **Fix:** Add synonyms / linguistic schema, or accept the trade-off.
- **Source:** <https://learn.microsoft.com/power-bi/create-reports/copilot-prepare-data-ai>

### GOV-09 Credential in M or shared expression

- **Severity:** Critical. **Check:** D (scan.py). **Type:** defect.
- **Why:** Passwords in source control leak to everyone with repository access.
- **How to verify:** `password=` / `pwd=` patterns in partition sources and expressions.tmdl.
- **Fix:** Remove the secret, rotate it and use gateway / data-source credentials.
- **Source:** <https://learn.microsoft.com/analysis-services/tmdl/tmdl-overview>

### GOV-10 Literal data values persisted in PBIR filters

- **Severity:** Low. **Check:** J (agent). **Type:** defect.
- **Why:** PBIR stores filter and slicer selections as literals, which can leak sensitive values into git.
- **How to verify:** Review `filterConfig` literals in sensitive projects.
- **Fix:** Clear selections before committing, or keep the repository private.
- **Source:** <https://learn.microsoft.com/power-bi/developer/projects/projects-report>

### GOV-11 RLS roles defined and filters valid

- **Severity:** Medium. **Check:** J (agent). **Type:** defect.
- **Why:** Row-level security filters that reference wrong columns fail open or closed.
- **How to verify:** Read `roles/*.tmdl` table permissions.
- **Fix:** Test roles with View as role.
- **Source:** <https://learn.microsoft.com/fabric/security/service-admin-row-level-security>

### GOV-12 Sensitivity label, endorsement, Copilot approval, Prep data for AI

- **Severity:** Info. **Check:** R (not offline). **Type:** defect.
- **Why:** Stored in the Service, not in PBIP files.
- **How to verify:** Not assessable offline.
- **Fix:** Check in the Service settings.
- **Source:** <https://learn.microsoft.com/power-bi/create-reports/copilot-prepare-data-ai>

### GOV-13 Report uses the PBIR-Legacy format

- **Severity:** Medium. **Check:** D (scan.py). **Type:** recommendation.
- **Why:** PBIR-Legacy `report.json` is an undocumented blob that cannot be reviewed or audited; PBIR is now the default.
- **How to verify:** Root `report.json` with no `definition/` folder.
- **Fix:** Open and save in a current Desktop release to convert to PBIR.
- **Source:** <https://learn.microsoft.com/power-bi/developer/projects/projects-report>

### GOV-14 Page or visual folder name ignored by Desktop

- **Severity:** High. **Check:** D (scan.py). **Type:** defect.
- **Why:** Folder names that are not word characters or hyphens are silently ignored as private files, so the page or visual disappears.
- **How to verify:** Folder names under `pages/` and `visuals/` not matching `^[\w-]+$`.
- **Fix:** Rename the folder to letters, digits, underscores or hyphens.
- **Source:** <https://learn.microsoft.com/power-bi/developer/projects/projects-report>

### GOV-15 Unparseable JSON or TMDL

- **Severity:** High. **Check:** D (scan.py). **Type:** defect.
- **Why:** Desktop refuses to open a project with invalid files.
- **How to verify:** JSON decode errors and unrecognised TMDL lines.
- **Fix:** Fix the file (usually a merge conflict or manual edit).
- **Source:** <https://learn.microsoft.com/power-bi/developer/projects/projects-report>

### GOV-17 PBIR file does not match its declared schema

- **Severity:** High. **Check:** D (scan.py). **Type:** defect.
- **Why:** Each PBIR file declares a `$schema` version. A file that lacks a required top-level property (or carries one the schema forbids) usually comes from a hand edit or a bad merge, and Desktop may refuse to open the report.
- **How to verify:** Opt-in (`--validate-schemas`): compare each file's top-level properties with the cached shape of the declared schema version (required, allowed, oneOf). High when something required is missing, Medium for a disallowed property.
- **Fix:** Restore the missing property or remove the unknown one; re-save in Desktop to normalise.
- **Source:** <https://github.com/microsoft/json-schemas/tree/main/fabric/item/report>

### GOV-18 Schema not checked (version not in the local cache)

- **Severity:** Info. **Check:** D (scan.py). **Type:** recommendation.
- **Why:** The scanner never downloads schemas. Files whose declared schema version is not cached are listed so the gap is visible rather than silently passing.
- **How to verify:** Opt-in (`--validate-schemas`): declared `$schema` kind/version absent from `scripts/pbip_audit/schema_cache.json`.
- **Fix:** Refresh the cache with `scripts/tools/refresh_schema_cache.py` (network) or ignore; this is information only.
- **Source:** <https://github.com/microsoft/json-schemas/tree/main/fabric/item/report>

### EXT-01 Imported Tabular Editor BPA result

- **Severity:** Info. **Check:** D (scan.py). **Type:** recommendation.
- **Why:** Best Practice Analyzer results imported with `--import-bpa`, so model-level rules from Tabular Editor appear in the same report and SARIF file. Severity, pillar and wording come from the BPA rule; the finding records the original rule in `origin`.
- **How to verify:** Run BPA (Tabular Editor CLI or semantic-link-labs) and pass its output file.
- **Fix:** Follow the BPA rule's own guidance.
- **Source:** <https://docs.tabulareditor.com/common/using-bpa.html>

### EXT-02 Imported Fab Inspector result

- **Severity:** Info. **Check:** D (scan.py). **Type:** recommendation.
- **Why:** Failed Fab Inspector (PBI Inspector) rules imported with `--import-fabinspector`. Severity and wording come from the Fab Inspector rule; the finding records the original rule in `origin`.
- **How to verify:** Run Fab Inspector against the PBIP and pass its JSON results file.
- **Fix:** Follow the Fab Inspector rule's own guidance.
- **Source:** <https://github.com/NatVanG/fab-inspector>

### GOV-16 Model stored as TMSL (model.bim)

- **Severity:** Info. **Check:** D (scan.py). **Type:** recommendation.
- **Why:** This version of the scanner only parses TMDL, so model rules were skipped.
- **How to verify:** `model.bim` present, no `definition/` folder.
- **Fix:** Save the model as TMDL (Desktop option) to get model findings.
- **Source:** <https://learn.microsoft.com/analysis-services/tmdl/tmdl-overview>

<!-- END GENERATED RULES -->
