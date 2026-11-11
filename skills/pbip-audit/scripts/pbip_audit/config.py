"""Configuration file (``.pbip-audit.json``) and external-usage allowlist.

Lookup order for the config file: ``--config PATH`` if given, otherwise
``.pbip-audit.json`` in the folder that holds the ``.pbip``, then in its parent
folders up to the filesystem root (so one file at a repository root covers every
project in it). Command-line options win over the file.

Schema (every key optional)::

    {
      "thresholds": {
        "max_visuals": 12, "max_fields": 20, "as_of_year": 2026,
        "tab_order_tolerance": 0.4, "tab_order_row_band": 40,
        "min_text_contrast": 4.5, "min_graphic_contrast": 3.0,
        "cvd_delta_e": 10, "cvd_palette_size": 8
      },
      "disabled_rules": ["MOB-01"],
      "severity_overrides": {"MOD-10": "Info"},
      "naming": {
        "locales": ["en", "es", "de"],
        "extra_default_page_patterns": ["^Sheet \\\\d+$"]
      },
      "domain_rules": "docs/domain-rules.md",
      "external_usage": "model-usage.txt"
    }
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

CONFIG_NAME = ".pbip-audit.json"

PAGE_NAME_PATTERNS_BY_LOCALE: Dict[str, List[str]] = {
    "en": [r"^Page \d+$", r"^Page \d+ \(\d+\)$", r"^Duplicate of\b", r"^Copy of\b"],
    "es": [r"^P[aá]gina \d+$", r"^Copia de\b", r"^Duplicado de\b"],
    "de": [r"^Seite \d+$", r"^Kopie von\b", r"^Duplikat von\b"],
    "fr": [r"^Page \d+$", r"^Copie de\b", r"^Dupliquer\b"],
    "pt": [r"^P[aá]gina \d+$", r"^C[oó]pia de\b", r"^Duplicado de\b"],
    "it": [r"^Pagina \d+$", r"^Copia di\b", r"^Duplicato di\b"],
    "nl": [r"^Pagina \d+$", r"^Kopie van\b", r"^Duplicaat van\b"],
}
DEFAULT_LOCALES = ["en", "es", "de"]

THRESHOLD_KEYS = {
    "max_visuals": int, "max_fields": int, "as_of_year": int,
    "tab_order_tolerance": float, "tab_order_row_band": float,
    "min_text_contrast": float, "min_graphic_contrast": float,
    "cvd_delta_e": float, "cvd_palette_size": int,
}
TOP_KEYS = {"thresholds", "disabled_rules", "severity_overrides", "naming", "domain_rules", "external_usage", "$schema"}


class ConfigError(ValueError):
    pass


def page_name_patterns(locales: Optional[List[str]], extra: Optional[List[str]] = None) -> List[str]:
    out: List[str] = []
    for loc in locales or DEFAULT_LOCALES:
        for p in PAGE_NAME_PATTERNS_BY_LOCALE.get(loc.lower().split("-")[0], []):
            if p not in out:
                out.append(p)
    for p in extra or []:
        re.compile(p)  # raises re.error early
        out.append(p)
    return out


def find_config(start: Path) -> Optional[Path]:
    cur = start.resolve()
    if cur.is_file():
        cur = cur.parent
    for folder in [cur] + list(cur.parents):
        cand = folder / CONFIG_NAME
        if cand.is_file():
            return cand
    return None


def load_config(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise ConfigError(f"cannot read {path}: {exc}")
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: top level must be an object")
    unknown = set(data) - TOP_KEYS
    if unknown:
        raise ConfigError(f"{path}: unknown key(s) {sorted(unknown)}")
    th = data.get("thresholds") or {}
    if not isinstance(th, dict):
        raise ConfigError(f"{path}: thresholds must be an object")
    for k, v in th.items():
        if k not in THRESHOLD_KEYS:
            raise ConfigError(f"{path}: unknown threshold '{k}'")
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            raise ConfigError(f"{path}: threshold '{k}' must be a number")
    if not isinstance(data.get("disabled_rules", []), list):
        raise ConfigError(f"{path}: disabled_rules must be a list")
    if not isinstance(data.get("severity_overrides", {}), dict):
        raise ConfigError(f"{path}: severity_overrides must be an object")
    naming = data.get("naming") or {}
    if not isinstance(naming, dict):
        raise ConfigError(f"{path}: naming must be an object")
    try:
        page_name_patterns(naming.get("locales"), naming.get("extra_default_page_patterns"))
    except re.error as exc:
        raise ConfigError(f"{path}: bad regular expression in naming: {exc}")
    data["_path"] = str(path)
    return data


_REF_RES = [
    re.compile(r"^'(?P<t>(?:[^']|'')+)'\s*\[(?P<o>[^\]]+)\]$"),
    re.compile(r"^(?P<t>[^\[\]]+?)\s*\[(?P<o>[^\]]+)\]$"),
    re.compile(r"^(?P<t>[^.]+)\.(?P<o>.+)$"),
]


def parse_object_ref(text: str) -> Optional[Tuple[str, str]]:
    """``'Table'[Object]``, ``Table[Object]`` or ``Table.Object`` -> (table, object) lower-cased."""
    s = text.strip()
    for rx in _REF_RES:
        m = rx.match(s)
        if m:
            return m.group("t").replace("''", "'").strip().lower(), m.group("o").strip().lower()
    return None


def load_external_usage(path: Path) -> Set[Tuple[str, str]]:
    """Objects used outside this report (other reports, Excel, paginated...).

    Accepts a JSON list of strings, a JSON object ``{"objects": [...]}``, or a
    text file with one reference per line (``#`` starts a comment).
    """
    raw = path.read_text(encoding="utf-8-sig")
    items: List[str]
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            data = data.get("objects", [])
        items = [x for x in data if isinstance(x, str)] if isinstance(data, list) else []
    except ValueError:
        items = [ln.split("#", 1)[0] for ln in raw.splitlines()]
    out: Set[Tuple[str, str]] = set()
    for it in items:
        if it.strip():
            ref = parse_object_ref(it)
            if ref:
                out.add(ref)
    return out
