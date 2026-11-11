import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
ROOT = SCRIPTS.parents[2]
FIX = HERE / "fixtures"
sys.path.insert(0, str(SCRIPTS))

from pbip_audit import __version__  # noqa: E402
import scan  # noqa: E402


def run_module(*args):
    return subprocess.run([sys.executable, "-m", "pbip_audit", *args], cwd=str(SCRIPTS),
                          capture_output=True, text=True, encoding="utf-8")


class ModuleEntryPoint(unittest.TestCase):
    def test_version_flag(self):
        out = run_module("--version")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "pbip-audit " + __version__)

    def test_module_scans_like_the_script(self):
        out = run_module(str(FIX / "defects"), "--as-of-year", "2026", "--fail-on", "Critical")
        self.assertEqual(out.returncode, 2, out.stderr)
        self.assertGreater(json.loads(out.stdout)["summary"]["total"], 0)

    def test_script_still_runs(self):
        out = subprocess.run([sys.executable, str(SCRIPTS / "scan.py"), "--version"],
                             capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "pbip-audit " + __version__)


class SarifPathPrefix(unittest.TestCase):
    def sarif_uris(self, *extra):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out.sarif"
            code = scan.main([str(FIX / "defects"), "--as-of-year", "2026", "--format", "sarif", "--out", str(out), *extra])
            self.assertEqual(code, 0)
            doc = json.loads(out.read_text(encoding="utf-8"))
        return [loc["physicalLocation"]["artifactLocation"]["uri"]
                for res in doc["runs"][0]["results"] for loc in res.get("locations", [])]

    def test_auto_prefix_is_the_project_folder_relative_to_cwd(self):
        expected = Path(os.path.relpath(str(FIX / "defects"), os.getcwd())).as_posix() + "/"
        uris = self.sarif_uris("--path-prefix", "auto")
        self.assertTrue(uris)
        self.assertTrue(all(u.startswith(expected) for u in uris), uris[:3])

    def test_windows_prefix_with_trailing_backslash(self):
        uris = self.sarif_uris("--path-prefix", "reports\\Sales\\")
        self.assertTrue(all(u.startswith("reports/Sales/") and "//" not in u for u in uris), uris[:3])

    def test_default_prefix_unchanged(self):
        uris = self.sarif_uris()
        self.assertTrue(any(u.startswith("Defects.") for u in uris), uris[:3])


class Manifests(unittest.TestCase):
    def load(self, rel):
        return json.loads((ROOT / rel).read_text(encoding="utf-8"))

    def test_plugin_and_marketplace_agree(self):
        plugin = self.load(".claude-plugin/plugin.json")
        market = self.load(".claude-plugin/marketplace.json")
        self.assertEqual(plugin["version"], __version__)
        entries = [p for p in market["plugins"] if p["name"] == plugin["name"]]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["source"], "./")
        self.assertNotEqual(market["name"], plugin["name"])

    def test_skill_is_where_the_plugin_loads_it(self):
        skill = (ROOT / "skills" / "pbip-audit" / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(re.search(r"^name: pbip-audit$", skill, re.M))

    def test_pyproject_reads_the_package_version(self):
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('dynamic = ["version"]', text)
        self.assertIn('version = { attr = "pbip_audit.__version__" }', text)
        self.assertIn('pbip-audit = "pbip_audit.cli:main"', text)

    def test_action_runs_the_bundled_scanner(self):
        text = (ROOT / "action.yml").read_text(encoding="utf-8")
        self.assertIn("skills/pbip-audit/scripts/scan.py", text)
        self.assertIn("github/codeql-action/upload-sarif", text)


if __name__ == "__main__":
    unittest.main()
