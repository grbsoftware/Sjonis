#!/usr/bin/env python3
"""Contrast validator for core/themes.css.

Checks every theme x mode against WCAG 2.1 contrast ratios, for the token pairs
that actually meet on screen: text on each ground, the accent's ink on the
accent, state colours on their soft grounds, and the categorical series on both
the page and a raised surface.

Two things it does that a naive checker does not:

  * Composites translucent tokens. halo's surfaces are rgba(); a ratio computed
    against the literal value is meaningless, because what the eye sees is that
    colour ALREADY blended over --ui-bg. Every rgba token is flattened over its
    theme's ground before comparison.
  * Emits ASCII only. cp1252 is still the default console encoding on Windows
    and a single tick mark is enough to kill the run.

Usage:
    python tools/validate_palette.py            # all themes, summary + failures
    python tools/validate_palette.py -v         # every pair, including passes
    python tools/validate_palette.py halo       # one theme

Exit code is 1 if any required pair fails, so it can gate a commit.
"""

import math
import re
import sys
import os

# ui.css: color-mix(in oklab, <series> 55%, var(--ui-text)). Keep in step with
# the --ui-mark-rim-mix default there, or this tool measures a different design.
RIM_MIX = 0.55

CSS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core", "themes.css")

# WCAG 2.1 thresholds. Body text is 4.5:1; "large" text and non-text UI parts
# (icons, borders, a chart mark) are 3.0:1 -- 1.4.11 Non-text Contrast.
AA_TEXT = 4.5
AA_LARGE = 3.0


# --------------------------------------------------------------------------
# colour
# --------------------------------------------------------------------------

def parse_colour(v):
    """-> (r, g, b, a) floats 0-255 / 0-1, or None if not a colour."""
    v = v.strip()
    m = re.match(r"^#([0-9A-Fa-f]{3})$", v)
    if m:
        h = m.group(1)
        return (int(h[0] * 2, 16), int(h[1] * 2, 16), int(h[2] * 2, 16), 1.0)
    m = re.match(r"^#([0-9A-Fa-f]{6})$", v)
    if m:
        h = m.group(1)
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 1.0)
    m = re.match(r"^rgba?\(([^)]+)\)$", v)
    if m:
        parts = [p.strip() for p in m.group(1).replace("/", ",").split(",")]
        if len(parts) < 3:
            return None
        try:
            r, g, b = (float(p.rstrip("%")) for p in parts[:3])
        except ValueError:
            return None
        a = float(parts[3]) if len(parts) > 3 else 1.0
        return (r, g, b, a)
    return None


def flatten(fg, bg):
    """Composite a possibly-translucent colour over an opaque one."""
    r1, g1, b1, a = fg
    r2, g2, b2, _ = bg
    return (r1 * a + r2 * (1 - a),
            g1 * a + g2 * (1 - a),
            b1 * a + b2 * (1 - a),
            1.0)


def _srgb_to_lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _lin_to_srgb(c):
    v = 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055
    return max(0.0, min(255.0, v * 255.0))


def to_oklab(rgb):
    r, g, b = (_srgb_to_lin(x) for x in rgb[:3])
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = (math.copysign(abs(v) ** (1.0 / 3.0), v) for v in (l, m, s))
    return (0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
            1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
            0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_)


def from_oklab(lab):
    L, a, b = lab
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = (v ** 3 for v in (l_, m_, s_))
    return (_lin_to_srgb(+4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s),
            _lin_to_srgb(-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s),
            _lin_to_srgb(-0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s),
            1.0)


def mix_oklab(a, b, t):
    """CSS color-mix(in oklab, `a` t%, `b`), with t as a 0-1 weight on `a`.

    Needed because ui.css derives the mark rim this way, and a checker that
    measured the raw fill instead would be measuring a design that is no longer
    on screen. Both inputs must already be opaque -- flatten() first.
    """
    la, lb = to_oklab(a), to_oklab(b)
    return from_oklab(tuple(x * t + y * (1 - t) for x, y in zip(la, lb)))


def luminance(c):
    def f(v):
        v = v / 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def ratio(a, b):
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


# --------------------------------------------------------------------------
# parse
# --------------------------------------------------------------------------

