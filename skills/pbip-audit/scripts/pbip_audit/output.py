"""Output renderers: scores, Markdown report and SARIF 2.1.0.

Score formula (documented in VALIDATION-AND-REPORTING.md and the report itself):

    pillar score = max(0, 100 - sum(weight[severity] for each counted finding in the pillar))
    weights: Critical 25, High 10, Medium 4, Low 1, Info 0
    overall score = mean of the assessed core pillar scores (rounded)

A pillar is not assessed (score null) when the files it needs are missing or in a
format the scanner does not read: report pillars when the report is not PBIR,
model and DAX when the model is not TMDL. A finding counts once, however many locations it aggregates. Findings marked
``status: false_positive`` are not counted. Scores rank where to look first; they
are not a certification and are not comparable across projects of very different
size.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Set

from .catalog import BY_ID, PILLARS, SEVERITIES

SEVERITY_WEIGHTS = {"Critical": 25, "High": 10, "Medium": 4, "Low": 1, "Info": 0}
PILLAR_LABELS = {
    "model": "Model and binding", "dax": "DAX", "performance": "Performance",
    "governance": "Governance and AI readiness", "visual-design": "Visual design",
    "storytelling": "Storytelling", "interaction": "Interaction", "accessibility": "Accessibility",
    "mobile": "Mobile", "domain": "Domain rules",
}
SARIF_LEVEL = {"Critical": "error", "High": "error", "Medium": "warning", "Low": "note", "Info": "note"}
SARIF_SECURITY = {"Critical": "9.0", "High": "7.0", "Medium": "5.0", "Low": "3.0", "Info": "1.0"}
INFO_URI = "https://github.com/alexguardiola/pbip-audit-skill"


REPORT_PILLARS = ("performance", "visual-design", "storytelling", "interaction", "accessibility", "mobile")
MODEL_PILLARS = ("model", "dax")


def assessed_pillars(report_format: str, model_format: str) -> Set[str]:
    """Core pillars the scanner could assess from the files present."""
    out = set(PILLARS)
    if report_format != "PBIR":
        out -= set(REPORT_PILLARS)
    if model_format != "TMDL":
        out -= set(MODEL_PILLARS)
    return out


def counted(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [f for f in findings if f.get("status") != "false_positive"]


def scores(findings: List[Dict[str, Any]], assessed: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    """Pillar and overall scores. ``assessed``: core pillars that could be assessed (default: all)."""
    ok = set(PILLARS) if assessed is None else set(assessed)
    per: Dict[str, Dict[str, Any]] = {}
    pillars = list(PILLARS) + sorted({f["pillar"] for f in findings} - set(PILLARS))
    for p in pillars:
        fs = [f for f in counted(findings) if f["pillar"] == p]
        by_sev = {s: sum(1 for f in fs if f["severity"] == s) for s in SEVERITIES}
        penalty = sum(SEVERITY_WEIGHTS[s] * n for s, n in by_sev.items())
        is_ok = p in ok or p not in PILLARS
        per[p] = {"score": max(0, 100 - penalty) if is_ok else None, "penalty": penalty, "by_severity": by_sev,
                  "assessed": is_ok}
    core = [per[p]["score"] for p in PILLARS if per[p]["assessed"]]
    skipped = [p for p in PILLARS if not per[p]["assessed"]]
    if skipped:
        overall_txt = (f"overall = mean of the {len(core)} assessed core pillars; not assessed (files missing or not "
                       f"PBIR/TMDL): {', '.join(skipped)}")
    else:
        overall_txt = "overall = mean of the nine core pillars"
    return {
        "formula": "pillar = max(0, 100 - sum(weights[severity])) per counted finding; " + overall_txt,
        "weights": dict(SEVERITY_WEIGHTS),
        "overall": round(sum(core) / len(core)) if core else None,
        "pillars": per,
    }


def _band(score: Optional[int]) -> str:
    if score is None:
        return "not assessed"
    return "good" if score >= 90 else ("fair" if score >= 70 else "needs work")


def _score_text(score: Optional[int]) -> str:
    return "not assessed" if score is None else str(score)


def _loc(e: Dict[str, Any]) -> str:
    return e["file"] + (f":{e['line']}" if e.get("line") else "")


def to_markdown(result: Dict[str, Any], max_evidence: int = 10) -> str:
    t = result["target"]
    findings = result["findings"]
    sc = result.get("scores") or scores(findings)
    out: List[str] = []
    out.append(f"# PBIP audit: {t['pbip'] or t.get('report_path') or t.get('model_path')}")
    out.append("")
    out.append(f"Scanner {result['tool']['version']} at {result['generated_at']}. Report format: {t['report_format']}; "
               f"model format: {t['model_format']}; thin report: {t['thin_report']}.")
    st = result["stats"]
    out.append("")
    out.append(f"Scanned {st['pages']} pages, {st['visuals']} visuals, {st['tables']} tables, {st['measures']} measures, "
               f"{st['relationships']} relationships.")
    theme = result.get("theme") or {}
    if theme:
        out.append(f"Theme: base `{theme.get('base')}`" + (f", custom `{theme.get('custom')}`" if theme.get("custom") else "") + ".")
    out.append("")

    # executive summary
    c = counted(findings)
    by_sev = {s: sum(1 for f in c if f["severity"] == s) for s in SEVERITIES}
    out.append("## Executive summary")
    out.append("")
    if not c:
        out.append("No deterministic findings. Judgement (J) rules and runtime (R) rules still need review; see below.")
    else:
        worst = next(s for s in SEVERITIES if by_sev[s])
        top = [f for f in c if f["severity"] == worst][:3]
        weakest = sorted((p for p in PILLARS if sc["pillars"][p].get("score") is not None),
                         key=lambda p: sc["pillars"][p]["score"])[:2]
        overall = f"Overall score {sc['overall']}/100 ({_band(sc['overall'])})" if sc["overall"] is not None else "Overall score not assessed"
        out.append(f"{len(c)} deterministic finding(s): " + ", ".join(f"{n} {s}" for s, n in by_sev.items() if n) + ". "
                   f"{overall}. "
                   f"Weakest pillars: " + ", ".join(f"{PILLAR_LABELS[p]} ({sc['pillars'][p]['score']})" for p in weakest) + ".")
        out.append("")
        out.append(f"Fix first ({worst}):")
        out.append("")
        for f in top:
            out.append(f"- **{f['id']}** {f['title']}: {f['message']}")
    out.append("")
    out.append("These are scanner findings only. Each one should be confirmed by reading its evidence; judgement rules are not covered by this file.")
    out.append("")

    # scorecard
    out.append("## Score per pillar")
    out.append("")
    out.append("| Pillar | Score | Critical | High | Medium | Low | Info |")
    out.append("|---|---|---|---|---|---|---|")
    for p, row in sc["pillars"].items():
        b = row["by_severity"]
        out.append(f"| {PILLAR_LABELS.get(p, p)} | {_score_text(row.get('score'))} | " + " | ".join(str(b[s]) for s in SEVERITIES) + " |")
    out.append(f"| **Overall** | **{_score_text(sc['overall'])}** | " + " | ".join(str(by_sev[s]) for s in SEVERITIES) + " |")
    out.append("")
    w = sc["weights"]
    skipped = [PILLAR_LABELS.get(p, p) for p in PILLARS if p in sc["pillars"] and sc["pillars"][p].get("score") is None]
    if skipped:
        overall_txt = (f"overall = mean of the {len(PILLARS) - len(skipped)} assessed pillars; not assessed because their files are "
                       f"missing or not in PBIR/TMDL format: {', '.join(skipped)}")
    else:
        overall_txt = "overall = mean of the nine pillars"
    out.append(f"Formula: pillar score = max(0, 100 - sum of severity weights of its findings); weights Critical {w['Critical']}, "
               f"High {w['High']}, Medium {w['Medium']}, Low {w['Low']}, Info {w['Info']}; a finding counts once however many "
               f"locations it lists; false positives are excluded; {overall_txt}. Use it to rank work, not to certify.")
    out.append("")

    # findings, by severity then pillar
    out.append("## Findings")
    out.append("")
    if not findings:
        out.append("No deterministic findings.")
        out.append("")
    for sev in SEVERITIES:
        group = [f for f in findings if f["severity"] == sev]
        if not group:
            continue
        out.append(f"### {sev} ({len(group)})")
        out.append("")
        pillars = list(PILLARS) + sorted({f["pillar"] for f in group} - set(PILLARS))
        for p in pillars:
            pg = [f for f in group if f["pillar"] == p]
            if not pg:
                continue
            out.append(f"#### {PILLAR_LABELS.get(p, p)}")
            out.append("")
            for f in pg:
                status = f" [{f['status']}]" if f.get("status") else ""
                out.append(f"##### {f['id']} {f['title']}{status}")
                out.append("")
                out.append(f["message"])
                out.append("")
                meta = f"Check: {f['check_type']}. Confidence: {f['confidence']}. Type: {f['classification']}."
                if f.get("original_severity"):
                    meta += f" Severity overridden by config (was {f['original_severity']})."
                if f.get("origin"):
                    meta += f" Imported from {f['origin'].get('tool')} (rule {f['origin'].get('rule_id')})."
                out.append(meta)
                out.append("")
                for e in f["evidence"][:max_evidence]:
                    extra = " ".join(x for x in [e.get("json_path"), e.get("detail")] if x)
                    out.append(f"- `{_loc(e)}`" + (f" {extra}" if extra else ""))
                more = f.get("count", len(f["evidence"])) - min(max_evidence, len(f["evidence"]))
                if more > 0:
                    out.append(f"- ... and {more} more")
                out.append("")
                if f.get("reviewer_note"):
                    out.append(f"Reviewer note: {f['reviewer_note']}")
                    out.append("")
                out.append(f"Fix: {f.get('fix', '')}" + (f" ([source]({f['source']}))" if f.get("source") else ""))
                out.append("")

    out.append("## Not assessable offline")
    out.append("")
    out.append("These runtime (R) rules need the Power BI Service, a running model or usage data. They were not checked:")
    out.append("")
    for na in result["not_assessable"]:
        out.append(f"- **{na['rule_id']}** {na['title']}: {na.get('reason', '')}")
    out.append("")
    if result.get("notes"):
        out.append("## Scanner notes")
        out.append("")
        for n in result["notes"]:
            out.append(f"- {n}")
        out.append("")
    return "\n".join(out)


def _rule_descriptor(rule_id: str) -> Dict[str, Any]:
    r = BY_ID[rule_id]
    return {
        "id": r.id,
        "name": "".join(w.capitalize() for w in r.title.replace("/", " ").replace("-", " ").split() if w.isalnum())[:80] or r.id,
        "shortDescription": {"text": r.title},
        "fullDescription": {"text": r.rationale},
        "help": {"text": f"How to verify: {r.verify}\nFix: {r.fix}", "markdown": f"**How to verify:** {r.verify}\n\n**Fix:** {r.fix}"},
        "helpUri": r.source,
        "defaultConfiguration": {"level": SARIF_LEVEL[r.severity]},
        "properties": {"pillar": r.pillar, "severity": r.severity, "check": r.check, "type": r.kind,
                       "tags": ["power-bi", "pbip", r.pillar], "security-severity": SARIF_SECURITY[r.severity]},
    }


def to_sarif(result: Dict[str, Any], path_prefix: str = "") -> Dict[str, Any]:
    """SARIF 2.1.0 for GitHub code scanning. ``path_prefix`` is prepended to evidence
    paths (which are relative to the folder holding the .pbip) so that they become
    relative to the repository root."""
    prefix = path_prefix.replace("\\", "/").strip("/")
    prefix = prefix + "/" if prefix else ""
    findings = [f for f in result["findings"] if f.get("status") != "false_positive"]
    used = sorted({f["rule_id"] for f in findings if f["rule_id"] in BY_ID})
    index = {rid: i for i, rid in enumerate(used)}
    results = []
    for f in findings:
        locs = []
        for e in f["evidence"][:10]:
            phys: Dict[str, Any] = {"artifactLocation": {"uri": prefix + e["file"], "uriBaseId": "%SRCROOT%"}}
            if e.get("line"):
                phys["region"] = {"startLine": int(e["line"])}
            loc: Dict[str, Any] = {"physicalLocation": phys}
            label = " ".join(x for x in [e.get("json_path"), e.get("detail")] if x)
            if label:
                loc["message"] = {"text": label}
            locs.append(loc)
        res: Dict[str, Any] = {
            "ruleId": f["rule_id"],
            "level": SARIF_LEVEL[f["severity"]],
            "message": {"text": f["message"]},
            "locations": locs,
            "partialFingerprints": {"pbipAudit/v1": f"{f['rule_id']}|{f['evidence'][0]['file']}|{f['message'][:120]}"},
            "properties": {"severity": f["severity"], "pillar": f["pillar"], "confidence": f["confidence"],
                           "classification": f["classification"], "findingId": f["id"]},
        }
        if f["rule_id"] in index:
            res["ruleIndex"] = index[f["rule_id"]]
        if f.get("origin"):
            res["properties"]["origin"] = f["origin"]
        if f.get("status"):
            res["properties"]["status"] = f["status"]
        results.append(res)
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {
                "name": "pbip-audit",
                "version": result["tool"]["version"],
                "semanticVersion": result["tool"]["version"],
                "informationUri": INFO_URI,
                "rules": [_rule_descriptor(rid) for rid in used],
            }},
            "originalUriBaseIds": {"%SRCROOT%": {"description": {"text": "Repository root (evidence paths are relative to the folder holding the .pbip, plus --path-prefix)."}}},
            "automationDetails": {"id": f"pbip-audit/{result['target'].get('pbip') or 'project'}/"},
            "results": results,
            "properties": {"notAssessable": [na["rule_id"] for na in result.get("not_assessable", [])]},
        }],
    }
