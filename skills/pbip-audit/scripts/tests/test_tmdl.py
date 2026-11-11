import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pbip_audit.tmdl import parse_name, parse_tmdl_text, split_qualified  # noqa: E402

SAMPLE = """/// Fact table description.
table 'Order Lines'
\tlineageTag: abc

\t/// Total amount.
\tmeasure 'Total ''Net''' = SUM('Order Lines'[Amount])
\t\tformatString: #,0
\t\tdisplayFolder: Sales

\tmeasure Ratio =
\t\t\tVAR a = [Total 'Net']

\t\t\tRETURN
\t\t\t    DIVIDE(a, 2)
\t\tisHidden

\tmeasure Fenced = ```
\t\t\tSUM('Order Lines'[Amount])
\t\t\t```
\t\tformatString: 0

\tcolumn Amount
\t\tdataType: decimal
\t\tsummarizeBy: sum

\tcolumn Year-Week = YEAR('Order Lines'[Date])
\t\tdataType: int64

\trefreshPolicy
\t\tpolicyType: basic
\t\tsourceExpression =
\t\t\t\tlet
\t\t\t\t    x = 1
\t\t\t\tin
\t\t\t\t    x

\tpartition 'Order Lines' = m
\t\tmode: import
\t\tsource =
\t\t\t\tlet
\t\t\t\t    Source = 1
\t\t\t\tin
\t\t\t\t    Source

\tannotation PBI_ResultType = Table
"""


class TmdlParserTests(unittest.TestCase):
    def setUp(self):
        self.warnings = []
        self.roots = parse_tmdl_text(SAMPLE, "t.tmdl", self.warnings)
        self.table = self.roots[0]

    def test_table_and_description(self):
        self.assertEqual(self.table.kind, "table")
        self.assertEqual(self.table.name, "Order Lines")
        self.assertEqual(self.table.description, "Fact table description.")
        self.assertEqual(self.warnings, [])

    def test_quoted_name_with_escaped_quotes(self):
        m = self.table.child("measure")[0]
        self.assertEqual(m.name, "Total 'Net'")
        self.assertEqual(m.value, "SUM('Order Lines'[Amount])")
        self.assertEqual(m.props["formatstring"], "#,0")
        self.assertEqual(m.description, "Total amount.")
        self.assertEqual(m.line, 6)

    def test_multiline_expression_keeps_blank_lines_and_stops_at_properties(self):
        m = self.table.child("measure")[1]
        self.assertEqual(m.name, "Ratio")
        self.assertIn("VAR a", m.value)
        self.assertIn("DIVIDE(a, 2)", m.value)
        self.assertIn("\n\n", m.value)
        self.assertTrue(m.flag("isHidden"))

    def test_fenced_expression(self):
        m = self.table.child("measure")[2]
        self.assertEqual(m.value.strip(), "SUM('Order Lines'[Amount])")
        self.assertEqual(m.props["formatstring"], "0")

    def test_columns_partition_refresh_policy(self):
        cols = self.table.child("column")
        self.assertEqual([c.name for c in cols], ["Amount", "Year-Week"])
        self.assertEqual(cols[1].value, "YEAR('Order Lines'[Date])")
        self.assertEqual(len(self.table.child("refreshpolicy")), 1)
        part = self.table.child("partition")[0]
        self.assertEqual(part.value, "m")
        self.assertIn("Source = 1", part.props["source"])
        ann = self.table.child("annotation")[0]
        self.assertEqual((ann.name, ann.value), ("PBI_ResultType", "Table"))

    def test_helpers(self):
        self.assertEqual(parse_name("'A ''b''' = 1"), ("A 'b'", "1"))
        self.assertEqual(parse_name("Plain"), ("Plain", None))
        self.assertEqual(split_qualified("'Order Lines'.'Customer Code'"), ["Order Lines", "Customer Code"])
        self.assertEqual(split_qualified("Date.Date"), ["Date", "Date"])

    def test_unknown_line_is_a_warning_not_a_crash(self):
        w = []
        parse_tmdl_text("table T\n\t%%% nonsense\n", "x.tmdl", w)
        self.assertEqual(len(w), 1)
        self.assertIn("x.tmdl:2", w[0])

    def test_bom_and_crlf(self):
        roots = parse_tmdl_text("table T\r\n\tcolumn C\r\n\t\tdataType: string\r\n", "x.tmdl")
        self.assertEqual(roots[0].child("column")[0].props["datatype"], "string")


if __name__ == "__main__":
    unittest.main()
