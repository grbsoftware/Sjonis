#!/usr/bin/env python3
"""The font catalogue: fetch it, then filter it.

Cataloguing is nearly free; bundling is what costs bytes. Those are different
questions and conflating them is why this suite shipped with fifteen fonts for
so long. The catalogue below is the whole Google Fonts library — 1,900+ families
— and the point of it is not the list, it is the FILTER.

    python tools/fonts.py fetch
    python tools/fonts.py find --category serif --variable --subset latin
    python tools/fonts.py find --max-kb 60 --sort popularity --limit 10
    python tools/fonts.py show Inter

What is recorded is only what is verifiable from the metadata: family, category,
weights, styles, variable axes, subsets, designers, file size, licence flag and
dates. Deliberately NOT recorded: x-height, "distinctiveness", personality, or
whether a face is good for dyslexic readers. Those are either judgments or
measurements of the font binary, and writing a guess into a data file is how a
guess becomes a fact three months later. tokens/fonts.json stays the curated
shortlist with reasoning attached; this is the long tail with none.

No dependencies — urllib and json are stdlib. No API key: the metadata endpoint
is public.
"""

import argparse
import io
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
SRC = "https://fonts.google.com/metadata/fonts"
OUT = os.path.join(ROOT, "tokens", "fonts.catalogue.json")

CATEGORIES = {
    "serif": "Serif", "sans": "Sans Serif", "sans-serif": "Sans Serif",
    "display": "Display", "handwriting": "Handwriting", "mono": "Monospace",
    "monospace": "Monospace",
}


# --------------------------------------------------------------------------

def slim(entry):
    """Keep what is checkable, drop what is not."""
    fonts = entry.get("fonts") or {}
    weights, italic = set(), False
    for key in fonts:
        if key.endswith("i"):
            italic = True
            key = key[:-1]
        if key.isdigit():
            weights.add(int(key))

    axes = entry.get("axes") or []
    return {
        "family": entry.get("family"),
        "category": entry.get("category"),
        "weights": sorted(weights),
        "italic": italic,
        "variable": bool(axes),
        "axes": [{"tag": a.get("tag"), "min": a.get("min"), "max": a.get("max")}
                 for a in axes],
        # menu is the tiny preview subset Google ships with every family; it is
        # not a language subset and would make every filter match.
        "subsets": [s for s in (entry.get("subsets") or []) if s != "menu"],
        "designers": entry.get("designers") or [],
        "bytes": entry.get("size"),
        "openSource": entry.get("isOpenSource"),
        "added": entry.get("dateAdded"),
        "updated": entry.get("lastModified"),
        # Google's own popularity rank. Recorded because it is a fact about the
        # catalogue, not an opinion about the typeface.
        "popularity": entry.get("popularity"),
    }


def cmd_fetch(args):
    print("fetching %s ..." % SRC)
    req = urllib.request.Request(SRC, headers={"User-Agent": "sjonis-fonts/1.0"})
    with urllib.request.urlopen(req, timeout=60) as fh:
        raw = json.loads(fh.read().decode("utf-8"))

    fams = raw.get("familyMetadataList") or []
    if not fams:
        print("no families in response — the endpoint's shape may have changed")
        return 2

    out = {
        "source": SRC,
        "families": sorted((slim(f) for f in fams), key=lambda f: f["family"] or ""),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False, sort_keys=False)
        fh.write("\n")

    kb = os.path.getsize(OUT) / 1024.0
    var = sum(1 for f in out["families"] if f["variable"])
    print("wrote %s" % os.path.relpath(OUT, ROOT))
    print("  %d families, %d variable, %.0f kB" % (len(out["families"]), var, kb))
    return 0


def load():
    if not os.path.exists(OUT):
        print("no catalogue yet — run:  python tools/fonts.py fetch")
        sys.exit(2)
    with io.open(OUT, encoding="utf-8") as fh:
        return json.load(fh)["families"]


