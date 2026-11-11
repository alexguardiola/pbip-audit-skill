# File map

Where each audited property lives in a PBIP project. PBIR paths were observed in Desktop-saved files (2025-2026); they are observed behaviour, not a published contract. Microsoft publishes the JSON schemas at `https://developer.microsoft.com/json-schemas/fabric/item/report/definition/<file>/<version>/schema.json` (mirrored in [microsoft/json-schemas](https://github.com/microsoft/json-schemas/tree/main/fabric/item/report/definition)). Format overview: [PBIP report folder](https://learn.microsoft.com/power-bi/developer/projects/projects-report), [TMDL overview](https://learn.microsoft.com/analysis-services/tmdl/tmdl-overview).

## Project layout

```
<Name>.pbip                         artifacts[].report.path
<Name>.Report/
  definition.pbir                   datasetReference.byPath.path | byConnection
  report.json                       (PBIR-Legacy only)
  definition/
    version.json
    report.json                     report filters, themeCollection, resourcePackages, annotations
    reportExtensions.json           report-level (thin) measures
    pages/pages.json                pageOrder, activePageName
    pages/<page>/page.json
    pages/<page>/visuals/<visual>/visual.json
    pages/<page>/visuals/<visual>/mobile.json
    bookmarks/bookmarks.json, <name>.bookmark.json
  StaticResources/RegisteredResources/   custom themes, images
<Name>.SemanticModel/
  definition.pbism
  model.bim                         (TMSL only)
  definition/
    database.tmdl, model.tmdl, relationships.tmdl, expressions.tmdl, functions.tmdl
    tables/<table>.tmdl             columns, measures, hierarchies, partitions, refreshPolicy
    roles/, cultures/, perspectives/
```

Folder names under `pages/` and `visuals/` must match `^[\w-]+$`; Desktop silently ignores others (GOV-14). Table file names may be URL-escaped (`%7C` for `|`); the table name comes from inside the file.

## Report (PBIR)

| Property | Path |
|---|---|
| Page name / title | `page.json` `name`, `displayName` |
| Page size | `page.json` `width`, `height`, `displayOption` |
| Hidden page | `page.json` `visibility: "HiddenInViewMode"` |
| Tooltip page | `page.json` `type: "Tooltip"` |
| Drillthrough | `page.json` `pageBinding.type: "Drillthrough"`, `pageBinding.parameters[].fieldExpr` |
| Page / report / visual filters | `filterConfig.filters[]` with `field`, `type`, `filter`, `isHiddenInViewMode`, `isLockedInViewMode` |
| Interactions | `page.json` `visualInteractions[]` |
| Visual type | `visual.json` `visual.visualType` |
| Position and tab order | `visual.json` `position.{x,y,z,width,height,tabOrder}` |
| Fields | `visual.query.queryState.<Role>.projections[].field` |
| Field rename | `projections[].displayName` |
| Sort | `visual.query.sortDefinition` |
| Formatting | `visual.objects.<object>[].properties` |
| Title, background, border, header | `visual.visualContainerObjects.<object>[].properties` |
| Alt text | `visual.visualContainerObjects.general[].properties.altText` |
| Slicer sync | `visual.syncGroup.{groupName, fieldChanges, filterChanges}` |
| Hidden visual | `visual.json` top-level `isHidden: true` |
| Group | `visualGroup` (container, no `visual` key); members carry `parentGroupName` |
| Button action | `visual.visualContainerObjects.visualLink[].properties.type` (`'Back'`, `'Bookmark'`, `'PageNavigation'`...) |
| Mobile layout | `mobile.json` next to `visual.json` |
| Bookmark state | `bookmarks/*.bookmark.json` `explorationState`, `options` |
| Theme | `report.json` `themeCollection.baseTheme` / `customTheme` |

### Field references

A field is an expression object:

```json
{"Column": {"Expression": {"SourceRef": {"Entity": "Product"}}, "Property": "Category"}}
{"Measure": {"Expression": {"SourceRef": {"Entity": "Orders"}}, "Property": "Revenue"}}
{"Aggregation": {"Expression": {"Column": {...}}, "Function": 0}}
{"HierarchyLevel": {"Expression": {"Hierarchy": {"Expression": {"SourceRef": {"Entity": "Calendar"}}, "Hierarchy": "Date Hierarchy"}}, "Level": "Year"}}
```

- Inside filters, `SourceRef` may be `{"Source": "a"}`: resolve the alias through the enclosing `From: [{"Name": "a", "Entity": "Product"}]`.
- `SourceRef.Schema: "extension"` means a report-level measure from `reportExtensions.json`.
- Auto date/time fields use `PropertyVariationSource` (the base column is `Property`).
- References also appear in conditional formatting inside `visual.objects`, and in bookmarks.

### Value decoding

Formatting values are expression objects: `{"expr": {"Literal": {"Value": "'text'"}}}`.

- Strings are single-quoted inside `Value`; `''` escapes a quote.
- Numbers carry a type suffix: `12D`, `20L`, `1.5M`.
- Booleans are `true` / `false`.
- Colours: `{"solid": {"color": {"expr": {"Literal": {"Value": "'#118DFF'"}}}}}` (literal, VD-06) or `{"expr": {"ThemeDataColor": {"ColorId": 2, "Percent": 0}}}` (theme).
- A missing property means the theme default applies; resolve the theme before judging titles or colours.

## Theme resolution

The scanner builds the effective theme the way Desktop does, as far as files allow:

1. `report.json` `themeCollection.baseTheme` (`type: SharedResources`) and `customTheme` (`type: RegisteredResources`) name the themes.
2. `report.json` `resourcePackages[].items[]` map each name to a file under `StaticResources/<package name>/<path>` (base themes usually at `StaticResources/SharedResources/BaseThemes/<name>.json`).
3. Effective theme = base theme with the custom theme's top-level keys laid over it; `visualStyles` are merged deeply (custom refines base).
4. When the base theme file is not in the project (older Desktop builds do not write it), the scanner uses a built-in copy of the default Power BI palette and says so in `notes`.

`ThemeDataColor` mapping used by the scanner (an approximation; Microsoft does not document it): `ColorId` 0 = theme `background`, 1 = `foreground`, 2..n = `dataColors[ColorId - 2]`. `Percent` > 0 tints toward white by that fraction, < 0 shades toward black. Findings that depend on it say `(theme)` in the evidence detail.

Text over a visual is judged against, in order: the property block's own background (`backColor`, or a data-label background box when `enableBackground` is true), a button or shape `fill` for the same state selector, the visual's `visualContainerObjects.background` (or the theme `visualStyles` default for that visual type), then the page background. When a shape, image, group or opaque visual sits underneath a see-through visual, the background is unknowable and the pair is skipped. Data labels on bar, column, pie, donut, treemap, funnel, waterfall and ribbon charts are skipped too: they can sit inside the marks.

## Schema versions

Every PBIR file declares `$schema` (`.../definition/<kind>/<version>/schema.json`). `scan.py --validate-schemas` compares each file's top-level properties with a cached summary of that exact version (`scripts/pbip_audit/schema_cache.json`: required, allowed, oneOf). Versions missing from the cache are listed under GOV-18 instead of being checked against a neighbouring version. Some versions Desktop writes are not (yet) published at the schema URL; at the time of writing `visualContainer/2.14.0` returned 404, so it is reported as not checked.

## Model (TMDL)

| Property | Where |
|---|---|
| Auto date/time | `model.tmdl` `annotation __PBI_TimeIntelligenceEnabled = 1`; `LocalDateTable_*` tables |
| Implicit measures | `model.tmdl` `discourageImplicitMeasures` |
| Culture | `model.tmdl` `culture:` |
| Date table | table `dataCategory: Time` |
| Description | `///` lines directly above the object |
| Measure | `measure Name = <DAX>` (single line) or `=` then lines two levels deeper, or a ```` ``` ```` fence |
| Format | `formatString:`, `formatStringDefinition =` |
| Visibility | bare `isHidden` |
| Column | `dataType:`, `summarizeBy:`, `sortByColumn:`, `isKey`, `dataCategory:`; calculated: `column Name = <DAX>` |
| Partition | `partition Name = m | calculated | entity`, `mode:`, `source =` |
| Incremental refresh | table-level `refreshPolicy` block |
| Relationship | `relationships.tmdl`: `fromColumn: T.C`, `toColumn:`, `isActive: false`, `crossFilteringBehavior: bothDirections`, `fromCardinality:`, `toCardinality:` (defaults: many-to-one, single, active) |
| RLS | `roles/<role>.tmdl`: `tablePermission T = <DAX>` |
| Parameters / shared M | `expressions.tmdl`: `expression Name = ... meta [IsParameterQuery=true]` |

### TMDL parsing traps

- Indentation is one tab per level; expressions sit one level deeper than the object's properties.
- Names with spaces or special characters are quoted `'...'` with `''` as escape; references look like `'Table 1'.'Column 1'`.
- Keywords and property names are case-insensitive; the serializer writes camelCase.
- One object can be split across files (partial declarations); merge by table name.
- Blank lines inside multi-line expressions are significant; trailing blank lines are not.
- Files are UTF-8, sometimes with a BOM; line endings may be CRLF.

The scanner's parser is deliberately tolerant: unknown lines become a GOV-15 finding with low confidence instead of a crash.
