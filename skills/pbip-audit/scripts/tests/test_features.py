"""Tests for the v0.2 features: precise evidence lines, theme resolution and
colour rules, schema validation, heuristics tuning, config, outputs, adapters."""

import io
import json
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import scan  # noqa: E402
from pbip_audit.adapters import parse_bpa, parse_fabinspector  # noqa: E402
from pbip_audit.checks import Options  # noqa: E402
from pbip_audit.config import ConfigError, load_config, load_external_usage, page_name_patterns, parse_object_ref  # noqa: E402
from pbip_audit.jsonloc import JsonLocator, format_path, parse_path  # noqa: E402
from pbip_audit.output import SEVERITY_WEIGHTS, scores, to_sarif  # noqa: E402
from pbip_audit.schemas import check_document, load_cache, parse_schema_url  # noqa: E402
from pbip_audit.theme import (Theme, confusable_pairs, contrast_ratio, normalize_hex,  # noqa: E402
                              relative_luminance, simulate_cvd, tint)
from validate_findings import semantic_checks, validate  # noqa: E402

FIX = HERE / "fixtures"
IMP = FIX / "imports"
SCHEMA = json.loads((HERE.parent.parent / "report-schema.json").read_text(encoding="utf-8"))


def run(name, **kw):
    imports = kw.pop("imports", None)
    return scan.build_result(FIX / name, Options(as_of_year=2026, **kw), imports)


def by_rule(result, rule_id):
    return [f for f in result["findings"] if f["rule_id"] == rule_id]


def quiet(fn, *a):
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        return fn(*a)


# ---------------------------------------------------------------------------
# 1. JSON locator and evidence precision
# ---------------------------------------------------------------------------


class JsonLocatorTests(unittest.TestCase):
    TEXT = '{\n  "a": {\n    "syncGroup": 1\n  },\n  "visual": {\n    "list": [\n      {"x": "y"},\n      {\n        "syncGroup": {"groupName": "G"}\n      }\n    ],\n    "syncGroup": "real"\n  }\n}\n'

    def test_lines_point_at_the_node_not_the_first_key(self):
        loc = JsonLocator(self.TEXT)
        self.assertTrue(loc.ok)
        self.assertEqual(loc.exact(("a", "syncGroup")), 3)
        self.assertEqual(loc.exact(("visual", "syncGroup")), 12)
        self.assertEqual(loc.exact(("visual", "list", 1, "syncGroup", "groupName")), 9)
        self.assertEqual(loc.exact(("visual", "list", 0)), 7)

    def test_fallback_to_nearest_ancestor(self):
        loc = JsonLocator(self.TEXT)
        self.assertEqual(loc.line(("visual", "missing", "deeper")), 5)
        self.assertIsNone(loc.exact(("visual", "missing")))

    def test_escapes_bom_and_invalid_json(self):
        loc = JsonLocator('﻿{"k\\"ey": "v\\u00e9\\n", "n": -1.5e3, "t": [true, false, null]}')
        self.assertTrue(loc.ok)
        self.assertEqual(loc.exact(('k"ey',)), 1)
        self.assertFalse(JsonLocator('{"a": ').ok)

    def test_path_round_trip(self):
        p = parse_path("$.visual.query.queryState.Values.projections[3].field")
        self.assertEqual(p, ("visual", "query", "queryState", "Values", "projections", 3, "field"))
        self.assertEqual(format_path(p), "$.visual.query.queryState.Values.projections[3].field")

    def test_scanner_evidence_uses_the_real_node(self):
        """A decoy "syncGroup" key earlier in the file must not attract the evidence line."""
        with tempfile.TemporaryDirectory() as tmp:
            dst = Path(tmp) / "defects"
            shutil.copytree(FIX / "defects", dst)
            vf = dst / "Defects.Report" / "definition" / "pages" / "page1" / "visuals" / "slicerCat" / "visual.json"
            data = json.loads(vf.read_text(encoding="utf-8"))
            vis = data["visual"]
            data["visual"] = {"visualType": vis["visualType"],
                              "objects": {"general": [{"properties": {"syncGroup": {"note": "decoy"}}}]},
                              **{k: v for k, v in vis.items() if k != "visualType"}}
            text = json.dumps(data, indent=2)
            vf.write_text(text, encoding="utf-8")
            res = scan.build_result(dst, Options(as_of_year=2026))
            first_text_line = next(i for i, ln in enumerate(text.splitlines(), 1) if '"syncGroup"' in ln)
            real = JsonLocator(text).exact(("visual", "syncGroup"))
            self.assertNotEqual(first_text_line, real)
            ev = [e for f in by_rule(res, "IN-03") for e in f["evidence"] if e["file"].endswith("slicerCat/visual.json")]
            self.assertEqual(ev[0]["line"], real)

    def test_binding_and_hidden_filter_lines(self):
        res = run("defects")
        f = next(f for f in by_rule(res, "BIND-01") if "Ghost Measure" in f["message"])
        e = f["evidence"][0]
        text = (FIX / "defects" / e["file"]).read_text(encoding="utf-8").splitlines()
        self.assertIn('"Property": "Ghost Measure"', text[e["line"] - 1])
        hf = by_rule(res, "IN-01")[0]["evidence"][0]
        text = (FIX / "defects" / hf["file"]).read_text(encoding="utf-8").splitlines()
        self.assertIn('"isHiddenInViewMode"', text[hf["line"] - 1])
        self.assertTrue(hf["json_path"].endswith("isHiddenInViewMode"))


