#!/usr/bin/env python3
"""Contrast validator for core/themes.css AND every skin in skins/.

Checks every theme x mode against WCAG 2.1 contrast ratios, for the token pairs
that actually meet on screen: text on each ground, the accent's ink on the
accent, state colours on their soft grounds, and the categorical series on both
the page and a raised surface.

Then it does the same again per skin. This half exists because a skin REPLACES
the ground that text is read against, and the theme pass cannot see that: while
skins/bevel.css was being built this tool reported green through two real
failures -- --ui-text-dim at 2.7-3.3 on the bevel face in all twelve theme x
mode combinations (and .ui-table td prints in exactly that token), and bevel's
two edges invisible on half the palette each. Both were caught by hand. A gate
that only reports what is already known to be fine is not a gate.

Three things it does that a naive checker does not:

  * Composites translucent tokens. halo's surfaces are rgba(); a ratio computed
    against the literal value is meaningless, because what the eye sees is that
    colour ALREADY blended over --ui-bg. Every rgba token is flattened over its
    theme's ground before comparison.
  * Evaluates var() and color-mix() rather than reading token text. A skin's
    surfaces are DERIVED -- bevel's face is a 70/30 mix of the theme's own bg
    and ink, and its edges are mixes of that. There is no literal to look up,
    so the tool computes what the browser computes (trap 15, one ring out).
  * Emits ASCII only. cp1252 is still the default console encoding on Windows
    and a single tick mark is enough to kill the run.

Usage:
    python tools/validate_palette.py            # themes + every skin
    python tools/validate_palette.py -v         # every pair, including passes
    python tools/validate_palette.py halo       # one theme (and skins on it)
    python tools/validate_palette.py --no-skins # themes only, the old behaviour
    python tools/validate_palette.py --skin skins/bevel.css   # one skin

Exit code is 1 if any required pair fails, so it can gate a commit.
"""

import glob
import math
import re
import sys
import os

# ui.css: color-mix(in oklab, <series> 55%, var(--ui-text)). Keep in step with
# the --ui-mark-rim-mix default there, or this tool measures a different design.
RIM_MIX = 0.55

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
CSS = os.path.join(ROOT, "core", "themes.css")
UI_CSS = os.path.join(ROOT, "core", "ui.css")
SKINS = os.path.join(ROOT, "skins")

# The four roles of the skin ring. Named here only so the tool can look for
# `--ui-<role>-fill`; WHICH component wears which role is read out of ui.css at
# run time and never written down twice (see role_map).
ROLES = ("raise", "float", "inset", "control")

# An edge has no WCAG floor -- it is a drawn boundary, not text, and a bevel's
# lit edge is meant to be subtle. Held to the same advisory bar as --ui-line so
# an edge that has flattened into its own face still shows up here. bevel's
# solved worst case is 1.81, and its broken first attempt was 1.04.
EDGE_WANT = 1.5

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


def _mix_premul(a, b, t, fwd, back):
    """Weighted mix with alpha premultiplied, which is what color-mix() does."""
    aa, ab = a[3], b[3]
    out_a = aa * t + ab * (1 - t)
    if out_a <= 0:
        return (0.0, 0.0, 0.0, 0.0)
    ca, cb = fwd(a), fwd(b)
    ch = tuple((x * aa * t + y * ab * (1 - t)) / out_a for x, y in zip(ca, cb))
    r, g, bl = back(ch)[:3]
    return (r, g, bl, out_a)


def mix_colour(space, a, b, t):
    """color-mix(in `space`, `a` t%, `b`) -- t as a 0-1 weight on `a`.

    srgb is a straight lerp of the channel values AS AUTHORED: `srgb` is the
    gamma-encoded space in CSS Color 4, `srgb-linear` is the other one. Mixing
    in linear light instead would move bevel's face by several percent and the
    tool would be measuring a design that is not on screen.

    Any other space returns None rather than a guess. A skin that reaches for
    lch or hwb should make this tool say so out loud -- silently substituting
    srgb is how a checker starts reporting on a design nobody wrote.
    """
    if space in ("srgb", ""):
        return _mix_premul(a, b, t, lambda c: c[:3], lambda v: v)
    if space == "oklab":
        return _mix_premul(a, b, t, to_oklab, from_oklab)
    return None


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


