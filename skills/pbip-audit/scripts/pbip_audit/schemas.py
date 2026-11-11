"""Lightweight PBIR schema validation against a local cache (no network, no jsonschema).

Each PBIR JSON file declares ``$schema`` as
``.../item/report/definition/<kind>/<version>/schema.json``, except
``definition.pbir``, which declares ``.../item/report/definitionProperties/<version>/schema.json``
(kind ``definitionProperties``, no ``/definition/`` segment). The cache
(``schema_cache.json``) stores the top-level shape of Microsoft's published
schemas: required properties, allowed properties and oneOf required sets. That
catches the common breakages (a file without ``name`` or ``position``, a
misspelled top-level key, a hand-edited file missing ``displayOption``) without
shipping or downloading the full schemas.

Files whose kind/version is not in the cache are reported as "schema not
checked"; they are never guessed against another version.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

CACHE_PATH = Path(__file__).resolve().parent / "schema_cache.json"
SCHEMA_URL_RE = re.compile(
    r"/item/report/(?:definition/(?P<kind>[A-Za-z]+)|(?P<props>definitionProperties))/(?P<version>\d+\.\d+\.\d+)/schema\.json$")

_cache: Optional[Dict[str, Any]] = None


def load_cache(path: Path = CACHE_PATH) -> Dict[str, Any]:
    global _cache
    if path == CACHE_PATH and _cache is not None:
        return _cache
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        schemas = doc.get("schemas") or {}
    except (OSError, ValueError):
        schemas = {}
    if path == CACHE_PATH:
        _cache = schemas
    return schemas


def parse_schema_url(url: Optional[str]) -> Optional[Tuple[str, str]]:
    if not url:
        return None
    m = SCHEMA_URL_RE.search(url)
    return (m.group("kind") or m.group("props"), m.group("version")) if m else None


def check_document(data: Any, kind: str, version: str, cache: Dict[str, Any]) -> Optional[List[Tuple[str, str]]]:
    """Return a list of (problem, property) or None when the schema is not cached."""
    entry = (cache.get(kind) or {}).get(version)
    if entry is None:
        return None
    if not isinstance(data, dict):
        return [("top level is not an object", "$")]
    problems: List[Tuple[str, str]] = []
    for key in entry.get("required") or []:
        if key not in data:
            problems.append(("missing required property", key))
    alts = entry.get("oneOfRequired") or []
    if alts and not any(all(k in data for k in alt) for alt in alts):
        problems.append(("missing one of", " | ".join("+".join(a) for a in alts)))
    if entry.get("additionalProperties") is False:
        allowed = set(entry.get("properties") or [])
        for key in data:
            if key not in allowed:
                problems.append(("property not allowed by the schema", key))
    return problems
