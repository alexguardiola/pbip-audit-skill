"""Report theme resolution and colour maths (stdlib only).

A PBIR report names its themes in ``definition/report.json``
(``themeCollection.baseTheme`` and ``themeCollection.customTheme``) and stores
the JSON files under ``StaticResources/`` as listed in ``resourcePackages``.
The effective theme is the base theme with the custom theme's top-level keys
laid over it. When the base theme file is not in the project (Desktop only
writes it for some versions), a built-in copy of the default Power BI palette
is used and ``Theme.base_source`` says so.

Colour references in visuals come in three shapes:

* literal: ``{"expr": {"Literal": {"Value": "'#118DFF'"}}}``
* theme reference: ``{"expr": {"ThemeDataColor": {"ColorId": 2, "Percent": 0.4}}}``
* expression (measure-driven, conditional): not resolvable offline

``ThemeDataColor`` mapping (approximation, documented in FILE-MAP.md): ColorId 0
is the theme background, 1 the foreground, and 2..n are ``dataColors[ColorId-2]``.
``Percent`` > 0 tints toward white, < 0 shades toward black.

Contrast follows WCAG 2.2 relative luminance. Colour-vision deficiency is
simulated with the Machado et al. (2009) matrices at full severity, and pairs
are compared with CIE76 delta E in CIELAB.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .jsonloc import JsonLocator, PathT

HEX6_RE = re.compile(r"^#?([0-9A-Fa-f]{6})(?:[0-9A-Fa-f]{2})?$")
HEX3_RE = re.compile(r"^#?([0-9A-Fa-f]{3})$")

# Public defaults of the Power BI base theme (Microsoft "CY" series), used only
# when the base theme JSON is not stored in the project.
DEFAULT_THEME: Dict[str, Any] = {
    "name": "built-in default",
    "dataColors": ["#118DFF", "#12239E", "#E66C37", "#6B007B", "#E044A7", "#744EC2", "#D9B300", "#D64550",
                   "#197278", "#1AAB40", "#15C6F4", "#4092FF", "#FFA058", "#BE5DC9", "#F472D0", "#B5A1FF"],
    "foreground": "#252423",
    "foregroundNeutralSecondary": "#605E5C",
    "foregroundNeutralTertiary": "#B3B0AD",
    "background": "#FFFFFF",
    "backgroundLight": "#F3F2F1",
    "backgroundNeutral": "#C8C6C4",
    "tableAccent": "#118DFF",
    "good": "#1AAB40",
    "neutral": "#D9B300",
    "bad": "#D64554",
    "maximum": "#118DFF",
    "center": "#D9B300",
    "minimum": "#DEEFFF",
    "null": "#FF7F48",
    "hyperlink": "#0078D4",
    "visitedHyperlink": "#0078D4",
}

PALETTE_KEYS = ["foreground", "foregroundNeutralSecondary", "foregroundNeutralTertiary", "background",
                "backgroundLight", "backgroundNeutral", "tableAccent", "good", "neutral", "bad",
                "maximum", "center", "minimum", "null", "hyperlink", "visitedHyperlink"]


# ---------------------------------------------------------------------------
# colour maths
# ---------------------------------------------------------------------------


def normalize_hex(value: Any) -> Optional[str]:
    """``'#abc'``, ``#AABBCC``, ``#AABBCCDD`` -> ``#AABBCC``; else None."""
    if not isinstance(value, str):
        return None
    v = value.strip().strip("'")
    m = HEX6_RE.match(v)
    if m:
        return "#" + m.group(1).upper()
    m = HEX3_RE.match(v)
    if m:
        return "#" + "".join(c * 2 for c in m.group(1)).upper()
    return None


def hex_to_rgb(h: str) -> Tuple[int, int, int]:
    h = normalize_hex(h) or "#000000"
    return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)


def rgb_to_hex(rgb: Tuple[float, float, float]) -> str:
    return "#" + "".join(f"{max(0, min(255, int(round(c)))):02X}" for c in rgb)


def _lin(c: float) -> float:
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _unlin(c: float) -> float:
    c = max(0.0, min(1.0, c))
    v = 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055
    return v * 255.0


def relative_luminance(h: str) -> float:
    """WCAG 2.x relative luminance (sRGB). WCAG uses 0.03928; the difference is negligible."""
    r, g, b = (_lin(c) for c in hex_to_rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a: str, b: str) -> float:
    la, lb = relative_luminance(a), relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def tint(h: str, percent: float) -> str:
    """Power BI ThemeDataColor ``Percent``: > 0 lighter, < 0 darker (approximation)."""
    if not percent:
        return normalize_hex(h) or h
    r, g, b = hex_to_rgb(h)
    if percent > 0:
        return rgb_to_hex(tuple(c + (255 - c) * percent for c in (r, g, b)))
    p = -percent
    return rgb_to_hex(tuple(c * (1 - p) for c in (r, g, b)))