# The only bare keywords that appear in this codebase's colour slots. `white`
# and `black` are not palette entries -- they are the two ends of lightness,
# which is why a skin is allowed them (see the header of skins/bevel.css).
NAMED = {"white": (255.0, 255.0, 255.0, 1.0),
         "black": (0.0, 0.0, 0.0, 1.0),
         "transparent": (0.0, 0.0, 0.0, 0.0)}


def split_top(s, sep=","):
    """Split on `sep`, ignoring anything inside parentheses."""
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == sep and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    out.append(cur)
    return [p.strip() for p in out if p.strip()]


def _call(expr, name):
    """If `expr` is exactly one `name(...)` call, return the argument text.

    Not a regex: `var(--a) var(--b)` and `var(--a, var(--b))` are the same
    shape to `^name\\((.*)\\)$` and mean completely different things.
    """
    if not expr.lower().startswith(name + "("):
        return None
    depth = 0
    for i, ch in enumerate(expr):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return expr[len(name) + 1:i] if i == len(expr) - 1 else None
    return None


def _weighted(arg):
    """-> (value_text, percent or None) for one color-mix() argument."""
    pct, rest = None, []
    for tok in split_top(arg, " "):
        if re.match(r"^[\d.]+%$", tok):
            pct = float(tok[:-1])
        else:
            rest.append(tok)
    return " ".join(rest), pct


def evaluate(expr, env, depth=0, seen=()):
    """Resolve a CSS value to (r,g,b,a), following var() and color-mix().

    `env` maps custom-property names to their raw declared text. Returns None
    for anything that is not a colour -- `2px solid`, `none`, `currentColor`,
    a cycle, an unmodelled colour space -- so callers can skip rather than
    invent a number.
    """
    if depth > 24 or not expr:
        return None
    expr = expr.strip()
    if not expr:
        return None

    lit = parse_colour(expr)
    if lit is not None:
        return lit
    if expr.lower() in NAMED:
        return NAMED[expr.lower()]

    arg = _call(expr, "var")
    if arg is not None:
        parts = split_top(arg)
        name = parts[0].strip()
        # A var() cycle is a real thing an author can write, and unguarded it
        # is an infinite loop rather than a diagnostic.
        if name in env and name not in seen:
            got = evaluate(env[name], env, depth + 1, tuple(seen) + (name,))
            if got is not None:
                return got
        if len(parts) > 1:
            return evaluate(",".join(parts[1:]), env, depth + 1, seen)
        return None

    arg = _call(expr, "color-mix")
    if arg is not None:
        parts = split_top(arg)
        if len(parts) != 3:
            return None
        space = parts[0].split()[-1].strip().lower() if parts[0].strip() else ""
        (va, pa), (vb, pb) = _weighted(parts[1]), _weighted(parts[2])
        ca, cb = evaluate(va, env, depth + 1, seen), evaluate(vb, env, depth + 1, seen)
        if ca is None or cb is None:
            return None
        if pa is None and pb is None:
            pa = pb = 50.0
        elif pa is None:
            pa = 100.0 - pb
        elif pb is None:
            pb = 100.0 - pa
        if pa + pb <= 0:
            return None
        return mix_colour(space, ca, cb, pa / (pa + pb))

    return None


