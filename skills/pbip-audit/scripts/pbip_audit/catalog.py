"""Rule catalog: the single source of truth for rule metadata.

Every rule the skill knows about lives here, whatever its check type:

* ``D`` deterministic: computed by ``scan.py`` from files (``implemented=True``)
  or documented but not yet automated (``implemented=False``; the agent checks it
  by hand during the judgement pass).
* ``J`` judgement: assessed by the agent with file:line evidence.
* ``R`` runtime: needs Service / runtime data, reported as "not assessable offline".

The pillar reference files (``MODEL.md`` and so on) are rendered from this list by
``render_catalog.py``. A unit test fails when the docs drift from the catalog.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

SEVERITIES = ["Critical", "High", "Medium", "Low", "Info"]
CHECK_TYPES = ["D", "J", "R"]

PILLARS: Dict[str, str] = {
    "model": "MODEL.md",
    "dax": "DAX.md",
    "performance": "PERFORMANCE.md",
    "governance": "GOVERNANCE-AND-AI-READINESS.md",
    "visual-design": "VISUAL-DESIGN.md",
    "storytelling": "STORYTELLING.md",
    "interaction": "INTERACTION.md",
    "accessibility": "ACCESSIBILITY.md",
    "mobile": "MOBILE.md",
}

ML = "https://learn.microsoft.com"
SRC_PBIR = f"{ML}/power-bi/developer/projects/projects-report"
SRC_TMDL = f"{ML}/analysis-services/tmdl/tmdl-overview"
SRC_BPA = "https://github.com/TabularEditor/BestPracticeRules"
SRC_STAR = f"{ML}/power-bi/guidance/star-schema"
SRC_BIDI = f"{ML}/power-bi/guidance/relationships-bidirectional-filtering"
SRC_DATE = f"{ML}/power-bi/guidance/model-date-tables"
SRC_AUTODATE = f"{ML}/power-bi/guidance/auto-date-time"
SRC_REDUCE = f"{ML}/power-bi/guidance/import-modeling-data-reduction"
SRC_DIVIDE = f"{ML}/dax/best-practices/dax-divide-function-operator"
SRC_ERRFN = f"{ML}/dax/best-practices/dax-error-functions"
SRC_BLANK = f"{ML}/dax/best-practices/dax-avoid-converting-blank"
SRC_FILTER = f"{ML}/dax/best-practices/dax-avoid-avoid-filter-as-filter-argument"
SRC_VARS = f"{ML}/dax/best-practices/dax-variables"
SRC_OPT = f"{ML}/power-bi/guidance/power-bi-optimization"
SRC_DQ = f"{ML}/power-bi/guidance/directquery-model-guidance"
SRC_INCR = f"{ML}/power-bi/connect-data/incremental-refresh-overview"
SRC_COPILOT = f"{ML}/power-bi/create-reports/copilot-prepare-data-ai"
SRC_COPILOT_MODEL = f"{ML}/power-bi/create-reports/copilot-semantic-models"
SRC_RLS = f"{ML}/fabric/security/service-admin-row-level-security"
SRC_VIZ = f"{ML}/power-bi/visuals/power-bi-visualization-best-practices"
SRC_DASH = f"{ML}/power-bi/create-reports/service-dashboards-design-tips"
SRC_THEME = f"{ML}/power-bi/create-reports/desktop-report-themes"
SRC_A11Y = f"{ML}/power-bi/create-reports/desktop-accessibility-creating-reports"
SRC_WCAG = "https://www.w3.org/TR/WCAG22/"
SRC_INTERACT = f"{ML}/power-bi/create-reports/service-reports-visual-interactions"
SRC_SLICER = f"{ML}/power-bi/visuals/power-bi-visualization-slicers"
SRC_FILTERS = f"{ML}/power-bi/create-reports/power-bi-report-filter"
SRC_DRILL = f"{ML}/power-bi/create-reports/desktop-drillthrough"
SRC_TOOLTIP = f"{ML}/power-bi/create-reports/desktop-tooltips"
SRC_BOOKMARK = f"{ML}/power-bi/create-reports/desktop-bookmarks"
SRC_MOBILE = f"{ML}/power-bi/create-reports/power-bi-create-mobile-optimized-report-mobile-layout-view"
SRC_FABINSPECTOR = "https://github.com/NatVanG/fab-inspector"
SRC_GAUGE = f"{ML}/power-bi/visuals/power-bi-visualization-radial-gauge-charts"
SRC_IBCS = "https://www.ibcs.com/ibcs-standards-1-2/"
SRC_SCHEMAS = "https://github.com/microsoft/json-schemas/tree/main/fabric/item/report"
SRC_TE_BPA = "https://docs.tabulareditor.com/common/using-bpa.html"
SRC_CONTRAST_GFX = "https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html"
SRC_USE_OF_COLOR = "https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html"


@dataclass(frozen=True)
class Rule:
    id: str
    pillar: str
    severity: str
    check: str  # D | J | R
    title: str
    rationale: str
    verify: str
    fix: str
    source: str
    implemented: bool = False  # True when scan.py emits it
    kind: str = "defect"  # defect | recommendation


R = Rule

RULES: List[Rule] = [
    # ------------------------------------------------------------------ MODEL
    R("BIND-01", "model", "Critical", "D", "Report field references a model object that does not exist",
      "A visual, filter or bookmark that points at a missing table, column, measure or hierarchy renders as an error (or silently drops a filter) for every viewer. No local tool checks this offline.",
      "Index every `SourceRef.Entity` + `Property` in visual.json, page.json, report.json and bookmarks (resolving `Source` aliases through `From`) and look each one up in the TMDL tables, columns, measures, hierarchies and reportExtensions.json. Severity follows the location: Critical when the missing object is in a visual's query (`queryState`), a filter with a condition or any other place; Medium when every reference is only a stale leftover in a `sortDefinition`, a formatting selector (`visual.objects.*[].selector`) or a filter card without a condition, because the visual itself still has its fields.",
      "Rebind the field in Desktop (or edit the JSON) to the renamed object, or restore the object in the model.",
      SRC_PBIR, implemented=True),
    R("BIND-02", "model", "Info", "D", "Thin report: model binding cannot be verified offline",
      "`definition.pbir` uses `byConnection`, so the semantic model is not in the project and report-to-model checks cannot run.",
      "Read `datasetReference` in `definition.pbir`.",
      "Audit the model project separately, or point `byPath` at a local copy of the model when auditing.",
      SRC_PBIR, implemented=True, kind="recommendation"),
    R("BIND-03", "model", "High", "D", "Bookmark stores state for a model object that no longer exists",
      "Bookmarks snapshot visual query state. After a measure or column is renamed or deleted, applying the bookmark can restore a broken field list.",
      "Model references inside `bookmarks/*.bookmark.json` that do not resolve against the TMDL. Medium instead of High when every stale reference of the bookmark is only in a sort definition, a formatting selector or a filter without a condition.",
      "Re-capture (update) the bookmark after fixing the page, or delete it if unused.",
      SRC_BOOKMARK, implemented=True),
    R("MOD-01", "model", "Medium", "D", "Bidirectional relationship",
      "Both-direction cross filtering creates ambiguous filter paths, slows queries and can give unexpected totals. It is justified mainly for bridge tables and some one-to-one cases.",
      "`crossFilteringBehavior: bothDirections` in relationships.tmdl.",
      "Set the relationship to single direction; use `CROSSFILTER` inside the specific measures that need it.",
      SRC_BIDI, implemented=True),
    R("MOD-02", "model", "Low", "D", "One-to-one relationship",
      "One-to-one relationships usually mean two tables that should be merged; they also make filter direction harder to reason about.",
      "`fromCardinality: one` and `toCardinality: one` on the same relationship.",
      "Merge the tables in Power Query, or document why they stay separate.",
      SRC_STAR, implemented=True, kind="recommendation"),
    R("MOD-03", "model", "Medium", "D", "Inactive relationship never activated with USERELATIONSHIP",
      "An inactive relationship that no measure activates is dead weight and often a forgotten modelling mistake.",
      "`isActive: false` with no `USERELATIONSHIP(...)` call in any DAX expression that names both columns.",
      "Delete the relationship, or add the measures that use it.",
      SRC_STAR, implemented=True),
    R("MOD-04", "model", "High", "D", "Time-intelligence DAX without a marked date table",
      "Functions such as SAMEPERIODLASTYEAR or DATESYTD require a contiguous date column. Without a marked date table they can return wrong results when the relationship is not on a date-typed column.",
      "Any measure using a time-intelligence function while no table has `dataCategory: Time`, unless every date column it passes to those functions is joined by an active relationship between two dateTime columns.",
      "Mark the calendar table as a date table (Table tools > Mark as date table).",
      SRC_DATE, implemented=True),
    R("MOD-05", "model", "Medium", "D", "Auto date/time is enabled",
      "Auto date/time creates a hidden LocalDateTable per date column, inflating model size and producing inconsistent time intelligence.",
      "`annotation __PBI_TimeIntelligenceEnabled = 1` in model.tmdl or `LocalDateTable_*` tables.",
      "Disable Auto date/time in the file options and use one shared, marked date table.",
      SRC_AUTODATE, implemented=True),
    R("MOD-06", "model", "Medium", "R", "Date table is contiguous, covers full years and has no blanks",
      "Time intelligence silently misbehaves on gaps; this depends on the data, not the definition.",
      "Requires querying the data (DAX query or refresh).",
      "Generate the date table with CALENDAR over full years.",
      SRC_DATE),
    R("MOD-07", "model", "Low", "D", "Foreign-key column is visible",
      "Visible key columns invite users to slice by the fact-side key instead of the dimension attribute, which bypasses the dimension.",
      "Columns used on the many side of a relationship without `isHidden`.",
      "Hide foreign-key columns in the fact table.",
      SRC_STAR, implemented=True, kind="recommendation"),
    R("MOD-08", "model", "Low", "D", "Floating-point (double) data type",
      "Double can introduce rounding differences in sums; fixed decimal (`decimal`) or whole numbers are exact and compress better.",
      "`dataType: double` on columns.",
      "Use Fixed decimal number for currency, whole number for counts.",
      SRC_BPA, implemented=True, kind="recommendation"),
    R("MOD-09", "model", "Low", "D", "Implicit measures are not discouraged",
      "Without `discourageImplicitMeasures`, users drag raw numeric columns and get default sums that bypass business logic and confuse Copilot.",
      "`discourageImplicitMeasures` missing from model.tmdl.",
      "Enable it (it is required for calculation groups anyway) and expose explicit measures.",
      SRC_BPA, implemented=True, kind="recommendation"),
    R("MOD-10", "model", "Low", "D", "Unused columns or measures",
      "Objects referenced by no visual, filter, measure, relationship, sort or RLS rule cost memory and maintenance.",
      "Join the report reference index with every DAX text (measures, calculated columns and tables, RLS, calculation items, format string expressions, KPIs and user-defined functions), relationship, sortByColumn and hierarchy level. Field parameter columns (`relatedColumnDetails groupByColumn`, `extendedProperty ParameterMetadata`) count as used, and so does every column of a table that a calculated table copies whole (`source = OtherTable`) or names in `sourceColumn: OtherTable[Column]`. Objects listed in an `--external-usage` file (used by other reports, Excel or paginated reports on the same model) count as used.",
      "Remove them after checking that no other report bound to this model uses them; record known external consumers in an external-usage file.",
      SRC_REDUCE, implemented=True, kind="recommendation"),
    R("MOD-11", "model", "Low", "J", "Single-attribute dimension",
      "A dimension with one attribute can usually be folded into the fact or another dimension.",
      "Look for small tables with one visible column and judge whether they add value.",
      "Merge it, or document why it exists (e.g. a shared slicer table).",
      SRC_STAR),
    R("MOD-12", "model", "Medium", "R", "High-cardinality text keys or columns",
      "Cardinality drives model size; it can only be measured with VertiPaq statistics.",
      "Requires VertiPaq Analyzer or DMVs.",
      "Split, round or remove high-cardinality columns.",
      SRC_REDUCE),
    R("MOD-13", "model", "Low", "J", "Role-playing date tables with generic column names",
      "Copies of the date table with identical column names make fields ambiguous in visuals and for Copilot.",
      "Look for several date-like tables with the same column names.",
      "Prefix columns (`Ship Year`, `Order Year`) or use USERELATIONSHIP with one date table.",
      SRC_STAR),
    # -------------------------------------------------------------------- DAX
    R("DAX-01", "dax", "Medium", "D", "Division operator instead of DIVIDE",
      "`/` raises an error or returns infinity when the denominator is zero or blank; DIVIDE handles it.",
      "A `/` in a measure, calculation item, format string expression, KPI expression or user-defined function whose denominator is not a numeric constant (strings, comments and names are stripped first).",
      "Use `DIVIDE(numerator, denominator)`.",
      SRC_DIVIDE, implemented=True),
    R("DAX-02", "dax", "Medium", "J", "FILTER over a table as a CALCULATE argument",
      "Filtering a whole table is slower and changes semantics compared to a Boolean column filter.",
      "Find `CALCULATE(..., FILTER(Table, ...))` where a column predicate would do.",
      "Use a Boolean filter or `KEEPFILTERS`.",
      SRC_FILTER),
    R("DAX-03", "dax", "Medium", "D", "IFERROR / ISERROR",
      "Error functions force row-by-row evaluation and hide data problems.",
      "`IFERROR(` or `ISERROR(` in any DAX expression.",
      "Use DIVIDE, defensive conditions, or fix the data.",
      SRC_ERRFN, implemented=True),
    R("DAX-04", "dax", "Low", "D", "BLANK converted to zero",
      "Turning BLANK into 0 makes visuals show every dimension member and can slow queries; sometimes it is intended.",
      "`DIVIDE(a, b, 0)`; confirm intent before raising severity.",
      "Return BLANK, or apply the zero only in the visual (show items with no data).",
      SRC_BLANK, implemented=True, kind="recommendation"),
    R("DAX-05", "dax", "Low", "J", "Repeated sub-expressions without variables / EARLIER",
      "Repeated expressions are evaluated more than once and are harder to read.",
      "Read long measures for repeated sub-expressions or EARLIER.",
      "Introduce `VAR` blocks.",
      SRC_VARS),
    R("DAX-07", "dax", "Medium", "D", "Visible measure without a format string",
      "Unformatted measures show raw decimals and inconsistent units across visuals and in Copilot answers.",
      "Visible measures with no `formatString` and no `formatStringDefinition`. Measures that look textual (name suggests title/label/colour, or the expression uses FORMAT, SELECTEDVALUE, CONCATENATEX, `&`, returns string literals or is a single string literal such as a hex colour) are skipped.",
      "Set a format string on every visible measure.",
      SRC_BPA, implemented=True),
    R("DAX-08", "dax", "Low", "D", "TODO / FIXME left in DAX",
      "Open work notes in production measures signal unfinished logic.",
      "`TODO`, `FIXME` or `HACK` inside a DAX expression.",
      "Resolve or move the note to the issue tracker.",
      SRC_BPA, implemented=True),
    R("DAX-09", "dax", "Medium", "J", "TODAY()/NOW() window measures that ignore slicers",
      "A measure that computes its own date window from TODAY() and removes date filters ignores the user's date selection. That is fine when labelled, misleading when not. The scanner raises the visual-level case as IN-05.",
      "Find measures combining TODAY/NOW with REMOVEFILTERS/ALL on the date table or DATESBETWEEN/DATESINPERIOD; read their description.",
      "Document the window in the description and in every visual title that shows it.",
      SRC_DATE),
    R("DAX-11", "dax", "High", "J", "Measure semantically wrong for its name or for the domain rules",
      "Business correctness cannot be checked generically. Load the project's domain-rules file and check measures against it.",
      "Compare each measure with its name, description and the user-supplied domain rules.",
      "Fix the logic or rename the measure; add an anchor-figure regression test.",
      SRC_BPA),
    # ------------------------------------------------------------ PERFORMANCE
    R("PERF-01", "performance", "Medium", "D", "Too many data visuals on one page",
      "Each data visual sends at least one query; busy pages render slowly and overload the reader. There is no official limit; the default threshold is 12 data-bound visuals.",
      "Count visible, data-bound visuals per page (`--max-visuals`); visuals inside a hidden group are hidden.",
      "Split the page, use a multi-row card or a small multiple, or move detail to drillthrough.",
      SRC_OPT, implemented=True),
    R("PERF-02", "performance", "Low", "D", "Too many fields in one visual",
      "Wide visuals generate heavy queries and are hard to read (hard limit is far higher).",
      "More than 20 projections in one visual.",
      "Split the visual or use drillthrough for detail.",
      SRC_FABINSPECTOR, implemented=True),
    R("PERF-03", "performance", "Medium", "J", "DirectQuery page with many single-value cards",
      "In DirectQuery every card is a separate source query.",
      "Partitions with `mode: directQuery` plus pages with many cards.",
      "Use a multi-row card or table; enable query reduction.",
      SRC_DQ),
    R("PERF-04", "performance", "Medium", "R", "Large fact table without incremental refresh",
      "Presence of `refreshPolicy` can be read from files, but whether a table is large needs runtime data.",
      "Check row counts in the Service or with DMVs; check `refreshPolicy` blocks in TMDL.",
      "Add an incremental refresh policy with RangeStart/RangeEnd.",
      SRC_INCR),
    R("PERF-05", "performance", "Info", "R", "Model size, column cardinality, visual query timings",
      "Only measurable with Performance Analyzer, VertiPaq Analyzer or the Service.",
      "Not assessable offline.",
      "Run Performance Analyzer on the slowest pages.",
      SRC_OPT),
    # ------------------------------------------------------------- GOVERNANCE
    R("GOV-01", "governance", "Medium", "D", "Visible measure without a description",
      "Descriptions show in tooltips, field lists and feed Copilot/Q&A grounding. Missing descriptions are the main AI-readiness gap.",
      "Visible measures without a `///` description line.",
      "Add a one-sentence description that says what the measure counts and any window or exclusion.",
      SRC_COPILOT, implemented=True),
    R("GOV-02", "governance", "Low", "D", "Description longer than 200 characters",
      "Copilot and tooltips truncate long descriptions.",
      "`///` description over 200 characters on a measure, column or table.",
      "Keep the first sentence self-contained; move detail to documentation.",
      SRC_COPILOT_MODEL, implemented=True),
    R("GOV-03", "governance", "Medium", "J", "Ambiguous or non-descriptive object names",
      "Duplicate field names across tables and names like `Table1` confuse users and AI.",
      "Read the field list for duplicates and placeholders.",
      "Rename to business terms.",
      SRC_COPILOT),
    R("GOV-07", "governance", "Info", "J", "Non-English object names lower Copilot synonym quality",
      "Copilot grounding works best with English names; this is a trade-off, not a defect.",
      "Note the model language from `culture` and the names.",
      "Add synonyms / linguistic schema, or accept the trade-off.",
      SRC_COPILOT),
    R("GOV-09", "governance", "Critical", "D", "Credential in M or shared expression",
      "Passwords in source control leak to everyone with repository access.",
      "`password=` / `pwd=` patterns in partition sources and expressions.tmdl.",
      "Remove the secret, rotate it and use gateway / data-source credentials.",
      SRC_TMDL, implemented=True),
    R("GOV-10", "governance", "Low", "J", "Literal data values persisted in PBIR filters",
      "PBIR stores filter and slicer selections as literals, which can leak sensitive values into git.",
      "Review `filterConfig` literals in sensitive projects.",
      "Clear selections before committing, or keep the repository private.",
      SRC_PBIR),
    R("GOV-11", "governance", "Medium", "J", "RLS roles defined and filters valid",
      "Row-level security filters that reference wrong columns fail open or closed.",
      "Read `roles/*.tmdl` table permissions.",
      "Test roles with View as role.",
      SRC_RLS),
    R("GOV-12", "governance", "Info", "R", "Sensitivity label, endorsement, Copilot approval, Prep data for AI",
      "Stored in the Service, not in PBIP files.",
      "Not assessable offline.",
      "Check in the Service settings.",
      SRC_COPILOT),
    R("GOV-13", "governance", "Medium", "D", "Report uses the PBIR-Legacy format",
      "PBIR-Legacy `report.json` is an undocumented blob that cannot be reviewed or audited; PBIR is now the default.",
      "Root `report.json` with no `definition/` folder.",
      "Open and save in a current Desktop release to convert to PBIR.",
      SRC_PBIR, implemented=True, kind="recommendation"),
    R("GOV-14", "governance", "High", "D", "Page or visual folder name ignored by Desktop",
      "Folder names that are not word characters or hyphens are silently ignored as private files, so the page or visual disappears.",
      "Folder names under `pages/` and `visuals/` not matching `^[\\w-]+$`.",
      "Rename the folder to letters, digits, underscores or hyphens.",
      SRC_PBIR, implemented=True),
    R("GOV-15", "governance", "High", "D", "Unparseable JSON or TMDL",
      "Desktop refuses to open a project with invalid files.",
      "JSON decode errors and unrecognised TMDL lines.",
      "Fix the file (usually a merge conflict or manual edit).",
      SRC_PBIR, implemented=True),
    R("GOV-17", "governance", "High", "D", "PBIR file does not match its declared schema",
      "Each PBIR file declares a `$schema` version. A file that lacks a required top-level property (or carries one the schema forbids) usually comes from a hand edit or a bad merge, and Desktop may refuse to open the report.",
      "Opt-in (`--validate-schemas`): compare each file's top-level properties with the cached shape of the declared schema version (required, allowed, oneOf). High when something required is missing, Medium for a disallowed property.",
      "Restore the missing property or remove the unknown one; re-save in Desktop to normalise.",
      SRC_SCHEMAS, implemented=True),
    R("GOV-18", "governance", "Info", "D", "Schema not checked (version not in the local cache)",
      "The scanner never downloads schemas. Files whose declared schema version is not cached are listed so the gap is visible rather than silently passing.",
      "Opt-in (`--validate-schemas`): declared `$schema` kind/version absent from `scripts/pbip_audit/schema_cache.json`.",
      "Refresh the cache with `scripts/tools/refresh_schema_cache.py` (network) or ignore; this is information only.",
      SRC_SCHEMAS, implemented=True, kind="recommendation"),
    R("EXT-01", "governance", "Info", "D", "Imported Tabular Editor BPA result",
      "Best Practice Analyzer results imported with `--import-bpa`, so model-level rules from Tabular Editor appear in the same report and SARIF file. Severity, pillar and wording come from the BPA rule; the finding records the original rule in `origin`.",
      "Run BPA (Tabular Editor CLI or semantic-link-labs) and pass its output file.",
      "Follow the BPA rule's own guidance.",
      SRC_TE_BPA, implemented=True, kind="recommendation"),
    R("EXT-02", "governance", "Info", "D", "Imported Fab Inspector result",
      "Failed Fab Inspector (PBI Inspector) rules imported with `--import-fabinspector`. Severity and wording come from the Fab Inspector rule; the finding records the original rule in `origin`.",
      "Run Fab Inspector against the PBIP and pass its JSON results file.",
      "Follow the Fab Inspector rule's own guidance.",
      SRC_FABINSPECTOR, implemented=True, kind="recommendation"),
    R("GOV-16", "governance", "Info", "D", "Model stored as TMSL (model.bim)",
      "This version of the scanner only parses TMDL, so model rules were skipped.",
      "`model.bim` present, no `definition/` folder.",
      "Save the model as TMDL (Desktop option) to get model findings.",
      SRC_TMDL, implemented=True, kind="recommendation"),
    # ---------------------------------------------------------- VISUAL DESIGN
    R("VD-01", "visual-design", "Low", "D", "Pie or donut chart",
      "Angles are hard to compare and the charts break down beyond a handful of categories. The type is deterministic, the category count is runtime.",
      "`visualType` pieChart / donutChart.",
      "Prefer a sorted bar chart; keep pies to 2-5 categories.",
      SRC_VIZ, implemented=True, kind="recommendation"),
    R("VD-02", "visual-design", "Medium", "D", "Gauge without a target",
      "A gauge without a target has no reference point, so the reader cannot judge the value.",
      "`gauge` visual with no `TargetValue` projection.",
      "Bind a target measure or replace with a card plus comparison.",
      SRC_GAUGE, implemented=True),
    R("VD-05", "visual-design", "High", "J", "KPI without comparison",
      "A number without prior period, target or variance carries no message.",
      "Check cards/KPIs for a comparison series or reference label.",
      "Add PY, target or variance.",
      SRC_DASH),
    R("VD-06", "visual-design", "Low", "D", "Hard-coded hex colours",
      "Literal colours bypass the theme, so rebranding and accessibility fixes must be done visual by visual.",
      "`'#RRGGBB'` literals in visual.json, compared with the resolved report theme (base + custom). Low when a literal is outside the theme palette; Info when every literal equals a theme colour (it still will not follow a theme change). Counted per page.",
      "Use theme colours (`ThemeDataColor`) or define the colour in the theme JSON.",
      SRC_THEME, implemented=True, kind="recommendation"),
    R("VD-07", "visual-design", "High", "J", "Bar/column value axis not starting at zero",
      "Truncated bar axes exaggerate differences.",
      "Check `valueAxis` start properties and rendered charts.",
      "Start bar axes at zero; use a line chart for small variations.",
      SRC_VIZ),
    R("VD-08", "visual-design", "Medium", "J", "Mixed time frames or magnitudes on one page",
      "Comparing a YTD card with a monthly chart misleads.",
      "Read titles and measure windows per page.",
      "Align windows or label them.",
      SRC_IBCS),
    R("VD-10", "visual-design", "Medium", "D", "Visual outside the page canvas",
      "Visuals beyond the page bounds are cut off or force scrolling.",
      "`position.x + width` or `y + height` beyond the page size.",
      "Move or resize the visual, or change the page size deliberately.",
      SRC_FABINSPECTOR, implemented=True),
    R("VD-16", "visual-design", "Medium", "J", "Titles state no message / unexplained acronyms",
      "Titles that only name the measure leave interpretation to the reader.",
      "Read titles.",
      "Write action titles; expand acronyms in tooltips or descriptions.",
      SRC_DASH),
    # ---------------------------------------------------------- STORYTELLING
    R("ST-01", "storytelling", "Medium", "D", "Default page names",
      "`Page 1` or `Duplicate of ...` tells the reader nothing and shows an unfinished report.",
      "Page `displayName` matching default patterns (configurable).",
      "Name pages after the question they answer.",
      SRC_DASH, implemented=True),
    R("ST-02", "storytelling", "Medium", "J", "Primary KPI not in the top-left reading position",
      "Readers scan top-left first.",
      "Use the page digest (positions + visual types).",
      "Move headline KPIs to the top-left band.",
      SRC_DASH),
    R("ST-05", "storytelling", "Medium", "D", "Hidden page that is not a drillthrough, tooltip or navigation target",
      "A hidden page nobody can reach is dead content or a forgotten draft.",
      "`visibility: HiddenInViewMode` without `pageBinding`, tooltip type, or any reference to the page name in visuals/bookmarks.",
      "Delete it or wire it to a button/bookmark.",
      SRC_DRILL, implemented=True),
    R("ST-06", "storytelling", "Low", "J", "Page does not state the question it answers",
      "Pages without a clear question become data dumps.",
      "Read page names, titles and text boxes.",
      "Add a page title or subtitle stating the question.",
      SRC_DASH),
    R("ST-07", "storytelling", "Medium", "J", "Chart type does not fit the analytical question",
      "Trend questions need time on the x-axis, composition questions need part-to-whole, and so on.",
      "Compare each visual type with the question it serves.",
      "Change the visual type.",
      SRC_VIZ),
    # ------------------------------------------------------------ INTERACTION
    R("IN-01", "interaction", "Medium", "D", "Hidden filter (may carry business logic)",
      "Filters hidden from the filter pane change numbers without the reader knowing. Often legitimate (scope), so confirm intent.",
      "`isHiddenInViewMode: true` on a report, page or visual filter.",
      "Lock instead of hide, or state the scope in the title / description.",
      SRC_FILTERS, implemented=True, kind="recommendation"),
    R("IN-02", "interaction", "High", "D", "Hidden slicer in a sync group",
      "A hidden synced slicer filters the page invisibly; the reader sees the effect but not the control.",
      "Slicer with `isHidden: true` and a `syncGroup`, with no visible slicer on the same field on that page.",
      "Show the slicer, or show the active selection in a title/card.",
      SRC_SLICER, implemented=True),
    R("IN-03", "interaction", "High", "D", "Sync group mixes different fields",
      "Slicers on different fields sharing one sync group push selections onto the wrong field, silently filtering the wrong dimension.",
      "`visual.syncGroup.groupName` shared by slicers bound to different fields.",
      "Give each field its own sync group.",
      SRC_SLICER, implemented=True),
    R("IN-04", "interaction", "Medium", "D", "Same field sliced in different sync groups",
      "Slicers on the same field across pages that are in different sync groups keep separate selections, so pages disagree.",
      "One field bound to slicers whose `syncGroup.groupName` differ.",
      "Use one sync group per field unless independence is intended.",
      SRC_SLICER, implemented=True),
    R("IN-05", "interaction", "Medium", "D", "Rolling-window measure shown without a window label",
      "A measure that rebuilds its own date window from TODAY() and removes date filters ignores the date slicer. If the visual title does not say so, readers assume it follows the slicer. Heuristic.",
      "Measure with TODAY/NOW plus REMOVEFILTERS/ALL on a date table (or DATESBETWEEN/DATESINPERIOD), bound in a visual whose title, display name, measure name and measure description contain no window words (last N, rolling, trailing, YTD, 12M, L3M, R12...).",
      "Say the window in the title (\"Revenue, last 3 closed months\") or in a subtitle.",
      SRC_DATE, implemented=True),
    R("IN-06", "interaction", "Medium", "J", "KPI cards cross-filtered by detail visuals",
      "Unreviewed default interactions make headline KPIs change when a detail visual is clicked.",
      "Read `visualInteractions` in page.json.",
      "Set interactions to None where KPIs must stay stable.",
      SRC_INTERACT),
    R("IN-07", "interaction", "Medium", "D", "Drillthrough page without a back button",
      "Users land on the drillthrough page and cannot return without knowing the Ctrl/Alt shortcut.",
      "`pageBinding.type: Drillthrough` page with no button, shape or image whose action (`visualLink`) is of type Back.",
      "Add a Back button (Insert > Buttons > Back).",
      SRC_DRILL, implemented=True),
    R("IN-08", "interaction", "Medium", "J", "Tooltip page carries unique information",
      "Information only available in a tooltip is invisible on touch and to keyboard users.",
      "Compare tooltip page content with the host pages.",
      "Surface key figures on the page itself.",
      SRC_TOOLTIP),
    R("IN-10", "interaction", "Medium", "J", "Navigation bookmarks capture data",
      "Bookmarks used as navigation that also capture data reset the reader's filters.",
      "Bookmark `options` without `suppressData` used by navigation buttons.",
      "Untick Data on navigation bookmarks.",
      SRC_BOOKMARK),
    R("IN-13", "interaction", "Medium", "D", "Year slicer exposes future years",
      "When the date table extends past the current year (for forecasts), a year slicer lists empty future years and users pick them by mistake.",
      "Slicer on a year column of a date table whose definition reaches beyond the current year, with no visual, page or report filter on the date table.",
      "Add a visual-level filter (e.g. an `Is Past or Current Year` flag) or trim the slicer values.",
      SRC_DATE, implemented=True),
    # ---------------------------------------------------------- ACCESSIBILITY
    R("A11Y-01", "accessibility", "High", "D", "Visuals without alt text",
      "Screen readers announce only the visual type when alt text is missing.",
      "Visible, non-decorative, non-slicer visuals with no `general.altText` (counted per page). Alt text bound to a measure counts as present; a visual inside a hidden group is hidden.",
      "Add alt text that states the insight, or bind it to a measure for dynamic text.",
      SRC_A11Y, implemented=True),
    R("A11Y-02", "accessibility", "Medium", "J", "Alt text that repeats the title or exceeds 250 characters",
      "Screen readers cut long alt text and repeated titles add nothing.",
      "Compare alt text with titles; check length.",
      "Write a short insight sentence.",
      SRC_A11Y),
    R("A11Y-04", "accessibility", "Low", "D", "Tab order does not follow reading order",
      "Keyboard users jump around the page when tab order ignores the visual layout.",
      "Compare `position.tabOrder` with a top-to-bottom, left-to-right order in page coordinates (group children are positioned relative to their group; visuals within the row band, default 40px, share a row); flag when more than the tolerance (default 40%) of pairs are inverted. Both are configurable.",
      "Set the tab order in the Selection pane.",
      SRC_A11Y, implemented=True, kind="recommendation"),
    R("A11Y-05", "accessibility", "High", "D", "Insufficient text or graphics contrast",
      "WCAG 2.2 requires 4.5:1 for normal text, 3:1 for large text (18pt+) and 3:1 for graphical objects such as series colours.",
      "The scanner resolves the base + custom theme and `ThemeDataColor` references and computes WCAG relative-luminance contrast for: theme foreground and text classes against the theme background; literal or theme font colours in visuals against the visual, page or theme background (only when every plausible background fails, and never when a shape or image sits underneath or the page has a background or wallpaper image; the new card visual's tile fill counts as its background); and the first N custom-theme data colours against the background (Medium). Measure-driven colours are not assessable offline; the agent checks the remaining cases by hand.",
      "Adjust the theme palette or the visual's font/background colours.",
      SRC_WCAG, implemented=True),
    R("A11Y-07", "accessibility", "Medium", "D", "Series colours confusable under colour-vision deficiency",
      "About 1 in 12 men have a red-green colour-vision deficiency. Two series colours that look distinct to most readers can collapse into one, so legends and comparisons stop working.",
      "Simulate protanopia and deuteranopia (Machado et al. 2009) on the first N data colours of a custom theme and flag pairs whose CIELAB delta E falls below the threshold (default 10) while being clearly distinct (2x threshold) for normal vision.",
      "Replace one colour of each pair (vary lightness, not only hue), or add markers, patterns or direct labels.",
      SRC_USE_OF_COLOR, implemented=True),
    R("A11Y-06", "accessibility", "High", "J", "Colour is the only carrier of meaning",
      "Colour-blind readers lose the message.",
      "Look for conditional formatting without icons, labels or patterns.",
      "Add icons, data labels or markers.",
      SRC_WCAG),
    R("A11Y-13", "accessibility", "Medium", "J", "Key insight only available through interaction",
      "Content behind hover or click is not reachable for all users.",
      "Check tooltips, drillthroughs and bookmarks for unique insights.",
      "Surface the insight on the page.",
      SRC_A11Y),
    # ----------------------------------------------------------------- MOBILE
    R("MOB-01", "mobile", "Info", "D", "No page has a mobile layout",
      "Phone users get the scaled desktop canvas, which is hard to read.",
      "No `mobile.json` files in the report.",
      "Create a mobile layout for the pages that mobile users open.",
      SRC_MOBILE, implemented=True, kind="recommendation"),
    R("MOB-02", "mobile", "Medium", "J", "Mobile layout does not put KPIs and slicers first",
      "Mobile readers scroll; the first screen should carry the headline.",
      "Read `mobile.json` positions.",
      "Reorder the mobile layout.",
      SRC_MOBILE),
    R("MOB-03", "mobile", "Low", "J", "Table or matrix drill relies on header clicks",
      "Header interactions are hard to hit on touch screens.",
      "Check matrices on mobile pages.",
      "Add explicit drill buttons or drillthrough.",
      SRC_MOBILE),
]

BY_ID: Dict[str, Rule] = {r.id: r for r in RULES}


def rules_for(pillar: str) -> List[Rule]:
    return [r for r in RULES if r.pillar == pillar]
