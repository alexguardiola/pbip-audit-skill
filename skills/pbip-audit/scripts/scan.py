#!/usr/bin/env python3
"""pbip-audit scanner: deterministic (D) findings for a Power BI PBIP project.

Usage:
    python scan.py <path-to-.pbip-or-folder> [--format json|md|sarif] [--out FILE]
                   [--config FILE] [--max-visuals N] [--max-fields N] [--as-of-year YYYY]
                   [--tab-order-tolerance R] [--tab-order-row-band PX]
                   [--external-usage FILE] [--validate-schemas]
                   [--import-bpa FILE] [--import-fabinspector FILE]
                   [--path-prefix PREFIX] [--fail-on SEVERITY]

Reads files only and never uses the network. Never writes anything except ``--out``.
Python 3.8+ standard library only.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pbip_audit import __version__  # noqa: E402
from pbip_audit.adapters import ImportError_, import_bpa, import_fabinspector, renumber  # noqa: E402
from pbip_audit.catalog import BY_ID, PILLARS, RULES, SEVERITIES  # noqa: E402
from pbip_audit.checks import Options, apply_policy, run_checks  # noqa: E402
from pbip_audit.config import ConfigError, find_config, load_config, load_external_usage, page_name_patterns  # noqa: E402
from pbip_audit.output import scores, to_markdown, to_sarif  # noqa: E402
from pbip_audit.project import DiscoveryError, load_project  # noqa: E402

SCHEMA_VERSION = "1.1"


def build_result(path: Path, options: Options, imports: Optional[Dict[str, List[Path]]] = None,
                 config_path: Optional[str] = None, domain_rules: Optional[str] = None) -> Dict[str, Any]:
    project = load_project(path)
    findings, ctx = run_checks(project, options)
    r, m = project.report, project.model
    notes: List[str] = list(project.notes)

    def rel(p: Optional[Path]) -> Optional[str]:
        if p is None:
            return None
        try:
            return p.relative_to(project.base).as_posix()
        except ValueError:
            return p.name

    imported: List[Dict[str, Any]] = []
    for kind, files in (imports or {}).items():
        for f in files:
            try:
                if kind == "bpa":
                    imported += import_bpa(f, project, f.name)
                else:
                    imported += import_fabinspector(f, project, f.name)
            except (OSError, ImportError_) as exc:
                notes.append(f"could not import {kind} file {f.name}: {exc}")
    if imported:
        renumber(imported)
        findings = apply_policy(findings + imported, options)

    if r is not None:
        notes.extend(r.theme.notes)

    by_sev = Counter(f["severity"] for f in findings)
    by_pillar = Counter(f["pillar"] for f in findings)
    stats = {
        "pages": len(r.pages) if r else 0,
        "visuals": sum(len(p.visuals) for p in r.pages) if r else 0,
        "bookmarks": len(r.bookmarks) if r else 0,
        "report_field_references": len(ctx.report_refs()),
        "tables": len(m.tables) if m else 0,
        "columns": len(m.all_columns()) if m else 0,
        "measures": len(m.all_measures()) if m else 0,
        "relationships": len(m.relationships) if m else 0,
    }
    result: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "tool": {"name": "pbip-audit-scan", "version": __version__},
        "generated_at": _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat(),
        "target": {
            "pbip": project.pbip.name if project.pbip else None,
            "report_path": rel(project.report_dir),
            "model_path": rel(project.model_dir),
            "report_format": r.format if r else "none",
            "model_format": project.model_format,
            "thin_report": project.thin,
        },
        "options": dict(options.as_dict(), config=config_path, domain_rules=domain_rules,
                        imports={k: [p.name for p in v] for k, v in (imports or {}).items() if v}),
        "stats": stats,
        "summary": {
            "total": len(findings),
            "by_severity": {s: by_sev.get(s, 0) for s in SEVERITIES},
            "by_pillar": {p: by_pillar.get(p, 0) for p in list(PILLARS) + sorted(set(by_pillar) - set(PILLARS))},
        },
        "findings": findings,
        "not_assessable": [
            {"rule_id": rule.id, "title": rule.title, "pillar": rule.pillar, "reason": "Requires runtime or Service data; not assessable offline."}
            for rule in RULES if rule.check == "R"
        ],
    }
    if r is not None and r.format == "PBIR":
        th = r.theme
        result["theme"] = {"base": th.base_source, "custom": th.custom.rel if th.custom else None,
                           "background": th.background, "foreground": th.foreground,
                           "data_colors": th.data_colors[:8]}
    result["scores"] = scores(findings)
    if notes:
        result["notes"] = notes
    return result


def _options_from(args: argparse.Namespace, cfg: Dict[str, Any]) -> Options:
    th = dict(cfg.get("thresholds") or {})
    cli = {
        "max_visuals": args.max_visuals, "max_fields": args.max_fields, "as_of_year": args.as_of_year,
        "tab_order_tolerance": args.tab_order_tolerance, "tab_order_row_band": args.tab_order_row_band,
    }
    for k, v in cli.items():
        if v is not None:
            th[k] = v
    naming = cfg.get("naming") or {}
    o = Options(
        max_visuals=int(th.get("max_visuals", 12)),
        max_fields=int(th.get("max_fields", 20)),
        as_of_year=int(th.get("as_of_year", _dt.date.today().year)),
        page_name_patterns=page_name_patterns(naming.get("locales"), naming.get("extra_default_page_patterns")),
        tab_inversion_ratio=float(th.get("tab_order_tolerance", 0.4)),
        tab_row_band=float(th.get("tab_order_row_band", 40)),
        min_text_contrast=float(th.get("min_text_contrast", 4.5)),
        min_graphic_contrast=float(th.get("min_graphic_contrast", 3.0)),
        cvd_delta_e=float(th.get("cvd_delta_e", 10)),
        cvd_palette_size=int(th.get("cvd_palette_size", 8)),
        validate_schemas=bool(args.validate_schemas),
    )
    disabled = set(cfg.get("disabled_rules") or [])
    unknown = sorted(d for d in disabled if d not in BY_ID)
    if unknown:
        raise ConfigError(f"disabled_rules: unknown rule id(s) {unknown}")
    o.disabled_rules = disabled
    overrides = dict(cfg.get("severity_overrides") or {})
    for rid, sev in overrides.items():
        if rid not in BY_ID or sev not in SEVERITIES:
            raise ConfigError(f"severity_overrides: bad entry {rid!r}: {sev!r}")
    o.severity_overrides = overrides
    return o


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Offline deterministic audit of a Power BI PBIP project.")
    ap.add_argument("path", help="Path to a .pbip file or a folder containing one")
    ap.add_argument("--format", choices=["json", "md", "sarif"], default="json")
    ap.add_argument("--out", help="Write output to this file instead of stdout")
    ap.add_argument("--config", help="Config file (default: nearest .pbip-audit.json at or above the project)")
    ap.add_argument("--no-config", action="store_true", help="Ignore any .pbip-audit.json")
    ap.add_argument("--max-visuals", type=int, help="PERF-01 threshold (data-bound visuals per page, default 12)")
    ap.add_argument("--max-fields", type=int, help="PERF-02 threshold (fields per visual, default 20)")
    ap.add_argument("--as-of-year", type=int, help="Current year for IN-13 (default: today)")
    ap.add_argument("--tab-order-tolerance", type=float, help="A11Y-04: share of inverted visual pairs tolerated (default 0.4)")
    ap.add_argument("--tab-order-row-band", type=float, help="A11Y-04: px within which visuals count as one row (default 40)")
    ap.add_argument("--external-usage", help="MOD-10 allowlist: objects used outside this report ('Table'[Object] per line, or a JSON list)")
    ap.add_argument("--validate-schemas", action="store_true", help="Check each PBIR file against the cached top-level shape of its declared $schema")
    ap.add_argument("--import-bpa", action="append", default=[], help="Tabular Editor BPA results to merge (repeatable)")
    ap.add_argument("--import-fabinspector", action="append", default=[], help="Fab Inspector JSON results to merge (repeatable)")
    ap.add_argument("--path-prefix", default="", help="SARIF: prefix for evidence paths so they are relative to the repository root")
    ap.add_argument("--fail-on", choices=SEVERITIES, help="Exit with code 2 when a finding at or above this severity exists")
    args = ap.parse_args(argv)

    target = Path(args.path)
    cfg: Dict[str, Any] = {}
    cfg_path: Optional[Path] = None
    try:
        if args.config:
            cfg_path = Path(args.config)
        elif not args.no_config and target.exists():
            cfg_path = find_config(target)
        if cfg_path is not None:
            cfg = load_config(cfg_path)
        opts = _options_from(args, cfg)
        usage = args.external_usage
        if usage is None and cfg.get("external_usage") and cfg_path is not None:
            usage = str(cfg_path.parent / cfg["external_usage"]) if not Path(cfg["external_usage"]).is_absolute() else cfg["external_usage"]
        if usage:
            up = Path(usage)
            opts.external_usage = load_external_usage(up)
            opts.external_usage_source = up.name
        domain = cfg.get("domain_rules")
        if domain and cfg_path is not None:
            dp = Path(domain) if Path(domain).is_absolute() else cfg_path.parent / domain
            domain = Path(domain).as_posix() + ("" if dp.exists() else " (not found)")
        result = build_result(target, opts,
                              {"bpa": [Path(p) for p in args.import_bpa], "fabinspector": [Path(p) for p in args.import_fabinspector]},
                              config_path=cfg_path.name if cfg_path else None, domain_rules=domain)
    except (ConfigError, DiscoveryError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.format == "json":
        text = json.dumps(result, indent=2, ensure_ascii=False)
    elif args.format == "sarif":
        text = json.dumps(to_sarif(result, args.path_prefix), indent=2, ensure_ascii=False)
    else:
        text = to_markdown(result)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    else:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        print(text)
    if args.fail_on:
        limit = SEVERITIES.index(args.fail_on)
        if any(SEVERITIES.index(f["severity"]) <= limit for f in result["findings"] if f.get("status") != "false_positive"):
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
