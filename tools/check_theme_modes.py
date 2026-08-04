#!/usr/bin/env python3
"""Every theme's BASE block must be a complete palette on its own.

Why this gate exists
--------------------
themes.css splits each theme in two:

    [data-theme="x"]                base  — shape, type, density, AND the
                                    theme's preferred mode repeated in full
    [data-theme="x"][data-mode="y"] mode  — colour for that mode

The header of themes.css states the contract: `data-mode` is optional, and
omitting it gets you the preferred mode. A page therefore only has to write
`data-theme` — and five of the seven skeletons do exactly that.

All six themes shipped base blocks missing the eight STATE tokens
(--ui-good/-soft, --ui-warn/-soft, --ui-crit/-soft, --ui-info/-soft). Those
live only in the mode blocks, so a page with no `data-mode` fell through to
ui.css's contract fallbacks — generic green/amber/red/blue — on every pill,
banner and toast. Found by measuring a tick on the marketing skeleton and
getting #15803d where halo says #4FD6C1.

The failure is invisible three times over, which is the whole argument for a
gate rather than a fix:

  * the fallbacks are perfectly legible, so nothing looks broken;
  * validate_palette.py reads the MODE blocks, so contrast passes — it is
    measuring values the page never actually used;
  * the tuning those tokens received (15 state colours moved to clear 4.5:1)
    silently did not reach any page that omits data-mode.

That last point is the real cost: the gate is not about tidiness, it is about
a whole thread of measured work being delivered to nobody.

Same principle as check_theme_order.py — the truth is read out of themes.css
itself and never written down a second time here. The list of tokens to
require is whatever the two mode blocks agree on, so a theme that grows a new
mode-dependent token is covered the day it is added, with no edit to this file.

    python tools/check_theme_modes.py        exit 0 = clean, 1 = failure
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "core" / "themes.css"


def strip_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def block_body(css: str, selector: str) -> str | None:
    """Body of `selector`'s rule, found with a brace scanner.

    Not a regex over `[^}]*`: that stops at the first closing brace and so
    cannot survive a nested at-rule. check_genres.py learned this the hard
    way and let a planted rule through inside @media.
    """
    m = re.search(re.escape(selector) + r"\s*\{", css)
    if not m:
        return None
    open_at = m.end() - 1
    depth, i = 1, open_at + 1
    while depth and i < len(css):
        if css[i] == "{":
            depth += 1
        elif css[i] == "}":
            depth -= 1
        i += 1
    return css[open_at + 1 : i - 1]


def declared(body: str) -> set[str]:
    return set(re.findall(r"(--ui-[a-z0-9-]+)\s*:", body))


def main() -> int:
    if not SRC.exists():
        print(f"missing {SRC}", file=sys.stderr)
        return 1

    css = strip_comments(SRC.read_text(encoding="utf-8"))
    themes = re.findall(r'(?m)^\[data-theme="([\w-]+)"\]\s*\{', css)
    if not themes:
        print("no theme base blocks parsed — did the selector shape change?",
              file=sys.stderr)
        return 1

    failures = 0
    for name in themes:
        base = block_body(css, f'[data-theme="{name}"]')
        dark = block_body(css, f'[data-theme="{name}"][data-mode="dark"]')
        light = block_body(css, f'[data-theme="{name}"][data-mode="light"]')

        if base is None or dark is None or light is None:
            print(f"FAIL {name}: needs a base block and BOTH mode blocks")
            failures += 1
            continue

        base_t, dark_t, light_t = declared(base), declared(dark), declared(light)

        # The requirement is what both modes declare: a token only one mode
        # sets is that mode's business, not a hole in the base block.
        required = dark_t & light_t
        missing = sorted(required - base_t)

        # A base block claiming a mode it does not match is the same bug
        # wearing a different hat — the comment says one thing and the
        # cascade does another.
        scheme = re.search(r"--ui-scheme:\s*(light|dark)", base)
        preferred = scheme.group(1) if scheme else None
        wrong = []
        if preferred:
            pref_body = dark if preferred == "dark" else light
            for token in sorted(required & base_t):
                a = re.search(rf"{re.escape(token)}:\s*([^;]+);", base)
                b = re.search(rf"{re.escape(token)}:\s*([^;]+);", pref_body)
                if a and b and " ".join(a.group(1).split()) != " ".join(b.group(1).split()):
                    wrong.append((token, a.group(1).strip(), b.group(1).strip()))

        if missing:
            failures += 1
            print(f"FAIL {name}: base block is missing {len(missing)} token(s) "
                  f"that both modes declare.")
            print(f"     A page with data-theme=\"{name}\" and no data-mode "
                  f"falls back to ui.css for these:")
            for t in missing:
                print(f"       {t}")
        if wrong:
            failures += 1
            print(f"FAIL {name}: base block says preferred mode is "
                  f"'{preferred}' but disagrees with it:")
            for t, got, want in wrong:
                print(f"       {t}: base {got}  !=  {preferred} {want}")
        if not missing and not wrong:
            print(f"ok   {name}: base block is a complete "
                  f"'{preferred}' palette ({len(base_t)} tokens)")

    print()
    if failures:
        print(f"{failures} theme(s) failed. Copy the preferred mode's values "
              f"into the base block.")
        return 1
    print(f"{len(themes)} themes: every base block stands alone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
