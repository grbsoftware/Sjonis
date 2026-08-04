# Sjonis — handoff

Project name: **Sjonis**. Lives at `C:\Users\grben\Design`.

Written 2026-08-04 at context ceiling. Current state, decisions, and dead ends.
Second half of this file is the newer material — read `## NEXT` first.

## Working loop (how this session actually ran)

Gary ran `/loop` and asked for autonomous work: fix bugs, add missing pieces,
commit and push each change, wake him only for decisions that are genuinely his.
That mandate still stands unless he says otherwise. He also said to be creative
and add features not yet discussed.

**Every change ships.** The cycle that worked, and should be repeated:

```bash
python tools/build_themes.py verify     # round trip, MUST pass before commit
python tools/validate_palette.py        # contrast; exit 1 on required failure
python tools/check_adapters.py          # adapter refs resolve
git add -A && git commit && git push origin main
gh api repos/grbsoftware/Sjonis/pages/builds/latest --jq .status   # poll to "built"
```

Then verify **on the live site**, not locally — the preview pane cannot open
`file://` here, and `file://` cannot do the cross-frame work anyway. Screenshots
often fail ("pane not displayed"); `mcp__Claude_Browser__javascript_tool` against
the served URL works reliably and is the tool of choice for verification.

If a theme colour changes: `python tools/css_to_tokens.py` then
`python tools/build_themes.py all` to regenerate `tokens/` and `dist/`, or the
round trip fails.

## Who / how to work

Gary: hardware + network background, artist, "vibe coder." Knows how systems talk,
not framework specifics. **Has ADHD — keep replies short.** Lead with the answer,
few bullets, one next step. Detail goes in files, not chat. When he says a tangent
is irrelevant, drop it completely.

He wants push-back, not a menu of options. Act as expert web designer / UI-UX dev.
His friend **Ken** is a real coder and a useful second opinion — take his input
seriously but check it against Gary's actual requirements.

**Never use the Claude-in-Chrome tools** — they corrupted his MSIX install and
forced a Claude Desktop reinstall. Use WebSearch/WebFetch.

## What exists

```
core/ui.css          structure + components, zero colours
core/themes.css      6 themes x light/dark (589 tokens, 18 blocks)
core/ui.js           LAYER 2 — behaviour. classic script, no deps, no build
index.html           EXAMPLE BROWSER — the front door. Frames every example,
                     hash-routed, global dark toggle, live tuner (T)
demo/behaviour.html  exercises every behaviour, all 6 themes live
demo/img/*.svg       14 placeholder drawings, transparent grounds
archetypes/app-shell.html          rail + main — the admin pattern
archetypes/portfolio.html          banded content page — the anti-admin
archetypes/storefront.html         catalogue — site frame + product grid
archetypes/storefront-product.html page two of the same site
archetypes/editorial.html          long-form — columns, drop cap, pull quotes
tools/validate_palette.py   WCAG contrast over every theme x mode
tools/check_adapters.py     adapter references resolve
tools/fonts.py              Google Fonts catalogue: fetch / find / show
tokens/fonts.catalogue.json 1,942 families, generated
LICENSE.md           PolyForm Noncommercial 1.0.0
tokens/themes.tokens.json   W3C DTCG, generated from CSS
tokens/fonts.json    15 OFL fonts, curated shortlist
tools/css_to_tokens.py, build_themes.py   (Python — NO NODE on this machine)
adapters/tailwind-v4.css, shadcn.css
archetypes/app-shell.html
dist/gtk/, dist/xaml/    generated, 12 files each
demo/gallery.html    live tuner: layout x theme x density/radius/accent + CSS export
.claude/skills/ui-suite/  SKILL.md + references/palettes.md
```

