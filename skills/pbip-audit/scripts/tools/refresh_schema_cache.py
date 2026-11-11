#!/usr/bin/env python3
"""Maintainer tool: refresh ``pbip_audit/schema_cache.json`` from Microsoft's schema site.

    python refresh_schema_cache.py [--kinds visualContainer,page] [--max-minor 30]

Only the kinds probed are updated (their versions are added or replaced); every
other kind already in the cache is kept, so a partial ``--kinds`` run is safe.

This is the only script in the repository that uses the network. ``scan.py``
never does: ``--validate-schemas`` reads the cache only. For each schema kind it
probes versions ``<major>.<minor>.0`` and keeps the top-level shape (required
properties, allowed properties, ``additionalProperties``, oneOf required sets).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

CACHE = Path(__file__).resolve().parent.parent / "pbip_audit" / "schema_cache.json"
BASE = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/{kind}/{version}/schema.json"
# definition.pbir declares its schema outside the /definition/ folder of the report item
BASE_BY_KIND = {
    "definitionProperties": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/{version}/schema.json",
}
KINDS = {
    "visualContainer": (1, 2), "page": (1, 2), "report": (1, 3), "bookmark": (1, 2),
    "pagesMetadata": (1, 1), "versionMetadata": (1, 1), "bookmarksMetadata": (1, 1),
    "reportExtension": (1, 1), "visualContainerMobileState": (1, 2), "definitionProperties": (1, 2),
}


def shape(d: dict) -> dict:
    entry = {"required": d.get("required", []), "properties": sorted(d.get("properties", {})),
             "additionalProperties": d.get("additionalProperties", True)}
    alts = [s.get("required") for s in (d.get("oneOf") or d.get("anyOf") or []) if isinstance(s, dict) and s.get("required")]
    if alts:
        entry["oneOfRequired"] = alts
    return entry


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kinds", default=",".join(KINDS))
    ap.add_argument("--max-minor", type=int, default=30)
    args = ap.parse_args(argv)
    schemas = {}
    for kind in args.kinds.split(","):
        lo, hi = KINDS.get(kind, (1, 3))
        for major in range(lo, hi + 1):
            for minor in range(0, args.max_minor + 1):
                version = f"{major}.{minor}.0"
                try:
                    url = BASE_BY_KIND.get(kind, BASE).format(kind=kind, version=version)
                    with urllib.request.urlopen(url, timeout=20) as r:
                        d = json.load(r)
                except (urllib.error.URLError, ValueError, OSError):
                    continue
                schemas.setdefault(kind, {})[version] = shape(d)
                print("cached", kind, version)
    doc = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    merged = doc.get("schemas") or {}
    for kind, versions in schemas.items():
        merged.setdefault(kind, {}).update(versions)
    doc["schemas"] = merged
    doc["_fetched"] = _dt.date.today().isoformat()
    CACHE.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