# ---------------------------------------------------------------------------
# 2. Theme resolution and colour maths
# ---------------------------------------------------------------------------


class ColourMathTests(unittest.TestCase):
    def test_wcag_reference_values(self):
        self.assertAlmostEqual(contrast_ratio("#000000", "#FFFFFF"), 21.0, places=2)
        self.assertAlmostEqual(contrast_ratio("#777777", "#FFFFFF"), 4.48, places=2)
        self.assertAlmostEqual(relative_luminance("#FFFFFF"), 1.0, places=4)
        self.assertEqual(contrast_ratio("#123456", "#123456"), 1.0)

    def test_hex_normalisation_and_tint(self):
        self.assertEqual(normalize_hex("'#abc'"), "#AABBCC")
        self.assertEqual(normalize_hex("#118dffcc"), "#118DFF")
        self.assertIsNone(normalize_hex("red"))
        self.assertEqual(tint("#000000", 0.5), "#808080")
        self.assertEqual(tint("#FFFFFF", -0.5), "#808080")

    def test_cvd_simulation_and_pairs(self):
        self.assertEqual(simulate_cvd("#FFFFFF", "deuteranopia"), "#FFFFFF")
        pairs = confusable_pairs(["#D62728", "#2CA02C", "#12239E"], 10)
        self.assertEqual([(i, j) for i, j, *_ in pairs], [(0, 1)])
        self.assertEqual(confusable_pairs(["#000000", "#FFFFFF"], 10), [])

    def test_theme_data_color_resolution(self):
        t = Theme()
        t.colors = dict(t.colors, background="#FFFFFF", foreground="#111111", dataColors=["#FF0000", "#00FF00"])
        ref = lambda cid, pct=0: {"solid": {"color": {"expr": {"ThemeDataColor": {"ColorId": cid, "Percent": pct}}}}}
        self.assertEqual(t.resolve(ref(0)), ("#FFFFFF", "theme"))
        self.assertEqual(t.resolve(ref(1)), ("#111111", "theme"))
        self.assertEqual(t.resolve(ref(3)), ("#00FF00", "theme"))
        self.assertEqual(t.resolve(ref(2, -0.5))[0], "#800000")
        self.assertEqual(t.resolve(ref(9)), (None, "dynamic"))
        self.assertEqual(t.resolve({"expr": {"Literal": {"Value": "'#00ff00'"}}}), ("#00FF00", "literal"))
        self.assertEqual(t.resolve({"expr": {"Measure": {}}}), (None, "dynamic"))