Artifacts: [tuner](https://claude.ai/code/artifact/089593e5-f49b-4b33-ae38-de4964fde67d) ·
[iteration 01 specimens](https://claude.ai/code/artifact/5df3c67f-ff6f-4635-9808-73dbeddc1681)

Always run `python tools/build_themes.py verify` after touching themes
(427 tokens, 18 blocks, currently lossless).

## Architecture (settled)

Two independent axes. **Archetype** = structure, chosen by what it is.
**Theme** = appearance, chosen by who it's for. Archetypes contain no colour,
size or typeface — only `--ui-*` tokens. Vanilla CSS, no build step for consumers.

Themes: vanilla (open-source default), blueprint, halo, graphite, oxide, vellum.
Gary's favourites: **halo** and **blueprint** (opposite poles — that's why the
two-axis split is right).

## Traps already hit — do not re-learn

1. **`var()` in a custom property is substituted where DECLARED.** The `--ui-s*`
   scale had to move from `:root` to `:root,.ui`, or density silently does nothing
   when a theme sits on a descendant. This broke theme density too, not just the
   slider.
2. **shadcn's `--accent` is its hover surface, NOT the brand colour** (`--primary`
   is). Mapping our accent onto it turns every hover neon. Adapter handles it.
3. **Halo is the least portable theme** — depends on `backdrop-filter`, which is
   compositor-dependent on Linux and unreliable in WebKitGTK (what Tauri uses).
   Blueprint is the most portable.
4. **Tailwind `@theme inline`** — the `inline` keyword is load-bearing; without it
   values bake at build time and freeze to whichever theme compiled.
5. **`[hidden]` is a ZERO-specificity UA rule**, so any class that sets `display`
   beats it — `.ui-scrim{display:grid}` left a "hidden" overlay covering the
   page. `ui.css` now restates `.ui [hidden]{display:none}` above class level.
6. **The HTML `pattern` attribute compiles with the `v` regex flag**, where
   `[a-z0-9-]` is an invalid character class — and per spec an uncompilable
   pattern is *ignored entirely*, so the field silently accepts anything. Worst
   possible failure mode. Escape as `[a-z0-9\-]`. ui.js detects, warns, and
   re-enforces under `u`.
7. **Never flag "already wired" in a data-attribute.** `dataset.uiMenu` IS
   `data-ui-menu` — the flag overwrote the selector it was about to read. ui.js
   keeps wiring state in a WeakMap, off the DOM entirely.
8. `<dialog>`'s `close` event and `<details>`'s `toggle` event are **queued, not
   synchronous**. Tests that assert immediately after will see the old state.
9. **`100vw` includes the vertical scrollbar; the page's width does not.** Every
   `.ui-bleed` overhung by ~15px and gave the document a horizontal scrollbar.
   `.ui-page` now sets `overflow-x:clip` — `clip`, not `hidden`, because hidden
   makes it a scroll container and breaks `position:sticky` inside.
10. **Native controls are painted by the UA, not by CSS.** Dark themes had
   white-on-white `<select>` drop-downs until `--ui-scheme` drove `color-scheme`.
   Same fix covers scrollbars, carets, spinners, date pickers.
11. **A translucent token on a UA-painted surface has nothing behind it.** The
   `<select>` option rule painted with `--ui-surface`; halo is the only theme
   whose surfaces are `rgba`, and in dark that is `rgba(255,255,255,.055)` —
   composited over the UA's own white popup base, not over our page, so it
   resolved to near-white under near-white `--ui-text`. Invisible. Halo *light*
   passed by luck (.72 white over white, dark text), which is why it read as a
   dark-mode-only bug. Rule: UA surfaces get `--ui-bg`, the only ground that is
   opaque in all six themes. Gary found this one.
12. **A percentage inside `columns:` resolves against the COLUMN box.** The side
   pull quote was `width:min(20rem,42%)`; inside a 22rem column that is ~150px,
   about seven characters a line, with the body text squeezed into the rest.
   Anything floated inside multi-column text has to be sized against the column,
   not the container — and usually should not float at all.
13. **The browser caches `core/*.css` and `ui.js` for 10 minutes on Pages.**
   A page loaded before a push keeps the old assets and the new work looks
   broken. Verify with a cache-buster:
   `document.querySelectorAll('link[rel=stylesheet]').forEach(l=>l.href=l.href.split('?')[0]+'?cb='+Date.now())`
   and re-inject `ui.js?cb=…` — three "bugs" this session were only this.
14. **The preview pane caches `core/*.css` and `ui.js` hard.** Edits appear not
   to work. Test with a cache-busted copy:
   `sed -e "s|../core/ui.css|../core/ui.css?v=$(date +%s)|" … > demo/_x.html`
   (gitignored), and delete it after. It also reports every element as visible,
   so IntersectionObserver work can only be confirmed with a tall spacer probe.

