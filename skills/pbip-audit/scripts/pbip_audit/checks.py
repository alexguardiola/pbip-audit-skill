"""Deterministic (D) checks.

Each check is a function ``check_xxx(ctx)`` that yields finding dicts built with
``ctx.finding(...)``. Rule metadata (pillar, default severity, title, source)
comes from ``catalog.RULES``; a check may only emit rule IDs that are declared
there with ``implemented=True`` (enforced by the tests).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple

from .catalog import BY_ID
from .config import DEFAULT_LOCALES, page_name_patterns
from .jsonloc import PathT, format_path, parse_path, walk
from .pbir import DECORATIVE_TYPES, FieldRef, JsonFile, Page, Report, Visual, collect_refs
from .project import Project
from .schemas import check_document, load_cache, parse_schema_url
from .theme import Theme, confusable_pairs, contrast_ratio, normalize_hex, style_props, theme_line
from .tmdl import SemanticModel, Table

MAX_EVIDENCE = 25

DEFAULT_PAGE_NAME_PATTERNS = page_name_patterns(DEFAULT_LOCALES)

SLICER_TYPES = {"slicer", "advancedSlicerVisual", "listSlicer", "textSlicer"}

WINDOW_WORDS_RE = re.compile(
    r"(\blast\b|\brolling\b|\btrailing\b|\bttm\b|\bltm\b|\br12\b|\bytd\b|\bmtd\b|\bqtd\b|\bwtd\b|"
    r"to date|\btoday\b|\bcurrent\b|\bthis (year|month|week|quarter)\b|\bprevious\b|\bprior\b|"
    r"\bnext\b|\bwindow\b|\bsince\b|\bmoving\b|\b[lrt]\d+[dwmqy]\b|"
    r"\b(last|past|trailing|rolling)\s+(\d+|n|one|two|three|six|twelve)\b|"
    r"\b[uú]ltim[oa]s?\b|\bletzte[nr]?\b|"
    r"\b\d+\s*(d|w|m|q|y|days?|weeks?|months?|quarters?|years?|yrs?)\b)",
    re.IGNORECASE,
)
TODAY_RE = re.compile(r"\b(TODAY|NOW|UTCNOW|UTCTODAY)\s*\(", re.IGNORECASE)
DATES_WINDOW_RE = re.compile(r"\b(DATESBETWEEN|DATESINPERIOD)\s*\(", re.IGNORECASE)
TI_RE = re.compile(
    r"\b(SAMEPERIODLASTYEAR|DATESYTD|DATESMTD|DATESQTD|TOTALYTD|TOTALMTD|TOTALQTD|DATEADD|"
    r"PARALLELPERIOD|PREVIOUSYEAR|PREVIOUSQUARTER|PREVIOUSMONTH|PREVIOUSDAY|NEXTYEAR|NEXTQUARTER|"
    r"NEXTMONTH|NEXTDAY|OPENINGBALANCE\w*|CLOSINGBALANCE\w*|STARTOFYEAR|ENDOFYEAR|STARTOFMONTH|ENDOFMONTH)\s*\(",
    re.IGNORECASE,
)
ERRFN_RE = re.compile(r"\b(IFERROR|ISERROR)\s*\(", re.IGNORECASE)
TODO_RE = re.compile(r"\b(TODO|FIXME|HACK)\b")
HEX_RE = re.compile(r"'#[0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?'")
CRED_RE = re.compile(r"\b(password|pwd)\s*=\s*[^;\s\"'#]{2,}", re.IGNORECASE)
TEXTY_MEASURE_RE = re.compile(
    r"(title|label|colou?r|text|icon|url|subtitle|tooltip|caption|message|status|name|selected|header)",
    re.IGNORECASE,
)


@dataclass
class Options:
    max_visuals: int = 12
    max_fields: int = 20
    as_of_year: int = 2026
    page_name_patterns: List[str] = field(default_factory=lambda: list(DEFAULT_PAGE_NAME_PATTERNS))
    tab_inversion_ratio: float = 0.4  # A11Y-04: share of inverted visual pairs tolerated
    tab_row_band: float = 40.0  # A11Y-04: visuals whose y differs by less than this share a row
    min_text_contrast: float = 4.5  # A11Y-05, WCAG 1.4.3
    min_graphic_contrast: float = 3.0  # A11Y-05, WCAG 1.4.11
    cvd_delta_e: float = 10.0  # A11Y-07
    cvd_palette_size: int = 8  # A11Y-07: first N theme data colours (default series colours)
    validate_schemas: bool = False  # GOV-17 / GOV-18
    external_usage: Set[Tuple[str, str]] = field(default_factory=set)  # MOD-10 allowlist
    external_usage_source: Optional[str] = None
    disabled_rules: Set[str] = field(default_factory=set)
    severity_overrides: Dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "max_visuals": self.max_visuals, "max_fields": self.max_fields, "as_of_year": self.as_of_year,
            "tab_order_tolerance": self.tab_inversion_ratio, "tab_order_row_band": self.tab_row_band,
            "min_text_contrast": self.min_text_contrast, "min_graphic_contrast": self.min_graphic_contrast,
            "cvd_delta_e": self.cvd_delta_e, "cvd_palette_size": self.cvd_palette_size,
            "validate_schemas": self.validate_schemas,
            "external_usage": self.external_usage_source,
            "disabled_rules": sorted(self.disabled_rules),
            "severity_overrides": dict(sorted(self.severity_overrides.items())),
        }


def ev(file: str, line: Optional[int] = None, json_path: Optional[str] = None, detail: Optional[str] = None) -> Dict[str, Any]:
    e: Dict[str, Any] = {"file": file}
    if line is not None:
        e["line"] = int(line)
    if json_path:
        e["json_path"] = json_path
    if detail:
        e["detail"] = detail
    return e


class Context:
    def __init__(self, project: Project, options: Options):
        self.project = project
        self.options = options
        self.report: Optional[Report] = project.report
        self.model: Optional[SemanticModel] = project.model
        self._counter: Dict[str, int] = {}
        self._dax_names: Optional[Set[str]] = None
        self._refs: Optional[List[Tuple[FieldRef, JsonFile]]] = None

    # -- finding factory ----------------------------------------------------
    def finding(self, rule_id: str, message: str, evidence: List[Dict[str, Any]],
                confidence: str = "high", severity: Optional[str] = None,
                count: Optional[int] = None) -> Dict[str, Any]:
        rule = BY_ID[rule_id]
        self._counter[rule_id] = self._counter.get(rule_id, 0) + 1
        total = len(evidence)
        f: Dict[str, Any] = {
            "id": f"{rule_id}#{self._counter[rule_id]}",
            "rule_id": rule_id,
            "title": rule.title,
            "pillar": rule.pillar,
            "severity": severity or rule.severity,
            "check_type": "D",
            "confidence": confidence,
            "classification": rule.kind,
            "message": message,
            "evidence": evidence[:MAX_EVIDENCE],
            "fix": rule.fix,
            "source": rule.source,
        }
        if count is not None or total > MAX_EVIDENCE:
            f["count"] = count if count is not None else total
        return f

    # -- shared indexes -------------------------------------------------------
    def date_tables(self) -> List[Table]:
        if not self.model:
            return []
        marked = [t for t in self.model.tables.values() if (t.data_category or "").lower() == "time" and not t.is_auto_date]
        if marked:
            return marked
        out = []
        for t in self.model.tables.values():
            n = t.name.lower()
            if t.is_auto_date:
                continue
            if n in ("date", "dates", "dim date", "dimdate", "dim_date", "calendar", "fecha", "calendario") or "calendar" in n:
                out.append(t)
        return out

    def dax_bracket_names(self) -> Set[str]:
        if self._dax_names is None:
            names: Set[str] = set()
            if self.model:
                for (_k, _f, _l, text) in self.model.dax_texts():
                    for m in re.finditer(r"\[([^\]]+)\]", text or ""):
                        names.add(m.group(1).strip().lower())
            self._dax_names = names
        return self._dax_names

    def report_refs(self) -> List[Tuple[FieldRef, JsonFile]]:
        if self._refs is None:
            refs: List[Tuple[FieldRef, JsonFile]] = []
            r = self.report
            if r is not None:
                sources: List[Tuple[Any, JsonFile, str]] = []
                if r.report_json and r.report_json.data is not None:
                    sources.append((r.report_json.data, r.report_json, "$"))
                for p in r.pages:
                    sources.append((p.data, p.file, "$"))
                    for v in p.visuals:
                        sources.append((v.data, v.file, "$"))
                for b in r.bookmarks:
                    if b.data is not None:
                        sources.append((b.data, b, "$"))
                for data, jf, root in sources:
                    tmp: List[FieldRef] = []
                    collect_refs(data, root, tmp)
                    refs.extend((fr, jf) for fr in tmp)
            self._refs = refs
        return self._refs


# ---------------------------------------------------------------------------
# DAX text helpers
# ---------------------------------------------------------------------------


def strip_dax(text: str, keep_names: bool = False) -> str:
    """Remove comments and string literals; optionally blank out names."""
    out = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        two = text[i:i + 2]
        if two in ("//", "--"):
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        if two == "/*":
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if c == '"':
            j = i + 1
            while j < n:
                if text[j] == '"':
                    if j + 1 < n and text[j + 1] == '"':
                        j += 2
                        continue
                    break
                j += 1
            out.append('""')
            i = j + 1
            continue
        if c == "'" and not keep_names:
            j = text.find("'", i + 1)
            while j >= 0 and j + 1 < n and text[j + 1] == "'":
                j = text.find("'", j + 2)
            out.append("T")
            i = n if j < 0 else j + 1
            continue
        if c == "[" and not keep_names:
            j = text.find("]", i + 1)
            out.append("[x]")
            i = n if j < 0 else j + 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


def find_calls(text: str, fname: str) -> List[List[str]]:
    """Return the argument lists of every ``fname(...)`` call (comment/string safe)."""
    clean = strip_dax(text, keep_names=True)
    res = []
    for m in re.finditer(rf"\b{fname}\s*\(", clean, re.IGNORECASE):
        depth = 1
        j = m.end()
        args: List[str] = []
        buf = ""
        while j < len(clean) and depth > 0:
            ch = clean[j]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    break
            if ch == "," and depth == 1:
                args.append(buf.strip())
                buf = ""
            else:
                buf += ch
            j += 1
        args.append(buf.strip())
        res.append(args)
    return res


TEXT_EXPR_RE = re.compile(r"\b(FORMAT|CONCATENATEX|COMBINEVALUES|UNICHAR|SELECTEDVALUE|CONCATENATE)\s*\(|(?<!&)&(?!&)", re.IGNORECASE)


def _looks_textual(me) -> bool:
    """Heuristic: measures that probably return text, colours or titles need no format string."""
    if TEXTY_MEASURE_RE.search(me.name):
        return True
    clean = strip_dax(me.expression or "", keep_names=False)
    if TEXT_EXPR_RE.search(clean):
        return True
    # returns string literals, e.g. IF(cond, "A", "B")
    return bool(re.search(r'[,(]\s*""\s*[,)]', clean))


def has_unsafe_division(expr: str) -> bool:
    clean = strip_dax(expr)
    for m in re.finditer(r"/", clean):
        rest = clean[m.end():].lstrip()
        if re.match(r"^\(?\s*-?\d+(\.\d+)?\s*\)?(?![\w\[(])", rest):
            continue
        return True
    return False


def window_regex_for(tables: List[Table]) -> Optional[re.Pattern]:
    if not tables:
        return None
    alts = []
    for t in tables:
        alts.append(r"'" + re.escape(t.name) + r"'")
        if re.match(r"^\w+$", t.name):
            alts.append(re.escape(t.name) + r"\b")
    return re.compile(
        r"\b(REMOVEFILTERS|ALL|ALLNOBLANKROW|ALLEXCEPT)\s*\(\s*(" + "|".join(alts) + ")",
        re.IGNORECASE,
    )


# ---------------------------------------------------------------------------
# Format and structure
# ---------------------------------------------------------------------------


def check_format(ctx: Context) -> Iterable[Dict[str, Any]]:
    p = ctx.project
    r = ctx.report
    if r is not None and r.format == "PBIR-Legacy":
        yield ctx.finding("GOV-13", "The report is stored as PBIR-Legacy (root report.json). Report-layer rules were skipped.",
                          [ev(_rel(p, r.root / "report.json"))])
    if p.thin:
        yield ctx.finding("BIND-02", "definition.pbir uses byConnection; the semantic model is not part of this project, so report-to-model binding was not checked.",
                          [ev(r.definition_pbir.rel if r and r.definition_pbir else "definition.pbir", json_path="$.datasetReference.byConnection")])
    if p.model_format == "TMSL":
        yield ctx.finding("GOV-16", "The semantic model is stored as model.bim (TMSL); model rules were skipped.",
                          [ev(_rel(p, p.model_dir / "model.bim"))])
    if r is not None:
        for folder, kind in r.invalid_folders:
            yield ctx.finding("GOV-14", f"The {kind} folder name is not word characters or hyphens, so Desktop ignores it.", [ev(folder)])
        for rel, msg in r.json_errors:
            yield ctx.finding("GOV-15", f"Invalid JSON: {msg}", [ev(rel)])
    if ctx.model is not None and ctx.model.warnings:
        evs = []
        for w in ctx.model.warnings:
            m = re.match(r"^(.*?):(\d+): (.*)$", w)
            evs.append(ev(m.group(1), int(m.group(2)), detail=m.group(3)) if m else ev("?", detail=w))
        yield ctx.finding("GOV-15", f"{len(evs)} TMDL line(s) were not recognised by the tolerant parser. They may be valid syntax this parser does not know, or real errors.",
                          evs, confidence="low", count=len(evs))


def _rel(p: Project, path) -> str:
    try:
        return path.relative_to(p.base).as_posix()
    except ValueError:
        return str(path)


# ---------------------------------------------------------------------------
# Binding (report -> model)
# ---------------------------------------------------------------------------


def check_binding(ctx: Context) -> Iterable[Dict[str, Any]]:
    m, r = ctx.model, ctx.report
    if m is None or r is None or ctx.project.thin:
        return
    missing: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = {}
    stale: Dict[str, List[Dict[str, Any]]] = {}
    bookmark_files = {b.rel for b in r.bookmarks}
    for ref, jf in ctx.report_refs():
        problem = _resolve(ref, m, r)
        if problem is None:
            continue
        line = jf.line_at(parse_path(ref.json_path) + ("Property",))
        if jf.rel in bookmark_files:
            d = f"{problem}: '{ref.entity}'[{ref.prop}]"
            lst = stale.setdefault(jf.rel, [])
            if all(e.get("detail") != d for e in lst):
                lst.append(ev(jf.rel, line, ref.json_path, detail=d))
            continue
        key = (ref.entity, ref.prop, problem)
        missing.setdefault(key, []).append(ev(jf.rel, line, ref.json_path))
    for rel, evs in sorted(stale.items()):
        name = next((b.data.get("displayName") for b in r.bookmarks if b.rel == rel and isinstance(b.data, dict)), None) or rel
        yield ctx.finding("BIND-03", f"Bookmark '{name}' stores state for {len(evs)} model object(s) that no longer exist; applying it can break visuals.",
                          evs, confidence="medium", count=len(evs))
    for (entity, prop, problem), evs in sorted(missing.items()):
        yield ctx.finding("BIND-01", f"{problem}: '{entity}'[{prop}] is referenced in {len(evs)} place(s) but is not defined in the semantic model.",
                          evs, count=len(evs))


def _resolve(ref: FieldRef, m: SemanticModel, r: Report) -> Optional[str]:
    ent = ref.entity.lower()
    prop = ref.prop.lower()
    if ref.schema == "extension" or ent in r.extension_measures:
        if prop in r.extension_measures.get(ent, set()):
            return None
        if ref.schema == "extension":
            return "Missing report-level measure"
    t = m.tables.get(ent)
    if t is None:
        return "Missing table"
    if ref.kind == "Hierarchy":
        if prop in t.hierarchies:
            return None
        return "Missing hierarchy"
    if prop in t.columns or prop in t.measures:
        return None
    return "Missing measure" if ref.kind == "Measure" else "Missing column"


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


def check_model(ctx: Context) -> Iterable[Dict[str, Any]]:
    m = ctx.model
    if m is None:
        return
    for rel in m.relationships:
        label = f"{rel.from_table}.{rel.from_column} -> {rel.to_table}.{rel.to_column}"
        if (rel.cross_filter or "").lower() == "bothdirections":
            yield ctx.finding("MOD-01", f"Relationship {label} filters in both directions.",
                              [ev(rel.file, rel.line, detail="crossFilteringBehavior: bothDirections")])
        if (rel.from_cardinality or "").lower() == "one" and (rel.to_cardinality or "one").lower() == "one":
            yield ctx.finding("MOD-02", f"Relationship {label} is one-to-one.", [ev(rel.file, rel.line)])

    # MOD-03 inactive relationships
    userel_args: List[str] = []
    for (_k, _f, _l, text) in m.dax_texts():
        for args in find_calls(text or "", "USERELATIONSHIP"):
            userel_args.append(" ".join(args).lower())
    for rel in m.relationships:
        if rel.is_active:
            continue
        fc, tc = rel.from_column.lower(), rel.to_column.lower()
        used = any(fc in a and tc in a for a in userel_args)
        if not used:
            yield ctx.finding("MOD-03", f"Inactive relationship {rel.from_table}.{rel.from_column} -> {rel.to_table}.{rel.to_column} is not activated by any USERELATIONSHIP call.",
                              [ev(rel.file, rel.line, detail="isActive: false")], confidence="medium")

    # MOD-04 time intelligence without marked date table
    has_marked = any((t.data_category or "").lower() == "time" for t in m.tables.values() if not t.is_auto_date)
    if not has_marked:
        evs = [ev(me.file, me.line, detail=me.name) for me in m.all_measures() if TI_RE.search(me.expression or "")]
        if evs:
            yield ctx.finding("MOD-04", f"{len(evs)} measure(s) use time-intelligence functions but no table is marked as a date table (dataCategory: Time).",
                              evs, confidence="medium", count=len(evs))

    # MOD-05 auto date/time
    ann = m.model_annotations.get("__PBI_TimeIntelligenceEnabled")
    autos = [t for t in m.tables.values() if t.is_auto_date and t.name.lower().startswith("localdatetable_")]
    if (ann and ann[0].strip() == "1") or autos:
        evs = []
        if ann:
            evs.append(ev(m.model_file or "model.tmdl", ann[1], detail=f"__PBI_TimeIntelligenceEnabled = {ann[0]}"))
        evs.extend(ev(t.file, t.line, detail=t.name) for t in autos[:5])
        if autos:
            yield ctx.finding("MOD-05", f"Auto date/time is enabled and has generated {len(autos)} LocalDateTable table(s).", evs)
        else:
            yield ctx.finding("MOD-05", "The Auto date/time option is on (model annotation), although no LocalDateTable table exists yet; new date columns will get one.",
                              evs, severity="Low")

    # MOD-07 visible FK
    fk_by_table: Dict[str, List[Dict[str, Any]]] = {}
    date_names = {t.name.lower() for t in ctx.date_tables()}
    for rel in m.relationships:
        to_t = m.table(rel.to_table)
        if to_t is not None and to_t.is_auto_date:
            continue  # auto date/time relationships are reported by MOD-05
        sides = []
        if (rel.from_cardinality or "many").lower() == "many":
            sides.append((rel.from_table, rel.from_column))
        if (rel.to_cardinality or "one").lower() == "many":
            sides.append((rel.to_table, rel.to_column))
        for tname, cname in sides:
            t = m.table(tname)
            if t is None or t.is_hidden or t.is_auto_date or t.name.lower() in date_names:
                continue
            c = t.columns.get(cname.lower())
            if c is not None and not c.is_hidden:
                fk_by_table.setdefault(t.name, []).append(ev(c.file, c.line, detail=c.name))
    for tname, evs in sorted(fk_by_table.items()):
        uniq = {e["detail"]: e for e in evs}
        yield ctx.finding("MOD-07", f"Table '{tname}' has {len(uniq)} visible foreign-key column(s): {', '.join(sorted(uniq))}.",
                          list(uniq.values()), count=len(uniq))

    # MOD-08 doubles
    for t in sorted(m.tables.values(), key=lambda x: x.name.lower()):
        if t.is_auto_date:
            continue
        dbl = [c for c in t.columns.values() if (c.data_type or "").lower() == "double"]
        if dbl:
            yield ctx.finding("MOD-08", f"Table '{t.name}' has {len(dbl)} double (floating-point) column(s): {', '.join(c.name for c in dbl[:10])}{'...' if len(dbl) > 10 else ''}.",
                              [ev(c.file, c.line, detail=c.name) for c in dbl], count=len(dbl))

    # MOD-09 implicit measures
    if m.model_file and "discourageimplicitmeasures" not in m.model_props:
        yield ctx.finding("MOD-09", "model.tmdl does not set discourageImplicitMeasures.", [ev(m.model_file, m.model_line)])

    # MOD-10 unused objects
    yield from _check_unused(ctx)


def _check_unused(ctx: Context) -> Iterable[Dict[str, Any]]:
    m, r = ctx.model, ctx.report
    if m is None or r is None or ctx.project.thin or r.format != "PBIR":
        return
    used: Set[Tuple[str, str]] = set(ctx.options.external_usage)
    for ref, _jf in ctx.report_refs():
        used.add((ref.entity.lower(), ref.prop.lower()))
    names = ctx.dax_bracket_names()
    rel_cols = set()
    for rel in m.relationships:
        rel_cols.add((rel.from_table.lower(), rel.from_column.lower()))
        rel_cols.add((rel.to_table.lower(), rel.to_column.lower()))
    for t in sorted(m.tables.values(), key=lambda x: x.name.lower()):
        if t.is_auto_date or t.is_calculation_group:
            continue
        tl = t.name.lower()
        sort_targets = {c.sort_by.lower() for c in t.columns.values() if c.sort_by}
        level_cols = {lv.lower() for levels in t.hierarchies.values() for lv in levels}
        unused = []
        dummy_measure_table = len(t.measures) > 0 and len(t.columns) == 1
        for c in t.columns.values():
            if dummy_measure_table:
                continue
            cl = c.name.lower()
            if (tl, cl) in used or cl in names or (tl, cl) in rel_cols or cl in sort_targets or cl in level_cols or c.is_key:
                continue
            if cl.startswith("rownumber-"):
                continue
            unused.append(("column", c))
        for me in t.measures.values():
            ml = me.name.lower()
            if (tl, ml) in used or ml in names:
                continue
            unused.append(("measure", me))
        if unused:
            label = ", ".join(f"{k} {o.name}" for k, o in unused[:12]) + ("..." if len(unused) > 12 else "")
            scope = ("this report, the external-usage list" if ctx.options.external_usage_source else "this report")
            note = ("" if ctx.options.external_usage_source else
                    " Other reports, Excel or paginated reports bound to the same model may use them; pass --external-usage to allowlist those.")
            yield ctx.finding("MOD-10", f"Table '{t.name}' has {len(unused)} object(s) not referenced by {scope}, any DAX, relationship, sort-by or hierarchy: {label}.{note}",
                              [ev(o.file, o.line, detail=f"{k} {o.name}") for k, o in unused],
                              confidence="medium", count=len(unused))


# ---------------------------------------------------------------------------
# DAX and governance metadata
# ---------------------------------------------------------------------------


def check_dax(ctx: Context) -> Iterable[Dict[str, Any]]:
    m = ctx.model
    if m is None:
        return
    for t in sorted(m.tables.values(), key=lambda x: x.name.lower()):
        if t.is_auto_date:
            continue
        no_fmt, no_desc, blank0 = [], [], []
        for me in t.measures.values():
            expr = me.expression or ""
            if has_unsafe_division(expr):
                yield ctx.finding("DAX-01", f"Measure '{me.name}' uses the / operator with a non-constant denominator.",
                                  [ev(me.file, me.line, detail=me.name)], confidence="medium")
            for args in find_calls(expr, "DIVIDE"):
                if len(args) >= 3 and re.match(r"^0+(\.0+)?$", args[2].strip()):
                    blank0.append(me)
                    break
            visible = not me.is_hidden and not t.is_hidden
            if visible and not me.format_string and not me.has_format_definition and not _looks_textual(me):
                no_fmt.append(me)
            if visible and not (me.description or "").strip():
                no_desc.append(me)
        if blank0:
            yield ctx.finding("DAX-04", f"Table '{t.name}' has {len(blank0)} measure(s) that turn BLANK into 0 via DIVIDE(..., ..., 0): {', '.join(x.name for x in blank0[:10])}{'...' if len(blank0) > 10 else ''}.",
                              [ev(x.file, x.line, detail=x.name) for x in blank0], confidence="medium", count=len(blank0))
        if no_fmt:
            yield ctx.finding("DAX-07", f"Table '{t.name}' has {len(no_fmt)} visible measure(s) without a format string: {', '.join(x.name for x in no_fmt[:10])}{'...' if len(no_fmt) > 10 else ''}.",
                              [ev(x.file, x.line, detail=x.name) for x in no_fmt], confidence="medium", count=len(no_fmt))
        if no_desc:
            yield ctx.finding("GOV-01", f"Table '{t.name}' has {len(no_desc)} visible measure(s) without a description: {', '.join(x.name for x in no_desc[:10])}{'...' if len(no_desc) > 10 else ''}.",
                              [ev(x.file, x.line, detail=x.name) for x in no_desc], count=len(no_desc))

    for (kind, file, line, text) in m.dax_texts():
        clean = strip_dax(text or "", keep_names=True)
        if ERRFN_RE.search(clean):
            yield ctx.finding("DAX-03", f"A {kind} expression uses IFERROR/ISERROR.", [ev(file, line)])
        # TODO markers live in comments, so search the raw text
        if TODO_RE.search(text or ""):
            yield ctx.finding("DAX-08", f"A {kind} expression contains a TODO/FIXME/HACK marker.", [ev(file, line)])

    long_desc = []
    for t in m.tables.values():
        objs: List[Any] = [t] + list(t.columns.values()) + list(t.measures.values())
        for o in objs:
            if o.description and len(o.description) > 200:
                long_desc.append(ev(o.file, o.line, detail=f"{o.name} ({len(o.description)} chars)"))
    if long_desc:
        yield ctx.finding("GOV-02", f"{len(long_desc)} description(s) are longer than 200 characters.", long_desc, count=len(long_desc))

    cred = []
    for t in m.tables.values():
        for p in t.partitions:
            if CRED_RE.search(p.source or ""):
                cred.append(ev(p.file, p.line, detail=f"partition {p.name}"))
    for e in m.expressions:
        if CRED_RE.search(e.value or ""):
            cred.append(ev(e.file, e.line, detail=f"expression {e.name}"))
    if cred:
        yield ctx.finding("GOV-09", "A password-like key/value pair appears in M source code.", cred, count=len(cred))


# ---------------------------------------------------------------------------
# Report layer
# ---------------------------------------------------------------------------


def _field_key(ref: FieldRef) -> str:
    return f"'{ref.entity}'[{ref.prop}]"


def _slicer_fields(v: Visual) -> List[FieldRef]:
    return [f for f in v.projection_refs() if f.kind in ("Column", "Measure", "Variation", "Hierarchy")]


def check_slicers(ctx: Context) -> Iterable[Dict[str, Any]]:
    r = ctx.report
    if r is None:
        return
    slicers = [v for v in r.visuals() if v.visual_type in SLICER_TYPES]
    groups: Dict[str, List[Visual]] = {}
    by_field: Dict[str, Dict[str, List[Visual]]] = {}
    for v in slicers:
        g = v.sync_group
        fields = _slicer_fields(v)
        fkey = ", ".join(sorted({_field_key(f) for f in fields})) or "(no field)"
        if g:
            groups.setdefault(g, []).append(v)
            by_field.setdefault(fkey, {}).setdefault(g, []).append(v)

    for g, vs in sorted(groups.items()):
        fieldsets: Dict[str, List[Visual]] = {}
        for v in vs:
            fkey = ", ".join(sorted({_field_key(f) for f in _slicer_fields(v)})) or "(no field)"
            fieldsets.setdefault(fkey, []).append(v)
        if len(fieldsets) > 1:
            evs = []
            for fkey, members in fieldsets.items():
                for v in members:
                    evs.append(ev(v.file.rel, v.file.line_at(("visual", "syncGroup")), "$.visual.syncGroup",
                                  detail=f"page '{v.page.display_name}', field {fkey}"))
            yield ctx.finding("IN-03", f"Sync group '{g}' mixes {len(fieldsets)} different fields: {' | '.join(sorted(fieldsets))}.", evs)

    for fkey, gmap in sorted(by_field.items()):
        if len(gmap) > 1:
            evs = []
            for g, members in sorted(gmap.items()):
                for v in members:
                    evs.append(ev(v.file.rel, v.file.line_at(("visual", "syncGroup")), "$.visual.syncGroup",
                                  detail=f"group '{g}', page '{v.page.display_name}'"))
            pages_per_group = {g: {v.page.name for v in members} for g, members in gmap.items()}
            all_pages = [p for s in pages_per_group.values() for p in s]
            same_page_only = len(set(all_pages)) == 1
            yield ctx.finding("IN-04", f"Field {fkey} is sliced in {len(gmap)} different sync groups: {', '.join(sorted(gmap))}.",
                              evs, severity="Info" if same_page_only else None,
                              confidence="medium")

    # IN-02 hidden synced slicers
    for v in slicers:
        if v.is_hidden and v.sync_group:
            fk = {_field_key(f) for f in _slicer_fields(v)}
            visible_twin = any(
                (not o.is_hidden) and o is not v and fk & {_field_key(f) for f in _slicer_fields(o)}
                for o in v.page.visuals if o.visual_type in SLICER_TYPES
            )
            if not visible_twin:
                yield ctx.finding("IN-02", f"Hidden slicer on {', '.join(sorted(fk))} in sync group '{v.sync_group}' filters page '{v.page.display_name}' invisibly.",
                                  [ev(v.file.rel, v.file.line_at(("isHidden",)), "$.isHidden")], confidence="medium")

    # IN-13 year slicer over a date table that reaches future years
    yield from _check_future_years(ctx, slicers)


def _date_table_max_year(t: Table) -> Tuple[Optional[int], bool]:
    """Return (max literal year, uses YEAR(TODAY())+n)."""
    years: List[int] = []
    future_rel = False
    for p in t.partitions:
        src = p.source or ""
        years += [int(y) for y in re.findall(r"\bDATE\s*\(\s*(\d{4})\s*,", src, re.IGNORECASE)]
        years += [int(y) for y in re.findall(r"#date\s*\(\s*(\d{4})\s*,", src)]
        if re.search(r"YEAR\s*\(\s*(TODAY|NOW|UTCNOW|UTCTODAY)\s*\(\s*\)\s*\)\s*\+\s*[1-9]", src, re.IGNORECASE):
            future_rel = True
        if re.search(r"Date\.Year\s*\(\s*DateTime\.LocalNow\s*\(\s*\)\s*\)\s*\+\s*[1-9]", src):
            future_rel = True
    return (max(years) if years else None), future_rel


def _filters_on(data: Any, entity_l: str) -> bool:
    if not isinstance(data, dict):
        return False
    fc = data.get("filterConfig") or {}
    refs: List[FieldRef] = []
    collect_refs(fc.get("filters") or [], "$", refs)
    return any(f.entity.lower() == entity_l for f in refs)


def _check_future_years(ctx: Context, slicers: List[Visual]) -> Iterable[Dict[str, Any]]:
    m, r = ctx.model, ctx.report
    if m is None or r is None:
        return
    dts = {t.name.lower(): t for t in ctx.date_tables()}
    report_data = r.report_json.data if r.report_json else None
    for v in slicers:
        if v.is_hidden:
            continue
        for f in _slicer_fields(v):
            t = dts.get(f.entity.lower())
            if t is None or f.kind not in ("Column",):
                continue
            col = t.columns.get(f.prop.lower())
            is_year = ("year" in f.prop.lower() or "año" in f.prop.lower() or
                       bool(col and col.expression and re.match(r"^\s*YEAR\s*\(", col.expression, re.IGNORECASE)))
            if not is_year:
                continue
            max_year, rel_future = _date_table_max_year(t)
            if not (rel_future or (max_year is not None and max_year > ctx.options.as_of_year)):
                continue
            el = t.name.lower()
            if _filters_on(v.data, el) or _filters_on(v.page.data, el) or _filters_on(report_data, el):
                continue
            reach = f"to {max_year}" if max_year else "beyond the current year"
            yield ctx.finding("IN-13", f"Slicer on '{t.name}'[{f.prop}] (page '{v.page.display_name}') has no filter limiting years, while the date table extends {reach}.",
                              [ev(v.file.rel, v.file.line_at(parse_path(f.json_path) + ("Property",)), f.json_path),
                               ev(t.partitions[0].file, t.partitions[0].line, detail="date table definition") if t.partitions else ev(t.file, t.line)],
                              confidence="medium")


def check_windows(ctx: Context) -> Iterable[Dict[str, Any]]:
    """IN-05: rolling-window measures shown in visuals without a window label."""
    m, r = ctx.model, ctx.report
    if m is None or r is None:
        return
    rx = window_regex_for(ctx.date_tables())
    window: Dict[str, Tuple[Any, str]] = {}
    for me in m.all_measures():
        expr = me.expression or ""
        if not TODAY_RE.search(expr):
            continue
        if (rx and rx.search(expr)) or DATES_WINDOW_RE.search(expr):
            window[me.name.lower()] = (me, "direct")
    # one level of propagation per pass, bounded
    for _ in range(3):
        added = False
        for me in m.all_measures():
            ml = me.name.lower()
            if ml in window:
                continue
            refs = {x.strip().lower() for x in re.findall(r"\[([^\]]+)\]", me.expression or "")}
            hit = next((w for w in refs if w in window), None)
            if hit:
                window[ml] = (me, f"via [{window[hit][0].name}]")
                added = True
        if not added:
            break
    if not window:
        return
    for v in r.visuals():
        if v.is_group or v.is_hidden:
            continue
        title = v.title_text or ""
        if title == "<expr>":
            continue
        qs = ((v.visual.get("query") or {}).get("queryState")) or {}
        for role, body in qs.items():
            for idx, p in enumerate((body or {}).get("projections", []) or []):
                fld = (p or {}).get("field") or {}
                meas = fld.get("Measure")
                if not isinstance(meas, dict):
                    continue
                name = (meas.get("Property") or "")
                hit = window.get(name.lower())
                if hit is None:
                    continue
                me, how = hit
                # the window is stated in the title, the measure name, the display name,
                # or documented in the measure description (intent is explicit)
                label = " ".join([title, name, p.get("displayName") or "", me.name, me.description or ""])
                if WINDOW_WORDS_RE.search(label):
                    continue
                path = ("visual", "query", "queryState", role, "projections", idx, "field", "Measure", "Property")
                yield ctx.finding("IN-05", f"Visual on page '{v.page.display_name}' shows [{name}], which builds its own date window from TODAY() ({how}), but neither the title ('{title or 'no title'}'), the field names nor the measure description say so.",
                                  [ev(v.file.rel, v.file.line_at(path), format_path(path[:6])),
                                   ev(me.file, me.line, detail=me.name)],
                                  confidence="low" if how != "direct" else "medium")


def check_pages(ctx: Context) -> Iterable[Dict[str, Any]]:
    r = ctx.report
    if r is None or r.format != "PBIR":
        return
    o = ctx.options
    patterns = [re.compile(p, re.IGNORECASE) for p in o.page_name_patterns]
    # text corpus for navigation references
    for page in r.pages:
        pf = page.file
        if any(p.search(page.display_name) for p in patterns):
            yield ctx.finding("ST-01", f"Page '{page.display_name}' has a default name.",
                              [ev(pf.rel, pf.line_at(("displayName",)), "$.displayName")])
        if page.is_hidden and not page.is_tooltip and not page.is_drillthrough:
            own = {pf.rel} | {v.file.rel for v in page.visuals}
            needles = (f"'{page.name}'", f'"{page.name}"')
            referenced = any(
                jf.rel not in own and any(n in jf.text for n in needles)
                for jf in r.all_text if jf.rel != (r.pages_json.rel if r.pages_json else "")
            )
            if not referenced:
                yield ctx.finding("ST-05", f"Page '{page.display_name}' is hidden, is not a drillthrough or tooltip page, and no button or bookmark references it.",
                                  [ev(pf.rel, pf.line_at(("visibility",)), "$.visibility")])
        if page.is_drillthrough:
            has_back = any(v.visual_type == "actionButton" and "'Back'" in v.file.text for v in page.visuals)
            if not has_back:
                yield ctx.finding("IN-07", f"Drillthrough page '{page.display_name}' has no Back button.",
                                  [ev(pf.rel, pf.line_at(("pageBinding",)), "$.pageBinding")])

        visible = [v for v in page.visuals if not v.is_group and not v.is_hidden]
        data_bound = [v for v in visible if v.projections()]
        if len(data_bound) > o.max_visuals:
            yield ctx.finding("PERF-01", f"Page '{page.display_name}' has {len(data_bound)} data-bound visuals (threshold {o.max_visuals}).",
                              [ev(pf.rel)], count=len(data_bound))

        missing_alt = []
        if not page.is_tooltip:
            for v in visible:
                if v.visual_type in DECORATIVE_TYPES or v.visual_type in SLICER_TYPES:
                    continue
                alt = v.alt_text
                if alt is None or not alt.strip():
                    missing_alt.append(v)
        if missing_alt:
            yield ctx.finding("A11Y-01", f"Page '{page.display_name}': {len(missing_alt)} of {len([v for v in visible if v.visual_type not in DECORATIVE_TYPES and v.visual_type not in SLICER_TYPES])} non-decorative visuals have no alt text.",
                              [ev(v.file.rel, v.file.line_at(("visual", "visualType")), "$.visual.visualType", detail=v.visual_type) for v in missing_alt], count=len(missing_alt))

        # tab order vs reading order
        tabbed = [v for v in visible if isinstance(v.position.get("tabOrder"), (int, float))]
        if len(tabbed) >= 4:
            by_tab = sorted(tabbed, key=lambda v: v.position.get("tabOrder"))
            band = max(1.0, float(o.tab_row_band))
            by_read = sorted(tabbed, key=lambda v: (round(float(v.position.get("y", 0)) / band), float(v.position.get("x", 0))))
            rank = {id(v): i for i, v in enumerate(by_read)}
            seq = [rank[id(v)] for v in by_tab]
            inv = sum(1 for i in range(len(seq)) for j in range(i + 1, len(seq)) if seq[i] > seq[j])
            pairs = len(seq) * (len(seq) - 1) / 2
            if pairs and inv / pairs > o.tab_inversion_ratio:
                first = by_tab[0]
                yield ctx.finding("A11Y-04", f"Page '{page.display_name}': tab order disagrees with reading order for {inv / pairs:.0%} of visual pairs (tolerance {o.tab_inversion_ratio:.0%}, row band {band:g}px).",
                                  [ev(first.file.rel, first.file.line_at(("position", "tabOrder")), "$.position.tabOrder",
                                      detail=f"first in tab order: {first.visual_type} at x={float(first.position.get('x', 0)):.0f}, y={float(first.position.get('y', 0)):.0f}")],
                                  confidence="medium")

        yield from _hex_literals(ctx, page)

        for v in visible:
            vt = v.visual_type
            if vt in ("pieChart", "donutChart"):
                yield ctx.finding("VD-01", f"Page '{page.display_name}' uses a {vt}; check the number of categories.",
                                  [ev(v.file.rel, v.file.line_at(("visual", "visualType")), "$.visual.visualType")], confidence="medium")
            if vt == "gauge":
                roles = {role for role, _ in v.projections()}
                if "TargetValue" not in roles:
                    yield ctx.finding("VD-02", f"Gauge on page '{page.display_name}' has no target value.",
                                      [ev(v.file.rel, v.file.line_at(("visual", "visualType")), "$.visual.visualType")])
            n_fields = len(v.projections())
            if n_fields > o.max_fields:
                yield ctx.finding("PERF-02", f"A {vt} on page '{page.display_name}' has {n_fields} fields (threshold {o.max_fields}).",
                                  [ev(v.file.rel, v.file.line_at(("visual", "query", "queryState")), "$.visual.query.queryState")], count=n_fields)
            if v.parent_group is None:
                pos = v.position
                try:
                    x, y = float(pos.get("x", 0)), float(pos.get("y", 0))
                    w, h = float(pos.get("width", 0)), float(pos.get("height", 0))
                except (TypeError, ValueError):
                    continue
                tol = 5
                if x < -tol or y < -tol or x + w > page.width + tol or y + h > page.height + tol:
                    yield ctx.finding("VD-10", f"A {vt} on page '{page.display_name}' extends outside the {int(page.width)}x{int(page.height)} canvas (x={x:.0f}, y={y:.0f}, w={w:.0f}, h={h:.0f}).",
                                      [ev(v.file.rel, v.file.line_at(("position",)), "$.position")])

    # hidden filters (IN-01)
    hidden: List[Dict[str, Any]] = []
    sources: List[Tuple[Any, JsonFile, str]] = []
    if r.report_json and isinstance(r.report_json.data, dict):
        sources.append((r.report_json.data, r.report_json, "report"))
    for page in r.pages:
        sources.append((page.data, page.file, f"page '{page.display_name}'"))
        for v in page.visuals:
            sources.append((v.data, v.file, f"visual on page '{page.display_name}'"))
    for data, jf, scope in sources:
        for i, flt in enumerate(((data or {}).get("filterConfig") or {}).get("filters") or []):
            if isinstance(flt, dict) and flt.get("isHiddenInViewMode"):
                refs: List[FieldRef] = []
                collect_refs(flt.get("field"), "$", refs)
                fld = _field_key(refs[0]) if refs else flt.get("name", "?")
                hidden.append(ev(jf.rel, jf.line_at(("filterConfig", "filters", i, "isHiddenInViewMode")), f"$.filterConfig.filters[{i}].isHiddenInViewMode", detail=f"{scope}: {fld}"))
    if hidden:
        yield ctx.finding("IN-01", f"{len(hidden)} filter(s) are hidden from the filter pane; confirm none changes the meaning of the numbers.",
                          hidden, confidence="medium", count=len(hidden))

    if r.pages and not any(v.has_mobile for v in r.visuals()):
        yield ctx.finding("MOB-01", "No visual has a mobile layout (no mobile.json files).", [ev(_rel(ctx.project, r.root / "definition" / "pages"))])


# ---------------------------------------------------------------------------
# Colour: hard-coded literals (VD-06), contrast (A11Y-05), confusable pairs (A11Y-07)
# ---------------------------------------------------------------------------

HEX_LITERAL_RE = re.compile(r"^'#[0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?'$")

# formatting objects whose "color" property is a text colour
TEXT_OBJECTS = {
    "title", "subTitle", "labels", "categoryLabels", "legend", "categoryAxis", "valueAxis", "values",
    "columnHeaders", "rowHeaders", "header", "calloutValue", "categoryLabel", "dataLabel", "text",
    "items", "date", "numeric", "total", "subTotals", "columnTotal", "rowTotal", "value", "label",
    "referenceLabel", "smallMultiplesLayout", "zoomSlider", "selection",
}
TEXT_COLOR_PROPS = {"fontColor", "labelColor", "titleColor"}
LARGE_TEXT_OBJECTS = {"calloutValue", "value"}
LAYER_TYPES = {"shape", "basicShape", "image"}
MARK_LABEL_HINTS = ("bar", "column", "pie", "donut", "treemap", "funnel", "waterfall", "ribbon")


def _hex_literals(ctx: Context, page: Page) -> Iterable[Dict[str, Any]]:
    r = ctx.report
    palette = r.theme.palette() if r else set()
    off_evs, on_total, off_total = [], 0, 0
    on_evs = []
    for v in page.visuals:
        hits = [(path, normalize_hex(val)) for path, val in walk(v.data)
                if isinstance(val, str) and HEX_LITERAL_RE.match(val)]
        if not hits:
            continue
        off = [(p, h) for p, h in hits if h not in palette]
        on = [(p, h) for p, h in hits if h in palette]
        on_total += len(on)
        off_total += len(off)
        if off:
            colours = ", ".join(sorted({h for _, h in off})[:5])
            off_evs.append(ev(v.file.rel, v.file.line_at(off[0][0]), format_path(off[0][0]),
                              detail=f"{len(off)} off-theme literal(s): {colours}"))
        elif on:
            on_evs.append(ev(v.file.rel, v.file.line_at(on[0][0]), format_path(on[0][0]),
                             detail=f"{len(on)} literal(s) equal to theme colours"))
    if off_evs:
        extra = f" ({on_total} more literal(s) equal theme colours)" if on_total else ""
        yield ctx.finding("VD-06", f"Page '{page.display_name}': {len(off_evs)} visual(s) use {off_total} hard-coded colour literal(s) that are not in the report theme{extra}.",
                          off_evs + on_evs, count=len(off_evs) + len(on_evs))
    elif on_evs:
        yield ctx.finding("VD-06", f"Page '{page.display_name}': {len(on_evs)} visual(s) hard-code {on_total} colour literal(s) that equal theme colours; they look right today but will not follow a theme change.",
                          on_evs, severity="Info", count=len(on_evs))


def _bool_lit(props: Dict[str, Any], key: str) -> Optional[bool]:
    v = props.get(key)
    if isinstance(v, bool):  # theme visualStyles use raw values
        return v
    if isinstance(v, dict):
        lit = ((v.get("expr") or {}).get("Literal") or {}).get("Value")
        if lit in ("true", "false"):
            return lit == "true"
    return None


def _num_lit(props: Dict[str, Any], key: str) -> Optional[float]:
    v = props.get(key)
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    if isinstance(v, dict):
        lit = ((v.get("expr") or {}).get("Literal") or {}).get("Value")
        if isinstance(lit, str):
            m = re.match(r"^(-?\d+(?:\.\d+)?)[DLM]?$", lit)
            if m:
                return float(m.group(1))
    return None


def _first_props(container: Dict[str, Any], obj: str) -> Dict[str, Any]:
    for entry in container.get(obj, []) or []:
        if isinstance(entry, dict) and isinstance(entry.get("properties"), dict):
            return entry["properties"]
    return {}


def _page_backgrounds(theme: Theme, page: Page) -> List[str]:
    props = _first_props(page.data.get("objects") or {}, "background")
    colour, _how = theme.resolve(props.get("color")) if "color" in props else (None, "")
    transp = _num_lit(props, "transparency")
    out: List[str] = []
    if colour:
        out.append(colour)
    if not colour or transp is None or transp >= 50:
        out.append(theme.background)
    return out


def _rect(v: Visual) -> Tuple[float, float, float, float, float]:
    p = v.position
    try:
        return (float(p.get("x", 0)), float(p.get("y", 0)), float(p.get("width", 0)), float(p.get("height", 0)), float(p.get("z", 0)))
    except (TypeError, ValueError):
        return (0.0, 0.0, 0.0, 0.0, 0.0)


def _layered(v: Visual, page: Page, theme: Theme) -> bool:
    """True when something with its own fill sits under ``v`` (shape, image, opaque visual)."""
    x, y, w, h, z = _rect(v)
    for o in page.visuals:
        if o is v or o.is_hidden:
            continue
        ox, oy, ow, oh, oz = _rect(o)
        if oz >= z or ox >= x + w or ox + ow <= x or oy >= y + h or oy + oh <= y:
            continue
        if o.visual_type in LAYER_TYPES or o.is_group:
            return True
        bg = _first_props(o.visual.get("visualContainerObjects") or {}, "background")
        if bg and _bool_lit(bg, "show") is not False:
            return True
    return False


def _visual_backgrounds(theme: Theme, page: Page, v: Visual) -> Optional[List[str]]:
    """Plausible backgrounds behind the visual's text, or None when unknowable.

    The visual's own ``background`` settings win over the theme's ``visualStyles``
    defaults (``*`` then the visual type). Opaque background: that colour only.
    Hidden or mostly transparent: whatever is underneath (page background, unless
    a shape, image or opaque visual sits below, which makes it unknowable).
    Unknown show state: every candidate, so only a fail against all of them counts.
    """
    own = _first_props(v.visual.get("visualContainerObjects") or {}, "background")
    style = style_props(theme, v.visual_type, "background")
    if "color" in own:
        colour, how = theme.resolve(own.get("color"))
        if how == "dynamic":
            return None
    elif "color" in style:
        colour, _how = theme.resolve(style.get("color"))
    else:
        colour = theme.background
    colour = colour or theme.background
    show = _bool_lit(own, "show")
    if show is None:
        show = _bool_lit(style, "show")
    transp = _num_lit(own, "transparency")
    if transp is None:
        transp = _num_lit(style, "transparency") or 0.0
    if show is True and transp < 50:
        return [colour]
    if _layered(v, page, theme):
        return None
    under = _page_backgrounds(theme, page)
    return under if show is False or transp >= 50 else sorted(set(under) | {colour})


def _fill_backgrounds(theme: Theme, v: Visual, selector: Optional[str]) -> Optional[List[str]]:
    """Buttons and shapes paint text over their own ``fill``; match the state selector."""
    fills = (v.visual.get("objects") or {}).get("fill") or []
    if not isinstance(fills, list) or not fills:
        return None
    shown = True
    by_sel: Dict[Optional[str], Any] = {}
    for entry in fills:
        if not isinstance(entry, dict):
            continue
        props = entry.get("properties") or {}
        if _bool_lit(props, "show") is False:
            shown = False
        sel = ((entry.get("selector") or {}).get("id")) if isinstance(entry.get("selector"), dict) else None
        if "fillColor" in props:
            by_sel[sel] = props["fillColor"]
    if not shown or not by_sel:
        return None
    raw = by_sel.get(selector) or by_sel.get("default") or by_sel.get(None)
    if raw is None:
        return None
    colour, how = theme.resolve(raw)
    return [colour] if colour else []


def _text_colours(v: Visual) -> Iterable[Tuple[PathT, Any, Optional[Any], bool, Optional[str]]]:
    """Yield (path, colour value, own background value or None, is_large_text, state selector)."""
    for ckey in ("visualContainerObjects", "objects"):
        cont = v.visual.get(ckey) or {}
        if not isinstance(cont, dict):
            continue
        for obj, entries in cont.items():
            for i, entry in enumerate(entries or []):
                props = (entry or {}).get("properties") if isinstance(entry, dict) else None
                if not isinstance(props, dict):
                    continue
                size = _num_lit(props, "fontSize")
                large = (size is not None and size >= 18) or (size is None and obj in LARGE_TEXT_OBJECTS) or \
                        (size is None and obj == "labels" and v.visual_type == "card")
                sel = entry.get("selector") if isinstance(entry.get("selector"), dict) else {}
                for prop, val in props.items():
                    if prop in TEXT_COLOR_PROPS or (prop == "color" and obj in TEXT_OBJECTS):
                        if "backColor" in props:
                            own_bg = props.get("backColor")
                        elif _bool_lit(props, "enableBackground") and "backgroundColor" in props and \
                                (_num_lit(props, "backgroundTransparency") or 0) < 50:
                            own_bg = props.get("backgroundColor")  # data-label background box
                        else:
                            own_bg = props.get("background")
                        yield ("visual", ckey, obj, i, "properties", prop), val, own_bg, large, sel.get("id")
    # text boxes: paragraphs[].textRuns[].textStyle.color (plain "#RRGGBB" strings)
    for path, val in walk(v.visual.get("objects") or {}, ("visual", "objects")):
        if len(path) >= 2 and path[-1] == "color" and path[-2] == "textStyle" and isinstance(val, str):
            yield path, val, None, False, None


def check_colour(ctx: Context) -> Iterable[Dict[str, Any]]:
    r = ctx.report
    if r is None or r.format != "PBIR":
        return
    theme = r.theme
    o = ctx.options
    yield from _theme_contrast(ctx, theme)

    for page in r.pages:
        fails = []
        for v in page.visuals:
            if v.is_group or v.is_hidden:
                continue
            backs = None
            inside_marks = any(k in v.visual_type.lower() for k in MARK_LABEL_HINTS)
            for path, val, own_bg, large, selector in _text_colours(v):
                if inside_marks and path[2] in ("labels", "dataLabel"):
                    continue  # data labels may sit inside bars/slices; their background is the mark colour
                fg, how = theme.resolve(val)
                if fg is None:
                    continue  # bound to an expression: not assessable offline
                fill = _fill_backgrounds(theme, v, selector)
                if own_bg is not None:
                    b, bhow = theme.resolve(own_bg)
                    cands = [b] if b else None
                elif fill is not None:
                    cands = fill
                else:
                    if backs is None:
                        backs = _visual_backgrounds(theme, page, v) or []
                    cands = backs
                if not cands:
                    continue
                need = o.min_graphic_contrast if large else o.min_text_contrast
                ratios = [contrast_ratio(fg, b) for b in cands]
                if max(ratios) < need:
                    worst = max(range(len(cands)), key=lambda k: ratios[k])
                    fails.append(ev(v.file.rel, v.file.line_at(path), format_path(path),
                                    detail=f"{v.visual_type}: text {fg} ({how}) on {cands[worst]} = {ratios[worst]:.2f}:1, needs {need:g}:1"))
        if fails:
            yield ctx.finding("A11Y-05", f"Page '{page.display_name}': {len(fails)} text colour(s) fall below the WCAG contrast minimum against every plausible background.",
                              fails, confidence="medium", count=len(fails))


def _theme_contrast(ctx: Context, theme: Theme) -> Iterable[Dict[str, Any]]:
    o = ctx.options
    bg = theme.background
    text_fails = []
    for key in ("foreground", "foregroundNeutralSecondary"):
        tf = theme.owner_of(key)
        c = normalize_hex(theme.colors.get(key))
        if tf is None or c is None:
            continue
        ratio = contrast_ratio(c, bg)
        if ratio < o.min_text_contrast:
            text_fails.append(ev(tf.rel, theme_line(tf, (key,)), f"$.{key}", detail=f"{key} {c} on background {bg} = {ratio:.2f}:1"))
    tf = theme.owner_of("textClasses")
    if tf is not None:
        for cls, spec in sorted((theme.colors.get("textClasses") or {}).items()):
            if not isinstance(spec, dict):
                continue
            c = normalize_hex(spec.get("color"))
            if c is None:
                continue
            size = spec.get("fontSize")
            need = o.min_graphic_contrast if isinstance(size, (int, float)) and size >= 18 else o.min_text_contrast
            ratio = contrast_ratio(c, bg)
            if ratio < need:
                text_fails.append(ev(tf.rel, theme_line(tf, ("textClasses", cls, "color")), f"$.textClasses.{cls}.color",
                                     detail=f"text class {cls} {c} on background {bg} = {ratio:.2f}:1, needs {need:g}:1"))
    if text_fails:
        yield ctx.finding("A11Y-05", f"The report theme sets {len(text_fails)} text colour(s) below the WCAG contrast minimum against the theme background.",
                          text_fails, count=len(text_fails))

    # graphics and colour-vision checks only judge palettes the author chose (custom theme)
    dtf = theme.owner_of("dataColors")
    if dtf is None or dtf is not theme.custom:
        return
    series = theme.data_colors[:max(0, int(o.cvd_palette_size))]
    gfx = []
    for i, c in enumerate(series):
        ratio = contrast_ratio(c, bg)
        if ratio < o.min_graphic_contrast:
            gfx.append(ev(dtf.rel, theme_line(dtf, ("dataColors", i)), f"$.dataColors[{i}]", detail=f"series colour {i + 1} {c} on {bg} = {ratio:.2f}:1"))
    if gfx:
        yield ctx.finding("A11Y-05", f"{len(gfx)} of the first {len(series)} theme data colours have less than {o.min_graphic_contrast:g}:1 contrast with the background (WCAG 1.4.11, graphical objects).",
                          gfx, severity="Medium", confidence="medium", count=len(gfx))
    pairs = confusable_pairs(series, o.cvd_delta_e)
    if pairs:
        evs = [ev(dtf.rel, theme_line(dtf, ("dataColors", j)), f"$.dataColors[{j}]",
                  detail=f"series {i + 1} {series[i]} vs series {j + 1} {series[j]}: delta E {sim:.1f} under {kind} (normal vision {normal:.0f})")
               for i, j, kind, sim, normal in pairs]
        yield ctx.finding("A11Y-07", f"{len(pairs)} pair(s) among the first {len(series)} theme data colours are hard to tell apart with red-green colour-vision deficiency.",
                          evs, confidence="medium", count=len(pairs))


# ---------------------------------------------------------------------------
# Optional PBIR schema validation (GOV-17 / GOV-18)
# ---------------------------------------------------------------------------


def check_schemas(ctx: Context) -> Iterable[Dict[str, Any]]:
    r = ctx.report
    if r is None or not ctx.options.validate_schemas or r.format != "PBIR":
        return
    cache = load_cache()
    unchecked: Dict[str, List[str]] = {}
    for jf in r.all_text:
        if jf.error is not None or not isinstance(jf.data, dict):
            continue
        url = jf.schema_url
        if not url:
            continue
        parsed = parse_schema_url(url)
        key = "/".join(parsed) if parsed else url.rsplit("/schema.json", 1)[0].split("/item/", 1)[-1]
        problems = check_document(jf.data, parsed[0], parsed[1], cache) if parsed else None
        if problems is None:
            unchecked.setdefault(key, []).append(jf.rel)
            continue
        if not problems:
            continue
        missing = [p for p in problems if p[0] != "property not allowed by the schema"]
        evs = []
        for what, prop in problems:
            line = jf.line_at((prop,)) if what == "property not allowed by the schema" else jf.line_at(("$schema",))
            evs.append(ev(jf.rel, line, "$" if what != "property not allowed by the schema" else f"$.{prop}", detail=f"{what}: {prop} ({key})"))
        yield ctx.finding("GOV-17", f"{jf.rel} does not match the top-level shape of its declared schema {key}: " +
                          "; ".join(f"{w} '{p}'" for w, p in problems) + ".",
                          evs, severity="High" if missing else "Medium")
    if unchecked:
        total = sum(len(v) for v in unchecked.values())
        evs = [ev(files[0], detail=f"{key}: {len(files)} file(s)") for key, files in sorted(unchecked.items())]
        yield ctx.finding("GOV-18", f"Schema not checked for {total} file(s): {len(unchecked)} declared schema version(s) are not in the local cache ({', '.join(sorted(unchecked))}).",
                          evs, count=total)


ALL_CHECKS: List[Callable[[Context], Iterable[Dict[str, Any]]]] = [
    check_format, check_binding, check_model, check_dax, check_slicers, check_windows, check_pages,
    check_colour, check_schemas,
]

SEVERITY_ORDER = {s: i for i, s in enumerate(["Critical", "High", "Medium", "Low", "Info"])}


def apply_policy(findings: List[Dict[str, Any]], options: Options) -> List[Dict[str, Any]]:
    """Drop disabled rules and apply severity overrides (config file)."""
    out = []
    for f in findings:
        if f["rule_id"] in options.disabled_rules:
            continue
        new = options.severity_overrides.get(f["rule_id"])
        if new and new != f["severity"]:
            f["original_severity"] = f["severity"]
            f["severity"] = new
        out.append(f)
    out.sort(key=lambda f: (SEVERITY_ORDER[f["severity"]], f["rule_id"], f["id"]))
    return out


def run_checks(project: Project, options: Optional[Options] = None) -> Tuple[List[Dict[str, Any]], Context]:
    ctx = Context(project, options or Options())
    findings: List[Dict[str, Any]] = []
    for chk in ALL_CHECKS:
        findings.extend(chk(ctx))
    return apply_policy(findings, ctx.options), ctx
