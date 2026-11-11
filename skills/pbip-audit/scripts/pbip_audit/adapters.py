"""Import results from other analyzers into the findings schema.

* ``--import-bpa FILE``: Tabular Editor Best Practice Analyzer results, as
  - Tabular Editor 2 CLI console output (``-A``; plain, ``-G`` GitHub or ``-V``
    Azure DevOps annotation lines: ``<Type> '<Object>' violates rule "<Rule>"``), or
  - JSON: a list of records (or ``{"results": [...]}``) with keys such as
    ``Rule Name``/``RuleName``, ``Object Name``/``ObjectName``, ``Object Type``,
    ``Category``, ``Severity``, ``Description``, ``URL`` (the column names of
    semantic-link-labs ``run_model_bpa`` exported with ``DataFrame.to_json(orient="records")``).
* ``--import-fabinspector FILE``: Fab Inspector / PBI Inspector JSON results, a
  list of records (or under ``Results``/``TestResults``) with ``RuleId``,
  ``RuleName``, ``RuleDescription``, ``Pass``, ``LogType``, ``ItemPath``,
  ``Expected``, ``Actual``. Only records with ``Pass: false`` are imported.

Key lookup is case- and punctuation-insensitive so minor format drift between
tool versions does not break the import. The mapping was written against the
documented formats and tested with synthetic files only; see the README.

Imported findings use rule ``EXT-01`` (BPA) or ``EXT-02`` (Fab Inspector), keep
the original rule in ``origin``, and never claim more than the source tool says.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .catalog import BY_ID

BPA_LINE_RE = re.compile(
    r"^(?:##vso\[task\.logissue type=(?P<vso>\w+);?\]|::(?P<gh>warning|error|notice)[^:]*::)?\s*"
    r"(?P<otype>[A-Za-z][A-Za-z ]*?)\s+(?P<obj>'(?:[^']|'')*'(?:\[[^\]]+\])?|\S+)\s+violates rule\s+\"(?P<rule>[^\"]+)\"",
)

BPA_CATEGORY_PILLAR = {
    "performance": "performance", "dax expressions": "dax", "dax": "dax", "error prevention": "model",
    "formatting": "governance", "maintenance": "governance", "naming conventions": "governance",
    "naming": "governance", "model layout": "model",
}

FI_PILLAR_HINTS = [
    ("ALTTEXT", "accessibility"), ("ALT_TEXT", "accessibility"), ("CONTRAST", "accessibility"),
    ("COLOUR", "visual-design"), ("COLOR", "visual-design"), ("THEME", "visual-design"),
    ("VISUALS_ON_PAGE", "performance"), ("OBJECTS_WITHIN", "performance"), ("TOPN", "performance"),
    ("ADVANCED_FILTERS", "performance"), ("CUSTOM_VISUAL", "governance"),
    ("TOOLTIP", "interaction"), ("DRILL", "interaction"), ("SLICER", "interaction"),
    ("PAGES", "storytelling"), ("SCROLL", "visual-design"), ("MOBILE", "mobile"),
]


class ImportError_(ValueError):
    pass


def _norm(key: str) -> str:
    return re.sub(r"[^a-z0-9]", "", key.lower())


def _get(rec: Dict[str, Any], *names: str) -> Any:
    idx = {_norm(k): v for k, v in rec.items()}
    for n in names:
        v = idx.get(_norm(n))
        if v not in (None, ""):
            return v
    return None


def _records(data: Any, keys: Tuple[str, ...]) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    if isinstance(data, dict):
        idx = {_norm(k): v for k, v in data.items()}
        for k in keys:
            v = idx.get(_norm(k))
            if isinstance(v, list):
                return [r for r in v if isinstance(r, dict)]
    raise ImportError_("no list of result records found")


def _bpa_severity(raw: Any) -> str:
    s = str(raw or "").strip().lower()
    if s in ("3", "error", "❌", "high"):
        return "Medium"
    if s in ("2", "warning", "⚠️", "⚠", "medium"):
        return "Low"
    return "Info"


def _fi_severity(raw: Any) -> str:
    s = str(raw or "").strip().lower()
    if s == "error":
        return "Medium"
    if s == "warning":
        return "Low"
    return "Info"


def _parse_object(obj: str) -> Tuple[Optional[str], Optional[str]]:
    """``'Sales'[Amount]`` -> (Sales, Amount); ``'Sales'`` -> (Sales, None); ``Sales.Amount`` -> (Sales, Amount)."""
    obj = obj.strip()
    m = re.match(r"^'((?:[^']|'')*)'(?:\[(.+)\])?$", obj)
    if m:
        return m.group(1).replace("''", "'"), m.group(2)
    m = re.match(r"^([^\[\].]+)\[(.+)\]$", obj)
    if m:
        return m.group(1).strip(), m.group(2)
    if "." in obj:
        t, o = obj.split(".", 1)
        return t.strip("'"), o.strip("[]")
    return obj.strip("'[]") or None, None


def parse_bpa(path: Path) -> List[Dict[str, Any]]:
    """Return neutral records: rule, object, object_type, category, severity, description, url."""
    raw = path.read_text(encoding="utf-8-sig")
    out: List[Dict[str, Any]] = []
    try:
        data = json.loads(raw)
    except ValueError:
        data = None
    if data is not None:
        for rec in _records(data, ("results", "violations", "items", "data")):
            rule = _get(rec, "Rule Name", "RuleName", "Rule", "RuleId", "RuleID")
            if not rule:
                continue
            obj = _get(rec, "Object Name", "ObjectName", "Object", "Name")
            table = _get(rec, "Table Name", "TableName", "Table")
            if table and obj and "[" not in str(obj) and str(obj) != str(table):
                obj = f"'{table}'[{obj}]"
            out.append({
                "rule": str(rule), "rule_id": str(_get(rec, "RuleId", "RuleID", "ID") or rule),
                "object": str(obj or ""), "object_type": str(_get(rec, "Object Type", "ObjectType", "Type") or ""),
                "category": str(_get(rec, "Category") or ""), "severity": _bpa_severity(_get(rec, "Severity")),
                "description": str(_get(rec, "Description") or ""), "url": str(_get(rec, "URL", "Url", "Link") or ""),
            })
        return out
    for line in raw.splitlines():
        m = BPA_LINE_RE.search(line.strip())
        if not m:
            continue
        level = (m.group("vso") or m.group("gh") or "").lower()
        out.append({
            "rule": m.group("rule"), "rule_id": m.group("rule"), "object": m.group("obj"),
            "object_type": m.group("otype").strip(), "category": "",
            "severity": "Medium" if level == "error" else ("Low" if level == "warning" else "Info"),
            "description": "", "url": "",
        })
    if not out and raw.strip():
        raise ImportError_("no BPA violations recognised (expected JSON records or 'violates rule' lines)")
    return out


def parse_fabinspector(path: Path) -> List[Dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except ValueError as exc:
        raise ImportError_(f"not JSON: {exc}")
    out: List[Dict[str, Any]] = []
    for rec in _records(data, ("Results", "TestResults", "results", "testResults")):
        passed = _get(rec, "Pass", "Passed", "Result")
        if passed is True or str(passed).lower() in ("true", "pass", "passed"):
            continue
        rid = _get(rec, "RuleId", "RuleID", "Id")
        name = _get(rec, "RuleName", "Name") or rid
        if not (rid or name):
            continue
        out.append({
            "rule_id": str(rid or name), "rule": str(name), "description": str(_get(rec, "RuleDescription", "Description", "Message") or ""),
            "severity": _fi_severity(_get(rec, "LogType", "Severity", "Level")),
            "item": str(_get(rec, "ItemPath", "Path", "FilePath", "ParentDisplayName", "ParentName", "ItemName") or ""),
            "expected": _get(rec, "Expected"), "actual": _get(rec, "Actual"),
        })
    return out


def _locate(model, obj: str) -> Tuple[Optional[str], Optional[int]]:
    if model is None or not obj:
        return None, None
    table, member = _parse_object(obj)
    if not table:
        return None, None
    t = model.table(table)
    if t is None:
        return None, None
    if member:
        key = member.lower()
        o = t.measures.get(key) or t.columns.get(key) or None
        if o is not None:
            return o.file, o.line
    return t.file, t.line


def ext_finding(rule_id: str, pillar: str, severity: str, message: str, evidence: List[Dict[str, Any]],
                origin: Dict[str, Any], fix: str = "", source: str = "") -> Dict[str, Any]:
    rule = BY_ID[rule_id]
    f: Dict[str, Any] = {
        "id": f"{rule_id}#0", "rule_id": rule_id, "title": rule.title, "pillar": pillar, "severity": severity,
        "check_type": "D", "confidence": "medium", "classification": rule.kind, "message": message,
        "evidence": evidence, "fix": fix or rule.fix, "source": source or rule.source, "origin": origin,
    }
    return f


def import_bpa(path: Path, project, rel_name: str) -> List[Dict[str, Any]]:
    out = []
    for rec in parse_bpa(path):
        file, line = _locate(project.model, rec["object"])
        evidence = {"file": file or rel_name, "detail": f"{rec['object_type']} {rec['object']}".strip()[:200]}
        if line:
            evidence["line"] = line
        pillar = BPA_CATEGORY_PILLAR.get(rec["category"].strip().lower(), "model")
        msg = f"Tabular Editor BPA: {rec['object_type'] or 'object'} {rec['object'] or '(model)'} violates \"{rec['rule']}\"."
        if rec["description"]:
            msg += f" {rec['description']}"
        out.append(ext_finding("EXT-01", pillar, rec["severity"], msg, [evidence],
                               {"tool": "Tabular Editor BPA", "rule_id": rec["rule_id"], "rule": rec["rule"], "file": rel_name},
                               source=rec["url"] if rec["url"].startswith("https://") else ""))
    return out


def import_fabinspector(path: Path, project, rel_name: str) -> List[Dict[str, Any]]:
    out = []
    base = project.base
    for rec in parse_fabinspector(path):
        item = rec["item"]
        file = None
        if item:
            cand = item.replace("\\", "/")
            for root in (base, base.parent):
                try:
                    p = (root / cand).resolve()
                    if p.exists():
                        file = p.relative_to(base).as_posix()
                        break
                except (ValueError, OSError):
                    continue
        evidence = {"file": file or rel_name}
        detail = item or rec["rule_id"]
        if rec["actual"] is not None:
            detail += f" (actual {json.dumps(rec['actual'])[:80]}, expected {json.dumps(rec['expected'])[:80]})"
        evidence["detail"] = detail[:300]
        upper = rec["rule_id"].upper()
        pillar = next((p for hint, p in FI_PILLAR_HINTS if hint in upper), "visual-design")
        msg = f"Fab Inspector: rule {rec['rule_id']} failed" + (f" ({rec['rule']})" if rec["rule"] != rec["rule_id"] else "") + "."
        if rec["description"]:
            msg += f" {rec['description']}"
        out.append(ext_finding("EXT-02", pillar, rec["severity"], msg, [evidence],
                               {"tool": "Fab Inspector", "rule_id": rec["rule_id"], "rule": rec["rule"], "file": rel_name}))
    return out


def renumber(findings: Iterable[Dict[str, Any]]) -> None:
    counter: Dict[str, int] = {}
    for f in findings:
        if f["id"].endswith("#0"):
            counter[f["rule_id"]] = counter.get(f["rule_id"], 0) + 1
            f["id"] = f"{f['rule_id']}#{counter[f['rule_id']]}"