## Positions taken

- **Colour psychology is mostly unevidenced.** Meaning is learned and contextual
  (Elliot & Maier, colour-in-context). Blue+orange+grey works for tools via
  *category convention* + *contrast role-separation*, not innate feeling. The
  suite encodes audience presets with stated reasoning. See references/palettes.md.
- **Font "science" is half real.** Legibility (x-height, counters, character
  differentiation) is solid research. Personality ("serif = trustworthy") is
  convention. Dyslexia-specific fonts test poorly.
- **Python for tooling, not C.** C has no JSON and no regex on Windows; needs a
  compiler per platform. Tokens are the asset, the generator is disposable.
- **Don't base the core on shadcn.** It's React+Tailwind+build step and ships one
  look — the opposite of the multi-look requirement. Adapters instead.

## OPEN — the two live threads

### 1. Layout monoculture (Gary's critique, valid)
Everything built so far is ONE paradigm: rail + main, operator-facing, data-dense.
Dashboard / split / settings / palette are four **pages of the same app**, not four
layouts. Gary noted his friend got near-identical output from Fable — mode collapse
toward SaaS admin.

Missing genuinely different skeletons: **artist/portfolio** (full-bleed, masonry,
horizontal scroll), **game** (HUD, hero art, leaderboards, loud display type),
**editorial/zine** (multi-column, pull quotes, overlap), **marketing**, **media
player**, **storefront**.

Honest gap: `ui.css` has **no grid system, no image handling, no hero primitives**.
The "just add markup" claim stops being true here. This needs real new CSS.

### 2. Font DB scale — DONE
`tools/fonts.py` + `tokens/fonts.catalogue.json`. 1,942 families, 555 variable,
828 kB, from the public Google Fonts metadata endpoint (no API key, stdlib only).
Records only what is checkable; records no x-height or personality rating on
purpose. `fonts.py find --category mono --variable --max-kb 200`, `fonts.py show
Inter`. `tokens/fonts.json` stays the curated shortlist with reasoning.

Still open here: nothing blocking. A "try this font" hook in the tuner would be
the natural next step — pick from the catalogue, inject the `@font-face`, look
at it — but that needs network at runtime, which the suite currently never does.

## DONE since last handoff — layer 2

Gary asked "what is the next layer, something js/react related right?" — yes.
CSS = faceplate, JS = wiring, React = control system. **Layer 2 is now built**:
`core/ui.js`, ~36 kB unminified, zero dependencies, no build step.

Deliberate constraints: classic script not an ES module (modules are blocked on
`file://`, and double-clicking one .html must keep working); declarative
data-attributes so no init code can be forgotten; and use the platform —
`<dialog>` for modals, `<details>` for accordions, the constraint-validation API
for forms. Each of those is a focus trap or state machine we would otherwise get
subtly wrong. Everything degrades: remove the file and the page still reads.

Covers dialog + promise-based confirm, anchored menu with type-ahead, tabs,
accordion, toast, tooltip, sortable table, live filter, clipboard, form
validation, command palette, and runtime theme/density/mode with localStorage.
All verified working in-browser across themes; see traps 5–8 above, all four
were found and fixed during that verification.

**Layer 3 (React) is still not started** — and worth questioning before starting.
It buys component reuse and state, but costs the no-build-step property that is
currently the suite's best feature. A thin `useUI()` wrapper over these same
data-attributes may be enough.

## DONE — layout monoculture, first half

**`git` is now in use.** Gary asked for it specifically so the look cannot drift
between versions unintentionally. Commit anything that changes appearance, with
a message saying what moved and why. `python tools/build_themes.py verify` before
every commit.

`archetypes/portfolio.html` shares no layout code with the app shell: no rail, no
toolbar, no table. A stack of full-width **bands**, each with a centred
**measure**. It needed the primitives ui.css genuinely lacked, all now in:

- `.ui-page` / `.ui-band` / `.ui-measure` / `.ui-bleed`
- `.ui-cols` (auto-fit, no breakpoints), `.ui-wall`, `.ui-justified`, `.ui-reel`,
  `.ui-marquee`