_MACHADO = {
    "protanopia": ((0.152286, 1.052583, -0.204868), (0.114503, 0.786281, 0.099216), (-0.003882, -0.048116, 1.051998)),
    "deuteranopia": ((0.367322, 0.860646, -0.227968), (0.280085, 0.672501, 0.047413), (-0.011820, 0.042940, 0.968881)),
}


def simulate_cvd(h: str, kind: str) -> str:
    m = _MACHADO[kind]
    lin = [_lin(c) for c in hex_to_rgb(h)]
    out = [sum(m[i][j] * lin[j] for j in range(3)) for i in range(3)]
    return rgb_to_hex(tuple(_unlin(c) for c in out))


def to_lab(h: str) -> Tuple[float, float, float]:
    r, g, b = (_lin(c) for c in hex_to_rgb(h))
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 1.0
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116

    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def delta_e(a: str, b: str) -> float:
    la, lb = to_lab(a), to_lab(b)
    return math.sqrt(sum((p - q) ** 2 for p, q in zip(la, lb)))


def confusable_pairs(colors: List[str], threshold: float) -> List[Tuple[int, int, str, float, float]]:
    """Pairs distinct for normal vision but within ``threshold`` delta E under protan/deutan simulation.

    Returns (i, j, deficiency, simulated delta E, normal delta E).
    """
    out = []
    for i in range(len(colors)):
        for j in range(i + 1, len(colors)):
            a, b = colors[i], colors[j]
            normal = delta_e(a, b)
            if normal < threshold * 2:
                continue  # already similar for everyone; a design choice, not a CVD problem
            worst = None
            for kind in ("deuteranopia", "protanopia"):
                d = delta_e(simulate_cvd(a, kind), simulate_cvd(b, kind))
                if worst is None or d < worst[1]:
                    worst = (kind, d)
            if worst and worst[1] < threshold:
                out.append((i, j, worst[0], worst[1], normal))
    return out


# ---------------------------------------------------------------------------
# theme loading
# ---------------------------------------------------------------------------


@dataclass
class ThemeFile:
    rel: str
    data: Dict[str, Any]
    locator: JsonLocator


@dataclass
class Theme:
    colors: Dict[str, Any] = field(default_factory=lambda: dict(DEFAULT_THEME))
    base: Optional[ThemeFile] = None
    custom: Optional[ThemeFile] = None
    base_source: str = "built-in default"
    notes: List[str] = field(default_factory=list)

    @property
    def data_colors(self) -> List[str]:
        return [c for c in (normalize_hex(x) for x in self.colors.get("dataColors") or []) if c]

    @property
    def background(self) -> str:
        return normalize_hex(self.colors.get("background")) or "#FFFFFF"

    @property
    def foreground(self) -> str:
        return normalize_hex(self.colors.get("foreground")) or "#252423"

    def palette(self) -> set:
        """Every colour the theme defines (for "is this literal a theme colour?")."""
        out = set(self.data_colors)
        for k in PALETTE_KEYS:
            c = normalize_hex(self.colors.get(k))
            if c:
                out.add(c)
        for tc in (self.colors.get("textClasses") or {}).values():
            if isinstance(tc, dict):
                c = normalize_hex(tc.get("color"))
                if c:
                    out.add(c)
        return out

    def owner_of(self, key: str) -> Optional[ThemeFile]:
        """The theme file that supplies a top-level key (custom wins)."""
        if self.custom and key in self.custom.data:
            return self.custom
        if self.base and key in self.base.data:
            return self.base
        return None

    def theme_color(self, color_id: int, percent: float = 0.0) -> Optional[str]:
        if color_id == 0:
            h = self.background
        elif color_id == 1:
            h = self.foreground
        else:
            dc = self.data_colors
            idx = color_id - 2
            if idx < 0 or idx >= len(dc):
                return None
            h = dc[idx]
        return tint(h, float(percent or 0))

    def resolve(self, value: Any) -> Tuple[Optional[str], str]:
        """Resolve a PBIR colour property value. Returns (hex or None, how).

        ``how`` is ``literal``, ``theme`` or ``dynamic`` (not resolvable offline).
        """
        if isinstance(value, dict) and "solid" in value:
            value = (value.get("solid") or {}).get("color")
        if isinstance(value, str):
            h = normalize_hex(value)
            return (h, "literal") if h else (None, "dynamic")
        if not isinstance(value, dict) or "expr" not in value:
            return None, "dynamic"
        expr = value["expr"]
        if not isinstance(expr, dict):
            return None, "dynamic"
        if "Literal" in expr:
            h = normalize_hex((expr["Literal"] or {}).get("Value"))
            return (h, "literal") if h else (None, "dynamic")
        if "ThemeDataColor" in expr:
            tdc = expr["ThemeDataColor"] or {}
            try:
                h = self.theme_color(int(tdc.get("ColorId", -1)), float(tdc.get("Percent", 0) or 0))
            except (TypeError, ValueError):
                h = None
            return (h, "theme") if h else (None, "dynamic")
        return None, "dynamic"


