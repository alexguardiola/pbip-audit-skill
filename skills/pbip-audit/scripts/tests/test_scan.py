import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import scan  # noqa: E402
from pbip_audit.checks import Options, has_unsafe_division, strip_dax  # noqa: E402
from validate_findings import semantic_checks, validate  # noqa: E402

FIX = HERE / "fixtures"
SCHEMA = json.loads((HERE.parent.parent / "report-schema.json").read_text(encoding="utf-8"))
OPTS = Options(as_of_year=2026)


def run(name):
    return scan.build_result(FIX / name, OPTS)


def rule_ids(result):
    return [f["rule_id"] for f in result["findings"]]


class CleanProjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = run("clean")

    def test_no_findings(self):
        self.assertEqual(self.result["findings"], [], json.dumps(self.result["findings"], indent=1))

    def test_detection(self):
        t = self.result["target"]
        self.assertEqual(t["report_format"], "PBIR")
        self.assertEqual(t["model_format"], "TMDL")
        self.assertFalse(t["thin_report"])
        self.assertEqual(self.result["stats"]["pages"], 3)
        self.assertEqual(self.result["stats"]["measures"], 5)

    def test_schema_valid(self):
        self.assertEqual(validate(self.result, SCHEMA, SCHEMA) + semantic_checks(self.result), [])


class DefectProjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = run("defects")
        cls.ids = rule_ids(cls.result)

    def find(self, rule_id, contains=""):
        hits = [f for f in self.result["findings"] if f["rule_id"] == rule_id and contains in f["message"]]
        self.assertTrue(hits, f"expected {rule_id} containing {contains!r}; got {sorted(set(self.ids))}")
        return hits

    def test_schema_valid(self):
        self.assertEqual(validate(self.result, SCHEMA, SCHEMA) + semantic_checks(self.result), [])

    # binding
    def test_bind_01_missing_measure_and_table(self):
        f = self.find("BIND-01", "'Orders'[Ghost Measure]")[0]
        self.assertEqual(f["severity"], "Critical")
        self.assertTrue(f["evidence"][0]["file"].endswith("visuals/broken/visual.json"))
        self.assertIsNotNone(f["evidence"][0].get("line"))
        self.find("BIND-01", "Missing table: 'Missing'[Thing]")

    def test_bind_03_stale_bookmark(self):
        f = self.find("BIND-03", "Old view")[0]
        self.assertEqual(f["severity"], "High")
        self.assertIn("Deleted Measure", f["evidence"][0]["detail"])
        self.assertFalse(any("Deleted Measure" in x["message"] for x in self.result["findings"] if x["rule_id"] == "BIND-01"))

    # model
    def test_model_rules(self):
        self.find("MOD-01", "Orders.ProductKey")
        self.find("MOD-02", "Product Extra")
        self.find("MOD-03", "ShipDate")
        self.find("MOD-04")
        f = self.find("MOD-05")[0]
        self.assertEqual(f["severity"], "Low")  # annotation on, no LocalDateTable yet
        self.find("MOD-07", "OrderDate")
        self.find("MOD-08", "Weight")
        self.find("MOD-09")
        unused = " ".join(f["message"] for f in self.find("MOD-10"))
        for name in ("Orphan Measure", "Unused Attr", "Notes"):
            self.assertIn(name, unused)
        self.assertNotIn("measure Revenue,", unused)

    # dax
    def test_dax_rules(self):
        self.assertTrue(any(e.get("detail") == "Avg Price" for f in self.find("DAX-01") for e in f["evidence"]))
        self.assertEqual(len(self.find("DAX-01")), 1, "DIVIDE inside IFERROR must not count as '/'")
        self.find("DAX-03")
        self.find("DAX-04", "Margin Pct")
        self.find("DAX-07", "Revenue")
        self.find("DAX-08")

    # governance
    def test_governance_rules(self):
        self.find("GOV-01", "Revenue")
        self.find("GOV-02")
        self.assertEqual(self.find("GOV-09")[0]["severity"], "Critical")
        self.assertTrue(any("bad page!" in e["file"] for f in self.find("GOV-14") for e in f["evidence"]))
        self.find("GOV-15", "Invalid JSON")
        tmdl = self.find("GOV-15", "TMDL line")[0]
        self.assertEqual(tmdl["confidence"], "low")
        self.assertTrue(tmdl["evidence"][0]["file"].endswith("tables/Product.tmdl"))

    # interaction
    def test_sync_group_mixing_fields(self):
        f = self.find("IN-03", "'Mixed'")[0]
        self.assertEqual(f["severity"], "High")
        self.assertIn("'Product'[Category]", f["message"])
        self.assertIn("'Product'[Color]", f["message"])

    def test_same_field_in_different_sync_groups(self):
        self.find("IN-04", "'Calendar'[Year]")

    def test_hidden_synced_slicer_and_hidden_filter(self):
        self.find("IN-02", "'Product'[Color]")
        self.find("IN-01")

    def test_window_measure_without_label(self):
        f = self.find("IN-05", "Recent Revenue")[0]
        self.assertEqual(f["confidence"], "medium")

    def test_drillthrough_without_back(self):
        self.find("IN-07", "Category Drill")

    def test_future_year_slicer(self):
        hits = self.find("IN-13", "2031")
        self.assertEqual(len(hits), 2)

    # report layer
    def test_report_rules(self):
        self.find("ST-01", "'Page 1'")
        self.find("ST-01", "Duplicate of Page 1")
        self.find("ST-05", "Scratch")
        self.find("PERF-01", "Page 1")
        self.find("PERF-02", "21 fields")
        self.find("VD-01", "pieChart")
        self.find("VD-02")
        self.find("VD-06")
        self.find("VD-10", "x=1200")
        self.find("A11Y-01", "Page 1")
        self.find("A11Y-04", "Page 1")
        self.find("MOB-01")

    def test_no_alt_text_finding_for_page_with_alt_text(self):
        self.assertFalse(any("Duplicate of Page 1" in f["message"] for f in self.result["findings"] if f["rule_id"] == "A11Y-01"))