def cmd_find(args):
    fams = load()
    want = CATEGORIES.get((args.category or "").lower()) if args.category else None

    def keep(f):
        if want and f["category"] != want:
            return False
        if args.variable and not f["variable"]:
            return False
        if args.axis and args.axis not in [a["tag"] for a in f["axes"]]:
            return False
        if args.subset and args.subset not in f["subsets"]:
            return False
        if args.weight and args.weight not in f["weights"]:
            return False
        if args.italic and not f["italic"]:
            return False
        if args.max_kb and (f["bytes"] or 0) / 1024.0 > args.max_kb:
            return False
        if args.name and args.name.lower() not in (f["family"] or "").lower():
            return False
        return True

    hits = [f for f in fams if keep(f)]
    if args.sort == "popularity":
        hits.sort(key=lambda f: f["popularity"] if f["popularity"] is not None else 10 ** 6)
    elif args.sort == "size":
        hits.sort(key=lambda f: f["bytes"] or 0)
    elif args.sort == "newest":
        hits.sort(key=lambda f: f["added"] or "", reverse=True)
    else:
        hits.sort(key=lambda f: f["family"] or "")

    total = len(hits)
    if args.limit:
        hits = hits[:args.limit]

    print("%-34s %-11s %-5s %-7s %s" % ("FAMILY", "CATEGORY", "VAR", "kB", "WEIGHTS"))
    print("-" * 82)
    for f in hits:
        kb = "%.0f" % ((f["bytes"] or 0) / 1024.0)
        ws = ",".join(str(w) for w in f["weights"][:6]) or "-"
        if len(f["weights"]) > 6:
            ws += ",..."
        print("%-34s %-11s %-5s %-7s %s" % (
            (f["family"] or "")[:34], (f["category"] or "")[:11],
            "yes" if f["variable"] else "", kb, ws))
    print("")
    print("%d of %d families shown" % (len(hits), total))
    return 0


def cmd_show(args):
    fams = load()
    name = args.family.lower()
    hit = [f for f in fams if (f["family"] or "").lower() == name]
    if not hit:
        hit = [f for f in fams if name in (f["family"] or "").lower()][:5]
        if not hit:
            print("no family matching %r" % args.family)
            return 1
        if len(hit) > 1:
            print("did you mean: " + ", ".join(f["family"] for f in hit))
            return 1
    f = hit[0]
    print(f["family"])
    print("-" * len(f["family"]))
    print("  category   %s" % f["category"])
    print("  weights    %s%s" % (", ".join(str(w) for w in f["weights"]) or "-",
                                 "  (+ italics)" if f["italic"] else ""))
    if f["variable"]:
        print("  variable   " + ", ".join(
            "%s %g-%g" % (a["tag"], a["min"], a["max"]) for a in f["axes"]))
    print("  size       %.0f kB (all styles)" % ((f["bytes"] or 0) / 1024.0))
    print("  subsets    %s" % ", ".join(f["subsets"]))
    print("  designers  %s" % ", ".join(f["designers"]))
    print("  added      %s   updated %s" % (f["added"], f["updated"]))
    print("")
    print("  Use it:")
    print("    --ui-font: \"%s\", system-ui, sans-serif;" % f["family"])
    print("  Sjonis records no opinion on x-height, personality or legibility.")
    print("  Set it in the tuner and look at it.")
    return 0


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")

    sub.add_parser("fetch", help="download and slim the catalogue")

    fi = sub.add_parser("find", help="filter the catalogue")
    fi.add_argument("--category", help="serif, sans, display, handwriting, mono")
    fi.add_argument("--variable", action="store_true", help="variable fonts only")
    fi.add_argument("--axis", help="require a variable axis, e.g. wght, opsz, slnt")
    fi.add_argument("--subset", help="require a script subset, e.g. latin, greek, cyrillic")
    fi.add_argument("--weight", type=int, help="require a static weight, e.g. 700")
    fi.add_argument("--italic", action="store_true", help="must ship italics")
    fi.add_argument("--max-kb", type=float, dest="max_kb", help="total size ceiling")
    fi.add_argument("--name", help="substring of the family name")
    fi.add_argument("--sort", choices=["name", "popularity", "size", "newest"], default="name")
    fi.add_argument("--limit", type=int, default=40)

    sh = sub.add_parser("show", help="everything known about one family")
    sh.add_argument("family")

    args = ap.parse_args(argv[1:])
    if args.cmd == "fetch":
        return cmd_fetch(args)
    if args.cmd == "find":
        return cmd_find(args)
    if args.cmd == "show":
        return cmd_show(args)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
