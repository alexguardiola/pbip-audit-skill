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


@dataclass
class Target:
    """What to audit: a .pbip file, or (Fabric Git layout) one *.Report or *.SemanticModel folder."""
    pbip: Optional[Path]
    base: Path
    report_dir: Optional[Path] = None
    model_dir: Optional[Path] = None


def _is_report_dir(p: Path) -> bool:
    return p.is_dir() and p.name.lower().endswith(".report") and (p / "definition.pbir").is_file()


def _is_model_dir(p: Path) -> bool:
    return p.is_dir() and p.name.lower().endswith(".semanticmodel") and (
        (p / "definition").is_dir() or (p / "model.bim").is_file() or (p / "definition.pbism").is_file())


def _folders(path: Path, suffix: str, test) -> List[Path]:
    return [p for p in sorted(path.glob("*" + suffix)) if test(p)] or [p for p in sorted(path.rglob("*" + suffix)) if test(p)]


def _several(what: str, found: List[Path]) -> DiscoveryError:
    listing = "\n  ".join(str(f) for f in found)
    return DiscoveryError(f"Several {what} found; pass one explicitly:\n  {listing}")


def find_target(path: Path) -> Target:
    """Find the project: a .pbip file first; without one, a single *.Report or *.SemanticModel folder."""
    path = path.resolve()
    if path.is_file() and path.suffix.lower() == ".pbip":
        return Target(path, path.parent)
    if not path.is_dir():
        raise DiscoveryError(f"Not a .pbip file or folder: {path}")
    if _is_report_dir(path):
        return Target(None, path.parent, report_dir=path)
    if _is_model_dir(path):
        return Target(None, path.parent, model_dir=path)
    found = sorted(path.glob("*.pbip")) or sorted(path.rglob("*.pbip"))
    if len(found) == 1:
        return Target(found[0], found[0].parent)
    if found:
        raise _several(".pbip files", found)
    reports = _folders(path, ".Report", _is_report_dir)
    if len(reports) == 1:
        return Target(None, reports[0].parent, report_dir=reports[0])
    if reports:
        raise _several("*.Report folders (no .pbip file)", reports)
    models = _folders(path, ".SemanticModel", _is_model_dir)
    if len(models) == 1:
        return Target(None, models[0].parent, model_dir=models[0])
    if models:
        raise _several("*.SemanticModel folders (no .pbip file)", models)
    raise DiscoveryError(f"No .pbip file found under {path} (nor a *.Report or *.SemanticModel folder)")


def find_pbip(path: Path) -> Path:
    """The .pbip file of a project; raises DiscoveryError when the target has none."""
    t = find_target(path)
    if t.pbip is None:
        raise DiscoveryError(f"No .pbip file found under {path.resolve()}")
    return t.pbip


def _artifact_report(pbip: Path, base: Path) -> Optional[Path]:
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
        return (base / report_rel).resolve()
    cands = sorted(base.glob("*.Report"))
    return cands[0] if cands else None


def load_project(path: Path) -> Project:
    target = find_target(path)
    base = target.base
    proj = Project(pbip=target.pbip, base=base)
    if target.pbip is not None:
        proj.report_dir = _artifact_report(target.pbip, base)
    elif target.report_dir is not None:
        proj.report_dir = target.report_dir
        proj.notes.append(f"No .pbip file: audited the Fabric Git folder {target.report_dir.name} and the semantic model it references; "
                          f"evidence paths are relative to {base.name}/.")
    else:
        proj.model_dir = target.model_dir
        proj.notes.append(f"No .pbip file and no report: audited the semantic model folder {target.model_dir.name} only; "
                          f"report rules were not run. Evidence paths are relative to {base.name}/.")

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
    if proj.model_dir is None and not proj.thin and target.pbip is not None:
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
