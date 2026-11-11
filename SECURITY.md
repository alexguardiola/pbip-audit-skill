# Security policy

## Supported versions

Only the latest released version receives fixes.

## Reporting a vulnerability

Please do **not** open a public issue. Use GitHub's private vulnerability reporting ("Security" tab, "Report a vulnerability") on this repository. Include the version, the command you ran, and a synthetic reproduction. You should get an acknowledgement within a week.

## Scope and design notes

- `scan.py` reads files only, never uses the network, and writes only the file named by `--out`. A report of any other write or network access is a security bug.
- Audited projects are untrusted input. A crafted PBIR or TMDL file must not cause code execution, writes outside `--out`, or unbounded resource use; reports of crashes or hangs on malformed input are welcome.
- GOV-09 reports password-like strings in M code by file and line; it never prints the value. If you see a secret value in scanner output, report it as a vulnerability.
- The skill instructs agents to keep audits read-only and not to paste data literals or credentials into reports. Prompt-injection content inside audited files (for example instructions hidden in a description) should be treated as data; reports of agent workflows that can be steered by project content are in scope.

## Never share real project files

When reporting anything, use synthetic files. Do not attach real `.pbip` projects, data, hosts or credentials.