def load_blocks(path):
    """-> [(theme, mode, {token: raw_value})] in file order."""
    with open(path, encoding="utf-8") as fh:
        css = fh.read()
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)

    out = []
    pattern = re.compile(
        r'\[data-theme="(\w+)"\]\[data-mode="(\w+)"\]\s*\{(.*?)\n\}', re.S)
    for m in pattern.finditer(css):
        theme, mode, body = m.groups()
        tokens = {}
        for tm in re.finditer(r"(--ui-[\w-]+)\s*:\s*([^;]+);", body):
            tokens[tm.group(1)] = tm.group(2).strip()
        out.append((theme, mode, tokens))
    return out


def resolve(tokens, name, ground):
    """Token value as an opaque colour, composited over `ground` if needed."""
    raw = tokens.get(name)
    if raw is None:
        return None
    c = parse_colour(raw)
    if c is None:
        return None
    return flatten(c, ground) if c[3] < 1.0 else c


# --------------------------------------------------------------------------
# the pairs that actually meet on screen
# --------------------------------------------------------------------------

def checks(tokens, bg):
    """-> [(label, fg_token, bg_token, threshold, required)]

    Every row is a pairing that ui.css actually produces. Guessing at plausible
    pairs instead measures a design that does not exist: .ui-pill has NO
    background, for one, so its hue meets the page, never --ui-*-soft.
    """
    rows = []

    grounds = ["--ui-bg", "--ui-surface", "--ui-surface-2", "--ui-surface-3"]
    for g in grounds:
        rows.append(("body text", "--ui-text", g, AA_TEXT, True))
        rows.append(("dim text", "--ui-text-dim", g, AA_TEXT, True))
        # Faint is deliberately recessive -- timestamps, units, captions. Held
        # to the non-text bar and reported, not enforced: pushing it to 4.5
        # would collapse the three text levels into two.
        rows.append(("faint text", "--ui-text-faint", g, AA_LARGE, False))

    rows.append(("accent on page", "--ui-accent", "--ui-bg", AA_LARGE, True))
    rows.append(("accent on surface", "--ui-accent", "--ui-surface", AA_LARGE, True))
    # The label printed inside a filled button.
    rows.append(("ink on accent", "--ui-accent-ink", "--ui-accent", AA_TEXT, True))

    # .ui-pill-* : hue as text, transparent ground, border in currentColor.
    for state in ("good", "warn", "crit", "info"):
        fg = "--ui-%s" % state
        rows.append(("%s pill on page" % state, fg, "--ui-bg", AA_TEXT, True))
        rows.append(("%s pill on surface" % state, fg, "--ui-surface", AA_TEXT, True))

    # .ui-banner-* : hue as text ON its own soft ground. Only these three exist;
    # there is no .ui-banner-good, so --ui-good-soft is never a text ground.
    for state in ("crit", "warn", "info"):
        soft = "--ui-%s-soft" % state
        if soft in tokens:
            rows.append(("%s banner" % state, "--ui-%s" % state, soft, AA_TEXT, True))

    # The categorical marks are measured in mark_checks(): what meets the ground
    # is the computed rim, not the raw token, so it cannot be named as a pair.

    # Borders have no WCAG floor. Reported so a theme that loses its structure
    # is visible here rather than only in a screenshot.
    rows.append(("line on page", "--ui-line", "--ui-bg", 1.5, False))
    rows.append(("strong line on page", "--ui-line-strong", "--ui-bg", 2.0, False))

    return rows


