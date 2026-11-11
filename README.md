# pbip-audit-skill

[![tests](https://github.com/alexguardiola/pbip-audit-skill/actions/workflows/tests.yml/badge.svg)](https://github.com/alexguardiola/pbip-audit-skill/actions/workflows/tests.yml)
![python](https://img.shields.io/badge/python-3.8%2B-blue)
![dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)

An agent skill (Claude Code and other skill-aware agents) that audits **Power BI PBIP projects** from files only: the TMDL semantic model and the PBIR report, cross-checked against each other. No Power BI Desktop, Service, Fabric workspace, XMLA endpoint or admin role is needed, and nothing is sent anywhere.

It combines:

- a **deterministic scanner** (`scan.py`, Python 3.8+ standard library, no dependencies) that emits findings with exact file and line evidence, as JSON, Markdown or SARIF, and
- a **written methodology** (`SKILL.md` and one reference file per pillar) that tells the agent how to apply judgement rules, keep false positives down, and report what cannot be checked offline.

Status: **v0.2**. 79 rules catalogued: 48 deterministic (all implemented in the scanner, including 2 that import other tools' results), 26 judgement, 5 runtime-only. See [CHANGELOG.md](CHANGELOG.md).

## What it finds that others do not

The scanner builds one index of every model object and every report reference, and resolves the report theme. That makes it possible to detect, offline:

- visuals, filters and bookmarks bound to fields that no longer exist (BIND-01, BIND-03);
- slicer sync groups that mix different fields, or the same field split across groups (IN-03, IN-04);
- rolling-window measures (TODAY() plus removed date filters) shown under titles that do not say so (IN-05);
- year slicers that expose future years of a forecast calendar (IN-13);
- objects unused by the report and by every DAX expression (MOD-10), with an allowlist for other consumers of the model;
- text below WCAG contrast after resolving base + custom theme and `ThemeDataColor` references (A11Y-05), and series colours that collapse under red-green colour-vision deficiency (A11Y-07);
- PBIR files that no longer match the top-level shape of their declared schema version (GOV-17, opt-in).

## Install

The skill is the folder `skills/pbip-audit/`. Requirements: Python 3.8 or later on Windows, macOS or Linux. Nothing to `pip install`.

**Claude Code, personal skill (all projects):**

```bash
git clone https://github.com/alexguardiola/pbip-audit-skill.git
cp -r pbip-audit-skill/skills/pbip-audit ~/.claude/skills/
```

On Windows (PowerShell): `Copy-Item -Recurse pbip-audit-skill\skills\pbip-audit $HOME\.claude\skills\`

**Claude Code, project skill (one repository):** copy `skills/pbip-audit/` to `<your repo>/.claude/skills/pbip-audit/` and commit it, so everyone working in that repository gets it.

Claude Code picks up skills when a session starts; ask *"Audit the Power BI project in ./reports/Example.pbip"* and it follows `SKILL.md`.

**Other agents** (any agent that can read files and run Python): point it at `skills/pbip-audit/SKILL.md` as instructions, for example in your agent's rules or system prompt ("For Power BI audits follow skills/pbip-audit/SKILL.md"). All other files are linked from there.

**Without an agent:** run the scanner directly (below) or in CI.

## Quick start

```bash
python skills/pbip-audit/scripts/scan.py path/to/Project.pbip --format md --out scan.md
python skills/pbip-audit/scripts/scan.py path/to/folder --format json --out findings.json
python skills/pbip-audit/scripts/validate_findings.py findings.json
python skills/pbip-audit/scripts/scan.py path/to/Project.pbip --format sarif --path-prefix reports/Project --out pbip-audit.sarif
```

Useful options: `--validate-schemas`, `--external-usage FILE`, `--import-bpa FILE`, `--import-fabinspector FILE`, `--config FILE`, `--fail-on High` (exit code 2, for CI). Thresholds, disabled rules, severity overrides and naming locales go in `.pbip-audit.json`. All of it is documented in [CONFIGURATION.md](skills/pbip-audit/CONFIGURATION.md).

Sample output from the synthetic `defects` fixture: [examples/defects-report.md](examples/defects-report.md) and [examples/defects-report.sarif](examples/defects-report.sarif).

## Rule pillars

| Pillar | File | Examples |
|---|---|---|
| Model and binding | `MODEL.md` | broken bindings, bidirectional and inactive relationships, auto date/time, visible keys, unused objects |
| DAX | `DAX.md` | `/` vs DIVIDE, IFERROR, BLANK to zero, missing format strings, domain-rule correctness |
| Performance | `PERFORMANCE.md` | visuals per page, fields per visual, incremental refresh |
| Governance and AI readiness | `GOVERNANCE-AND-AI-READINESS.md` | descriptions, secrets in M, PBIR-Legacy, ignored folders, schema conformance, imported BPA / Fab Inspector results |
| Visual design | `VISUAL-DESIGN.md` | pie/donut, gauges without target, colours outside the theme, off-canvas visuals |
| Storytelling | `STORYTELLING.md` | default page names, unreachable hidden pages, narrative order |
| Interaction | `INTERACTION.md` | sync groups, hidden filters and slicers, drillthrough back buttons, rolling windows |
| Accessibility | `ACCESSIBILITY.md` | alt text, tab order, contrast, colour-vision confusion |
| Mobile | `MOBILE.md` | mobile layouts |

Each rule has an ID, severity (Critical / High / Medium / Low / Info), check type (D deterministic, J judgement, R runtime), rationale, how to verify, fix and a source link. Business-specific rules belong in your own `domain-rules.md` (template: `skills/pbip-audit/domain-rules.example.md`); the skill ships none.

## How it compares

Use the right tool for the job; several of these combine well (this skill can import BPA and Fab Inspector results).

| | This skill | [Tabular Editor BPA](https://docs.tabulareditor.com/common/using-bpa.html) | [Fab Inspector](https://github.com/NatVanG/fab-inspector) | [semantic-link-labs](https://github.com/microsoft/semantic-link-labs) | [Data Goblins `review-report`](https://github.com/data-goblin/power-bi-agentic-development) |
|---|---|---|---|---|---|
| Layer | Model + report, cross-checked | Semantic model | Report (PBIR) and other Fabric item definitions | Model and report | Report-centred review, plus a separate model auditor |
| Runs where | Locally, offline, files only | Tabular Editor 2/3 (CLI for CI) against a model or model files | Locally, in CI, or against a workspace | Fabric notebook, published items | Agent session; several dimensions call Fabric/Power BI APIs |
| Rules | 48 deterministic + 26 judgement rules with a written method | Community rule set ([BestPracticeRules](https://github.com/microsoft/Analysis-Services/tree/master/BestPracticeRules)) plus custom rules as expressions | Declarative JSON-Logic rules; [base set](https://raw.githubusercontent.com/NatVanG/fab-inspector/main/Rules/Base-rules.json) of about 11 threshold and hygiene rules, custom rules supported | `run_model_bpa`, `run_report_bpa` with custom rules as DataFrame expressions | Six review dimensions in the skill text |
| Report to model binding | Yes, offline | No (model only) | No model, so no | Yes (in the service) | Yes (binding dimension) |
| Uses runtime data (sizes, query times, usage) | No (listed as not assessable) | Some community rules read VertiPaq statistics stored as model annotations | Can inspect published workspace items | Yes | Yes, with the right API roles |
| Auto-fix | No (proposals only) | Yes, rules can carry fix expressions | No | Not part of the BPA run | Agent-driven |
| Output | JSON, Markdown, SARIF | UI; CLI console with GitHub / Azure DevOps annotations | Result files and CI-friendly exit codes (see its docs) | DataFrames | Agent report |

Where the others are stronger: BPA has a large, battle-tested model rule set and automatic fixes; Fab Inspector lets you write custom report rules without code and inspect live workspaces; semantic-link-labs and Data Goblins can use real model statistics, usage and performance data that a file-only tool never sees. What this skill adds is the offline join between the report and the model, interaction and accessibility checks that need both, and a methodology for the judgement pillars. Facts above were checked against each project's documentation in November 2026; tools change, so check their current docs.

## Limitations

- **Files only.** Model size, cardinality, query timings, usage, refresh history, sensitivity labels and endorsement are runtime facts; they are listed under "Not assessable offline", never guessed.
- **Formats.** TMSL (`model.bim`) models are detected but not parsed; PBIR-Legacy reports are flagged, not parsed.
- **DAX** checks are pattern-based over comment- and string-stripped text, not a DAX parser or engine.
- **Themes.** The `ThemeDataColor` mapping (0 background, 1 foreground, 2+ data colours, Percent as tint/shade) is an approximation of undocumented behaviour. Contrast is skipped for measure-driven colours, text over shapes/images, and data labels that may sit inside bars or slices. When the base theme file is absent, a built-in copy of the default palette is used.
- **Schema validation** checks top-level properties only, against a cached summary of Microsoft's published schemas; versions that are not published or not cached are reported as not checked.
- **MOD-10** sees only this report; list other consumers of the model with `--external-usage`.
- **Heuristic rules** (IN-05, MOD-10, A11Y-04, visual-level A11Y-05, DAX patterns) can produce false positives; the methodology tells the agent to confirm each one.
- **Adapters** for Tabular Editor BPA and Fab Inspector were written from documented formats and tested with synthetic samples only.
- Judgement findings depend on the agent and the model running it; the deterministic scanner does not.

## Repository layout

```
README.md  LICENSE  CHANGELOG.md  CONTRIBUTING.md  CODE_OF_CONDUCT.md  SECURITY.md
.github/   workflows/tests.yml, issue templates
examples/  sample Markdown and SARIF output from the synthetic defects fixture
skills/pbip-audit/
  SKILL.md                         entry point and workflow
  RECONNAISSANCE.md  FILE-MAP.md  VALIDATION-AND-REPORTING.md  CONFIGURATION.md
  MODEL.md  DAX.md  PERFORMANCE.md  GOVERNANCE-AND-AI-READINESS.md
  VISUAL-DESIGN.md  STORYTELLING.md  INTERACTION.md  ACCESSIBILITY.md  MOBILE.md
  domain-rules.example.md  pbip-audit.example.json  report-schema.json
  scripts/
    scan.py  validate_findings.py  render_catalog.py
    pbip_audit/  catalog, TMDL parser, PBIR loader, JSON locator, theme, schemas, checks, adapters, outputs
    tools/       refresh_schema_cache.py (maintainers, uses the network)
    tests/       unittest suite + synthetic fixtures
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Bug reports about false positives are especially welcome; please use the issue template and include only synthetic snippets.

## License

MIT, see [LICENSE](LICENSE).
