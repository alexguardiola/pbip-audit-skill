"""Tolerant TMDL parser (stdlib only).

TMDL is indentation based (one tab per level), case-insensitive, and YAML-like.
This parser does not try to be a full TmdlSerializer. It builds a node tree that
keeps file and line numbers, then projects the nodes we audit (tables, columns,
measures, partitions, relationships, roles, shared expressions, model settings)
into small dataclasses.

Unknown or malformed lines never raise: they are recorded in ``warnings`` so the
scanner can report them instead of crashing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

OBJECT_KEYWORDS = {
    "model", "database", "table", "column", "measure", "partition", "hierarchy",
    "level", "relationship", "role", "tablepermission", "columnpermission",
    "expression", "cultureinfo", "perspective", "perspectivetable",
    "perspectivecolumn", "perspectivemeasure", "perspectivehierarchy",
    "annotation", "extendedproperty", "calculationgroup", "calculationitem",
    "function", "datasource", "variation", "translation", "member", "kpi",
    "querygroup", "calendar", "objecttranslation", "linguisticmetadata",
    "detailrowsdefinition", "alternateof", "refreshpolicy", "dataaccessoptions",
}

# Keywords that are objects but never carry a name.
NAMELESS_OBJECTS = {"refreshpolicy", "dataaccessoptions", "kpi", "alternateof", "detailrowsdefinition"}

_PROP_RE = re.compile(r"^([A-Za-z_][\w]*)\s*:\s*(.*)$")
_PROP_EXPR_RE = re.compile(r"^([A-Za-z_][\w]*)\s*=\s*(.*)$")
_KW_RE = re.compile(r"^(ref\s+)?([A-Za-z_][\w]*)(?:\s+(.*))?$")


def read_text(path: Path) -> str:
    """Read a text file as UTF-8, tolerating a BOM and odd bytes."""
    data = path.read_bytes()
    return data.decode("utf-8-sig", errors="replace")


def _depth(line: str) -> Tuple[int, str]:
    """Return (indent depth, stripped text). Tabs count 1, four spaces count 1."""
    i = 0
    depth = 0
    spaces = 0
    while i < len(line) and line[i] in "\t ":
        if line[i] == "\t":
            depth += 1
            spaces = 0
        else:
            spaces += 1
            if spaces == 4:
                depth += 1
                spaces = 0
        i += 1
    return depth, line[i:].rstrip("\r\n")


def unquote_name(text: str) -> str:
    text = text.strip()
    if len(text) >= 2 and text[0] == "'" and text[-1] == "'":
        return text[1:-1].replace("''", "'")
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        return text[1:-1].replace('""', '"')
    return text


def parse_name(rest: str) -> Tuple[str, Optional[str]]:
    """Split ``'Name' = expr`` / ``Name = expr`` / ``Name`` into (name, expr|None)."""
    rest = rest.strip()
    if rest.startswith("'"):
        i = 1
        while i < len(rest):
            if rest[i] == "'":
                if i + 1 < len(rest) and rest[i + 1] == "'":
                    i += 2
                    continue
                break
            i += 1
        name = rest[1:i].replace("''", "'")
        tail = rest[i + 1:].strip()
    else:
        m = re.match(r"^(.*?)(\s*=\s*.*)?$", rest)
        name = (m.group(1) if m else rest).strip()
        tail = (m.group(2) or "").strip() if m else ""
    if tail.startswith("="):
        return name, tail[1:].strip()
    return name, None


def split_qualified(ref: str) -> List[str]:
    """Split ``'Table 1'.'Col'`` or ``Table.Col`` into parts, honouring quotes."""
    parts: List[str] = []
    buf = ""
    in_q = False
    i = 0
    ref = ref.strip()
    while i < len(ref):
        c = ref[i]
        if c == "'":
            if in_q and i + 1 < len(ref) and ref[i + 1] == "'":
                buf += "'"
                i += 2
                continue
            in_q = not in_q
        elif c == "." and not in_q:
            parts.append(buf)
            buf = ""
        else:
            buf += c
        i += 1
    parts.append(buf)
    return [p.strip() for p in parts]


@dataclass
class Node:
    kind: str
    name: Optional[str]
    file: str
    line: int
    depth: int
    value: Optional[str] = None  # expression text after "="
    value_line: Optional[int] = None
    props: Dict[str, str] = field(default_factory=dict)
    prop_lines: Dict[str, int] = field(default_factory=dict)
    children: List["Node"] = field(default_factory=list)
    description: Optional[str] = None
    is_ref: bool = False

    def child(self, kind: str) -> List["Node"]:
        return [c for c in self.children if c.kind == kind]

    def flag(self, key: str) -> bool:
        v = self.props.get(key.lower())
        if v is None:
            return False
        return v.strip().lower() not in ("false", "0")


def _consume_expression(lines: List[str], start: int, first: str, min_depth: int) -> Tuple[str, int]:
    """Consume a (possibly multi-line) expression. Returns (text, next index)."""
    if first.startswith("```"):
        body: List[str] = []
        rest = first[3:]
        if rest.strip():
            body.append(rest)
        j = start
        while j < len(lines):
            _, txt = _depth(lines[j])
            if txt.strip() == "```":
                return "\n".join(body), j + 1
            body.append(lines[j].rstrip("\r\n").lstrip("\t"))
            j += 1
        return "\n".join(body), j
    body = [first] if first else []
    j = start
    while j < len(lines):
        raw = lines[j].rstrip("\r\n")
        if not raw.strip():
            body.append("")
            j += 1
            continue
        d, txt = _depth(raw)
        if d >= min_depth:
            body.append(txt)
            j += 1
            continue
        break
    while body and not body[-1].strip():
        body.pop()
    return "\n".join(body), j


def parse_tmdl_text(text: str, file: str, warnings: Optional[List[str]] = None) -> List[Node]:
    """Parse one TMDL document into top-level nodes."""
    if warnings is None:
        warnings = []
    lines = text.splitlines()
    roots: List[Node] = []
    stack: List[Node] = []
    pending_desc: List[str] = []
    i = 0
    while i < len(lines):
        raw = lines[i]
        lineno = i + 1
        if not raw.strip():
            i += 1
            continue
        depth, txt = _depth(raw)
        i += 1
        if txt.startswith("///"):
            pending_desc.append(txt[3:].strip())
            continue
        while stack and stack[-1].depth >= depth:
            stack.pop()
        parent = stack[-1] if stack else None

        kw = _KW_RE.match(txt)
        prop = _PROP_RE.match(txt)
        keyword = kw.group(2).lower() if kw else ""
        is_object = bool(kw) and keyword in OBJECT_KEYWORDS and not prop and (
            kw.group(3) is not None and not kw.group(3).lstrip().startswith("=")
            or keyword in NAMELESS_OBJECTS
        )
        if is_object:
            is_ref = bool(kw.group(1))
            rest = kw.group(3) or ""
            if keyword in NAMELESS_OBJECTS and not rest:
                name, expr = None, None
            else:
                name, expr = parse_name(rest)
            node = Node(kind=keyword, name=name, file=file, line=lineno, depth=depth, is_ref=is_ref)
            if pending_desc:
                node.description = " ".join(pending_desc).strip()
            pending_desc = []
            if expr is not None:
                node.value_line = lineno
                node.value, i = _consume_expression(lines, i, expr, depth + 2)
            if parent is not None:
                parent.children.append(node)
            else:
                roots.append(node)
            stack.append(node)
            continue
        pending_desc = []
        if prop:
            key = prop.group(1).lower()
            if parent is not None:
                parent.props[key] = unquote_name(prop.group(2)) if prop.group(2).strip().startswith('"') else prop.group(2).strip()
                parent.prop_lines[key] = lineno
            continue
        pexpr = _PROP_EXPR_RE.match(txt)
        if pexpr:
            key = pexpr.group(1).lower()
            value, i = _consume_expression(lines, i, pexpr.group(2).strip(), depth + 1)
            if parent is not None:
                parent.props[key] = value
                parent.prop_lines[key] = lineno
            continue
        if re.match(r"^[A-Za-z_]\w*$", txt):
            # bare boolean property (e.g. isHidden) or nameless container
            key = txt.lower()
            node = Node(kind=key, name=None, file=file, line=lineno, depth=depth)
            if parent is not None:
                parent.props[key] = "true"
                parent.prop_lines[key] = lineno
                parent.children.append(node)
            else:
                roots.append(node)
            stack.append(node)
            continue
        warnings.append(f"{file}:{lineno}: unrecognised TMDL line: {txt[:80]}")
    return roots


# ---------------------------------------------------------------------------
# Projection into an auditable semantic model
# ---------------------------------------------------------------------------


@dataclass
class Column:
    name: str
    table: str
    file: str
    line: int
    data_type: Optional[str] = None
    is_hidden: bool = False
    format_string: Optional[str] = None
    summarize_by: Optional[str] = None
    description: Optional[str] = None
    expression: Optional[str] = None
    is_key: bool = False
    sort_by: Optional[str] = None
    data_category: Optional[str] = None
    variations: List[str] = field(default_factory=list)
    source_column: Optional[str] = None
    group_by: List[str] = field(default_factory=list)  # relatedColumnDetails groupByColumn (field parameters)
    is_parameter: bool = False  # extendedProperty ParameterMetadata (field parameter Fields column)


@dataclass
class Measure:
    name: str
    table: str
    file: str
    line: int
    expression: str = ""
    format_string: Optional[str] = None
    has_format_definition: bool = False
    is_hidden: bool = False
    display_folder: Optional[str] = None
    description: Optional[str] = None
    format_expression: Optional[str] = None  # formatStringDefinition DAX
    format_expression_line: Optional[int] = None
    kpi: List[Tuple[str, int, str]] = field(default_factory=list)  # (property, line, DAX)


@dataclass
class CalculationItem:
    name: str
    table: str
    file: str
    line: int
    expression: str = ""
    format_expression: Optional[str] = None
    format_expression_line: Optional[int] = None


@dataclass
class Function:
    name: str
    file: str
    line: int
    expression: str = ""


@dataclass
class Partition:
    name: str
    file: str
    line: int
    source_type: Optional[str] = None  # m | calculated | entity | ...
    mode: Optional[str] = None
    source: str = ""


@dataclass
class Table:
    name: str
    file: str
    line: int
    description: Optional[str] = None
    is_hidden: bool = False
    data_category: Optional[str] = None
    columns: Dict[str, Column] = field(default_factory=dict)
    measures: Dict[str, Measure] = field(default_factory=dict)
    hierarchies: Dict[str, List[str]] = field(default_factory=dict)
    partitions: List[Partition] = field(default_factory=list)
    has_refresh_policy: bool = False
    refresh_policy_line: Optional[int] = None
    is_calculation_group: bool = False
    calculation_items: List[CalculationItem] = field(default_factory=list)
    annotations: Dict[str, str] = field(default_factory=dict)

    @property
    def is_auto_date(self) -> bool:
        n = self.name.lower()
        return (
            n.startswith("localdatetable_")
            or n.startswith("datetabletemplate_")
            or "__pbi_localdatetable" in {k.lower() for k in self.annotations}
            or "__pbi_templatedatetable" in {k.lower() for k in self.annotations}
        )


@dataclass
class Relationship:
    name: str
    file: str
    line: int
    from_table: str = ""
    from_column: str = ""
    to_table: str = ""
    to_column: str = ""
    is_active: bool = True
    cross_filter: Optional[str] = None
    from_cardinality: Optional[str] = None
    to_cardinality: Optional[str] = None


@dataclass
class Role:
    name: str
    file: str
    line: int
    filters: List[Tuple[str, str, int]] = field(default_factory=list)  # (table, dax, line)


@dataclass
class SharedExpression:
    name: str
    file: str
    line: int
    value: str


@dataclass
class SemanticModel:
    root: Path
    tables: Dict[str, Table] = field(default_factory=dict)  # key: lower name
    relationships: List[Relationship] = field(default_factory=list)
    roles: List[Role] = field(default_factory=list)
    expressions: List[SharedExpression] = field(default_factory=list)
    functions: List[Function] = field(default_factory=list)
    model_props: Dict[str, str] = field(default_factory=dict)
    model_annotations: Dict[str, Tuple[str, int]] = field(default_factory=dict)
    model_file: Optional[str] = None
    model_line: Optional[int] = None
    warnings: List[str] = field(default_factory=list)

    def table(self, name: str) -> Optional[Table]:
        return self.tables.get(name.lower())

    def all_measures(self) -> List[Measure]:
        return [m for t in self.tables.values() for m in t.measures.values()]

    def all_columns(self) -> List[Column]:
        return [c for t in self.tables.values() for c in t.columns.values()]

    def dax_texts(self) -> List[Tuple[str, str, int, str]]:
        """Every DAX expression in the model: (kind, file, line, text)."""
        out: List[Tuple[str, str, int, str]] = []
        for t in self.tables.values():
            for m in t.measures.values():
                out.append(("measure", m.file, m.line, m.expression))
            for c in t.columns.values():
                if c.expression:
                    out.append(("column", c.file, c.line, c.expression))
            for p in t.partitions:
                if p.source_type == "calculated":
                    out.append(("partition", p.file, p.line, p.source))
        for r in self.roles:
            for (_tbl, dax, line) in r.filters:
                out.append(("role", r.file, line, dax))
        out.extend((kind, file, line, text) for (kind, _name, file, line, text) in self.extra_dax())
        return out

    def extra_dax(self) -> List[Tuple[str, str, str, int, str]]:
        """DAX outside measures, columns, partitions and roles: (kind, owner name, file, line, text).

        User-defined functions, calculation items, format string expressions and KPI expressions.
        """
        out: List[Tuple[str, str, str, int, str]] = []
        for t in self.tables.values():
            for m in t.measures.values():
                if m.format_expression:
                    out.append(("format string", m.name, m.file, m.format_expression_line or m.line, m.format_expression))
                for prop, line, text in m.kpi:
                    out.append(("KPI", m.name, m.file, line, text))
            for ci in t.calculation_items:
                out.append(("calculation item", ci.name, ci.file, ci.line, ci.expression))
                if ci.format_expression:
                    out.append(("format string", ci.name, ci.file, ci.format_expression_line or ci.line, ci.format_expression))
        for fn in self.functions:
            out.append(("function", fn.name, fn.file, fn.line, fn.expression))
        return out


def _rel(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def load_model(definition_dir: Path, rel_base: Path) -> SemanticModel:
    """Load every ``*.tmdl`` file under a SemanticModel ``definition`` folder."""
    model = SemanticModel(root=definition_dir)
    files = sorted(definition_dir.rglob("*.tmdl"))
    for path in files:
        rel = _rel(path, rel_base)
        try:
            text = read_text(path)
        except OSError as exc:  # pragma: no cover - IO failure
            model.warnings.append(f"{rel}: cannot read ({exc})")
            continue
        for node in parse_tmdl_text(text, rel, model.warnings):
            _project(model, node)
    return model


def _project(model: SemanticModel, node: Node) -> None:
    k = node.kind
    if k == "table" and not node.is_ref:
        _project_table(model, node)
    elif k == "model":
        model.model_file = node.file
        model.model_line = node.line
        model.model_props.update(node.props)
        for c in node.children:
            if c.kind == "annotation" and c.name:
                model.model_annotations[c.name] = ((c.value or "").strip(), c.line)
            elif c.kind == "table" and not c.is_ref:
                _project_table(model, c)
            elif c.kind == "relationship":
                _project_relationship(model, c)
    elif k == "annotation" and node.name:
        # top-level annotations in model.tmdl belong to the model
        if node.file.endswith("model.tmdl"):
            model.model_annotations[node.name] = ((node.value or "").strip(), node.line)
    elif k == "relationship":
        _project_relationship(model, node)
    elif k == "role":
        role = Role(name=node.name or "", file=node.file, line=node.line)
        for c in node.children:
            if c.kind == "tablepermission" and c.name:
                role.filters.append((c.name, c.value or "", c.line))
        model.roles.append(role)
    elif k == "expression" and node.name:
        model.expressions.append(SharedExpression(node.name, node.file, node.line, node.value or ""))
    elif k == "function" and node.name and not node.is_ref:
        model.functions.append(Function(node.name, node.file, node.line, node.value or ""))
    elif k == "database":
        for c in node.children:
            _project(model, c)


def _project_table(model: SemanticModel, node: Node) -> None:
    name = node.name or ""
    table = model.tables.get(name.lower())
    if table is None:
        table = Table(name=name, file=node.file, line=node.line)
        model.tables[name.lower()] = table
    if node.description:
        table.description = node.description
    table.is_hidden = table.is_hidden or node.flag("isHidden")
    if "datacategory" in node.props:
        table.data_category = node.props["datacategory"]
    for c in node.children:
        ck = c.kind
        if ck == "column" and c.name:
            col = Column(
                name=c.name, table=name, file=c.file, line=c.line,
                data_type=c.props.get("datatype"),
                is_hidden=c.flag("isHidden"),
                format_string=c.props.get("formatstring"),
                summarize_by=c.props.get("summarizeby"),
                description=c.description,
                expression=c.value,
                is_key=c.flag("isKey"),
                sort_by=unquote_name(c.props["sortbycolumn"]) if "sortbycolumn" in c.props else None,
                data_category=c.props.get("datacategory"),
                source_column=c.props.get("sourcecolumn"),
                is_parameter=any((e.name or "").lower() == "parametermetadata" for e in c.child("extendedproperty")),
            )
            for d in c.child("relatedcolumndetails"):
                if "groupbycolumn" in d.props:
                    col.group_by.append(unquote_name(d.props["groupbycolumn"]))
            for v in c.child("variation"):
                if "defaulthierarchy" in v.props:
                    col.variations.append(v.props["defaulthierarchy"])
            table.columns[c.name.lower()] = col
        elif ck == "measure" and c.name:
            me = table.measures[c.name.lower()] = Measure(
                name=c.name, table=name, file=c.file, line=c.line,
                expression=c.value or "",
                format_string=c.props.get("formatstring"),
                has_format_definition="formatstringdefinition" in c.props
                or bool(c.child("formatstringdefinition")),
                is_hidden=c.flag("isHidden"),
                display_folder=c.props.get("displayfolder"),
                description=c.description,
            )
            if c.props.get("formatstringdefinition", "").strip():
                me.format_expression = c.props["formatstringdefinition"]
                me.format_expression_line = c.prop_lines.get("formatstringdefinition")
            for k in c.child("kpi"):
                for prop in ("targetexpression", "statusexpression", "trendexpression"):
                    if (k.props.get(prop) or "").strip():
                        me.kpi.append((prop, k.prop_lines.get(prop, k.line), k.props[prop]))
        elif ck == "hierarchy" and c.name:
            levels = []
            for lv in c.child("level"):
                levels.append(unquote_name(lv.props.get("column", lv.name or "")))
            table.hierarchies[c.name.lower()] = levels
        elif ck == "partition" and c.name is not None:
            p = Partition(
                name=c.name, file=c.file, line=c.line,
                source_type=(c.value or "").strip().lower() or None,
                mode=c.props.get("mode"),
                source=c.props.get("source", ""),
            )
            table.partitions.append(p)
        elif ck == "refreshpolicy":
            table.has_refresh_policy = True
            table.refresh_policy_line = c.line
        elif ck == "calculationgroup":
            table.is_calculation_group = True
            for ci in c.child("calculationitem"):
                if ci.name is None:
                    continue
                fsd = ci.props.get("formatstringdefinition")
                table.calculation_items.append(CalculationItem(
                    name=ci.name, table=name, file=ci.file, line=ci.line, expression=ci.value or "",
                    format_expression=fsd if (fsd or "").strip() else None,
                    format_expression_line=ci.prop_lines.get("formatstringdefinition"),
                ))
        elif ck == "annotation" and c.name:
            table.annotations[c.name] = (c.value or "").strip()


def _project_relationship(model: SemanticModel, node: Node) -> None:
    rel = Relationship(name=node.name or "", file=node.file, line=node.line)
    fc = split_qualified(node.props.get("fromcolumn", ""))
    tc = split_qualified(node.props.get("tocolumn", ""))
    if len(fc) >= 2:
        rel.from_table, rel.from_column = ".".join(fc[:-1]), fc[-1]
    if len(tc) >= 2:
        rel.to_table, rel.to_column = ".".join(tc[:-1]), tc[-1]
    rel.is_active = node.props.get("isactive", "true").strip().lower() != "false"
    rel.cross_filter = node.props.get("crossfilteringbehavior")
    rel.from_cardinality = node.props.get("fromcardinality")
    rel.to_cardinality = node.props.get("tocardinality")
    model.relationships.append(rel)
