"""Bring an outside palette into Sjonis, measured on the way in.

THE GAP THIS FILLS. Every colour in the suite was solved against the grounds it
lands on. A palette from anywhere else -- Radiance, a client's brand sheet, a
photograph -- has been solved against nothing, so pasting it into a token file
is how a system that validates its own colours starts shipping ones it never
checked. There was no path in at all before this; the only option was editing
tokens by hand.

    python tools/import_palette.py --theme vanilla --mode light \
        "#6B3FA0" "#554C88" "#3A5470" "#367066" "#2E8B57"

    python tools/import_palette.py --all "#6B3FA0" "#3A5470" "#2E8B57"

WHAT COMES OUT IS A GENRE, NOT A THEME, and that is a position rather than a
convenience. A theme is chosen by who the interface is FOR -- the six that ship
are audience presets with stated reasoning. A palette somebody likes is not an
audience, it is a point of view, and the ring for a point of view is the genre.
So this emits a genre's colour block: one hue promoted to --ui-accent, the rest
landing in the categorical slots that ui.css already paints blocks, bars and
marks with. The genre still names a theme, which keeps supplying type, radius,
surfaces and the four state hues.

TWO CONTRAST REGIMES, AND THE SUITE ALREADY HAS A MECHANISM FOR EACH. Gary put
it exactly right after seeing a rainbow come out of Radiance: "the solid blocks
of color or bars or circles could be 2 or more of the colors, and the accented
text like the blue in the vanilla portfolio". Blocks are non-text and want 3.0;
accent text is text and wants 4.5. Only ONE colour ever needs 4.5, because
there is only one accent -- which is why an analogous palette that would be
useless as a categorical set is perfectly usable here.

THE FIX WHEN ONE MISSES is the one the state colours already use: hold OKLCH
hue and chroma, walk lightness toward the ink, stop at the first value that
clears every ground it meets. Most moves are invisible. It re-checks the
ROUNDED hex rather than the solved float, because rounding to 8-bit can cost up
to half a step per channel and that is enough to drop a solved 4.502 back under
the bar (trap 16).
"""

import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validate_palette import (          # noqa: E402
    AA_LARGE, AA_TEXT, CSS, RIM_MIX,
    flatten, from_oklab, load_blocks, mix_oklab, parse_colour, ratio, to_oklab,
)

# The grounds a colour actually meets. --ui-bg is the page; the three surfaces
# are what ui.css paints cards, table wraps and the deeper wells with. A block
# can land on any of them, so all four are required, not just the page.
GROUNDS = ("--ui-bg", "--ui-surface", "--ui-surface-2", "--ui-surface-3")


def hexof(c):
    return "#%02X%02X%02X" % tuple(int(round(max(0.0, min(255.0, v)))) for v in c[:3])


def oklch(c):
    L, a, b = to_oklab(c)
    return L, math.hypot(a, b), math.atan2(b, a)


def from_oklch(L, C, h):
    return from_oklab((L, C * math.cos(h), C * math.sin(h)))


def grounds_of(tokens):
    """-> [(label, opaque rgb)] for every ground in this theme x mode."""
    out = []
    page = parse_colour(tokens["--ui-bg"])
    for name in GROUNDS:
        raw = tokens.get(name)
        if raw is None:
            continue
        c = parse_colour(raw)
        if c is None:
            continue
        # halo's surfaces are rgba over the page, so they have to be
        # composited before they are a ground anything can be measured against
        # (trap 11). --ui-bg is the only token opaque in all six themes.
        out.append((name, flatten(c, page) if c[3] < 1.0 else c))
    return out


def worst(colour, grounds):
    """-> (lowest ratio, the ground label that produced it)."""
    lo, where = None, None
    for label, g in grounds:
        r = ratio(colour, g)
        if lo is None or r < lo:
            lo, where = r, label
    return lo, where