def mark_checks(tokens, bg):
    """The categorical marks, whose colours are COMPUTED rather than named.

    Two things here cannot be expressed as a token pair:

      * .ui-dot and .ui-tag::before are delimited by a rim of the series hue
        mixed toward --ui-text. What has to clear 1.4.11's 3.0 is that rim
        against the ground -- the fill is inside the rim and is allowed to be
        any hue the palette wants. Measuring the fill instead is what produced
        the old 126-failure report for a problem the rim solves.
      * .ui-tag's ground is a 12% tint of the series hue over the surface, so
        the ground itself has to be computed before anything can be measured
        against it. Its label is --ui-text, not the hue (see ui.css).

    Returns rows already resolved to colours: (label, fg, bg, floor, required,
    fg_name, bg_name).
    """
    rows = []
    text = resolve(tokens, "--ui-text", bg)
    if text is None:
        return rows

    def rim(cat):
        return mix_oklab(cat, text, RIM_MIX)

    # The plain dot, on each ground it is actually placed on.
    for ground_name in ("--ui-bg", "--ui-surface", "--ui-surface-2", "--ui-surface-3"):
        ground = resolve(tokens, ground_name, bg)
        if ground is None:
            continue
        short = ground_name.replace("--ui-", "")
        for n in range(1, 9):
            cat = resolve(tokens, "--ui-cat-%d" % n, bg)
            if cat is None:
                continue
            rows.append(("cat-%d dot rim on %s" % (n, short),
                         rim(cat), ground, AA_LARGE, True,
                         "rim(--ui-cat-%d)" % n, ground_name))
            # Reported, never enforced. The whole point of the rim decision is
            # that the FILL keeps its identity; this line is here so the cost of
            # that choice stays visible instead of being quietly dropped.
            rows.append(("cat-%d fill on %s" % (n, short),
                         cat, ground, AA_LARGE, False,
                         "--ui-cat-%d" % n, ground_name))

    # The tag: computed tint ground, --ui-text label, rimmed dot.
    for ground_name in ("--ui-bg", "--ui-surface"):
        ground = resolve(tokens, ground_name, bg)
        if ground is None:
            continue
        short = ground_name.replace("--ui-", "")
        for n in range(1, 9):
            cat = resolve(tokens, "--ui-cat-%d" % n, bg)
            if cat is None:
                continue
            tinted = flatten((cat[0], cat[1], cat[2], 0.12), ground)
            rows.append(("cat-%d tag label on %s" % (n, short),
                         text, tinted, AA_TEXT, True,
                         "--ui-text", ".ui-tag/cat-%d on %s" % (n, short)))
            rows.append(("cat-%d tag dot rim on %s" % (n, short),
                         rim(cat), tinted, AA_LARGE, True,
                         "rim(--ui-cat-%d)" % n, ".ui-tag tint on %s" % short))
    return rows


# --------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------

def main(argv):
    verbose = "-v" in argv or "--verbose" in argv
    wanted = [a for a in argv[1:] if not a.startswith("-")]

    blocks = load_blocks(CSS)
    if not blocks:
        print("no theme blocks found in %s" % CSS)
        return 2

    failures = []
    warnings = []
    total = 0

    for theme, mode, tokens in blocks:
        if wanted and theme not in wanted:
            continue

        bg = parse_colour(tokens.get("--ui-bg", ""))
        if bg is None:
            failures.append((theme, mode, "--ui-bg", "", 0.0, 0.0))
            print("%-10s %-5s  NO OPAQUE --ui-bg -- cannot composite" % (theme, mode))
            continue

        print("")
        print("%s %s" % (theme, mode))
        print("-" * 58)

        rows = []
        for label, fg_tok, bg_tok, floor, required in checks(tokens, bg):
            fg = resolve(tokens, fg_tok, bg)
            ground = resolve(tokens, bg_tok, bg)
            if fg is None or ground is None:
                continue
            rows.append((label, fg, ground, floor, required, fg_tok, bg_tok))
        for label, fg, ground, floor, required, fg_tok, bg_tok in mark_checks(tokens, bg):
            rows.append((label, fg, ground, floor, required, fg_tok, bg_tok))

        for label, fg, ground, floor, required, fg_tok, bg_tok in rows:
            total += 1
            r = ratio(fg, ground)
            ok = r >= floor
            if not ok:
                (failures if required else warnings).append(
                    (theme, mode, fg_tok, bg_tok, r, floor))
            if verbose or not ok:
                print("  %-6s %-26s %5.2f  (need %.1f)%s" % (
                    "PASS" if ok else ("FAIL" if required else "warn"),
                    label, r, floor,
                    "" if ok else "  <-- " + fg_tok + " on " + bg_tok))

        if not verbose:
            print("  %d pairs checked" % len(rows))

    print("")
    print("=" * 58)
    print("%d pairs checked, %d failures, %d advisory" % (total, len(failures), len(warnings)))

    if warnings and not verbose:
        print("")
        print("advisory (not enforced):")
        for theme, mode, fg, bg_tok, r, floor in warnings:
            print("  %-10s %-5s %s on %s  %.2f (want %.1f)" % (theme, mode, fg, bg_tok, r, floor))

    if failures:
        print("")
        print("FAILURES:")
        for theme, mode, fg, bg_tok, r, floor in failures:
            print("  %-10s %-5s %s on %s  %.2f (need %.1f)" % (theme, mode, fg, bg_tok, r, floor))
        return 1

    print("all required pairs pass")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