class ThemeResolutionTests(unittest.TestCase):
    def test_base_theme_loaded_from_static_resources(self):
        th = run("clean")["theme"]
        self.assertTrue(th["base"].endswith("BaseThemes/CY24SU10.json"))
        self.assertIsNone(th["custom"])

    def test_custom_theme_over_builtin_base(self):
        res = run("defects")
        self.assertEqual(res["theme"]["base"], "built-in default")
        self.assertTrue(res["theme"]["custom"].endswith("RegisteredResources/BrandTheme.json"))
        self.assertEqual(res["theme"]["foreground"], "#9A9A9A")
        self.assertTrue(any("not found in StaticResources" in n for n in res["notes"]))


class ColourRuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = run("defects")

    def test_a11y05_theme_text_and_graphics(self):
        fs = by_rule(self.res, "A11Y-05")
        theme_text = next(f for f in fs if "report theme sets" in f["message"])
        self.assertEqual(theme_text["severity"], "High")
        self.assertIn("foreground #9A9A9A", theme_text["evidence"][0]["detail"])
        self.assertTrue(theme_text["evidence"][0]["file"].endswith("BrandTheme.json"))
        self.assertIsNotNone(theme_text["evidence"][0]["line"])
        gfx = next(f for f in fs if "graphical objects" in f["message"])
        self.assertEqual(gfx["severity"], "Medium")
        self.assertTrue(any("#FFE600" in e["detail"] for e in gfx["evidence"]))

    def test_a11y05_visual_theme_reference(self):
        f = next(f for f in by_rule(self.res, "A11Y-05") if "Duplicate of Page 1" in f["message"])
        e = f["evidence"][0]
        self.assertTrue(e["file"].endswith("pulse/visual.json"))
        self.assertIn("(theme)", e["detail"])
        self.assertIn("fontColor", e["json_path"])

    def test_a11y07_red_green_pair(self):
        f = by_rule(self.res, "A11Y-07")[0]
        self.assertTrue(any("#D62728 vs series 2 #2CA02C" in e["detail"] for e in f["evidence"]))

    def test_vd06_off_theme_low_and_on_theme_info(self):
        fs = by_rule(self.res, "VD-06")
        low = next(f for f in fs if "'Page 1'" in f["message"])
        self.assertEqual(low["severity"], "Low")
        self.assertIn("#FF0000", low["evidence"][0]["detail"])
        info = next(f for f in fs if "Duplicate of Page 1" in f["message"])
        self.assertEqual(info["severity"], "Info")

    def test_layered_text_is_not_judged(self):
        """White text over a shape that sits underneath cannot be assessed offline."""
        with tempfile.TemporaryDirectory() as tmp:
            dst = Path(tmp) / "defects"
            shutil.copytree(FIX / "defects", dst)
            vdir = dst / "Defects.Report" / "definition" / "pages" / "page2" / "visuals"
            (vdir / "panel").mkdir()
            (vdir / "panel" / "visual.json").write_text(json.dumps({
                "name": "panel", "position": {"x": 850, "y": 120, "z": 0, "width": 420, "height": 160},
                "visual": {"visualType": "shape"}}), encoding="utf-8")
            res = scan.build_result(dst, Options(as_of_year=2026))
            self.assertFalse(any("Duplicate of Page 1" in f["message"] for f in by_rule(res, "A11Y-05")))

    def test_clean_project_has_no_colour_findings(self):
        res = run("clean")
        self.assertEqual([f for f in res["findings"] if f["rule_id"] in ("A11Y-05", "A11Y-07", "VD-06")], [])


# ---------------------------------------------------------------------------
# 3. Schema validation
# ---------------------------------------------------------------------------