def walk_to_ink(colour, grounds, want, ink):
    """Hold hue and chroma, walk lightness toward `ink` until it clears `want`.

    Returns (hex, moved) -- moved is the change in OKLCH lightness, so a caller
    can say how far it went. Steps in L rather than mixing toward the ink
    because a mix drags chroma toward the ink's as well, and a desaturated
    version of somebody's colour is not their colour any more.
    """
    L0, C, h = oklch(colour)
    target_L = to_oklab(ink)[0]
    direction = 1.0 if target_L > L0 else -1.0

    step = 0.002
    L = L0
    for _ in range(500):
        L += direction * step
        if not (0.0 <= L <= 1.0):
            break
        # Round to hex FIRST, then measure -- see trap 16 in RESUME.md.
        cand = parse_colour(hexof(from_oklch(L, C, h)))
        lo, _where = worst(cand, grounds)
        if lo >= want:
            return hexof(cand), L - L0
    return None, None


def rimmed(colour, ink):
    """What a mark actually puts on screen: the hue with its 1px rim.

    ui.css rims .ui-dot, .ui-tag::before and .ui-swatch with the mark's own hue
    mixed toward --ui-text, so the thing meeting the ground is a computed
    color-mix rather than the token (trap 15). Reported as a second opinion:
    a colour that misses 3.0 bare but clears it rimmed is usable as a MARK and
    not as a bar, and only the author knows which they wanted.
    """
    return mix_oklab(colour, ink, RIM_MIX)


def report(colours, blocks, accent_index, args):
    rows = []
    fixed = {}

    for idx, hexin in enumerate(colours):
        c = parse_colour(hexin)
        if c is None:
            print("not a colour: %s" % hexin)
            return None, 1
        is_accent = idx == accent_index
        want = AA_TEXT if is_accent else AA_LARGE

        per_theme = []
        for theme, mode, tokens in blocks:
            grounds = grounds_of(tokens)
            ink = parse_colour(tokens["--ui-text"])
            ink = flatten(ink, parse_colour(tokens["--ui-bg"])) if ink[3] < 1.0 else ink
            lo, where = worst(c, grounds)
            rim_lo, _ = worst(rimmed(c, ink), grounds)
            out_hex, moved = (hexin, 0.0)
            if lo < want:
                out_hex, moved = walk_to_ink(c, grounds, want, ink)
            per_theme.append((theme, mode, lo, where, rim_lo, out_hex, moved))
        rows.append((hexin, is_accent, want, per_theme))

    target = (args.theme, args.mode)
    print("=" * 74)
    print("IMPORTING %d COLOURS%s" % (
        len(colours),
        "" if args.all else "  ->  %s %s" % target))
    print("=" * 74)
    print("one colour carries text at %.1f (the accent); the rest are blocks at %.1f"
          % (AA_TEXT, AA_LARGE))
    print()

    header = "%-9s %-7s %-9s %6s %6s  %-9s %s" % (
        "colour", "role", "worst on", "ratio", "rimmed", "shipped", "moved")
    for theme, mode, tokens in blocks:
        if not args.all and (theme, mode) != target:
            continue
        print("-- %s %s " % (theme, mode) + "-" * (70 - len(theme) - len(mode)))
        print(header)
        for hexin, is_accent, want, per_theme in rows:
            t = next(p for p in per_theme if (p[0], p[1]) == (theme, mode))
            _th, _md, lo, where, rim_lo, out_hex, moved = t
            verdict = "ok" if lo >= want else ("-> %s" % out_hex if out_hex else "NO ROOM")
            print("%-9s %-7s %-9s %6.2f %6.2f  %-9s %s" % (
                hexin,
                "accent" if is_accent else "block",
                where.replace("--ui-", ""),
                lo, rim_lo,
                out_hex or "-",
                "" if not moved else "L %+.3f" % moved))
            # Only record a CHANGE. walk_to_ink returns the input unchanged
            # when nothing needed doing, and treating that as a fix made the
            # tool report five corrections on a palette it had not touched.
            if (theme, mode) == target and out_hex and out_hex.upper() != hexin.upper():
                fixed[hexin] = out_hex
        print()

    return (rows, fixed), 0


