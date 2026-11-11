#!/usr/bin/env python3
"""Render the rule sections of the pillar reference files from catalog.py.

    python render_catalog.py          # rewrite the generated blocks in place
    python render_catalog.py --check  # exit 1 if any file is out of date

Only the text between ``<!-- BEGIN GENERATED RULES -->`` and
``<!-- END GENERATED RULES -->`` is touched, so the hand-written introduction of
each pillar file stays as is.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pbip_audit.catalog import PILLARS, Rule, rules_for  # noqa: E402

SKILL_DIR = Path(__file__).resolve().parent.parent
BEGIN = "<!-- BEGIN GENERATED RULES -->"
END = "<!-- END GENERATED RULES -->"


def _scanner(r: Rule) -> str:
    if r.check == "D":
        return "scan.py" if r.implemented else "manual"
    return "agent" if r.check == "J" else "not offline"


def render_pillar(pillar: str) -> str:
    rules = rules_for(pillar)
    out = [BEGIN, "", "<!-- Generated from scripts/pbip_audit/catalog.py by scripts/render_catalog.py. Do not edit by hand. -->", ""]
    out.append("| ID | Title | Severity | Check | Who checks | Type |")
    out.append("|---|---|---|---|---|---|")
    for r in rules:
        out.append(f"| {r.id} | {r.title} | {r.severity} | {r.check} | {_scanner(r)} | {r.kind} |")
    out.append("")
    for r in rules:
        out.append(f"### {r.id} {r.title}")
        out.append("")
        out.append(f"- **Severity:** {r.severity}. **Check:** {r.check} ({_scanner(r)}). **Type:** {r.kind}.")
        out.append(f"- **Why:** {r.rationale}")
        out.append(f"- **How to verify:** {r.verify}")
        out.append(f"- **Fix:** {r.fix}")
        out.append(f"- **Source:** <{r.source}>")
        out.append("")
    out.append(END)
    return "\n".join(out)


def apply(text: str, block: str) -> str:
    if BEGIN in text and END in text:
        head = text.split(BEGIN, 1)[0]
        tail = text.split(END, 1)[1]
        return head + block + tail
    return text.rstrip("\n") + "\n\n" + block + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    stale = []
    for pillar, fname in PILLARS.items():
        path = SKILL_DIR / fname
        current = path.read_text(encoding="utf-8") if path.exists() else f"# {fname}\n"
        updated = apply(current, render_pillar(pillar))
        if updated != current:
            stale.append(fname)
            if not args.check:
                path.write_text(updated, encoding="utf-8", newline="\n")
    if args.check and stale:
        print("out of date: " + ", ".join(stale))
        return 1
    print("up to date" if args.check else f"rendered {len(PILLARS)} pillar files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
