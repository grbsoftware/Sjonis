#!/usr/bin/env python3
"""Check the adapters against the token contract.

An adapter is a promise that every name on its left-hand side resolves to a
real token on its right. Nothing enforces that: rename a token in themes.css
and the adapter keeps compiling, keeps loading, and silently hands every
consumer an empty value. CSS has no undefined-variable error.

    python tools/check_adapters.py         # exit 1 if an adapter is broken
    python tools/check_adapters.py -v      # also list tokens no adapter exposes

The second list is informational, not a failure. Plenty of tokens are
intentionally suite-only — --ui-scheme drives color-scheme and has no meaning
in Tailwind, --ui-blur has no namespace to live in.
"""

import io
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SOURCES = ["core/ui.css", "core/themes.css"]
ADAPTERS = ["adapters/tailwind-v4.css", "adapters/shadcn.css"]


def read(rel):
    with io.open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def main(argv):
    verbose = "-v" in argv

    defined = set()
    for src in SOURCES:
        # A declaration, not a use: "--ui-x:" with no var( in front of it.
        defined |= set(re.findall(r"(--ui-[\w-]+)\s*:", read(src)))

    broken = []
    exposed = set()
    for rel in ADAPTERS:
        used = set(re.findall(r"var\((--ui-[\w-]+)", read(rel)))
        exposed |= used
        missing = sorted(used - defined)
        print("%-30s %3d tokens referenced, %d missing" % (rel, len(used), len(missing)))
        for m in missing:
            print("    MISSING  %s" % m)
            broken.append((rel, m))

    print("")
    print("%d tokens defined across %s" % (len(defined), ", ".join(SOURCES)))

    if verbose:
        gap = sorted(defined - exposed)
        print("")
        print("not exposed by any adapter (%d) — informational:" % len(gap))
        for g in gap:
            print("   ", g)

    if broken:
        print("")
        print("BROKEN: %d adapter reference(s) point at tokens that do not exist." % len(broken))
        return 1
    print("all adapter references resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