def load_rules(path):
    """-> [(selector, {prop: value})], declaration rules only, in file order.

    Skips anything inside an at-rule. bevel's forced-colors block repaints every
    edge as CanvasText, which is the UA's colour and not ours to measure; taking
    it at face value would report a skin as fixed when the fix only applies
    under High Contrast.
    """
    with open(path, encoding="utf-8") as fh:
        css = re.sub(r"/\*.*?\*/", "", fh.read(), flags=re.S)

    rules, buf, stack = [], "", []
    for ch in css:
        if ch == "{":
            stack.append(buf.strip())
            buf = ""
        elif ch == "}":
            sel = stack.pop() if stack else ""
            body = buf.strip()
            buf = ""
            if body and not sel.startswith("@") and not any(s.startswith("@") for s in stack):
                decls = []
                for dm in re.finditer(r"([-\w]+)\s*:\s*([^;]+)", body):
                    decls.append((dm.group(1), dm.group(2).strip()))
                if decls:
                    rules.append((" ".join(sel.split()), decls))
        else:
            buf += ch
    return rules


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

    mix = rim_mix(tokens)

    def rim(cat):
        return mix_oklab(cat, text, mix)

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
# skins -- the ring the theme pass is blind to
# --------------------------------------------------------------------------
#
# A skin changes the GROUND. Everything above measures tokens against tokens,
# which is right for a theme (a theme can only set values) and useless for a
# skin (a skin may add rules, and its surfaces are computed). So this half works
# the other way round: find every surface that is actually painted, compute what
# it resolves to, and re-run the same battery against it.
#
# Nothing here is hardcoded about which component wears which role. That map is
# read out of ui.css, because ui.css is where the decision lives -- writing it
# down a second time is how a checker starts describing an older design.


def rim_mix(env):
    """--ui-mark-rim-mix in force here, as a 0-1 weight on the series hue.

    ui.css declares that hook as a plain percentage precisely so it can be set
    from any level, and a skin that has moved the ground is the case it was put
    there for. Reading the constant instead would report the rim a skin has
    already fixed as still broken.
    """
    raw = env.get("--ui-mark-rim-mix")
    if raw:
        m = re.match(r"^\s*([\d.]+)%", raw)
        if m:
            return float(m.group(1)) / 100.0
    return RIM_MIX


def base_selector(sel):
    """`.ui-btn:active` -> `.ui-btn`. Strips pseudo-classes and elements."""
    prev = None
    while prev != sel:
        prev = sel
        sel = re.sub(r"::?[\w-]+(\([^)]*\))?$", "", sel).strip()
    return sel


def strip_skin(sel, name):
    """`[data-skin="bevel"] .ui-card` -> `.ui-card`."""
    return re.sub(r'^\[data-skin="%s"\]\s*' % re.escape(name), "", sel).strip()


def root_tokens(rules):
    """Custom properties declared on :root / .ui, in cascade order."""
    out = {}
    for sel, decls in rules:
        if ":root" in sel or sel.strip() == ".ui":
            for prop, val in decls:
                if prop.startswith("--"):
                    out[prop] = val
    return out


def role_map(ui_rules):
    """-> {selector: (role, ink_token)} read out of ui.css.

    A component belongs to a role because ui.css paints it with that role's
    fill. The ink is whatever `color` the same rule sets -- .ui-btn prints in
    --ui-accent-ink, not --ui-text, and checking it against the wrong one would
    either invent a failure or hide a real one.
    """
    out = {}
    for sel, decls in ui_rules:
        props = dict(decls)
        bg = props.get("background") or props.get("background-color") or ""
        for role in ROLES:
            if "--ui-%s-fill" % role in bg:
                ink = props.get("color", "var(--ui-text)")
                for one in split_top(sel):
                    out[one] = (role, ink)
    return out