- `.ui-frame` aspect-ratio boxes, `.ui-figure`, `.ui-caption`, `.ui-frame-label`
- `.ui-display` / `.ui-lead` / `.ui-prose` / `.ui-quote`, derived `--ui-fs-display`

**Justified rows** are the gallery layout: give each item a `flex-grow` AND
`flex-basis` proportional to its aspect ratio and every item in a row lands on
the same height. `<i class="ui-fill">` (huge grow, zero height) can only reach
the last row, where it stops two leftovers stretching to half the page.

**Lazy loading** — Gary wants this free because galleries charge for it. Native
`loading="lazy"` does the download deferral; the value added is the reserved box,
the shimmer, the fade, the error state, and NOT fading cached images (flicker on
scroll-back is worse than no animation). `data-src` defers harder but needs JS.

**Marquee** — auto-scrolls, track cloned in JS for a seamless loop, clones
`aria-hidden`. Pauses on hover, focus and click (10s), stops when the tab is
hidden, and under `prefers-reduced-motion` it stops moving and becomes a
scrollable reel — hidden overflow plus no animation would strand the content.

**Categorical colour** — `--ui-cat-1..8`, identity rather than state, validated
with the dataviz skill's Python validator against every theme surface. Position
held and agreed: the four state colours keep their conventional hues; themes vary
the hue, never the role. Node is NOT installed — use `validate_palette.py`, and
set `PYTHONIOENCODING=utf-8` or it dies on cp1252.

## DONE — published, licensed, and the site frame

**Sjonis is public and live: https://grbsoftware.github.io/Sjonis/**
Repo `grbsoftware/Sjonis`, Pages from `main` at root. Local `master` was renamed
`main`. Git identity was set repo-local (it had been global and was lost).
After every push, Pages takes 30–90s to rebuild — poll
`gh api repos/grbsoftware/Sjonis/pages/builds/latest --jq .status`.

**Licence: PolyForm Noncommercial 1.0.0** (`LICENSE.md`), verbatim. Noncommercial
use fully granted; **commercial use requires a separate licence from Gary**, so a
commercial user has to make contact. Gary considered cutting the free-use grant
for government and decided against it — do not re-open unprompted. Contact is
routed through GitHub, not his email, deliberately: a plain-text address on a
public repo is scraped within days. GitHub shows no licence badge because
PolyForm is not OSI — that is expected, not a misconfiguration.

**`index.html` — the example browser.** Every example in one frame: prev/next,
tab strip, arrow keys, width presets. The hash is the state, so the browser's own
back/forward walk the viewing history and `#storefront` links land. Dark by
default and the toggle is **global** — it drives the framed document too, because
a dark surround with a white page inside is worse than either alone. How each
page takes that instruction is **declared per example, not sniffed**: `data-theme`
means a suite theme on an archetype and light/dark on a standalone demo page, so
guessing breaks one of them. Reaching into the frame needs same origin — it works
on the served site, and from `file://` only the chrome switches.

**The site frame** — the layer above the page, which the suite genuinely lacked.
`.ui-skip`, `.ui-sitehead` (+`-stick`, `-sunk`), `.ui-sitebar`, `.ui-sitenav`
(+`-item`, `aria-current`), `.ui-sitehead-actions`, `.ui-crumbs`, `.ui-sitefoot`
(+`-cols`, `-base`). Deliberately not the app shell's rail: a rail is for an
operator moving between views of one tool and owns the viewport; a site header is
for a reader moving between documents and yields to the content.

**`archetypes/storefront.html`** — the third skeleton, and the proof the site
frame generalises: it reuses the header, crumbs and footer markup unchanged.
New COMMERCE primitives in ui.css: `.ui-price`/`-was`/`-note`, `.ui-badge`,
`.ui-swatch`/`.ui-swatches`, `.ui-frame-muted`, `.ui-card-body`.

**New in ui.js**: `data-ui-choice` (single-select button group, `aria-pressed`,
arrow keys) and the live filter now honours `data-ui-item`, so a card grid can be
filtered — it only understood list items and table rows before.

**`tools/validate_palette.py` now exists.** RESUME used to reference one that was
never in the repo. It models the pairings ui.css actually produces (`.ui-pill`
has no background, so its hue meets the page, never `--ui-*-soft`), composites
rgba tokens over their ground first, and prints ASCII only so cp1252 cannot kill
it. `python tools/validate_palette.py`, exit 1 on failure.

