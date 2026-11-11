# Configuration, integrations and outputs

Everything here is optional. With no configuration the scanner uses the defaults below.

## `.pbip-audit.json`

The scanner looks for `.pbip-audit.json` in the folder that holds the `.pbip`, then in each parent folder up to the filesystem root, so one file at a repository root covers every project below it. `--config FILE` picks a file explicitly; `--no-config` ignores any file. Command-line options override the file. Unknown keys, bad thresholds, bad regular expressions, unknown rule IDs and unknown severities are errors (exit code 1), so typos do not silently change results.

```json
{
  "thresholds": {
    "max_visuals": 12,
    "max_fields": 20,
    "as_of_year": 2026,
    "tab_order_tolerance": 0.4,
    "tab_order_row_band": 40,
    "min_text_contrast": 4.5,
    "min_graphic_contrast": 3.0,
    "cvd_delta_e": 10,
    "cvd_palette_size": 8
  },
  "disabled_rules": ["MOB-01"],
  "severity_overrides": {"MOD-10": "Info"},
  "naming": {
    "locales": ["en", "es"],
    "extra_default_page_patterns": ["^Sheet \\d+$"]
  },
  "domain_rules": "docs/domain-rules.md",
  "external_usage": "model-usage.txt"
}
```

| Key | Default | Effect |
|---|---|---|
| `thresholds.max_visuals` | 12 | PERF-01: data-bound visuals per page |
| `thresholds.max_fields` | 20 | PERF-02: fields per visual |
| `thresholds.as_of_year` | current year | IN-13: years after this are "future" |
| `thresholds.tab_order_tolerance` | 0.4 | A11Y-04: share of visual pairs whose tab order may disagree with reading order |
| `thresholds.tab_order_row_band` | 40 | A11Y-04: visuals whose `y` differs by less than this many px are one row |
| `thresholds.min_text_contrast` | 4.5 | A11Y-05: WCAG 1.4.3 normal text |
| `thresholds.min_graphic_contrast` | 3.0 | A11Y-05: large text (18pt+) and series colours (WCAG 1.4.11) |
| `thresholds.cvd_delta_e` | 10 | A11Y-07: CIELAB delta E under simulation below which two series colours are confusable |
| `thresholds.cvd_palette_size` | 8 | A11Y-05 graphics / A11Y-07: how many theme data colours count as series colours |
| `disabled_rules` | none | Rule IDs whose findings are dropped |
| `severity_overrides` | none | Rule ID to severity; the finding keeps `original_severity` so the change is visible |
| `naming.locales` | `["en", "es", "de"]` | Which languages' default page names ST-01 recognises (`en es de fr pt it nl`) |
| `naming.extra_default_page_patterns` | none | Extra regular expressions for ST-01 |
| `domain_rules` | none | Path (relative to the config file) to your domain-rules file; recorded in the output so the agent applies it (DAX-11) |
| `external_usage` | none | MOD-10 allowlist file (below), relative to the config file |

Disabling or downgrading a rule is a policy decision; the output records the config file name so readers can see that one was applied.

## External usage (MOD-10)

MOD-10 only sees the report in the project. Other reports, Excel pivot tables, paginated reports or Copilot may use the same model. List those objects in a file and pass it with `--external-usage FILE` (or `external_usage` in the config):

```text
# one reference per line; '#' starts a comment
'Sales'[Margin %]
Customer[Segment]
Calendar.Fiscal Week
```

A JSON list of the same strings, or `{"objects": [...]}`, also works. Without the file, MOD-10 messages say that other consumers may use the objects.

## Schema validation (`--validate-schemas`)

Off by default. Each PBIR JSON file declares a `$schema` URL with a kind and version. The scanner compares the file's top-level properties with the cached shape of that exact version (`scripts/pbip_audit/schema_cache.json`): required properties, allowed properties when the schema forbids others, and oneOf sets such as `visual` or `visualGroup`. It does not validate nested structure. Findings:

- GOV-17 (High when something required is missing, Medium for a disallowed property);
- GOV-18 (Info) listing kinds/versions that are not in the cache. They are not guessed against another version.

The scanner never downloads anything. Maintainers refresh the cache with `python scripts/tools/refresh_schema_cache.py` (network).

## Importing other analyzers

Both adapters map results into the same findings schema, with `origin` naming the tool and the original rule, so one Markdown or SARIF output covers everything.

| Option | Tool | Accepted formats | Rule |
|---|---|---|---|
| `--import-bpa FILE` | Tabular Editor Best Practice Analyzer | Tabular Editor 2 CLI `-A` console output (plain, `-G` GitHub or `-V` Azure DevOps lines of the form `<Type> '<Object>' violates rule "<Rule>"`); JSON records with `Rule Name`, `Object Name`, `Object Type`, `Category`, `Severity`, `Description`, `URL` (for example semantic-link-labs `run_model_bpa` exported with `to_json(orient="records")`) | EXT-01 |
| `--import-fabinspector FILE` | Fab Inspector (PBI Inspector V2) | JSON results with `RuleId`, `RuleName`, `RuleDescription`, `Pass`, `LogType`, `ItemPath`, `Expected`, `Actual` (a list or under `Results`) | EXT-02 |

Mapping:

- BPA severity 3 / Error -> Medium, 2 / Warning -> Low, 1 / Info -> Info. Category -> pillar (Performance, DAX Expressions, Error Prevention -> model, Formatting/Maintenance/Naming -> governance). The object is located in the TMDL files when it exists, so the evidence has a file and line.
- Fab Inspector `LogType` Error -> Medium, Warning -> Low; only failed rules (`Pass: false`) are imported; pillar from the rule ID (ALTTEXT -> accessibility, COLOUR/THEME -> visual design, VISUALS_ON_PAGE -> performance...). `ItemPath` becomes the evidence file when it exists in the project.
- Keys are matched case- and punctuation-insensitively. A file that cannot be parsed becomes a note in the output, not a crash.

The formats were implemented from the tools' documentation and tested with synthetic files only (`scripts/tests/fixtures/imports/`). If your version's output differs, open an issue with a redacted sample.

Imported findings may duplicate scanner findings (both tools flag hard-coded colours, for example). That is deliberate: the source of each finding stays visible. Mark duplicates `false_positive` with a note during review if you prefer one.

## Outputs

| `--format` | Use |
|---|---|
| `json` (default) | Machine-readable findings, validated by `validate_findings.py` against `report-schema.json` |
| `md` | Human report: executive summary, score per pillar (formula printed), findings grouped by severity then pillar, "Not assessable offline" list, scanner notes |
| `sarif` | SARIF 2.1.0 for GitHub code scanning. Evidence paths are relative to the folder holding the `.pbip`; `--path-prefix powerbi/Sales` makes them relative to the repository root. Severity maps to `error` (Critical, High), `warning` (Medium), `note` (Low, Info) |

Example GitHub Actions step:

```yaml
- run: python skills/pbip-audit/scripts/scan.py reports/Sales --format sarif --path-prefix reports/Sales --out pbip-audit.sarif
- uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: pbip-audit.sarif
```

`--fail-on High` returns exit code 2 when a finding at or above that severity exists (false positives excluded), for CI gates.