def emit(colours, fixed, accent_index, genre, theme, mode, blocks):
    """The paste-ready block. Scoped to the genre, never to :root."""
    tokens = next(t for th, md, t in blocks if (th, md) == (theme, mode))
    ink = parse_colour(tokens["--ui-text"])
    ink = flatten(ink, parse_colour(tokens["--ui-bg"])) if ink[3] < 1.0 else ink

    accent = fixed.get(colours[accent_index], colours[accent_index])
    ac = parse_colour(accent)
    # --ui-accent is a FILL as well as text -- ui.css paints buttons, meters,
    # switches and the focus ring with it -- so the ink that sits ON it has to
    # clear 4.5 too. White and black are the only two candidates and the
    # crossover between them is sqrt(0.0525)-0.05, not the midpoint: contrast
    # is a ratio and black has the shorter run to the floor.
    crossover = math.sqrt(0.0525) - 0.05
    from validate_palette import luminance
    accent_ink = "#FFFFFF" if luminance(ac) <= crossover else "#0B0B0C"

    blocks_out = [fixed.get(h, h) for j, h in enumerate(colours) if j != accent_index]

    lines = []
    lines.append("/* Imported by tools/import_palette.py and checked against %s %s."
                 % (theme, mode))
    lines.append("   Every value clears the bar it is measured at on all four of that")
    lines.append("   theme's grounds. Re-run the tool before changing any of them: these")
    lines.append("   are solved values, not chosen ones, and the solving is the point. */")
    lines.append('[data-genre="%s"]{' % genre)
    lines.append("  --ui-accent:%s;" % accent)
    lines.append("  --ui-accent-ink:%s;" % accent_ink)
    lines.append("  --ui-accent-hover:%s;" % hexof(mix_oklab(ac, ink, 0.85)))
    for n, h in enumerate(blocks_out, start=1):
        lines.append("  --ui-cat-%d:%s;" % (n, h))
    lines.append("}")
    return "\n".join(lines)


def main(argv):
    ap = argparse.ArgumentParser(
        prog="import_palette.py",
        description="Check an outside palette against Sjonis's grounds and emit a genre block.")
    ap.add_argument("colours", nargs="+", help="hex colours, accent first unless --accent")
    ap.add_argument("--theme", default="vanilla")
    ap.add_argument("--mode", default="light", choices=("light", "dark"))
    ap.add_argument("--all", action="store_true",
                    help="report against every theme x mode, to see how portable it is")
    ap.add_argument("--accent", type=int, default=None, metavar="N",
                    help="1-based index of the colour to promote to --ui-accent; "
                         "default is whichever needs the least correction")
    ap.add_argument("--genre", default="imported", help="genre id for the emitted selector")
    args = ap.parse_args(argv[1:])

    colours = [c if c.startswith("#") else "#" + c for c in args.colours]
    blocks = load_blocks(CSS)
    if not any((t, m) == (args.theme, args.mode) for t, m, _ in blocks):
        print("no such theme x mode: %s %s" % (args.theme, args.mode))
        return 1

    tokens = next(t for th, md, t in blocks if (th, md) == (args.theme, args.mode))
    grounds = grounds_of(tokens)

    # THE ACCENT IS CHOSEN BY MEASUREMENT, not by position. Only one colour has
    # to carry text, so the palette keeps the most of itself if the one picked
    # is the one already closest to clearing 4.5 -- every other choice moves a
    # colour further than it needed to move.
    if args.accent is not None:
        accent_index = args.accent - 1
    else:
        scored = [(worst(parse_colour(h), grounds)[0], j) for j, h in enumerate(colours)]
        accent_index = max(scored)[1]

    result, code = report(colours, blocks, accent_index, args)
    if code:
        return code
    _rows, fixed = result

    print("=" * 74)
    print("PASTE INTO genres/%s.css" % args.genre)
    print("=" * 74)
    print(emit(colours, fixed, accent_index, args.genre, args.theme, args.mode, blocks))
    print()
    if fixed:
        print("%d colour(s) were moved to clear their bar. The originals do not" % len(fixed))
        print("appear anywhere -- an unmeasured value in a token file is the thing")
        print("this tool exists to prevent.")
    else:
        print("Nothing needed moving. The palette clears every ground as supplied.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