def _read_json(path: Path) -> Optional[Tuple[Dict[str, Any], str]]:
    try:
        raw = path.read_bytes().decode("utf-8-sig")
        data = json.loads(raw)
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    return (data, raw) if isinstance(data, dict) else None


def _theme_path(report_root: Path, report_data: Dict[str, Any], entry: Dict[str, Any]) -> Optional[Path]:
    """Find the file for a themeCollection entry via resourcePackages, then by convention."""
    name = entry.get("name")
    ptype = entry.get("type")
    if not name:
        return None
    static = report_root / "StaticResources"
    for pkg in report_data.get("resourcePackages") or []:
        if not isinstance(pkg, dict):
            continue
        if ptype and pkg.get("type") != ptype and pkg.get("name") != ptype:
            continue
        for item in pkg.get("items") or []:
            if isinstance(item, dict) and item.get("name") == name and item.get("path"):
                p = static / (pkg.get("name") or ptype or "") / item["path"]
                if p.is_file():
                    return p
    for cand in (static / "SharedResources" / "BaseThemes" / f"{name}.json",
                 static / "RegisteredResources" / name,
                 static / "RegisteredResources" / f"{name}.json"):
        if cand.is_file():
            return cand
    return None


def load_theme(report_root: Path, report_data: Any, rel) -> Theme:
    """Build the effective theme. ``rel`` maps a Path to the evidence path string."""
    theme = Theme()
    if not isinstance(report_data, dict):
        theme.notes.append("report.json not readable; using the built-in default theme")
        return theme
    tc = report_data.get("themeCollection") or {}
    colors: Dict[str, Any] = dict(DEFAULT_THEME)
    base = tc.get("baseTheme") if isinstance(tc.get("baseTheme"), dict) else None
    custom = tc.get("customTheme") if isinstance(tc.get("customTheme"), dict) else None
    if base:
        p = _theme_path(report_root, report_data, base)
        loaded = _read_json(p) if p else None
        if loaded:
            data, raw = loaded
            theme.base = ThemeFile(rel(p), data, JsonLocator(raw))
            theme.base_source = theme.base.rel
            colors.update(data)
        else:
            theme.notes.append(f"base theme '{base.get('name')}' not found in StaticResources; using the built-in default palette")
    if custom:
        p = _theme_path(report_root, report_data, custom)
        loaded = _read_json(p) if p else None
        if loaded:
            data, raw = loaded
            theme.custom = ThemeFile(rel(p), data, JsonLocator(raw))
            styles = _deep_merge(colors.get("visualStyles") or {}, data.get("visualStyles") or {})
            colors.update(data)
            colors["visualStyles"] = styles
        else:
            theme.notes.append(f"custom theme '{custom.get('name')}' not found in StaticResources")
    theme.colors = colors
    return theme


def _deep_merge(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Custom theme ``visualStyles`` refine the base theme's instead of replacing them."""
    out = dict(a)
    for k, v in b.items():
        out[k] = _deep_merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def style_props(theme: "Theme", visual_type: str, obj: str) -> Dict[str, Any]:
    """Theme default formatting for ``obj`` on ``visual_type`` (``visualStyles``, raw values)."""
    out: Dict[str, Any] = {}
    styles = theme.colors.get("visualStyles") or {}
    for key in ("*", visual_type):
        entry = ((styles.get(key) or {}).get("*") or {}).get(obj)
        if isinstance(entry, list) and entry and isinstance(entry[0], dict):
            out.update(entry[0])
    return out


def theme_line(tf: Optional[ThemeFile], path: PathT) -> Optional[int]:
    return tf.locator.line(path) if tf else None
