# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- **Claude Code plugin.** `/plugin marketplace add alexguardiola/pbip-audit-skill` then `/plugin install pbip-audit@pbip-audit-skill` installs the skill; manifests in `.claude-plugin/`.
- **Installable CLI.** `pipx install git+https://github.com/alexguardiola/pbip-audit-skill` gives a `pbip-audit` command (still no runtime dependencies); `python -m pbip_audit` works from `scripts/`. New `--version` flag.

### Changed

- The scanner's command line moved from `scripts/scan.py` into `pbip_audit/cli.py`; `scan.py` is now a thin wrapper and keeps the same options, output and exit codes.

## 0.2.0 - 2026-11-10 (pre-release, not published)

### Added

- **Exact evidence lines.** A small line-tracking JSON locator (`pbip_audit/jsonloc.py`) maps every node to its line, so evidence points at the actual `syncGroup`, filter, field, `tabOrder` or colour property instead of the first line containing the key.
- **Theme resolution.** Base and custom themes are loaded from `StaticResources` via `report.json` (`themeCollection`, `resourcePackages`), with `visualStyles` merged and a built-in default palette when the base theme file is absent. `ThemeDataColor` references (ColorId, Percent) are resolved.
- **A11Y-05 is now deterministic**: WCAG 2.2 relative-luminance contrast for theme text colours, text colours in visuals (against the visual, button fill, label box, page or theme background; skipped when unknowable), and custom-theme series colours (3:1, Medium).
- **A11Y-07** (new): series colours confusable under protanopia/deuteranopia (Machado et al. 2009 simulation, CIELAB delta E).
- **Opt-in schema validation** `--validate-schemas`: each PBIR file is checked against the cached top-level shape of its declared schema version. New rules **GOV-17** (file does not match its schema) and **GOV-18** (schema version not in the cache, Info). No network access; maintainers refresh the cache with `scripts/tools/refresh_schema_cache.py`.
- **Config file** `.pbip-audit.json` (found at or above the project, or `--config`): thresholds, disabled rules, severity overrides (recorded as `original_severity`), naming locales and extra default-page patterns, domain-rules path, external-usage file. Documented in `CONFIGURATION.md`.
- **MOD-10 allowlist** `--external-usage FILE` for objects used by other reports or tools on the same model.
- **A11Y-04** tolerance and row band are configurable (`--tab-order-tolerance`, `--tab-order-row-band`).
- **Markdown report** with executive summary, score per pillar (formula printed and documented), findings grouped by severity then pillar, and a "Not assessable offline" section.
- **SARIF 2.1.0 output** (`--format sarif`, `--path-prefix`) for GitHub code scanning.
- **Adapters**: `--import-bpa` (Tabular Editor 2 CLI output or BPA JSON records) and `--import-fabinspector` (Fab Inspector JSON results) map into the findings schema as **EXT-01** / **EXT-02** with an `origin` block.
- Repository hygiene: CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, GitHub Actions (Python 3.8 and 3.12 on Ubuntu and Windows), issue templates, `examples/`.

### Changed

- **IN-05** also accepts window wording in the measure name, display name or measure description (`L12M`, `R3M`, `last 6 months`, `rolling`, `trailing 3`...), so documented rolling measures are no longer reported.
- **VD-06** compares literals with the resolved theme: Low for colours outside the theme, Info when every literal equals a theme colour.
- **MOD-10** messages say that other reports may use the objects, unless an external-usage list was given.
- **ST-01** default-name patterns are grouped by locale (en, es, de, fr, pt, it, nl); en, es and de are on by default.
- Findings JSON `schema_version` 1.1: optional `original_severity`, `origin`, top-level `scores`, `theme`, `notes`.
- SKILL.md rewritten around explicit ground rules (read-only unless asked), the J-rule evidence method, false-positive discipline and how to present results.

## 0.1.0 - 2026-11-10 (pre-release, not published)

### Added

- First release: 74-rule catalog across nine pillars (42 deterministic, 27 judgement, 5 runtime), stdlib scanner for TMDL + PBIR with report-to-model binding index, findings schema and validator, pillar reference files generated from the catalog, synthetic fixtures and tests.

[Unreleased]: https://github.com/alexguardiola/pbip-audit-skill/compare/v0.3.0...HEAD