class SchemaTests(unittest.TestCase):
    def test_cache_and_url_parsing(self):
        cache = load_cache()
        self.assertIn("2.4.0", cache["visualContainer"])
        self.assertEqual(parse_schema_url("https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.0.0/schema.json"),
                         ("page", "2.0.0"))
        self.assertIsNone(parse_schema_url("https://example.invalid/x.json"))

    def test_check_document(self):
        cache = load_cache()
        self.assertEqual(check_document({"$schema": "x", "name": "a", "position": {}, "visual": {}}, "visualContainer", "2.4.0", cache), [])
        probs = check_document({"$schema": "x", "name": "a", "position": {}, "bogus": 1}, "visualContainer", "2.4.0", cache)
        kinds = {p[0] for p in probs}
        self.assertIn("missing one of", kinds)
        self.assertIn("property not allowed by the schema", kinds)
        self.assertIsNone(check_document({}, "visualContainer", "9.9.9", cache))

    def test_off_by_default(self):
        ids = {f["rule_id"] for f in run("defects")["findings"]}
        self.assertFalse(ids & {"GOV-17", "GOV-18"})

    def test_findings_with_flag(self):
        res = run("defects", validate_schemas=True)
        g17 = by_rule(res, "GOV-17")
        self.assertEqual(len(g17), 1)
        self.assertEqual(g17[0]["severity"], "High")
        self.assertIn("displayOption", g17[0]["message"])
        g18 = by_rule(res, "GOV-18")[0]
        self.assertEqual(g18["severity"], "Info")
        self.assertIn("visualContainer/2.99.0", g18["message"])
        self.assertEqual(run("clean", validate_schemas=True)["findings"], [])


# ---------------------------------------------------------------------------
# 4. Heuristic tuning
# ---------------------------------------------------------------------------


class HeuristicTests(unittest.TestCase):
    def test_in05_documented_window_is_not_reported(self):
        res = run("defects")
        msgs = " ".join(f["message"] for f in by_rule(res, "IN-05"))
        self.assertIn("Recent Revenue", msgs)
        self.assertNotIn("Revenue Pulse", msgs)
        ev = by_rule(res, "IN-05")[0]["evidence"][0]
        self.assertIn("projections[0]", ev["json_path"])

    def test_in05_window_words(self):
        from pbip_audit.checks import WINDOW_WORDS_RE
        for s in ("Sales L12M", "R3M margin", "last 6 months", "Rolling revenue", "Revenue 12M", "Trailing 3"):
            self.assertTrue(WINDOW_WORDS_RE.search(s), s)
        for s in ("Revenue", "Margin by customer", "Lastname"):
            self.assertFalse(WINDOW_WORDS_RE.search(s), s)

    def test_mod10_external_usage_and_note(self):
        res = run("defects")
        msg = " ".join(f["message"] for f in by_rule(res, "MOD-10"))
        self.assertIn("Orphan Measure", msg)
        self.assertIn("Other reports", msg)
        usage = load_external_usage(IMP / "external-usage.txt")
        self.assertIn(("orders", "orphan measure"), usage)
        res2 = run("defects", external_usage=usage, external_usage_source="external-usage.txt")
        msg2 = " ".join(f["message"] for f in by_rule(res2, "MOD-10"))
        self.assertNotIn("Orphan Measure", msg2)
        self.assertNotIn("Unused Attr", msg2)
        self.assertIn("Notes", msg2)
        self.assertNotIn("Other reports", msg2)

    def test_object_ref_forms(self):
        self.assertEqual(parse_object_ref("'My Table'[A b]"), ("my table", "a b"))
        self.assertEqual(parse_object_ref("Sales[Amount]"), ("sales", "amount"))
        self.assertEqual(parse_object_ref("Sales.Amount"), ("sales", "amount"))
        self.assertEqual(parse_object_ref("'It''s'[x]"), ("it's", "x"))

    def test_a11y04_tolerance(self):
        self.assertTrue(by_rule(run("defects"), "A11Y-04"))
        self.assertFalse(by_rule(run("defects", tab_inversion_ratio=0.9), "A11Y-04"))
        f = by_rule(run("defects"), "A11Y-04")[0]
        self.assertIn("tolerance 40%", f["message"])
        self.assertEqual(f["evidence"][0]["json_path"], "$.position.tabOrder")


# ---------------------------------------------------------------------------
# 5. Config file
# ---------------------------------------------------------------------------