def skin_surfaces(skin_name, skin_rules, ui_roles):
    """Every painted surface a skin puts on screen.

    Two sources, and both are needed. The role fills are the skin's contract and
    cover the components ui.css maps. The explicit backgrounds are the rules a
    skin is allowed to add and a theme is not -- bevel paints .ui-table th,
    .ui-tab and .ui-rail directly, and those are surfaces with text on them that
    no role token describes.

    Each surface is tagged CONTAINER or CHROME, and the distinction decides how
    much gets measured against it. A card or a dialog holds arbitrary content, so
    a status pill or a series dot can land there and every ink token is in play.
    A button, a tab, a table head or a rail holds a label -- asserting that
    --ui-crit must be readable on a tab is measuring a design nobody wrote, which
    is the same mistake checks() exists to avoid, one ring out.

    Containers are raise and float, and that is not a judgement call: those are
    the two roles ui.css puts arbitrary children inside.

    -> [(selector, fill_expr, ink_expr, is_container)]
    """
    seen, out = set(), []

    for sel, (role, ink) in sorted(ui_roles.items()):
        out.append((sel, "var(--ui-%s-fill)" % role, ink, role in ("raise", "float")))
        seen.add(sel)

    for sel, decls in skin_rules:
        props = dict(decls)
        bg = props.get("background") or props.get("background-color")
        if not bg:
            continue
        for one in split_top(sel):
            one = strip_skin(one, skin_name)
            if not one or one in seen:
                continue
            seen.add(one)
            ink = props.get("color")
            if ink is None:
                mapped = ui_roles.get(base_selector(one))
                ink = mapped[1] if mapped else "var(--ui-text)"
            # A surface the skin invented inherits its role from the component
            # it is based on, and is chrome otherwise: a skin adds panels and
            # headers, it does not add new kinds of container.
            mapped = ui_roles.get(base_selector(one))
            out.append((one, bg, ink, bool(mapped) and mapped[0] in ("raise", "float")))
    return out


def skin_env(base, skin_name, skin_root, skin_rules, selector):
    """Token values in force on one element: theme, then skin, then scope.

    The scoped half is load-bearing. bevel re-derives --ui-text-dim on its own
    faces precisely because the inherited value fails there; an env that stopped
    at the skin's root block would report a failure the skin has already fixed.
    """
    env = dict(base)
    env.update(skin_root)
    want = {selector, base_selector(selector)}
    for sel, decls in skin_rules:
        targets = set()
        for one in split_top(sel):
            one = strip_skin(one, skin_name)
            targets.add(one)
            targets.add(base_selector(one))
        if targets & want:
            for prop, val in decls:
                if prop.startswith("--"):
                    env[prop] = val
    return env


def surface_checks(env, ground, ground_label, ink_expr, container, pill_bg=None):
    """The battery for ONE computed ground. Same pairings as checks()."""
    rows = []

    def add(label, fg, floor, required, name):
        if fg is not None:
            rows.append((label, flatten(fg, ground) if fg[3] < 1 else fg,
                         ground, floor, required, name, ground_label))

    # Every surface holds a label, so its own ink always applies.
    ink = evaluate(ink_expr, env)
    add("ink", ink, AA_TEXT, True, ink_expr.strip())

    # The rest of the text hierarchy only applies where the ink IS --ui-text.
    # A filled button prints one label in --ui-accent-ink and nothing else; a
    # dim placeholder on an accent-filled surface is not a thing that exists.
    if "--ui-text" not in ink_expr:
        return rows

    add("dim text", evaluate("var(--ui-text-dim)", env), AA_TEXT, True, "--ui-text-dim")
    add("faint text", evaluate("var(--ui-text-faint)", env), AA_LARGE, False, "--ui-text-faint")
    add("accent", evaluate("var(--ui-accent)", env), AA_LARGE, True, "--ui-accent")

    # Marks only land inside a container. See skin_surfaces().
    if not container:
        return rows

    # .ui-pill-* prints its hue as text and ui.css gives it no ground, so it
    # meets the skin's face directly -- the same reasoning as checks(), one ring
    # out. Unless the skin gives it one: a skin may add rules, and putting the
    # pill in a well is a legitimate answer to a face the hue cannot sit on.
    # Reading the ground back out of the CSS is the only way to tell which
    # design is on screen (trap 15).
    pill_ground = ground
    if pill_bg:
        got = evaluate(pill_bg, env)
        if got is not None:
            pill_ground = flatten(got, ground) if got[3] < 1 else got
    for state in ("good", "warn", "crit", "info"):
        hue = evaluate("var(--ui-%s)" % state, env)
        if hue is not None:
            rows.append(("%s pill" % state,
                         flatten(hue, pill_ground) if hue[3] < 1 else hue,
                         pill_ground, AA_TEXT, True, "--ui-%s" % state,
                         ground_label if pill_ground is ground else ".ui-pill"))

    text = evaluate("var(--ui-text)", env)
    if text is not None:
        text = flatten(text, ground) if text[3] < 1 else text
        mix = rim_mix(env)
        for n in range(1, 9):
            cat = evaluate("var(--ui-cat-%d)" % n, env)
            if cat is None:
                continue
            cat = flatten(cat, ground) if cat[3] < 1 else cat
            add("cat-%d dot rim" % n, mix_oklab(cat, text, mix),
                AA_LARGE, True, "rim(--ui-cat-%d)" % n)
            add("cat-%d fill" % n, cat, AA_LARGE, False, "--ui-cat-%d" % n)
    return rows


