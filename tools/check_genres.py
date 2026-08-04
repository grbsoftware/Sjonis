#!/usr/bin/env python3
"""Gate for the genre ring.

A genre's composition is spelled out twice on purpose: once in
tokens/genres.json, which is the authored record, and once in the markup of any
page that wears it, because the alternative was to have data-genre imply the
rest -- which either makes every theme know about every genre, or stops the page
resolving without JavaScript. Everything here has to survive being double-clicked
off a disk, so the composition is written out and this file checks the spelling.

Checks, in order of how badly each would rot:

  * Every genre names a skin, a theme and a mode that exist.
  * Every genre names skeletons that exist.
  * Every genre has a stylesheet, and it is scoped to its own id -- a genre file
    with a bare `.ui-brand` rule would restyle every page that loads it.
  * Every page carrying data-genre matches its manifest entry exactly, and links
    the four stylesheets that composition needs.
  * Every genre states a `why`. A named look with no point of view is a preset,
    and the whole ring exists to not be a preset.

python tools/check_genres.py, exit 1 on failure. ASCII only -- cp1252 is still
the default console encoding on Windows.
"""

import glob
import json
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
MANIFEST = os.path.join(ROOT, "tokens", "genres.json")
THEMES = os.path.join(ROOT, "core", "themes.css")

REQUIRED = ("id", "name", "skin", "theme", "mode", "skeletons", "why")

# The default skin, which lives in ui.css rather than in skins/ because
# something has to define the four role tokens before any skin loads. It is
# still a skin and a genre may name it; it just ships no stylesheet and sets
# no data-skin, because there is no rule for the attribute to match.
FLAT_SKIN = "flat"


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def selectors(css):
    """Every rule selector in a stylesheet, at-rules walked into rather than over.

    This was a regex and the regex was wrong twice, in opposite directions:
    the first version refused to start a selector with `@`, which skipped a
    media query's prelude AND everything nested inside it; the fix that
    flattened preludes then let a greedy character class swallow the inner
    selectors into an empty capture, so a deliberately planted
    `.ui-card{border:1px solid red}` inside @media(forced-colors) passed
    silently. A leak that only appears under high contrast is the worst kind,
    because nobody testing normally will ever see it.

    Scanning braces is not clever, and that is the point -- it cannot be fooled
    by nesting, by commas in a selector list, or by a colon in a declaration.
    Comments must already be stripped.
    """
    out, buf, at_depth, depth = [], [], None, 0
    for ch in css:
        if ch == "{":
            sel = "".join(buf).strip()
            buf = []
            depth += 1
            if sel.startswith("@"):
                # An at-rule's own prelude is not a selector. Remember where it
                # opened so its CONTENTS are still checked as ordinary rules.
                if at_depth is None:
                    at_depth = depth
            elif sel:
                out.append(sel)
        elif ch == "}":
            buf = []
            depth -= 1
            if at_depth is not None and depth < at_depth:
                at_depth = None
        elif ch == ";":
            buf = []          # a declaration, not the start of a selector
        else:
            buf.append(ch)
    return out


def attrs(html):
    """data-* attributes on the tag that carries data-genre.

    Deliberately NOT "the <html> tag". A genre's four attributes have to sit on
    the element that carries class="ui", because ui.css's derived block is
    `:root,.ui` and re-declares the skin's four role tokens at the .ui level --
    a skin on an ancestor is overwritten and does nothing, silently. So a page
    may legitimately put them on <body>, and a checker that only reads <html>
    would pass a page whose skin is inert.
    """
    m = re.search(r"<(\w+)\b([^>]*\bdata-genre\s*=[^>]*)>", html, re.I)
    if not m:
        return {}
    found = dict(re.findall(r'(data-[\w-]+)\s*=\s*"([^"]*)"', m.group(2)))
    found["_tag"] = m.group(1).lower()
    found["_has_ui"] = bool(re.search(r'class\s*=\s*"[^"]*\bui\b', m.group(2)))
    return found


