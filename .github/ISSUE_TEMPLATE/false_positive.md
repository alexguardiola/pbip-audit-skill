---
name: False positive
about: The scanner reported something that is not a problem
title: "[FP] <RULE-ID>: <short description>"
labels: false-positive
---

**Rule ID and scanner version**
e.g. IN-05, pbip-audit-scan 0.2.0 (`"tool"` block of the JSON output)

**What the scanner reported**
Paste the finding message and evidence (file, line, json_path). Rename anything real.

**Minimal synthetic reproduction**
The smallest `visual.json` / `page.json` / TMDL snippet, with invented names, that triggers the finding.
Do not attach real project files, data, hosts or credentials.

```json

```

**Why it is wrong**
What the report or model actually does, and why a reader would not be affected.

**Options used**
Command line, `.pbip-audit.json` (if any), Desktop version that saved the files.
