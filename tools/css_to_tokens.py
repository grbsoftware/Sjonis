#!/usr/bin/env python3
"""
core/themes.css  ->  tokens/themes.tokens.json   (W3C DTCG format)

The CSS is the current source of truth, so the token file is derived from it
rather than transcribed by hand — transcription is where fidelity is lost.
Once the round-trip is proven (build_themes.py regenerates identical CSS), the
JSON becomes the source and the CSS becomes an output.

Composite values — shadows, gradients, blur filters — are stored as raw CSS
strings under a vendor extension. DTCG has composite types for shadow, but the
mapping is lossy for multi-layer and `none` values, and being honest about that
is worth more than a leaky conversion. Only the CSS and GTK generators consume
them; XAML has to handle depth natively.
"""

import json
import re
import sys
from pathlib import Path
from collections import OrderedDict

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "core" / "themes.css"
OUT = ROOT / "tokens" / "themes.tokens.json"

# Prose lifted from the comment banner above each theme, so the token file
# carries the intent and not only the numbers.
DESCRIPTIONS = {
    "vanilla":   "Neutral but designed. The open-source default and the worked example for authoring a theme.",
    "blueprint": "Technical console. Square corners, monospace throughout, cyan as the only signal colour.",
    "halo":      "Soft depth. Translucent layers, ambient glow, generous radii, mint accent.",
    "graphite":  "Calm precision. Cool near-monochrome, one restrained steel accent, hairline rules.",
    "oxide":     "Warm industrial. Rust signal colour, heavier weights, hard drop shadow.",
    "vellum":    "Editorial calm. Cool bone ground, serif display, generous spacing, low contrast.",
}

BLOCK = re.compile(
    r'\[data-theme="(?P<theme>[a-z0-9-]+)"\]'
    r'(?:\[data-mode="(?P<mode>light|dark)"\])?'
    r'\s*\{(?P<body>[^}]*)\}',
    re.DOTALL,
)
DECL = re.compile(r'(--ui-[a-z0-9-]+)\s*:\s*([^;]+)', re.DOTALL)

RAW_CSS = ("shadow", "shadow-lg", "ambient", "blur")


def classify(name: str, value: str):
    """Return (dtcg_type, cleaned_value). None type => raw CSS extension."""
    v = " ".join(value.split())
    short = name[len("--ui-"):]

    if short in RAW_CSS:
        return None, v
    if v.startswith("#") or v.startswith("rgba(") or v.startswith("rgb("):
        return "color", v
    if re.fullmatch(r'-?[\d.]+(px|em|rem)', v):
        return "dimension", v
    if re.fullmatch(r'-?[\d.]+', v):
        return "number", v
    if "font" in short:
        return "fontFamily", v
    return None, v


def token(name: str, value: str):
    ttype, val = classify(name, value)
    if ttype is None:
        # Raw CSS: keep it addressable but do not pretend it is a typed token.
        return OrderedDict([
            ("$value", val),
            ("$extensions", {"design.uisuite": {"raw": "css"}}),
        ])
    return OrderedDict([("$type", ttype), ("$value", val)])


def main() -> int:
    if not SRC.exists():
        print(f"missing {SRC}", file=sys.stderr)
        return 1

    css = SRC.read_text(encoding="utf-8")
    themes: "OrderedDict[str, OrderedDict]" = OrderedDict()

    for m in BLOCK.finditer(css):
        theme, mode, body = m.group("theme"), m.group("mode"), m.group("body")
        bucket = mode or "base"
        node = themes.setdefault(theme, OrderedDict())
        if "$description" not in node and theme in DESCRIPTIONS:
            node["$description"] = DESCRIPTIONS[theme]
        group = node.setdefault(bucket, OrderedDict())
        for name, value in DECL.findall(body):
            group[name[len("--ui-"):]] = token(name, value)

    if not themes:
        print("no theme blocks parsed — did the selector shape change?", file=sys.stderr)
        return 1

    doc = OrderedDict([
        ("$description",
         "UI Suite theme tokens. Generated from core/themes.css by "
         "tools/css_to_tokens.py — see tools/build_themes.py for the inverse."),
        ("theme", themes),
    ])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    total = sum(len(g) for t in themes.values()
                for k, g in t.items() if k != "$description")
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"  themes: {len(themes)} ({', '.join(themes)})")
    print(f"  tokens: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
