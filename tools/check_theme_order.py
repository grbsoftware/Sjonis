#!/usr/bin/env python3
"""Every list that lets you CHOOSE a theme must offer them in one order.

Gary noticed the ordering differed between pages and asked whether it should be
a class. It should not: a class is for styling, and this is a single source of
truth problem. Nothing renders differently -- the lists just disagree, and a
reader picking a theme on two pages should not have to re-find it.

THE CANONICAL ORDER IS core/themes.css's OWN, first appearance wins. Not a list
written down here, because a second list is the thing that drifts. Add a theme
to themes.css and it takes its place; this file only checks that every chooser
agrees.

WHAT IS DELIBERATELY NOT CHECKED: specimens/. Those pages are dated decks, not
choosers. directions-01.html numbers its five plates 01-05 in the order they
were presented, and vanilla is absent because vanilla was designed afterwards.
Renumbering it to match would falsify a record of what was actually shown. The
rule is about pickers, and a specimen is not a picker.

python tools/check_theme_order.py, exit 1 on failure. ASCII only.
"""

import glob
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
THEMES = os.path.join(ROOT, "core", "themes.css")
SKIP_DIRS = ("specimens",)


def read(p):
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def canonical():
    seen, out = set(), []
    for name in re.findall(r'\[data-theme="(\w+)"\]', read(THEMES)):
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out


def choosers(order):
    """-> [(file, label, [themes in the order they are offered])]"""
    known = set(order)
    found = []
    for path in glob.glob(os.path.join(ROOT, "**", "*.html"), recursive=True) + \
               glob.glob(os.path.join(ROOT, "**", "*.js"), recursive=True):
        rel = os.path.relpath(path, ROOT).replace("\\", "/")
        if any(rel.startswith(d + "/") for d in SKIP_DIRS):
            continue
        src = read(path)

        # <select> option lists. Only those made ENTIRELY of theme names --
        # the mode select next door is options too, and it is not this list.
        for m in re.finditer(r"<select\b[^>]*>(.*?)</select>", src, re.S | re.I):
            opts = [o.strip().lower()
                    for o in re.findall(r"<option[^>]*>([^<]*)</option>", m.group(1))]
            if opts and set(opts) <= known:
                found.append((rel, "<select>", opts))

        # JS arrays of theme names, which is how the two tuners hold theirs.
        for m in re.finditer(r"=\s*\[([^\]\[]*)\]", src):
            items = [i.strip().strip("\"'").lower() for i in m.group(1).split(",") if i.strip()]
            if len(items) > 1 and set(items) <= known:
                found.append((rel, "array", items))
    return found


def main():
    order = canonical()
    fails = []
    lists = choosers(order)

    for rel, kind, items in lists:
        # A chooser may legitimately offer a SUBSET -- what it must not do is
        # offer them in a different relative order.
        expected = [t for t in order if t in items]
        if items != expected:
            fails.append("%s %s\n      offers   %s\n      canonical %s"
                         % (rel, kind, " ".join(items), " ".join(expected)))

    print("canonical order (core/themes.css): %s" % " ".join(order))
    print("%d theme chooser(s) checked" % len(lists))
    if fails:
        print()
        for f in fails:
            print("  FAIL  %s" % f)
        return 1
    print("every chooser agrees")
    return 0


if __name__ == "__main__":
    sys.exit(main())
