#!/usr/bin/env python3
"""
tokens/themes.tokens.json  ->  platform theme files.

    python tools/build_themes.py verify   round-trip check against core/themes.css
    python tools/build_themes.py css      -> dist/css/themes.css
    python tools/build_themes.py gtk      -> dist/gtk/<theme>-<mode>.css
    python tools/build_themes.py xaml     -> dist/xaml/<theme>-<mode>.xaml
    python tools/build_themes.py all

`verify` is the one that matters. It regenerates CSS from the tokens, re-parses
both that and the hand-written core/themes.css with the SAME parser, and
compares token maps. Byte-identical output is not the goal — losing a token in
the round trip is the failure worth catching.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOKENS = ROOT / "tokens" / "themes.tokens.json"
CANON = ROOT / "core" / "themes.css"
DIST = ROOT / "dist"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from css_to_tokens import BLOCK, DECL  # same parser, so the check is honest

# GTK 4.16+ understands CSS custom properties and var(), but not these.
GTK_UNSUPPORTED = {"blur", "ambient"}


def load():
    return json.loads(TOKENS.read_text(encoding="utf-8"))["theme"]


def buckets(node):
    return [k for k in ("base", "light", "dark") if k in node]


def selector(theme, bucket):
    if bucket == "base":
        return f'[data-theme="{theme}"]'
    return f'[data-theme="{theme}"][data-mode="{bucket}"]'


# ---------------------------------------------------------------- CSS --------
def emit_css(themes) -> str:
    out = ["/* GENERATED from tokens/themes.tokens.json — do not edit by hand.",
           "   Run: python tools/build_themes.py css */", ""]
    for name, node in themes.items():
        desc = node.get("$description", "")
        out += [f"/* {'=' * 74}", f"   {name.upper()} — {desc}", f"   {'=' * 74} */"]
        for b in buckets(node):
            out.append(selector(name, b) + "{")
            for key, tok in node[b].items():
                out.append(f"  --ui-{key}:{tok['$value']};")
            out += ["}", ""]
    return "\n".join(out)


# ---------------------------------------------------------------- GTK --------
def emit_gtk(themes):
    written = []
    for name, node in themes.items():
        base = node.get("base", {})
        for mode in ("light", "dark"):
            if mode not in node:
                continue
            merged = dict(base)
            merged.update(node[mode])
            lines = [
                f"/* UI Suite — {name} / {mode} — GTK4 */",
                "/* Requires GTK 4.16+, which added CSS custom properties and var().",
                "   Widget rules are NOT generated: GTK selectors are widget names",
                "   (window, headerbar, button) and its supported property set is a",
                "   subset of web CSS. Author those against these tokens. */",
                "",
                ":root {",
            ]
            skipped = []
            for key, tok in merged.items():
                if key in GTK_UNSUPPORTED:
                    skipped.append(key)
                    continue
                lines.append(f"  --ui-{key}: {tok['$value']};")
            lines.append("}")
            if skipped:
                lines += ["", "/* No GTK equivalent, omitted: " + ", ".join(skipped),
                          "   Translucency/blur is compositor-dependent on Linux —",
                          "   raise surface opacity instead of relying on blur. */"]
            p = DIST / "gtk" / f"{name}-{mode}.css"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("\n".join(lines) + "\n", encoding="utf-8")
            written.append(p)
    return written


# --------------------------------------------------------------- XAML --------
HEX = re.compile(r"^#([0-9a-fA-F]{6})$")
RGBA = re.compile(r"^rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)$")


def to_argb(v):
    """CSS colour -> XAML #AARRGGBB, or None if not a colour."""
    v = v.strip()
    m = HEX.match(v)
    if m:
        return "#FF" + m.group(1).upper()
    m = RGBA.match(v)
    if m:
        r, g, b = (int(round(float(m.group(i)))) for i in (1, 2, 3))
        a = int(round(float(m.group(4) or 1) * 255))
        return f"#{a:02X}{r:02X}{g:02X}{b:02X}"
    return None


def pascal(key):
    return "".join(p.capitalize() for p in key.split("-"))


