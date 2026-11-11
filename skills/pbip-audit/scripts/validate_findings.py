#!/usr/bin/env python3
"""Validate a findings JSON file against report-schema.json (stdlib only).

Usage:
    python validate_findings.py findings.json [--schema ../report-schema.json]

Implements the JSON Schema subset the schema uses: type (incl. type lists),
required, properties, additionalProperties (bool or schema), enum, pattern, minLength,
minimum, minItems, items, $ref to #/definitions/... . Also checks that
summary counts agree with the findings list, that finding ids are unique and
that a pillar scored as not assessed has no score (and an assessed one has one).

Exit code 0 when valid, 1 when invalid, 2 on usage/IO errors.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

DEFAULT_SCHEMA = Path(__file__).resolve().parent.parent / "report-schema.json"

_TYPES = {
    "object": dict, "array": list, "string": str, "boolean": bool, "null": type(None),
}


def _is_type(value: Any, t: str) -> bool:
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, _TYPES[t])


def validate(instance: Any, schema: Dict[str, Any], root: Dict[str, Any], path: str = "$") -> List[str]:
    errors: List[str] = []
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/"):
            return [f"{path}: unsupported $ref {ref}"]
        target: Any = root
        for part in ref[2:].split("/"):
            target = target[part]
        return validate(instance, target, root, path)
    t = schema.get("type")
    if t is not None:
        types = t if isinstance(t, list) else [t]
        if not any(_is_type(instance, x) for x in types):
            return [f"{path}: expected {t}, got {type(instance).__name__}"]
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: {instance!r} not in {schema['enum']}")
    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append(f"{path}: shorter than {schema['minLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append(f"{path}: {instance!r} does not match {schema['pattern']}")
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path}: {instance} < {schema['minimum']}")
    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path}: missing required property '{key}'")
        props = schema.get("properties", {})
        for key, value in instance.items():
            extra = schema.get("additionalProperties")
            if key in props:
                errors.extend(validate(value, props[key], root, f"{path}.{key}"))
            elif extra is False:
                errors.append(f"{path}: unexpected property '{key}'")
            elif isinstance(extra, dict):
                errors.extend(validate(value, extra, root, f"{path}.{key}"))
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(f"{path}: fewer than {schema['minItems']} items")
        if "items" in schema:
            for i, item in enumerate(instance):
                errors.extend(validate(item, schema["items"], root, f"{path}[{i}]"))
    return errors


def semantic_checks(doc: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    findings = doc.get("findings") or []
    if not isinstance(findings, list):
        return errors
    ids = [f.get("id") for f in findings if isinstance(f, dict)]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        errors.append(f"$.findings: duplicate ids {dupes}")
    for i, f in enumerate(findings):
        if isinstance(f, dict) and isinstance(f.get("id"), str) and isinstance(f.get("rule_id"), str):
            if not f["id"].startswith(f["rule_id"] + "#"):
                errors.append(f"$.findings[{i}]: id {f['id']} does not start with rule_id {f['rule_id']}")
    summary = doc.get("summary") or {}
    if isinstance(summary, dict):
        if summary.get("total") != len(findings):
            errors.append(f"$.summary.total: {summary.get('total')} != {len(findings)} findings")
        by_sev = summary.get("by_severity") or {}
        for sev, n in by_sev.items():
            actual = sum(1 for f in findings if isinstance(f, dict) and f.get("severity") == sev)
            if n != actual:
                errors.append(f"$.summary.by_severity.{sev}: {n} != {actual}")
    pillars = (doc.get("scores") or {}).get("pillars") if isinstance(doc.get("scores"), dict) else None
    if isinstance(pillars, dict):
        for name, row in sorted(pillars.items()):
            if not isinstance(row, dict) or "assessed" not in row:
                continue
            if row["assessed"] is False and row.get("score") is not None:
                errors.append(f"$.scores.pillars.{name}: not assessed but scored {row.get('score')}")
            if row["assessed"] is True and row.get("score") is None:
                errors.append(f"$.scores.pillars.{name}: assessed but score is null")
    return errors


def validate_file(path: Path, schema_path: Path = DEFAULT_SCHEMA) -> List[str]:
    schema = json.loads(schema_path.read_text(encoding="utf-8-sig"))
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    errors = validate(doc, schema, schema)
    if not errors:
        errors.extend(semantic_checks(doc))
    return errors


def main(argv: List[str] = None) -> int:
    ap = argparse.ArgumentParser(description="Validate a pbip-audit findings JSON file.")
    ap.add_argument("findings")
    ap.add_argument("--schema", default=str(DEFAULT_SCHEMA))
    args = ap.parse_args(argv)
    try:
        errors = validate_file(Path(args.findings), Path(args.schema))
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if errors:
        for e in errors:
            print(e)
        print(f"INVALID: {len(errors)} error(s)")
        return 1
    print("VALID")
    return 0


if __name__ == "__main__":
    sys.exit(main())
