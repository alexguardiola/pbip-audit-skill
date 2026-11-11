#!/usr/bin/env python3
"""pbip-audit scanner: deterministic (D) findings for a Power BI PBIP project.

Usage:
    python scan.py <path-to-.pbip-or-folder> [--format json|md|sarif] [--out FILE]
                   [--config FILE] [--max-visuals N] [--max-fields N] [--as-of-year YYYY]
                   [--tab-order-tolerance R] [--tab-order-row-band PX]
                   [--external-usage FILE] [--validate-schemas]
                   [--import-bpa FILE] [--import-fabinspector FILE]
                   [--path-prefix PREFIX] [--fail-on SEVERITY] [--version]

Reads files only and never uses the network. Never writes anything except ``--out``.
Python 3.8+ standard library only.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pbip_audit.cli import SCHEMA_VERSION, build_result, main  # noqa: E402,F401
from pbip_audit.output import scores, to_markdown, to_sarif  # noqa: E402,F401

if __name__ == "__main__":
    sys.exit(main())