## Traps found by measuring rather than looking

Two bugs this session were invisible on screen and obvious in arithmetic. Both
had been shipped and reviewed without anyone noticing:

- **The black-vs-white ink crossover is 0.1791, not 0.45 or 0.5.** White beats
  black only while `1.05/(L+0.05) > (L+0.05)/0.05`, so the boundary is
  `sqrt(0.0525) - 0.05`. The old 0.45 gave a mid ochre accent white text at
  2.17:1 where black scores 9.70:1. Four of six test hues flipped.
- **halo light shipped a failing button label** — `#FFFFFF` on `#0E9C86`, 3.43:1.
  Now `#06231F`, which halo dark already used, 4.83:1.

The lesson worth keeping: contrast is not a thing to eyeball. `validate_palette.py`
found the second one in a second, and would have found the first if the tuner's
maths had been in a checkable place rather than inline in a page.

Three more of the same kind, from the palette work:

15. **A checker must measure what the CSS computes, not what the token says.**
   Once `.ui-dot` gained a rim, the thing meeting the ground was a computed
   `color-mix`, not `--ui-cat-4`. `validate_palette.py` grew OKLab conversion and
   `mix_oklab` so it measures the rim; left alone it would have gone on reporting
   126 failures for a problem that had been solved a different way. It still
   prints the fill-vs-ground ratio as *advisory*, so the cost of the choice stays
   visible rather than being quietly dropped.
16. **Rounding to hex can undo a solved contrast value.** Up to half a step per
   channel, which is enough to drop a solved 4.502 back under 4.5. Five tokens
   landed at 4.49–4.50. Solve, round, then re-check the ROUNDED value, with margin.
17. **halo's `-soft` tokens are `rgba(<the state hue>,.12)`** — so moving a hue
   also moves the ground that hue is read against, and fixing them in sequence
   oscillates. Hue and tint have to be solved together, recomputing the tint from
   each candidate. It converges because the tint moves at 12% of the hue's rate.
   Any derived token has this shape; check for it before solving one in isolation.

## DONE — the palette thread is CLOSED. 125 failures -> 0.

Both halves shipped and verified on the live site. `validate_palette.py` exits 0.