def main():
    fails = []

    if not os.path.exists(MANIFEST):
        print("no manifest at %s" % MANIFEST)
        return 2
    try:
        data = json.loads(read(MANIFEST))
    except ValueError as e:
        print("manifest is not valid JSON: %s" % e)
        return 2

    themes_css = read(THEMES)
    known_themes = set(re.findall(r'\[data-theme="(\w+)"\]', themes_css))
    genres = data.get("genres", [])
    if not genres:
        print("manifest lists no genres")
        return 2

    by_id = {}
    for g in genres:
        gid = g.get("id", "<unnamed>")
        by_id[gid] = g

        for field in REQUIRED:
            if not g.get(field):
                fails.append("%s: missing or empty '%s'" % (gid, field))

        skin = g.get("skin")
        # "flat" IS a skin -- it is the default set of role tokens, and it lives
        # in ui.css because something has to be there before any skin loads.
        # That does not make it nameless, and a genre whose point of view is
        # "no depth at all" has to be able to say so. Everything downstream
        # treats it as a skin with no stylesheet rather than as an absence:
        # data-skin is left OFF the element (there is no rule to match) and no
        # link is added, which is exactly what a hand-written flat page does.
        if skin and skin != FLAT_SKIN \
                and not os.path.exists(os.path.join(ROOT, "skins", "%s.css" % skin)):
            fails.append("%s: skin '%s' has no skins/%s.css" % (gid, skin, skin))

        theme = g.get("theme")
        if theme and theme not in known_themes:
            fails.append("%s: theme '%s' is not in core/themes.css (have: %s)"
                         % (gid, theme, ", ".join(sorted(known_themes))))

        if g.get("mode") not in ("light", "dark"):
            fails.append("%s: mode '%s' is not light or dark" % (gid, g.get("mode")))

        for sk in g.get("skeletons", []):
            if not os.path.exists(os.path.join(ROOT, "skeletons", "%s.html" % sk)):
                fails.append("%s: skeleton '%s' has no skeletons/%s.html" % (gid, sk, sk))

        css = os.path.join(ROOT, "genres", "%s.css" % gid)
        if not os.path.exists(css):
            fails.append("%s: no genres/%s.css" % (gid, gid))
        else:
            # Every rule must be scoped to this genre. A genre that leaks is
            # worse than a broken one: it silently restyles pages that merely
            # link it, and nothing in the page says why.
            body = re.sub(r"/\*.*?\*/", "", read(css), flags=re.S)
            for sel in selectors(body):
                sel = " ".join(sel.split())
                for one in sel.split(","):
                    one = one.strip()
                    if one and '[data-genre="%s"]' % gid not in one:
                        fails.append("%s: unscoped selector in genres/%s.css -- %s"
                                     % (gid, gid, one[:60]))

    # Pages that claim a genre have to agree with it.
    pages = []
    for pat in ("*.html", "*/*.html"):
        pages.extend(glob.glob(os.path.join(ROOT, pat)))
    checked = 0
    for page in sorted(set(pages)):
        html = read(page)
        a = attrs(html)
        gid = a.get("data-genre")
        if not gid:
            continue
        checked += 1
        rel = os.path.relpath(page, ROOT).replace("\\", "/")
        g = by_id.get(gid)
        if g is None:
            fails.append("%s: declares genre '%s', which is not in the manifest" % (rel, gid))
            continue
        for attr, key in (("data-theme", "theme"), ("data-mode", "mode"), ("data-skin", "skin")):
            want = g.get(key)
            # flat sets no data-skin: the absence IS the value. Demanding
            # data-skin="flat" would invent an attribute nothing reads.
            if key == "skin" and want == FLAT_SKIN:
                if a.get(attr) is not None:
                    fails.append("%s: data-skin is '%s', but the manifest says flat, "
                                 "which sets no data-skin at all" % (rel, a.get(attr)))
                continue
            if a.get(attr) != want:
                fails.append("%s: %s is '%s', manifest says '%s'"
                             % (rel, attr, a.get(attr), want))
        # The four have to be on the .ui element or the skin is inert. See attrs().
        if not a.get("_has_ui"):
            fails.append("%s: data-genre is on <%s>, which has no class=\"ui\" -- "
                         "ui.css re-declares the role tokens at .ui, so the skin "
                         "will silently do nothing" % (rel, a.get("_tag")))
        needs = ["core/ui.css", "core/themes.css", "genres/%s.css" % gid]
        if g.get("skin") != FLAT_SKIN:
            needs.insert(2, "skins/%s.css" % g.get("skin"))
        for needed in needs:
            if needed not in html:
                fails.append("%s: does not link %s" % (rel, needed))

    print("%d genre(s), %d page(s) wearing one" % (len(genres), checked))
    if fails:
        print("")
        for f in fails:
            print("  FAIL  %s" % f)
        return 1
    print("all genre references resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main())