class ConfigTests(unittest.TestCase):
    def test_config_applied_through_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "r.json"
            code = quiet(scan.main, [str(FIX / "defects"), "--config", str(IMP / "pbip-audit.json"), "--out", str(out), "--as-of-year", "2026"])
            self.assertEqual(code, 0)
            res = json.loads(out.read_text(encoding="utf-8"))
        ids = [f["rule_id"] for f in res["findings"]]
        self.assertNotIn("MOB-01", ids)  # disabled
        self.assertNotIn("PERF-01", ids)  # max_visuals 30
        self.assertNotIn("A11Y-04", ids)  # tolerance 0.9
        mod10 = [f for f in res["findings"] if f["rule_id"] == "MOD-10"]
        self.assertTrue(all(f["severity"] == "Info" and f["original_severity"] == "Low" for f in mod10))
        self.assertNotIn("Orphan Measure", " ".join(f["message"] for f in mod10))  # external_usage from config
        st01 = " ".join(f["message"] for f in res["findings"] if f["rule_id"] == "ST-01")
        self.assertIn("Scratch", st01)  # extra pattern
        self.assertEqual(res["options"]["config"], "pbip-audit.json")
        self.assertTrue(res["options"]["domain_rules"].endswith("(not found)"))
        self.assertEqual(validate(res, SCHEMA, SCHEMA) + semantic_checks(res), [])

    def test_config_discovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            dst = Path(tmp) / "repo" / "proj"
            shutil.copytree(FIX / "clean", dst)
            (Path(tmp) / "repo" / ".pbip-audit.json").write_text(json.dumps({"thresholds": {"max_visuals": 1}}), encoding="utf-8")
            out = Path(tmp) / "r.json"
            quiet(scan.main, [str(dst), "--out", str(out)])
            res = json.loads(out.read_text(encoding="utf-8"))
            self.assertIn("PERF-01", [f["rule_id"] for f in res["findings"]])
            quiet(scan.main, [str(dst), "--out", str(out), "--no-config"])
            self.assertNotIn("PERF-01", [f["rule_id"] for f in json.loads(out.read_text(encoding="utf-8"))["findings"]])

    def test_bad_config_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            for bad in ({"thresholds": {"nope": 1}}, {"unknown": 1}, {"naming": {"extra_default_page_patterns": ["("]}},
                        {"severity_overrides": {"MOD-10": "Severe"}}, {"disabled_rules": ["XX-99"]}):
                p = Path(tmp) / "c.json"
                p.write_text(json.dumps(bad), encoding="utf-8")
                self.assertEqual(quiet(scan.main, [str(FIX / "clean"), "--config", str(p)]), 1, bad)
            p.write_text("{", encoding="utf-8")
            with self.assertRaises(ConfigError):
                load_config(p)

    def test_locales(self):
        en = page_name_patterns(["en"])
        self.assertFalse(any("gina" in p for p in en))
        self.assertTrue(any("Seite" in p for p in page_name_patterns(["de-DE"])))


# ---------------------------------------------------------------------------
# 6. Outputs
# ---------------------------------------------------------------------------


class OutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = run("defects")

    def test_scores_formula(self):
        sc = self.res["scores"]
        for p, row in sc["pillars"].items():
            fs = [f for f in self.res["findings"] if f["pillar"] == p]
            expected = max(0, 100 - sum(SEVERITY_WEIGHTS[f["severity"]] for f in fs))
            self.assertEqual(row["score"], expected, p)
        self.assertEqual(scores([])["overall"], 100)

    def test_false_positives_are_not_scored(self):
        f = dict(self.res["findings"][0], status="false_positive")
        self.assertEqual(scores([f])["overall"], 100)

    def test_markdown_structure(self):
        md = scan.to_markdown(self.res)
        order = [md.index(h) for h in ("## Executive summary", "## Score per pillar", "## Findings", "### Critical", "### High",
                                       "## Not assessable offline")]
        self.assertEqual(order, sorted(order))
        crit = md[md.index("### Critical"):md.index("### High")]
        self.assertLess(crit.index("#### Model and binding"), crit.index("#### Governance and AI readiness"))
        self.assertIn("Formula:", md)
        self.assertIn("PERF-05", md[md.index("## Not assessable offline"):])

    def test_sarif(self):
        s = to_sarif(self.res, "reports/demo")
        self.assertEqual(s["version"], "2.1.0")
        run_ = s["runs"][0]
        rule_ids = [r["id"] for r in run_["tool"]["driver"]["rules"]]
        self.assertEqual(len(run_["results"]), len(self.res["findings"]))
        for r in run_["results"]:
            self.assertIn(r["level"], ("error", "warning", "note"))
            self.assertEqual(rule_ids[r["ruleIndex"]], r["ruleId"])
            uri = r["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]
            self.assertTrue(uri.startswith("reports/demo/"), uri)
            self.assertNotIn("\\", uri)
        crit = next(r for r in run_["results"] if r["ruleId"] == "BIND-01")
        self.assertEqual(crit["level"], "error")
        self.assertIn("startLine", crit["locations"][0]["physicalLocation"]["region"])

    def test_sarif_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "r.sarif"
            self.assertEqual(quiet(scan.main, [str(FIX / "defects"), "--format", "sarif", "--out", str(out)]), 0)
            self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["version"], "2.1.0")


# ---------------------------------------------------------------------------
# 7. Adapters
# ---------------------------------------------------------------------------


class AdapterTests(unittest.TestCase):
    def test_parse_bpa_json_and_console(self):
        recs = parse_bpa(IMP / "bpa_results.json")
        self.assertEqual(len(recs), 3)
        self.assertEqual(recs[0]["object"], "'Orders'[Avg Price]")
        self.assertEqual([r["severity"] for r in recs], ["Low", "Medium", "Info"])
        con = parse_bpa(IMP / "bpa_console.txt")
        self.assertEqual([r["object_type"] for r in con], ["Measure", "Column", "Table"])
        self.assertEqual([r["severity"] for r in con], ["Info", "Low", "Medium"])

    def test_parse_fabinspector_skips_passes(self):
        recs = parse_fabinspector(IMP / "fabinspector_results.json")
        self.assertEqual([r["rule_id"] for r in recs], ["ENSURE_THEME_COLOURS", "REDUCE_VISUALS_ON_PAGE"])

    def test_imported_findings(self):
        res = run("defects", imports={"bpa": [IMP / "bpa_results.json"], "fabinspector": [IMP / "fabinspector_results.json"]})
        ext1, ext2 = by_rule(res, "EXT-01"), by_rule(res, "EXT-02")
        self.assertEqual(len(ext1), 3)
        self.assertEqual(len(ext2), 2)
        avg = next(f for f in ext1 if "Avg Price" in f["message"])
        self.assertEqual(avg["pillar"], "dax")
        self.assertEqual(avg["origin"]["tool"], "Tabular Editor BPA")
        self.assertTrue(avg["evidence"][0]["file"].endswith("tables/Orders.tmdl"))
        self.assertIsNotNone(avg["evidence"][0]["line"])
        nowhere = next(f for f in ext1 if "Nowhere" in f["message"])
        self.assertEqual(nowhere["evidence"][0]["file"], "bpa_results.json")
        theme = next(f for f in ext2 if "ENSURE_THEME_COLOURS" in f["message"])
        self.assertTrue(theme["evidence"][0]["file"].endswith("card00/visual.json"))
        self.assertEqual(theme["pillar"], "visual-design")
        self.assertEqual(len({f["id"] for f in res["findings"]}), len(res["findings"]))
        self.assertEqual(validate(res, SCHEMA, SCHEMA) + semantic_checks(res), [])

    def test_bad_import_becomes_a_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "x.json"
            bad.write_text("not json and no violations", encoding="utf-8")
            res = run("clean", imports={"bpa": [bad], "fabinspector": [bad]})
            self.assertEqual(res["findings"], [])
            self.assertEqual(len(res["notes"]), 2)


if __name__ == "__main__":
    unittest.main()