**The rim (Gary's decision, implemented).** No `--ui-cat-*` value changed.
`.ui-dot`, `.ui-tag::before` and `.ui-swatch` carry a 1px rim of their own hue
mixed 55% toward `--ui-text`, so it darkens on light grounds and lightens on dark
without ui.css naming a colour. Worst case 3.76:1, was 1.86:1. The rim is
declared **on the mark, never at :root** — trap 1 would bake `--ui-series` to its
fallback and rim every dot as cat-1. Tunable via `--ui-mark-rim-mix`, which is a
plain percentage and therefore safe to set from any level.

**State colours moved.** The remaining 33 failures were all a state hue printed
AS TEXT (`.ui-pill-*` has no background; `.ui-banner-*` sits on its own soft
ground), sitting at 2.72–4.49 against a 4.5 bar. Unlike the categorical set there
was no competing constraint — four hues at conventional positions have room that
eight mutually-separated series hues do not. 15 tokens moved by the minimum:
hold OKLCH hue and chroma, walk lightness toward the ink, stop at the first value
clearing every ground it meets. Most moved under 0.03 L and are invisible.

**halo light is the one visible change and the one to re-check with Gary.** It
was worst (warn 2.72), so it moved furthest; its four states now read distinctly
deeper. `--ui-accent` moved only `#0E9C86` -> `#0C9B85`, so halo's mint is
intact — but `--ui-good` was *the same value as the accent* and could not stay
bright. If Gary dislikes it, the alternative is to stop printing state hues as
text in halo and carry them on a border + dot the way `.ui-tag` already does.
Specimen artifact showing every before/after:
https://claude.ai/code/artifact/598ce1c1-d2b7-486a-b89f-2e507c50148b

Also fixed in passing: `.ui-tag::before` had no forced-colours border (the tag's
dot vanished under Windows High Contrast), and marks now `print-color-adjust:
exact` — a browser drops backgrounds on paper, and a legend whose dots did not
print is a list of labels bound to nothing.

## NEXT

**Not started, and it was next in line: the GAME / HUD archetype.** The most
different remaining skeleton — overlaid HUD chrome on hero art, a leaderboard,
loud display type, no reading measure at all. `marketing` and `media player`
from the original monoculture list are also unbuilt, but game is the one that
proves the primitives stretch furthest. Nothing blocks it; it just needs a fresh
context window, which is why it was deferred rather than half-built.

Likely new primitives it would need, none of which exist yet: an overlay layer
positioned over a full-bleed image, a stat readout at display size, a ranked
table with a highlighted "you" row, and a progress/meter element — `ui.css` has
no meter of any kind, which is a real gap independent of the game page.

### DECIDED 2026-08-04 — palette: rim the dots — SHIPPED, see "palette thread is
CLOSED" above. The 55% guess in the original decision turned out to be exactly
right (worst 3.76:1); 65% would have been the edge at 2.99.

### NEW DIRECTION — more palettes, and Radiance

Gary: "there are palettes I like a lot that are not listed. For instance I really
like blue purple and green together." He is unsure whether it belongs here,
"always, or yet" — so treat it as an invitation, not a spec, and push back if it
does not fit.

Honest read to carry forward: that is an **analogous** scheme (adjacent hues),
and the current `--ui-cat-*` set is deliberately the opposite — maximally
separated hues, because eight series must stay apart from EACH OTHER. Analogous
palettes are gorgeous and are the wrong tool for categorical identity. Where they
genuinely fit: a **sequential/continuous** ramp (one variable, low to high), a
theme's accent family, or a decorative gradient. So the right move is probably a
NEW token family — a sequential ramp — rather than editing `--ui-cat-*`.

**Radiance** is Gary's own public repo (`grbsoftware/Radiance`): a PWA that
generates palettes by HSL interpolation between anchor colours. Not yet read.
The real question to answer next session: could its interpolation formulae
generate a perceptually even sequential ramp for Sjonis? Caveats to check first —
HSL interpolation is not perceptually uniform (it bunches and produces dead
greys through the middle); OKLCH would be. If Radiance is HSL-only, the useful
move may be to improve Radiance's maths (oklch interpolation) and then reuse it,
which serves both projects.

- **The palette decision** — DONE. Nothing left open except Gary's eye on halo light.
- Layer 3 (React) still unstarted and still worth questioning, because it costs
  the no-build-step property that is currently the suite's best feature.
- **Adapters — DONE this session.** Both now expose `--ui-cat-1..8` (shadcn's
  `--chart-1..5` plus 6-8 under our names; Tailwind's `text-cat-3` etc). The
  shadcn file had a stale note declining to map charts because "our single
  accent cannot supply" series colours — untrue since the categorical work.
  Boundary confirmed and now stated in both files: adapters bridge **tokens,
  never classes**. `tools/check_adapters.py` gates it.
- **Print / forced-colors / reduced-transparency — DONE this session.** See
  README. `prefers-reduced-motion` was the only one previously handled.
- `demo/gallery.html` is now largely redundant. Tuning moved to `index.html`,
  which reaches into the framed document and tunes the REAL archetype files;
  gallery still tunes four hand-built mini-layouts that duplicate the
  archetypes and drift from them. Either retire it or repoint it — but it is
  still the only place showing one layout across six themes side by side, so
  decide deliberately rather than deleting it.
- Adapters (`adapters/tailwind-v4.css`, `shadcn.css`) predate the site frame,
  commerce and editorial primitives and only bridge tokens, not classes — check
  whether that is still the right boundary before extending them.

Five archetype files now exist: app-shell, portfolio, storefront,
storefront-product, editorial. The layout-monoculture thread is closed — four
genuinely different skeletons (the fifth is page two of one of them), not four
pages of one app.

## Working with Gary — what came up this session

- He catches real regressions. He spotted that baking a background into the
  placeholder SVGs broke theming (they're transparent now, so the art takes the
  theme's ground). Take his visual reports seriously and go measure.
- Credit generated art as **generated by Claude, reviewed and approved by Gary**.
  His reasoning: unreviewed AI work presented as finished reflects badly on
  Anthropic. He also asked for the artist link to point at anthropic.com.
- He asks good structural questions (density vs text size) — answer the contract
  question even when deferring the feature.
