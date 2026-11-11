"""PBIR report loader (stdlib only).

Loads ``definition/report.json``, pages, visuals (including groups and
``mobile.json``), bookmarks and ``reportExtensions.json``. Every JSON file is kept
with its raw text so findings can point at a line number.

Also extracts every semantic-model reference (``SourceRef.Entity`` + ``Property``)
from queries, filters, bookmarks and formatting expressions, resolving
``SourceRef.Source`` aliases through the enclosing ``From`` list.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .jsonloc import JsonLocator, PathT, parse_path
from .theme import Theme, load_theme
from .tmdl import read_text

VALID_FOLDER_RE = re.compile(r"^[\w-]+$")
DECORATIVE_TYPES = {"textbox", "shape", "basicShape", "image", "actionButton", "pageNavigator", "bookmarkNavigator"}


@dataclass
class JsonFile:
    path: Path
    rel: str
    text: str
    data: Any
    error: Optional[str] = None
    _locator: Optional[JsonLocator] = field(default=None, repr=False, compare=False)

    def line_of(self, needle: str, start_line: int = 1) -> Optional[int]:
        """First 1-based line containing ``needle`` at or after start_line (text fallback)."""
        for n, line in enumerate(self.text.splitlines(), start=1):
            if n >= start_line and needle in line:
                return n
        return None

    @property
    def locator(self) -> JsonLocator:
        if self._locator is None:
            self._locator = JsonLocator(self.text or "")
        return self._locator

    def line_at(self, path) -> Optional[int]:
        """Line of the node at ``path`` (tuple or ``$.a.b[0]`` string); nearest ancestor if absent."""
        if isinstance(path, str):
            path = parse_path(path)
        if self.error is not None:
            return None
        return self.locator.line(tuple(path))

    @property
    def schema_url(self) -> Optional[str]:
        if isinstance(self.data, dict):
            v = self.data.get("$schema")
            return v if isinstance(v, str) else None
        return None


@dataclass
class FieldRef:
    kind: str  # Column | Measure | Hierarchy | HierarchyLevel | Variation
    entity: str
    prop: str
    json_path: str
    schema: Optional[str] = None  # "extension" for report-level measures
    level: Optional[str] = None


@dataclass
class Visual:
    name: str
    file: JsonFile
    page: "Page"
    data: Dict[str, Any]
    has_mobile: bool = False

    @property
    def visual(self) -> Dict[str, Any]:
        return self.data.get("visual") or {}

    @property
    def is_group(self) -> bool:
        return "visualGroup" in self.data and "visual" not in self.data

    @property
    def visual_type(self) -> str:
        return self.visual.get("visualType", "group" if self.is_group else "unknown")

    @property
    def is_hidden(self) -> bool:
        """Hidden itself or through any enclosing group (parentGroupName chain)."""
        return any(bool(v.data.get("isHidden")) for v in self.ancestors(include_self=True))

    @property
    def position(self) -> Dict[str, Any]:
        return self.data.get("position") or {}

    @property
    def parent_group(self) -> Optional[str]:
        return self.data.get("parentGroupName")

    def ancestors(self, include_self: bool = False) -> List["Visual"]:
        """This visual (optionally) and its enclosing groups, innermost first; cycle safe."""
        out: List[Visual] = [self] if include_self else []
        seen = {id(self)}
        v: Optional[Visual] = self
        while v is not None and v.parent_group:
            v = self.page.visual_named(v.parent_group)
            if v is None or id(v) in seen:
                break
            seen.add(id(v))
            out.append(v)
        return out

    @property
    def page_xy(self) -> Tuple[float, float]:
        """Top-left corner in page coordinates: PBIR stores group children relative to their group."""
        x = y = 0.0
        for v in self.ancestors(include_self=True):
            try:
                x += float(v.position.get("x", 0) or 0)
                y += float(v.position.get("y", 0) or 0)
            except (TypeError, ValueError):
                pass
        return x, y

    @property
    def sync_group(self) -> Optional[str]:
        sg = self.visual.get("syncGroup")
        if isinstance(sg, dict):
            return sg.get("groupName")
        return None

    def projections(self) -> List[Tuple[str, Dict[str, Any]]]:
        out = []
        qs = ((self.visual.get("query") or {}).get("queryState")) or {}
        for role, body in qs.items():
            for p in (body or {}).get("projections", []) or []:
                out.append((role, p))
        return out

    def projection_refs(self) -> List[FieldRef]:
        refs: List[FieldRef] = []
        qs = ((self.visual.get("query") or {}).get("queryState")) or {}
        collect_refs(qs, "$.visual.query.queryState", refs)
        return refs

    def container_literal(self, obj: str, prop: str) -> Optional[Any]:
        """Return the decoded literal of visualContainerObjects.<obj>[*].properties.<prop>.

        Returns "<expr>" when the value is bound to an expression (dynamic).
        """
        vco = self.visual.get("visualContainerObjects") or {}
        for entry in vco.get(obj, []) or []:
            props = (entry or {}).get("properties") or {}
            if prop in props:
                return decode_value(props[prop])
        return None

    @property
    def title_text(self) -> Optional[str]:
        v = self.container_literal("title", "text")
        return v if isinstance(v, str) else None

    @property
    def alt_text(self) -> Optional[str]:
        v = self.container_literal("general", "altText")
        return v if isinstance(v, str) else None


@dataclass
class Page:
    name: str
    folder: Path
    file: JsonFile
    data: Dict[str, Any]
    visuals: List[Visual] = field(default_factory=list)
    _by_name: Optional[Dict[str, Visual]] = field(default=None, repr=False, compare=False)

    def visual_named(self, name: str) -> Optional[Visual]:
        if self._by_name is None or len(self._by_name) != len(self.visuals):
            self._by_name = {v.name: v for v in self.visuals}
        return self._by_name.get(name)

    @property
    def display_name(self) -> str:
        return self.data.get("displayName", self.name)

    @property
    def is_hidden(self) -> bool:
        return self.data.get("visibility") == "HiddenInViewMode"

    @property
    def binding_type(self) -> Optional[str]:
        pb = self.data.get("pageBinding")
        if isinstance(pb, dict):
            return pb.get("type")
        return None

    @property
    def is_tooltip(self) -> bool:
        return self.data.get("type") == "Tooltip" or (self.binding_type or "").lower() == "tooltip"

    @property
    def is_drillthrough(self) -> bool:
        return (self.binding_type or "").lower() == "drillthrough"

    @property
    def width(self) -> float:
        return float(self.data.get("width") or 1280)

    @property
    def height(self) -> float:
        return float(self.data.get("height") or 720)


@dataclass
class Report:
    root: Path
    format: str  # PBIR | PBIR-Legacy | unknown
    definition_pbir: Optional[JsonFile] = None
    report_json: Optional[JsonFile] = None
    pages_json: Optional[JsonFile] = None
    pages: List[Page] = field(default_factory=list)
    bookmarks: List[JsonFile] = field(default_factory=list)
    extensions: Optional[JsonFile] = None
    extension_measures: Dict[str, set] = field(default_factory=dict)
    invalid_folders: List[Tuple[str, str]] = field(default_factory=list)  # (rel path, kind)
    json_errors: List[Tuple[str, str]] = field(default_factory=list)  # (rel path, message)
    all_text: List[JsonFile] = field(default_factory=list)
    theme: Theme = field(default_factory=Theme)

    def visuals(self) -> Iterable[Visual]:
        for p in self.pages:
            yield from p.visuals


def decode_value(value: Any) -> Any:
    """Decode a PBIR property value expression.

    ``{"expr":{"Literal":{"Value":"'text'"}}}`` -> ``"text"``; numbers lose their
    suffix (``12D`` -> 12.0); booleans become bool. Non-literal expressions
    (measure bound, ThemeDataColor...) return ``"<expr>"``.
    """
    if isinstance(value, dict) and "expr" in value:
        expr = value["expr"]
        if isinstance(expr, dict) and "Literal" in expr:
            return decode_literal(expr["Literal"].get("Value"))
        return "<expr>"
    if isinstance(value, dict) and "solid" in value:
        return decode_value((value.get("solid") or {}).get("color"))
    return value


def decode_literal(raw: Any) -> Any:
    if not isinstance(raw, str):
        return raw
    if len(raw) >= 2 and raw[0] == "'" and raw[-1] == "'":
        return raw[1:-1].replace("''", "'")
    if raw in ("true", "false"):
        return raw == "true"
    m = re.match(r"^(-?\d+(?:\.\d+)?)[DLM]?$", raw)
    if m:
        return float(m.group(1))
    return raw


def _load_json(path: Path, rel: str, report: Report) -> JsonFile:
    text = ""
    try:
        text = read_text(path)
        data = json.loads(text)
        jf = JsonFile(path, rel, text, data)
    except (OSError, ValueError) as exc:
        jf = JsonFile(path, rel, text, None, error=str(exc))
        report.json_errors.append((rel, str(exc)))
    report.all_text.append(jf)
    return jf


def collect_refs(node: Any, path: str, out: List[FieldRef], aliases: Optional[Dict[str, str]] = None) -> None:
    """Walk any PBIR JSON fragment and collect semantic-model field references."""
    aliases = dict(aliases or {})
    if isinstance(node, dict):
        frm = node.get("From")
        if isinstance(frm, list):
            for f in frm:
                if isinstance(f, dict) and "Name" in f and "Entity" in f:
                    aliases[f["Name"]] = f["Entity"]
        for kind in ("Column", "Measure"):
            v = node.get(kind)
            if isinstance(v, dict) and "Property" in v and isinstance(v.get("Expression"), dict):
                ent, schema = _entity(v["Expression"], aliases)
                if ent is not None:
                    out.append(FieldRef(kind, ent, v["Property"], f"{path}.{kind}", schema))
                elif "PropertyVariationSource" in v["Expression"]:
                    pvs = v["Expression"]["PropertyVariationSource"]
                    ent2, schema2 = _entity(pvs.get("Expression") or {}, aliases)
                    if ent2 is not None and pvs.get("Property"):
                        out.append(FieldRef("Variation", ent2, pvs["Property"], f"{path}.{kind}", schema2))
        h = node.get("Hierarchy")
        if isinstance(h, dict) and isinstance(h.get("Expression"), dict) and "Hierarchy" in h:
            expr = h["Expression"]
            if "PropertyVariationSource" in expr:
                pvs = expr["PropertyVariationSource"]
                ent, schema = _entity(pvs.get("Expression") or {}, aliases)
                if ent is not None and pvs.get("Property"):
                    out.append(FieldRef("Variation", ent, pvs["Property"], f"{path}.Hierarchy", schema))
            else:
                ent, schema = _entity(expr, aliases)
                if ent is not None:
                    out.append(FieldRef("Hierarchy", ent, h["Hierarchy"], f"{path}.Hierarchy", schema))
        for k, v in node.items():
            if k in ("Column", "Measure") and isinstance(v, dict) and "Property" in v:
                # already handled; still descend for nested expressions
                collect_refs(v.get("Expression"), f"{path}.{k}.Expression", out, aliases)
                continue
            if k == "Hierarchy" and isinstance(v, dict) and "Hierarchy" in v:
                continue
            collect_refs(v, f"{path}.{k}", out, aliases)
    elif isinstance(node, list):
        for idx, item in enumerate(node):
            collect_refs(item, f"{path}[{idx}]", out, aliases)


def _entity(expr: Dict[str, Any], aliases: Dict[str, str]) -> Tuple[Optional[str], Optional[str]]:
    sr = expr.get("SourceRef") if isinstance(expr, dict) else None
    if not isinstance(sr, dict):
        return None, None
    schema = sr.get("Schema")
    if "Entity" in sr:
        return sr["Entity"], schema
    if "Source" in sr:
        return aliases.get(sr["Source"]), schema
    return None, schema


def load_report(report_dir: Path, rel_base: Path) -> Report:
    def rel(p: Path) -> str:
        try:
            return p.relative_to(rel_base).as_posix()
        except ValueError:
            return p.as_posix()

    definition = report_dir / "definition"
    if definition.is_dir():
        fmt = "PBIR"
    elif (report_dir / "report.json").is_file():
        fmt = "PBIR-Legacy"
    else:
        fmt = "unknown"
    report = Report(root=report_dir, format=fmt)
    pbir = report_dir / "definition.pbir"
    if pbir.is_file():
        report.definition_pbir = _load_json(pbir, rel(pbir), report)
    if fmt != "PBIR":
        return report

    rj = definition / "report.json"
    if rj.is_file():
        report.report_json = _load_json(rj, rel(rj), report)
    report.theme = load_theme(report_dir, report.report_json.data if report.report_json else None, rel)
    pj = definition / "pages" / "pages.json"
    if pj.is_file():
        report.pages_json = _load_json(pj, rel(pj), report)
    ext = definition / "reportExtensions.json"
    if ext.is_file():
        report.extensions = _load_json(ext, rel(ext), report)
        data = report.extensions.data or {}
        for ent in data.get("entities", []) or []:
            names = {m.get("name", "").lower() for m in ent.get("measures", []) or []}
            report.extension_measures[(ent.get("name") or "").lower()] = names

    pages_dir = definition / "pages"
    order: List[str] = []
    if report.pages_json and isinstance(report.pages_json.data, dict):
        order = list(report.pages_json.data.get("pageOrder") or [])
    if pages_dir.is_dir():
        for folder in sorted(p for p in pages_dir.iterdir() if p.is_dir()):
            if not VALID_FOLDER_RE.match(folder.name):
                report.invalid_folders.append((rel(folder), "page"))
                continue
            pfile = folder / "page.json"
            if not pfile.is_file():
                continue
            jf = _load_json(pfile, rel(pfile), report)
            page = Page(name=folder.name, folder=folder, file=jf, data=jf.data if isinstance(jf.data, dict) else {})
            vdir = folder / "visuals"
            if vdir.is_dir():
                for vf in sorted(p for p in vdir.iterdir() if p.is_dir()):
                    if not VALID_FOLDER_RE.match(vf.name):
                        report.invalid_folders.append((rel(vf), "visual"))
                        continue
                    vjson = vf / "visual.json"
                    if not vjson.is_file():
                        continue
                    vj = _load_json(vjson, rel(vjson), report)
                    if not isinstance(vj.data, dict):
                        continue
                    page.visuals.append(Visual(
                        name=vj.data.get("name", vf.name), file=vj, page=page, data=vj.data,
                        has_mobile=(vf / "mobile.json").is_file(),
                    ))
            report.pages.append(page)
    if order:
        idx = {n: i for i, n in enumerate(order)}
        report.pages.sort(key=lambda p: idx.get(p.name, len(idx)))

    bdir = definition / "bookmarks"
    if bdir.is_dir():
        for bf in sorted(bdir.glob("*.bookmark.json")):
            report.bookmarks.append(_load_json(bf, rel(bf), report))
    return report