def emit_xaml(themes):
    written = []
    for name, node in themes.items():
        base = node.get("base", {})
        for mode in ("light", "dark"):
            if mode not in node:
                continue
            merged = dict(base)
            merged.update(node[mode])

            colors, dims, dropped = [], [], []
            for key, tok in merged.items():
                argb = to_argb(str(tok["$value"]))
                if argb:
                    colors.append((pascal(key), argb))
                    continue
                if tok.get("$type") == "dimension":
                    dims.append((pascal(key), str(tok["$value"]).rstrip("pxemr")))
                elif tok.get("$type") == "number":
                    dims.append((pascal(key), str(tok["$value"])))
                else:
                    dropped.append(key)

            L = [
                '<!-- UI Suite — {} / {} — generated, do not edit -->'.format(name, mode),
                '<!-- WinUI 3 / UWP. For WPF, x:Double needs',
                '     xmlns:sys="clr-namespace:System;assembly=mscorlib" and sys:Double. -->',
                '<ResourceDictionary',
                '    xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"',
                '    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">',
                '',
            ]
            for k, v in colors:
                L.append(f'    <Color x:Key="Ui{k}Color">{v}</Color>')
            L.append('')
            for k, _ in colors:
                L.append(f'    <SolidColorBrush x:Key="Ui{k}" Color="{{StaticResource Ui{k}Color}}" />')
            if dims:
                L.append('')
                for k, v in dims:
                    L.append(f'    <x:Double x:Key="Ui{k}">{v}</x:Double>')
            if dropped:
                L += ['', '    <!-- Not expressible as a XAML resource: ' + ", ".join(dropped),
                      '         Depth on Windows is Mica/Acrylic + ThemeShadow, set in code',
                      '         or on the element — not a brush. -->']
            L += ['', '</ResourceDictionary>']

            p = DIST / "xaml" / f"{name}-{mode}.xaml"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("\n".join(L) + "\n", encoding="utf-8")
            written.append(p)
    return written


# ------------------------------------------------------------- verify --------
def parse_css(text):
    """selector -> {token: value}, using the extraction parser."""
    found = {}
    for m in BLOCK.finditer(text):
        key = (m.group("theme"), m.group("mode") or "base")
        found[key] = {n: " ".join(v.split()) for n, v in DECL.findall(m.group("body"))}
    return found


def verify(themes):
    canon = parse_css(CANON.read_text(encoding="utf-8"))
    regen = parse_css(emit_css(themes))

    problems = []
    for key in sorted(set(canon) | set(regen)):
        a, b = canon.get(key), regen.get(key)
        if a is None:
            problems.append(f"  {key}: only in generated output")
            continue
        if b is None:
            problems.append(f"  {key}: LOST in round trip")
            continue
        for tok in sorted(set(a) | set(b)):
            # `tok` already carries its --ui- prefix here: parse_css keys on the
            # full declaration name, unlike the token file, which strips it.
            if tok not in b:
                problems.append(f"  {key} {tok}: LOST")
            elif tok not in a:
                problems.append(f"  {key} {tok}: extra")
            elif a[tok] != b[tok]:
                problems.append(f"  {key} {tok}: {a[tok]!r} -> {b[tok]!r}")

    n = sum(len(v) for v in canon.values())
    if problems:
        print(f"ROUND TRIP FAILED — {len(problems)} difference(s) across {n} tokens")
        for p in problems[:40]:
            print(p)
        return 1
    print(f"round trip OK — {n} tokens across {len(canon)} blocks, no loss")
    return 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "verify"
    themes = load()

    if cmd == "verify":
        return verify(themes)
    if cmd in ("css", "all"):
        p = DIST / "css" / "themes.css"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(emit_css(themes), encoding="utf-8")
        print(f"wrote {p.relative_to(ROOT)}")
    if cmd in ("gtk", "all"):
        for p in emit_gtk(themes):
            print(f"wrote {p.relative_to(ROOT)}")
    if cmd in ("xaml", "all"):
        for p in emit_xaml(themes):
            print(f"wrote {p.relative_to(ROOT)}")
    if cmd not in ("css", "gtk", "xaml", "all"):
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
