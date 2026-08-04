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


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def attrs(html):
    """data-* attributes on the first <html> tag."""
    m = re.search(r"<html\b([^>]*)>", html, re.I)
    if not m:
        return {}
    return dict(re.findall(r'(data-[\w-]+)\s*=\s*"([^"]*)"', m.group(1)))


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
        if skin and not os.path.exists(os.path.join(ROOT, "skins", "%s.css" % skin)):
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
            for sel in re.findall(r"(?:^|\})\s*([^{}@][^{}]*)\{", body):
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
            if a.get(attr) != g.get(key):
                fails.append("%s: %s is '%s', manifest says '%s'"
                             % (rel, attr, a.get(attr), g.get(key)))
        for needed in ("core/ui.css", "core/themes.css",
                       "skins/%s.css" % g.get("skin"), "genres/%s.css" % gid):
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
