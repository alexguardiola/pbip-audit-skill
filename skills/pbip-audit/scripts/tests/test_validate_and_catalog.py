import copy
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
SKILL = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import render_catalog  # noqa: E402
import scan  # noqa: E402
from pbip_audit.catalog import BY_ID, PILLARS, RULES, SEVERITIES  # noqa: E402
from pbip_audit.checks import Options  # noqa: E402
from validate_findings import validate_file  # noqa: E402


class ValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = scan.build_result(HERE / "fixtures" / "defects", Options(as_of_year=2026))

    def check(self, doc):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "f.json"
            p.write_text(json.dumps(doc), encoding="utf-8")
            return validate_file(p)

    def test_valid(self):
        self.assertEqual(self.check(self.doc), [])

    def test_bad_severity(self):
        d = copy.deepcopy(self.doc)
        d["findings"][0]["severity"] = "Severe"
        self.assertTrue(any("not in" in e for e in self.check(d)))

    def test_missing_evidence_and_extra_field(self):
        d = copy.deepcopy(self.doc)
        d["findings"][0]["evidence"] = []
        d["findings"][0]["oops"] = 1
        errs = self.check(d)
        self.assertTrue(any("fewer than 1" in e for e in errs))
        self.assertTrue(any("unexpected property 'oops'" in e for e in errs))

    def test_judgement_finding_accepted(self):
        d = copy.deepcopy(self.doc)
        d["findings"].append({
            "id": "ST-07#1", "rule_id": "ST-07", "title": "Chart type does not fit", "pillar": "storytelling",
            "severity": "Medium", "check_type": "J", "confidence": "medium", "classification": "recommendation",
            "message": "Trend shown as a pie.", "evidence": [{"file": "x/visual.json", "line": 3}], "status": "confirmed"})
        d["summary"]["total"] += 1
        d["summary"]["by_severity"]["Medium"] += 1
        self.assertEqual(self.check(d), [])

    def test_summary_mismatch(self):
        d = copy.deepcopy(self.doc)
        d["summary"]["total"] = 0
        self.assertTrue(any("summary.total" in e for e in self.check(d)))

    def test_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "f.json"
            p.write_text(json.dumps(self.doc), encoding="utf-8")
            out = subprocess.run([sys.executable, str(SCRIPTS / "validate_findings.py"), str(p)],
                                 capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
            self.assertIn("VALID", out.stdout)


class CatalogTests(unittest.TestCase):
    def test_catalog_is_well_formed(self):
        self.assertEqual(len(BY_ID), len(RULES), "duplicate rule ids")
        for r in RULES:
            self.assertRegex(r.id, r"^[A-Z0-9]+-[0-9]{2}$")
            self.assertIn(r.pillar, PILLARS)
            self.assertIn(r.severity, SEVERITIES)
            self.assertIn(r.check, ("D", "J", "R"))
            self.assertIn(r.kind, ("defect", "recommendation"))
            self.assertTrue(r.source.startswith("https://"), r.id)
            if r.implemented:
                self.assertEqual(r.check, "D", f"{r.id}: only D rules can be implemented")

    def test_emitted_ids_are_declared_and_implemented(self):
        src = "\n".join(p.read_text(encoding="utf-8") for p in (SCRIPTS / "pbip_audit").glob("*.py"))
        emitted = set(re.findall(r'finding\(\s*"([A-Z0-9]+-[0-9]{2})"', src))
        self.assertTrue(emitted)
        for rid in emitted:
            self.assertIn(rid, BY_ID)
            self.assertTrue(BY_ID[rid].implemented, f"{rid} is emitted but not marked implemented")
        implemented = {r.id for r in RULES if r.implemented}
        self.assertEqual(implemented - emitted, set(), "rules marked implemented but never emitted")

    def test_every_implemented_rule_is_exercised_by_a_fixture(self):
        seen = set()
        imp = HERE / "fixtures" / "imports"
        imports = {"bpa": [imp / "bpa_results.json"], "fabinspector": [imp / "fabinspector_results.json"]}
        for name in ("clean", "defects", "legacy", "thin", "tmsl"):
            res = scan.build_result(HERE / "fixtures" / name, Options(as_of_year=2026, validate_schemas=True), imports)
            seen |= {f["rule_id"] for f in res["findings"]}
        missing = {r.id for r in RULES if r.implemented} - seen
        self.assertEqual(missing, set(), "implemented rules without a seeded fixture defect")

    def test_pillar_docs_are_in_sync(self):
        self.assertEqual(render_catalog.main(["--check"]), 0, "run scripts/render_catalog.py")
        for pillar, fname in PILLARS.items():
            text = (SKILL / fname).read_text(encoding="utf-8")
            for r in RULES:
                if r.pillar == pillar:
                    self.assertIn(f"### {r.id} ", text)


if __name__ == "__main__":
    unittest.main()