def edge_checks(env, ground, outer, ground_label, decls):
    """Every drawn edge on this surface, against BOTH sides of itself.

    An edge that has flattened into its own face is not a style bug, it is a
    missing boundary -- and it is invisible in a screenshot of the one theme the
    author happened to be looking at. bevel's first attempt had an invisible lit
    edge in every light mode and an invisible shade edge in every dark one, in
    all twelve combinations, and nothing reported it.

    But an edge has two sides, and it only has to be visible against ONE of
    them. This is not a loophole; it is how a sunken control has always been
    drawn -- Win95's white list box showed its dark edge against the white
    interior and its light edge against the grey panel around it, and neither
    edge was visible against both. Measuring against the fill alone reported
    bevel's inset lit edge at 1.10 and called it broken when it is doing exactly
    its job. The score kept is the better of the two.
    """
    rows, seen = [], set()
    for prop, val in decls:
        if not prop.startswith("border"):
            continue
        for tok in split_top(val, " "):
            c = evaluate(tok, env)
            if c is None or tok in seen:
                continue
            seen.add(tok)
            # A deliberately absent edge is not a failed edge. bevel's selected
            # folder tab has no bottom border precisely so it joins the panel
            # under it; scoring that as an invisible boundary would report the
            # design working as intended.
            if c[3] == 0:
                continue
            inner = flatten(c, ground) if c[3] < 1 else c
            best, against = ratio(inner, ground), ground
            if outer is not None:
                out_c = flatten(c, outer) if c[3] < 1 else c
                if ratio(out_c, outer) > best:
                    best, against, inner = ratio(out_c, outer), outer, out_c
            rows.append(("edge", inner, against, EDGE_WANT, False,
                         tok if len(tok) < 40 else "edge", ground_label))
    return rows


