# Accessibility

Rules from Microsoft's report accessibility checklist and WCAG 2.2. Alt text and tab order are deterministic from visual.json. The scanner resolves the report theme and computes WCAG contrast (A11Y-05) and colour-vision confusion between series colours (A11Y-07) where the colours are knowable from files; see [FILE-MAP.md](FILE-MAP.md#theme-resolution) for what it can and cannot see. Measure-driven (conditional) colours, text over images or shapes, and colour-only meaning (A11Y-06) still need your judgement, and the final word needs the rendered report.

## Rules

<!-- BEGIN GENERATED RULES -->

<!-- Generated from scripts/pbip_audit/catalog.py by scripts/render_catalog.py. Do not edit by hand. -->

| ID | Title | Severity | Check | Who checks | Type |
|---|---|---|---|---|---|
| A11Y-01 | Visuals without alt text | High | D | scan.py | defect |
| A11Y-02 | Alt text that repeats the title or exceeds 250 characters | Medium | J | agent | defect |
| A11Y-04 | Tab order does not follow reading order | Low | D | scan.py | recommendation |
| A11Y-05 | Insufficient text or graphics contrast | High | D | scan.py | defect |
| A11Y-07 | Series colours confusable under colour-vision deficiency | Medium | D | scan.py | defect |
| A11Y-06 | Colour is the only carrier of meaning | High | J | agent | defect |
| A11Y-13 | Key insight only available through interaction | Medium | J | agent | defect |

### A11Y-01 Visuals without alt text

- **Severity:** High. **Check:** D (scan.py). **Type:** defect.
- **Why:** Screen readers announce only the visual type when alt text is missing.
- **How to verify:** Visible, non-decorative, non-slicer visuals with no `general.altText` (counted per page). Alt text bound to a measure counts as present; a visual inside a hidden group is hidden.
- **Fix:** Add alt text that states the insight, or bind it to a measure for dynamic text.
- **Source:** <https://learn.microsoft.com/power-bi/create-reports/desktop-accessibility-creating-reports>

### A11Y-02 Alt text that repeats the title or exceeds 250 characters

- **Severity:** Medium. **Check:** J (agent). **Type:** defect.
- **Why:** Screen readers cut long alt text and repeated titles add nothing.
- **How to verify:** Compare alt text with titles; check length.
- **Fix:** Write a short insight sentence.
- **Source:** <https://learn.microsoft.com/power-bi/create-reports/desktop-accessibility-creating-reports>

### A11Y-04 Tab order does not follow reading order

- **Severity:** Low. **Check:** D (scan.py). **Type:** recommendation.
- **Why:** Keyboard users jump around the page when tab order ignores the visual layout.
- **How to verify:** Compare `position.tabOrder` with a top-to-bottom, left-to-right order in page coordinates (group children are positioned relative to their group; visuals within the row band, default 40px, share a row); flag when more than the tolerance (default 40%) of pairs are inverted. Both are configurable.
- **Fix:** Set the tab order in the Selection pane.
- **Source:** <https://learn.microsoft.com/power-bi/create-reports/desktop-accessibility-creating-reports>

### A11Y-05 Insufficient text or graphics contrast

- **Severity:** High. **Check:** D (scan.py). **Type:** defect.
- **Why:** WCAG 2.2 requires 4.5:1 for normal text, 3:1 for large text (18pt+) and 3:1 for graphical objects such as series colours.
- **How to verify:** The scanner resolves the base + custom theme and `ThemeDataColor` references and computes WCAG relative-luminance contrast for: theme foreground and text classes against the theme background; literal or theme font colours in visuals against the visual, page or theme background (only when every plausible background fails, and never when a shape or image sits underneath or the page has a background or wallpaper image; the new card visual's tile fill counts as its background); and the first N custom-theme data colours against the background (Medium). Measure-driven colours are not assessable offline; the agent checks the remaining cases by hand.
- **Fix:** Adjust the theme palette or the visual's font/background colours.
- **Source:** <https://www.w3.org/TR/WCAG22/>

### A11Y-07 Series colours confusable under colour-vision deficiency

- **Severity:** Medium. **Check:** D (scan.py). **Type:** defect.
- **Why:** About 1 in 12 men have a red-green colour-vision deficiency. Two series colours that look distinct to most readers can collapse into one, so legends and comparisons stop working.
- **How to verify:** Simulate protanopia and deuteranopia (Machado et al. 2009) on the first N data colours of a custom theme and flag pairs whose CIELAB delta E falls below the threshold (default 10) while being clearly distinct (2x threshold) for normal vision.
- **Fix:** Replace one colour of each pair (vary lightness, not only hue), or add markers, patterns or direct labels.
- **Source:** <https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html>

### A11Y-06 Colour is the only carrier of meaning

- **Severity:** High. **Check:** J (agent). **Type:** defect.
- **Why:** Colour-blind readers lose the message.
- **How to verify:** Look for conditional formatting without icons, labels or patterns.
- **Fix:** Add icons, data labels or markers.
- **Source:** <https://www.w3.org/TR/WCAG22/>

### A11Y-13 Key insight only available through interaction

- **Severity:** Medium. **Check:** J (agent). **Type:** defect.
- **Why:** Content behind hover or click is not reachable for all users.
- **How to verify:** Check tooltips, drillthroughs and bookmarks for unique insights.
- **Fix:** Surface the insight on the page.
- **Source:** <https://learn.microsoft.com/power-bi/create-reports/desktop-accessibility-creating-reports>

<!-- END GENERATED RULES -->