class OtherFormatTests(unittest.TestCase):
    def test_legacy(self):
        r = run("legacy")
        self.assertEqual(r["target"]["report_format"], "PBIR-Legacy")
        self.assertIn("GOV-13", rule_ids(r))

    def test_thin(self):
        r = run("thin")
        self.assertTrue(r["target"]["thin_report"])
        self.assertEqual(rule_ids(r), ["BIND-02"])

    def test_tmsl(self):
        r = run("tmsl")
        self.assertEqual(r["target"]["model_format"], "TMSL")
        self.assertIn("GOV-16", rule_ids(r))


class CliTests(unittest.TestCase):
    def test_markdown_and_out_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "r.md"
            code = scan.main([str(FIX / "defects" / "Defects.pbip"), "--format", "md", "--out", str(out), "--as-of-year", "2026"])
            self.assertEqual(code, 0)
            text = out.read_text(encoding="utf-8")
            self.assertIn("# PBIP audit: Defects.pbip", text)
            self.assertIn("### Critical", text)
            self.assertIn("## Executive summary", text)
            self.assertIn("## Score per pillar", text)
            self.assertIn("Not assessable offline", text)

    def test_fail_on(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(scan.main([str(FIX / "defects"), "--fail-on", "Critical"]), 2)
            self.assertEqual(scan.main([str(FIX / "clean"), "--fail-on", "Low"]), 0)

    def test_missing_path(self):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(scan.main([str(FIX / "does-not-exist")]), 1)


class DaxHelperTests(unittest.TestCase):
    def test_division(self):
        self.assertTrue(has_unsafe_division("[A] / [B]"))
        self.assertFalse(has_unsafe_division("[A] / 100"))
        self.assertFalse(has_unsafe_division("DIVIDE([A], [B]) // ratio"))
        self.assertFalse(has_unsafe_division('"a/b" & [x]'))
        self.assertFalse(has_unsafe_division("[A/B] + 'T/1'[c]"))
        self.assertTrue(has_unsafe_division("SUM(T[a]) / SUM(T[b])"))

    def test_strip(self):
        self.assertEqual(strip_dax('/* x */ "s" -- c'), ' "" ')


if __name__ == "__main__":
    unittest.main()