def skin_rows(path, base, ui_rules, ui_roles):
    """All rows for one skin against one already-resolved theme env."""
    skin_rules = load_rules(path)
    name = os.path.splitext(os.path.basename(path))[0]
    skin_root = {}
    for sel, decls in skin_rules:
        if strip_skin(sel, name) == "" and 'data-skin="%s"' % name in sel:
            for prop, val in decls:
                if prop.startswith("--"):
                    skin_root[prop] = val

    # A ground the skin hands to the pill, if it hands it one. See surface_checks.
    pill_bg = None
    for sel, decls in skin_rules:
        if ".ui-pill" in [strip_skin(s, name) for s in split_top(sel)]:
            props = dict(decls)
            pill_bg = props.get("background") or props.get("background-color") or pill_bg

    page_bg = evaluate("var(--ui-bg)", base)
    rows = []
    for sel, fill, ink, container in skin_surfaces(name, skin_rules, ui_roles):
        env = skin_env(base, name, skin_root, skin_rules, sel)
        ground = evaluate(fill, env)
        if ground is None:
            continue
        if ground[3] < 1 and page_bg is not None:
            ground = flatten(ground, page_bg)

        # What is on the far side of this element's edge. Only a container sits
        # directly on the page; an input, a button, a status pill sit inside one.
        # Approximate, and stated as such -- but the alternative is to model
        # containment from the markup, which the CSS does not record, and the
        # crude version of this reported bevel's sunken pill as edgeless when it
        # is drawn exactly the way a sunken field has always been drawn: dark
        # edge against the light interior, light edge against the panel outside.
        role = ui_roles.get(base_selector(sel), (None, None))[0]
        outer_expr = "var(--ui-bg)" if role in ("raise", "float") else "var(--ui-raise-fill)"
        # Resolved in the OUTER env, deliberately. bevel's filled button
        # redefines --ui-bevel-face to the accent for its own edges, so asking
        # this element what --ui-raise-fill means answers "the accent" -- the
        # button's own face, not the panel it sits on. Measured that way its lit
        # edge scored 1.27 against itself when against the panel it is 1.73.
        outer = evaluate(outer_expr, dict(base, **skin_root))
        if outer is not None and outer[3] < 1 and page_bg is not None:
            outer = flatten(outer, page_bg)

        for r in surface_checks(env, ground, sel, ink, container, pill_bg):
            rows.append((sel,) + r)
        for rule_sel, decls in skin_rules:
            targets = set()
            for one in split_top(rule_sel):
                one = strip_skin(one, name)
                targets.update((one, base_selector(one)))
            if sel in targets or base_selector(sel) in targets:
                for r in edge_checks(env, ground, outer, sel, decls):
                    rows.append((sel,) + r)
    return name, rows


# --------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------

def main(argv):
    verbose = "-v" in argv or "--verbose" in argv

    skin_files = []
    wanted = []
    take_skin = False
    for a in argv[1:]:
        if take_skin:
            skin_files.append(a)
            take_skin = False
        elif a == "--skin":
            take_skin = True
        elif not a.startswith("-"):
            wanted.append(a)
    if not skin_files and "--no-skins" not in argv:
        skin_files = sorted(glob.glob(os.path.join(SKINS, "*.css")))

    blocks = load_blocks(CSS)
    if not blocks:
        print("no theme blocks found in %s" % CSS)
        return 2

    ui_rules = load_rules(UI_CSS) if skin_files else []
    ui_base = root_tokens(ui_rules)
    ui_roles = role_map(ui_rules)
    if skin_files and not ui_roles:
        print("no role fills found in %s -- cannot check skins" % UI_CSS)
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

        # The skin pass, on this same theme x mode. A skin is not a theme's
        # peer -- it sits on top of one, so there is no such thing as checking
        # a skin once.
        for path in skin_files:
            skin, srows = skin_rows(path, dict(ui_base, **tokens), ui_rules, ui_roles)
            bad = 0
            for sel, label, fg, ground, floor, required, fg_tok, bg_tok in srows:
                total += 1
                r = ratio(fg, ground)
                ok = r >= floor
                if not ok:
                    bad += 1
                    where = "%s %s" % (skin, sel)
                    (failures if required else warnings).append(
                        (theme, mode, fg_tok, where, r, floor))
                if verbose or not ok:
                    print("  %-6s %-26s %5.2f  (need %.1f)%s" % (
                        "PASS" if ok else ("FAIL" if required else "warn"),
                        ("%s %s %s" % (skin, sel, label))[:26], r, floor,
                        "" if ok else "  <-- " + fg_tok + " on " + sel))
            if not verbose:
                print("  %d pairs checked on skin %s%s" % (
                    len(srows), skin, "" if not bad else "  (%d below bar)" % bad))

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
