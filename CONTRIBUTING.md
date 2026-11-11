# Contributing

Thanks for helping. The most valuable contributions are **false-positive reports** with a minimal synthetic example, and **new rules** with a clear source.

## Ground rules

- **Synthetic data only.** Never commit files from a real project, real table or measure names from a client, hosts, connection strings, screenshots of real reports or real data. Fixtures are built by `build_fixtures.py` from invented names.
- **Standard library only**, Python 3.8 compatible. No `pip install` for users. Use `pathlib`, read text as UTF-8 with BOM tolerance, keep Windows and Linux working.
- **The scanner reads files only.** No network access, no writes except `--out`. The single network script is `scripts/tools/refresh_schema_cache.py`, for maintainers.
- **English** in code, docs and rule text.

## Development setup

```bash
git clone https://github.com/alexguardiola/pbip-audit-skill.git
cd pbip-audit-skill
python -m unittest discover -s skills/pbip-audit/scripts/tests
```

That is the whole setup. CI runs the same command on Python 3.8 and 3.12, on Ubuntu and Windows.

## Adding a rule

Every rule lives in one place, `skills/pbip-audit/scripts/pbip_audit/catalog.py`. Docs, tests and outputs are derived from it.

1. **Catalog entry.** Add `R("PILLAR-NN", pillar, severity, check, title, rationale, verify, fix, source, implemented=..., kind=...)`.
   - `check`: `D` (the scanner can decide from files), `J` (the agent judges with evidence), `R` (needs runtime data).
   - `source`: an `https://` link to Microsoft Learn, WCAG, or another primary source. No source, no rule.
   - `kind`: `defect` only when the current state is objectively broken or wrong; otherwise `recommendation`.
   - Pick the severity with the rubric in `SKILL.md`. Prefer the lower severity when unsure.
2. **Check (D rules).** Implement it in `scripts/pbip_audit/checks.py` (or a module it calls) as a generator that yields `ctx.finding("PILLAR-NN", message, evidence, ...)`, and add the function to `ALL_CHECKS` if it is new. Then set `implemented=True` in the catalog.
   - Evidence: `ev(file, line, json_path, detail)`. For JSON use `jsonfile.line_at(path_tuple)` so the line points at the exact node; for TMDL use the object's `file` and `line`.
   - Aggregate per root cause (per page, per table), not one finding per location.
   - Say in the message what a reader would see, not only what the file contains.
   - Heuristic? Use `confidence="medium"` or `"low"` and document the false-positive cases in the rule's `verify` text.
3. **Seeded fixture.** Add the smallest defect that triggers the rule to `build_defects()` in `scripts/tests/fixtures/build_fixtures.py`, and make sure the `clean` project still produces no findings. Regenerate:

   ```bash
   python skills/pbip-audit/scripts/tests/fixtures/build_fixtures.py
   ```

4. **Test.** Assert the finding (rule, severity, a key word of the message, the evidence file and line) in `scripts/tests/test_scan.py` or `test_features.py`. Add a negative test for the main false-positive case you thought of.
5. **Regenerate the docs.**

   ```bash
   python skills/pbip-audit/scripts/render_catalog.py
   ```

6. **Run the tests.** The suite fails if a rule is emitted but not declared, declared as implemented but never triggered by a fixture, or if the pillar docs drift from the catalog.
7. **Changelog.** Add a line under `Unreleased` in `CHANGELOG.md`.

J and R rules need steps 1, 5 and 7 only.

## Reporting a false positive

Use the "False positive" issue template. Include the rule ID, scanner version, a **minimal synthetic** snippet (a few lines of `visual.json` or TMDL with invented names), what the scanner said, and why it is wrong. Do not attach real project files.

## Pull requests

- One topic per pull request; keep it reviewable.
- Conventional commit messages (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`).
- Tests and regenerated docs in the same pull request as the code.
- By contributing you agree to license your work under the MIT license and to follow the [Code of Conduct](CODE_OF_CONDUCT.md).
