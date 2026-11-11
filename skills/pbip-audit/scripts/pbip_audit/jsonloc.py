"""Line-tracking JSON locator (stdlib only).

``json.loads`` drops positions, so evidence used to point at the first line
containing a key, which is often the wrong node (a second ``"syncGroup"`` in a
bookmark, an ``"altText"`` in another container). This module re-scans the text
with a small recursive-descent parser and records, for every value, the 1-based
line where it starts. For object members the recorded line is the line of the
member's key.

Paths are tuples of keys and list indexes, e.g. ``("visual", "syncGroup")`` or
``("filterConfig", "filters", 2, "isHiddenInViewMode")``. ``parse_path`` converts
the scanner's ``$.a.b[0].c`` notation into such a tuple.
"""

from __future__ import annotations

import bisect
import re
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union

PathT = Tuple[Union[str, int], ...]

_WS = " \t\r\n"
_NUM_RE = re.compile(r"-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?")
_PATH_TOKEN_RE = re.compile(r"\.([^.\[\]]+)|\[(\d+)\]")


class LocatorError(ValueError):
    pass


class JsonLocator:
    """Map JSON paths to line numbers for one document."""

    def __init__(self, text: str):
        if text.startswith("﻿"):
            text = text[1:]
        self.text = text
        self._nl = [i for i, c in enumerate(text) if c == "\n"]
        self.lines: Dict[PathT, int] = {}
        self.ok = True
        try:
            end = self._value(self._skip(0), ())
            if self._skip(end) != len(text):
                self.ok = False
        except (LocatorError, IndexError, RecursionError):
            self.ok = False

    # -- public API -----------------------------------------------------------
    def line(self, path: PathT) -> Optional[int]:
        """Line of ``path``; falls back to the deepest existing ancestor."""
        p = tuple(path)
        while p:
            if p in self.lines:
                return self.lines[p]
            p = p[:-1]
        return self.lines.get((), None)

    def exact(self, path: PathT) -> Optional[int]:
        return self.lines.get(tuple(path))

    def paths(self) -> Iterator[PathT]:
        return iter(self.lines)

    # -- parser ---------------------------------------------------------------
    def _line_of(self, pos: int) -> int:
        return bisect.bisect_left(self._nl, pos) + 1

    def _skip(self, i: int) -> int:
        t = self.text
        n = len(t)
        while i < n and t[i] in _WS:
            i += 1
        return i

    def _value(self, i: int, path: PathT, line: Optional[int] = None) -> int:
        t = self.text
        self.lines[path] = line if line is not None else self._line_of(i)
        c = t[i]
        if c == "{":
            return self._object(i + 1, path)
        if c == "[":
            return self._array(i + 1, path)
        if c == '"':
            return self._string(i)[1]
        for lit in ("true", "false", "null"):
            if t.startswith(lit, i):
                return i + len(lit)
        m = _NUM_RE.match(t, i)
        if m and m.end() > i:
            return m.end()
        raise LocatorError(f"unexpected character at {i}")

    def _string(self, i: int) -> Tuple[str, int]:
        t = self.text
        j = i + 1
        buf: List[str] = []
        while True:
            c = t[j]
            if c == '"':
                return "".join(buf), j + 1
            if c == "\\":
                nxt = t[j + 1]
                if nxt == "u":
                    buf.append(chr(int(t[j + 2:j + 6], 16)))
                    j += 6
                    continue
                buf.append({"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f"}.get(nxt, nxt))
                j += 2
                continue
            buf.append(c)
            j += 1

    def _object(self, i: int, path: PathT) -> int:
        t = self.text
        i = self._skip(i)
        if t[i] == "}":
            return i + 1
        while True:
            i = self._skip(i)
            if t[i] != '"':
                raise LocatorError("expected key")
            key_line = self._line_of(i)
            key, i = self._string(i)
            i = self._skip(i)
            if t[i] != ":":
                raise LocatorError("expected colon")
            i = self._skip(i + 1)
            i = self._value(i, path + (key,), key_line)
            i = self._skip(i)
            if t[i] == ",":
                i += 1
                continue
            if t[i] == "}":
                return i + 1
            raise LocatorError("expected , or }")

    def _array(self, i: int, path: PathT) -> int:
        t = self.text
        i = self._skip(i)
        if t[i] == "]":
            return i + 1
        idx = 0
        while True:
            i = self._skip(i)
            i = self._value(i, path + (idx,))
            idx += 1
            i = self._skip(i)
            if t[i] == ",":
                i += 1
                continue
            if t[i] == "]":
                return i + 1
            raise LocatorError("expected , or ]")


def parse_path(json_path: Optional[str]) -> PathT:
    """``$.visual.query.queryState.Values.projections[0]`` -> tuple path."""
    if not json_path:
        return ()
    s = json_path[1:] if json_path.startswith("$") else json_path
    out: List[Union[str, int]] = []
    for m in _PATH_TOKEN_RE.finditer(s):
        out.append(m.group(1) if m.group(1) is not None else int(m.group(2)))
    return tuple(out)


def format_path(path: PathT) -> str:
    s = "$"
    for p in path:
        s += f"[{p}]" if isinstance(p, int) else f".{p}"
    return s


def walk(node: Any, path: PathT = ()) -> Iterator[Tuple[PathT, Any]]:
    """Yield (path, value) for every node of a decoded JSON value."""
    yield path, node
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk(v, path + (k,))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk(v, path + (i,))
