"""PBIP project discovery."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from .pbir import Report, load_report
from .tmdl import SemanticModel, load_model, read_text


class DiscoveryError(Exception):
    pass


@dataclass
class Project:
    pbip: Optional[Path]
    base: Path  # folder that holds the .pbip; evidence paths are relative to it
    report_dir: Optional[Path] = None
    model_dir: Optional[Path] = None
    model_format: str = "none"  # TMDL | TMSL | none
    thin: bool = False
    report: Optional[Report] = None
    model: Optional[SemanticModel] = None
    notes: List[str] = field(default_factory=list)


def find_pbip(path: Path) -> Path:
    path = path.resolve()
    if path.is_file() and path.suffix.lower() == ".pbip":
        return path
    if path.is_dir():
        found = sorted(path.glob("*.pbip")) or sorted(path.rglob("*.pbip"))
        if len(found) == 1:
            return found[0]
        if not found:
            raise DiscoveryError(f"No .pbip file found under {path}")
        listing = "\n  ".join(str(f) for f in found)
        raise DiscoveryError(f"Several .pbip files found; pass one explicitly:\n  {listing}")
    raise DiscoveryError(f"Not a .pbip file or folder: {path}")


def load_project(path: Path) -> Project:
    pbip = find_pbip(path)
    base = pbip.parent
    proj = Project(pbip=pbip, base=base)
    try:
        data = json.loads(read_text(pbip))
    except ValueError as exc:
        raise DiscoveryError(f"Cannot parse {pbip}: {exc}")
    report_rel = None
    for art in data.get("artifacts", []) or []:
        if isinstance(art, dict) and "report" in art:
            report_rel = (art["report"] or {}).get("path")
            break
    if report_rel:
        proj.report_dir = (base / report_rel).resolve()
    else:
        cands = sorted(base.glob("*.Report"))
        proj.report_dir = cands[0] if cands else None

    if proj.report_dir and proj.report_dir.is_dir():
        proj.report = load_report(proj.report_dir, base)
        ref = None
        if proj.report.definition_pbir and isinstance(proj.report.definition_pbir.data, dict):
            ref = proj.report.definition_pbir.data.get("datasetReference") or {}
        if ref:
            if ref.get("byPath") and ref["byPath"].get("path"):
                proj.model_dir = (proj.report_dir / ref["byPath"]["path"]).resolve()
            elif "byConnection" in ref:
                proj.thin = True
    if proj.model_dir is None and not proj.thin:
        cands = sorted(base.glob("*.SemanticModel"))
        if cands:
            proj.model_dir = cands[0]

    if proj.model_dir and proj.model_dir.is_dir():
        definition = proj.model_dir / "definition"
        if definition.is_dir():
            proj.model_format = "TMDL"
            proj.model = load_model(definition, base)
        elif (proj.model_dir / "model.bim").is_file():
            proj.model_format = "TMSL"
    return proj
